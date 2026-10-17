#!/usr/bin/env python
"""Relevé Meylan (lot A) : ortho IGN 20 cm, altitude et OSM d'un site ; mesures de largeurs par transects.

Repère du site : origine au centre du site (L93, EPSG:2154), x vers l'est, y vers le nord, en mètres.

Commandes :
  python -I ortho_osm_site.py preparer SITE LON LAT [--cote 160]
        ortho WMS Géoplateforme ORTHOIMAGERY.ORTHOPHOTOS (BD ORTHO, prise de vue 2024 en Isère, 20 cm natif,
        Licence Ouverte Etalab 2.0) au pas natif 0,20 m ; tuiles natives par decoupe.py ortho ; altitude du centre
        (API altimétrie Géoplateforme, RGE ALTI) ; OSM (Overpass, ODbL) dans un rayon de cote/2 + 20 m.
        Sorties lourdes : recon/out/generateur/meylan/<site>/ortho/ et osm/ (non versionnées) ;
        résumé versionné : recon/generateur/meylan/<site>/mesures.json → clés « repere », « ortho », « osm ».
  python -I ortho_osm_site.py zoom SITE X Y [--cote 60] [--grille 5] [--echelle 3]
        copie agrandie (plus proche voisin, aucun détail créé) d'une fenêtre de l'ortho avec une grille annotée
        en coordonnées du site, pour lire les positions (fichier séparé, l'ortho brute reste à côté).
  python -I ortho_osm_site.py profil SITE X0 Y0 X1 Y1 [--demi 1.0] [--nom t1]
        transect : luminance moyenne sur une bande de ±demi m autour du segment, pas 0,10 m (bilinéaire) ;
        écrit une bande redressée agrandie et la liste des pics clairs (marquages) et des fronts (bords).
"""
import argparse
import io
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon/out/generateur/meylan"
VERS = RACINE / "recon/generateur/meylan"
DECOUPE = RACINE / "recon/pcg/vision/decoupe.py"
WMS = "https://data.geopf.fr/wms-r"
COUCHE = "ORTHOIMAGERY.ORTHOPHOTOS"
ALTI = "https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = {"User-Agent": "ClaudeCode-RoadCreation-releve-meylan/1.0 (etude non commerciale)"}
PAS = 0.20
T = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
TI = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)


def mesures(site):
    f = VERS / site / "mesures.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"site": site}


def ecrire_mesures(site, doc):
    f = VERS / site / "mesures.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def ortho_info(site):
    j = json.loads((OUT / site / "ortho" / "ortho.json").read_text(encoding="utf-8"))
    im = np.asarray(Image.open(OUT / site / "ortho" / j["fichier"]).convert("RGB"))
    return j, im


def vers_px(j, x, y):
    """coordonnées du site → pixel (colonne, ligne) flottants de l'ortho (centre de pixel en +0,5)."""
    X, Y = j["centre_l93"][0] + x, j["centre_l93"][1] + y
    b = j["bbox_l93"]
    return (X - b[0]) / PAS, (b[3] - Y) / PAS


def cmd_preparer(a):
    xc, yc = T.transform(a.lon, a.lat)
    xc, yc = round(xc, 2), round(yc, 2)
    c = a.cote
    b = (xc - c / 2, yc - c / 2, xc + c / 2, yc + c / 2)
    n = int(round(c / PAS))
    d = OUT / a.site / "ortho"
    d.mkdir(parents=True, exist_ok=True)
    f = d / ("ign2024_%s.png" % a.site)
    if not f.exists():
        p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": COUCHE, "STYLES": "",
             "FORMAT": "image/png", "WIDTH": n, "HEIGHT": n, "CRS": "EPSG:2154",
             "BBOX": ",".join("%.2f" % v for v in b)}
        r = requests.get(WMS, params=p, timeout=300, headers=UA)
        if not r.headers.get("content-type", "").startswith("image"):
            sys.exit("WMS : " + r.text[:300])
        Image.open(io.BytesIO(r.content)).convert("RGB").save(f)
    f.with_suffix(".pgw").write_text("%.6f\n0.0\n0.0\n%.6f\n%.4f\n%.4f\n" % (PAS, -PAS, b[0] + PAS / 2, b[3] - PAS / 2))
    tu = d / "tuiles"
    if not (tu / "tuiles.json").exists():
        subprocess.run([sys.executable, "-I", str(DECOUPE), "ortho", str(tu), "--emprise", *map(str, b),
                        "--repere", "l93", "--source", str(f), "--pas", "0.2", "--prefixe", "ign2024"], check=True)
    j = {"fichier": f.name, "couche": COUCHE, "service": WMS, "crs": "EPSG:2154", "bbox_l93": [round(v, 2) for v in b],
         "centre_l93": [xc, yc], "centre_wgs84": [a.lon, a.lat], "pas_m": PAS, "pas_natif_m": 0.20,
         "prise_de_vue": "BD ORTHO IGN, mosaïque la plus récente (Isère : 2024) ; ORTHO-EXPRESS 2025 et RVB-EXPRESS 2026 vides sur Meylan (contrôle du 17/10/2026)",
         "licence": "Licence Ouverte Etalab 2.0 - IGN"}
    (d / "ortho.json").write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    # altitude du centre
    z = None
    try:
        r = requests.get(ALTI, params={"lon": a.lon, "lat": a.lat, "resource": "ign_rge_alti_wld", "zonly": "true"},
                         timeout=60, headers=UA)
        z = round(float(r.json()["elevations"][0]), 2)
    except Exception as e:
        print("altitude indisponible :", e)
    # OSM : extrait local du dépôt (plan_site.py extraire) ; Overpass seulement avec --overpass (serveurs saturés
    # le 17/10/2026 : « 502, all query workers are busy »)
    osm = osm_site(a.site, a.lon, a.lat, c / 2 + 20) if a.overpass else None
    doc = mesures(a.site) if (VERS / a.site / "mesures.json").exists() else {"site": a.site}
    doc["repere"] = {"origine_l93": [xc, yc, z], "origine_wgs84": [a.lon, a.lat],
                     "axes": "x vers l'est, y vers le nord (m) ; origine = centre du site",
                     "z_source": "API altimétrie Géoplateforme, ressource ign_rge_alti_wld (RGE ALTI), au centre"}
    doc["ortho"] = {"couche": COUCHE, "service": WMS, "prise_de_vue": "2024 (BD ORTHO IGN, Isère)", "pas_m": PAS,
                    "bbox_l93": j["bbox_l93"], "licence": j["licence"],
                    "incertitude": "± 1 pixel natif (0,20 m) par bord, soit ± 0,3 m sur une largeur"}
    if osm is not None:
        doc["osm"] = osm
    elif "erreur" in doc.get("osm", {}):
        doc.pop("osm")
    ecrire_mesures(a.site, doc)
    print(a.site, "ortho", f.name, "z", z)


TAGS_VOIE = ("highway", "name", "ref", "lanes", "lanes:forward", "lanes:backward", "oneway", "maxspeed", "width",
             "width:carriageway", "turn:lanes", "turn:lanes:forward", "turn:lanes:backward", "cycleway",
             "cycleway:left", "cycleway:right", "cycleway:both", "sidewalk", "sidewalk:left", "sidewalk:right",
             "surface", "junction", "bridge", "layer", "segregated", "foot", "bicycle", "bus", "psv",
             "parking:lane:both", "parking:both", "parking:left", "parking:right", "lit", "dual_carriageway",
             "placement", "lane_markings", "crossing", "footway", "smoothness", "maxspeed:type", "network", "cycle_network")
TAGS_NOEUD = ("highway", "crossing", "crossing:island", "crossing:markings", "traffic_signals", "traffic_signals:direction",
              "direction", "traffic_sign", "traffic_calming", "kerb", "tactile_paving", "button_operated", "natural",
              "name", "barrier", "junction", "ref", "highway:stop")


def overpass(q):
    for url in OVERPASS:
        for essai in range(3):
            try:
                r = requests.post(url, data={"data": q}, timeout=180, headers=UA)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
            time.sleep(10 * (essai + 1))
    return None


def osm_site(site, lon, lat, r):
    A = "(around:%d,%.6f,%.6f)" % (r, lat, lon)
    q = """[out:json][timeout:120];
(way{A}[highway];
 way{A}[area:highway];
 way{A}[traffic_calming];
 node{A}[highway];
 node{A}[crossing];
 node{A}[traffic_calming];
 node{A}[natural=tree];
 way{A}[natural=tree_row];
 relation{A}[route=bicycle];
);
out body; >; out skel qt;""".replace("{A}", A)
    d = overpass(q)
    od = OUT / site / "osm"
    od.mkdir(parents=True, exist_ok=True)
    if d is None:
        return {"erreur": "Overpass indisponible"}
    (od / "overpass.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    pos = {e["id"]: (e["lon"], e["lat"]) for e in d["elements"] if e["type"] == "node" and "lon" in e}
    xc, yc = T.transform(lon, lat)
    voies, noeuds, rels = [], [], []
    for e in d["elements"]:
        t = e.get("tags", {})
        if e["type"] == "way" and t:
            pts = []
            for nid in e.get("nodes", []):
                if nid in pos:
                    X, Y = T.transform(*pos[nid])
                    pts.append([round(X - xc, 2), round(Y - yc, 2)])
            voies.append({"id": e["id"], "tags": {k: v for k, v in t.items() if k in TAGS_VOIE or k.startswith("area:")
                                                   or k.startswith("traffic_calming") or k == "natural"},
                          "local": pts})
        elif e["type"] == "node" and t:
            X, Y = T.transform(e["lon"], e["lat"])
            tt = {k: v for k, v in t.items() if k in TAGS_NOEUD}
            if tt:
                noeuds.append({"id": e["id"], "tags": tt, "local": [round(X - xc, 2), round(Y - yc, 2)]})
        elif e["type"] == "relation" and t:
            rels.append({"id": e["id"], "name": t.get("name"), "network": t.get("network"), "ref": t.get("ref")})
    return {"source": "OpenStreetMap (Overpass API), ODbL © contributeurs OpenStreetMap",
            "requete": time.strftime("%Y-%m-%d"), "rayon_m": round(r), "voies": voies, "noeuds": noeuds,
            "relations_velo": rels}


def police(t):
    for nom in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except Exception:
            pass
    return ImageFont.load_default()


def cmd_zoom(a):
    j, im = ortho_info(a.site)
    c, e = a.cote, a.echelle
    i0, j0 = vers_px(j, a.x - c / 2, a.y + c / 2)
    i0, j0 = int(round(i0)), int(round(j0))
    npx = int(round(c / PAS))
    H, W = im.shape[:2]
    fen = np.zeros((npx, npx, 3), np.uint8)
    si0, sj0 = max(0, i0), max(0, j0)
    si1, sj1 = min(W, i0 + npx), min(H, j0 + npx)
    fen[sj0 - j0:sj1 - j0, si0 - i0:si1 - i0] = im[sj0:sj1, si0:si1]
    big = Image.fromarray(fen).resize((npx * e, npx * e), Image.NEAREST)
    dr = ImageDraw.Draw(big)
    fo = police(14)
    x0, y1 = a.x - c / 2, a.y + c / 2
    g = a.grille
    k = math.ceil(x0 / g)
    while k * g <= x0 + c:
        px = (k * g - x0) / PAS * e
        dr.line([(px, 0), (px, npx * e)], fill=(255, 0, 255) if k % 2 == 0 else (0, 255, 255), width=1)
        dr.text((px + 2, 2), "x%+d" % (k * g), fill=(255, 255, 0), font=fo)
        k += 1
    k = math.ceil((y1 - c) / g)
    while k * g <= y1:
        py = (y1 - k * g) / PAS * e
        dr.line([(0, py), (npx * e, py)], fill=(255, 0, 255) if k % 2 == 0 else (0, 255, 255), width=1)
        dr.text((2, py + 2), "y%+d" % (k * g), fill=(255, 255, 0), font=fo)
        k += 1
    d = OUT / a.site / "ortho" / "zooms"
    d.mkdir(parents=True, exist_ok=True)
    nom = "zoom_%s_x%+04d_y%+04d_c%d.png" % (a.site, round(a.x), round(a.y), round(c))
    big.save(d / nom)
    print(d / nom, big.size)


def echantillon(im, u, v):
    H, W = im.shape[:2]
    u0 = np.clip(np.floor(u).astype(int), 0, W - 2)
    v0 = np.clip(np.floor(v).astype(int), 0, H - 2)
    du, dv = np.clip(u - u0, 0, 1)[..., None], np.clip(v - v0, 0, 1)[..., None]
    f = im.astype(np.float64)
    return (f[v0, u0] * (1 - du) * (1 - dv) + f[v0, u0 + 1] * du * (1 - dv)
            + f[v0 + 1, u0] * (1 - du) * dv + f[v0 + 1, u0 + 1] * du * dv)


def cmd_profil(a):
    j, im = ortho_info(a.site)
    L = math.hypot(a.x1 - a.x0, a.y1 - a.y0)
    ux, uy = (a.x1 - a.x0) / L, (a.y1 - a.y0) / L
    nx, ny = -uy, ux
    s = np.arange(0, L + 1e-9, 0.10)
    t = np.arange(-a.demi, a.demi + 1e-9, 0.10)
    S, Tt = np.meshgrid(s, t)
    X = a.x0 + S * ux + Tt * nx
    Y = a.y0 + S * uy + Tt * ny
    u, v = vers_px(j, X, Y)
    rgb = echantillon(im, u - 0.5, v - 0.5)
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2])
    prof = np.median(lum, axis=0)
    # bande redressée agrandie (lecture)
    bande = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((len(s) * 4, len(t) * 4), Image.NEAREST)
    big = Image.new("RGB", (bande.width, bande.height + 140), (255, 255, 255))
    big.paste(bande, (0, 0))
    dr = ImageDraw.Draw(big)
    fo = police(12)
    y0 = bande.height + 130
    pts = [(i * 4, y0 - prof[i] / 255 * 110) for i in range(len(s))]
    dr.line(pts, fill=(0, 0, 0), width=1)
    for m in range(0, int(L) + 1):
        px = m / 0.10 * 4
        dr.line([(px, bande.height), (px, bande.height + 8 + (6 if m % 5 == 0 else 0))], fill=(200, 0, 0))
        if m % 5 == 0:
            dr.text((px + 2, bande.height + 14), "%d" % m, fill=(200, 0, 0), font=fo)
    d = OUT / a.site / "ortho" / "profils"
    d.mkdir(parents=True, exist_ok=True)
    nom = "profil_%s_%s.png" % (a.site, a.nom)
    big.save(d / nom)
    # pics clairs (marquages) et fronts
    lis = np.convolve(prof, np.ones(3) / 3, mode="same")
    fond = np.array([np.median(lis[max(0, i - 15):i + 16]) for i in range(len(lis))])
    pics = [i for i in range(1, len(lis) - 1) if lis[i] >= lis[i - 1] and lis[i] >= lis[i + 1] and lis[i] - fond[i] > a.seuil]
    grad = np.gradient(lis)
    fronts = [i for i in range(1, len(grad) - 1) if abs(grad[i]) >= abs(grad[i - 1]) and abs(grad[i]) >= abs(grad[i + 1])
              and abs(grad[i]) > a.seuil / 2]
    res = {"segment": [a.x0, a.y0, a.x1, a.y1], "longueur_m": round(L, 2), "demi_largeur_m": a.demi,
           "pics_clairs_s_m": [round(float(s[i]), 1) for i in pics],
           "fronts_s_m": [[round(float(s[i]), 1), "+" if grad[i] > 0 else "-", round(float(grad[i]), 1)] for i in fronts],
           "luminance_pas_1m": [round(float(np.mean(prof[k:k + 10])), 0) for k in range(0, len(prof), 10)]}
    (d / (nom[:-4] + ".json")).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(d / nom, big.size)
    print("pics clairs (s, m) :", res["pics_clairs_s_m"])
    print("fronts (s, sens, gradient) :", res["fronts_s_m"])


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    c = s.add_parser("preparer"); c.add_argument("site"); c.add_argument("lon", type=float); c.add_argument("lat", type=float)
    c.add_argument("--cote", type=float, default=160); c.add_argument("--overpass", action="store_true")
    z = s.add_parser("zoom"); z.add_argument("site"); z.add_argument("x", type=float); z.add_argument("y", type=float)
    z.add_argument("--cote", type=float, default=60); z.add_argument("--grille", type=float, default=5)
    z.add_argument("--echelle", type=int, default=3)
    r = s.add_parser("profil"); r.add_argument("site")
    for k in ("x0", "y0", "x1", "y1"):
        r.add_argument(k, type=float)
    r.add_argument("--demi", type=float, default=1.0); r.add_argument("--nom", default="t1")
    r.add_argument("--seuil", type=float, default=25)
    o = s.add_parser("osm"); o.add_argument("site"); o.add_argument("--rayon", type=float, default=100)
    a = p.parse_args()
    {"preparer": cmd_preparer, "zoom": cmd_zoom, "profil": cmd_profil, "osm": cmd_osm}[a.cmd](a)


def cmd_osm(a):
    """Relance seulement la requête OSM (Overpass) d'un site déjà préparé."""
    doc = mesures(a.site)
    lon, lat = doc["repere"]["origine_wgs84"]
    doc["osm"] = osm_site(a.site, lon, lat, a.rayon)
    ecrire_mesures(a.site, doc)
    print(a.site, "osm", len(doc["osm"].get("voies", [])), "voies", len(doc["osm"].get("noeuds", [])), "noeuds",
          doc["osm"].get("erreur", ""))


if __name__ == "__main__":
    main()
