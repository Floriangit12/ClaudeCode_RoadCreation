#!/usr/bin/env python
"""Inventaire des photos de rue (Panoramax + Mapillary) par période et par secteur, carrefour Paquet Jardin.

Entrées (lues, jamais modifiées) :
  - data/sites/paquet_jardin/avant_travaux/panoramax/search_site_tout.json  (STAC api.panoramax.xyz, emprise du site, 2026-10-11)
  - data/raw/mapillary/paquet_jardin/images.json                             (Graph API Mapillary, emprise du site, 2026-10-10)
  - recon/out/paquet_jardin/v2/enrichi/poses/poses.json                      (Panoramax posées)
  - recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/poses/poses_mapillary.json
  - data/sites/paquet_jardin/ortho5cm_2022/*.jpg + .jgw                      (fond de carte PCRS 2022, Licence Ouverte)
Sorties : photos_inventaire.json, cartes/couverture_photos_<periode>.png, cartes/photos_par_mois.png
Aucune image de tiers n'est lue ni écrite : seules les positions, dates et identifiants sont utilisés.

Usage : python -I inventaire_photos.py <racine_depot>
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

RACINE = Path(sys.argv[1]).resolve()
SORTIE = RACINE / "recon/out/paquet_jardin/v2_avant_travaux/inventaire/sources"
O = (917279.43, 6460289.98)
DEMI = 150.0                       # emprise du site : carré ± 150 m
COEUR = 80.0                       # cœur : carré ± 80 m (convention fusion_recensement.py)
R_CENTRE = 35.0                    # centre du carrefour (passages compris)
DEBUT_TRAVAUX = dt.datetime(2025, 6, 23, tzinfo=dt.timezone(dt.timedelta(hours=2)))
# secteurs par azimut depuis O (axes OSM : Verdun NE 44°, Vercors 158°, Verdun SO 222°, Revirée 327°)
SECTEURS = [("reviree", 275, 5), ("verdun_ne", 5, 75), ("est", 75, 140), ("vercors", 140, 190), ("verdun_so", 190, 275)]
NOMS = {"centre": "centre (r ≤ 35 m)", "reviree": "Revirée (NO)", "verdun_ne": "Verdun NE", "est": "secteur est (constructions)",
        "vercors": "Vercors (S)", "verdun_so": "Verdun SO", "autre": "autre (parkings, dessertes)"}
PERIODES = [("2017-2021", "2017-01-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"),
            ("2024", "2024-01-01", "2025-01-01"), ("2025-S1", "2025-01-01", "2025-06-23"),
            ("apres_debut_travaux", "2025-06-23", "2027-01-01")]
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)


AXES_VOIES = {}          # nom de branche -> liste de polylignes (local), rempli par charger_axes()
D_AXE = 15.0             # distance max à l'axe de la voie pour appartenir à une branche


def charger_axes():
    """Axes des branches depuis OSM (data/sites/paquet_jardin/vector/osm_roads.geojson) : Verdun (coupé en NE / SO
    à l'origine), Revirée, Vercors. Les axes n'ont pas bougé avec les travaux (seules les bretelles ont été supprimées)."""
    d = json.loads((RACINE / "data/sites/paquet_jardin/vector/osm_roads.geojson").read_text(encoding="utf-8"))
    noms = {"Avenue de Verdun": "verdun", "Chemin de la Revirée": "reviree", "Avenue du Vercors": "vercors"}
    for f in d["features"]:
        b = noms.get(f["properties"].get("name"))
        if not b:
            continue
        g = f["geometry"]
        lignes = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
        for l in lignes:
            pts = [(X - O[0], Y - O[1]) for X, Y in (T.transform(c[0], c[1]) for c in l)]
            if b == "verdun":
                for nom, sg in (("verdun_ne", 1), ("verdun_so", -1)):
                    # côté NE : x + y > 0 (axe orienté 44° / 224°)
                    seg = [q for q in pts if sg * (q[0] + q[1]) >= -2]
                    if len(seg) >= 2:
                        AXES_VOIES.setdefault(nom, []).append(seg)
            else:
                AXES_VOIES.setdefault(b, []).append(pts)


def _dist(x, y, l):
    best = 1e9
    for (ax, ay), (bx, by) in zip(l[:-1], l[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L2))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def secteur(x, y):
    """centre (r ≤ 35 m) | branche dont l'axe est à ≤ 15 m | est (azimut 60–150°, nouvelles voies du secteur
    construit) | autre (parkings, dessertes, hors axes)."""
    r = math.hypot(x, y)
    if r <= R_CENTRE:
        return "centre"
    best, nom = D_AXE, None
    for b, ls in AXES_VOIES.items():
        for l in ls:
            dd = _dist(x, y, l)
            if dd < best:
                best, nom = dd, b
    if nom:
        if nom in ("verdun_ne", "verdun_so"):
            nom = "verdun_ne" if x + y > 0 else "verdun_so"
        return nom
    az = math.degrees(math.atan2(x, y)) % 360
    return "est" if 60 <= az < 150 else "autre"


def periode(d: str):
    for n, a, b in PERIODES:
        if a <= d < b:
            return n
    return "avant_2017"


def voit_centre(x, y, cap, is360):
    """Heuristique : la photo montre-t-elle le centre du carrefour ?"""
    r = math.hypot(x, y)
    if r <= 25:
        return True
    if is360:
        return r <= 100
    if cap is None or r > 120:
        return False
    rel = (math.degrees(math.atan2(-x, -y)) - cap + 540) % 360 - 180   # azimut vers O moins cap
    return abs(rel) <= 40


def charger():
    photos = []
    pano = json.loads((RACINE / "data/sites/paquet_jardin/avant_travaux/panoramax/search_site_tout.json").read_text(encoding="utf-8"))
    poses_p = json.loads((RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json").read_text(encoding="utf-8"))
    pose_ids = {p["id"]: p for p in poses_p["photos"]}
    for f in pano["features"]:
        lon, lat = f["geometry"]["coordinates"][:2]
        X, Y = T.transform(lon, lat)
        p = f["properties"]
        fov = (p.get("pers:interior_orientation") or {}).get("field_of_view")
        loc = p.get("datetimetz") or p["datetime"]
        photos.append(dict(source="panoramax", id=f["id"], datetime=p["datetime"], date=loc[:10],
                           x=round(X - O[0], 2), y=round(Y - O[1], 2), cap=p.get("view:azimuth"), is360=(fov == 360),
                           collection=f.get("collection"), auteur=p.get("geovisio:producer"), licence=p.get("license"),
                           posee=f["id"] in pose_ids, pose_acceptee=bool(pose_ids.get(f["id"], {}).get("accepte"))))
    mp = json.loads((RACINE / "data/raw/mapillary/paquet_jardin/images.json").read_text(encoding="utf-8"))
    poses_m = json.loads((RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/poses/poses_mapillary.json").read_text(encoding="utf-8"))
    pm = {p["id"]: p for p in poses_m["images"]}
    for im in mp["images"]:
        g = im.get("computed_geometry") or im.get("geometry")
        lon, lat = g["coordinates"][:2]
        X, Y = T.transform(lon, lat)
        t = dt.datetime.fromtimestamp(im["captured_at"] / 1000, tz=dt.timezone.utc)
        loc = t.astimezone(dt.timezone(dt.timedelta(hours=2)))
        cap = im.get("computed_compass_angle", im.get("compass_angle"))
        is360 = im.get("camera_type") in ("spherical", "equirectangular")
        photos.append(dict(source="mapillary", id=im["id"], datetime=t.isoformat(timespec="seconds"), date=loc.date().isoformat(),
                           x=round(X - O[0], 2), y=round(Y - O[1], 2), cap=cap, is360=is360, collection=im.get("sequence"),
                           auteur=(mp["sequences"].get(im.get("sequence"), {}).get("auteur") or [None])[0], licence="CC-BY-SA-4.0",
                           posee=im["id"] in pm, pose_acceptee=pm.get(im["id"], {}).get("statut", "a_priori") != "a_priori"))
    # doublons : même prise de vue publiée sur les deux plateformes (écart ≤ 3 s à un nombre entier d'heures près,
    # fuseau horaire mal renseigné, et ≤ 15 m)
    import bisect
    tp = sorted((dt.datetime.fromisoformat(p["datetime"]).timestamp(), p) for p in photos if p["source"] == "panoramax")
    ts = [t for t, _ in tp]
    for p in photos:
        p["doublon_de"] = None
        if p["source"] != "mapillary":
            continue
        t0 = dt.datetime.fromisoformat(p["datetime"]).timestamp()
        best = None
        for k in (0, -1, 1, -2, 2):
            t = t0 + 3600 * k
            i = bisect.bisect_left(ts, t - 3)
            while i < len(ts) and ts[i] <= t + 3:
                q = tp[i][1]
                dd = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
                if dd <= 15 and (best is None or dd < best[0]):
                    best = (dd, q["id"])
                i += 1
            if best:
                break
        p["doublon_de"] = best[1] if best else None
    for p in photos:
        p["secteur"] = secteur(p["x"], p["y"])
        p["coeur80"] = max(abs(p["x"]), abs(p["y"])) <= COEUR
        p["dans_emprise"] = max(abs(p["x"]), abs(p["y"])) <= DEMI
        p["periode"] = periode(p["date"])
        p["voit_centre"] = voit_centre(p["x"], p["y"], p["cap"], p["is360"])
    return photos, pano, mp


def stats(photos):
    out = {}
    per = defaultdict(lambda: defaultdict(Counter))
    for p in photos:
        if not p["dans_emprise"]:
            continue
        for src in (p["source"], "total"):
            c = per[p["periode"]][src]
            c["n"] += 1
            c["sect:" + p["secteur"]] += 1
            c["coeur80"] += p["coeur80"]
            c["voit_centre"] += p["voit_centre"]
            c["posees"] += p["posee"]
            c["poses_acceptees"] += p["pose_acceptee"]
            c["360"] += p["is360"]
            if src == "total" and not p.get("doublon_de"):
                c["uniques"] += 1
                c["uniques_coeur80"] += p["coeur80"]
                c["uniques_voit_centre"] += p["voit_centre"]
                c["uniques_sect:" + p["secteur"]] += 1
            if src == "mapillary" and p.get("doublon_de"):
                c["doublons_panoramax"] += 1
    for k, v in per.items():
        out[k] = {s: dict(c) for s, c in v.items()}
    mois = defaultdict(Counter)
    jours = defaultdict(Counter)
    for p in photos:
        if p["dans_emprise"]:
            mois[p["date"][:7]][p["source"]] += 1
            jours[p["date"]][p["source"]] += 1
    seq = defaultdict(lambda: dict(n=0))
    for p in photos:
        if not p["dans_emprise"]:
            continue
        k = (p["source"], p["date"], p["collection"])
        s = seq[k]
        s["n"] += 1
        s.setdefault("secteurs", Counter())[p["secteur"]] += 1
        s["auteur"] = p["auteur"]
        s["is360"] = p["is360"]
        s["voit_centre"] = s.get("voit_centre", 0) + p["voit_centre"]
    seqs = [dict(source=k[0], date=k[1], sequence=k[2], auteur=v["auteur"], n=v["n"], is360=v["is360"],
                 voit_centre=v["voit_centre"], secteurs=dict(v["secteurs"])) for k, v in sorted(seq.items(), key=lambda kv: kv[0][1])]
    return out, {k: dict(v) for k, v in sorted(mois.items())}, {k: dict(v) for k, v in sorted(jours.items())}, seqs


# --------------------------------------------------------------------------- cartes
BLEU, ORANGE = (42, 120, 214), (235, 104, 52)
ENCRE, ENCRE2, MUET = (11, 11, 11), (82, 81, 78), (150, 149, 145)
RES = 0.3                                     # m/px
MARGE_HAUT = 150


def police(t, gras=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf" if gras else "C:/Windows/Fonts/arial.ttf", t)
    except OSError:
        return ImageFont.load_default()


def fond():
    n = int(2 * (DEMI + 5) / RES)
    img = Image.new("RGB", (n, n), (240, 240, 238))
    x0, y1 = O[0] - DEMI - 5, O[1] + DEMI + 5
    for jgw in sorted((RACINE / "data/sites/paquet_jardin/ortho5cm_2022").glob("*.jgw")):
        a = [float(v) for v in jgw.read_text().split()]
        jpg = jgw.with_suffix(".jpg")
        im = Image.open(jpg).convert("L")
        w, h = im.size
        X0, Y0 = a[4] - a[0] / 2, a[5] - a[3] / 2         # coin haut-gauche
        k = RES / a[0]
        im = im.resize((max(1, round(w / k)), max(1, round(h / k))), Image.LANCZOS)
        u, v = round((X0 - x0) / RES), round((y1 - Y0) / RES)
        img.paste(im.convert("RGB"), (u, v))
    # éclaircir pour la lisibilité des points
    return Image.blend(img, Image.new("RGB", img.size, (252, 252, 251)), 0.55)


def px(x, y, n):
    return ((x + DEMI + 5) / RES, (DEMI + 5 - y) / RES + MARGE_HAUT)


def carte(base, photos, titre, sous_titre, chemin, compte):
    n = base.size[0]
    im = Image.new("RGB", (n, n + MARGE_HAUT + 66), (252, 252, 251))
    im.paste(base, (0, MARGE_HAUT))
    d = ImageDraw.Draw(im)
    # cœur ± 80 m, centre, rayons de secteurs
    a, b = px(-COEUR, COEUR, n), px(COEUR, -COEUR, n)
    for i in range(0, int(b[0] - a[0]), 14):
        d.line([(a[0] + i, a[1]), (a[0] + i + 7, a[1])], fill=ENCRE2, width=2)
        d.line([(a[0] + i, b[1]), (a[0] + i + 7, b[1])], fill=ENCRE2, width=2)
        d.line([(a[0], a[1] + i), (a[0], a[1] + i + 7)], fill=ENCRE2, width=2)
        d.line([(b[0], a[1] + i), (b[0], a[1] + i + 7)], fill=ENCRE2, width=2)
    c = px(0, 0, n)
    rr = R_CENTRE / RES
    d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], outline=ENCRE2, width=2)
    for b, ls in AXES_VOIES.items():          # axes des branches (zone d'appartenance : ± 15 m)
        for l in ls:
            d.line([px(qx, qy, n) for qx, qy in l], fill=(125, 124, 120), width=2)
    # points : Mapillary d'abord (plus nombreux), Panoramax par-dessus ; plein = posée, creux = non posée
    for src, col, r in (("mapillary", ORANGE, 5), ("panoramax", BLEU, 6)):
        for p in photos:
            if p["source"] != src or not p["dans_emprise"]:
                continue
            u, v = px(p["x"], p["y"], n)
            d.ellipse([u - r - 2, v - r - 2, u + r + 2, v + r + 2], fill=(255, 255, 255))
            if p["posee"]:
                d.ellipse([u - r, v - r, u + r, v + r], fill=col)
            else:
                d.ellipse([u - r, v - r, u + r, v + r], fill=(255, 255, 255), outline=col, width=3)
    # étiquettes de secteurs (après les points, décalées de l'axe des voies)
    f_s = police(17, True)
    AXES = {"reviree": 345, "verdun_ne": 22, "est": 95, "vercors": 182, "verdun_so": 244, "autre": 290}
    for nom, am in AXES.items():
        t = math.radians(am)
        q = px(128 * math.sin(t), 128 * math.cos(t), n)
        lab = NOMS[nom]
        w = d.textlength(lab, font=f_s)
        d.rectangle([q[0] - w / 2 - 4, q[1] - 11, q[0] + w / 2 + 4, q[1] + 11], fill=(252, 252, 251))
        d.text((q[0] - w / 2, q[1] - 10), lab, fill=ENCRE, font=f_s)
    # titre, légende
    d.text((20, 14), titre, fill=ENCRE, font=police(30, True))
    d.text((20, 54), sous_titre, fill=ENCRE2, font=police(18))
    f = police(17)
    y = 84
    for src, col, lab in (("panoramax", BLEU, "Panoramax"), ("mapillary", ORANGE, "Mapillary")):
        d.ellipse([20, y + 2, 34, y + 16], fill=col)
        c_ = compte.get(src, {})
        t = (f"{lab} : {c_.get('n', 0)} photos ; cœur ± 80 m : {c_.get('coeur80', 0)} ; voient le centre : {c_.get('voit_centre', 0)} ; "
             f"posées : {c_.get('posees', 0)}" + (f" ; dont {c_.get('doublons_panoramax', 0)} doublons de Panoramax" if src == "mapillary" and c_.get('doublons_panoramax') else ""))
        d.text((42, y), t, fill=ENCRE, font=f)
        y += 24
    d.ellipse([20, y + 2, 34, y + 16], fill=(255, 255, 255), outline=ENCRE2, width=3)
    d.text((42, y), "creux = non posée ; plein = pose calculée (poses.json, poses_mapillary.json)", fill=ENCRE2, font=police(15))
    # pied : échelle, nord, sources
    yb = n + MARGE_HAUT + 18
    L = 50 / RES
    d.rectangle([20, yb, 20 + L, yb + 8], fill=ENCRE)
    d.text((20 + L + 10, yb - 6), "50 m", fill=ENCRE, font=police(16))
    d.text((120 + L, yb - 8), "Nord en haut. Pointillés : cœur ± 80 m ; cercle : centre r = 35 m ; traits gris : axes des branches (± 15 m).", fill=ENCRE2, font=police(14))
    d.text((120 + L, yb + 10), "Fond : ortho PCRS 5 cm du 10/05/2022 (CRAIG / GAM, Licence Ouverte). Positions : api.panoramax.xyz,", fill=ENCRE2, font=police(14))
    d.text((120 + L, yb + 28), "graph.mapillary.com (computed_geometry). Aucune image de tiers reproduite.", fill=ENCRE2, font=police(14))
    im.save(chemin, optimize=True)


def histogramme(mois, chemin):
    ms = []
    y, m = 2017, 1
    while (y, m) <= (2026, 10):
        ms.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    W, H, g, b = 1600, 620, 70, 90
    im = Image.new("RGB", (W, H), (252, 252, 251))
    d = ImageDraw.Draw(im)
    vmax = 250                                   # axe tronqué : les mois > 250 photos sont écrêtés et annotés
    x0, x1, y0, y1 = g + 20, W - 30, H - b, 110
    bw = (x1 - x0) / len(ms)
    f = police(15)
    for k in range(0, vmax + 1, 50):
        yy = y0 - (y0 - y1) * k / vmax
        d.line([(x0, yy), (x1, yy)], fill=(230, 229, 225), width=1)
        d.text((x0 - 10 - d.textlength(str(k), font=f), yy - 8), str(k), fill=ENCRE2, font=f)
    # bande « travaux »
    def xm(s):
        return x0 + ms.index(s) * bw
    d.rectangle([xm("2025-06") + bw * 0.73, y1, xm("2025-12") + bw * 0.16, y0], fill=(238, 236, 230))
    d.text((xm("2025-06") + 4, y1 + 4), "travaux", fill=ENCRE2, font=police(15, True))
    for i, s in enumerate(ms):
        v = mois.get(s, {})
        yy = y0
        for src, col in (("mapillary", ORANGE), ("panoramax", BLEU)):
            n = v.get(src, 0)
            if not n:
                continue
            h = (y0 - y1) * min(n, vmax - (y0 - yy) / (y0 - y1) * vmax) / vmax
            xa, xb = x0 + i * bw + 1, x0 + (i + 1) * bw - 1
            d.rectangle([xa, yy - h + (1 if yy < y0 else 0), xb, yy - (1 if yy < y0 else 0)], fill=col)
            yy -= h
        tot = sum(v.values())
        if tot > vmax:
            d.polygon([(x0 + i * bw - 2, y1 + 8), (x0 + (i + 1) * bw + 2, y1 + 8), (x0 + (i + 0.5) * bw, y1 - 2)], fill=ORANGE)
        if tot >= 20:
            lab = str(tot) + (" (écrêté)" if tot > vmax else "")
            xt = x0 + (i + 0.5) * bw - d.textlength(lab, font=police(13)) / 2 if tot <= vmax else x0 + (i + 1) * bw + 6
            d.text((xt, max(yy - 18, y1 + 2)), lab, fill=ENCRE, font=police(13))
    d.line([(x0, y0), (x1, y0)], fill=ENCRE2, width=1)
    for yr in range(2017, 2027):
        xx = xm(f"{yr}-01")
        d.line([(xx, y0), (xx, y0 + 6)], fill=ENCRE2, width=1)
        d.text((xx + 4, y0 + 8), str(yr), fill=ENCRE2, font=f)
    d.text((x0, 20), "Photos de rue dans l'emprise du site (± 150 m), par mois", fill=ENCRE, font=police(26, True))
    d.text((x0, 56), "Nombre de photos par mois de prise de vue ; étiquette = total des mois ≥ 20 photos ; axe tronqué à 250 (août 2018 écrêté).", fill=ENCRE2, font=police(17))
    xL = x0
    for src, col, lab in (("panoramax", BLEU, "Panoramax"), ("mapillary", ORANGE, "Mapillary")):
        d.rectangle([xL, 84, xL + 14, 98], fill=col)
        d.text((xL + 20, 82), lab, fill=ENCRE, font=f)
        xL += 140
    d.text((x0, H - 40), "Sources : api.panoramax.xyz (2026-10-11), graph.mapillary.com (2026-10-10). Bande grise : travaux du carrefour (23/06/2025 → 05/12/2025).",
           fill=ENCRE2, font=police(14))
    im.save(chemin, optimize=True)


def main():
    charger_axes()
    photos, pano, mp = charger()
    st, mois, jours, seqs = stats(photos)
    cartes = SORTIE / "cartes"
    cartes.mkdir(parents=True, exist_ok=True)
    base = fond()
    titres = {"2017-2021": "2017 – 2021", "2022": "2022", "2023": "2023", "2024": "2024",
              "2025-S1": "2025, 1er semestre (jusqu'au 22/06/2025)", "apres_debut_travaux": "Après le début des travaux (≥ 23/06/2025)"}
    for nom, a, b in PERIODES:
        ph = [p for p in photos if p["periode"] == nom]
        jours_p = sorted({p["date"] for p in ph if p["dans_emprise"]})
        sous = "Jours de prise de vue : " + (", ".join(jours_p) if len(jours_p) <= 9 else ", ".join(jours_p[:8]) + f" … ({len(jours_p)} jours)")
        carte(base, ph, f"Couverture photo – {titres[nom]}", sous, cartes / f"couverture_photos_{nom}.png", st.get(nom, {}))
    histogramme(mois, cartes / "photos_par_mois.png")
    res = dict(
        genere="outils/inventaire_photos.py", date="2026-10-11",
        conventions=dict(origine_l93=O, emprise="carré ± 150 m", coeur="carré ± 80 m", centre=f"r ≤ {R_CENTRE} m",
                         secteurs=("centre si r ≤ 35 m ; sinon branche dont l'axe OSM (Verdun NE/SO, Revirée, Vercors) est à ≤ 15 m ; "
                                   "sinon « est » si azimut 60–150° (voies nouvelles du secteur construit), sinon « autre »"), voit_centre=("360° à ≤ 100 m, ou perspective à ≤ 120 m "
                         "dont le cap pointe vers O à ± 40°, ou toute photo à ≤ 25 m"), date_photos="date locale (UTC+2)"),
        sources=dict(panoramax=dict(fichier="data/sites/paquet_jardin/avant_travaux/panoramax/search_site_tout.json",
                                    requete="https://api.panoramax.xyz/api/search?bbox=5.766223,45.206347,5.770177,45.208953&limit=10000",
                                    n=len(pano["features"])),
                     mapillary=dict(fichier="data/raw/mapillary/paquet_jardin/images.json", requete=mp["source"], n=mp["n"],
                                    date_requete=mp["date_requete"])),
        par_periode=st, par_mois=mois, par_jour=jours, sequences=seqs,
        photos=[{k: p[k] for k in ("source", "id", "date", "x", "y", "cap", "is360", "secteur", "coeur80", "voit_centre", "periode", "posee", "pose_acceptee", "collection", "doublon_de")}
                for p in photos if p["dans_emprise"]])
    (SORTIE / "photos_inventaire.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for nom, *_ in PERIODES:
        print(nom, json.dumps(st.get(nom, {}).get("total", {}), ensure_ascii=False))
        for s in ("panoramax", "mapillary"):
            print("   ", s, json.dumps(st.get(nom, {}).get(s, {}), ensure_ascii=False))


if __name__ == "__main__":
    main()
