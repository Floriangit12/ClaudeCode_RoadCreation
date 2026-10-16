#!/usr/bin/env python
"""Archives et téléchargements publics de l'état d'avant travaux (lot 1g du plan, § 5).

Deux temps :
- les sous-commandes « telecharger-* » interrogent les services publics et rangent les fichiers bruts, avec un
  manifeste daté (URL, date, taille, sha256), dans data/sites/paquet_jardin/avant_travaux/<source>/ ; les photos
  Panoramax vont dans data/raw/panoramax/paquet_jardin/ (usage du dépôt, hors git) ;
- « resume » relit ces fichiers sans réseau et écrit, de façon déterministe, les synthèses versionnables
  dans <dossier de l'état>/sources/archives/ (JSON, GeoJSON) avec les sources et la config etat_cible.

Les fichiers téléchargés sont des données non fiables : ce script se lance avec « python -I », il est rangé hors
des dossiers de téléchargement et ne fait que les lire (JSON, XML, CSV, texte de PDF par PyMuPDF).

    python -I recon/pcg/etat/sources/archives.py telecharger-lidar
    python -I recon/pcg/etat/sources/archives.py telecharger-panoramax
    python -I recon/pcg/etat/sources/archives.py telecharger-pcrs
    python -I recon/pcg/etat/sources/archives.py telecharger-arretes
    python -I recon/pcg/etat/sources/archives.py telecharger-wayback
    python -I recon/pcg/etat/sources/archives.py telecharger-arbres
    python -I recon/pcg/etat/sources/archives.py resume          # PJ_ETAT=avant_travaux (lanceur recon/pcg/etat)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
import unicodedata
import urllib.parse
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[4]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

AT = RACINE / "data/sites/paquet_jardin/avant_travaux"
RAW_PNX = RACINE / "data/raw/panoramax/paquet_jardin"
CONFIG = json.loads((RACINE / "config/meylan.json").read_text(encoding="utf-8"))
SITE = CONFIG["sites"]["paquet_jardin"]
O = tuple(SITE["center_l93"])
DEMI = float(SITE["half_size_m"])
UA = "meylan-adas-sim/0.1 (research; reconstruction avant travaux Paquet Jardin)"

# --- sources (URL de service, pas de date d'état) ---
LIDAR_BLOC = "https://data.geopf.fr/telechargement/download/LiDARHD-NUALID/NUALHD_1-0__LAZ_LAMB93_PM_2025-03-25/"
LIDAR_NOM = "LHD_FXX_{x:04d}_{y:04d}_PTS_LAMB93_IGN69.copc.laz"
RAYON_PERIPHERIE_M = 500.0          # critère C5 du plan (§ 4.2) : périphérie jusqu'à >= 500 m
CRAIG_DAV = "https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm/"
CRAIG_AUTH = ("opendata", "")       # partage public du CRAIG (utilisateur « opendata », sans mot de passe)
PUBLIACT = "https://publiact.fr/api/v1/public"
PUBLIACT_MEYLAN = "1086_632ad65b94451"   # intégration PubliAct de la page « Délibérations et arrêtés » de meylan.fr
CDX = "https://web.archive.org/cdx/search/cdx"
WAYBACK = "https://web.archive.org/web/{ts}id_/{url}"
ARBRES = {
    # Grenoble-Alpes Métropole, données ouvertes (fichiers déposés le 22/02/2023 et le 11/09/2023)
    "arbres_metropole_2023-02-22.geojson":
        "https://data.metropolegrenoble.fr/sites/default/files/dataset/2023/02/22/cf47c651-fce0-4773-8883-68957560514b/arbre.geojson",
    "patrimoine_arbore_2023-09-11.geojson":
        "https://data.metropolegrenoble.fr/sites/default/files/dataset/2023/09/11/965f573d-52da-46df-8cd6-90df2f014df6/"
        "open_data1espnat_pat_arbore_tous_amnjkb.geojson.geojson",
}

# Requêtes Wayback (domaine, mot de l'URL) et documents retenus pour le carrefour : concertation C1 de 2022,
# travaux de 2024-2025 sur Verdun, Vercors et la Revirée (réseau de chaleur, ligne C1). Chaque cible garde la capture
# la plus ancienne (état publié au plus tôt) ; « motif » est une expression sur l'URL d'origine.
CDX_REQUETES = [("smmag.fr", "C1"), ("smmag.fr", "concertation"), ("smmag.fr", "meylan"),
                ("www.meylan.fr", "vercors"), ("www.meylan.fr", "verdun"), ("www.meylan.fr", "carrefour"),
                ("www.meylan.fr", "reviree"), ("www.meylan.fr", "rcu"), ("www.meylan.fr", "chaleur"),
                ("www.meylan.fr", "concertation")]
WAYBACK_CIBLES = [
    ("concertation_c1_2022", r"smmag\.fr/wp-content/uploads/2022/03/BHNS-C1_dossier-concertation_A3-v8\.pdf$",
     "dossier de la concertation préalable C1 (mars-avril 2022) : plans de l'existant et du projet"),
    ("concertation_c1_2022", r"smmag\.fr/wp-content/uploads/2022/03/CP-concertation-C1\.pdf$", "communiqué d'ouverture"),
    ("concertation_c1_2022", r"smmag\.fr/wp-content/uploads/2022/07/ANNEXES-concertation-C1\.pdf$", "annexes du bilan"),
    ("concertation_c1_2022", r"smmag\.fr/wp-content/uploads/2022/07/C1-_-Bilan-de-concertation-VF\.pdf$", "bilan"),
    ("concertation_c1_2022", r"smmag\.fr/wp-content/uploads/2022/07/C1-delib-bilan-concert-signee\.pdf$", "délibération"),
    ("concertation_c1_2022", r"smmag\.fr/plateforme-participative/les-concertations/amenagements-a-meylan-et-montbonnot"
                             r"-saint-martin-pour-ameliorer-la-performance-de-la-ligne-de-bus-c1/$", "page de la concertation"),
    ("vercors_granier", r"meylan\.fr/actualite/618/42-apaiser-les-circulations-sur-l-axe-vercors-granier", "réflexion Vercors-Granier (10/2022)"),
    ("vercors_granier", r"meylan\.fr/actualite/658/42-vercors-granier-premieres-decisions-prises\.htm$", "premières décisions (02/2023)"),
    ("vercors_granier", r"meylan\.fr/uploads/Image/6b/5793_322_carrefour-vercors-granier\.png$", "illustration du projet"),
    ("vercors_granier", r"meylan\.fr/actualite/900/42-amenagement-des-avenues-vercors-granier\.htm$", "aménagement Vercors-Granier (05/2024)"),
    ("vercors_granier", r"meylan\.fr/actualite/930/42-travaux-avenues-vercors-granier-taillefer\.htm$", "travaux Vercors-Granier-Taillefer (06/2024)"),
    ("vercors_granier", r"meylan\.fr/cms_viewFile\.php\?idtf=8138&path=Tracat-GAM-annonce-travaux-vercors-granier\.pdf$", "tract GAM des travaux"),
    ("vercors_granier", r"meylan\.fr/actualite/974/42-mise-en-sens-unique-temporaire-de-l-avenue-vercors\.htm$", "sens unique temporaire du Vercors (10/2024)"),
    ("vercors_granier", r"meylan\.fr/uploads/Image/b1/8479_073_bandeau-sens-unique-vercors-octobre\.jpg$", "plan du sens unique (10/2024)"),
    ("reseau_chaleur", r"meylan\.fr/386-un-nouveau-reseau-de-chaleur\.htm$", "réseau de chaleur urbain : tracé"),
    ("reseau_chaleur", r"meylan\.fr/actualite/874/42-s-informer-sur-les-futurs-travaux-du-reseau-de-chaleur\.htm$", "annonce des travaux RCU"),
    ("reseau_chaleur", r"meylan\.fr/actualite/888/42-chauffage-urbain-travaux-avenue-de-verdun\.htm$", "travaux RCU avenue de Verdun (04/2024)"),
    ("reseau_chaleur", r"meylan\.fr/uploads/Image/71/IMF_LISTE/GAB_MEYLAN/7856_721_travaux-rcu-verdun-vercors-2\.jpg$", "vignette RCU Verdun-Vercors"),
    ("reseau_chaleur", r"meylan\.fr/actualite/896/42-travaux-rcu-chemin-de-la-reviree\.htm$", "travaux RCU chemin de la Revirée (04/2024)"),
    ("reseau_chaleur", r"meylan\.fr/cms_viewFile\.php\?idtf=7810&path=arrete-de-circulation-RCU-reviree\.pdf$", "arrêté de circulation RCU Revirée"),
    ("reseau_chaleur", r"meylan\.fr/actualite/1079/42-reseau-de-chaleur-urbain-les-travaux-en-cours\.htm$", "travaux RCU en cours (2025)"),
    ("travaux_c1_2025", r"meylan\.fr/actualite/1082/42-travaux-avenue-du-vercors\.htm$", "travaux C1 avenue du Vercors (annonce 04/2025)"),
    ("travaux_c1_2025", r"meylan\.fr/uploads/Image/84/9336_833_plan-travaux-ligne-c1-av-vercors\.jpg$", "plan des travaux C1 du Vercors"),
    ("travaux_c1_2025", r"meylan\.fr/uploads/Image/64/9337_892_travaux-vercors-gam\.jpg$", "visuel travaux Vercors"),
    ("travaux_c1_2025", r"meylan\.fr/actualite/1108/42-travaux-avenue-du-vercors\.htm$", "travaux avenue du Vercors (05/2025)"),
    ("travaux_c1_2025", r"meylan\.fr/uploads/Image/21/9530_730_plan-circulation-avenue-du-Vercors-2-au-20-juin\.jpg$", "plan de circulation du 2 au 20/06/2025"),
    ("travaux_c1_2025", r"meylan\.fr/uploads/Image/c7/9531_757_tvx-vercors-30-juin-25-juillet-25\.jpg$", "travaux du 30/06 au 25/07/2025"),
    ("travaux_c1_2025", r"meylan\.fr/actualite/1129/42-travaux-c1-carrefour-verdun-vercors\.htm$", "travaux C1 du carrefour (06/2025)"),
    ("travaux_c1_2025", r"meylan\.fr/cms_viewFile\.php\?idtf=9331&path=Panneau-Amenagement-carrefour-Verdun-Vercors\.pdf$", "panneau du projet (04/2025)"),
    ("travaux_c1_2025", r"meylan\.fr/cms_viewFile\.php\?idtf=9330&path=panneau-amenagement-avenue-du-vercors\.pdf$", "panneau du projet Vercors (04/2025)"),
]
# Document public en ligne (hors Wayback) : décision de l'autorité environnementale sur le projet C1 de Meylan
DOCUMENTS_PUBLICS = [
    ("dreal_cas_par_cas_2022-08-16",
     "https://www.auvergne-rhone-alpes.developpement-durable.gouv.fr/IMG/pdf/20220816-dec-kkp3860-meylan_c1-38.pdf",
     "décision après examen au cas par cas du projet d'amélioration de la ligne C1 à Meylan (16/08/2022)"),
]


# --------------------------------------------------------------------------- outils
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lire_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ecrire_json(p, obj, indent=1):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8")


def maintenant():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _requests():
    import requests  # import tardif : la synthèse « resume » n'en a pas besoin
    return requests


def http(url, methode="GET", essais=5, **kw):
    """Requête avec reprises (429 / 5xx / coupure réseau)."""
    rq = _requests()
    h = {"User-Agent": UA, **kw.pop("headers", {})}
    dernier = None
    for k in range(essais):
        try:
            r = rq.request(methode, url, headers=h, timeout=kw.pop("timeout", (30, 180)), **kw)
            if r.status_code in (429, 500, 502, 503, 504):
                raise rq.HTTPError(f"HTTP {r.status_code}")
            return r
        except (rq.RequestException, OSError) as e:
            dernier = e
            time.sleep(min(5 * 2 ** k, 60))
    raise RuntimeError(f"échec {methode} {url} : {dernier}")


def telecharger(url, dest: Path, auth=None, essais=8):
    """Téléchargement en flux vers <dest>.part (reprise HTTP Range), puis renommage atomique."""
    rq = _requests()
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    total, dernier = None, None
    for k in range(essais):
        deja = tmp.stat().st_size if tmp.exists() else 0
        h = {"User-Agent": UA}
        if deja:
            h["Range"] = f"bytes={deja}-"
        try:
            with rq.get(url, headers=h, auth=auth, stream=True, timeout=(30, 90)) as r:
                if r.status_code == 416 and total and deja >= total:
                    break
                r.raise_for_status()
                if r.status_code == 200:
                    deja = 0
                    total = int(r.headers.get("content-length", 0)) or None
                elif r.status_code == 206:
                    cr = r.headers.get("content-range", "")
                    total = int(cr.rsplit("/", 1)[-1]) if "/" in cr else None
                with open(tmp, "ab" if deja else "wb") as f:
                    for b in r.iter_content(1 << 20):
                        f.write(b)
            if total is None or tmp.stat().st_size >= total:
                break
        except (rq.RequestException, OSError) as e:
            dernier = e
        time.sleep(min(2 ** (k + 1), 30))
    else:
        raise RuntimeError(f"échec du téléchargement {url} : {dernier}")
    if total is not None and tmp.stat().st_size != total:
        raise RuntimeError(f"taille incorrecte pour {dest.name} : {tmp.stat().st_size} != {total}")
    os.replace(tmp, dest)
    return dest


def wgs_l93(lon, lat):
    from pyproj import Transformer
    if not hasattr(wgs_l93, "t"):
        wgs_l93.t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    return wgs_l93.t.transform(lon, lat)


def l93_wgs(x, y):
    from pyproj import Transformer
    if not hasattr(l93_wgs, "t"):
        l93_wgs.t = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    return l93_wgs.t.transform(x, y)


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn")


def rel(p):
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return str(p)


def ecrire_gitignore(dossier: Path, motifs):
    """Documents de tiers (droits non précisés) et binaires lourds : jamais versionnés ; seuls les manifestes JSON le sont."""
    dossier.mkdir(parents=True, exist_ok=True)
    g = dossier / ".gitignore"
    txt = "".join(m + "\n" for m in motifs)
    if not g.exists() or g.read_text(encoding="utf-8") != txt:
        g.write_text(txt, encoding="utf-8")


# --------------------------------------------------------------------------- LiDAR HD de la périphérie (C5)
def dalles_lidar(rayon):
    """Dalles LiDAR HD de 1 km (nom = coin NO en km) couvrant le carré O ± rayon."""
    xs = range(int(math.floor((O[0] - rayon) / 1000)), int(math.floor((O[0] + rayon) / 1000)) + 1)
    ys = range(int(math.floor((O[1] - rayon) / 1000)) + 1, int(math.floor((O[1] + rayon) / 1000)) + 2)
    return [(x, y) for x in xs for y in ys]


def telecharger_lidar(a):
    dossier = AT / "lidar_hd_peripherie"
    ecrire_gitignore(dossier, ["*.laz", "*.part"])
    deja = {p.name for p in (AT / "lidar_hd").glob("*.copc.laz")}
    man = []
    for x, y in dalles_lidar(a.rayon):
        nom = LIDAR_NOM.format(x=x, y=y)
        url = LIDAR_BLOC + nom
        if nom in deja:
            p = AT / "lidar_hd" / nom
            man.append(dict(dalle=f"{x:04d}_{y:04d}", url=url, fichier=rel(p), octets=p.stat().st_size,
                            note="dalle du site, déjà téléchargée par l'inventaire des sources"))
            continue
        p = telecharger(url, dossier / nom)
        man.append(dict(dalle=f"{x:04d}_{y:04d}", url=url, fichier=rel(p), octets=p.stat().st_size, sha256=sha256(p),
                        telecharge_le=maintenant()))
        print(nom, p.stat().st_size)
    ecrire_json(dossier / "manifeste.json", {
        "source": "IGN, LiDAR HD (nuages classés COPC), bloc PM, édition 2025-03-25", "licence": "Licence Ouverte Etalab 2.0",
        "rayon_demande_m": a.rayon, "centre_l93": list(O), "dalles": man})


# --------------------------------------------------------------------------- Panoramax manquantes
def slim_panoramax(f):
    """Mêmes champs que pipeline/panoramax_enum.py:slim (métadonnées de la photo, sans l'EXIF brut)."""
    p = f.get("properties", {})
    ex = p.get("exif", {}) or {}
    io = p.get("pers:interior_orientation", {}) or {}
    lon, lat = f["geometry"]["coordinates"][:2]
    assets = f.get("assets", {})
    via = [l for l in f.get("links", []) if l.get("rel") == "via"]
    fov = io.get("field_of_view")
    proj = ex.get("Xmp.GPano.ProjectionType")
    sensor = io.get("sensor_array_dimensions")
    w = ex.get("Exif.Photo.PixelXDimension") or (sensor[0] if sensor else None)
    h = ex.get("Exif.Photo.PixelYDimension") or (sensor[1] if sensor else None)
    sem_coll = (p.get("collection") or {}).get("semantics") or []
    x, y = wgs_l93(lon, lat)
    return {
        "id": f["id"], "collection": f.get("collection"),
        "instance": via[0].get("instance_name") if via else None, "instance_url": via[0].get("href") if via else None,
        "producer": p.get("geovisio:producer") or ((f.get("providers") or [{}])[0].get("name")),
        "license": p.get("license"), "datetime": p.get("datetime"), "datetimetz": p.get("datetimetz"),
        "azimuth": p.get("view:azimuth"), "pers_yaw": p.get("pers:yaw"), "pers_pitch": p.get("pers:pitch"),
        "pers_roll": p.get("pers:roll"),
        "camera_make": io.get("camera_manufacturer") or ex.get("Exif.Image.Make"),
        "camera_model": io.get("camera_model") or ex.get("Exif.Image.Model"),
        "focal_length_mm": io.get("focal_length"), "field_of_view": fov,
        "projection": proj or ("equirectangular" if fov == 360 else "flat"),
        "is_360": bool(fov == 360 or proj == "equirectangular"),
        "width": int(w) if w not in (None, "") else None, "height": int(h) if h not in (None, "") else None,
        "original_file_size": p.get("original_file:size"), "original_file_name": p.get("original_file:name"),
        "horizontal_accuracy_m": p.get("quality:horizontal_accuracy"),
        "pixel_density": p.get("panoramax:horizontal_pixel_density"),
        "gps_altitude": ex.get("Exif.GPSInfo.GPSAltitude"),
        "transport": ";".join(s.get("value", "") for s in sem_coll if s.get("key") == "transport") or None,
        "n_annotations": len(p.get("annotations") or []),
        "annotation_tags": sorted({s["key"] + "=" + s["value"] for an in (p.get("annotations") or [])
                                   for s in an.get("semantics", []) if s.get("key", "").startswith("osm|")}),
        "rank_in_collection": p.get("geovisio:rank_in_collection"),
        "hd": assets.get("hd", {}).get("href"), "sd": assets.get("sd", {}).get("href"),
        "thumb": assets.get("thumb", {}).get("href"),
        "lat": lat, "lon": lon,
        "dist_center_m": round(math.hypot(x - O[0], y - O[1]), 1),
        "dx_e_m": round(x - O[0], 1), "dy_n_m": round(y - O[1], 1),
    }


def photos_manquantes():
    rech = lire_json(AT / "panoramax_semantique/recherche_2022_2025.json")
    locales = {p.name[11:-7] for p in RAW_PNX.glob("*_hd.jpg")}
    return rech, [it for it in rech["items"] if it["id"] not in locales]


def telecharger_panoramax(a):
    rech, manq = photos_manquantes()
    dossier = AT / "panoramax_complement"
    man_p = dossier / "manifeste.json"
    man = lire_json(man_p)["photos"] if man_p.exists() else {}
    print("photos de la recherche absentes du PC :", len(manq))
    for it in sorted(manq, key=lambda i: i["id"]):
        if it["id"] in man and (RAW_PNX / man[it["id"]]["fichier_local"]).exists():
            continue
        f = http(it["links_self"][0], headers={"Accept": "application/geo+json"}).json()
        p = slim_panoramax(f)
        nom = f"{(p['datetime'] or '')[:10]}_{p['id']}_hd"
        img = telecharger(p["hd"], RAW_PNX / f"{nom}.jpg")
        p["local_file"] = img.name
        (RAW_PNX / f"{nom}.json").write_text(json.dumps(p, indent=1, ensure_ascii=False), encoding="utf-8")
        man[p["id"]] = dict(fichier_local=img.name, octets=img.stat().st_size, sha256=sha256(img), url_hd=p["hd"],
                            url_item=it["links_self"][0], telecharge_le=maintenant())
        print(nom, img.stat().st_size)
        time.sleep(0.5)
    ecrire_json(man_p, {"source": rech["source"], "liste": rel(AT / "panoramax_semantique/recherche_2022_2025.json"),
                        "rangement_images": rel(RAW_PNX) + " (data/raw : hors git)",
                        "licence": "CC-BY-SA 4.0 (Panoramax, contributeurs) : images jamais versionnées",
                        "photos": dict(sorted(man.items()))})


# --------------------------------------------------------------------------- PCRS 5 cm du CRAIG
def lister_dav(url):
    r = http(url, methode="PROPFIND", auth=CRAIG_AUTH, headers={"Depth": "1"})
    if r.status_code >= 400:
        return None
    rep = []
    for bloc in re.findall(r"<d:response>(.*?)</d:response>", r.text, flags=re.S):
        href = re.search(r"<d:href>([^<]+)</d:href>", bloc)
        mod = re.search(r"<d:getlastmodified>([^<]+)</d:getlastmodified>", bloc)
        taille = re.search(r"<d:getcontentlength>([^<]+)</d:getcontentlength>", bloc)
        rep.append(dict(href=href.group(1) if href else None, modifie=mod.group(1) if mod else None,
                        octets=int(taille.group(1)) if taille else None))
    return rep[1:]


def telecharger_pcrs(a):
    dossier = AT / "craig_pcrs"
    ecrire_gitignore(dossier, ["*.zip", "*.gpkg", "*.part", "listing_webdav.json"])
    racine = lister_dav(CRAIG_DAV) or []
    arbre = {"racine": racine, "annees": {}}
    for e in racine:
        m = re.search(r"/(\d{4})/$", e["href"] or "")
        if not m:
            continue
        camp = lister_dav(CRAIG_DAV + m.group(1) + "/") or []
        arbre["annees"][m.group(1)] = {}
        for c in camp:
            mc = re.search(r"/(\d{4})/([^/]+)/$", c["href"] or "")
            if not mc:
                continue
            dalles = lister_dav(CRAIG_DAV + f"{mc.group(1)}/{mc.group(2)}/") or []
            arbre["annees"][m.group(1)][mc.group(2)] = dict(modifie=c["modifie"], fichiers=[
                dict(nom=d["href"].rsplit("/", 1)[-1], octets=d["octets"], modifie=d["modifie"]) for d in dalles])
            print(m.group(1), mc.group(2), len(dalles))
    ecrire_json(dossier / "listing_webdav.json", {"source": CRAIG_DAV, "acces": "PROPFIND Depth 1, utilisateur opendata",
                                                   "interroge_le": maintenant(), "arbre": arbre}, indent=0)
    for nom in ("Readme.md", "dallage_pcrs_opendata.gpkg.zip"):
        if any((e["href"] or "").endswith("/" + nom) for e in racine):
            telecharger(CRAIG_DAV + nom, dossier / nom, auth=CRAIG_AUTH)


# --------------------------------------------------------------------------- arrêtés municipaux (PubliAct)
def qs(obj, prefixe=""):
    """Encodage « qs » (crochets indexés) attendu par l'API PubliAct."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += qs(v, f"{prefixe}[{k}]" if prefixe else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += qs(v, f"{prefixe}[{i}]")
    elif obj is not None:
        out.append((prefixe, str(obj).lower() if isinstance(obj, bool) else str(obj)))
    return out


def noms_de_voies_du_site():
    """Noms des voies OSM de l'emprise (couche du dépôt) : termes de recherche des arrêtés."""
    fs = lire_json(RACINE / "data/sites/paquet_jardin/vector/osm_roads.geojson")["features"]
    noms = sorted({sans_accents(f["properties"]["name"]).lower().strip() for f in fs if f["properties"].get("name")})
    mots = set()
    for n in noms:
        n = re.sub(r"\s+", " ", n)
        m = re.match(r"(avenue|chemin|allee|rue|place|boulevard|impasse) (du |de la |de l'|des |de |d')?(.+)", n)
        mots.add((m.group(3) if m else n).strip())
    return sorted(mots)


TERMES_ARRETES_SUPPL = ["carrefour", "paquet", "saules blancs", "chronovelo", "C1"]
TERMES_TITRE_SEUL = {"vercors", "C1"}
ANNEES_ARRETES = ("2022", "2023", "2024", "2025")   # période demandée pour le lot 1g


def telecharger_arretes(a):
    dossier = AT / "arretes_meylan"
    ecrire_gitignore(dossier, ["pdf/", "*.part"])
    base = f"{PUBLIACT}/integrations/uid/{PUBLIACT_MEYLAN}"
    h = {"Accept": "application/json"}
    integ = http(base, headers=h).json()
    dossiers = http(base + "/folders", headers=h).json()
    annees = http(base + "/years", headers=h).json()
    termes = noms_de_voies_du_site() + TERMES_ARRETES_SUPPL
    docs = {}
    for t in termes:
        page = 0
        while True:
            q = {"filters": {"folderTypes": [], "folderIds": [], "status": ["ONLINE"], "search": {"text": t, "type": "STRICT"}},
                 "muiModels": {"pagination": {"pageSize": 100, "page": page}, "sorts": [{"field": "date", "sort": "desc"}]}}
            r = http(base + "/documents?" + urllib.parse.urlencode(qs(q)), headers=h)
            if r.status_code != 200:
                print("recherche refusée", t, r.status_code)
                break
            d = r.json()
            for x in d.get("rows", []):
                e = docs.setdefault(x["id"], dict(id=x["id"], nom=x.get("namePublic"), date_publication=x.get("date"),
                                                   dossier_id=x.get("folderId"), octets=x.get("size"), termes=[]))
                e["termes"] = sorted(set(e["termes"]) | {t})
            if (page + 1) * 100 >= d.get("count", 0):
                break
            page += 1
        print("terme", t, "->", len(docs), "documents cumulés")
        time.sleep(0.5)
    ecrire_json(dossier / "recherche.json", {
        "source": base, "organisation": (integ.get("organisation") or {}).get("name"), "annees_publiees": annees,
        "interroge_le": maintenant(), "termes": termes, "n": len(docs),
        "documents": sorted(docs.values(), key=lambda e: (e["date_publication"] or "", e["id"]))}, indent=1)
    ecrire_json(dossier / "dossiers.json", dossiers, indent=0)
    # PDF des actes de la période du lot (plan § 5, 1g) dont le titre ou le texte cite un lieu du site ; le texte
    # est relu par « resume ». La recherche porte aussi sur le contenu : « vercors » figure dans l'en-tête de tous les
    # actes (adresse de la mairie) et « C1 » est ambigu, ces deux termes ne valent donc que dans le titre.
    voies = [sans_accents(t).upper() for t in termes]
    for e in sorted(docs.values(), key=lambda e: e["id"]):
        an = (e["date_publication"] or "")[:4]
        if an not in ANNEES_ARRETES:
            continue
        titre = sans_accents(e["nom"] or "").upper()
        par_titre = any(re.search(r"\b" + re.escape(v) + r"\b", titre) for v in voies)
        par_texte = any(t not in TERMES_TITRE_SEUL for t in e["termes"])
        if not (par_titre or par_texte):
            continue
        dest = dossier / "pdf" / f"{e['id']}.pdf"
        if not dest.exists():
            telecharger(f"{PUBLIACT}/documents/{e['id']}/download", dest)
            time.sleep(0.3)


# --------------------------------------------------------------------------- Wayback
def telecharger_wayback(a):
    dossier = AT / "wayback"
    ecrire_gitignore(dossier, ["fichiers/", "*.part"])
    cdx = {}
    for dom, mot in CDX_REQUETES:
        p = [("url", dom + "/*"), ("output", "json"), ("filter", "statuscode:200"), ("filter", f"original:.*{mot}.*"),
             ("fl", "timestamp,original,mimetype,length,digest")]
        r = http(CDX, params=p, timeout=(30, 300))
        lignes = r.json() if r.status_code == 200 and r.text.strip() else []
        cdx[f"{dom}|{mot}"] = lignes[1:]
        print("cdx", dom, mot, len(lignes) - 1 if lignes else 0)
        time.sleep(3)
    ecrire_json(dossier / "cdx.json", {"source": CDX, "interroge_le": maintenant(), "requetes": cdx}, indent=0)
    captures = {}
    for v in cdx.values():
        for ts, orig, mime, longueur, dig in v:
            captures.setdefault(orig, []).append((ts, mime, longueur, dig))
    man = []
    for theme, motif, objet in WAYBACK_CIBLES:
        trouve = sorted((o for o in captures if re.search(motif, o)), key=lambda o: min(c[0] for c in captures[o]))
        if not trouve:
            man.append(dict(theme=theme, motif=motif, objet=objet, statut="aucune capture"))
            continue
        orig = trouve[0]
        cs = sorted(captures[orig])
        ts, mime = cs[0][0], cs[0][1]
        ext = {"application/pdf": ".pdf", "text/html": ".html", "image/jpeg": ".jpg", "image/png": ".png"}.get(mime, ".bin")
        nom = re.sub(r"[^A-Za-z0-9._-]+", "_", orig.split("://", 1)[-1])[-120:]
        dest = dossier / "fichiers" / f"{ts}_{nom}{'' if nom.endswith(ext) else ext}"
        try:
            telecharger(WAYBACK.format(ts=ts, url=orig), dest)
            man.append(dict(theme=theme, objet=objet, url=orig, capture=ts, capture_url=WAYBACK.format(ts=ts, url=orig),
                            captures=[c[0] for c in cs], mimetype=mime, fichier=rel(dest), octets=dest.stat().st_size,
                            sha256=sha256(dest)))
        except RuntimeError as e:
            man.append(dict(theme=theme, objet=objet, url=orig, capture=ts, statut=f"échec : {e}"[:300]))
        print(theme, ts, orig[-80:])
        time.sleep(2)
    pub = []
    for ident, url, objet in DOCUMENTS_PUBLICS:
        dest = AT / "documents_publics" / f"{ident}.pdf"
        ecrire_gitignore(dest.parent, ["*.pdf", "*.part"])
        try:
            telecharger(url, dest)
            pub.append(dict(id=ident, url=url, objet=objet, fichier=rel(dest), octets=dest.stat().st_size, sha256=sha256(dest)))
        except RuntimeError as e:
            pub.append(dict(id=ident, url=url, objet=objet, statut=f"échec : {e}"[:300]))
    ecrire_json(dossier / "manifeste.json", {"source": "Internet Archive (Wayback Machine), captures « id_ » (octets d'origine)",
                                            "telecharge_le": maintenant(), "documents": man, "documents_publics": pub})


# --------------------------------------------------------------------------- inventaires arborés publics
def telecharger_arbres(a):
    dossier = AT / "inventaire_arbore"
    man = []
    for nom, url in ARBRES.items():
        p = telecharger(url, dossier / nom)
        r = http(url, methode="HEAD")
        man.append(dict(fichier=rel(p), url=url, octets=p.stat().st_size, sha256=sha256(p),
                        last_modified=r.headers.get("Last-Modified"), telecharge_le=maintenant()))
    ecrire_gitignore(dossier, ["*.geojson", "*.part"])
    ecrire_json(dossier / "manifeste.json", {"source": "Grenoble-Alpes Métropole, données ouvertes (data.metropolegrenoble.fr)",
                                             "fichiers": man})


# =========================================================================== synthèse (sans réseau, déterministe)
def etat_cible():
    """État courant (recon/pcg/etat/etat_cible.py, sélectionné par PJ_ETAT et PJ_DATE_CIBLE)."""
    sys.path.insert(0, str(RACINE / "recon/pcg/etat"))
    import etat_cible as EC  # noqa: PLC0415 (module du socle, phase 0)
    E = EC.courant()
    if E is None:
        sys.exit("PJ_ETAT absent : lancer par recon/pcg/etat/lancer.py --etat avant_travaux (ou PJ_ETAT=avant_travaux)")
    EC.verifier_ecriture(E.dossier("sources"), E)
    return E


def citer_etat(E):
    return E.manifeste()


def resume(a):
    E = etat_cible()
    sortie = Path(E.dossier("sources")) / "archives"
    sortie.mkdir(parents=True, exist_ok=True)
    res = {}
    res["lidar"] = resume_lidar(E, sortie)
    res["pcrs"] = resume_pcrs(E, sortie)
    res["panoramax"] = resume_panoramax(E, sortie)
    res["arretes"] = resume_arretes(E, sortie)
    res["wayback"] = resume_wayback(E, sortie)
    res["arbres"] = resume_arbres(E, sortie)
    ecrire_json(sortie / "archives.json", {
        "schema": "pj_archives_avant_travaux/0.1", "generateur": rel(__file__), "etat_cible": citer_etat(E),
        "date_cible": E.date_cible, "sorties": res})
    for k, v in res.items():
        print(k, json.dumps(v, ensure_ascii=False)[:300])


def resume_lidar(E, sortie):
    man = lire_json(AT / "lidar_hd_peripherie/manifeste.json")
    xs, ys = [], []
    for d in man["dalles"]:
        x, y = (int(v) for v in d["dalle"].split("_"))
        xs += [x * 1000, x * 1000 + 1000]
        ys += [y * 1000 - 1000, y * 1000]
    emprise = [min(xs), min(ys), max(xs), max(ys)]
    marges = dict(ouest=round(O[0] - emprise[0], 1), est=round(emprise[2] - O[0], 1),
                  sud=round(O[1] - emprise[1], 1), nord=round(emprise[3] - O[1], 1))
    out = {"source": man["source"], "licence": man["licence"], "dalles": man["dalles"], "emprise_l93": emprise,
           "marge_au_centre_m": marges, "marge_min_m": min(marges.values()), "seuil_c5_m": RAYON_PERIPHERIE_M,
           "etat_cible": citer_etat(E),
           "validite": "relevé des 12/08 et 06/09/2021 (même mission que la dalle du site) ; hors quartier est (CONSTR-EST) "
                       "le bâti et la végétation de la périphérie sont réputés stables jusqu'à T (à contrôler sur l'IGN 2024)"}
    ecrire_json(sortie / "lidar_peripherie.json", out)
    return {"fichier": rel(sortie / "lidar_peripherie.json"), "n_dalles": len(man["dalles"]), "marge_min_m": out["marge_min_m"]}


def lire_gpkg_dallage(zp: Path):
    """Attributs du dallage PCRS (GeoPackage = SQLite) : campagne, date de PVA, nom de dalle. Lecture seule."""
    if not zp.exists():
        return []
    tmp = zp.with_suffix("")  # .gpkg à côté du zip (ignoré par git)
    if not tmp.exists():
        with zipfile.ZipFile(zp) as z:
            noms = [n for n in z.namelist() if n.endswith(".gpkg")]
            with z.open(noms[0]) as src, open(tmp, "wb") as dst:
                dst.write(src.read())
    con = sqlite3.connect(f"file:{tmp.as_posix()}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("select table_name from gpkg_contents where data_type='features'")]
        lignes = []
        for t in tables:
            cols = [r[1] for r in con.execute(f'pragma table_info("{t}")')]
            garde = [c for c in cols if c.lower() not in ("geom", "geometry", "fid")]
            for r in con.execute(f'select {",".join(chr(34) + c + chr(34) for c in garde)} from "{t}"'):
                lignes.append(dict(zip(garde, r)))
        return lignes
    finally:
        con.close()


def resume_pcrs(E, sortie):
    lst = lire_json(AT / "craig_pcrs/listing_webdav.json")
    x0c, y0c, x1c, y1c = CONFIG["commune"]["bbox_wgs84"]
    cx = [wgs_l93(x, y) for x, y in ((x0c, y0c), (x1c, y0c), (x0c, y1c), (x1c, y1c))]
    meylan = (min(p[0] for p in cx), min(p[1] for p in cx), max(p[0] for p in cx), max(p[1] for p in cx))
    site = (O[0] - DEMI, O[1] - DEMI, O[0] + DEMI, O[1] + DEMI)

    def touche(xh, yh, b):  # nom de dalle = coin haut-gauche en hm, dalle de 200 m
        return xh * 100 < b[2] and xh * 100 + 200 > b[0] and yh * 100 > b[1] and yh * 100 - 200 < b[3]
    dallage = lire_gpkg_dallage(AT / "craig_pcrs/dallage_pcrs_opendata.gpkg.zip")
    dates = {}
    for r in dallage:
        loc = str(r.get("location") or r.get("nom") or "")
        m = re.search(r"(\d{4})/([^/]+)/(\d{4}-\d{5})\.tif", loc)
        if m:
            dates.setdefault((m.group(1), m.group(2)), set()).add(str(r.get("date_pva") or r.get("date") or ""))
    camp = []
    for an, cs in sorted(lst["arbre"]["annees"].items()):
        for c, v in sorted(cs.items()):
            xy = [(int(g.group(1)), int(g.group(2))) for g in
                  (re.search(r"^(\d{4})-(\d{5})\.tif$", f["nom"]) for f in v["fichiers"]) if g]
            dm = sorted(f"{x}-{y}" for x, y in xy if touche(x, y, meylan))
            ds = sorted(f"{x}-{y}" for x, y in xy if touche(x, y, site))
            camp.append(dict(annee=int(an), campagne=c, n_dalles=len(xy), n_dalles_meylan=len(dm), dalles_site=ds,
                             couvre_meylan=bool(dm), couvre_site=bool(ds),
                             dates_pva=sorted(d for d in dates.get((an, c), set()) if d)))
    annees = sorted({c["annee"] for c in camp})
    sur_meylan = [c for c in camp if c["couvre_meylan"]]
    an_t = int(E.date_cible[:4])
    a_t = [c for c in camp if c["couvre_site"] and c["annee"] == an_t]
    liste_meylan = ", ".join("%d %s" % (c["annee"], c["campagne"]) for c in sur_meylan) or "aucune"
    liste_an_t = ", ".join(c["campagne"] for c in camp if c["annee"] == an_t) or "aucune campagne"
    if a_t:
        phrase_t = "Une campagne %d couvre le site : %s. " % (an_t, a_t[0]["campagne"])
    else:
        phrase_t = "Aucune campagne %d ne couvre Meylan ni le site (campagnes %d : %s). " % (an_t, an_t, liste_an_t)
    conclusion = (
        "Le WebDAV ouvert du CRAIG publie les années %d à %d (%d campagnes). Campagnes couvrant Meylan : %s. "
        % (annees[0], annees[-1], len(camp), liste_meylan) + phrase_t
        + "La seule ortho PCRS 5 cm ouverte sur le site est donc celle de la campagne qui le couvre ci-dessus ; "
          "la campagne GAM de 2025 n'est diffusée qu'en accès restreint (RTGE), hors de ce partage.")
    out = {"source": lst["source"], "interroge_le": lst["interroge_le"], "etat_cible": citer_etat(E),
           "emprise_meylan_l93": [round(v, 1) for v in meylan], "emprise_site_l93": [round(v, 2) for v in site],
           "dallage_gpkg": rel(AT / "craig_pcrs/dallage_pcrs_opendata.gpkg.zip") if dallage else None,
           "campagnes": camp, "conclusion": conclusion}
    ecrire_json(sortie / "pcrs_campagnes.json", out)
    return {"fichier": rel(sortie / "pcrs_campagnes.json"), "n_campagnes": len(camp),
            "campagnes_meylan": [f"{c['annee']}/{c['campagne']}" for c in sur_meylan], "campagne_annee_T_sur_site": bool(a_t)}


def resume_panoramax(E, sortie):
    man = lire_json(AT / "panoramax_complement/manifeste.json")
    rech = lire_json(AT / "panoramax_semantique/recherche_2022_2025.json")
    par_id = {it["id"]: it for it in rech["items"]}
    photos = []
    for pid, m in sorted(man["photos"].items()):
        meta_p = RAW_PNX / (m["fichier_local"][:-4] + ".json")
        p = lire_json(meta_p) if meta_p.exists() else {}
        x, y = wgs_l93(p.get("lon", 0), p.get("lat", 0)) if p else (None, None)
        photos.append(dict(id=pid, datetime=p.get("datetime") or par_id.get(pid, {}).get("datetime"),
                           auteur=p.get("producer"), licence=p.get("license"), instance=p.get("instance_url"),
                           projection=p.get("projection"), is_360=p.get("is_360"), azimut=p.get("azimuth"),
                           camera=" ".join(v for v in (p.get("camera_make"), p.get("camera_model")) if v),
                           x_local=round(x - O[0], 2) if x else None, y_local=round(y - O[1], 2) if y else None,
                           dist_centre_m=p.get("dist_center_m"), url_hd=m["url_hd"], url_item=m["url_item"],
                           fichier_local=rel(RAW_PNX / m["fichier_local"]), sha256=m["sha256"], octets=m["octets"]))
    t = E.date_cible
    jour = [ph for ph in photos if (ph["datetime"] or "")[:10] == t]
    par_mois = {}
    for ph in photos:
        par_mois[(ph["datetime"] or "")[:7]] = par_mois.get((ph["datetime"] or "")[:7], 0) + 1
    out = {"source": man["source"], "liste": man["liste"], "licence": "CC-BY-SA 4.0 : images hors git (data/raw)",
           "attribution": sorted({ph["auteur"] for ph in photos if ph["auteur"]}), "etat_cible": citer_etat(E),
           "n": len(photos), "n_jour_T": len(jour), "par_mois": dict(sorted(par_mois.items())), "photos": photos}
    ecrire_json(sortie / "panoramax_complement.json", out)
    return {"fichier": rel(sortie / "panoramax_complement.json"), "n": len(photos), "n_jour_T": len(jour)}


# --- arrêtés : lecture des PDF et rattachement au carrefour
def adresses_du_site(rayon):
    """(voie normalisée, numéro) -> distance au centre, depuis la BAN de Meylan (data/context/ban_meylan.csv)."""
    out = {}
    with open(RACINE / "data/context/ban_meylan.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                x, y = float(r["x"]), float(r["y"])
            except ValueError:
                continue
            d = math.hypot(x - O[0], y - O[1])
            if d <= rayon:
                cle = (sans_accents(r["voie_nom"]).lower(), r["numero"])
                out[cle] = min(out.get(cle, 1e9), round(d, 1))
    return out


MOIS = {m: i + 1 for i, m in enumerate(["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout",
                                         "septembre", "octobre", "novembre", "decembre"])}


def dates_du_texte(t):
    """Dates écrites en clair ou en chiffres dans le texte d'un arrêté (ISO, triées, uniques)."""
    s = set()
    for j, m, a in re.findall(r"\b(\d{1,2})(?:er)?\s+(janvier|fevrier|mars|avril|mai|juin|juillet|aout|septembre|octobre|"
                              r"novembre|decembre)\s+(20\d\d)\b", t):
        try:
            s.add(dt.date(int(a), MOIS[m], int(j)).isoformat())
        except ValueError:
            pass
    for j, m, a in re.findall(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d\d)\b", t):
        try:
            s.add(dt.date(int(a), int(m), int(j)).isoformat())
        except ValueError:
            pass
    return sorted(s)


def texte_pdf(p: Path):
    import fitz  # PyMuPDF : extraction du texte seulement
    with fitz.open(p) as doc:
        return "\n".join(page.get_text() for page in doc)


def resume_arretes(E, sortie):
    rech = lire_json(AT / "arretes_meylan/recherche.json")
    adr = adresses_du_site(200.0)
    voies_site = sorted({v for v, _ in adr})
    retenus, lus = [], 0
    for e in rech["documents"]:
        p = AT / "arretes_meylan/pdf" / f"{e['id']}.pdf"
        if not p.exists():
            continue
        lus += 1
        brut = texte_pdf(p)
        t = sans_accents(brut).lower()
        t = re.sub(r"[ \t ]+", " ", t)
        # adresses du site citées : « n° 12 avenue de verdun », « 12, avenue de verdun », « au droit du 12 ... »
        cites = set()
        for v in voies_site:
            for m in re.finditer(r"(\d{1,3})(?:\s*(?:bis|ter))?\s*,?\s*" + re.escape(v), t):
                if (v, m.group(1)) in adr:
                    cites.add((v, m.group(1), adr[(v, m.group(1))]))
        carrefour = bool(re.search(r"carrefour[^.\n]{0,60}(verdun|vercors|reviree)|(verdun|vercors)[^.\n]{0,40}"
                                   r"(verdun|vercors|reviree)", t))
        reviree = "reviree" in t
        mitailleres = "mitailleres" in t
        objet = []
        for cle, motif in (("circulation", r"circulation|deviation|sens unique|alternat|vitesse"),
                           ("stationnement", r"stationnement"), ("travaux", r"travaux|chantier|tranchee|reseau|branchement"),
                           ("voirie", r"chaussee|enrobe|revetement|trottoir|bordure"),
                           ("reseau_chaleur", r"reseau de chaleur|chauffage urbain|\brcu\b"),
                           ("signalisation", r"signalisation|feux|marquage")):
            if re.search(motif, t):
                objet.append(cle)
        if not (cites or carrefour or reviree or mitailleres):
            continue
        ds = [d for d in dates_du_texte(t) if "2019" <= d[:4] <= "2026"]
        retenus.append(dict(
            id=e["id"], titre=e["nom"], date_publication=(e["date_publication"] or "")[:10],
            url=f"{PUBLIACT}/documents/{e['id']}/download", sha256=sha256(p),
            adresses_site=[dict(voie=v, numero=n, dist_centre_m=d) for v, n, d in sorted(cites)],
            cite_carrefour=carrefour, cite_reviree=reviree, cite_mitailleres=mitailleres, objet=objet,
            dates_citees=ds, periode_citee=[ds[0], ds[-1]] if ds else None,
            avant_T=bool(ds) and ds[0] <= E.date_cible))
    retenus.sort(key=lambda r: (r["date_publication"], r["id"]))
    out = {"source": rech["source"], "organisation": rech["organisation"], "interroge_le": rech["interroge_le"],
           "annees_publiees": rech["annees_publiees"], "termes": rech["termes"], "etat_cible": citer_etat(E),
           "methode": "titres PubliAct filtrés par les voies du site, PDF lus (PyMuPDF), adresses rapprochées de la BAN "
                      "à 200 m du centre ; carrefour = Verdun et Vercors (ou la Revirée) cités ensemble",
           "lacune": "PubliAct ne publie les actes de Meylan qu'à partir du 24/09/2022 ; les arrêtés métropolitains de "
                     "voirie (data/context/arretes_travaux_metropole.csv) s'arrêtent en 06/2022",
           "n_resultats_recherche": rech["n"], "n_pdf_lus": lus, "n_retenus": len(retenus), "arretes": retenus}
    ecrire_json(sortie / "arretes_meylan.json", out)
    return {"fichier": rel(sortie / "arretes_meylan.json"), "n_recherche": rech["n"], "n_pdf": lus, "n_retenus": len(retenus)}


def resume_wayback(E, sortie):
    man = lire_json(AT / "wayback/manifeste.json")
    docs = []
    for d in man["documents"]:
        e = {k: d.get(k) for k in ("theme", "objet", "url", "capture", "capture_url", "captures", "mimetype", "octets",
                                   "sha256", "statut") if d.get(k) is not None}
        p = RACINE / d["fichier"] if d.get("fichier") else None
        if p and p.exists() and d.get("mimetype") == "application/pdf":
            with __import__("fitz").open(p) as doc:
                e["pages"] = doc.page_count
        if p and p.exists() and d.get("mimetype") == "text/html":
            h = p.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"<title>(.*?)</title>", h, flags=re.S)
            e["titre_page"] = re.sub(r"\s+", " ", m.group(1)).strip() if m else None
        docs.append(e)
    out = {"source": man["source"], "etat_cible": citer_etat(E), "documents": docs,
           "documents_publics": [{k: v for k, v in d.items() if k != "fichier"} for d in man["documents_publics"]],
           "droits": "documents de la commune, du SMMAG et de l'État : fichiers non versionnés (data/.../wayback/fichiers/)"}
    ecrire_json(sortie / "wayback_documents.json", out)
    return {"fichier": rel(sortie / "wayback_documents.json"), "n": len(docs),
            "n_ok": sum(1 for d in docs if d.get("sha256")), "n_publics": len(out["documents_publics"])}


def resume_arbres(E, sortie):
    man = lire_json(AT / "inventaire_arbore/manifeste.json")
    feats, stats = [], []
    for m in man["fichiers"]:
        p = RACINE / m["fichier"]
        fc = lire_json(p)
        n_tot, n_site = len(fc["features"]), 0
        for f in fc["features"]:
            g = f.get("geometry") or {}
            c = g.get("coordinates")
            if not c:
                continue
            lon, lat = (c[0] if g["type"] == "MultiPoint" else c)[:2]
            x, y = wgs_l93(lon, lat)
            if max(abs(x - O[0]), abs(y - O[1])) > DEMI:
                continue
            n_site += 1
            pr = f.get("properties", {})
            garde = {k: pr.get(k) for k in ("arbre_id", "id_metro", "genre", "espece", "essence", "nom_commun", "type",
                                            "hauteur", "circonference", "annee_plantation", "situation", "adresse",
                                            "alignement", "etat") if k in pr}
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(x, 3), round(y, 3)]},
                          "properties": {"jeu": Path(m["fichier"]).name, **garde,
                                         "x_local": round(x - O[0], 2), "y_local": round(y - O[1], 2)}})
        genres = {}
        for f in feats:
            if f["properties"]["jeu"] == Path(m["fichier"]).name:
                g = f["properties"].get("genre") or "(non renseigné)"
                genres[g] = genres.get(g, 0) + 1
        stats.append(dict(jeu=Path(m["fichier"]).name, url=m["url"], last_modified=m.get("last_modified"),
                          sha256=m["sha256"], n_total=n_tot, n_site=n_site,
                          genres_site=dict(sorted(genres.items(), key=lambda kv: (-kv[1], kv[0])))))
    feats.sort(key=lambda f: (f["properties"]["jeu"], f["geometry"]["coordinates"]))
    ecrire_json(sortie / "inventaire_arbore_site.geojson", {
        "type": "FeatureCollection", "name": "inventaire_arbore_site",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}},
        "meta": {"source": man["source"], "jeux": stats, "emprise": f"carré O ± {DEMI:g} m", "etat_cible": citer_etat(E),
                 "validite": "fichiers déposés en 2023 (avant T) : présence attestée à la date du jeu ; genre et espèce "
                             "à rapprocher des arbres d'objets_avant_travaux (lot 2c)"},
        "features": feats}, indent=0)
    return {"fichier": rel(sortie / "inventaire_arbore_site.geojson"), "jeux": [(s["jeu"], s["n_site"]) for s in stats]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("telecharger-lidar")
    s.add_argument("--rayon", type=float, default=RAYON_PERIPHERIE_M)
    s.set_defaults(f=telecharger_lidar)
    for nom, f in (("telecharger-panoramax", telecharger_panoramax), ("telecharger-pcrs", telecharger_pcrs),
                   ("telecharger-arretes", telecharger_arretes), ("telecharger-wayback", telecharger_wayback),
                   ("telecharger-arbres", telecharger_arbres), ("resume", resume)):
        sp.add_parser(nom).set_defaults(f=f)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
