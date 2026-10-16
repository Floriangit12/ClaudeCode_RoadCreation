#!/usr/bin/env python
"""OSM de l'état (lot 1g du plan, § 5) : extraction Overpass « attic » à la date OSM de l'état, découpée en couches
osm_* comme les couches du dépôt (pipeline/osm.py, puis pipeline/site_extract.py), et comparaison aux autres dates.

    python -I recon/pcg/etat/sources/osm_historique.py telecharger [--dates AAAA-MM-JJ ...]
    python recon/pcg/etat/lancer.py --etat avant_travaux -- python -I recon/pcg/etat/sources/osm_historique.py couches

- telecharger : réponse brute d'Overpass (jamais modifiée) dans data/sites/paquet_jardin/avant_travaux/osm_<date>/,
  avec sa requête et son sha256 ; dates par défaut : date OSM de l'état et de chacune de ses variantes, et la date
  cible de chaque variante (configuration recon/pcg/etat/etats/<id>.json) ;
- couches : relit la réponse de la date OSM de l'état courant (PJ_ETAT, PJ_DATE_CIBLE) et écrit, sans réseau et de
  façon déterministe, <dossier de l'état>/sources/osm_<date>/ : osm_<couche>.geojson (WGS84, même format que
  data/sites/paquet_jardin/vector/osm_*.geojson), osm_index.json (version et date de chaque objet), meta.json
  (sources, licence ODbL, etat_cible), osm_comparaison.json (objets supprimés, ajoutés ou déplacés par rapport aux
  autres instantanés) et carte_osm.png (fond ortho PCRS 2022).

Les réponses Overpass sont des données téléchargées, non fiables : lecture JSON seulement, script lancé avec -I.
OSM prouve une présence, jamais une absence (la carte s'enrichit sans que le terrain change).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
AT = RACINE / "data/sites/paquet_jardin/avant_travaux"
CONFIG = json.loads((RACINE / "config/meylan.json").read_text(encoding="utf-8"))
SITE = CONFIG["sites"]["paquet_jardin"]
O = tuple(SITE["center_l93"])
DEMI = float(SITE["half_size_m"])
UA = "meylan-adas-sim/0.1 (research; reconstruction avant travaux Paquet Jardin)"
SERVEURS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
HEURE = "00:00:00Z"   # instantané en début de journée, comme les extractions déjà présentes (osm_2022-05-10, osm_2025-06-01)

# Couches : mêmes prédicats que pipeline/osm.py (recopiés : ce module n'importe rien du pipeline)
AREA_KEYS = ("building", "area:highway", "landuse", "leisure", "natural", "amenity")
LAYERS = {
    "roads": (lambda t: "highway" in t and t["highway"] not in (
        "footway", "path", "steps", "cycleway", "pedestrian", "bridleway", "track",
        "crossing", "traffic_signals", "street_lamp", "bus_stop", "give_way", "stop",
        "platform", "elevator", "corridor", "proposed", "construction"), "way"),
    "cycleways": (lambda t: t.get("highway") == "cycleway" or t.get("bicycle") == "designated"
                  or any(k.startswith("cycleway") and k.count(":") <= 1
                         and v not in ("no", "none", "separate") for k, v in t.items()), "way"),
    "footways": (lambda t: t.get("highway") in ("footway", "path", "pedestrian", "steps"), "way"),
    "road_areas": (lambda t: "area:highway" in t or (t.get("highway") and t.get("area") == "yes"), "way"),
    "crossings": (lambda t: t.get("highway") == "crossing" or "crossing" in t, "node"),
    "traffic_signals": (lambda t: t.get("highway") == "traffic_signals" or
                        t.get("crossing") == "traffic_signals", "node"),
    "traffic_calming": (lambda t: "traffic_calming" in t, "any"),
    "kerbs": (lambda t: "kerb" in t or t.get("barrier") == "kerb", "any"),
    "road_signs": (lambda t: "traffic_sign" in t or t.get("highway") in ("stop", "give_way"), "node"),
    "street_lamps": (lambda t: t.get("highway") == "street_lamp", "node"),
    "public_transport": (lambda t: "public_transport" in t or t.get("highway") == "bus_stop", "any"),
    "parking": (lambda t: t.get("amenity") == "parking" or any(k.startswith("parking:") for k in t), "any"),
    "buildings": (lambda t: "building" in t, "way"),
    "trees": (lambda t: t.get("natural") in ("tree", "tree_row"), "any"),
    "barriers": (lambda t: "barrier" in t and t.get("barrier") != "kerb", "any"),
    "landuse": (lambda t: any(k in t for k in ("landuse", "leisure")) or
                t.get("natural") in ("wood", "grassland", "scrub", "water"), "way"),
    "railways_tram": (lambda t: "railway" in t, "any"),
}
TAGS_CLES = ("highway", "name", "building", "amenity", "barrier", "crossing", "kerb", "public_transport", "bus", "ref",
             "natural", "landuse", "leisure", "traffic_sign", "cycleway", "footway", "construction", "parking", "service",
             "oneway", "traffic_signals", "railway")


# --------------------------------------------------------------------------- outils
def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def rel(p):
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return str(p)


def ecrire(p, txt):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8", newline="\n")


def ecrire_json(p, obj, indent=1):
    ecrire(p, json.dumps(obj, ensure_ascii=False, indent=indent) + "\n")


def _transfo():
    from pyproj import Transformer
    if not hasattr(_transfo, "t"):
        _transfo.t = (Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True),
                      Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True))
    return _transfo.t


def wgs_l93(lon, lat):
    return _transfo()[0].transform(lon, lat)


def emprise_wgs84():
    """Carré O ± demi-côté (config/meylan.json) en WGS84, comme pipeline/site_extract.py : (ouest, sud, est, nord)."""
    t = _transfo()[1]
    (x0, y0), (x1, y1) = t.transform(O[0] - DEMI, O[1] - DEMI), t.transform(O[0] + DEMI, O[1] + DEMI)
    return x0, y0, x1, y1


def etat():
    sys.path.insert(0, str(RACINE / "recon/pcg/etat"))
    import etat_cible as EC  # noqa: PLC0415 (socle de la phase 0)
    return EC


def date_osm(E):
    return (E.config.get("dates_derivees") or {}).get("osm") or E.date_cible


def brut(d):
    """Réponse Overpass brute pour la date d (première trouvée), ou None."""
    fs = sorted((AT / f"osm_{d}").glob(f"overpass_{d}T*.json"))
    return fs[0] if fs else None


# --------------------------------------------------------------------------- téléchargement
def requete(d):
    w, s, e, n = emprise_wgs84()
    return (f'[out:json][timeout:300][date:"{d}T{HEURE}"];'
            f"(nwr({s:.6f},{w:.6f},{n:.6f},{e:.6f}););out meta geom;")


def dates_par_defaut(EC):
    E = EC.charger("avant_travaux" if not os.environ.get(EC.ENV_ETAT) else None)
    brut_cfg = json.loads(Path(E.fichier).read_text(encoding="utf-8"))
    ds = {date_osm(E), brut_cfg["date_cible"]}
    for v, var in (brut_cfg.get("variantes") or {}).items():
        ds.add(v)
        ds.add(((var.get("surcharges") or {}).get("dates_derivees") or {}).get("osm") or v)
    return sorted(ds)


def telecharger(a):
    import requests
    dates = a.dates or dates_par_defaut(etat())
    for d in dates:
        dt.date.fromisoformat(d)
        if brut(d):
            print(d, "déjà présent :", rel(brut(d)))
            continue
        q = requete(d)
        dest = AT / f"osm_{d}" / f"overpass_{d}T{HEURE[:2]}Z.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dernier = None
        for k in range(6):
            url = SERVEURS[k % len(SERVEURS)]
            try:
                r = requests.post(url, data={"data": q}, headers={"User-Agent": UA}, timeout=(30, 400))
                if r.status_code == 200 and r.content.lstrip().startswith(b"{"):
                    json.loads(r.content.decode("utf-8"))           # réponse complète et lisible
                    tmp = dest.with_name(dest.name + ".part")
                    tmp.write_bytes(r.content)
                    os.replace(tmp, dest)
                    ecrire_json(dest.with_name(f"requete_{d}.json"), {
                        "serveur": url, "requete": q, "telecharge_le": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fichier": dest.name, "octets": dest.stat().st_size, "sha256": sha256(dest),
                        "licence": "ODbL 1.0, © contributeurs OpenStreetMap"})
                    print(d, "->", rel(dest), dest.stat().st_size)
                    break
                dernier = f"HTTP {r.status_code} {r.text[:120]!r}"
            except (requests.RequestException, ValueError) as e:
                dernier = repr(e)[:200]
            time.sleep(15 * (k + 1))
        else:
            raise RuntimeError(f"Overpass indisponible pour {d} : {dernier}")
        time.sleep(10)


# --------------------------------------------------------------------------- découpe à l'emprise
def _clip_segment(p, q, b):
    """Liang-Barsky : partie du segment pq dans la boîte b = (x0, y0, x1, y1), ou None."""
    x0, y0, x1, y1 = b
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pk, qk in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if pk == 0:
            if qk < 0:
                return None
            continue
        t = qk / pk
        if pk < 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1:
            return None
    a = p if t0 == 0.0 else (p[0] + t0 * dx, p[1] + t0 * dy)
    c = q if t1 == 1.0 else (p[0] + t1 * dx, p[1] + t1 * dy)
    return a, c


def decouper_ligne(pts, b):
    """Polyligne découpée à la boîte : liste de morceaux (au moins 2 points distincts)."""
    morceaux, cour = [], None
    for p, q in zip(pts[:-1], pts[1:]):
        s = _clip_segment(p, q, b)
        if s is None:
            cour = None
            continue
        a, c = s
        if cour is not None and cour[-1] == a:
            cour.append(c)
        else:
            cour = [a, c]
            morceaux.append(cour)
    out = []
    for m in morceaux:
        u = [m[0]] + [v for k, v in enumerate(m[1:]) if v != m[k]]
        if len(u) >= 2:
            out.append(u)
    return out


def decouper_anneau(pts, b):
    """Sutherland-Hodgman : anneau fermé découpé à la boîte, ou None."""
    x0, y0, x1, y1 = b
    poly = pts[:-1] if pts[0] == pts[-1] else list(pts)
    for dedans, inter in (
            (lambda p: p[0] >= x0, lambda p, q: (x0, p[1] + (q[1] - p[1]) * (x0 - p[0]) / (q[0] - p[0]))),
            (lambda p: p[0] <= x1, lambda p, q: (x1, p[1] + (q[1] - p[1]) * (x1 - p[0]) / (q[0] - p[0]))),
            (lambda p: p[1] >= y0, lambda p, q: (p[0] + (q[0] - p[0]) * (y0 - p[1]) / (q[1] - p[1]), y0)),
            (lambda p: p[1] <= y1, lambda p, q: (p[0] + (q[0] - p[0]) * (y1 - p[1]) / (q[1] - p[1]), y1))):
        if not poly:
            return None
        sortie = []
        for k, q in enumerate(poly):
            p = poly[k - 1]
            if dedans(q):
                if not dedans(p):
                    sortie.append(inter(p, q))
                sortie.append(q)
            elif dedans(p):
                sortie.append(inter(p, q))
        poly = sortie
    u = [p for k, p in enumerate(poly) if k == 0 or p != poly[k - 1]]
    if len(u) < 3:
        return None
    return u + [u[0]]


def _arr(c):
    return [round(c[0], 8), round(c[1], 8)]


def geometrie(e, b):
    """Géométrie GeoJSON découpée à la boîte (règles de pipeline/osm.py:way_geom et site_extract.py), ou None."""
    if e["type"] == "node":
        lon, lat = e["lon"], e["lat"]
        if b[0] <= lon <= b[2] and b[1] <= lat <= b[3]:
            return {"type": "Point", "coordinates": [lon, lat]}
        return None
    pts = [(q["lon"], q["lat"]) for q in (e.get("geometry") or []) if q]
    if len(pts) < 2:
        return None
    t, refs = e.get("tags", {}), e.get("nodes") or []
    closed = bool(refs) and refs[0] == refs[-1] and len(pts) >= 4
    linear_hw = "highway" in t and t.get("area") != "yes"
    if closed and not linear_hw and (t.get("area") == "yes" or any(k in t for k in AREA_KEYS)):
        if all(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in pts):
            return {"type": "Polygon", "coordinates": [[list(p) for p in pts]]}
        r = decouper_anneau(pts, b)
        return {"type": "Polygon", "coordinates": [[_arr(p) for p in r]]} if r else None
    if all(b[0] <= x <= b[2] and b[1] <= y <= b[3] for x, y in pts):
        return {"type": "LineString", "coordinates": [list(p) for p in pts]}
    ms = decouper_ligne(pts, b)
    if not ms:
        return None
    if len(ms) == 1:
        return {"type": "LineString", "coordinates": [_arr(p) for p in ms[0]]}
    return {"type": "MultiLineString", "coordinates": [[_arr(p) for p in m] for m in ms]}


def couches_de(t, typ):
    return [n for n, (pred, kind) in LAYERS.items() if t and kind in (typ, "any") and pred(t)]


def charger_brut(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    el = sorted(d["elements"], key=lambda e: ({"node": 0, "way": 1, "relation": 2}[e["type"]], e["id"]))
    return d.get("osm3s", {}), el


# --------------------------------------------------------------------------- comparaison entre instantanés
def objets_site(el, b):
    """Objets tagués d'au moins une couche, dans l'emprise : {osm_id: dict(couches, loc L93, tags, version, date)}."""
    out = {}
    for e in el:
        if e["type"] == "relation":
            continue
        cs = couches_de(e.get("tags", {}), e["type"])
        if not cs:
            continue
        g = geometrie(e, b)
        if g is None:
            continue
        if e["type"] == "node":
            ll = [(e["lon"], e["lat"])]
        else:
            ll = [(q["lon"], q["lat"]) for q in (e.get("geometry") or []) if q]
        loc = [tuple(v - o for v, o in zip(wgs_l93(*q), O)) for q in ll]
        out[f"{e['type']}/{e['id']}"] = dict(couches=cs, loc=loc, tags=e.get("tags", {}), version=e.get("version"),
                                            date=e.get("timestamp"), changeset=e.get("changeset"))
    return out


def _d_pt_poly(p, poly):
    if len(poly) == 1:
        return math.hypot(p[0] - poly[0][0], p[1] - poly[0][1])
    best = 1e18
    for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
        best = min(best, math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy))
    return best


def ecart(a, b):
    """Hausdorff discret sommet-polyligne (m) entre deux versions."""
    return max(max(_d_pt_poly(p, b) for p in a), max(_d_pt_poly(p, a) for p in b))


def r_min(loc):
    return round(min(math.hypot(x, y) for x, y in loc), 1)


def comparer(A, B, sens):
    """A = instantané de l'état, B = autre instantané ; sens = 'apres' ou 'avant' (B postérieur ou antérieur)."""
    res = dict(seulement_etat=[], seulement_autre=[], deplaces=[], tags_modifies=0, identiques=0)
    for k in sorted(set(A) | set(B)):
        if k in A and k not in B:
            e = A[k]
            res["seulement_etat"].append(dict(osm=k, couches=e["couches"], r_min_m=r_min(e["loc"]),
                                              tags={t: v for t, v in sorted(e["tags"].items()) if t in TAGS_CLES}))
        elif k in B and k not in A:
            e = B[k]
            res["seulement_autre"].append(dict(osm=k, couches=e["couches"], r_min_m=r_min(e["loc"]), date=e["date"],
                                               tags={t: v for t, v in sorted(e["tags"].items()) if t in TAGS_CLES}))
        else:
            ea, eb = A[k], B[k]
            if ea["version"] == eb["version"]:
                res["identiques"] += 1
                continue
            dep = ecart(ea["loc"], eb["loc"])
            if dep > 0.5:
                res["deplaces"].append(dict(osm=k, couches=eb["couches"], r_min_m=r_min(ea["loc"]), ecart_max_m=round(dep, 2),
                                            version_etat=ea["version"], version_autre=eb["version"], date_autre=eb["date"]))
            if ea["tags"] != eb["tags"]:
                res["tags_modifies"] += 1
            elif dep <= 0.5:
                res["identiques"] += 1
    for k in ("seulement_etat", "seulement_autre", "deplaces"):
        res[k].sort(key=lambda r: (r["r_min_m"], r["osm"]))
        res["n_" + k] = len(res[k])
        res["n_" + k + "_coeur80"] = sum(1 for r in res[k] if r["r_min_m"] <= 80)
    lib = {"apres": ("présents à T, absents de l'instantané postérieur (supprimés depuis, ou fusionnés)",
                     "absents à T, présents ensuite (ajoutés à la carte : création réelle ou simple enrichissement)"),
           "avant": ("absents de l'instantané antérieur, présents à T", "présents avant, absents à T")}[sens]
    res["lecture"] = {"seulement_etat": lib[0], "seulement_autre": lib[1]}
    return res


def instantanes():
    """Autres instantanés complets téléchargés : {libellé: (date, fichier)}."""
    out = {}
    for p in sorted(AT.glob("osm_*/overpass_*.json")):
        nom = p.stem.replace("overpass_", "")
        d = p.parent.name[4:] if nom == "actuel" else nom[:10]
        out[nom if nom != "actuel" else f"actuel_{d}"] = (d, p)
    return out


# --------------------------------------------------------------------------- carte de contrôle
def carte(objs, cmp_post, nom_post, chemin, date, demi=90.0):
    from PIL import Image, ImageDraw, ImageFont
    res = 0.2
    n = int(2 * demi / res)
    base = Image.new("RGB", (n, n), (240, 240, 238))
    x0, y1 = O[0] - demi, O[1] + demi
    for jgw in sorted((RACINE / "data/sites/paquet_jardin/ortho5cm_2022").glob("*.jgw")):
        a = [float(v) for v in jgw.read_text().split()]
        X0, Y0 = a[4] - a[0] / 2, a[5] - a[3] / 2
        if X0 > x0 + 2 * demi or X0 + 50 < x0 or Y0 < y1 - 2 * demi or Y0 - 50 > y1:
            continue
        im = Image.open(jgw.with_suffix(".jpg")).convert("L")
        k = res / a[0]
        im = im.resize((round(im.size[0] / k), round(im.size[1] / k)), Image.LANCZOS)
        base.paste(im.convert("RGB"), (round((X0 - x0) / res), round((y1 - Y0) / res)))
    base = Image.blend(base, Image.new("RGB", base.size, (252, 252, 251)), 0.45)
    d = ImageDraw.Draw(base)

    def px(p):
        return ((p[0] + demi) / res, (demi - p[1]) / res)
    styles = {"roads": ((60, 60, 60), 3), "footways": ((120, 120, 120), 1), "cycleways": ((27, 150, 110), 2),
              "crossings": ((42, 120, 214), 0), "traffic_signals": ((200, 30, 30), 0), "road_signs": ((150, 70, 180), 0),
              "public_transport": ((235, 150, 20), 0), "street_lamps": ((120, 100, 0), 0)}
    supp = {r["osm"] for r in cmp_post["seulement_etat"]}
    for c in ("footways", "cycleways", "roads", "street_lamps", "public_transport", "road_signs", "crossings", "traffic_signals"):
        col, w = styles[c]
        for k, e in sorted(objs.items()):
            if c not in e["couches"]:
                continue
            pts = [px(q) for q in e["loc"]]
            if k in supp:
                if len(pts) == 1:
                    u, v = pts[0]
                    d.ellipse([u - 9, v - 9, u + 9, v + 9], outline=(235, 104, 52), width=3)
                else:
                    d.line(pts, fill=(235, 104, 52), width=w + 6)
            if len(pts) == 1:
                u, v = pts[0]
                d.ellipse([u - 4, v - 4, u + 4, v + 4], fill=col)
            else:
                d.line(pts, fill=col, width=w)
    H0 = 110
    img = Image.new("RGB", (n, n + H0 + 56), (252, 252, 251))
    img.paste(base, (0, H0))
    d = ImageDraw.Draw(img)

    def police(t, g=False):
        try:
            return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if g else "C:/Windows/Fonts/arial.ttf", t)
        except OSError:
            return ImageFont.load_default()
    d.text((16, 10), f"OSM de l'état au {date} (Overpass « attic »)", fill=(11, 11, 11), font=police(26, True))
    d.text((16, 46), "voirie (gris), cycles (vert), traversées (bleu), feux (rouge), panneaux (violet), arrêts (orange clair), "
                     "lampadaires (olive)", fill=(82, 81, 78), font=police(15))
    d.text((16, 70), f"cerclé / surligné orange : présent à T, absent de l'instantané {nom_post} "
                     f"({cmp_post['n_seulement_etat']} objets)", fill=(82, 81, 78), font=police(15))
    yb = n + H0 + 12
    L = 25 / res
    d.rectangle([16, yb, 16 + L, yb + 8], fill=(11, 11, 11))
    d.text((24 + L, yb - 6), "25 m", fill=(11, 11, 11), font=police(14))
    d.text((80 + L, yb - 6), "Nord en haut ; fond : ortho PCRS 5 cm du 10/05/2022 (CRAIG / GAM, Licence Ouverte).",
           fill=(82, 81, 78), font=police(13))
    d.text((80 + L, yb + 12), "© contributeurs OpenStreetMap (ODbL).", fill=(82, 81, 78), font=police(13))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    img.save(chemin, optimize=True)


# --------------------------------------------------------------------------- couches de l'état
def couches(a):
    EC = etat()
    E = EC.courant()
    if E is None:
        sys.exit("PJ_ETAT absent : lancer par recon/pcg/etat/lancer.py --etat avant_travaux")
    d = date_osm(E)
    p = brut(d)
    if p is None:
        sys.exit(f"extraction OSM du {d} absente : python -I {rel(__file__)} telecharger --dates {d}")
    sortie = Path(a.sortie) if a.sortie else E.dossier("sources") / f"osm_{d}"
    EC.verifier_ecriture(sortie, E)
    b = emprise_wgs84()
    osm3s, el = charger_brut(p)
    feats = {c: [] for c in LAYERS}
    index = {}
    for e in el:
        if e["type"] == "relation":
            continue
        t = e.get("tags", {})
        cs = couches_de(t, e["type"])
        if not cs:
            continue
        g = geometrie(e, b)
        if g is None:
            continue
        k = f"{e['type']}/{e['id']}"
        for c in cs:
            feats[c].append({"type": "Feature", "id": f"{e['type'][0]}{e['id']}",
                             "properties": {"osm_id": k, **t}, "geometry": g})
        index[k] = [e.get("version"), e.get("timestamp"), e.get("changeset")]
    n = {}
    for c, fs in feats.items():
        ecrire(sortie / f"osm_{c}.geojson", json.dumps({"type": "FeatureCollection", "features": fs}, ensure_ascii=False))
        n[c] = len(fs)
    ecrire_json(sortie / "osm_index.json", {"champs": ["version", "date_version", "changeset"], "objets": index}, indent=0)
    # comparaison aux autres instantanés
    A = objets_site(el, b)
    comps, post = {}, None
    for nom, (dd, fp) in instantanes().items():
        if fp.resolve() == p.resolve():
            continue
        sens = "apres" if dd > d else "avant"
        comps[nom] = dict(date=dd, fichier=rel(fp), sha256=sha256(fp), sens=sens,
                          **comparer(A, objets_site(charger_brut(fp)[1], b), sens))
        if sens == "apres" and nom.startswith("actuel"):
            post = nom
    ecrire_json(sortie / "osm_comparaison.json", {
        "date_osm": d, "etat_cible": E.manifeste(), "objets_etat_dans_emprise": len(A),
        "regle": "objets tagués d'au moins une couche et touchant l'emprise ; déplacement = Hausdorff discret > 0,5 m "
                 "entre versions ; OSM prouve une présence, pas une absence",
        "comparaisons": comps})
    req = p.with_name(f"requete_{d}.json")
    meta_req = json.loads(req.read_text(encoding="utf-8")) if req.exists() else {}
    ecrire_json(sortie / "meta.json", {
        "schema": "pj_osm_etat/0.1", "generateur": rel(__file__), "etat_cible": E.manifeste(), "date_osm": d,
        "sources": [{"nom": "OpenStreetMap, Overpass API mode attic", "serveur": meta_req.get("serveur", SERVEURS[0]),
                     "requete": meta_req.get("requete", requete(d)), "fichier": rel(p), "sha256": sha256(p),
                     "telecharge_le": meta_req.get("telecharge_le"),
                     "timestamp_osm_base": osm3s.get("timestamp_osm_base")}],
        "licence": "ODbL 1.0", "attribution": "© contributeurs OpenStreetMap, ODbL",
        "partage": "partage à l'identique de toute base dérivée diffusée hors du dépôt privé (PLAN § 2.8)",
        "emprise_wgs84": [round(v, 7) for v in b],
        "decoupage": "prédicats de pipeline/osm.py:LAYERS, découpe à l'emprise de pipeline/site_extract.py ; "
                     "même format que data/sites/paquet_jardin/vector/osm_*.geojson (WGS84)",
        "couches": n, "n_elements_bruts": len(el),
        "usage": "topologie, arrêts, feux, traversées à T ; présence seulement (jamais une absence)"})
    if post and not a.sans_carte:
        carte(A, comps[post]["comparaisons"] if "comparaisons" in comps[post] else comps[post], post,
              sortie / "carte_osm.png", d)
    print(rel(sortie), n)
    for k, v in comps.items():
        print(" ", k, {x: v[x] for x in v if x.startswith("n_")})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("telecharger")
    s.add_argument("--dates", nargs="*", help="dates AAAA-MM-JJ (défaut : dates OSM de l'état et de ses variantes)")
    s.set_defaults(f=telecharger)
    s = sp.add_parser("couches")
    s.add_argument("--sortie", help="dossier de sortie (défaut : <état>/sources/osm_<date OSM>)")
    s.add_argument("--sans-carte", action="store_true")
    s.set_defaults(f=couches)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
