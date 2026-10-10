"""Images Mapillary du site : inventaire (Graph API v4), sélection, téléchargement, caméras et poses.

Étapes (CLI, depuis recon/pcg/enrichir) :
  python mapillary.py --lister        # Graph API -> data/raw/mapillary/paquet_jardin/images.json
  python mapillary.py --selectionner  # <= 90 m du centre + emprise 2023-2024, séquences récentes d'abord
  python mapillary.py --telecharger   # thumb_2048 -> data/raw/mapillary/paquet_jardin/img/<id>.jpg
  python mapillary.py --poses         # sphériques : pose Panoramax équivalente, sinon calage GCP (poses.py)
  python mapillary.py --recaler       # recalage sur les bordures GAM (séquences : retard GNSS ; images)
  python mapillary.py --assembler     # pose retenue par image -> poses/poses_mapillary.json
  python mapillary.py --valider       # 10 planches de validation + résidus des mâts levés
  python mapillary.py --trianguler    # axes de mâts sur vues Mapillary + Panoramax calées
  python mapillary.py --census        # cibles (conflits ouverts, entités sans preuve), découpes, planches
  python mapillary.py --obs           # revue_mapillary.json (verdicts visuels) -> obs_mapillary.json

Jeton : variable d'environnement MAPILLARY_TOKEN, sinon fichier désigné par MAPILLARY_TOKEN_FILE
(ou --jeton-fichier). Le jeton n'est JAMAIS écrit (ni dans les fichiers, ni dans les journaux, ni
dans les URL : en-tête « Authorization: OAuth ... » ; toute URL enregistrée est purgée de
`access_token`).

Licence : images Mapillary CC-BY-SA 4.0 ; l'attribution (auteur, id, date, lien) est recopiée dans
images.json, dans chaque observation et dans le README des preuves. Les images ne sont pas versionnées
(data/raw est ignoré par git).

Modèles de caméra Mapillary (conventions OpenSfM) :
- coordonnées image normalisées : x_n = (u − W/2)/max(W, H), y_n = (v − H/2)/max(W, H) (pixels
  continus, le pixel (i, j) couvre [i, i+1[) ; repère caméra OpenSfM (x droite, y bas, z avant) ;
- `perspective` [f, k1, k2] : x = X/Z, y = Y/Z, r² = x² + y², d = 1 + k1 r² + k2 r⁴, x_n = f·d·x ;
- `fisheye` [f, k1, k2] : θ = atan(r), d = 1 + k1 θ² + k2 θ⁴, x_n = f·d·θ/r·x ;
- `spherical` / `equirectangular` : lon = atan2(X, Z), lat = atan2(−Y, √(X² + Z²)),
  x_n = lon/2π, y_n = −lat/2π (même chose que le modèle `equirect` de camera.py) ;
- computed_rotation = vecteur rotation (axe·angle) de R_cw : X_cam = R_cw·(X_enu − C), monde ENU
  (est, nord, haut) au voisinage de computed_geometry ; à défaut computed_compass_angle (nord vrai).
Conversion au repère local : ENU -> grille Lambert-93 par la convergence des méridiens γ (azimut grille
du nord vrai, ≈ −2,01° au site) ; repère caméra du projet (droite, avant, haut) = (x, z, −y) OpenSfM ;
pose [x, y, z, lacet, tangage, roulis] par décomposition de R dans la convention de
camera.matrice_rotation (aucune modification de camera.py : sous-classe `CameraMly`).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
if str(ICI) not in sys.path:
    sys.path.insert(0, str(ICI))

from camera import (CENTRE, O, RACINE, Camera, arrondi, ecrire_json, gps_local, lire_json,  # noqa: E402
                    matrice_rotation, z_sol)

SCHEMA = "pj_mapillary/0.1"
API = "https://graph.mapillary.com"
BBOX = (5.7662, 45.2063, 5.7702, 45.2090)          # lon min, lat min, lon max, lat max (WGS84)
BRUT = RACINE / "data/raw/mapillary/paquet_jardin"
IMG = BRUT / "img"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary"
CHAMPS = ("id,captured_at,camera_type,camera_parameters,computed_geometry,geometry,computed_compass_angle,"
          "compass_angle,computed_rotation,computed_altitude,altitude,sequence,thumb_2048_url,thumb_original_url,"
          "creator,quality_score,width,height,make,model,is_pano,atomic_scale,exif_orientation,merge_cc")
LICENCE = "CC-BY-SA 4.0"
RAYON_SELECTION_M = 90.0
MAX_IMAGES = 400


# --------------------------------------------------------------------------- jeton / HTTP
def jeton(fichier=None):
    """Jeton Mapillary : MAPILLARY_TOKEN, sinon le fichier (argument ou MAPILLARY_TOKEN_FILE)."""
    t = os.environ.get("MAPILLARY_TOKEN")
    if t:
        return t.strip()
    f = fichier or os.environ.get("MAPILLARY_TOKEN_FILE")
    if not f or not Path(f).exists():
        raise SystemExit("jeton Mapillary introuvable : définir MAPILLARY_TOKEN ou MAPILLARY_TOKEN_FILE")
    return Path(f).read_text(encoding="utf-8").strip()


def url_sans_jeton(u):
    """URL purgée de tout paramètre access_token (avant tout enregistrement)."""
    if not isinstance(u, str) or "?" not in u:
        return u
    p = urllib.parse.urlsplit(u)
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if k.lower() != "access_token"]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(q), p.fragment))


def _purger(v):
    if isinstance(v, dict):
        return {k: _purger(x) for k, x in v.items() if k.lower() != "access_token"}
    if isinstance(v, list):
        return [_purger(x) for x in v]
    if isinstance(v, str) and v.startswith("http"):
        return url_sans_jeton(v)
    return v


def http_get(url, tok=None, essais=5, timeout=90, binaire=False):
    """GET avec reprises (429 / 5xx / réseau : attente exponentielle). Le jeton passe par l'en-tête."""
    h = {"User-Agent": "paquet-jardin-recon/0.1"}
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
            raise RuntimeError(f"HTTP {e.code} sur {url_sans_jeton(url).split('?')[0]}") from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            if k < essais - 1:
                time.sleep(attente)
                attente *= 2
                continue
            raise
    raise RuntimeError("échec réseau")


# --------------------------------------------------------------------------- 1. inventaire
def lister(tok, n=4):
    """Toutes les images de la bbox (dallée n×n : la recherche bbox plafonne à 2 000 réponses)."""
    lo0, la0, lo1, la1 = BBOX
    vus = {}
    for i in range(n):
        for j in range(n):
            b = (lo0 + (lo1 - lo0) * i / n, la0 + (la1 - la0) * j / n,
                 lo0 + (lo1 - lo0) * (i + 1) / n, la0 + (la1 - la0) * (j + 1) / n)
            url = f"{API}/images?" + urllib.parse.urlencode(
                {"bbox": ",".join(f"{x:.6f}" for x in b), "fields": CHAMPS, "limit": 2000})
            d = http_get(url, tok)
            lot = d.get("data", [])
            if len(lot) >= 2000:
                print(f"  dalle {i},{j} saturée (2 000) : affiner le dallage", flush=True)
            for im in lot:
                vus[str(im["id"])] = im
            print(f"  dalle {i},{j} : {len(lot)} images ({len(vus)} distinctes)", flush=True)
            time.sleep(0.3)
    return [vus[k] for k in sorted(vus)]


def _date(im):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(im["captured_at"] / 1000.0))


def enrichir_meta(im):
    """Champs dérivés : date UTC, position locale (computed puis brute), distance au centre."""
    g = im.get("computed_geometry") or im.get("geometry")
    lon, lat = g["coordinates"][:2]
    xy, gamma = gps_local(lon, lat)
    im = _purger(dict(im))
    im["date"] = _date(im)
    im["local_xy"] = [round(float(xy[0]), 3), round(float(xy[1]), 3)]
    im["gamma_deg"] = round(float(gamma), 5)
    im["d_centre_m"] = round(float(np.hypot(*(xy - CENTRE))), 2)
    im["geometrie_source"] = "computed_geometry" if im.get("computed_geometry") else "geometry"
    cr = im.get("creator") or {}
    im["attribution"] = {"auteur": cr.get("username"), "licence": LICENCE, "plateforme": "Mapillary",
                         "lien": f"https://www.mapillary.com/app/?pKey={im['id']}"}
    return im


def ecrire_inventaire(images):
    BRUT.mkdir(parents=True, exist_ok=True)
    seqs = {}
    for im in images:
        s = seqs.setdefault(im.get("sequence") or "?", {"n": 0, "dates": set(), "camera_type": set(),
                                                         "auteur": set()})
        s["n"] += 1
        s["dates"].add(im["date"][:10])
        s["camera_type"].add(im.get("camera_type") or "?")
        s["auteur"].add((im.get("creator") or {}).get("username") or "?")
    resume = {k: {"n": v["n"], "dates": sorted(v["dates"]), "camera_type": sorted(v["camera_type"]),
                  "auteur": sorted(v["auteur"])} for k, v in sorted(seqs.items())}
    doc = {"schema": SCHEMA, "source": f"{API}/images (bbox {','.join(map(str, BBOX))})",
           "date_requete": time.strftime("%Y-%m-%d"), "licence": LICENCE,
           "attribution": "Images © contributeurs Mapillary, CC-BY-SA 4.0 (auteur par image)",
           "remarque": "URL des vignettes signées et périssables ; aucun jeton enregistré.",
           "n": len(images), "sequences": resume, "images": images}
    ecrire_json(BRUT / "images.json", doc)
    return doc


def inventaire():
    return lire_json(BRUT / "images.json")


# --------------------------------------------------------------------------- 2. sélection
def palier(date):
    """Priorité temporelle : 1 = 2022-2025 (état le plus proche de 2026), 2 = 2019-2020, 3 = 2017-2018."""
    return 1 if date >= "2022-01-01" else (2 if date >= "2019-01-01" else 3)


def distance_zone_2023(xy):
    """Distance (m) aux surfaces construites en 2023-2024 (0 dedans) ; points locaux (N, 2)."""
    import gcp as G
    c23, _ = G._zones_changees()
    Q = np.atleast_2d(np.asarray(xy, float))
    d = np.full(len(Q), np.inf)
    dedans = G._dans(Q, c23)
    for r in c23:
        A, B = r, np.roll(r, -1, axis=0)
        AB = B - A
        L2 = np.maximum((AB ** 2).sum(1), 1e-12)
        t = np.clip(((Q[:, None, :] - A[None]) * AB[None]).sum(2) / L2[None], 0, 1)
        P = A[None] + t[..., None] * AB[None]
        d = np.minimum(d, np.hypot(*(Q[:, None, :] - P).transpose(2, 0, 1)).min(1))
    d[dedans] = 0.0
    return d


def selectionner(rayon=RAYON_SELECTION_M, nmax=MAX_IMAGES, pas_eclaircie=4.0, marge_2023=15.0, dmax_recent=170.0,
                 pas_recent=5.0):
    """Sélection déterministe, par ordre de priorité : (1) images 2022-2025 à <= rayon du centre ou à
    <= marge_2023 de l'emprise construite en 2023-2024 ; (2) images 2022-2025 jusqu'à dmax_recent du
    centre (bordures et objets sans preuve hors du cœur), éclaircies à pas_recent m par séquence ;
    (3) images 2019-2020 puis 2017-2018 à <= rayon, éclaircies à pas_eclaircie m. Plafond nmax.
    Le cœur du carrefour ayant été refait en 2025, les images anciennes du cœur ne prouvent rien pour
    2026 : les images récentes du reste du site passent avant elles."""
    inv = inventaire()
    ims = inv["images"]
    X = np.array([im["local_xy"] for im in ims])
    dz = distance_zone_2023(X)
    cand = []
    for im, x, d23 in zip(ims, X, dz):
        p = palier(im["date"])
        dc = im["d_centre_m"]
        if p == 1 and (dc <= rayon or (d23 <= marge_2023 and dc <= dmax_recent)):
            rang, motif = 0, ("centre" if dc <= rayon else "emprise_2023_2024")
        elif p == 1 and dc <= dmax_recent:
            rang, motif = 1, "recent_hors_cœur"
        elif dc <= rayon:
            rang, motif = p, "centre"
        else:
            continue
        cand.append((rang, dc, im["id"], im, motif, float(d23)))
    cand.sort(key=lambda t: (t[0], t[1], t[2]))
    gardes, par_seq = [], {}
    for rang, dc, iid, im, motif, d23 in cand:
        if len(gardes) >= nmax:
            break
        xy = np.array(im["local_xy"])
        az = im.get("computed_compass_angle") or im.get("compass_angle") or 0.0
        pas = 0.0 if rang == 0 else (pas_recent if rang == 1 else pas_eclaircie)
        if pas > 0:
            voisins = par_seq.get(im["sequence"], [])
            if any(np.hypot(*(xy - q)) < pas and abs((az - a + 180) % 360 - 180) < 45 for q, a in voisins):
                continue
        par_seq.setdefault(im["sequence"], []).append((xy, az))
        gardes.append(dict(id=iid, date=im["date"], sequence=im["sequence"], camera_type=im["camera_type"],
                           palier=palier(im["date"]), rang=rang, motif=motif, d_centre_m=dc,
                           d_zone_2023_m=round(d23, 2), auteur=(im.get("creator") or {}).get("username")))
    gardes.sort(key=lambda g: (g["rang"], g["date"], g["id"]))
    from collections import Counter
    doc = {"schema": SCHEMA, "regle": " ".join(selectionner.__doc__.split()),
           "parametres": dict(rayon_m=rayon, nmax=nmax, pas_eclaircie_m=pas_eclaircie, marge_2023_m=marge_2023,
                              dmax_recent_m=dmax_recent, pas_recent_m=pas_recent),
           "n_candidates": len(cand), "n": len(gardes),
           "par_mois": dict(sorted(Counter(g["date"][:7] for g in gardes).items())),
           "par_motif": dict(sorted(Counter(g["motif"] for g in gardes).items())),
           "images": gardes}
    ecrire_json(BRUT / "selection.json", doc)
    print(f"sélection : {len(gardes)} / {len(cand)} candidates ; {doc['par_mois']} ; {doc['par_motif']}")
    return doc


# --------------------------------------------------------------------------- téléchargement
def chemin_image(iid):
    return IMG / f"{iid}.jpg"


def telecharger(tok, pause=0.15):
    """thumb_2048 (perspective) ou thumb_original (sphérique) de la sélection ; URL rafraîchie par la
    Graph API (les URL signées de l'inventaire expirent). Reprises sur erreur, fichiers existants gardés."""
    sel = lire_json(BRUT / "selection.json")["images"]
    inv = {im["id"]: im for im in inventaire()["images"]}
    IMG.mkdir(parents=True, exist_ok=True)
    journal = {}
    jp = BRUT / "telechargement.json"
    if jp.exists():
        journal = lire_json(jp).get("images", {})
    n_ok = n_err = 0
    for k, s in enumerate(sel):
        iid = s["id"]
        f = chemin_image(iid)
        if f.exists() and f.stat().st_size > 10000:
            n_ok += 1
            continue
        champ = "thumb_original_url" if inv[iid]["camera_type"] in ("spherical", "equirectangular") else "thumb_2048_url"
        try:
            meta = http_get(f"{API}/{iid}?fields={champ}", tok)
            url = meta.get(champ)
            if not url:
                raise RuntimeError(f"pas de {champ}")
            data = http_get(url, None, binaire=True, timeout=180)
            if len(data) < 10000 or data[:2] != b"\xff\xd8":
                raise RuntimeError("réponse non JPEG")
            tmp = f.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(f)
            journal[iid] = dict(champ=champ, octets=len(data), sha256=hashlib.sha256(data).hexdigest())
            n_ok += 1
        except Exception as e:  # noqa: BLE001
            journal[iid] = dict(champ=champ, erreur=str(e)[:200])
            n_err += 1
        if k % 25 == 0:
            print(f"  {k + 1}/{len(sel)} ok={n_ok} err={n_err}", flush=True)
            ecrire_json(jp, {"schema": SCHEMA, "images": dict(sorted(journal.items()))})
        time.sleep(pause)
    ecrire_json(jp, {"schema": SCHEMA, "images": dict(sorted(journal.items()))})
    print(f"téléchargement : {n_ok} ok, {n_err} erreurs -> {IMG}")


# --------------------------------------------------------------------------- 3. caméras Mapillary
class CameraMly(Camera):
    """Caméra Mapillary perspective / fisheye (OpenSfM) dans le repère du projet.
    `modele` reste « stenope » pour les fonctions existantes (photo à plat) ; f = focale normalisée ×
    max(W, H) (pixels) ; cam_vers_pixel / pixel_vers_cam appliquent la distorsion k1, k2."""

    def __init__(self, type_mly, W, H, pose, fn, k1=0.0, k2=0.0):
        S = float(max(W, H))
        super().__init__("stenope", int(W), int(H), pose, f=fn * S, cx=W / 2.0, cy=H / 2.0, k1=0.0)
        self.type_mly, self.fn, self.k1m, self.k2m, self.S = type_mly, float(fn), float(k1), float(k2), S

    def _distordre(self, x, y):
        if self.type_mly == "fisheye":
            r = np.hypot(x, y)
            th = np.arctan(r)
            d = 1.0 + self.k1m * th ** 2 + self.k2m * th ** 4
            s = np.where(r > 1e-12, th * d / np.maximum(r, 1e-12), 1.0)
            return x * s, y * s
        r2 = x * x + y * y
        d = 1.0 + self.k1m * r2 + self.k2m * r2 * r2
        return x * d, y * d

    def cam_vers_pixel(self, c):
        c = np.atleast_2d(c)
        d, a, h = c[:, 0], c[:, 1], c[:, 2]
        ok = a > 1e-6
        a_ = np.where(ok, a, 1.0)
        x, y = d / a_, -h / a_                       # OpenSfM : y vers le bas
        xd, yd = self._distordre(x, y)
        uv = np.c_[self.W / 2.0 + self.S * self.fn * xd, self.H / 2.0 + self.S * self.fn * yd]
        ok &= (uv[:, 0] >= 0) & (uv[:, 0] < self.W) & (uv[:, 1] >= 0) & (uv[:, 1] < self.H)
        if self.type_mly != "fisheye":
            # hors du domaine où la distorsion polynomiale est monotone : rejeté
            r2 = x * x + y * y
            ok &= (1.0 + 3 * self.k1m * r2 + 5 * self.k2m * r2 * r2) > 0.05
        return uv, ok

    def pixel_vers_cam(self, uv):
        uv = np.atleast_2d(np.asarray(uv, dtype=np.float64))
        xd = (uv[:, 0] - self.W / 2.0) / (self.S * self.fn)
        yd = (uv[:, 1] - self.H / 2.0) / (self.S * self.fn)
        if self.type_mly == "fisheye":
            rd = np.hypot(xd, yd)
            th = rd.copy()
            for _ in range(10):            # Newton sur θ (1 + k1 θ² + k2 θ⁴) = rd
                f = th * (1 + self.k1m * th ** 2 + self.k2m * th ** 4) - rd
                fp = 1 + 3 * self.k1m * th ** 2 + 5 * self.k2m * th ** 4
                th = th - f / np.where(np.abs(fp) > 1e-9, fp, 1e-9)
            r = np.tan(np.clip(th, 0, 1.55))
            s = np.where(rd > 1e-12, r / np.maximum(rd, 1e-12), 1.0)
            x, y = xd * s, yd * s
        else:
            x, y = xd.copy(), yd.copy()
            for _ in range(12):
                r2 = x * x + y * y
                g = 1.0 + self.k1m * r2 + self.k2m * r2 * r2
                x, y = xd / g, yd / g
        c = np.c_[x, np.ones_like(x), -y]
        return c / np.linalg.norm(c, axis=1, keepdims=True)


def rodrigues(r):
    r = np.asarray(r, float)
    th = float(np.linalg.norm(r))
    if th < 1e-12:
        return np.eye(3)
    k = r / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def euler_depuis_R(R):
    """(lacet, tangage, roulis) en degrés tels que camera.matrice_rotation(...) = R (lignes d, a, h)."""
    d2, a1 = R[0], R[1]
    th = math.asin(float(np.clip(a1[2], -1, 1)))
    ps = math.atan2(a1[0], a1[1])
    d0 = np.array([math.cos(ps), -math.sin(ps), 0.0])
    a0 = np.array([math.sin(ps), math.cos(ps), 0.0])
    h1 = -a0 * math.sin(th) + np.array([0.0, 0.0, 1.0]) * math.cos(th)
    ph = math.atan2(float(d2 @ h1), float(d2 @ d0))
    return math.degrees(ps) % 360.0, math.degrees(th), math.degrees(ph)


def R_projet_depuis_mly(rot, gamma_deg):
    """R du projet (lignes droite, avant, haut en coordonnées locales grille) depuis computed_rotation
    (R_cw OpenSfM, monde ENU) et la convergence des méridiens γ."""
    Rcw = rodrigues(rot)
    g = math.radians(gamma_deg)
    Rg = np.array([[math.cos(g), math.sin(g), 0.0], [-math.sin(g), math.cos(g), 0.0], [0.0, 0.0, 1.0]])
    M = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])      # (x, y, z) OpenSfM -> (d, a, h)
    return M @ Rcw @ Rg.T


# A priori de hauteur de l'objectif par auteur / type (m, écart type) ; calée ensuite si GCP.
HAUTEURS = {"sogefi": (2.5, 0.4), "spherical": (2.1, 0.4), "eric_s": (1.3, 0.4), "tartine78": (1.4, 0.4),
            "marcp": (1.4, 0.5)}
PORTEURS = {"sogefi": "véhicule de relevé (Sogefi), caméra perspective 2448×2048",
            "eric_s": "voiture, téléphone ou GoPro Max (mêmes prises que Panoramax pour 2020-2025)",
            "tartine78": "voiture ou vélo, téléphone", "marcp": "inconnu (téléphone)"}


class PhotoMly:
    """Équivalent minimal de camera.Photo pour les fonctions de gcp.py (date, is360, seq, id8, W, H)."""

    def __init__(self, im):
        self.im = im
        self.id = str(im["id"])
        self.id8 = "m" + self.id[-7:]
        self.datetime = im["date"]
        self.date = im["date"][:10]
        self.jpg = chemin_image(self.id)
        self.meta = {"projection": "equirectangular" if self.is360 else "perspective"}
        self._wh = None

    @property
    def is360(self):
        return self.im.get("camera_type") in ("spherical", "equirectangular")

    @property
    def W(self):
        return self.taille()[0]

    @property
    def H(self):
        return self.taille()[1]

    def taille(self):
        if self._wh is None:
            from PIL import Image
            with Image.open(self.jpg) as I:
                self._wh = I.size
        return self._wh

    @property
    def seq(self):
        h, sh = self.hauteur_a_priori()
        return dict(porteur=PORTEURS.get(self.auteur, "inconnu"), h=h, sh=sh,
                    lat_min=-25.0 if self.is360 else -89.0)

    @property
    def auteur(self):
        return (self.im.get("creator") or {}).get("username") or "?"

    def hauteur_a_priori(self):
        if self.is360:
            return HAUTEURS["spherical"]
        return HAUTEURS.get(self.auteur, (1.6, 0.6))


def camera_mly(ph, pose):
    """Caméra du projet pour l'image Mapillary ph (PhotoMly) à la pose [x, y, z, lacet, tangage, roulis]."""
    im = ph.im
    W, H = ph.taille()
    if ph.is360:
        return Camera("equirect", W, H, np.asarray(pose, float))
    cp = list(im.get("camera_parameters") or [])
    fn = float(cp[0]) if cp else 0.85
    k1 = float(cp[1]) if len(cp) > 1 else 0.0
    k2 = float(cp[2]) if len(cp) > 2 else 0.0
    return CameraMly(im.get("camera_type") or "perspective", W, H, pose, fn, k1, k2)


def pose_mly(ph):
    """Pose a priori du projet depuis le SfM Mapillary : dict(pose, sigma, source, gamma, ...)."""
    im = ph.im
    g = im.get("computed_geometry") or im.get("geometry")
    xy, gamma = gps_local(*g["coordinates"][:2])
    h, sh = ph.hauteur_a_priori()
    z = z_sol(float(xy[0]), float(xy[1])) + h
    if im.get("computed_rotation") is not None:
        R = R_projet_depuis_mly(im["computed_rotation"], gamma)
        lac, tan, rou = euler_depuis_R(R)
        src = "computed_rotation"
        sig_ang = (2.0, 2.0, 2.0)
    else:
        az = im.get("computed_compass_angle", im.get("compass_angle")) or 0.0
        lac, tan, rou = (float(az) + gamma) % 360.0, 0.0, 0.0
        src = "computed_compass_angle" if im.get("computed_compass_angle") is not None else "compass_angle"
        sig_ang = (8.0, 6.0, 4.0)
    sig_xy = 2.0 if im.get("computed_geometry") else 6.0
    return dict(pose=np.array([xy[0], xy[1], z, lac, tan, rou]), gamma=gamma, h_a_priori=h,
                sigma=dict(xy=sig_xy, z=sh, lacet=sig_ang[0], tangage=sig_ang[1], roulis=sig_ang[2]),
                source_orientation=src, source_position=im.get("geometrie_source"))


@functools.lru_cache(maxsize=1)
def images_par_id():
    return {im["id"]: im for im in inventaire()["images"]}


def photo_mly(iid):
    return PhotoMly(images_par_id()[str(iid)])


@functools.lru_cache(maxsize=2)
def image_rgb_mly(iid):
    from PIL import Image
    return np.asarray(Image.open(chemin_image(iid)).convert("RGB"))


def image_gris_mly(iid):
    a = image_rgb_mly(iid).astype(np.float32)
    return (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0


# --------------------------------------------------------------------------- 3 bis. calage (GCP)
POSES = SORTIE / "poses"


def intrinseques_mly(ph):
    W, H = ph.taille()
    if ph.is360:
        return dict(modele="equirect", W=W, H=H, f=0.0, cx=0.0, cy=0.0, k1=0.0,
                    source="Mapillary spherical (équirectangulaire)")
    cp = list(ph.im.get("camera_parameters") or [0.85])
    fn = float(cp[0])
    return dict(modele="stenope", W=W, H=H, f=fn * max(W, H), cx=W / 2.0, cy=H / 2.0, k1=0.0,
                source=f"Mapillary {ph.im.get('camera_type')} [f, k1, k2] = {cp} (SfM, normalisés par max(W, H))")


_camera_origine = None


def _brancher_poses():
    """Les fonctions de poses.py construisent la caméra par `poses.camera(ph, pose, intr)` : dans ce
    processus seulement, les PhotoMly y reçoivent leur CameraMly (les photos Panoramax gardent la leur)."""
    global _camera_origine
    import poses as PO
    if _camera_origine is None:
        _camera_origine = PO.camera

        def cam(ph, pose=None, intr=None):
            if isinstance(ph, PhotoMly):
                return camera_mly(ph, pose_mly(ph)["pose"] if pose is None else pose)
            return _camera_origine(ph, pose, intr)
        PO.camera = cam
    return PO


@functools.lru_cache(maxsize=1)
def poses_panoramax_par_instant():
    """Photos Panoramax calées acceptées, indexées par instant de prise de vue (s UTC)."""
    from camera import catalogue, charger_poses
    import datetime as dt
    out = []
    P = charger_poses()
    for id8, ph in catalogue().items():
        r = P.get(id8)
        if r and r.get("accepte") and r.get("pose"):
            t = dt.datetime.fromisoformat(ph.datetime.replace("Z", "+00:00")).timestamp()
            out.append((t, id8, r))
    return out


def pose_panoramax_equivalente(ph, tol_s=1.0):
    """Même prise de vue publiée sur Panoramax et calée (sphériques 2024-08 / 2025-05) : (id8, record)."""
    if not ph.is360:
        return None
    t = ph.im["captured_at"] / 1000.0
    c = [(abs(tp - t), id8, r) for tp, id8, r in poses_panoramax_par_instant() if abs(tp - t) <= tol_s]
    if not c:
        return None
    c.sort(key=lambda x: (x[0], x[1]))
    # garde-fou : même position (< 4 m) et même cap (< 5°) que le SfM Mapillary
    p = pose_mly(ph)["pose"]
    q = c[0][2]["pose"]
    if np.hypot(p[0] - q["x"], p[1] - q["y"]) > 4.0 or abs((p[3] - q["lacet"] + 180) % 360 - 180) > 5.0:
        return None
    return c[0][1], c[0][2]


def caler_mly(iid, verbeux=True, decalages_long=(0.0,), a_priori=None):
    """Calage d'une image Mapillary : a priori SfM Mapillary, vote en espace de pose (mâts + sol),
    trois passes pointer/ajuster (RANSAC + LM robuste, poses.py), qualité et acceptation de poses.py.
    Une sphérique déjà calée sur Panoramax (même prise de vue) reprend cette pose."""
    PO = _brancher_poses()
    import gcp as G
    t0 = time.time()
    ph = photo_mly(iid)
    pm = pose_mly(ph)
    intr = intrinseques_mly(ph)
    p0 = pm["pose"].copy()
    rec = dict(id=ph.id, id8=ph.id8, date=ph.date, datetime=ph.datetime, sequence=ph.im.get("sequence"),
               camera_type=ph.im.get("camera_type"), auteur=ph.auteur, porteur=ph.seq["porteur"],
               fichier=ph.jpg.name, modele=intr["modele"], W=intr["W"], H=intr["H"],
               camera_parameters=ph.im.get("camera_parameters"), intrinseques=arrondi(intr, 4),
               pose_mapillary=PO._pose_dict(p0), sigma_a_priori=pm["sigma"],
               source_orientation=pm["source_orientation"], source_position=pm["source_position"],
               gamma_deg=round(pm["gamma"], 5), h_a_priori=pm["h_a_priori"], attribution=ph.im["attribution"])
    eq = pose_panoramax_equivalente(ph)
    if eq is not None:
        id8, r = eq
        q = r["pose"]
        p = np.array([q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]])
        rec.update(pose=PO._pose_dict(p), accepte=True, raison="ok", methode="pose Panoramax calée (même prise de vue)",
                   panoramax=id8, qualite=r.get("qualite"), ecart_type=r.get("ecart_type"),
                   ecart_mapillary=dict(d_xy_m=round(float(np.hypot(*(p[:2] - p0[:2]))), 3),
                                        d_lacet_deg=round(float((p[3] - p0[3] + 180) % 360 - 180), 3),
                                        d_tangage_deg=round(float(p[4] - p0[4]), 3),
                                        d_roulis_deg=round(float(p[5] - p0[5]), 3)),
                   duree_s=round(time.time() - t0, 1))
        _ecrire_pose(rec)
        return rec
    ph.meta["horizontal_accuracy_m"] = pm["sigma"]["xy"]
    img = image_gris_mly(ph.id)
    img_flou = G._flou_boite(img, 2)
    sigma = dict(pm["sigma"])
    gidx = {}
    graine = int(ph.id[-8:]) % (2 ** 31)
    if a_priori is not None:                      # a priori de séquence (retard GNSS estimé)
        rec["a_priori_sequence"] = arrondi(dict(a_priori, pose=PO._pose_dict(a_priori["pose"])), 4)
        p0 = np.asarray(a_priori["pose"], float).copy()
        sigma.update(a_priori.get("sigma", {}))
    av = np.array([math.sin(math.radians(p0[3])), math.cos(math.radians(p0[3]))])
    departs = []
    for dl in decalages_long:
        q = p0.copy()
        q[:2] += dl * av
        departs.append((f"long{dl:+.0f}", q))
    best, journal = None, []
    for nom, q in departs:
        q = PO.voter(ph, intr, q, img, img_flou, sigma, verbeux, nom, t0)
        cfg = dict(fen=lambda g, c: 1.5, rech=24 if ph.is360 else 30, ech=0.5 if ph.is360 else 0.5, ransac=True)
        r = PO.passe(ph, intr, p0, sigma, q, img, img_flou, gidx, cfg, graine, False)
        if r is None:
            journal.append(dict(depart=nom, n_obs=0))
            continue
        journal.append(dict(depart=nom, n_obs=len(r["obs"]), n_inliers=r["n_inl"], score=round(r["score"], 2),
                            moy_deg=round(r["moy"], 3)))
        if best is None or r["score"] > best["score"]:
            best = dict(r, depart=nom)
    rec["departs"] = journal
    px_deg = (camera_mly(ph, p0).px_par_rad) * math.pi / 180
    if best is not None:
        for k in range(3):
            m = best["moy"]
            fen = float(np.clip(3 * m, 0.5, 1.5))
            rech = int(np.clip(3 * m * px_deg, 6, 30))
            cfg = dict(fen=lambda g, c, fen=fen: fen, rech=rech, ech=1.0, ransac=k == 0)
            r = PO.passe(ph, intr, p0, sigma, best["p"], img, img_flou, gidx, cfg, graine + k + 1, False)
            if r is None:
                break
            if verbeux:
                print(f"[{ph.id}] passe {k + 1}: {len(r['obs'])} obs, {r['n_inl']} inl, score {r['score']:.1f}, "
                      f"moy {r['moy']:.3f}° ({time.time() - t0:.0f} s)", flush=True)
            if r["score"] >= 0.9 * best["score"]:
                best = dict(r, depart=best["depart"])
            else:
                break
    if best is None or not best["inl"].any():
        rec.update(accepte=False, raison="pas assez d'observations", pose=None, methode="GCP",
                   duree_s=round(time.time() - t0, 1))
        _ecrire_pose(rec)
        return rec
    rec.update(PO._qualite(ph, best["aj"], best["p"], best["inl"], p0, intr, gidx))
    rec["methode"] = "GCP (vote + RANSAC + LM, poses.py) depuis le SfM Mapillary"
    p, pmy = best["p"], pm["pose"]
    av = np.array([math.sin(math.radians(pmy[3])), math.cos(math.radians(pmy[3]))])
    rec["ecart_mapillary"] = dict(d_xy_m=round(float(np.hypot(*(p[:2] - pmy[:2]))), 3),
                                  d_long_m=round(float((p[:2] - pmy[:2]) @ av), 3),
                                  d_trans_m=round(float((p[:2] - pmy[:2]) @ np.array([av[1], -av[0]])), 3),
                                  d_lacet_deg=round(float((p[3] - pmy[3] + 180) % 360 - 180), 3),
                                  d_tangage_deg=round(float(p[4] - pmy[4]), 3), d_roulis_deg=round(float(p[5] - pmy[5]), 3),
                                  d_z_m=round(float(p[2] - pmy[2]), 3))
    rec["duree_s"] = round(time.time() - t0, 1)
    if verbeux:
        q = rec["qualite"]
        print(f"[{ph.id}] => accepte={rec['accepte']} ({rec['raison']}) n_gcp={q['n_gcp']} (mâts {q['n_mats']}, "
              f"sol {q['n_sol']}) moy={q['residu_moy_deg']}° px={q['residu_moy_px']} "
              f"d_mly={rec['ecart_mapillary']} ({rec['duree_s']} s)", flush=True)
    _ecrire_pose(rec)
    return rec


def _ecrire_pose(rec):
    ecrire_json(POSES / "par_image" / f"{rec['id']}.json", arrondi(rec, 4))


def poses_toutes(ids=None, part=None):
    sel = [s["id"] for s in lire_json(BRUT / "selection.json")["images"]]
    ids = [i for i in (ids or sel) if chemin_image(i).exists()]
    ids = sorted(ids)
    if part:
        k, n = (int(x) for x in part.split("/"))
        ids = ids[k::n]
    for iid in ids:
        if (POSES / "par_image" / f"{iid}.json").exists():
            continue
        try:
            caler_mly(iid)
        except Exception as e:  # noqa: BLE001
            print(f"[{iid}] ERREUR {type(e).__name__}: {e}", flush=True)
            _ecrire_pose(dict(id=iid, accepte=False, raison=f"erreur {type(e).__name__}: {str(e)[:200]}", pose=None))


@functools.lru_cache(maxsize=1)
def poses_calees():
    f = POSES / "poses_mapillary.json"
    if not f.exists():
        return {}
    return {r["id"]: r for r in lire_json(f)["images"]}


# --------------------------------------------------------------------------- couches de référence
DESC = RACINE / "recon/out/paquet_jardin/v2/description"


def _anneaux(g):
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    if g["type"] == "MultiPolygon":
        return [p[0] for p in g["coordinates"]]
    return []


@functools.lru_cache(maxsize=1)
def couches_reference():
    """Éléments 3D (repère local) pour les superpositions : mâts levés (catalogue GCP), bordures v0.3
    (arête de référence 3D, travaux 2025 ou non), emprises bâties (pied et égout), marquages v0.3.
    Liste de dict(id, couche, pts (N, 3), ferme, valide_de, valide_a)."""
    import gcp as G
    out = []
    for g in G.catalogue_gcp():
        if g["famille"] == "mat":
            out.append(dict(id=g["id"], couche="mat", pts=np.array([g["pied"], g["sommet"]]), ferme=False,
                            valide_de=g["valide_de"], valide_a=g["valide_a"]))
    for f in lire_json(DESC / "base/bordures.geojson")["features"]:
        p, g = f["properties"], f["geometry"]
        lignes = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"] if g["type"] == "MultiLineString" else []
        for L in lignes:
            A = np.asarray(L, float)
            if A.shape[1] < 3:
                continue
            A = A - np.array(O)
            t25 = bool(p.get("zone_travaux_2025"))
            out.append(dict(id=p["id"], couche="bordure_2025" if t25 else "bordure", pts=A, ferme=False,
                            valide_de="2025-12-05" if t25 else "2000-01-01", valide_a="2100-01-01"))
    for f in lire_json(RACINE / "recon/out/paquet_jardin/package/donnees/objets/batiments_local.geojson")["features"]:
        p = f["properties"]
        z0 = float(p.get("z_sol_local") if p.get("z_sol_local") is not None else (p.get("z_sol_ngf", O[2]) - O[2]))
        he = float(p.get("hauteur_egout_m") or 3.0)
        for r in _anneaux(f["geometry"]):
            r = np.asarray(r, float)[:, :2]
            for k, z in enumerate((z0, z0 + he)):
                out.append(dict(id=f"BAT-{str(p.get('cleabs') or p.get('osm_id') or '?')[-6:]}-{k}", couche="batiment",
                                pts=np.c_[r, np.full(len(r), z)], ferme=True, valide_de="2000-01-01",
                                valide_a="2100-01-01"))
    for f in lire_json(DESC / "base/marquages.geojson")["features"]:
        p = f["properties"]
        for r in _anneaux(f["geometry"]):
            r = np.asarray(r, float)[:, :2] - np.array(O[:2])
            z = np.array([z_sol(*q) + 0.01 for q in r])
            neuf = p.get("etat") in ("neuf_2025", "refait_2025_identique")
            out.append(dict(id=p["id"], couche="marquage_2025" if neuf else "marquage", pts=np.c_[r, z], ferme=True,
                            valide_de="2025-12-05" if neuf else "2000-01-01", valide_a="2100-01-01"))
    return out


COULEURS = {"mat": (0, 255, 255), "bordure": (255, 230, 0), "bordure_2025": (255, 60, 60),
            "batiment": (255, 140, 0), "marquage": (255, 0, 255), "marquage_2025": (160, 60, 255),
            "entite": (0, 255, 0), "obs": (0, 255, 0)}


def densifier3(P, pas=0.3, ferme=False):
    P = np.asarray(P, float)
    if ferme and len(P) > 2 and np.linalg.norm(P[0] - P[-1]) > 1e-6:
        P = np.vstack([P, P[:1]])
    out = [P[:1]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b - a) / pas)))
        out.append(a + (b - a) * (np.arange(1, n + 1) / n)[:, None])
    return np.vstack(out)


def tracer_polyligne(dr, cam, P, couleur, larg=2, dmax=70.0, echelle=1.0, ferme=False, pas=0.3):
    """Trace une polyligne 3D projetée (morceaux visibles seulement). Renvoie le nombre de points tracés."""
    Q = densifier3(P, pas, ferme)
    uv, ok, dist = cam.projeter(Q)
    ok &= dist <= dmax
    n = 0
    for k in range(len(Q) - 1):
        if ok[k] and ok[k + 1]:
            a, b = uv[k] * echelle, uv[k + 1] * echelle
            if cam.modele == "equirect" and abs(a[0] - b[0]) > cam.W * echelle / 2:
                continue
            dr.line([tuple(a), tuple(b)], fill=couleur, width=larg)
            n += 1
    return n


def superposition(ph, cam, couches=("mat", "bordure", "bordure_2025", "batiment", "marquage"), largeur=1600,
                  dmax=70.0, etiquettes=True, extra=None):
    """Image (PIL) de la photo avec les éléments de référence valides à sa date projetés."""
    from PIL import Image, ImageDraw
    img = Image.fromarray(image_rgb_mly(ph.id))
    e = largeur / img.size[0]
    img = img.resize((largeur, int(round(img.size[1] * e))), Image.BILINEAR)
    dr = ImageDraw.Draw(img)
    for el in couches_reference():
        if el["couche"] not in couches:
            continue
        if not (el["valide_de"] <= ph.date <= el["valide_a"]) and el["couche"] != "bordure_2025":
            continue
        n = tracer_polyligne(dr, cam, el["pts"], COULEURS[el["couche"]], 2 if el["couche"] != "mat" else 3,
                             dmax=dmax, echelle=e, ferme=el["ferme"])
        if n and etiquettes and el["couche"] == "mat":
            uv, ok, dist = cam.projeter(el["pts"][1:2])
            if ok[0] and dist[0] <= dmax:
                dr.text(tuple(uv[0] * e + np.array([3, -12])), el["id"][4:22], fill=(0, 255, 255))
    for it in (extra or []):
        tracer_polyligne(dr, cam, it["pts"], it.get("couleur", (0, 255, 0)), it.get("larg", 3), dmax=dmax,
                         echelle=e, ferme=it.get("ferme", False))
        if it.get("texte"):
            uv, ok, dist = cam.projeter(np.atleast_2d(it["pts"])[:1])
            if ok[0]:
                dr.text(tuple(uv[0] * e + np.array([3, 3])), it["texte"], fill=it.get("couleur", (0, 255, 0)))
    return img


# --------------------------------------------------------------------------- 3 ter. recalage sur les bordures
# Les GCP de poses.py (mâts LiDAR, coins de zébras, texture de l'ortho 2022) sont rares ou peu
# corrélables sur des vignettes 2048 px de téléphone (contre-jour, ombres) et le GNSS des téléphones
# retarde de ~1 s (jusqu'à 10 m le long de la marche). Les bordures levées par le GAM (σ 5 cm, arête
# avant 3D) hors travaux 2025 sont, elles, visibles à toutes les dates : la pose est recalée en
# maximisant le contraste de l'image perpendiculairement aux bordures projetées (tenseur de structure
# lissé, deux échelles). Une séquence entière vote d'abord pour un retard τ et une translation Δ
# (le SfM Mapillary est cohérent à l'intérieur d'une séquence), puis chaque image est affinée
# localement. Contrôle indépendant : les mâts LiDAR (non utilisés ici) pointés à la pose finale.

def _tenseur(img, r):
    import gcp as G
    a = G._flou_boite(img, 1)
    gy, gx = np.gradient(a)
    jxx = G._flou_boite(gx * gx, r)
    jxy = G._flou_boite(gx * gy, r)
    jyy = G._flou_boite(gy * gy, r)
    return np.stack([jxx, jxy, jyy]).astype(np.float32)


class AttacheBordures:
    """Score d'alignement des bordures projetées pour une image (deux échelles de lissage)."""

    def __init__(self, ph, img, C0, dmax=40.0, dmin=2.5, pas=0.25, echelles=(8, 2)):
        self.ph = ph
        self.J = {r: _tenseur(img, r) for r in echelles}
        self.norm = {}
        for r, J in self.J.items():
            tr = np.sqrt(np.maximum(J[0] + J[2], 0))
            self.norm[r] = float(np.percentile(tr, 90)) + 1e-6
        P, T = points_bordures(ph.date, C0, dmax=dmax + 6.0, pas=pas)
        d = np.hypot(P[:, 0] - C0[0], P[:, 1] - C0[1]) if len(P) else np.zeros(0)
        m = (d >= dmin) & (d <= dmax)
        self.P, self.T = P[m], T[m]

    def score(self, cam, r, detail=False, dmin=3.0, dmax=30.0):
        """Contraste moyen perpendiculaire aux bordures projetées, pondéré par la proximité (w = 15/d
        borné à [0,3 ; 2]) et rapporté à TOUS les points à dmin–dmax de la caméra (un point hors champ
        compte 0 : pas de prime à la fuite hors de l'image)."""
        vide = (0.0, 0) if not detail else (0.0, 0, None)
        if len(self.P) == 0:
            return vide
        dh = np.hypot(self.P[:, 0] - cam.C[0], self.P[:, 1] - cam.C[1])
        m = (dh >= dmin) & (dh <= dmax)
        if m.sum() < 10:
            return vide
        P, T, w = self.P[m], self.T[m], np.clip(15.0 / dh[m], 0.3, 2.0)
        uv, ok, dist = cam.projeter(P)
        uv2, ok2, _ = cam.projeter(P + 0.15 * T)
        ok &= ok2
        if self.ph.is360:
            ok &= np.degrees(np.arcsin(np.clip(cam.pixel_vers_cam(uv)[:, 2], -1, 1))) > self.ph.seq["lat_min"] + 2
        n = np.c_[-(uv2[:, 1] - uv[:, 1]), uv2[:, 0] - uv[:, 0]]
        nn = np.linalg.norm(n, axis=1)
        ok &= nn > 1e-3
        if not ok.any():
            return vide
        n = n[ok] / nn[ok, None]
        J = self.J[r]
        H, W = J.shape[1:]
        u = np.clip(uv[ok, 0].astype(int), 0, W - 1)
        v = np.clip(uv[ok, 1].astype(int), 0, H - 1)
        jxx, jxy, jyy = J[0, v, u], J[1, v, u], J[2, v, u]
        resp = np.sqrt(np.maximum(n[:, 0] ** 2 * jxx + 2 * n[:, 0] * n[:, 1] * jxy + n[:, 1] ** 2 * jyy, 0))
        resp = np.minimum(resp / self.norm[r], 1.5)
        s = float((resp * w[ok]).sum() / w.sum())
        if detail:
            return s, int(ok.sum()), resp
        return s, int(ok.sum())


@functools.lru_cache(maxsize=1)
def _bordures_3d():
    """Bordures v0.3 (arête de référence 3D locale) : liste de (id, A (N, 3), travaux_2025)."""
    out = []
    for f in lire_json(DESC / "base/bordures.geojson")["features"]:
        p, g = f["properties"], f["geometry"]
        lignes = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"] if g["type"] == "MultiLineString" else []
        for L in lignes:
            A = np.asarray(L, float)
            if A.ndim == 2 and A.shape[1] >= 3 and len(A) >= 2:
                out.append((p["id"], A[:, :3] - np.array(O), bool(p.get("zone_travaux_2025"))))
    return out


def points_bordures(date, C0, dmax=46.0, pas=0.25):
    """Points (N, 3) et tangentes (N, 3) des bordures existant à `date` (hors travaux 2025 ; hors
    surfaces construites en 2023-2024 pour les images antérieures à 2024) à moins de dmax de C0."""
    import gcp as G
    c23, m25 = G._zones_changees()
    P, T = [], []
    for eid, A, t25 in _bordures_3d():
        if t25:
            continue
        lo, hi = A[:, :2].min(0), A[:, :2].max(0)
        if (np.maximum(lo - C0[:2], C0[:2] - hi).clip(0) ** 2).sum() > dmax ** 2:
            continue
        Q = densifier3(A, pas)
        Tq = np.gradient(Q, axis=0)
        Tq /= np.maximum(np.linalg.norm(Tq, axis=1, keepdims=True), 1e-9)
        m = np.hypot(Q[:, 0] - C0[0], Q[:, 1] - C0[1]) <= dmax
        if date < "2024-01-01":
            m &= ~G._dans(Q[:, :2], c23)
        if date < "2025-12-05":
            m &= ~G._dans(Q[:, :2], m25)
        if m.any():
            P.append(Q[m])
            T.append(Tq[m])
    if not P:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.vstack(P), np.vstack(T)


def _vitesses(seq_ims):
    """Vitesse horizontale (m/s, vecteur local) de chaque image de la séquence (SfM Mapillary)."""
    X = [pose_mly(PhotoMly(im))["pose"][:2] for im in seq_ims]
    t = [im["captured_at"] / 1000.0 for im in seq_ims]
    V = []
    for k in range(len(seq_ims)):
        a, b = max(k - 1, 0), min(k + 1, len(seq_ims) - 1)
        dt = t[b] - t[a]
        V.append((X[b] - X[a]) / dt if dt > 0 and b != a else np.zeros(2))
    return np.array(V)


def pose_decalee(p, v, tau, dx, dy, dlac=0.0, dz=0.0, dtan=0.0, drou=0.0):
    q = np.array(p, float).copy()
    q[0] += tau * v[0] + dx
    q[1] += tau * v[1] + dy
    q[2] += dz
    q[3] = (q[3] + dlac) % 360.0
    q[4] += dtan
    q[5] += drou
    return q


def recaler_sequence(seq_id, ids=None, verbeux=True, tau_max=2.0, dmax_xy=2.5):
    """Modèle « retard GNSS » d'une séquence : position = SfM + τ·v(t) + Δ (Δ borné à ±dmax_xy : les
    bordures parallèles d'une voie rendent la translation transversale ambiguë au-delà), lacet + Δψ.
    τ, Δ, Δψ maximisent l'alignement moyen des bordures sur toutes les images ; profil de τ conservé
    (distinction du pic). Puis affinage image par image. Écrit recalage_bordures/<séquence>.json."""
    inv = images_par_id()
    seq_all = sorted([im for im in inv.values() if im["sequence"] == seq_id], key=lambda im: im["captured_at"])
    V = dict(zip([im["id"] for im in seq_all], _vitesses(seq_all)))
    sel = set(ids) if ids else {s["id"] for s in lire_json(BRUT / "selection.json")["images"]}
    ims = [im for im in seq_all if im["id"] in sel and chemin_image(im["id"]).exists()]
    t0 = time.time()
    data = []
    for im in ims:
        ph = PhotoMly(im)
        p0 = pose_mly(ph)["pose"]
        v = V[im["id"]]
        att = AttacheBordures(ph, image_gris_mly(im["id"]), p0[:3], dmax=32.0 + tau_max * float(np.hypot(*v)))
        if len(att.P) < 40:
            continue
        data.append((ph, p0, v, att))
    res = {"sequence": seq_id, "modele": "retard GNSS", "n_images": len(ims), "n_utilisees": len(data)}
    if verbeux:
        print(f"[{seq_id[:8]}] {len(data)}/{len(ims)} images avec bordures ({time.time() - t0:.0f} s)", flush=True)
    if not data:
        return res

    def total(tau, dx, dy, dlac, r):
        return float(np.mean([att.score(camera_mly(ph, pose_decalee(p0, v, tau, dx, dy, dlac)), r)[0]
                              for ph, p0, v, att in data]))

    s_prior = total(0, 0, 0, 0, 8)
    best = (-1.0, 0.0, 0.0, 0.0, 0.0)
    prof = {}
    for tau in np.arange(-tau_max, tau_max + 1e-9, 0.1):
        bt = -1.0
        for dx in np.arange(-dmax_xy, dmax_xy + 1e-9, 0.5):
            for dy in np.arange(-dmax_xy, dmax_xy + 1e-9, 0.5):
                sc = total(tau, dx, dy, 0.0, 8)
                bt = max(bt, sc)
                if sc > best[0]:
                    best = (sc, tau, dx, dy, 0.0)
        prof[round(float(tau), 2)] = round(bt, 4)
    _, tau, dx, dy, dlac = best
    for pas, rt, rr, rl, pl in ((0.25, 0.2, 0.5, 2.0, 0.5), (0.1, 0.05, 0.2, 0.5, 0.1)):
        b2 = (-1.0, tau, dx, dy, dlac)
        for dt_ in np.arange(-rt, rt + 1e-9, rt / 2):
            for ddx in np.arange(-rr, rr + 1e-9, pas):
                for ddy in np.arange(-rr, rr + 1e-9, pas):
                    for dl in np.arange(-rl, rl + 1e-9, pl):
                        sc = total(tau + dt_, dx + ddx, dy + ddy, dlac + dl, 8)
                        if sc > b2[0]:
                            b2 = (sc, tau + dt_, dx + ddx, dy + ddy, dlac + dl)
        _, tau, dx, dy, dlac = b2
    v = np.array(list(prof.values()))
    s_s = total(tau, dx, dy, dlac, 8)
    res.update(tau_s=round(float(tau), 3), dx_m=round(float(dx), 3), dy_m=round(float(dy), 3),
               dlacet_deg=round(float(dlac), 3), score_a_priori=round(s_prior, 4), score_sequence=round(s_s, 4),
               distinction_tau=round(float((v.max() - np.median(v)) / (np.median(np.abs(v - np.median(v))) + 1e-9)), 2),
               profil_tau=prof)
    if verbeux:
        print(f"[{seq_id[:8]}] τ={tau:+.2f} s Δ=({dx:+.2f}, {dy:+.2f}) m Δψ={dlac:+.2f}° score {s_prior:.3f} -> "
              f"{s_s:.3f} distinction τ {res['distinction_tau']} ({time.time() - t0:.0f} s)", flush=True)
    res["images"] = [affiner_image(ph, pose_decalee(p0, v, tau, dx, dy, dlac), att, p0) for ph, p0, v, att in data]
    ecrire_json(SORTIE / "poses/recalage_bordures" / f"{seq_id}.json", arrondi(res, 4))
    return res


def affiner_image(ph, q, att, p_mly, R1=1.5, Y1=2.0):
    """Recherche locale par blocs (x, y, lacet) puis (z, tangage, roulis), lissage 8 px puis 2 px.
    Distinction : score au pic rapporté à la médiane/MAD des scores de la grille (x, y).
    `borne` : la solution touche le bord du domaine de recherche (non fiable)."""
    p = np.array(q, float)
    q = np.array(q, float)
    s_dep = att.score(camera_mly(ph, p), 2)[0]
    stats = {}
    for r, R, pas, Y, py in ((8, R1, 0.25, Y1, 0.5), (2, 0.5, 0.1, 0.6, 0.15), (2, 0.2, 0.05, 0.2, 0.05)):
        best = (-1.0, None)
        tous = []
        for ddx in np.arange(-R, R + 1e-9, pas):
            for ddy in np.arange(-R, R + 1e-9, pas):
                for dl in np.arange(-Y, Y + 1e-9, py):
                    c = pose_decalee(p, (0, 0), 0, ddx, ddy, dl)
                    s = att.score(camera_mly(ph, c), r)[0]
                    tous.append(s)
                    if s > best[0]:
                        best = (s, c)
        p = best[1]
        tous = np.array(tous)
        stats[r] = (best[0], float(np.median(tous)), float(np.median(np.abs(tous - np.median(tous)))) + 1e-6)
        best = (-1.0, None)
        for dz in np.arange(-0.3, 0.31, 0.15 if r == 8 else 0.05):
            for dt in np.arange(-1.5, 1.51, 0.5 if r == 8 else 0.15):
                for dr in np.arange(-1.5, 1.51, 0.5 if r == 8 else 0.15):
                    c = pose_decalee(p, (0, 0), 0, 0, 0, 0, dz, dt, dr)
                    s = att.score(camera_mly(ph, c), r)[0]
                    if s > best[0]:
                        best = (s, c)
        p = best[1]
    s_fin, n_vis, resp = att.score(camera_mly(ph, p), 2, detail=True)
    s8 = stats[8]
    distinction = (s8[0] - s8[1]) / s8[2]
    dq = p - q
    borne = bool(max(abs(dq[0]), abs(dq[1])) >= R1 + 0.65 or abs((dq[3] + 180) % 360 - 180) >= Y1 + 0.75
                 or abs(dq[4]) >= 2.0 or abs(dq[5]) >= 2.0 or abs(dq[2]) >= 0.85)
    av = np.array([math.sin(math.radians(p_mly[3])), math.cos(math.radians(p_mly[3]))])
    d = p[:2] - p_mly[:2]
    return dict(id=ph.id, date=ph.date, pose=dict(zip(("x", "y", "z", "lacet", "tangage", "roulis"),
                                                     [round(float(x), 4) for x in p])),
                score_depart=round(s_dep, 4), score=round(s_fin, 4), n_points=int(len(att.P)), n_visibles=n_vis,
                part_contrastee=round(float(np.mean(resp > 0.35)) if resp is not None else 0.0, 3),
                distinction=round(float(distinction), 2), borne=borne,
                ecart_depart=dict(dx=round(float(dq[0]), 3), dy=round(float(dq[1]), 3), dz=round(float(dq[2]), 3),
                                  dlacet=round(float((dq[3] + 180) % 360 - 180), 3), dtangage=round(float(dq[4]), 3),
                                  droulis=round(float(dq[5]), 3)),
                ecart_mapillary=dict(d_long_m=round(float(d @ av), 3), d_trans_m=round(float(d @ [av[1], -av[0]]), 3),
                                     d_lacet_deg=round(float((p[3] - p_mly[3] + 180) % 360 - 180), 3),
                                     d_tangage_deg=round(float(p[4] - p_mly[4]), 3),
                                     d_roulis_deg=round(float(p[5] - p_mly[5]), 3), d_z_m=round(float(p[2] - p_mly[2]), 3)))


def recaler_image(iid, R1=2.0, Y1=2.0, depart=None):
    """Recalage sur les bordures d'une image seule (depuis le SfM Mapillary ou `depart`)."""
    ph = photo_mly(iid)
    p_mly = pose_mly(ph)["pose"]
    q = p_mly if depart is None else np.asarray(depart, float)
    att = AttacheBordures(ph, image_gris_mly(iid), q[:3], dmax=32.0 + R1)
    if len(att.P) < 40:
        r = dict(id=ph.id, date=ph.date, pose=None, n_points=int(len(att.P)), raison="trop peu de bordures")
    else:
        r = affiner_image(ph, q, att, p_mly, R1=R1, Y1=Y1)
    ecrire_json(SORTIE / "poses/recalage_bordures/images" / f"{iid}.json", arrondi(r, 4))
    return r


# Acceptation d'un recalage sur les bordures (seuils réglés sur les planches de validation)
BORD_DISTINCTION_MIN = 2.5
BORD_SCORE_MIN = 0.20
BORD_VISIBLES_MIN = 80
BORD_CONTRASTE_MIN = 0.40


def accepte_bordures(r):
    if not r or not r.get("pose"):
        return False, "pas de recalage"
    why = []
    if r.get("borne"):
        why.append("solution au bord du domaine")
    if r.get("distinction", 0) < BORD_DISTINCTION_MIN:
        why.append("pic peu distinct")
    if r.get("score", 0) < BORD_SCORE_MIN:
        why.append("contraste faible")
    if r.get("n_visibles", 0) < BORD_VISIBLES_MIN:
        why.append("trop peu de bordures visibles")
    if r.get("part_contrastee", 0) < BORD_CONTRASTE_MIN:
        why.append("bordures projetées hors des contours")
    return (not why), ("ok" if not why else " ; ".join(why))


def taches_recalage():
    """Liste déterministe des tâches de recalage sur les bordures : ('sequence', id) pour les séquences
    perspective motorisées (vitesse médiane > 3 m/s : modèle de retard GNSS), ('image', id) sinon
    (sphériques non calées par GCP, piétons)."""
    sel = [s for s in lire_json(BRUT / "selection.json")["images"] if chemin_image(s["id"]).exists()]
    inv = images_par_id()
    par_seq = {}
    for s_ in sel:
        par_seq.setdefault(s_["sequence"], []).append(s_["id"])
    taches = []
    for seq, ids in sorted(par_seq.items()):
        ims = sorted([im for im in inv.values() if im["sequence"] == seq], key=lambda im: im["captured_at"])
        v = float(np.median(np.hypot(*_vitesses(ims).T))) if len(ims) > 1 else 0.0
        if inv[ids[0]]["camera_type"] in ("spherical", "equirectangular"):
            for iid in sorted(ids):
                r = POSES / "par_image" / f"{iid}.json"
                if r.exists() and lire_json(r).get("accepte"):
                    continue
                taches.append(("image", iid, 2.0))
        elif v > 3.0:
            taches.append(("sequence", seq, 0.0))
        else:
            for iid in sorted(ids):
                taches.append(("image", iid, 3.0))
    return taches


def recaler_tout(part=None):
    taches = taches_recalage()
    if part:
        k, n = (int(x) for x in part.split("/"))
        taches = taches[k::n]
    for genre, cle, R1 in taches:
        try:
            if genre == "sequence":
                if not (SORTIE / "poses/recalage_bordures" / f"{cle}.json").exists():
                    recaler_sequence(cle)
            else:
                if not (SORTIE / "poses/recalage_bordures/images" / f"{cle}.json").exists():
                    r = recaler_image(cle, R1=R1, Y1=2.0)
                    print(f"[{cle}] bordures : {accepte_bordures(r)} score {r.get('score')} distinction "
                          f"{r.get('distinction')}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[{cle}] ERREUR {type(e).__name__}: {e}", flush=True)


# --------------------------------------------------------------------------- 3 quater. poses finales
def _rec_bordures(iid, seq):
    f = SORTIE / "poses/recalage_bordures/images" / f"{iid}.json"
    if f.exists():
        return lire_json(f)
    f = SORTIE / "poses/recalage_bordures" / f"{seq}.json"
    if f.exists():
        d = lire_json(f)
        r = next((x for x in d.get("images", []) if x["id"] == iid), None)
        if r is not None:
            return dict(r, sequence_modele={k: d.get(k) for k in ("tau_s", "dx_m", "dy_m", "dlacet_deg",
                                                                  "distinction_tau", "score_a_priori",
                                                                  "score_sequence")})
    return None


def assembler_poses():
    """Pose retenue par image : Panoramax calée (même prise) > GCP acceptés (poses.py) > recalage sur
    les bordures accepté > a priori SfM Mapillary (statut « a_priori » : jamais utilisé pour mesurer)."""
    sel = lire_json(BRUT / "selection.json")["images"]
    out = []
    for s_ in sel:
        iid = s_["id"]
        if not chemin_image(iid).exists():
            continue
        ph = photo_mly(iid)
        pm = pose_mly(ph)
        rg = POSES / "par_image" / f"{iid}.json"
        rg = lire_json(rg) if rg.exists() else None
        rb = _rec_bordures(iid, s_["sequence"])
        okb, why_b = accepte_bordures(rb)
        rec = dict(id=iid, date=ph.date, datetime=ph.datetime, sequence=s_["sequence"], camera_type=ph.im["camera_type"],
                   auteur=ph.auteur, W=ph.W, H=ph.H, camera_parameters=ph.im.get("camera_parameters"),
                   pose_mapillary={k: round(float(v), 4) for k, v in zip(("x", "y", "z", "lacet", "tangage", "roulis"),
                                                                         pm["pose"])},
                   attribution=ph.im["attribution"])
        if rg and rg.get("accepte") and rg.get("pose"):
            st = "calee_panoramax" if rg.get("panoramax") else "calee_gcp"
            rec.update(statut=st, pose=rg["pose"], qualite=rg.get("qualite"), ecart_type=rg.get("ecart_type"),
                       panoramax=rg.get("panoramax"), sigma_pos_m=0.15 if st == "calee_panoramax" else 0.25,
                       sigma_ang_deg=0.3)
        elif okb and not ph.is360:
            # revue visuelle (planches bordures_03/04/05, surfaces_00/01/06/07) : poses des téléphones
            # 2018 / 2024-02 recalées sur les bordures encore fausses de 1 à 3 m -> non retenues
            rec.update(statut="a_priori", pose=rec["pose_mapillary"], sigma_pos_m=10.0, sigma_ang_deg=3.0,
                       pose_bordures=rb["pose"], raison_refus=dict(gcp=(rg or {}).get("raison"),
                                                                   bordures="perspective : recalage rejeté à la revue visuelle"))
        elif okb:
            rec.update(statut="calee_bordures", pose=rb["pose"],
                       qualite={k: rb.get(k) for k in ("score_depart", "score", "n_points", "n_visibles",
                                                       "part_contrastee", "distinction", "ecart_mapillary")},
                       sequence_modele=rb.get("sequence_modele"),
                       # validation visuelle : sphériques ≈ 0,2–0,3 m ; perspectives (téléphones, 2048 px) : écarts
                       # de 1–2° visibles sur les bordures et mâts -> identification seulement, pas de mesure
                       sigma_pos_m=0.3 if ph.is360 else 1.0, sigma_ang_deg=0.4 if ph.is360 else 1.5)
        else:
            rec.update(statut="a_priori", pose=rec["pose_mapillary"], sigma_pos_m=10.0 if not ph.is360 else 2.0,
                       sigma_ang_deg=3.0, raison_refus=dict(gcp=(rg or {}).get("raison"), bordures=why_b))
        out.append(rec)
    from collections import Counter
    doc = {"schema": SCHEMA,
           "repere": "local = L93 − O, z = NGF − 216,30 ; pose [x, y, z, lacet grille, tangage, roulis] (camera.py)",
           "licence_images": LICENCE, "n": len(out), "statuts": dict(sorted(Counter(r["statut"] for r in out).items())),
           "regle": " ".join(assembler_poses.__doc__.split()), "images": out}
    ecrire_json(POSES / "poses_mapillary.json", arrondi(doc, 4))
    poses_calees.cache_clear()
    print(f"poses : {doc['statuts']}")
    return doc


def camera_finale(iid):
    """(camera, statut, sigma_pos_m) de la pose retenue (poses_mapillary.json)."""
    r = poses_calees().get(str(iid))
    ph = photo_mly(iid)
    if not r:
        return camera_mly(ph, pose_mly(ph)["pose"]), "a_priori", 10.0
    q = r["pose"]
    return (camera_mly(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]), r["statut"],
            r["sigma_pos_m"])


def vue_superposee(iid, lacet, tangage, fov, taille=(900, 600), couches=("mat", "bordure", "bordure_2025", "batiment"),
                   dmax=60.0, cam=None, extra=None):
    """Vue perspective (pose retenue) avec les éléments de référence valides à la date projetés."""
    from PIL import Image, ImageDraw
    from projection import camera_virtuelle, reechantillonner
    ph = photo_mly(iid)
    if cam is None:
        cam, _, _ = camera_finale(iid)
    cv = camera_virtuelle(cam, lacet, tangage, fov, taille)
    img = reechantillonner(cam, image_rgb_mly(iid).astype(np.float32), cv)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for el in couches_reference():
        if el["couche"] not in couches:
            continue
        if not (el["valide_de"] <= ph.date <= el["valide_a"]) and el["couche"] != "bordure_2025":
            continue
        n = tracer_polyligne(dr, cv, el["pts"], COULEURS[el["couche"]], 2 if el["couche"] != "mat" else 3, dmax=dmax,
                             ferme=el["ferme"])
        if n and el["couche"] == "mat":
            uv, ok, dist = cv.projeter(el["pts"][1:2])
            if ok[0]:
                dr.text(tuple(uv[0] + np.array([3, -12])), el["id"][4:24], fill=(0, 255, 255), font=police(12))
    for it in (extra or []):
        tracer_polyligne(dr, cv, it["pts"], it.get("couleur", (0, 255, 0)), it.get("larg", 3), dmax=dmax,
                         ferme=it.get("ferme", False))
    return im, cv


# --------------------------------------------------------------------------- 3 quinquies. validation
def residus_mats(iid, recherche_deg=2.0, dmax=35.0):
    """Contrôle indépendant d'une pose : mâts LiDAR / levés (catalogue GCP de gcp.py, valides à la date,
    jamais utilisés par le recalage sur les bordures) pointés automatiquement autour de leur projection ;
    écart angulaire (azimut) entre l'axe détecté et l'axe projeté. Liste de dict."""
    import gcp as G
    ph = photo_mly(iid)
    cam, st, _ = camera_finale(iid)
    img = image_gris_mly(iid)
    out = []
    for g in G.catalogue_gcp():
        if g["famille"] != "mat" or not G.valide(g, ph.date):
            continue
        P0 = np.array(g["pied"])
        d = float(np.hypot(*(P0[:2] - cam.C[:2])))
        if d < 4.0 or d > dmax:
            continue
        uv, ok, _ = cam.projeter(np.array([g["pied"], g["sommet"]]))
        if not ok.all():
            continue
        from projection import occulte_par_batiments
        if occulte_par_batiments(cam.C, P0[None])[0]:
            continue
        o = G.detecter_mat(ph, cam, img, g, recherche_deg)
        if o is None or o["force"] < 4.0 or o["coherence"] < 0.65:
            continue
        out.append(dict(gcp=g["id"], d_m=round(d, 2), ecart_deg=round(o["ecart_prediction_deg"], 3),
                        ecart_m=round(d * math.radians(o["ecart_prediction_deg"]), 3), force=round(o["force"], 2),
                        coherence=round(o["coherence"], 2)))
    return out


def images_validation(n=10):
    """10 images (déterministe) : tour à tour par groupe (statut de pose, date), la mieux notée d'abord,
    plus deux photos à plat recalées sur les bordures (rejetées) pour documenter le refus."""
    P = poses_calees()
    groupes = {}
    for iid, r in sorted(P.items()):
        if r["statut"] == "a_priori":
            continue
        groupes.setdefault((r["statut"], r["date"][:7]), []).append((iid, r))
    for k in groupes:
        groupes[k].sort(key=lambda t: (-float((t[1].get("qualite") or {}).get("score") or
                                              (t[1].get("qualite") or {}).get("n_gcp") or 0), t[0]))
    choix, rang = [], 0
    while len(choix) < n - 2 and any(rang < len(L) for L in groupes.values()):
        for k in sorted(groupes):
            if rang < len(groupes[k]) and len(choix) < n - 2:
                choix.append(groupes[k][rang][0])
        rang += 1
    rej = sorted(iid for iid, r in P.items() if r.get("pose_bordures"))
    choix += rej[:: max(1, len(rej) // 2)][:2]
    return choix


def valider(ids=None, n=10):
    """Planches de validation : mâts (cyan), bordures hors travaux (jaune) et travaux 2025 (rouge),
    emprises bâties pied/égout (orange) projetés à la pose retenue ; résidus des mâts pointés."""
    ids = ids or images_validation(n)
    VAL = SORTIE / "validation"
    VAL.mkdir(parents=True, exist_ok=True)
    rap = []
    for iid in ids:
        ph = photo_mly(iid)
        cam, st, sig = camera_finale(iid)
        rb = poses_calees()[iid].get("pose_bordures")
        if rb:                       # photo à plat : on montre la pose recalée (rejetée) pour la juger
            cam = camera_mly(ph, [rb[k] for k in ("x", "y", "z", "lacet", "tangage", "roulis")])
            st = "rejetee_bordures_perspective"
        from PIL import Image
        if ph.is360:
            vues = [vue_superposee(iid, (cam.pose[3] + a_) % 360, -8.0, 90.0, (800, 560), cam=cam)[0]
                    for a_ in (0, 90, 180, 270)]
            im = Image.new("RGB", (1604, 1124))
            for k, v in enumerate(vues):
                im.paste(v, ((k % 2) * 804, (k // 2) * 564))
        else:
            im = vue_superposee(iid, cam.pose[3], cam.pose[4], 2 * math.degrees(math.atan(0.5 / cam.fn)),
                                (1400, 1400 * ph.H // ph.W), cam=cam)[0]
        f = VAL / f"validation_{ph.date}_{iid}.jpg"
        im.save(f, quality=85)
        res = residus_mats(iid)
        e = [abs(x["ecart_deg"]) for x in res]
        rap.append(dict(id=iid, date=ph.date, camera_type=ph.im["camera_type"], statut_pose=st, planche=rel_racine(f),
                        mats=res, n_mats=len(res), ecart_median_deg=round(float(np.median(e)), 3) if e else None,
                        ecart_max_deg=round(float(np.max(e)), 3) if e else None))
        print(f"[{iid}] {ph.date} {st} : {len(res)} mâts, écart médian "
              f"{rap[-1]['ecart_median_deg']}° -> {f.name}", flush=True)
    ecrire_json(VAL / "validation.json", {"schema": SCHEMA, "regle": " ".join(valider.__doc__.split()),
                                          "images": rap})
    return rap


def rel_racine(p):
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return Path(p).as_posix()


# --------------------------------------------------------------------------- 4. recensement
ENRICHI = DESC / "enrichi"
PREUVES = SORTIE / "preuves"
PLANCHES = SORTIE / "planches"
CENSUS = SORTIE / "census"
POSES_FIABLES = ("calee_panoramax", "calee_gcp", "calee_bordures")


@functools.lru_cache(maxsize=1)
def index_description():
    import fusion_recensement as FR
    return FR.charger_index()


def _l93_local(A):
    A = np.asarray(A, float)
    return A[:, :2] - np.array(O[:2])


@functools.lru_cache(maxsize=4096)
def geometrie_3d(eid):
    """Géométrie 3D locale d'une entité : dict(genre 'vertical'|'ligne'|'poly'|'point', pts (N, 3), haut)."""
    ix = index_description()
    e = ix.E[eid]
    fam, p, G = e["famille"], e["props"], e["G"]
    if fam == "bordures":
        for i, A, _ in _bordures_3d():
            if i == eid:
                return dict(genre="ligne", pts=A, haut=0.0)
    if fam in ("mobilier", "arbres") and p.get("x_local") is not None and G["type"] == "point":
        x, y = p["x_local"], p["y_local"]
        z = p.get("z_local")
        z = z_sol(x, y) if z is None else z
        h = float(p.get("hauteur_m") or (8.0 if fam == "arbres" else 2.5))
        return dict(genre="vertical", pts=np.array([[x, y, z], [x, y, z + (min(h, 6.0) if fam == "arbres" else h)]]),
                    haut=h, couronne=float(p.get("diametre_couronne_m") or 0.0) if fam == "arbres" else 0.0)
    if fam == "instances":
        x, y = float(p["x"]), float(p["y"])
        z = float(p.get("z") if p.get("z") is not None else z_sol(x, y))
        h = 6.0 if "arbre" in str(p.get("prototype")) else 2.5
        return dict(genre="vertical", pts=np.array([[x, y, z], [x, y, z + h]]), haut=h, couronne=0.0)
    if G["type"] == "ligne":
        L = max(G["lignes"], key=len)
        Q = _l93_local(L)
        h = float(p.get("hauteur_m") or 0.0)
        return dict(genre="ligne", pts=np.c_[Q, [z_sol(*q) + 0.02 for q in Q]], haut=h)
    if G["type"] == "poly":
        R = max((pg[0] for pg in G["polys"]), key=len)
        Q = _l93_local(R)
        return dict(genre="poly", pts=np.c_[Q, [z_sol(*q) + 0.02 for q in Q]], haut=0.0)
    q = G["pt"] - np.array(O[:2])
    return dict(genre="point", pts=np.array([[q[0], q[1], z_sol(*q) + 0.02]]), haut=0.0)


def date_min_valide(eid):
    """Date à partir de laquelle une image montre l'entité sous sa forme 2026 (None : toujours)."""
    import fusion_recensement as FR
    import gcp as G
    e = index_description().E[eid]
    dm = FR.date_min_entite(e)
    if dm:
        return dm
    g = geometrie_3d(eid)
    c23, _ = G._zones_changees()
    if G._dans(g["pts"][:, :2], c23).mean() > 0.5:
        return "2023-06-01"
    return None


def validite_2026(eid, date_image):
    """valide_2026 d'une observation Mapillary (toutes antérieures aux travaux de 2025)."""
    import gcp as G
    e = index_description().E[eid]
    fam, p = e["famille"], e["props"]
    dm = date_min_valide(eid)
    if dm and date_image < dm:
        return dict(valeur=False, raison=f"image du {date_image} antérieure à la forme 2026 de l'entité (à partir de {dm})")
    g = geometrie_3d(eid)
    _, m25 = G._zones_changees()
    part25 = float(G._dans(g["pts"][:, :2], m25).mean()) if len(g["pts"]) else 0.0
    if part25 > 0.5:
        return dict(valeur="incertain", raison=f"image du {date_image} ; entité dans l'emprise des travaux 2025 "
                                               f"({part25:.0%}) : état antérieur aux travaux")
    st = str(p.get("statut_2026") or p.get("etat_2026") or p.get("etat") or p.get("etat_v1") or "")
    if fam == "bordures":
        return dict(valeur=True, raison=f"bordure hors travaux 2025, levée GAM (≈ 2025-12) ; image du {date_image}")
    if date_image >= "2022-01-01":
        return dict(valeur=True, raison=f"entité hors emprise des travaux 2025 ({st or 'inchangée'}) ; image du {date_image}")
    return dict(valeur="incertain", raison=f"image ancienne ({date_image}) : entité hors travaux 2025 mais changements "
                                           f"possibles depuis ({st or 'inchangée'})")


def _echantillons(g):
    if g["genre"] == "vertical":
        return g["pts"][0] + np.linspace(0, 1, 8)[:, None] * (g["pts"][1] - g["pts"][0])
    if len(g["pts"]) > 1:
        return densifier3(g["pts"], 0.5, ferme=g["genre"] == "poly")
    return g["pts"]


def vues_candidates(eid, n=3, dmin=2.5, dmax=30.0, statuts=POSES_FIABLES, spheriques_a_priori=True):
    """Meilleures images pour une entité : pose fiable, entité dans le champ (≥ 60 % des points
    échantillonnés, ou ≥ 8 points d'une ligne), 2,5–30 m, non occultée par le bâti ; score : date valide,
    récente, proximité (10 m idéal), part visible, pose GCP. Au plus une image par séquence."""
    from projection import occulte_par_batiments
    g = geometrie_3d(eid)
    pts = _echantillons(g)
    dm = date_min_valide(eid) or "0000"
    out = []
    for iid, r in sorted(poses_calees().items()):
        if r["statut"] not in statuts and not (spheriques_a_priori and r["statut"] == "a_priori"
                                               and r["camera_type"] == "spherical"):
            continue
        cam, st, sig = camera_finale(iid)
        d = np.hypot(pts[:, 0] - cam.C[0], pts[:, 1] - cam.C[1])
        if d.min() > dmax or d.max() < dmin:
            continue
        m = (d >= dmin) & (d <= dmax)
        uv, ok, dist = cam.projeter(pts[m])
        if cam.modele == "equirect":
            c = cam.pixel_vers_cam(uv)
            ok &= np.degrees(np.arcsin(np.clip(c[:, 2], -1, 1))) > -24.0
        part = ok.sum() / max(len(pts), 1)
        if part < 0.6 and not (g["genre"] in ("ligne", "poly") and ok.sum() >= 8):
            continue
        rep = pts[m][ok].mean(0)
        if occulte_par_batiments(cam.C, rep[None])[0]:
            continue
        dr = float(np.hypot(*(rep[:2] - cam.C[:2])))
        valide = r["date"] >= dm
        sc = (2.0 if valide else 0.0) + (1.0 if r["date"] >= "2022" else 0.0) + 0.5 * (r["date"] >= "2024") \
            + (1.0 - min(abs(dr - 10.0), 20.0) / 20.0) + 0.5 * min(part, 1.0) \
            + {"calee_panoramax": 0.6, "calee_gcp": 0.6, "calee_bordures": 0.4 if r["camera_type"] == "spherical"
               else 0.0, "a_priori": -0.3}[r["statut"]] + (0.3 if r["camera_type"] == "spherical" else 0.0)
        out.append((round(sc, 4), iid, dict(d_m=round(dr, 2), part=round(float(part), 2), statut=r["statut"],
                                            date=r["date"], valide=valide)))
    out.sort(key=lambda t: (-t[0], t[1]))
    res, seqs = [], set()
    for t in out:
        sq = poses_calees()[t[1]]["sequence"]
        if sq in seqs:
            continue
        seqs.add(sq)
        res.append(t)
        if len(res) >= n:
            break
    return res


def vignette_entite(eid, iid, taille=(400, 300), marge=1.6, fov_min=12.0, extra=None):
    """Découpe perspective centrée sur l'entité (pose retenue) : (brute, annotée, info). Entité en vert
    (axe vertical pour un objet, arête pour une bordure, contour sinon) ; trait jaune = 1 m."""
    from PIL import ImageDraw
    from projection import camera_virtuelle, reechantillonner
    from PIL import Image
    g = geometrie_3d(eid)
    cam, st, sig = camera_finale(iid)
    pts = g["pts"]
    Q = densifier3(pts, 0.25, ferme=g["genre"] == "poly") if len(pts) > 1 else pts
    if g["genre"] in ("ligne", "poly"):
        d = np.hypot(Q[:, 0] - cam.C[0], Q[:, 1] - cam.C[1])
        Qv = Q[(d >= 2.0) & (d <= 35.0)]
        Qv = Qv if len(Qv) else Q
        uv, ok, _ = cam.projeter(Qv)
        if ok.sum() >= 2:
            Qv = Qv[ok]
        if len(Qv) > 2:            # portion la plus proche (≈ 12 m) d'une ligne longue
            dd = np.hypot(Qv[:, 0] - cam.C[0], Qv[:, 1] - cam.C[1])
            k0 = int(np.argmin(dd))
            Qv = Qv[max(0, k0 - 24): k0 + 25]
        c = Qv.mean(0)
        dirs = Qv - cam.C
    else:
        c = pts[0] + np.array([0, 0, min(g["haut"], 6.0) * 0.45]) if g["genre"] == "vertical" else pts[0]
        dirs = np.vstack([pts - cam.C, pts - cam.C + np.array([1.2, 0, 0]), pts - cam.C - np.array([1.2, 0, 0]),
                          pts - cam.C + np.array([0, 1.2, 0]), pts - cam.C - np.array([0, 1.2, 0])])
    v = c - cam.C
    lac = math.degrees(math.atan2(v[0], v[1])) % 360
    tan = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))
    az = np.degrees(np.arctan2(dirs[:, 0], dirs[:, 1]))
    el = np.degrees(np.arctan2(dirs[:, 2], np.hypot(dirs[:, 0], dirs[:, 1])))
    da = np.abs(((az - lac + 180) % 360) - 180).max()
    de = np.abs(el - tan).max()
    fov = float(np.clip(2 * marge * max(da, de * taille[0] / taille[1], 2.0), fov_min, 100.0))
    cv = camera_virtuelle(cam, lac, tan, fov, taille)
    img = reechantillonner(cam, image_rgb_mly(iid).astype(np.float32), cv)
    brute = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    ann = brute.copy()
    dr = ImageDraw.Draw(ann)
    if g["genre"] == "vertical":
        tracer_polyligne(dr, cv, pts, (0, 255, 0), 2, dmax=80)
        if g.get("couronne"):
            r = g["couronne"] / 2
            t = np.linspace(0, 2 * np.pi, 25)
            ring = np.c_[pts[0, 0] + r * np.cos(t), pts[0, 1] + r * np.sin(t), np.full(25, pts[0, 2] + 0.05)]
            tracer_polyligne(dr, cv, ring, (0, 200, 0), 1, dmax=80)
    else:
        tracer_polyligne(dr, cv, pts, (0, 255, 0), 2, dmax=80, ferme=g["genre"] == "poly", pas=0.1)
    for it in (extra or []):
        tracer_polyligne(dr, cv, it["pts"], it.get("couleur", (255, 0, 255)), it.get("larg", 2), dmax=80,
                         ferme=it.get("ferme", False), pas=0.1)
    perp = np.array([math.cos(math.radians(lac)), -math.sin(math.radians(lac)), 0.0])
    base = c.copy()
    base[2] = z_sol(base[0], base[1]) + 0.02
    tracer_polyligne(dr, cv, np.array([base - 0.5 * perp, base + 0.5 * perp]), (255, 255, 0), 1, dmax=80)
    info = dict(lacet=round(lac, 2), tangage=round(tan, 2), fov=round(fov, 2), taille=list(taille), statut_pose=st,
                sigma_pos_m=sig, d_m=round(float(np.hypot(*(c[:2] - cam.C[:2]))), 2))
    return brute, ann, info


def police(t=13):
    from PIL import ImageFont
    for f in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            continue
    return ImageFont.load_default()


def planche(items, chemin, titre, taille=(400, 300), n_col=2):
    """Planche de revue : par item, découpe brute | découpe annotée + légende (clé, entité, date, d)."""
    from PIL import Image, ImageDraw
    w, h = taille
    cw, ch = 2 * w + 12, h + 22
    n_lig = (len(items) + n_col - 1) // n_col
    P = Image.new("RGB", (n_col * cw + 8, n_lig * ch + 30), (30, 30, 30))
    dr = ImageDraw.Draw(P)
    dr.text((8, 6), titre, fill=(255, 255, 255), font=police(15))
    for k, it in enumerate(items):
        x0 = 8 + (k % n_col) * cw
        y0 = 30 + (k // n_col) * ch
        P.paste(it["brute"], (x0, y0))
        P.paste(it["annotee"], (x0 + w + 4, y0))
        dr.text((x0 + 2, y0 + h + 3), it["legende"], fill=(255, 255, 160), font=police(13))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    P.save(chemin, quality=88)
    return chemin


CLASSES_SURFACES = ("trottoir", "chaussee", "parking", "piste_cyclable", "quai_bus", "ilot", "terre_plein_vegetal",
                    "espace_vert", "acces_riverain")


def cibles_census():
    """Cibles par groupe (ordre de priorité) : conflits ouverts (« a_verifier »), puis entités sans preuve
    image (ou seulement non valable 2026) par famille. Les entités entièrement dans l'emprise des
    travaux 2025 sont exclues (aucune image Mapillary n'est postérieure au 18/05/2025)."""
    import gcp as G
    ix = index_description()
    ev = lire_json(ENRICHI / "entites_verifiees.json")["entites"]
    cf = lire_json(ENRICHI / "conflits.json")["conflits"]
    _, m25 = G._zones_changees()
    out = {"conflits": []}
    vus = set()
    for c in cf:
        if c.get("gravite") == "a_verifier" and c["cible"] in ix.E and c["cible"] not in vus:
            out["conflits"].append(c["cible"])
            vus.add(c["cible"])
    for eid in sorted(ix.E):
        e = ix.E[eid]
        fam, p = e["famille"], e["props"]
        if eid in vus or ev.get(eid, {}).get("categorie_preuve", "sans") not in ("sans", "non_valable_2026"):
            continue
        if fam == "bordures":
            if p.get("zone_travaux_2025"):
                continue
            grp = "bordures"
        elif fam == "arbres":
            grp = "arbres"
        elif fam == "mobilier":
            grp = "mobilier"
        elif fam == "marquages":
            if p.get("etat") in ("neuf_2025", "refait_2025_identique"):
                continue
            grp = "marquages"
        elif fam in ("ilots", "ponctuels_sol"):
            grp = "ilots_ponctuels"
        elif fam == "surfaces":
            if p.get("classe") not in CLASSES_SURFACES or float(p.get("aire_m2") or 0) < 8.0 \
                    or "modifie_2025" in str(p.get("etat_v1")):
                continue
            grp = "surfaces"
        else:
            continue
        g = geometrie_3d(eid)
        if len(g["pts"]) and G._dans(g["pts"][:, :2], m25).mean() > 0.8:
            continue
        out.setdefault(grp, []).append(eid)
    return out


def _voisines(eid, rayon=20.0):
    """Autres bordures à moins de `rayon` m (tracées en jaune fin pour situer la bordure cible)."""
    g = geometrie_3d(eid)
    c = g["pts"][:, :2].mean(0)
    out = []
    for i, A, t25 in _bordures_3d():
        if i == eid:
            continue
        if np.hypot(*(A[:, :2] - c).T).min() <= rayon:
            out.append(dict(pts=A, couleur=(255, 220, 0) if not t25 else (255, 80, 80), larg=1))
    return out


def preparer_planches(groupe, eids=None, n_vues=1, par_planche=10, taille=(400, 300), debut=0, fov_min=12.0):
    """Découpes (brute | annotée) des meilleures vues de chaque cible du groupe, planches de revue et index
    (census/<groupe>.json : clé -> entité, image, date, pose, découpe, caméra virtuelle)."""
    eids = eids if eids is not None else cibles_census().get(groupe, [])
    items, sans_vue = [], []
    for eid in eids:
        vues = vues_candidates(eid, n=n_vues)
        if not vues:
            sans_vue.append(eid)
            continue
        for sc, iid, inf in vues:
            try:
                ex = _voisines(eid) if groupe.startswith("bordures") else None
                b, a_, info = vignette_entite(eid, iid, taille=taille, fov_min=fov_min, extra=ex)
            except Exception as e:  # noqa: BLE001
                print(f"  {eid}@{iid} : {type(e).__name__} {e}", flush=True)
                continue
            items.append(dict(eid=eid, iid=iid, date=inf["date"], d_m=inf["d_m"], statut_pose=inf["statut"],
                              valide_date=inf["valide"], camera_virtuelle=info, brute=b, annotee=a_))
    index = []
    for k in range(0, len(items), par_planche):
        lot = items[k:k + par_planche]
        num = debut + k // par_planche
        for j, it in enumerate(lot):
            cle = f"{groupe[:3].upper()}{num:02d}-{j}"
            it["cle"] = cle
            it["legende"] = (f"{cle}  {it['eid']}  {it['date']}  {it['d_m']:.0f} m  {it['statut_pose'][6:]}"
                             + ("" if it["valide_date"] else "  [avant forme 2026]"))
            from PIL import Image
            pair = Image.new("RGB", (2 * taille[0] + 4, taille[1]), (0, 0, 0))
            pair.paste(it["brute"], (0, 0))
            pair.paste(it["annotee"], (taille[0] + 4, 0))
            fp = PREUVES / groupe / f"{it['eid']}__{it['iid']}.jpg"
            fp.parent.mkdir(parents=True, exist_ok=True)
            pair.save(fp, quality=88)
            it["preuve"] = rel_racine(fp)
        chemin = PLANCHES / f"{groupe}_{num:02d}.jpg"
        planche(lot, chemin, f"Mapillary — revue {groupe} {num:02d} (gauche : brute ; droite : entité en vert, "
                             f"trait jaune = 1 m)", taille=taille)
        for it in lot:
            index.append({k_: v for k_, v in it.items() if k_ not in ("brute", "annotee")} | {"planche": rel_racine(chemin)})
    doc = {"schema": SCHEMA, "groupe": groupe, "n_cibles": len(eids), "n_vues": len(index), "sans_vue": sans_vue,
           "items": index}
    f = CENSUS / f"{groupe}.json" if debut == 0 else CENSUS / f"{groupe}_{debut:02d}.json"
    ecrire_json(f, arrondi(doc, 4))
    print(f"{groupe} : {len(eids)} cibles, {len(index)} vues, {len(sans_vue)} sans vue, "
          f"{(len(items) + par_planche - 1) // par_planche} planches", flush=True)
    return doc


TYPES_MATS = ("lampadaire", "support_feux", "panneau", "poteau_reseau", "mat_camera", "potelet", "poteau_arret",
              "panneau_information", "totem_PR", "balise_J11")


def trianguler_tout():
    """trianguler_mat_mixte sur tous les mâts du mobilier -> triangulation_mixte.json (résultats triangulés)."""
    ix = index_description()
    eids = sorted(e for e, v in ix.E.items() if v["famille"] == "mobilier" and str(v["type"]) in TYPES_MATS
                  and geometrie_3d(e)["genre"] == "vertical")
    out = []
    for e in eids:
        r = trianguler_mat_mixte(e, rayon_m=2.0)
        if r.get("xy"):
            r["n_mly"] = sum(v["source"].startswith("mly:") for v in r["vues"])
            out.append(r)
    ecrire_json(SORTIE / "triangulation_mixte.json", {"schema": SCHEMA, "regle": " ".join(trianguler_mat_mixte.__doc__.split()),
                                                      "n_objets": len(eids), "resultats": out})
    print(f"{len(eids)} mâts, {len(out)} triangulés, {sum(r['fiable'] for r in out)} fiables")
    return out


def planche_triangulation(eids, chemin):
    """Planche de revue d'une triangulation mixte : pour chaque vue retenue (Mapillary ou Panoramax),
    découpe brute | annotée (vert : axe à la position décrite, magenta : axe triangulé)."""
    from PIL import Image, ImageDraw
    from camera import camera_calee, image_rgb
    from projection import camera_virtuelle, reechantillonner
    tri = {r["entite"]: r for r in lire_json(SORTIE / "triangulation_mixte.json")["resultats"]}
    tuiles, items = [], []
    for eid in eids:
        r = tri[eid]
        g = geometrie_3d(eid)
        P, h = g["pts"][0], min(g["haut"], 5.0)
        X = np.array(r["xy"])
        zx = z_sol(*X)
        for v in r["vues"]:
            src = v["source"]
            if src.startswith("mly:"):
                cam, _, _ = camera_finale(src[4:])
                img = image_rgb_mly(src[4:])
            else:
                cam, _ = camera_calee(src[4:12])
                img = image_rgb(src[4:12])
            c = P + np.array([0, 0, h * 0.4])
            d = c - cam.C
            lac = math.degrees(math.atan2(d[0], d[1]))
            tan = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
            fov = float(np.clip(math.degrees(2 * math.atan(3.0 / max(np.hypot(d[0], d[1]), 1))), 8, 40))
            cv = camera_virtuelle(cam, lac, tan, fov, (360, 300))
            im = Image.fromarray(np.clip(reechantillonner(cam, img.astype(np.float32), cv), 0, 255).astype(np.uint8))
            a = im.copy()
            dr = ImageDraw.Draw(a)
            tracer_polyligne(dr, cv, np.array([P, P + [0, 0, h]]), (0, 255, 0), 1)
            tracer_polyligne(dr, cv, np.array([[X[0], X[1], zx], [X[0], X[1], zx + h]]), (255, 0, 255), 1)
            t = Image.new("RGB", (724, 320), (20, 20, 20))
            t.paste(im, (0, 0))
            t.paste(a, (364, 0))
            ImageDraw.Draw(t).text((4, 303), f"{eid} {src[:16]} {v['date']} d {v['d_m']} m (vert : description, "
                                             f"magenta : triangulé, écart {r['ecart_description_m']} m)",
                                   fill=(255, 255, 0), font=police(12))
            tuiles.append(t)
        mly = [v for v in r["vues"] if v["source"].startswith("mly:")]
        if mly:
            items.append(dict(cle=f"TRI00-{len(items)}", eid=eid, iid=mly[0]["source"][4:], date=mly[0]["date"],
                              d_m=mly[0]["d_m"], statut_pose=poses_calees()[mly[0]["source"][4:]]["statut"],
                              valide_date=True, triangulation=r, preuve=rel_racine(chemin), planche=rel_racine(chemin)))
    n = len(tuiles)
    P_ = Image.new("RGB", (2 * 728, ((n + 1) // 2) * 324), (0, 0, 0))
    for k, t in enumerate(tuiles):
        P_.paste(t, ((k % 2) * 728, (k // 2) * 324))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    P_.save(chemin, quality=88)
    ecrire_json(CENSUS / "triangulation.json", arrondi({"schema": SCHEMA, "groupe": "triangulation", "items": items}, 4))
    return items


CLASSE_OBS = {"lampadaire": "candelabre", "mat_camera": "candelabre", "poteau_reseau": "autre_poteau",
              "panneau": "panneau", "panneau_information": "panneau", "totem_PR": "panneau", "poteau_arret": "panneau",
              "support_feux": "feu", "potelet": "potelet", "balise_J11": "potelet", "poteau_incendie": "potelet",
              "cloture": "cloture", "portail": "cloture", "barriere_levante": "cloture", "chicane": "cloture",
              "abri_bus": "abri_bus"}
REVUE = SORTIE / "revue_mapillary.json"
OBS = SORTIE.parent / "obs_mapillary.json"
STATUTS_OBS = ("confirme", "attribut_corrige", "position_corrigee", "absent_sur_image", "absent_de_description",
               "incertain")


def classe_obs(eid):
    e = index_description().E[eid]
    fam, typ = e["famille"], str(e["type"] or "")
    if fam == "bordures":
        return "bordure"
    if fam == "arbres":
        return "arbre"
    if fam == "marquages":
        return "marquage"
    if fam == "ilots":
        return "ilot"
    if fam == "ponctuels_sol":
        return typ if typ in ("bev", "tampon", "avaloir") else "bev"
    if fam == "surfaces":
        return "surface"
    if fam == "mobilier":
        return CLASSE_OBS.get(typ, "mobilier")
    return "autre"


def position_entite(eid):
    """Point représentatif (local 3D et L93) de l'entité décrite."""
    g = geometrie_3d(eid)
    if g["genre"] in ("vertical", "point"):
        q = g["pts"][0]
    else:
        e = index_description().E[eid]
        pt = np.asarray(e["G"]["pt"], float) - np.array(O[:2])
        q = np.array([pt[0], pt[1], z_sol(*pt)])
    return [round(float(x), 3) for x in q], [round(float(q[0] + O[0]), 3), round(float(q[1] + O[1]), 3)]


def items_census():
    out = {}
    for f in sorted(CENSUS.glob("*.json")):
        for it in lire_json(f).get("items", []):
            out[it["cle"]] = it
    return out


REGLES_MATERIAU = [(r"béton désactivé|beton desactive", "beton_desactive"), (r"pav[ée]s", "paves_beton"),
                   (r"stabilis|terre-pierre", "stabilise_beige"), (r"paillage|copeaux|brf", "brf_bois_concasse"),
                   (r"gravier|gravillon|concass", "gravier_concasse_6_10"), (r"herbe haute|prairie", "herbe_haute"),
                   (r"gazon|pelouse|herbe", "gazon_tondu"), (r"terre nue", "terre_nue"), (r"béton|beton", "beton_balaye")]


def normaliser_attributs(a, eid, classe):
    """Clés et valeurs alignées sur la table d'alias de la fusion (FUS-ATT-01) : matériau -> identifiant du
    vocabulaire (texte gardé), enrobé générique -> matériau décrit s'il est déjà un enrobé, végétation
    (haie, massif) -> note ; hauteur d'arbre -> hauteur_estimee_m."""
    a = dict(a)
    if classe in ("surface", "ilot") and "materiau_observe" in a:
        txt = str(a.pop("materiau_observe"))
        a["materiau_observe_texte"] = txt
        decrit = str(((index_description().E[eid]["props"].get("revetement") or {}).get("materiau_id")
                      if eid in index_description().E else "") or "")
        t = txt.lower()
        mat = None
        if re.search(r"haie|arbust|massif|sous-bois", t) and not re.search(r"gazon|enrob|pav", t):
            a["vegetation_observee"] = txt
        elif re.search(r"enrob", t) and not re.search(r"pas (d.)?enrob", t):
            mat = decrit if decrit.startswith("enrobe") else "enrobe_bbsg_ancien"
        else:
            for rx, k in REGLES_MATERIAU:
                if re.search(rx, t):
                    mat = k
                    break
        if mat:
            a["materiau_observe"] = mat
    if classe == "arbre" and "hauteur_m" in a:
        a["hauteur_estimee_m"] = a.pop("hauteur_m")
    return a


def construire_obs():
    """revue_mapillary.json (verdicts de la revue visuelle, un par clé de planche) -> obs_mapillary.json
    (format OBS du recensement). Les verdicts « non_visible » ne produisent pas d'observation."""
    rev = lire_json(REVUE)
    items = items_census()
    P = poses_calees()
    obs = []
    compte = {}
    for v in rev["verdicts"]:
        st = v["statut"]
        if st not in STATUTS_OBS:
            continue
        cles = v["cle"] if isinstance(v["cle"], list) else [v["cle"]]
        it = items[cles[0]]
        eid = v.get("entite", it["eid"])
        iid = v.get("image", it["iid"])
        r = P[iid]
        grp = cles[0][:3]
        compte[grp] = compte.get(grp, 0) + 1
        loc, l93 = position_entite(eid) if eid in index_description().E else (None, None)
        pos = dict(local=loc, l93=l93, precision_m=round(max(0.15, 0.5 * r.get("sigma_pos_m", 0.4)), 2),
                   methode="projection_description")
        if v.get("position"):
            pos = dict(v["position"])
            if pos.get("local") and not pos.get("l93"):
                pos["l93"] = [round(pos["local"][0] + O[0], 3), round(pos["local"][1] + O[1], 3)]
        val = v.get("valide_2026") or (validite_2026(eid, r["date"]) if eid in index_description().E else
                                       dict(valeur="incertain", raison=f"image du {r['date']}"))
        cl = v.get("classe") or (classe_obs(eid) if eid in index_description().E else "autre")
        att = normaliser_attributs(v.get("attributs") or {}, eid, cl)
        att["image"] = dict(auteur=r["attribution"]["auteur"], licence=r["attribution"]["licence"],
                            lien=r["attribution"]["lien"], camera=r["camera_type"], pose=r["statut"],
                            distance_m=it.get("d_m"))
        if len(cles) > 1:
            att["autres_vues"] = [dict(cle=c, image=items[c]["iid"], date=items[c]["date"],
                                       preuve=items[c]["preuve"]) for c in cles[1:]]
        if v.get("remarque"):
            att["remarque"] = v["remarque"]
        o = dict(id=f"MLY-{grp}-{compte[grp]:03d}", source=f"mly:{iid}", date_image=r["datetime"],
                 classe=v.get("classe") or (classe_obs(eid) if eid in index_description().E else "autre"),
                 sous_type=v.get("sous_type") or str(index_description().E[eid]["type"] or "")
                 if eid in index_description().E else v.get("sous_type", "?"),
                 attributs=att, position=pos, lien_description=None if st == "absent_de_description" else eid,
                 statut=st, valide_2026=val, confiance=v.get("confiance", "moyenne"),
                 preuve=dict(fichier=it["preuve"], bbox=v.get("bbox") or [404, 0, 808, 300], cle=cles[0],
                             planche=it.get("planche")))
        obs.append(o)
    ecrire_json(OBS, obs)
    # preuves : seules les découpes citées par une observation sont gardées ; attribution CC-BY-SA
    citees = {RACINE / o["preuve"]["fichier"] for o in obs}
    for f in sorted(PREUVES.rglob("*.jpg")):
        if f not in citees:
            f.unlink()
    auteurs = {}
    for o in obs:
        im = o["attributs"]["image"]
        auteurs.setdefault(im["auteur"], set()).add(o["source"][4:])
    ecrire_json(SORTIE / "ATTRIBUTION.json", {
        "licence": LICENCE, "plateforme": "Mapillary",
        "mention": "Découpes et planches dérivées d'images Mapillary © leurs auteurs, CC-BY-SA 4.0 ; "
                   "diffusion sous la même licence, auteur et lien cités par image.",
        "auteurs": {a: dict(n_images=len(v), images=[f"https://www.mapillary.com/app/?pKey={i}" for i in sorted(v)])
                    for a, v in sorted(auteurs.items())}})
    from collections import Counter
    print(f"{len(obs)} observations -> {OBS} ; {dict(Counter(o['statut'] for o in obs))}")
    return obs


def corrections_proposees():
    """Positions corrigées proposées par la fusion (enrichi/corrections_position.geojson) : id -> (origine, corrigée) L93."""
    out = {}
    f = ENRICHI / "corrections_position.geojson"
    if f.exists():
        for ft in lire_json(f)["features"]:
            p = ft["properties"]
            c = ft["geometry"]["coordinates"]
            out[p.get("id") or p.get("entite")] = (np.array(c[0][:2]), np.array(c[-1][:2]), p)
    return out


def preparer_conflits(n_vues=3, taille=(400, 300)):
    """Conflits ouverts : 3 vues par cible ; vert = description, magenta = position corrigée proposée
    (vecteur de correction de la fusion), cyan = autre entité du conflit (doublon)."""
    ix = index_description()
    cf = [c for c in lire_json(ENRICHI / "conflits.json")["conflits"] if c.get("gravite") == "a_verifier"]
    corr = corrections_proposees()
    items, sans_vue, vus = [], [], set()
    for c in cf:
        eid = c["cible"]
        if eid not in ix.E or eid in vus:
            continue
        vus.add(eid)
        extra = []
        g = geometrie_3d(eid)
        if eid in corr:
            o, q, _ = corr[eid]
            ql = q - np.array(O[:2])
            dq = ql - (o - np.array(O[:2]))
            if g["genre"] == "vertical":
                z = z_sol(*ql)
                extra.append(dict(pts=np.array([[ql[0], ql[1], z], [ql[0], ql[1], z + min(g["haut"], 6.0)]]),
                                  couleur=(255, 0, 255), larg=2))
            else:
                extra.append(dict(pts=g["pts"] + np.array([dq[0], dq[1], 0.0]), couleur=(255, 0, 255), larg=1,
                                  ferme=g["genre"] == "poly"))
        for autre in re.findall(r"de (\w+) \(", c.get("detail", "")):
            if autre in ix.E and autre != eid:
                ga = geometrie_3d(autre)
                extra.append(dict(pts=ga["pts"], couleur=(0, 255, 255), larg=2))
        vues = vues_candidates(eid, n=n_vues, dmax=35.0)
        if not vues:
            sans_vue.append(eid)
            continue
        for sc, iid, inf in vues:
            b, a_, info = vignette_entite(eid, iid, taille=taille, extra=extra, marge=2.2)
            items.append(dict(eid=eid, conflit=c["id"], type_conflit=c["type"], iid=iid, date=inf["date"],
                              d_m=inf["d_m"], statut_pose=inf["statut"], valide_date=inf["valide"],
                              camera_virtuelle=info, brute=b, annotee=a_))
    index = []
    for k in range(0, len(items), 9):
        lot = items[k:k + 9]
        num = k // 9
        from PIL import Image
        for j, it in enumerate(lot):
            it["cle"] = f"CON{num:02d}-{j}"
            it["legende"] = f"{it['cle']}  {it['eid']} ({it['conflit']})  {it['date']}  {it['d_m']:.0f} m  {it['statut_pose'][6:]}"
            pair = Image.new("RGB", (2 * taille[0] + 4, taille[1]), (0, 0, 0))
            pair.paste(it["brute"], (0, 0))
            pair.paste(it["annotee"], (taille[0] + 4, 0))
            fp = PREUVES / "conflits" / f"{it['eid']}__{it['iid']}.jpg"
            fp.parent.mkdir(parents=True, exist_ok=True)
            pair.save(fp, quality=88)
            it["preuve"] = rel_racine(fp)
        chemin = PLANCHES / f"conflits_{num:02d}.jpg"
        planche(lot, chemin, f"Mapillary — conflits {num:02d} (vert : description ; magenta : correction proposée ; "
                             f"cyan : autre objet)", taille=taille)
        for it in lot:
            index.append({k_: v for k_, v in it.items() if k_ not in ("brute", "annotee")} | {"planche": rel_racine(chemin)})
    doc = {"schema": SCHEMA, "groupe": "conflits", "n_cibles": len(vus), "n_vues": len(index), "sans_vue": sans_vue,
           "items": index}
    ecrire_json(CENSUS / "conflits.json", arrondi(doc, 4))
    print(f"conflits : {len(vus)} cibles, {len(index)} vues, sans vue {sans_vue}")
    return doc


# --------------------------------------------------------------------------- 5. triangulation mixte
def _cameras_mixtes(P, dmin=4.0, dmax=30.0, date_min="0000", date_max="9999"):
    """Caméras fiables voyant le point P (local) : Mapillary (poses calées, perspectives exclues : écarts de
    1–2°) et Panoramax (poses calées acceptées, poses.json). Liste de dict(source, cam, img_gris, ph, sig_deg)."""
    from camera import catalogue, camera_calee, charger_poses, image_gris
    out = []
    for iid, r in sorted(poses_calees().items()):
        if r["statut"] not in POSES_FIABLES or r["camera_type"] != "spherical":
            continue
        if not (date_min <= r["date"] <= date_max):
            continue
        cam, st, sig = camera_finale(iid)
        d = float(np.hypot(*(P[:2] - cam.C[:2])))
        if dmin <= d <= dmax:
            out.append(dict(source=f"mly:{iid}", date=r["date"], cam=cam, ph=photo_mly(iid),
                            img=lambda iid=iid: image_gris_mly(iid), sig_deg=r.get("sigma_ang_deg", 0.4),
                            sigma_pos_m=r["sigma_pos_m"]))
    pp = charger_poses()
    for id8, ph in sorted(catalogue().items()):
        rec = pp.get(id8)
        if not rec or not rec.get("accepte") or not (date_min <= ph.date <= date_max):
            continue
        cam, st = camera_calee(id8, pp)
        d = float(np.hypot(*(P[:2] - cam.C[:2])))
        if dmin <= d <= dmax:
            out.append(dict(source=f"pnx:{ph.id}", date=ph.date, cam=cam, ph=ph, img=lambda i=id8: image_gris(i),
                            sig_deg=max(0.1, float(rec["qualite"]["residu_moy_deg"])), sigma_pos_m=0.15))
    # même prise de vue sur les deux plateformes : une seule fois (Panoramax gardée)
    pnx_t = {}
    for c in out:
        if c["source"].startswith("pnx:"):
            pnx_t[round(float(c["cam"].C[0]), 1), round(float(c["cam"].C[1]), 1)] = 1
    return [c for c in out if not (c["source"].startswith("mly:") and poses_calees()[c["source"][4:]].get("panoramax"))]


def trianguler_mat_mixte(eid, rayon_m=2.0, dmax=30.0, date_min="0000", date_max="9999", diam=None, h=None):
    """Axe vertical d'un mât / tronc pointé automatiquement (gcp.detecter_mat, 3 pics) dans toutes les vues
    fiables (Mapillary sphériques calées + Panoramax calées), RANSAC sur les visées, moindres carrés
    (triangulation.trianguler_verticale). Renvoie dict ou None."""
    import gcp as G
    from triangulation import trianguler_verticale
    g3 = geometrie_3d(eid)
    P = g3["pts"][0]
    e = index_description().E[eid]
    typ = str(e["type"] or "")
    hh = float(h or min(g3.get("haut") or 3.0, 6.0))
    gg = dict(id="TRI-" + eid, famille="mat", pied=[P[0], P[1], P[2]], sommet=[P[0], P[1], P[2] + max(hh - 0.4, 1.0)],
              diametre_m=diam or G.DIAMETRES.get(typ, 0.25 if e["famille"] == "arbres" else 0.15), sigma_m=rayon_m)
    vis = []
    for c in _cameras_mixtes(P, 4.0, dmax, date_min, date_max):
        cam = c["cam"]
        d = float(np.hypot(*(P[:2] - cam.C[:2])))
        uv, ok, _ = cam.projeter(np.array([gg["pied"], gg["sommet"]]))
        if not ok.all():
            continue
        fen = math.degrees(math.atan2(rayon_m, d))
        try:
            pics = G.detecter_mat(c["ph"], cam, c["img"](), gg, fen, n_pics=3, prior_deg=fen)
        except Exception:  # noqa: BLE001
            continue
        for o in (pics or []):
            if o["force"] < 3.0 or o["coherence"] < 0.5:
                continue
            az = math.radians(o["az"])
            vis.append(dict(source=c["source"], date=c["date"], C=cam.C.copy(), az=o["az"],
                            D=np.array([math.sin(az), math.cos(az), 0.0]), sig=math.radians(c["sig_deg"] + 0.08),
                            force=o["force"], coherence=o["coherence"], d=d))
    sources = sorted({v["source"] for v in vis})
    if len(sources) < 2:
        return dict(entite=eid, n_vues=len(sources), resultat=None, raison="moins de 2 vues avec un mât détecté")
    # RANSAC déterministe : toutes les paires de visées de sources différentes
    best = None
    for i in range(len(vis)):
        for j in range(i + 1, len(vis)):
            a, b = vis[i], vis[j]
            if a["source"] == b["source"]:
                continue
            A = np.array([[a["D"][0], -b["D"][0]], [a["D"][1], -b["D"][1]]])
            if abs(np.linalg.det(A)) < 0.17:      # angle < 10°
                continue
            t = np.linalg.solve(A, (b["C"] - a["C"])[:2])
            if t[0] <= 0 or t[1] <= 0:
                continue
            X = a["C"][:2] + t[0] * a["D"][:2]
            if np.hypot(*(X - P[:2])) > rayon_m + 0.5:
                continue
            inl = {}
            for v in vis:
                n = np.array([v["D"][1], -v["D"][0]])
                r = abs(float(n @ (X - v["C"][:2])))
                if r <= max(0.12, 2.5 * v["sig"] * v["d"]):
                    if v["source"] not in inl or r < inl[v["source"]][0]:
                        inl[v["source"]] = (r, v)
            sc = len(inl) - 0.1 * float(np.hypot(*(X - P[:2])))
            if best is None or sc > best[0]:
                best = (sc, X, inl)
    if best is None:
        return dict(entite=eid, n_vues=len(sources), resultat=None, raison="aucune paire de visées cohérente")
    _, X, inl = best
    V = [v for _, v in sorted(inl.values(), key=lambda t: t[1]["source"])]
    C = np.array([v["C"] for v in V])
    D = np.array([v["D"] for v in V])
    S = np.array([v["sig"] for v in V])
    t = trianguler_verticale(None, rayons=(C, D, S))
    if t is None:
        return dict(entite=eid, n_vues=len(sources), resultat=None, raison="triangulation impossible")
    xy = np.array(t["xy"])
    # stabilité : retrait d'une vue
    loo = []
    if len(V) >= 3:
        for k in range(len(V)):
            m = np.arange(len(V)) != k
            tk = trianguler_verticale(None, rayons=(C[m], D[m], S[m]))
            if tk:
                loo.append(float(np.hypot(*(np.array(tk["xy"]) - xy))))
    d_desc = float(np.hypot(*(xy - P[:2])))
    return dict(entite=eid, n_vues=len(sources), n_inliers=len(V), xy=[round(float(x), 3) for x in xy],
                ecart_type=[round(float(s), 3) for s in t["ecart_type"]], angle_intersection_deg=round(t["angle_intersection_deg"], 1),
                residus_deg=[round(float(r), 3) for r in t["residus_deg"]], stabilite_loo_m=round(max(loo), 3) if loo else None,
                ecart_description_m=round(d_desc, 3), vues=[dict(source=v["source"], date=v["date"], az=round(v["az"], 3),
                                                               d_m=round(v["d"], 2), force=round(v["force"], 1))
                                                          for v in V],
                fiable=bool(len(V) >= 3 and t["angle_intersection_deg"] >= 20 and max(t["ecart_type"]) <= 0.25
                            and (not loo or max(loo) <= 0.3)))


# --------------------------------------------------------------------------- CLI
def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--jeton-fichier", default=None)
    a.add_argument("--lister", action="store_true")
    a.add_argument("--selectionner", action="store_true")
    a.add_argument("--telecharger", action="store_true")
    a.add_argument("--poses", action="store_true")
    a.add_argument("--valider", action="store_true")
    a.add_argument("--recaler", action="store_true", help="recalage sur les bordures (séquences, images)")
    a.add_argument("--assembler", action="store_true", help="poses retenues -> poses_mapillary.json")
    a.add_argument("--census", action="store_true", help="cibles, découpes et planches de revue (census/, planches/)")
    a.add_argument("--obs", action="store_true", help="revue_mapillary.json -> obs_mapillary.json")
    a.add_argument("--trianguler", action="store_true", help="triangulation mixte des mâts -> triangulation_mixte.json")
    a.add_argument("--ids", nargs="*", default=None)
    a.add_argument("--part", default=None, help="k/n : sous-ensemble déterministe des images")
    a = a.parse_args(argv)
    if a.lister:
        tok = jeton(a.jeton_fichier)
        brutes = lister(tok)
        images = [enrichir_meta(im) for im in brutes]
        doc = ecrire_inventaire(images)
        print(f"{doc['n']} images, {len(doc['sequences'])} séquences -> {BRUT / 'images.json'}")
    if a.selectionner:
        selectionner()
    if a.telecharger:
        telecharger(jeton(a.jeton_fichier))
    if a.poses:
        poses_toutes(a.ids, a.part)
    if a.recaler:
        recaler_tout(a.part)
    if a.assembler:
        assembler_poses()
    if a.valider:
        valider(a.ids)
    if a.census:
        c = cibles_census()
        ecrire_json(CENSUS / "cibles.json", c)
        preparer_conflits()
        for g in ("mobilier", "arbres", "marquages", "ilots_ponctuels", "surfaces"):
            preparer_planches(g, c.get(g, []))
        preparer_planches("bordures", c.get("bordures", []), fov_min=50.0)
    if a.trianguler:
        trianguler_tout()
    if a.obs:
        construire_obs()


if __name__ == "__main__":
    main()
