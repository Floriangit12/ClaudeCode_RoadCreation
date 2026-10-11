#!/usr/bin/env python
"""État OSM du site à plusieurs dates (Overpass « attic ») et comparaison avec l'état actuel et les couches du dépôt.

Entrées (téléchargées par requête Overpass, traitées comme non fiables, lues avec python -I) :
  data/sites/paquet_jardin/avant_travaux/osm_2022-05-10/overpass_2022-05-10T00Z.json
  data/sites/paquet_jardin/avant_travaux/osm_2025-06-01/overpass_2025-06-01T00Z.json
  data/sites/paquet_jardin/avant_travaux/osm_2025-06-01/overpass_2025-06-22T22Z.json
  data/sites/paquet_jardin/avant_travaux/osm_actuel_2026-10-11/overpass_actuel.json
  requête : [out:json][timeout:300][date:"<date>"];(nwr(45.206347,5.766223,45.208953,5.770177););out meta geom;
  data/sites/paquet_jardin/vector/osm_*.geojson (couches du dépôt, API OSM 0.6, extraites en oct. 2026)
Sorties (dossier de l'inventaire) :
  osm_2025-06-01/osm_<couche>.geojson (WGS84, même découpage en couches que pipeline/osm.py), osm_comparaison.json,
  cartes/osm_2025-06-01_vs_actuel.png

Usage : python -I osm_historique.py <racine_depot>
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

RACINE = Path(sys.argv[1]).resolve()
SORTIE = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources"
AT = RACINE / "data/sites/paquet_jardin/avant_travaux"
O = (917279.43, 6460289.98)
DEMI = 150.0
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
ETATS = {
    "2022-05-10": AT / "osm_2022-05-10/overpass_2022-05-10T00Z.json",
    "2025-06-01": AT / "osm_2025-06-01/overpass_2025-06-01T00Z.json",
    "2025-06-22": AT / "osm_2025-06-01/overpass_2025-06-22T22Z.json",
    "actuel": AT / "osm_actuel_2026-10-11/overpass_actuel.json",
}

# mêmes prédicats que pipeline/osm.py (recopiés, le fichier d'origine n'est pas importé)
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
    "traffic_signals": (lambda t: t.get("highway") == "traffic_signals" or t.get("crossing") == "traffic_signals", "node"),
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
}


def loc(lon, lat):
    X, Y = T.transform(lon, lat)
    return (X - O[0], Y - O[1])


def charger(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    el = {}
    for e in d["elements"]:
        k = f"{e['type']}/{e['id']}"
        if e["type"] == "node":
            g = [(e["lon"], e["lat"])]
        elif e["type"] == "way":
            g = [(q["lon"], q["lat"]) for q in e.get("geometry", []) if q]
        else:
            g = []
        el[k] = dict(type=e["type"], id=e["id"], tags=e.get("tags", {}), version=e.get("version"),
                     timestamp=e.get("timestamp"), user=e.get("user"), changeset=e.get("changeset"), geom=g,
                     loc=[loc(*q) for q in g], nodes=e.get("nodes"))
    return d.get("osm3s", {}).get("timestamp_osm_base"), el


def couches(e):
    out = []
    for n, (pred, kind) in LAYERS.items():
        if e["tags"] and (kind == "any" or kind == e["type"]) and pred(e["tags"]):
            out.append(n)
    return out


def dans_site(e):
    return any(max(abs(x), abs(y)) <= DEMI for x, y in e["loc"])


def r_min(e):
    return min((math.hypot(x, y) for x, y in e["loc"]), default=1e9)


def deplacement(a, b, sens_unique=False):
    """Écart géométrique max (m) entre deux versions : distance de Hausdorff discrète sommet-à-polyligne
    (sens_unique : seulement les sommets de a vers b, pour une géométrie a découpée à l'emprise)."""
    def d_pt_poly(p, poly):
        if len(poly) == 1:
            return math.hypot(p[0] - poly[0][0], p[1] - poly[0][1])
        best = 1e9
        for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
            dx, dy = bx - ax, by - ay
            L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
            best = min(best, math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy))
        return best
    if not a["loc"] or not b["loc"]:
        return None
    dab = max(d_pt_poly(p, b["loc"]) for p in a["loc"])
    if sens_unique:
        return dab
    return max(dab, max(d_pt_poly(p, a["loc"]) for p in b["loc"]))


def comparer(A, B, nomA, nomB):
    """Objets tagués (dans au moins une couche) dans l'emprise : supprimés, ajoutés, déplacés (> 0,5 m), tags modifiés."""
    def sel(E):
        return {k: e for k, e in E.items() if couches(e) and dans_site(e)}
    a, b = sel(A), sel(B)
    res = dict(n_a=len(a), n_b=len(b), supprimes=[], ajoutes=[], deplaces=[], tags_modifies=[], identiques=0)
    for k in sorted(set(a) | set(b)):
        if k in a and k not in b:
            e = a[k]
            res["supprimes"].append(dict(osm=k, couches=couches(e), r_min_m=round(r_min(e), 1), tags=_tags_cles(e["tags"]),
                                         derniere_version_avant=e["timestamp"]))
        elif k in b and k not in a:
            e = b[k]
            res["ajoutes"].append(dict(osm=k, couches=couches(e), r_min_m=round(r_min(e), 1), tags=_tags_cles(e["tags"]),
                                       version=e["version"], date=e["timestamp"], user=e["user"], changeset=e["changeset"]))
        else:
            ea, eb = a[k], b[k]
            if ea["version"] == eb["version"] and ea["loc"] == eb["loc"]:
                res["identiques"] += 1
                continue
            dep = deplacement(ea, eb)
            dt = {t: [ea["tags"].get(t), eb["tags"].get(t)] for t in set(ea["tags"]) | set(eb["tags"]) if ea["tags"].get(t) != eb["tags"].get(t)}
            if dep is not None and dep > 0.5:
                res["deplaces"].append(dict(osm=k, couches=couches(eb), r_min_m=round(min(r_min(ea), r_min(eb)), 1), ecart_max_m=round(dep, 2),
                                            date=eb["timestamp"], user=eb["user"], changeset=eb["changeset"]))
            if dt:
                res["tags_modifies"].append(dict(osm=k, couches=couches(eb), r_min_m=round(min(r_min(ea), r_min(eb)), 1), tags=dt,
                                                 date=eb["timestamp"], changeset=eb["changeset"]))
            if not dt and (dep is None or dep <= 0.5):
                res["identiques"] += 1
    for k in ("supprimes", "ajoutes", "deplaces", "tags_modifies"):
        res[k].sort(key=lambda r: r["r_min_m"])
        res["n_" + k] = len(res[k])
        res["n_" + k + "_coeur80"] = sum(1 for r in res[k] if r["r_min_m"] <= 80)
    res["par_couche"] = {}
    for c in LAYERS:
        res["par_couche"][c] = dict(
            a=sum(1 for e in a.values() if c in couches(e)), b=sum(1 for e in b.values() if c in couches(e)),
            supprimes=sum(1 for r in res["supprimes"] if c in r["couches"]), ajoutes=sum(1 for r in res["ajoutes"] if c in r["couches"]),
            deplaces=sum(1 for r in res["deplaces"] if c in r["couches"]))
    res["libelle"] = f"{nomA} -> {nomB}"
    return res


def _tags_cles(t):
    keep = ("highway", "name", "building", "amenity", "barrier", "crossing", "kerb", "public_transport", "bus", "ref",
            "natural", "landuse", "leisure", "traffic_sign", "cycleway", "footway", "construction", "parking", "service", "oneway")
    return {k: v for k, v in t.items() if k in keep}


def exporter_couches(E, dossier: Path, date):
    dossier.mkdir(parents=True, exist_ok=True)
    feats = defaultdict(list)
    for k, e in E.items():
        cs = couches(e)
        if not cs or not dans_site(e) or not e["geom"]:
            continue
        if e["type"] == "node":
            g = {"type": "Point", "coordinates": list(e["geom"][0])}
        else:
            pts = [list(q) for q in e["geom"]]
            closed = e["nodes"] and e["nodes"][0] == e["nodes"][-1] and len(pts) >= 4
            linear_hw = "highway" in e["tags"] and e["tags"].get("area") != "yes"
            is_area = closed and not linear_hw and (e["tags"].get("area") == "yes" or any(a in e["tags"] for a in AREA_KEYS))
            g = {"type": "Polygon", "coordinates": [pts]} if is_area else {"type": "LineString", "coordinates": pts}
        for c in cs:
            feats[c].append({"type": "Feature", "id": k, "geometry": g,
                             "properties": {"osm_id": k, "osm_version": e["version"], "osm_timestamp": e["timestamp"], **e["tags"]}})
    n = {}
    for c in LAYERS:
        fc = {"type": "FeatureCollection", "name": f"osm_{c}_{date}",
              "source": f"Overpass API attic [date:\"{date}T00:00:00Z\"], © contributeurs OpenStreetMap, ODbL",
              "features": feats.get(c, [])}
        (dossier / f"osm_{c}.geojson").write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        n[c] = len(feats.get(c, []))
    return n


def comparer_depot(E):
    """Couches du dépôt (API 0.6, oct. 2026) contre l'état 2025-06-01 : identifiants communs / propres."""
    res = {}
    for p in sorted((RACINE / "data/sites/paquet_jardin/vector").glob("osm_*.geojson")):
        c = p.stem[4:]
        fs = json.loads(p.read_text(encoding="utf-8"))["features"]
        ids_d = {f["properties"]["osm_id"] for f in fs}
        ids_e = {k for k, e in E.items() if c in couches(e) and dans_site(e)}
        moved = []
        for f in fs:
            k = f["properties"]["osm_id"]
            if k in E and E[k]["loc"]:
                def _plat(c):
                    if isinstance(c[0], (int, float)):
                        return [c]
                    return [q for s in c for q in _plat(s)]
                cs = _plat(f["geometry"]["coordinates"])
                ldep = dict(loc=[loc(q[0], q[1]) for q in cs])
                if E[k]["type"] == "way" and len(E[k]["loc"]) >= 2 and E[k]["nodes"] and E[k]["nodes"][0] == E[k]["nodes"][-1]:
                    pass
                dep = deplacement(ldep, E[k], sens_unique=True)
                if dep is not None and dep > 0.5:
                    moved.append(dict(osm=k, ecart_max_m=round(dep, 2), r_min_m=round(r_min(E[k]), 1)))
        res[c] = dict(depot=len(ids_d), etat_2025_06_01=len(ids_e), communs=len(ids_d & ids_e),
                      seulement_depot=sorted(ids_d - ids_e), seulement_2025=sorted(ids_e - ids_d),
                      communs_deplaces=sorted(moved, key=lambda r: -r["ecart_max_m"]))
    return res


# --------------------------------------------------------------------------- carte
RES = 0.2
BLEU, ORANGE, AQUA = (42, 120, 214), (235, 104, 52), (27, 175, 122)
ENCRE, ENCRE2 = (11, 11, 11), (82, 81, 78)


def police(t, gras=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf", t)
    except OSError:
        return ImageFont.load_default()


def carte(A, B, cmp_, chemin, demi=90.0):
    n = int(2 * demi / RES)
    base = Image.new("RGB", (n, n), (240, 240, 238))
    x0, y1 = O[0] - demi, O[1] + demi
    for jgw in sorted((RACINE / "data/sites/paquet_jardin/ortho5cm_2022").glob("*.jgw")):
        a = [float(v) for v in jgw.read_text().split()]
        X0, Y0 = a[4] - a[0] / 2, a[5] - a[3] / 2
        if X0 > x0 + 2 * demi or X0 + 50 < x0 or Y0 < y1 - 2 * demi or Y0 - 50 > y1:
            continue
        im = Image.open(jgw.with_suffix(".jpg")).convert("L")
        k = RES / a[0]
        im = im.resize((round(im.size[0] / k), round(im.size[1] / k)), Image.LANCZOS)
        base.paste(im.convert("RGB"), (round((X0 - x0) / RES), round((y1 - Y0) / RES)))
    base = Image.blend(base, Image.new("RGB", base.size, (252, 252, 251)), 0.5)
    H0 = 120
    d = ImageDraw.Draw(base)                    # tracé sur le fond seul (découpé à l'emprise), en-tête ajouté ensuite

    def px(p):
        return ((p[0] + demi) / RES, (demi - p[1]) / RES)

    def tracer(e, col, w):
        pts = [px(q) for q in e["loc"]]
        if len(pts) == 1:
            u, v = pts[0]
            d.ellipse([u - 6, v - 6, u + 6, v + 6], fill=(255, 255, 255))
            d.ellipse([u - 4, v - 4, u + 4, v + 4], fill=col)
        else:
            d.line(pts, fill=(255, 255, 255), width=w + 4)
            d.line(pts, fill=col, width=w)
    sup = {r["osm"] for r in cmp_["supprimes"]}
    aj = {r["osm"] for r in cmp_["ajoutes"]}
    dep = {r["osm"] for r in cmp_["deplaces"]}
    for k in sup:
        tracer(A[k], ORANGE, 4)
    for k in dep:
        tracer(A[k], ORANGE, 2)
        tracer(B[k], BLEU, 2)
    for k in aj:
        tracer(B[k], BLEU, 4)
    img = Image.new("RGB", (n, n + H0 + 64), (252, 252, 251))
    img.paste(base, (0, H0))
    d = ImageDraw.Draw(img)
    d.text((16, 12), "OSM : état au 01/06/2025 et état actuel (11/10/2026)", fill=ENCRE, font=police(26, True))
    d.text((16, 48), f"Emprise ± {demi:.0f} m autour du centre ; couches de pipeline/osm.py (voirie, bâti, mobilier).", fill=ENCRE2, font=police(16))
    y = 76
    d.line([(16, y + 9), (46, y + 9)], fill=ORANGE, width=5)
    d.text((54, y), f"au 01/06/2025, supprimé ou modifié depuis ({cmp_['n_supprimes']} supprimés, {cmp_['n_deplaces']} modifiés > 0,5 m)",
           fill=ENCRE, font=police(16))
    d.line([(16, y + 31), (46, y + 31)], fill=BLEU, width=5)
    d.text((54, y + 22), f"actuel : ajouté ou nouvelle géométrie ({cmp_['n_ajoutes']} ajoutés)", fill=ENCRE, font=police(16))
    yb = n + H0 + 14
    L = 25 / RES
    d.rectangle([16, yb, 16 + L, yb + 8], fill=ENCRE)
    d.text((24 + L, yb - 6), "25 m", fill=ENCRE, font=police(15))
    d.text((80 + L, yb - 6), "Nord en haut. Fond : ortho PCRS 5 cm du 10/05/2022 (CRAIG / GAM, Licence Ouverte).", fill=ENCRE2, font=police(14))
    d.text((80 + L, yb + 12), "© contributeurs OpenStreetMap (ODbL), Overpass API (requêtes attic du 11/10/2026).", fill=ENCRE2, font=police(14))
    img.save(chemin, optimize=True)


def main():
    E = {}
    base = {}
    for k, p in ETATS.items():
        base[k], E[k] = charger(p)
    n_couches = exporter_couches(E["2025-06-01"], SORTIE / "osm_2025-06-01", "2025-06-01")
    res = dict(
        genere="outils/osm_historique.py", requete="[out:json][timeout:300][date:\"<date>\"];(nwr(45.206347,5.766223,45.208953,5.770177););out meta geom;",
        serveur="https://overpass-api.de/api/interpreter", timestamp_osm_base=base,
        n_elements={k: len(v) for k, v in E.items()},
        n_par_couche_2025_06_01=n_couches,
        comparaisons={
            "2025-06-01_vs_actuel": comparer(E["2025-06-01"], E["actuel"], "2025-06-01", "actuel (2026-10-11)"),
            "2025-06-01_vs_2025-06-22": comparer(E["2025-06-01"], E["2025-06-22"], "2025-06-01", "2025-06-22"),
            "2022-05-10_vs_2025-06-01": comparer(E["2022-05-10"], E["2025-06-01"], "2022-05-10", "2025-06-01"),
        },
        depot_vs_2025_06_01=comparer_depot(E["2025-06-01"]),
    )
    # éditions de la période avant travaux (dernière version de chaque objet au 2025-06-01)
    ts = Counter((e["timestamp"] or "")[:7] for e in E["2025-06-01"].values() if couches(e) and dans_site(e))
    res["mois_derniere_edition_2025_06_01"] = dict(sorted(ts.items()))
    (SORTIE / "osm_comparaison.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    c = res["comparaisons"]["2025-06-01_vs_actuel"]
    carte(E["2025-06-01"], E["actuel"], c, SORTIE / "cartes/osm_2025-06-01_vs_actuel.png")
    for k, v in res["comparaisons"].items():
        print(k, {kk: v[kk] for kk in v if kk.startswith("n_")})
    print("dépôt vs 2025-06-01 :")
    for k, v in res["depot_vs_2025_06_01"].items():
        print("  ", k, v["depot"], v["etat_2025_06_01"], v["communs"], len(v["seulement_depot"]), len(v["seulement_2025"]), len(v["communs_deplaces"]))


if __name__ == "__main__":
    main()
