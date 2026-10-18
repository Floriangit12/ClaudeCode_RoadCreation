"""Accès à l'API Graph de Mapillary (v4) pour la comparaison v2 : recherche par emprise (métadonnées en cache) et
téléchargement des images (cache sous photos_non_versionnees/), au même format résumé que api_panoramax._resume.

Jeton : lu SEULEMENT dans %USERPROFILE%\\.config\\meylan_adas\\mapillary_token.txt ; il passe par l'en-tête
« Authorization: OAuth … », n'est jamais affiché, ni écrit, ni mis dans une URL. Les URL des images (signées et
périssables, sans jeton) ne sont pas mises en cache : elles sont redemandées par identifiant au téléchargement.
Images Mapillary : CC-BY-SA 4.0 (auteur = compte du contributeur). Sans jeton, la recherche renvoie une liste vide.

Format résumé (comme Panoramax) : id, collection (séquence), lon, lat (computed_geometry, sinon geometry),
proprietes (datetime UTC ISO, view:azimuth = computed_compass_angle, pers:interior_orientation.field_of_view = 360
pour les sphériques, sinon champ horizontal du modèle perspective, license, geovisio:producer), assets vides,
source = « mapillary », mly (camera_type, camera_parameters, width, height, quality_score, is_pano).
"""
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://graph.mapillary.com"
UA = "ClaudeCode_RoadCreation/1.0 (comparaison multivues, voirie Meylan)"
LICENCE = "CC-BY-SA-4.0"
CHAMPS = ("id,captured_at,camera_type,camera_parameters,computed_geometry,geometry,computed_compass_angle,"
          "compass_angle,sequence,creator,width,height,quality_score,is_pano")


def fichier_jeton():
    return Path(os.environ.get("USERPROFILE", "")) / ".config" / "meylan_adas" / "mapillary_token.txt"


def jeton():
    f = fichier_jeton()
    if not f.exists():
        return None
    t = f.read_text(encoding="utf-8").strip()
    return t or None


def _get(url, tok, binaire=False, essais=5, timeout=90):
    h = {"User-Agent": UA}
    if tok:
        h["Authorization"] = "OAuth " + tok
    attente = 2.0
    for k in range(essais):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                data = r.read()
            return data if binaire else json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and k < essais - 1:
                time.sleep(attente)
                attente *= 2
                continue
            raise RuntimeError(f"Mapillary : HTTP {e.code} sur {url.split('?')[0]}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if k < essais - 1:
                time.sleep(attente)
                attente *= 2
                continue
            raise RuntimeError(f"Mapillary : réseau indisponible ({url.split('?')[0]})") from None


def champ_perspective(cp, w, h):
    """Champ horizontal (°) du modèle perspective/fisheye d'OpenSfM : f normalisée par max(W, H)."""
    try:
        f = float(cp[0])
    except (TypeError, IndexError, ValueError):
        return None
    if f <= 0 or not w or not h:
        return None
    return math.degrees(2.0 * math.atan(w / (2.0 * f * max(w, h))))


def _resume(im):
    g = im.get("computed_geometry") or im.get("geometry")
    lon, lat = g["coordinates"][:2]
    d = datetime.fromtimestamp(im["captured_at"] / 1000.0, tz=timezone.utc)
    ct = im.get("camera_type") or "perspective"
    sph = ct in ("spherical", "equirectangular")
    w, h = im.get("width"), im.get("height")
    fov = 360 if sph else champ_perspective(im.get("camera_parameters"), w, h)
    az = im.get("computed_compass_angle", im.get("compass_angle"))
    cr = im.get("creator") or {}
    props = {"datetime": d.isoformat().replace("+00:00", "Z"), "view:azimuth": az, "license": LICENCE,
             "geovisio:producer": cr.get("username"), "geovisio:status": "ready",
             "pers:interior_orientation": {"field_of_view": round(fov, 3) if fov else None,
                                           "sensor_array_dimensions": [w, h]}}
    return {"id": str(im["id"]), "collection": "mly-" + str(im.get("sequence") or "?"), "lon": float(lon),
            "lat": float(lat), "proprietes": props, "assets": {}, "voisins": {}, "instance": "mapillary",
            "source": "mapillary",
            "mly": {"camera_type": ct, "camera_parameters": im.get("camera_parameters"), "width": w, "height": h,
                    "quality_score": im.get("quality_score"), "is_pano": im.get("is_pano"),
                    "geometrie": "computed_geometry" if im.get("computed_geometry") else "geometry",
                    "lien": f"https://www.mapillary.com/app/?pKey={im['id']}"}}


def rechercher(bbox, cache, rafraichir=False, n=2):
    """Images dans bbox (lon0, lat0, lon1, lat1), dallée n × n (la recherche plafonne à 2 000 réponses). Cache :
    métadonnées résumées seulement. Renvoie (photos, doc) ; ([], doc) sans jeton."""
    cache = Path(cache)
    cle = hashlib.sha256(json.dumps([round(v, 6) for v in bbox]).encode()).hexdigest()[:12]
    if cache.exists() and not rafraichir:
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("cle") == cle:
            return d["photos"], d
    tok = jeton()
    if tok is None:
        return [], {"cle": cle, "n": 0, "date_requete": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "note": "jeton Mapillary absent : aucune recherche"}
    lo0, la0, lo1, la1 = bbox
    vus = {}
    satures = 0
    for i in range(n):
        for j in range(n):
            b = (lo0 + (lo1 - lo0) * i / n, la0 + (la1 - la0) * j / n,
                 lo0 + (lo1 - lo0) * (i + 1) / n, la0 + (la1 - la0) * (j + 1) / n)
            url = f"{API}/images?" + urllib.parse.urlencode({"bbox": ",".join(f"{x:.6f}" for x in b), "fields": CHAMPS,
                                                             "limit": 2000})
            lot = _get(url, tok).get("data", [])
            satures += len(lot) >= 2000
            for im in lot:
                if im.get("captured_at") and (im.get("computed_geometry") or im.get("geometry")):
                    vus[str(im["id"])] = _resume(im)
    photos = sorted(vus.values(), key=lambda r: (r["proprietes"]["datetime"], r["id"]))
    doc = {"schema": "comparaison_recherche_mapillary/0.1", "cle": cle, "bbox": list(bbox), "api": API + "/images",
           "date_requete": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": len(photos), "dalles_saturees": satures,
           "licence": "CC-BY-SA 4.0 (auteur par image)", "photos": photos}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(doc, ensure_ascii=False, indent=0), encoding="utf-8")
    return photos, doc


def telecharger(photo, qualite, dossier):
    """Image d'une photo Mapillary (hd : originale, sinon 2 048 px ; sd : 2 048 px) en cache sous dossier
    (photos_non_versionnees/...). L'URL signée est demandée au moment du téléchargement (jamais enregistrée)."""
    dossier = Path(dossier)
    if "photos_non_versionnees" not in dossier.as_posix():
        raise RuntimeError("refus : image de tiers hors d'un dossier photos_non_versionnees/")
    nom = "%s_%s_%s.jpg" % (photo["proprietes"]["datetime"][:10], id8(photo["id"]), qualite)
    f = dossier / nom
    if f.exists() and f.stat().st_size > 0:
        return f
    tok = jeton()
    if tok is None:
        raise RuntimeError("jeton Mapillary absent : téléchargement impossible")
    # sd = 2 048 px, comme l'image SD de Panoramax (la netteté se compare à résolution égale)
    champs = ("thumb_original_url", "thumb_2048_url") if qualite == "hd" else ("thumb_2048_url", "thumb_1024_url")
    d = _get(f"{API}/{photo['id']}?" + urllib.parse.urlencode({"fields": ",".join(champs)}), tok)
    url = next((d.get(c) for c in champs if d.get(c)), None)
    if not url:
        raise RuntimeError(f"photo Mapillary {photo['id']} : pas d'image {qualite}")
    dossier.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".part")
    tmp.write_bytes(_get(url, None, binaire=True, timeout=600))
    tmp.replace(f)
    return f


def id8(i):
    """Identifiant court d'une image Mapillary (les identifiants numériques se ressemblent au début) : « m » + les
    9 derniers chiffres."""
    return "m" + str(i)[-9:]
