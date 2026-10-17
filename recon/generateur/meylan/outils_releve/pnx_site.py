#!/usr/bin/env python
"""Relevé Meylan (lot A) : photos Panoramax d'un site (API STAC publique du méta-catalogue).

Écrit :
  - les MÉTADONNÉES (identifiant, date, position, cap, champ, licence, producteur) des candidats dans
    recon/out/generateur/meylan/<site>/panoramax_candidats.json (non versionné) ;
  - les PHOTOS HD et leurs tuiles natives uniquement sous
    recon/out/generateur/meylan/<site>/photos_non_versionnees/ (jamais versionnées, CC-BY-SA / Etalab) ;
  - le fichier versionné recon/generateur/meylan/<site>/photos.json ne contient que des identifiants, dates,
    positions, caps, licences et constats (commande « retenir »).

Commandes :
  python -I pnx_site.py chercher  SITE LON LAT [--rayon 60] [--depuis 2024-01-01]
  python -I pnx_site.py telecharger SITE ID [ID ...]          (HD + tuiles natives decoupe.py)
  python -I pnx_site.py vise SITE ID LON LAT [--tangage -12] [--nom cible]
                                         (vue sténopé 1092 px dirigée vers un point, photo 360° ou plane)
  python -I pnx_site.py retenir SITE ID [ID ...]               (écrit photos.json, sans photo)
"""
import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon/out/generateur/meylan"
VERS = RACINE / "recon/generateur/meylan"
DECOUPE = RACINE / "recon/pcg/vision/decoupe.py"
API = "https://api.panoramax.xyz/api/search"
UA = {"User-Agent": "ClaudeCode-RoadCreation-releve-meylan/1.0 (etude non commerciale)"}
R_TERRE = 6371008.8


def dist_cap(lon1, lat1, lon2, lat2):
    kx = math.cos(math.radians((lat1 + lat2) / 2)) * math.pi / 180 * R_TERRE
    ky = math.pi / 180 * R_TERRE
    dx, dy = (lon2 - lon1) * kx, (lat2 - lat1) * ky
    return math.hypot(dx, dy), (math.degrees(math.atan2(dx, dy)) + 360) % 360


def bbox(lon, lat, r):
    dlat = r / (math.pi / 180 * R_TERRE)
    dlon = r / (math.cos(math.radians(lat)) * math.pi / 180 * R_TERRE)
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def get(url, **kw):
    for essai in range(5):
        try:
            r = requests.get(url, timeout=120, headers=UA, **kw)
            if r.status_code == 200:
                return r
        except Exception:
            pass
        time.sleep(4 * (essai + 1))
    return None


def chercher(lon, lat, r, depuis):
    b = bbox(lon, lat, r)
    url = API + "?bbox=%.6f,%.6f,%.6f,%.6f&limit=500" % b
    if depuis:
        url += "&datetime=%sT00:00:00Z/.." % depuis
    out = []
    for _ in range(20):
        rep = get(url)
        if rep is None:
            break
        d = rep.json()
        out += d.get("features", [])
        nxt = [l["href"] for l in d.get("links", []) if l.get("rel") == "next"]
        if not nxt:
            break
        url = nxt[0]
        time.sleep(0.3)
    return out


def resume(f, lon, lat):
    p = f.get("properties", {})
    io = p.get("pers:interior_orientation", {}) or {}
    plon, plat = f["geometry"]["coordinates"][:2]
    d, cap_site = dist_cap(plon, plat, lon, lat)
    az = p.get("view:azimuth")
    via = [l for l in f.get("links", []) if l.get("rel") == "via"]
    return {
        "id": f["id"], "collection": f.get("collection"), "lon": round(plon, 7), "lat": round(plat, 7),
        "date": p.get("datetime"), "azimut_deg": az, "fov_deg": io.get("field_of_view"),
        "dim_capteur": io.get("sensor_array_dimensions"),
        "appareil": " ".join(str(x) for x in (io.get("camera_manufacturer"), io.get("camera_model")) if x),
        "licence": p.get("license"), "producteur": p.get("geovisio:producer"),
        "instance": via[0].get("instance_name") if via else None,
        "hd": (f.get("assets", {}).get("hd") or {}).get("href"),
        "lien": "https://api.panoramax.xyz/#focus=pic&pic=%s" % f["id"],
        "distance_site_m": round(d, 1), "cap_vers_site_deg": round(cap_site, 1),
        "statut": p.get("geovisio:status"),
    }


def dossier_photos(site):
    return OUT / site / "photos_non_versionnees"


def charger_candidats(site):
    f = OUT / site / "panoramax_candidats.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"photos": []}


def cmd_chercher(a):
    fs = chercher(a.lon, a.lat, a.rayon, a.depuis)
    ms = [resume(f, a.lon, a.lat) for f in fs]
    ms.sort(key=lambda m: (m["date"] or ""), reverse=True)
    (OUT / a.site).mkdir(parents=True, exist_ok=True)
    doc = {"site": a.site, "centre": [a.lon, a.lat], "rayon_m": a.rayon, "depuis": a.depuis,
           "requete": time.strftime("%Y-%m-%d %H:%M"), "n": len(ms), "photos": ms}
    (OUT / a.site / "panoramax_candidats.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                                           encoding="utf-8")
    jours = {}
    for m in ms:
        jours.setdefault((m["date"] or "")[:10], []).append(m)
    print(a.site, len(ms), "photos")
    for j in sorted(jours, reverse=True)[:12]:
        l = jours[j]
        print(" ", j, len(l), "photos ;", sorted({(m["instance"], m["fov_deg"]) for m in l}, key=str))
    for m in ms[:a.liste]:
        print("   ", m["id"][:8], (m["date"] or "")[:16], m["instance"], "fov", m["fov_deg"], "az", m["azimut_deg"],
              "d", m["distance_site_m"], "cap->site", m["cap_vers_site_deg"])


def trouver(site, ident):
    for m in charger_candidats(site)["photos"]:
        if m["id"].startswith(ident):
            return m
    sys.exit("photo %s absente des candidats de %s : relancer « chercher »" % (ident, site))


def cmd_telecharger(a):
    dp = dossier_photos(a.site)
    dp.mkdir(parents=True, exist_ok=True)
    for ident in a.ids:
        m = trouver(a.site, ident)
        f = dp / (m["id"] + ".jpg")
        if not (f.exists() and f.stat().st_size > 10000):
            r = get(m["hd"])
            if r is None or r.content[:3] != b"\xff\xd8\xff":
                print("échec", m["id"])
                continue
            f.write_bytes(r.content)
        im = Image.open(f)
        w, h = im.size
        sortie = dp / ("tuiles_" + m["id"][:8])
        if (sortie / "tuiles.json").exists():
            print(m["id"][:8], "déjà découpée", w, h)
            continue
        if abs(w - 2 * h) <= 2:
            cmd = [sys.executable, "-I", str(DECOUPE), "equirect", str(f), str(sortie), "--tangages", a.tangages]
        else:
            cmd = [sys.executable, "-I", str(DECOUPE), "image", str(f), str(sortie)]
        subprocess.run(cmd, check=True)
        print(m["id"][:8], w, h, "->", sortie)


def vue_plane(img, fov_h, lacet, tangage, fov_vue, taille=1092):
    """Vue sténopé dirigée (lacet relatif au centre, tangage) dans une photo plane de champ horizontal fov_h."""
    H, W = img.shape[:2]
    fs = (W / 2.0) / math.tan(math.radians(fov_h) / 2.0)
    f = (taille / 2.0) / math.tan(math.radians(fov_vue) / 2.0)
    jj, ii = np.mgrid[0:taille, 0:taille].astype(np.float64)
    x = (ii + 0.5 - taille / 2.0) / f
    y = -(jj + 0.5 - taille / 2.0) / f
    d = np.stack([x, y, np.ones_like(x)], -1)
    t, l = math.radians(tangage), math.radians(lacet)
    Rx = np.array([[1, 0, 0], [0, math.cos(t), math.sin(t)], [0, -math.sin(t), math.cos(t)]])
    Ry = np.array([[math.cos(l), 0, math.sin(l)], [0, 1, 0], [-math.sin(l), 0, math.cos(l)]])
    d = d @ (Ry @ Rx).T
    ok = d[..., 2] > 1e-6
    u = fs * d[..., 0] / np.where(ok, d[..., 2], 1) + W / 2.0 - 0.5
    v = -fs * d[..., 1] / np.where(ok, d[..., 2], 1) + H / 2.0 - 0.5
    ok &= (u >= 0) & (u < W - 1) & (v >= 0) & (v < H - 1)
    u0 = np.clip(np.floor(u).astype(int), 0, W - 2)
    v0 = np.clip(np.floor(v).astype(int), 0, H - 2)
    du, dv = np.clip(u - u0, 0, 1)[..., None], np.clip(v - v0, 0, 1)[..., None]
    src = img.astype(np.float32)
    val = (src[v0, u0] * (1 - du) * (1 - dv) + src[v0, u0 + 1] * du * (1 - dv)
           + src[v0 + 1, u0] * (1 - du) * dv + src[v0 + 1, u0 + 1] * du * dv)
    val[~ok] = 0
    return Image.fromarray(np.clip(val + 0.5, 0, 255).astype(np.uint8))


def cmd_vise(a):
    sys.path.insert(0, str(DECOUPE.parent))
    import decoupe  # noqa
    m = trouver(a.site, a.id)
    f = dossier_photos(a.site) / (m["id"] + ".jpg")
    im = Image.open(f).convert("RGB")
    w, h = im.size
    d, cap = dist_cap(m["lon"], m["lat"], a.lon, a.lat)
    lacet = (cap - (m["azimut_deg"] or 0) + 540) % 360 - 180
    img = np.asarray(im)
    if abs(w - 2 * h) <= 2:
        fov = a.fov or min(90.0, max(40.0, 1092 / (w / 360.0)))
        vue = decoupe.vue_equirect(img, lacet, a.tangage, fov)
    else:
        fov_h = m["fov_deg"] or 70
        fov = a.fov or max(20.0, min(fov_h, 1092 / (w / fov_h)))
        vue = vue_plane(img, fov_h, lacet, a.tangage, fov)
    nom = "vise_%s_%s_t%+03d_f%02d.png" % (m["id"][:8], a.nom, int(a.tangage), int(round(fov)))
    vue.save(dossier_photos(a.site) / nom)
    print(nom, "distance %.1f m, cap %.1f°, lacet %.1f°, fov %.1f°" % (d, cap, lacet, fov))


def cmd_retenir(a):
    ms = [trouver(a.site, i) for i in a.ids]
    dst = VERS / a.site / "photos.json"
    ancien = json.loads(dst.read_text(encoding="utf-8")) if dst.exists() else {}
    deja = {p["id"]: p for p in ancien.get("photos", [])}
    photos = []
    for m in ms:
        p = deja.get(m["id"], {})
        p.update({k: m[k] for k in ("id", "date", "lon", "lat", "azimut_deg", "fov_deg", "licence", "producteur",
                                    "instance", "lien", "distance_site_m")})
        p.setdefault("constats", [])
        photos.append(p)
    photos.sort(key=lambda p: p["date"] or "", reverse=True)
    doc = {"site": a.site, "source": "Panoramax, API STAC publique (https://api.panoramax.xyz/api)",
           "regle": "aucune photo ni tuile versionnée ; seulement identifiants, dates, positions, caps et constats",
           "photos": photos}
    for k in ("etat_decrit", "note"):
        if k in ancien:
            doc[k] = ancien[k]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(dst, len(photos))


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    c = s.add_parser("chercher"); c.add_argument("site"); c.add_argument("lon", type=float); c.add_argument("lat", type=float)
    c.add_argument("--rayon", type=float, default=60); c.add_argument("--depuis", default="2024-01-01")
    c.add_argument("--liste", type=int, default=30)
    t = s.add_parser("telecharger"); t.add_argument("site"); t.add_argument("ids", nargs="+")
    t.add_argument("--tangages", default="-20,0")
    v = s.add_parser("vise"); v.add_argument("site"); v.add_argument("id"); v.add_argument("lon", type=float)
    v.add_argument("lat", type=float); v.add_argument("--tangage", type=float, default=-12)
    v.add_argument("--fov", type=float); v.add_argument("--nom", default="cible")
    r = s.add_parser("retenir"); r.add_argument("site"); r.add_argument("ids", nargs="+")
    a = p.parse_args()
    {"chercher": cmd_chercher, "telecharger": cmd_telecharger, "vise": cmd_vise, "retenir": cmd_retenir}[a.cmd](a)


if __name__ == "__main__":
    main()
