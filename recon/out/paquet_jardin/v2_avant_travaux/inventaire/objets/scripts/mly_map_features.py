"""Mapillary « map features » (points + panneaux) du site Paquet Jardin, avec dates de détection.

Usage : python -I mly_map_features.py <dossier_sortie>

- Jeton lu UNIQUEMENT dans %USERPROFILE%/.config/meylan_adas/mapillary_token.txt, transmis par l'en-tête
  « Authorization: OAuth ... » ; jamais affiché, jamais écrit ; toute URL enregistrée est purgée.
- Sorties (données publiques Mapillary, CC-BY-SA 4.0) :
    map_features.json        : un enregistrement par objet (id, object_value, object_type, geometry WGS84,
                               first_seen_at, last_seen_at, aligned_direction, images [id])
    detections/<id>.json     : détections par image (image id, created_at, value) pour les objets du site
    images_detection.json    : métadonnées des images portant une détection (captured_at, geometry, compass)
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.mapillary.com"
# emprise du site (±150 m autour de O) élargie de 10 m
BBOX = (5.76600, 45.20620, 5.77035, 45.20910)


def _jeton():
    f = Path(os.environ["USERPROFILE"]) / ".config" / "meylan_adas" / "mapillary_token.txt"
    return f.read_text(encoding="utf-8").strip()


def _get(url, tok, essais=5):
    h = {"User-Agent": "paquet-jardin-recon/0.1", "Authorization": "OAuth " + tok}
    att = 2.0
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and k < essais - 1:
                time.sleep(att)
                att *= 2
                continue
            corps = ""
            try:
                corps = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            corps = corps.replace(tok, "<jeton>")
            raise RuntimeError(f"HTTP {e.code} sur {url.split('?')[0]} : {corps}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if k < essais - 1:
                time.sleep(att)
                att *= 2
                continue
            raise RuntimeError(f"réseau : {url.split('?')[0]}") from None


def _purger(v):
    if isinstance(v, dict):
        return {k: _purger(x) for k, x in v.items() if k.lower() != "access_token"}
    if isinstance(v, list):
        return [_purger(x) for x in v]
    if isinstance(v, str) and "access_token" in v:
        p = urllib.parse.urlsplit(v)
        q = [(a, b) for a, b in urllib.parse.parse_qsl(p.query) if a.lower() != "access_token"]
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment))
    return v


def main(sortie):
    sortie = Path(sortie)
    (sortie / "detections").mkdir(parents=True, exist_ok=True)
    tok = _jeton()
    champs = "id,object_value,object_type,geometry,first_seen_at,last_seen_at,aligned_direction,images"
    tous = {}
    # découpage en 4x3 tuiles (le endpoint plafonne le nombre de résultats par requête)
    nx, ny = 4, 3
    x0, y0, x1, y1 = BBOX
    for i in range(nx):
        for j in range(ny):
            b = (x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, x0 + (x1 - x0) * (i + 1) / nx, y0 + (y1 - y0) * (j + 1) / ny)
            for typ in ("point", "trafficsign"):
                url = f"{API}/map_features?" + urllib.parse.urlencode(
                    {"fields": champs, "bbox": ",".join(f"{v:.6f}" for v in b), "object_types": typ, "limit": 2000})
                d = _get(url, tok)
                n = 0
                while True:
                    for f in d.get("data", []):
                        tous[f["id"]] = f
                        n += 1
                    nxt = (d.get("paging") or {}).get("next")
                    if not nxt:
                        break
                    d = _get(nxt, tok)
                print(f"tuile {i},{j} {typ}: {n}")
    feats = list(tous.values())
    print("objets :", len(feats))
    # détections par objet (image, date de création de la détection, valeur)
    imgs = set()
    for k, f in enumerate(feats):
        fid = f["id"]
        url = f"{API}/{fid}/detections?" + urllib.parse.urlencode({"fields": "id,image,created_at,value,geometry"})
        try:
            d = _get(url, tok)
            det = d.get("data", [])
        except RuntimeError as e:
            det = {"erreur": str(e)}
        (sortie / "detections" / f"{fid}.json").write_text(json.dumps(_purger(det), ensure_ascii=False), encoding="utf-8")
        if isinstance(det, list):
            for x in det:
                im = x.get("image")
                if isinstance(im, dict):
                    imgs.add(im.get("id"))
        for im in (f.get("images") or {}).get("data", []):
            imgs.add(im.get("id"))
        if k % 50 == 0:
            print("détections", k, "/", len(feats))
    imgs.discard(None)
    # métadonnées des images (par lots de 50)
    meta = {}
    L = sorted(imgs)
    for a in range(0, len(L), 50):
        lot = L[a:a + 50]
        url = f"{API}/images?" + urllib.parse.urlencode(
            {"image_ids": ",".join(lot),
             "fields": "id,captured_at,geometry,computed_geometry,compass_angle,computed_compass_angle,camera_type,sequence,creator,width,height"})
        try:
            d = _get(url, tok)
            for im in d.get("data", []):
                meta[im["id"]] = im
        except RuntimeError as e:
            print("images lot", a, ":", e)
    out = {
        "schema": "pj_mly_map_features/0.1",
        "source": f"{API}/map_features (object_types point, trafficsign ; bbox {','.join(map(str, BBOX))})",
        "date_requete": time.strftime("%Y-%m-%d"),
        "licence": "CC-BY-SA 4.0 (Mapillary)",
        "remarque": "aucun jeton enregistré ; first_seen_at / last_seen_at = dates de capture des images détectantes",
        "n": len(feats),
        "features": _purger(feats),
    }
    (sortie / "map_features.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    (sortie / "images_detection.json").write_text(json.dumps(_purger(meta), ensure_ascii=False, indent=1), encoding="utf-8")
    print("images détectantes :", len(meta))


if __name__ == "__main__":
    main(sys.argv[1])
