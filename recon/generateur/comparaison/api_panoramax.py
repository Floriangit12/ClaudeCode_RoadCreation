"""Accès à l'API publique Panoramax (STAC, https://api.panoramax.xyz/api) : recherche par emprise et par
identifiants, avec cache disque des réponses (métadonnées seulement), et téléchargement des images avec cache.

Le cache rend la suite déterministe hors appel réseau : une recherche déjà faite n'est rejouée qu'avec --rafraichir.
Les images (CC-BY-SA, etalab…) ne sont écrites que sous un dossier photos_non_versionnees/ (contrôlé ici).
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.panoramax.xyz/api"
UA = "ClaudeCode_RoadCreation/1.0 (comparaison multivues, voirie Meylan)"

GARDER_PROPS = ("datetime", "datetimetz", "view:azimuth", "pers:interior_orientation", "pers:pitch", "pers:roll",
                "pers:yaw", "quality:horizontal_accuracy", "license", "geovisio:producer", "collection",
                "geovisio:status", "geovisio:visibility", "panoramax:horizontal_pixel_density",
                "geovisio:rank_in_collection")
GARDER_EXIF = ("Exif.Image.Make", "Exif.Image.Model", "Xmp.GPano.ProjectionType", "Exif.Photo.FocalLength",
               "Exif.Photo.FocalLengthIn35mmFilm", "Exif.Photo.PixelXDimension", "Exif.Photo.PixelYDimension")


def _get(url, timeout=120):
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception:  # réseau : nouvel essai
            if essai == 3:
                raise
            time.sleep(3 * (essai + 1))


def _resume(f):
    """Garde d'une Feature STAC ce qui sert à la sélection et aux fichiers versionnés (aucune image)."""
    p = f.get("properties", {})
    props = {k: p[k] for k in GARDER_PROPS if k in p}
    exif = p.get("exif") or {}
    props["exif"] = {k: exif[k] for k in GARDER_EXIF if k in exif}
    assets = {k: (v or {}).get("href") for k, v in (f.get("assets") or {}).items() if k in ("hd", "sd", "thumb")}
    voisins = {}
    for ln in f.get("links", []):
        if ln.get("rel") in ("prev", "next") and ln.get("id"):
            voisins[ln["rel"]] = {"id": ln["id"], "coordonnees": (ln.get("geometry") or {}).get("coordinates")}
    instance = next((ln.get("instance_name") for ln in f.get("links", []) if ln.get("rel") == "via"), None)
    return {"id": f["id"], "collection": f.get("collection"), "lon": f["geometry"]["coordinates"][0],
            "lat": f["geometry"]["coordinates"][1], "proprietes": props, "assets": assets, "voisins": voisins,
            "instance": instance}


def rechercher(bbox, cache, rafraichir=False, limite=1000, pages_max=10):
    """Photos dans bbox (lon0, lat0, lon1, lat1). Cache : fichier JSON (requête + réponses résumées)."""
    cache = Path(cache)
    cle = hashlib.sha256(json.dumps([round(v, 6) for v in bbox]).encode()).hexdigest()[:12]
    if cache.exists() and not rafraichir:
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("cle") == cle:
            return d["photos"], d
    url = API + "/search?" + urllib.parse.urlencode({"bbox": ",".join("%.6f" % v for v in bbox), "limit": limite})
    vus = {}
    for _ in range(pages_max):
        d = json.loads(_get(url).decode("utf-8"))
        for f in d.get("features", []):
            vus[f["id"]] = _resume(f)
        nxt = next((ln.get("href") for ln in d.get("links", []) if ln.get("rel") == "next"), None)
        if not nxt or not d.get("features"):
            break
        url = nxt
    photos = sorted(vus.values(), key=lambda r: (r["proprietes"].get("datetime") or "", r["id"]))
    doc = {"schema": "comparaison_recherche_panoramax/0.1", "cle": cle, "bbox": list(bbox), "api": API,
           "date_requete": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "n": len(photos), "photos": photos}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(doc, ensure_ascii=False, indent=0), encoding="utf-8")
    return photos, doc


def par_identifiants(ids, cache, rafraichir=False):
    """Métadonnées de photos données par identifiant complet (cache : un fichier JSON {id: résumé})."""
    cache = Path(cache)
    d = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    manque = [i for i in ids if rafraichir or i not in d]
    for k in range(0, len(manque), 50):
        lot = manque[k:k + 50]
        url = API + "/search?" + urllib.parse.urlencode({"ids": ",".join(lot), "limit": len(lot)})
        rep = json.loads(_get(url).decode("utf-8"))
        for f in rep.get("features", []):
            d[f["id"]] = _resume(f)
    if manque:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8")
    return {i: d[i] for i in ids if i in d}


def telecharger(photo, qualite, dossier):
    """Image `qualite` (hd | sd | thumb) d'une photo résumée, en cache sous dossier (photos_non_versionnees/...)."""
    dossier = Path(dossier)
    if "photos_non_versionnees" not in dossier.as_posix():
        raise RuntimeError("refus : image de tiers hors d'un dossier photos_non_versionnees/")
    url = photo["assets"].get(qualite)
    if not url:
        raise RuntimeError("photo %s : pas d'image %s" % (photo["id"], qualite))
    nom = "%s_%s_%s.jpg" % ((photo["proprietes"].get("datetime") or "")[:10], photo["id"][:8], qualite)
    f = dossier / nom
    if f.exists() and f.stat().st_size > 0:
        return f
    dossier.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".part")
    tmp.write_bytes(_get(url, timeout=600))
    tmp.replace(f)
    return f
