#!/usr/bin/env python
"""Orthophotos récentes (postérieures au PCRS 5 cm du 10/05/2022) sur le carrefour Paquet Jardin.

Chaîne (déterministe ; numpy + Pillow + pyproj + requests ; réutilise pipeline/ortho.py) :

  python orthos_recentes.py --decouvrir    # GetCapabilities IGN / CRAIG / GAM + WebDAV PCRS CRAIG,
                                           # couverture de chaque couche sur l'emprise, dates
                                           # (graphe de mosaïquage BD ORTHO, identité d'image),
                                           # -> ortho_recentes/catalogue_orthos.json
  python orthos_recentes.py --telecharger  # couches datées > 2022-05 et couvrantes, résolution native,
                                           # dalles 1000 px + .jgw -> data/raw/ortho_recentes/<couche>/
  python orthos_recentes.py --recaler      # décalage de chaque couche par rapport au PCRS 2022
                                           # (corrélation de phase sur fenêtres stables) -> recalage.json
  python orthos_recentes.py --planches     # planches 2 x 2 (PCRS 2022 | IGN 2024 / 2024 + description |
                                           # Pléiades 2025) du cœur (± 75 m) et du secteur construit
                                           # 2023-2024 (est / sud-est), carte des changements
  python orthos_recentes.py --obs          # saisie/observations.json -> obs_ortho_recentes.json (format OBS)

Repères : local = L93 − O(917279.43, 6460289.98) ; pixel (i, j) = [i, i+1[ ; x = X_gauche + u·res,
y = Y_haut − v·res (le .jgw donne le centre du pixel haut-gauche, comme pipeline/ortho.py).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RACINE / "pipeline"))
import ortho as pipeline_ortho  # noqa: E402  (grille + fetch_tile + fichier monde)
from common import http_get, USER_AGENT  # noqa: E402

O = (917279.43, 6460289.98)
BBOX = (917129.0, 6460140.0, 917429.0, 6460440.0)          # emprise du site (L93)
DATE_PCRS = "2022-05-10"
DEBUT_TRAVAUX, FIN_TRAVAUX, FIN_TROTTOIRS_VERCORS = "2025-06-23", "2025-12-05", "2026-01-30"
RAW = RACINE / "data/raw/ortho_recentes"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/ortho_recentes"
OBS = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/obs_ortho_recentes.json"
PCRS = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
DONNEES = RACINE / "recon/out/paquet_jardin/package/donnees"

IGN_WMS = "https://data.geopf.fr/wms-r"
IGN_WFS = "https://data.geopf.fr/wfs"
CRAIG_WMS = "https://wms.craig.fr/ortho"
GAM_WMS = "https://geoflux.grenoblealpesmetropole.fr/geoserver/wms"
CRAIG_DAV = "https://drive.opendata.craig.fr/public.php/webdav/ortho/PCRS_5cm/"
CRAIG_RTGE = "https://tiles.rtge.craig.fr/pcrs/service?SERVICE=WMTS&REQUEST=GetCapabilities"

LICENCES = {
    "ign": ("Licence Ouverte Etalab 2.0", "IGN – Géoplateforme (data.geopf.fr)"),
    "craig": ("Licence Ouverte Etalab 2.0", "CRAIG / IGN – orthophotographie régionale"),
    "gam": ("Licence Ouverte (ODbL pour certains jeux)", "Grenoble-Alpes Métropole – geoflux"),
}

# Couches retenues pour le téléchargement : résolution native et format. Les autres couches
# couvrantes sont des doublons (identité d'image) ou antérieures à mai 2022 (voir le catalogue).
NATIVES = {
    "ORTHOIMAGERY.ORTHOPHOTOS2024": dict(res=0.20, fmt="image/jpeg", tag="ign_bdortho_2024_rvb_20cm"),
    "ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024": dict(res=0.20, fmt="image/jpeg", tag="ign_bdortho_2024_irc_20cm"),
    "ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-EXPRESS.2024": dict(res=0.20, fmt="image/jpeg", tag="ign_express_2024_rvb_20cm"),
    "ORTHOIMAGERY.ORTHOPHOTOS.IRC-EXPRESS.2024": dict(res=0.20, fmt="image/jpeg", tag="ign_express_2024_irc_20cm"),
    "ORTHOIMAGERY.ORTHOPHOTOS.ORTHO-ASP_PAC2025": dict(res=0.20, fmt="image/jpeg", tag="ign_asp_pac2025_20cm"),
    "ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025": dict(res=0.50, fmt="image/png", tag="ign_pleiades_2025_50cm"),
    "ORTHOIMAGERY.ORTHO-SAT.SPOT.2022": dict(res=1.50, fmt="image/png", tag="ign_spot_2022_150cm"),
    "ORTHOIMAGERY.ORTHO-SAT.SPOT.2023": dict(res=1.50, fmt="image/png", tag="ign_spot_2023_150cm"),
    "ORTHOIMAGERY.ORTHO-SAT.SPOT.2024": dict(res=1.50, fmt="image/png", tag="ign_spot_2024_150cm"),
    "ORTHOIMAGERY.ORTHO-SAT.SPOT.2025": dict(res=1.50, fmt="image/png", tag="ign_spot_2025_150cm"),
    "craig:ortho_2024": dict(res=0.20, fmt="image/jpeg", tag="craig_ortho_2024_20cm"),
}
REF_2024 = "ORTHOIMAGERY.ORTHOPHOTOS2024"
REF_2021 = "ORTHOIMAGERY.ORTHOPHOTOS2021"                  # PVA IGN Isère 2021-08 (antérieure au PCRS)

# Dates sans métadonnée publique : estimées et documentées (voir README, « Orthos récentes »).
# Rempli après analyse des images (ombres, état du chantier, phénologie) ; provenance citée.
DATES_ESTIMEES: dict[str, dict] = {
    "ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025": {
        "dates": ["2025"], "posterieure_pcrs_2022": True,
        "methode": ("aucune métadonnée de date publique (couche annuelle CNES / IGN, CSW IGNF_ORTHO-SAT sans étendue "
                    "temporelle) ; examen de l'image : feuillage complet, carrefour encore dans son état 2024 (zébras, îlots, "
                    "kiosque), aucune emprise de chantier au cœur -> probablement avant le 23/06/2025 (planches vue_pleiades_*)")},
}


# --------------------------------------------------------------------------- utilitaires
def local(x, y):
    return [round(x - O[0], 3), round(y - O[1], 3)]


def l93(xl, yl):
    return [round(xl + O[0], 3), round(yl + O[1], 3)]


def rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return str(p)


def sha256(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ecrire_json(p: Path, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def lire_json(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _police(t):
    for n in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, t)
        except OSError:
            pass
    return ImageFont.load_default()


def wms_image(url, couche, bbox, res, fmt="image/png", crs="EPSG:2154", version="1.3.0"):
    """GetMap -> (RGBA uint8, None) ou (None, message)."""
    n_x, n_y = round((bbox[2] - bbox[0]) / res), round((bbox[3] - bbox[1]) / res)
    p = {"SERVICE": "WMS", "VERSION": version, "REQUEST": "GetMap", "LAYERS": couche, "STYLES": "",
         "FORMAT": fmt, "WIDTH": n_x, "HEIGHT": n_y, ("CRS" if version == "1.3.0" else "SRS"): crs,
         "BBOX": ",".join(f"{v:.3f}" for v in bbox)}
    if fmt == "image/png":
        p["TRANSPARENT"] = "TRUE"
    try:
        r = http_get(url, params=p, timeout=(30, 180))
    except RuntimeError as e:
        return None, str(e)[:200]
    if not r.headers.get("content-type", "").startswith("image"):
        return None, re.sub(r"\s+", " ", r.text[:200])
    return np.asarray(Image.open(io.BytesIO(r.content)).convert("RGBA")), None


def couverture(a):
    """Part de pixels porteurs de données (opaques et non blancs/noirs purs) et écart type."""
    ok = (a[..., 3] > 0) & (a[..., :3].min(axis=2) < 250) & (a[..., :3].max(axis=2) > 5)
    v = a[..., :3][ok]
    return round(float(ok.mean()), 3), round(float(v.std()) if len(v) else 0.0, 1)


def passe_haut(g, k=7):
    """Image grise moins sa moyenne locale (boîte k x k) : insensible aux écarts radiométriques."""
    g = g.astype(np.float64)
    c = np.cumsum(np.cumsum(np.pad(g, ((k // 2 + 1, k // 2), (k // 2 + 1, k // 2)), mode="edge"), 0), 1)
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return g - s / (k * k)


def ncc(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = math.sqrt(float((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else 0.0


def ncc_max(a, b, r=3):
    """NCC maximale sur des décalages entiers |d| <= r (tolère un léger écart de géoréférencement)."""
    h, w = a.shape
    best = -1.0
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            aa = a[r + dy:h - r + dy, r + dx:w - r + dx]
            bb = b[r:h - r, r:w - r]
            best = max(best, ncc(aa, bb))
    return round(best, 3)


# --------------------------------------------------------------------------- géométrie simple
def _clip_anneau(pts, b):
    """Sutherland-Hodgman d'un anneau contre le rectangle b = (x0, y0, x1, y1)."""
    def couper(pts, dedans, inter):
        out = []
        for i in range(len(pts)):
            p, q = pts[i - 1], pts[i]
            if dedans(q):
                if not dedans(p):
                    out.append(inter(p, q))
                out.append(q)
            elif dedans(p):
                out.append(inter(p, q))
        return out

    def ix(p, q, x):
        t = (x - p[0]) / (q[0] - p[0])
        return (x, p[1] + t * (q[1] - p[1]))

    def iy(p, q, y):
        t = (y - p[1]) / (q[1] - p[1])
        return (p[0] + t * (q[0] - p[0]), y)

    x0, y0, x1, y1 = b
    pts = [tuple(c[:2]) for c in pts]
    for dedans, inter in ((lambda p: p[0] >= x0, lambda p, q: ix(p, q, x0)),
                          (lambda p: p[0] <= x1, lambda p, q: ix(p, q, x1)),
                          (lambda p: p[1] >= y0, lambda p, q: iy(p, q, y0)),
                          (lambda p: p[1] <= y1, lambda p, q: iy(p, q, y1))):
        if not pts:
            break
        pts = couper(pts, dedans, inter)
    return pts


def aire(pts):
    if len(pts) < 3:
        return 0.0
    a = np.asarray(pts)
    return 0.5 * abs(float(np.dot(a[:, 0], np.roll(a[:, 1], -1)) - np.dot(a[:, 1], np.roll(a[:, 0], -1))))


def dans_anneau(x, y, pts):
    a = np.asarray(pts)
    xi, yi = a[:, 0], a[:, 1]
    xj, yj = np.roll(xi, 1), np.roll(yi, 1)
    c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / np.where(yj - yi == 0, 1e-12, yj - yi) + xi)
    return bool(c.sum() % 2)


def polygones(g):
    if g["type"] == "Polygon":
        return [g["coordinates"]]
    if g["type"] == "MultiPolygon":
        return g["coordinates"]
    return []


# --------------------------------------------------------------------------- découverte
def capacites_wms(url):
    r = http_get(url, params={"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"},
                 timeout=(30, 180))
    t = r.content.decode("utf-8", errors="replace")
    couches = []
    for m in re.finditer(r"<Layer[^>]*>\s*<Name>([^<]+)</Name>\s*<Title>([^<]*)</Title>(.*?)(?=<Layer|</Layer>)", t, re.S):
        ab = re.search(r"<Abstract>([^<]*)</Abstract>", m.group(3))
        couches.append({"nom": m.group(1).strip(), "titre": m.group(2).strip(),
                        "resume": re.sub(r"\s+", " ", ab.group(1))[:300] if ab else ""})
    return couches, hashlib.sha256(r.content).hexdigest()


def annees(nom):
    return [int(a) for a in re.findall(r"(?<!\d)(19\d\d|20\d\d)(?!\d)", nom)]


def candidates_ign(couches):
    """Couches ortho de la Géoplateforme pouvant être postérieures à mai 2022 (non datées comprises)."""
    out = []
    for c in couches:
        n = c["nom"]
        if not re.search(r"ORTHO|PCRS|OrthoimageCoverage", n):
            continue
        if re.search(r"GRAPHE|RESTRICTED|URGENCE|EDUGEO|MAYOTTE|OYAPOCK|D075|ZONES-TESTS|TPM|^PCRS\d|^PCRS_", n):
            continue
        a = annees(n)
        if a and max(a) < 2022:
            continue
        out.append(c)
    return out


def graphe_bdortho(typename="ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho"):
    """Polygones du graphe de mosaïquage BD ORTHO sur l'emprise, découpés à l'emprise, avec date de vol."""
    r = http_get(IGN_WFS, params={"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
                                  "TYPENAMES": typename, "SRSNAME": "EPSG:2154",
                                  "BBOX": ",".join(str(v) for v in BBOX) + ",EPSG:2154",
                                  "OUTPUTFORMAT": "application/json", "COUNT": 100}, timeout=(30, 300))
    feats = []
    for f in r.json()["features"]:
        p = f["properties"]
        anneaux = []
        for poly in polygones(f["geometry"]):
            for k, ring in enumerate(poly):
                c = _clip_anneau(ring, BBOX)
                if len(c) >= 3:
                    anneaux.append({"trou": k > 0, "pts": [[round(x, 2), round(y, 2)] for x, y in c]})
        a = sum(aire(r_["pts"]) * (-1 if r_["trou"] else 1) for r_ in anneaux)
        if a > 0.5:
            feats.append({"date_vol": str(p.get("date_vol", ""))[:10], "pva": p.get("pva"),
                          "res_cm": p.get("res"), "echelle": p.get("echelle"), "dep": p.get("dep"),
                          "aire_emprise_m2": round(a, 1), "anneaux": anneaux})
    return feats


def date_au_point(graphe, x, y, echelle=20):
    for f in graphe:
        if f.get("echelle") not in (None, echelle):
            continue
        ext = any(dans_anneau(x, y, r_["pts"]) for r_ in f["anneaux"] if not r_["trou"])
        if ext and not any(dans_anneau(x, y, r_["pts"]) for r_ in f["anneaux"] if r_["trou"]):
            return f["date_vol"]
    return None


def lister_dav(url):
    r = requests.request("PROPFIND", url, auth=("opendata", ""), headers={"Depth": "1", "User-Agent": USER_AGENT},
                         timeout=(30, 300))
    if r.status_code >= 400:
        return None
    return re.findall(r"<d:href>([^<]+)</d:href>", r.text)[1:]


def campagnes_pcrs():
    """Campagnes PCRS 5 cm ouvertes du CRAIG et couverture du site (nom de dalle = coin haut-gauche en hm)."""
    out = []
    annees_ = lister_dav(CRAIG_DAV) or []
    for a in annees_:
        m = re.search(r"/(\d{4})/$", a)
        if not m:
            continue
        for c in lister_dav(CRAIG_DAV + m.group(1) + "/") or []:
            mc = re.search(r"/(\d{4})/([^/]+)/$", c)
            if not mc:
                continue
            dalles = lister_dav(CRAIG_DAV + f"{mc.group(1)}/{mc.group(2)}/") or []
            xy = [(int(g.group(1)), int(g.group(2))) for g in
                  (re.search(r"/(\d{4})-(\d{5})\.tif$", d) for d in dalles) if g]
            site = [f"{x}-{y}" for x, y in xy
                    if x * 100 < BBOX[2] and x * 100 + 200 > BBOX[0] and y * 100 > BBOX[1] and y * 100 - 200 < BBOX[3]]
            out.append({"annee": int(mc.group(1)), "campagne": mc.group(2), "n_dalles": len(xy),
                        "dalles_site": site, "couvre_site": bool(site)})
    return out


def decouvrir():
    SORTIE.mkdir(parents=True, exist_ok=True)
    cat = {"genere": "orthos_recentes.py --decouvrir", "date_consultation": dt.date.today().isoformat(),
           "emprise_l93": BBOX, "date_pcrs_reference": DATE_PCRS, "services": {}, "couches": [],
           "pcrs_craig_opendata": [], "graphe_bdortho": {}}
    # 1. IGN Géoplateforme
    caps, h = capacites_wms(IGN_WMS)
    cat["services"]["ign_wms"] = {"url": IGN_WMS, "n_couches": len(caps), "sha256_capacites": h}
    cand = [dict(c, service="ign", url=IGN_WMS) for c in candidates_ign(caps)]
    # 2. CRAIG (WMS ortho régionale)
    try:
        caps_c, hc = capacites_wms(CRAIG_WMS)
        cat["services"]["craig_wms"] = {"url": CRAIG_WMS, "n_couches": len(caps_c), "sha256_capacites": hc}
        cand += [dict(c, service="craig", url=CRAIG_WMS, nom_complet="craig:" + c["nom"]) for c in caps_c
                 if c["nom"] == "ortho" or (annees(c["nom"]) and max(annees(c["nom"])) >= 2022)]
    except RuntimeError as e:
        cat["services"]["craig_wms"] = {"url": CRAIG_WMS, "erreur": str(e)[:200]}
    # 3. Grenoble-Alpes Métropole (geoflux) : couches raster ortho
    try:
        caps_g, hg = capacites_wms(GAM_WMS)
        cat["services"]["gam_wms"] = {"url": GAM_WMS, "n_couches": len(caps_g), "sha256_capacites": hg}
        cand += [dict(c, service="gam", url=GAM_WMS, nom_complet="gam:" + c["nom"]) for c in caps_g
                 if re.search(r"ortho", c["nom"], re.I)]
    except RuntimeError as e:
        cat["services"]["gam_wms"] = {"url": GAM_WMS, "erreur": str(e)[:200]}
    # 4. PCRS CRAIG : open data (WebDAV) et flux RTGE (abonnement)
    cat["pcrs_craig_opendata"] = campagnes_pcrs()
    try:
        cat["services"]["craig_rtge_pcrs"] = {"url": CRAIG_RTGE.split("?")[0],
                                              "http": requests.get(CRAIG_RTGE, timeout=60).status_code,
                                              "remarque": "PCRS 5 cm 2025 (RVB + IRC, juin-juillet 2025) : flux sur abonnement, non utilisé"}
    except requests.RequestException as e:
        cat["services"]["craig_rtge_pcrs"] = {"erreur": str(e)[:200]}

    # graphe de mosaïquage BD ORTHO (édition courante = PVA 2024 sur l'Isère) et 2021-2023
    for nom, tn in (("courant", "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho"),
                    ("2021-2023", "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE.2021-2023:graphe_bdortho")):
        g = graphe_bdortho(tn)
        cat["graphe_bdortho"][nom] = [{k: v for k, v in f.items() if k != "anneaux"} for f in g]
        if nom == "courant":
            ecrire_json(SORTIE / "graphe_bdortho_2024.json", {"typename": tn, "emprise_l93": BBOX, "polygones": g})
            grille = {}
            for nm, (xl, yl) in ZONES_DATES.items():
                grille[nm] = date_au_point(g, O[0] + xl, O[1] + yl)
            cat["graphe_bdortho"]["dates_aux_points"] = grille

    # couverture de chaque candidate (1 m/px sur l'emprise) et image de référence 2024
    ref, _ = wms_image(IGN_WMS, REF_2024, BBOX, 1.0)
    ref_hp = passe_haut(ref[..., :3].mean(axis=2)) if ref is not None else None
    r21, _ = wms_image(IGN_WMS, REF_2021, BBOX, 1.0)
    r21_hp = passe_haut(r21[..., :3].mean(axis=2)) if r21 is not None else None
    for c in cand:
        nom = c.get("nom_complet", c["nom"])
        a, err = wms_image(c["url"], c["nom"], BBOX, 1.0)
        e = {"couche": nom, "service": c["service"], "titre": c["titre"], "resume": c["resume"][:200]}
        if a is None:
            e.update(couverture_emprise=None, erreur=err)
        else:
            cv, sd = couverture(a)
            e.update(couverture_emprise=cv, ecart_type=sd)
            if cv > 0.5 and ref_hp is not None:
                hp = passe_haut(a[..., :3].mean(axis=2))
                e["ncc_avec_ign_2024"] = ncc_max(hp, ref_hp)
                if r21_hp is not None:
                    e["ncc_avec_ign_2021"] = ncc_max(hp, r21_hp)
        cat["couches"].append(e)
        print(f"{nom:55s} couverture={e.get('couverture_emprise')} ncc2024={e.get('ncc_avec_ign_2024')}", flush=True)
    for e in cat["couches"]:
        e.update(dater(e, cat))
    ecrire_json(SORTIE / "catalogue_orthos.json", cat)
    print("->", rel(SORTIE / "catalogue_orthos.json"))


# points de contrôle des dates (local) : cœur et secteur construit 2023-2024
ZONES_DATES = {"centre": (0.0, 0.0), "coeur_NO": (-50.0, 50.0), "coeur_NE": (50.0, 50.0), "coeur_SO": (-50.0, -50.0),
               "coeur_SE": (50.0, -50.0), "est": (110.0, 0.0), "sud_est": (110.0, -110.0), "nord_est": (110.0, 110.0),
               "sud": (0.0, -130.0), "ouest": (-130.0, 0.0), "nord": (0.0, 130.0)}


def dater(e, cat):
    """Date(s) d'acquisition d'une couche sur Meylan et décision de téléchargement."""
    nom, cv = e["couche"], e.get("couverture_emprise") or 0.0
    g = cat["graphe_bdortho"].get("courant", [])
    dates_2024 = sorted({f["date_vol"] for f in g if f.get("pva") == 2024 and f.get("echelle") == 20})
    d = {"dates": [], "methode_date": None, "posterieure_pcrs_2022": None}
    if cv < 0.5:
        d.update(decision="ignoree", raison="pas de données sur l'emprise (couverture < 50 %)")
        return d
    ncc_ = e.get("ncc_avec_ign_2024")
    a = annees(nom.split(":")[-1])
    if nom in ("ORTHOIMAGERY.ORTHOPHOTOS2024", "ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024") or (
            ncc_ is not None and ncc_ >= 0.8 and not re.search(r"SAT", nom)):
        d.update(dates=dates_2024, posterieure_pcrs_2022=True,
                 methode_date="graphe de mosaïquage BD ORTHO (WFS, PVA 2024 Isère)" + (
                     "" if nom.endswith("2024") and "EXPRESS" not in nom and "craig" not in nom
                     else f" ; même prise de vue que ORTHOPHOTOS2024 (NCC passe-haut {ncc_})"))
    elif "2021-2023" in nom or (e.get("ncc_avec_ign_2021") or 0) >= 0.8:
        g2 = cat["graphe_bdortho"].get("2021-2023", [])
        d.update(dates=sorted({f["date_vol"] for f in g2 if f.get("dep") == "38"}), posterieure_pcrs_2022=False,
                 methode_date="graphe de mosaïquage BD ORTHO 2021-2023 (Isère : PVA 2021)" + (
                     "" if "2021-2023" in nom else f" ; même prise de vue que ORTHOPHOTOS2021 (NCC {e.get('ncc_avec_ign_2021')})"))
    elif nom in DATES_ESTIMEES:
        de = DATES_ESTIMEES[nom]
        d.update(dates=de["dates"], posterieure_pcrs_2022=de["posterieure_pcrs_2022"],
                 methode_date=de["methode"])
    elif a:
        d.update(dates=[str(max(a))], posterieure_pcrs_2022=(True if max(a) >= 2023 else (False if max(a) < 2022 else None)),
                 methode_date="année du nom de couche (aucune métadonnée de date publique)")
    if nom in NATIVES:
        dbl = ncc_ is not None and ncc_ >= 0.98 and nom != REF_2024
        d.update(decision="doublon" if dbl else "telecharger",
                 raison="image identique à ORTHOPHOTOS2024" if dbl else "datée après mai 2022, couvrante")
    elif d.get("posterieure_pcrs_2022") is False:
        d.update(decision="ignoree", raison="antérieure au PCRS 2022 (5 cm) déjà exploité")
    elif ncc_ is not None and ncc_ >= 0.8:
        d.update(decision="doublon", raison=f"même image que ORTHOPHOTOS2024 (NCC {ncc_}) : téléchargée sous ce nom")
    else:
        d.update(decision="a_examiner", raison="couvrante, date non établie")
    return d


# --------------------------------------------------------------------------- téléchargement
def telecharger(couches=None, workers=4):
    cat = lire_json(SORTIE / "catalogue_orthos.json")
    par_nom = {e["couche"]: e for e in cat["couches"]}
    bilan = {}
    for nom, spec in NATIVES.items():
        if couches and nom not in couches:
            continue
        e = par_nom.get(nom, {})
        if e.get("decision") not in ("telecharger",):
            print(f"{nom}: {e.get('decision')} ({e.get('raison')}) -> non téléchargée")
            continue
        service = "craig" if nom.startswith("craig:") else "ign"
        src = {"url": CRAIG_WMS if service == "craig" else IGN_WMS, "layers": nom.split(":")[-1],
               "version": "1.3.0", "crs": "EPSG:2154", "format": spec["fmt"]}
        out = RAW / spec["tag"]
        out.mkdir(parents=True, exist_ok=True)
        tuiles = list(pipeline_ortho.grid(BBOX, spec["res"]))
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(workers) as ex:
            index = list(ex.map(lambda b: pipeline_ortho.fetch_tile(src, b, out, spec["tag"], spec["res"]), tuiles))
        lic, attr = LICENCES[service]
        if "ORTHO-SAT" in nom:
            attr = "CNES (attribution de la couche WMS) – diffusion IGN Géoplateforme (data.geopf.fr)"
        meta = {"couche": nom, "service": src["url"], "res_m": spec["res"], "format_wms": spec["fmt"],
                "emprise_demandee_l93": BBOX, "dates_acquisition": e.get("dates"), "methode_date": e.get("methode_date"),
                "licence": lic, "attribution": f"{attr}, couche {nom.split(':')[-1]}",
                "telecharge_le": dt.date.today().isoformat(), "genere": "recon/pcg/enrichir/orthos_recentes.py --telecharger",
                "tuiles": [dict(t, sha256=sha256(out / t["file"])) for t in index]}
        ecrire_json(out / "index.json", meta)
        bilan[nom] = {"dossier": rel(out), "n_tuiles": len(index), "res_m": spec["res"]}
        print(f"{nom}: {len(index)} tuiles -> {rel(out)}")
    ecrire_json(SORTIE / "telechargements.json", bilan)


# --------------------------------------------------------------------------- mosaïques
class Mosaique:
    """Dalles géoréférencées (jpg + jgw) d'un dossier ; lecture d'une fenêtre L93 à une résolution donnée."""

    def __init__(self, dossier: Path, motif="*.jpg"):
        self.dalles = []
        for f in sorted(Path(dossier).glob(motif)):
            w = f.with_suffix(".jgw")
            if not w.exists():
                continue
            a = [float(v) for v in w.read_text().split()]
            res = a[0]
            W, H = Image.open(f).size
            self.dalles.append((f, a[4] - res / 2, a[5] + res / 2, res, W, H))
        if not self.dalles:
            raise FileNotFoundError(f"aucune dalle géoréférencée dans {dossier}")
        self.res = self.dalles[0][3]

    @lru_cache(maxsize=64)
    def _img(self, f):
        return Image.open(f).convert("RGB")

    def fenetre(self, x0, y0, x1, y1, res=None, filtre=Image.BICUBIC) -> Image.Image:
        """Image de la boîte [x0, x1] x [y0, y1] (L93) à `res` m/px (sous-pixel exact, `box` de PIL)."""
        r = self.res
        res = res or r
        c0, c1 = math.floor(x0 / r + 1e-6) - 1, math.ceil(x1 / r - 1e-6) + 1
        l0, l1 = math.floor(y0 / r + 1e-6) - 1, math.ceil(y1 / r - 1e-6) + 1
        can = Image.new("RGB", (c1 - c0, l1 - l0), (0, 0, 0))
        for f, gx, gy, _, W, H in self.dalles:
            tc, tl = round(gx / r), round(gy / r)          # colonne gauche, ligne haute (indices globaux)
            if tc >= c1 or tc + W <= c0 or tl - H >= l1 or tl <= l0:
                continue
            can.paste(self._img(f), (tc - c0, l1 - tl))
        box = ((x0 / r - c0), (l1 - y1 / r), (x1 / r - c0), (l1 - y0 / r))
        size = (round((x1 - x0) / res), round((y1 - y0) / res))
        return can.resize(size, filtre, box=box)


@lru_cache(maxsize=None)
def mosaique(tag: str) -> Mosaique:
    if tag == "pcrs2022":
        return Mosaique(PCRS)
    return Mosaique(RAW / tag)


# --------------------------------------------------------------------------- recalage
def correlation_phase(a, b):
    """Décalage (dx, dy) en pixels tel que b(u, v) ≈ a(u − dx, v − dy) ; pic sous-pixel parabolique."""
    h, w = a.shape
    win = np.outer(np.hanning(h), np.hanning(w))
    A, B = np.fft.fft2(a * win), np.fft.fft2(b * win)
    R = B * np.conj(A)
    R /= np.abs(R) + 1e-9
    c = np.fft.ifft2(R).real
    j, i = np.unravel_index(np.argmax(c), c.shape)
    pk = c[j, i]
    second = np.sort(c.ravel())[-20]

    def sub(cm, c0, cp):
        d = cm - 2 * c0 + cp
        return 0.5 * (cm - cp) / d if d != 0 else 0.0
    di = sub(c[j, (i - 1) % w], pk, c[j, (i + 1) % w])
    dj = sub(c[(j - 1) % h, i], pk, c[(j + 1) % h, i])
    dx = (i + di) if i <= w // 2 else (i + di - w)
    dy = (j + dj) if j <= h // 2 else (j + dj - h)
    return float(dx), float(dy), float(pk), float(pk / max(second, 1e-9))


def recaler(tags=None):
    """Décalage de chaque ortho récente par rapport au PCRS 2022 (référence de la description).

    Fenêtres carrées (côté max(40 m ; 100 px), recouvrement de moitié) sur l'emprise ; images passe-haut
    à la résolution de la couche ; corrélation de phase, pic net (rapport >= 2,5). Couches à 20 cm :
    référence PCRS 2022 ; couches plus grossières : IGN 2024 (lui-même recalé sur le PCRS). Le décalage
    retenu est la médiane du groupe de mesures le plus dense (rayon 2 px) : les fenêtres dominées par
    les toits d'immeubles (déversement en visée oblique) en sont exclues.
    Convention : position vraie (cadre PCRS) = position lue sur la couche − (dx, dy)."""
    tags = tags or [v["tag"] for v in NATIVES.values() if (RAW / v["tag"]).exists()]
    t24 = NATIVES[REF_2024]["tag"]
    res_out = {}
    for tag in sorted(tags, key=lambda s: s != t24):
        m = mosaique(tag)
        if m.res > 0.6:
            res_out[tag] = {"remarque": "résolution trop grossière (> 0,6 m) pour un recalage utile"}
            continue
        r = max(m.res, 0.2)
        if r <= 0.25:
            ref, base, nref = mosaique("pcrs2022"), (0.0, 0.0), "PCRS 2022"
        else:
            ref, nref = mosaique(t24), "IGN 2024"
            base = (res_out.get(t24, {}).get("dx_m", 0.0), res_out.get(t24, {}).get("dy_m", 0.0))
        cote = max(40.0, 100 * r)
        mes = []
        for xc in np.arange(BBOX[0] + cote / 2, BBOX[2] - cote / 2 + 1e-6, cote / 2):
            for yc in np.arange(BBOX[1] + cote / 2, BBOX[3] - cote / 2 + 1e-6, cote / 2):
                b = (xc - cote / 2, yc - cote / 2, xc + cote / 2, yc + cote / 2)
                bb = (b[0] + base[0], b[1] + base[1], b[2] + base[0], b[3] + base[1])
                a0 = np.asarray(ref.fenetre(*bb, res=r, filtre=Image.BOX).convert("L"), float)
                a1 = np.asarray(m.fenetre(*b, res=r).convert("L"), float)
                if a1.mean() < 5:
                    continue
                dx, dy, pk, rap = correlation_phase(passe_haut(a0, 9), passe_haut(a1, 9))
                if rap >= 2.5:
                    mes.append([round(float(xc), 1), round(float(yc), 1), round(dx * r + base[0], 3),
                                round(-dy * r + base[1], 3), round(rap, 1)])
        if not mes:
            res_out[tag] = {"n_fenetres": 0, "reference": nref}
            continue
        a = np.array([[v[2], v[3]] for v in mes])
        voisins = [(np.hypot(*(a - a[k]).T) <= 2 * r).sum() for k in range(len(a))]
        k0 = int(np.argmax(voisins))
        grp = np.hypot(*(a - a[k0]).T) <= 2 * r
        med = np.median(a[grp], axis=0)
        mad = np.median(np.abs(a[grp] - med), axis=0) * 1.4826
        for k, v in enumerate(mes):
            v.append(bool(grp[k]))
        res_out[tag] = {"dx_m": round(float(med[0]), 3), "dy_m": round(float(med[1]), 3),
                        "mad_m": [round(float(mad[0]), 3), round(float(mad[1]), 3)], "n_fenetres": len(mes),
                        "n_retenues": int(grp.sum()), "reference": nref, "res_calcul_m": r, "cote_fenetre_m": cote,
                        "fenetres_[x,y,dx,dy,rapport_pic,retenue]": mes}
        print(f"{tag}: décalage / PCRS 2022 = ({med[0]:+.2f}, {med[1]:+.2f}) m ± ({mad[0]:.2f}, {mad[1]:.2f}) "
              f"({int(grp.sum())}/{len(mes)} fenêtres, réf. {nref})")
    ecrire_json(SORTIE / "recalage.json", {"convention": "position cadre PCRS 2022 = position lue sur la couche − (dx_m, dy_m)",
                                           "reference": "PCRS 5 cm Grenoble-Alpes Métropole 2022-05-10", "couches": res_out})


@lru_cache(maxsize=1)
def decalages():
    p = SORTIE / "recalage.json"
    if not p.exists():
        return {}
    return {k: (v.get("dx_m", 0.0), v.get("dy_m", 0.0)) for k, v in lire_json(p)["couches"].items() if "dx_m" in v}


# --------------------------------------------------------------------------- description (superposition)
def _feats(p):
    p = Path(p)
    return lire_json(p).get("features", []) if p.exists() else []


@lru_cache(maxsize=1)
def couches_description():
    base = DESC / "base"
    return {"bordures": _feats(base / "bordures.geojson"), "marquages": _feats(base / "marquages.geojson"),
            "ilots": _feats(base / "ilots.geojson"), "ponctuels": _feats(base / "ponctuels_sol.geojson"),
            "mobilier": _feats(DONNEES / "objets/mobilier.geojson"), "arbres": _feats(DONNEES / "objets/arbres.geojson"),
            "surfaces_v1": _feats(DONNEES / "surfaces/surfaces_2026.geojson")}


COUL_MQ = {"conserve": (60, 255, 60), "neuf_2025": (255, 60, 255), "refait_2025_identique": (0, 220, 255)}
COUL_MOB = {"lampadaire": (255, 230, 0), "support_feux": (255, 40, 40), "panneau": (60, 140, 255),
            "potelet": (255, 255, 255), "poteau_reseau": (200, 140, 60)}


class Panneau:
    """Image d'une fenêtre L93 (une source) avec grille locale et, en option, la description."""

    def __init__(self, tag, b, px=600, titre=""):
        self.b, self.px = b, px
        self.res = (b[2] - b[0]) / px
        dxy = decalages().get(tag, (0.0, 0.0))          # on lit la couche décalée -> cadre PCRS
        bb = (b[0] + dxy[0], b[1] + dxy[1], b[2] + dxy[0], b[3] + dxy[1])
        try:
            self.im = mosaique(tag).fenetre(*bb, res=self.res)
        except FileNotFoundError:
            self.im = Image.new("RGB", (px, round((b[3] - b[1]) / self.res)), (40, 40, 40))
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.titre = titre

    def P(self, x, y):
        return ((x - self.b[0]) / self.res, (self.b[3] - y) / self.res)

    def grille(self, pas=5.0, etiquette=10.0):
        f = _police(12)
        x0l, y0l = self.b[0] - O[0], self.b[1] - O[1]
        x1l, y1l = self.b[2] - O[0], self.b[3] - O[1]
        for v in np.arange(math.ceil(x0l / pas) * pas, x1l + 1e-6, pas):
            u = self.P(O[0] + v, 0)[0]
            fort = abs(v / etiquette - round(v / etiquette)) < 1e-6
            self.d.line([(u, 0), (u, self.im.height)], fill=(255, 255, 0, 110 if fort else 55), width=1)
            if fort:
                self.d.text((u + 2, self.im.height - 14), f"{v:+.0f}", fill=(255, 255, 0, 255), font=f)
        for v in np.arange(math.ceil(y0l / pas) * pas, y1l + 1e-6, pas):
            w = self.P(0, O[1] + v)[1]
            fort = abs(v / etiquette - round(v / etiquette)) < 1e-6
            self.d.line([(0, w), (self.im.width, w)], fill=(255, 255, 0, 110 if fort else 55), width=1)
            if fort:
                self.d.text((2, w + 1), f"{v:+.0f}", fill=(255, 255, 0, 255), font=f)
        if self.titre:
            self.d.rectangle([0, 0, 8 * len(self.titre) + 6, 18], fill=(0, 0, 0, 170))
            self.d.text((3, 2), self.titre, fill=(255, 255, 255, 255), font=_police(13))

    def _ligne(self, co, col, w=1):
        pts = [self.P(c[0], c[1]) for c in co]
        if len(pts) >= 2:
            self.d.line(pts, fill=col, width=w)

    def description(self):
        C = couches_description()
        x0, y0, x1, y1 = self.b

        def proche(g):
            co = np.asarray([c[:2] for c in _coords(g)])
            return len(co) and co[:, 0].max() >= x0 - 2 and co[:, 0].min() <= x1 + 2 and co[:, 1].max() >= y0 - 2 and co[:, 1].min() <= y1 + 2
        for f in C["surfaces_v1"]:
            if f["properties"].get("etat") == "construit_2023_2024" and proche(f["geometry"]):
                for poly in polygones(f["geometry"]):
                    self._ligne(poly[0] + [poly[0][0]], (255, 150, 0, 120), 1)
        for f in C["bordures"]:
            if proche(f["geometry"]):
                col = (255, 120, 0, 230) if f["properties"].get("zone_travaux_2025") else (235, 235, 235, 220)
                self._ligne(f["geometry"]["coordinates"], col, 1)
        for f in C["ilots"]:
            if proche(f["geometry"]):
                for poly in polygones(f["geometry"]):
                    self._ligne(poly[0] + [poly[0][0]], (255, 255, 0, 200), 1)
        for f in C["marquages"]:
            g = f["geometry"]
            if not proche(g):
                continue
            col = COUL_MQ.get(f["properties"].get("etat"), (200, 200, 200)) + (230,)
            if g["type"] in ("LineString",):
                self._ligne(g["coordinates"], col, 1)
            elif g["type"] == "MultiLineString":
                for l_ in g["coordinates"]:
                    self._ligne(l_, col, 1)
            else:
                for poly in polygones(g):
                    self._ligne(poly[0] + [poly[0][0]], col, 1)
        for f in C["mobilier"]:
            g = f["geometry"]
            if not proche(g):
                continue
            t = f["properties"].get("type")
            if g["type"] == "LineString":
                self._ligne(g["coordinates"], (180, 120, 60, 200), 1)
                continue
            u, v = self.P(*g["coordinates"][:2])
            col = COUL_MOB.get(t, (0, 255, 255))
            self.d.rectangle([u - 3, v - 3, u + 3, v + 3], outline=col + (255,), width=2)
        for f in C["arbres"]:
            g = f["geometry"]
            if not proche(g):
                continue
            p = f["properties"]
            u, v = self.P(*g["coordinates"][:2])
            st = str(p.get("statut_2026") or "")
            col = (255, 80, 80) if "absent" in st else ((80, 200, 255) if "planté 2025" in st else (60, 255, 60))
            rr = max(2.0, (p.get("diametre_couronne_m") or 0) / 2 / self.res)
            self.d.ellipse([u - rr, v - rr, u + rr, v + rr], outline=col + (120,), width=1)
            self.d.line([(u - 3, v), (u + 3, v)], fill=col + (255,))
            self.d.line([(u, v - 3), (u, v + 3)], fill=col + (255,))


def _coords(g):
    t, c = g["type"], g["coordinates"]
    if t == "Point":
        return [c]
    if t in ("LineString", "MultiPoint"):
        return c
    if t in ("Polygon", "MultiLineString"):
        return [p for r in c for p in r]
    if t == "MultiPolygon":
        return [p for poly in c for r in poly for p in r]
    return []


# --------------------------------------------------------------------------- planches
def fenetres():
    """Fenêtres de recensement (L93) : cœur ± 75 m (3 x 3 de 50 m) et secteur construit 2023-2024."""
    out = {}
    noms = {(-1, 1): "NO", (0, 1): "N", (1, 1): "NE", (-1, 0): "O", (0, 0): "C", (1, 0): "E",
            (-1, -1): "SO", (0, -1): "S", (1, -1): "SE"}
    for (i, j), n in noms.items():
        xc, yc = O[0] + 50 * i, O[1] + 50 * j
        out[f"coeur_{n}"] = (xc - 25, yc - 25, xc + 25, yc + 25)
    # secteur construit 2023-2024 (surfaces « construit_2023_2024 » : x local 15..150, y local -150..141)
    for k, (yl0, yl1) in enumerate(((75, 150), (0, 75), (-75, 0), (-150, -75))):
        out[f"est_{k + 1}"] = (O[0] + 75, O[1] + yl0, O[0] + 150, O[1] + yl1)
    out["sud_1"] = (O[0], O[1] - 150, O[0] + 75, O[1] - 75)
    out["nord_1"] = (O[0], O[1] + 75, O[0] + 75, O[1] + 150)
    return out


def planche(nom, b, px=600, sources=None, sortie=None):
    sources = sources or [("pcrs2022", f"PCRS 5 cm {DATE_PCRS}", False),
                          (NATIVES[REF_2024]["tag"], "IGN 2024 (20 cm, 30/07-10/08/2024)", False),
                          (NATIVES[REF_2024]["tag"], "IGN 2024 + description", True),
                          (NATIVES["ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025"]["tag"], "Pléiades 2025 (50 cm)", False)]
    pans = []
    for tag, titre, desc in sources:
        p = Panneau(tag, b, px, titre)
        if desc:
            p.description()
        p.grille()
        pans.append(p.im)
    w, h = pans[0].size
    ncol = 2
    nl = math.ceil(len(pans) / ncol)
    im = Image.new("RGB", (ncol * w + (ncol - 1) * 6, nl * h + (nl - 1) * 6 + 22), (25, 25, 25))
    for k, p in enumerate(pans):
        im.paste(p, ((k % ncol) * (w + 6), 22 + (k // ncol) * (h + 6)))
    d = ImageDraw.Draw(im)
    bl = local(b[0], b[1])
    d.text((4, 3), f"{nom} : local x {bl[0]:+.0f}..{bl[0] + b[2] - b[0]:+.0f}, y {bl[1]:+.0f}..{bl[1] + b[3] - b[1]:+.0f} m "
                   f"(grille 5 m, étiquettes = coordonnées locales) ; {((b[2] - b[0]) / px) * 100:.1f} cm/px",
           fill=(255, 255, 255), font=_police(14))
    sortie = sortie or (SORTIE / "planches" / f"{nom}.jpg")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    im.save(sortie, quality=90)
    return {"planche": rel(sortie), "emprise_l93": [round(v, 2) for v in b], "px_panneau": px,
            "res_m": round((b[2] - b[0]) / px, 4), "panneaux": [s[1] for s in sources],
            "decalages_appliques": {s[0]: decalages().get(s[0], (0.0, 0.0)) for s in sources}}


def carte_changements(b=BBOX, res=0.5):
    """Différence 2022 -> 2024 par blocs de 1 m (couleur moyenne), après recalage ; rouge = changement."""
    t24 = NATIVES[REF_2024]["tag"]
    a0 = np.asarray(mosaique("pcrs2022").fenetre(*b, res=res, filtre=Image.BOX), float)
    dxy = decalages().get(t24, (0.0, 0.0))
    a1 = np.asarray(mosaique(t24).fenetre(b[0] + dxy[0], b[1] + dxy[1], b[2] + dxy[0], b[3] + dxy[1], res=res), float)
    # normalisation radiométrique globale (moyenne / écart type par canal)
    a1n = (a1 - a1.mean((0, 1))) / a1.std((0, 1)) * a0.std((0, 1)) + a0.mean((0, 1))
    d = np.sqrt(((a1n - a0) ** 2).sum(axis=2))
    k = max(1, round(1.0 / res))
    H, W = d.shape[0] // k * k, d.shape[1] // k * k
    blocs = d[:H, :W].reshape(H // k, k, W // k, k).mean(axis=(1, 3))
    seuil = float(np.percentile(blocs, 85))
    g = Image.fromarray(a1.astype(np.uint8)).convert("L").convert("RGB")
    rouge = Image.new("RGB", g.size, (255, 0, 0))
    m = (np.kron(blocs > seuil, np.ones((k, k))) * 140).astype(np.uint8)
    mm = np.zeros(d.shape, np.uint8)
    mm[:H, :W] = m
    im = Image.composite(rouge, g, Image.fromarray(mm))
    p = Panneau.__new__(Panneau)
    p.b, p.res, p.im, p.titre = b, res, im, f"changements 2022 -> 2024 (> P85 = {seuil:.0f})"
    p.d = ImageDraw.Draw(im, "RGBA")
    p.grille(pas=10.0, etiquette=50.0)
    s = SORTIE / "planches" / "carte_changements_2022_2024.jpg"
    s.parent.mkdir(parents=True, exist_ok=True)
    im.save(s, quality=88)
    return rel(s)


def planches(noms=None, px=600):
    idx = {}
    for nom, b in fenetres().items():
        if noms and nom not in noms:
            continue
        idx[nom] = planche(nom, b, px)
        print("planche", idx[nom]["planche"])
    tp = NATIVES["ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025"]["tag"]
    for nom, (x0, y0, x1, y1) in {"vue_pleiades_coeur": (-75, -75, 75, 75), "vue_pleiades_est": (40, -150, 150, -40),
                                  "vue_pleiades_ne": (40, -40, 150, 70)}.items():
        if noms and nom not in noms:
            continue
        idx[nom] = planche(nom, (O[0] + x0, O[1] + y0, O[0] + x1, O[1] + y1), 700,
                           sources=[(NATIVES[REF_2024]["tag"], "IGN 2024-08-09", False), (tp, "Pléiades 2025 (recalé)", False)])
    try:
        idx["_carte_changements"] = carte_changements()
    except FileNotFoundError as e:
        idx["_carte_changements"] = str(e)
    old = lire_json(SORTIE / "planches/index.json") if (SORTIE / "planches/index.json").exists() else {}
    old.update(idx)
    ecrire_json(SORTIE / "planches/index.json", old)


# --------------------------------------------------------------------------- contrôles 2024 (bordures, marquages)
VERCORS_AXE = [(1.1, -5.5), (3.9, -11.3), (14.6, -33.8), (38.0, -129.0), (41.3, -143.3)]   # local, BD TOPO


def _dist_polyligne(x, y, axe):
    best = 1e9
    for (ax, ay), (bx, by) in zip(axe[:-1], axe[1:]):
        vx, vy = bx - ax, by - ay
        t_ = max(0.0, min(1.0, ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)))
        best = min(best, math.hypot(x - ax - t_ * vx, y - ay - t_ * vy))
    return best


@lru_cache(maxsize=1)
def batiments_recents():
    """Emprises BD TOPO créées en 2025 ou après (immeubles neufs du secteur est), en L93 (sommets denses)."""
    from pyproj import Transformer
    tr = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    p = RACINE / "data/sites/paquet_jardin/vector/bdtopo_batiment.geojson"
    out = []
    for f in (lire_json(p).get("features", []) if p.exists() else []):
        if str(f["properties"].get("date_creation") or "") < "2025":
            continue
        for poly in polygones(f["geometry"]):
            a = np.asarray([tr.transform(*c[:2]) for c in poly[0]])
            seg = [a[k] + (a[k + 1] - a[k]) * s for k in range(len(a) - 1) for s in np.linspace(0, 1, 20, endpoint=False)]
            out.append(np.asarray(seg))
    return out


class Raster:
    """Image d'une couche sur l'emprise (recalée sur le PCRS), échantillonnage bilinéaire en L93."""

    def __init__(self, tag, res=0.2, b=BBOX):
        dx, dy = decalages().get(tag, (0.0, 0.0))
        self.b, self.r = b, res
        self.a = np.asarray(mosaique(tag).fenetre(b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy, res=res), float)

    @classmethod
    def depuis(cls, a, b, r):
        o = cls.__new__(cls)
        o.a, o.b, o.r = a, b, r
        return o

    def __call__(self, x, y):
        a = self.a
        u = (np.asarray(x) - self.b[0]) / self.r - 0.5
        v = (self.b[3] - np.asarray(y)) / self.r - 0.5
        u = np.clip(u, 0, a.shape[1] - 1.001)
        v = np.clip(v, 0, a.shape[0] - 1.001)
        i, j = np.floor(u).astype(int), np.floor(v).astype(int)
        fu, fv = u - i, v - j
        if a.ndim == 3:
            fu, fv = fu[..., None], fv[..., None]
        return (a[j, i] * (1 - fu) * (1 - fv) + a[j, i + 1] * fu * (1 - fv) + a[j + 1, i] * (1 - fu) * fv
                + a[j + 1, i + 1] * fu * fv)


def echantillons(co, pas=0.4, marge=0.3):
    """Points et normales unitaires le long d'une polyligne (L93), tous les `pas` m, sans les extrémités."""
    co = np.asarray([c[:2] for c in co], float)
    seg = np.diff(co, axis=0)
    lg = np.hypot(seg[:, 0], seg[:, 1])
    ok = lg > 1e-6
    co = np.vstack([co[:1], co[1:][ok]])
    seg, lg = seg[ok], lg[ok]
    if not len(lg):
        return np.zeros((0, 2)), np.zeros((0, 2))
    s = np.concatenate([[0], np.cumsum(lg)])
    L = s[-1]
    ts = np.arange(marge, L - marge + 1e-9, pas) if L > 2 * marge + 0.1 else np.array([L / 2])
    k = np.clip(np.searchsorted(s, ts, side="right") - 1, 0, len(lg) - 1)
    f = (ts - s[k]) / lg[k]
    P = co[k] + seg[k] * f[:, None]
    T = seg[k] / lg[k][:, None]
    N = np.stack([-T[:, 1], T[:, 0]], axis=1)
    return P, N


def profil_bord(P, N, G, D=np.round(np.arange(-1.2, 1.2001, 0.1), 2), h=0.2):
    """Réponse de bord |dI/dn| médiane le long de la ligne pour chaque décalage normal d."""
    S = []
    for d in D:
        a = G(P[:, 0] + (d + h) * N[:, 0], P[:, 1] + (d + h) * N[:, 1])
        b = G(P[:, 0] + (d - h) * N[:, 0], P[:, 1] + (d - h) * N[:, 1])
        S.append(np.median(np.abs(a - b)))
    return D, np.array(S)


def _contraste_marquage(g, p, gris):
    """Contraste peinture − abords (niveaux de gris) et luminance moyenne ; None si non mesurable."""
    if g["type"] in ("LineString", "MultiLineString") and p.get("classe") != "passage":
        lignes = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        cs, ib = [], []
        for l_ in lignes:
            P, N = echantillons(l_, pas=0.2, marge=0.1)
            if not len(P):
                continue
            best = None
            q = 70 if p.get("type") == "discontinue" else 50
            for d in (-0.2, -0.1, 0.0, 0.1, 0.2):
                c_ = gris(P[:, 0] + d * N[:, 0], P[:, 1] + d * N[:, 1])
                side = 0.5 * (gris(P[:, 0] + (d + 0.5) * N[:, 0], P[:, 1] + (d + 0.5) * N[:, 1])
                              + gris(P[:, 0] + (d - 0.5) * N[:, 0], P[:, 1] + (d - 0.5) * N[:, 1]))
                val = float(np.percentile(c_ - side, q))
                if best is None or val > best:
                    best = val
            cs.append(best)
            ib.append(float(np.mean(gris(P[:, 0], P[:, 1]))))
        return (float(np.median(cs)), float(np.mean(ib))) if cs else None
    if g["type"] == "LineString":                       # passage piéton : axe -> bandes de part et d'autre
        P, N = echantillons(g["coordinates"], pas=0.2, marge=0.1)
        if not len(P):
            return None
        v_ = gris(P[:, 0], P[:, 1])
        ref = np.concatenate([gris(P[:, 0] + s * 3.0 * N[:, 0], P[:, 1] + s * 3.0 * N[:, 1]) for s in (-1, 1)])
        return float(np.percentile(v_, 75) - np.median(ref)), float(np.mean(v_))
    pts = [np.asarray([c[:2] for c in poly[0]]) for poly in polygones(g)]
    if not pts:
        return None
    xs = np.concatenate([q[:, 0] for q in pts])
    ys = np.concatenate([q[:, 1] for q in pts])
    X, Y = np.meshgrid(np.arange(xs.min(), xs.max(), 0.1), np.arange(ys.min(), ys.max(), 0.1))
    X, Y = X.ravel(), Y.ravel()
    if len(X) > 6000:
        return None
    dedans = np.array([any(dans_anneau(x, y, q) for q in pts) for x, y in zip(X, Y)])
    if dedans.sum() < 3:
        return None
    vin = gris(X[dedans], Y[dedans])
    xc, yc = X[dedans].mean(), Y[dedans].mean()
    rr = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2 + 0.6
    ang = np.linspace(0, 2 * np.pi, 36, endpoint=False)
    vout = gris(xc + rr * np.cos(ang), yc + rr * np.sin(ang))
    return float(np.percentile(vin, 70) - np.median(vout)), float(np.mean(vin))


def controles_2024():
    """Contrôle automatique des bordures et marquages de la description sur l'ortho IGN 2024 (20 cm).

    Bordures : profil de réponse de bord (gradient normal) pour des décalages de −1,2 à +1,2 m ; pic net
    (rapport pic / médiane du profil >= 1,6) à |d| <= 0,4 m -> « vu » ; pic fort plus loin -> « décalé ? » ;
    végétation (NDVI IRC 2024 > 0,15) ou ombre (gris < 55) des deux côtés -> « masqué ». Marquages :
    contraste de luminance peinture − abords (± 0,5 m) le long de la ligne, dans le polygone ou sur l'axe
    du passage ; >= 15 « vu », < 4 sur fond clair « absent ? », sinon « incertain ». Résultats revus
    visuellement sur les planches `controle_<fenêtre>.jpg` (verdicts finaux : saisie/revue_controles.json)."""
    t24 = NATIVES[REF_2024]["tag"]
    G = Raster(t24)
    gris = Raster.depuis(G.a.mean(axis=2), G.b, G.r)
    irc = Raster(NATIVES["ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024"]["tag"])
    ndvi = Raster.depuis((irc.a[..., 0] - irc.a[..., 1]) / (irc.a[..., 0] + irc.a[..., 1] + 1e-6), G.b, G.r)
    p22 = Raster("pcrs2022", res=0.1)
    gris22 = Raster.depuis(p22.a.mean(axis=2), p22.b, p22.r)
    del p22
    C = couches_description()
    zt = [f for f in C["bordures"] if f["properties"].get("zone_travaux_2025")]
    pts_trav = np.vstack([np.asarray([c[:2] for c in f["geometry"]["coordinates"]]) for f in zt]) if zt else np.zeros((0, 2))
    res = {"bordures": {}, "marquages": {}}
    bat = batiments_recents()

    def d_bat(x, y):
        return round(min((float(np.min(np.hypot(b[:, 0] - x, b[:, 1] - y))) for b in bat), default=1e9), 1)

    def contexte(x, y):
        d_trav = float(np.min(np.hypot(pts_trav[:, 0] - x, pts_trav[:, 1] - y))) if len(pts_trav) else 1e9
        d_verc = _dist_polyligne(x - O[0], y - O[1], VERCORS_AXE) if y - O[1] < -15 else 1e9
        return round(d_trav, 1), round(d_verc, 1)

    for f in C["bordures"]:
        g, p = f["geometry"], f["properties"]
        co = np.asarray([c[:2] for c in g["coordinates"]])
        if not (co[:, 0].max() > BBOX[0] and co[:, 0].min() < BBOX[2] and co[:, 1].max() > BBOX[1] and co[:, 1].min() < BBOX[3]):
            continue
        P, N = echantillons(g["coordinates"])
        if not len(P):
            continue
        D, S = profil_bord(P, N, gris)
        k = int(np.argmax(S))
        rap = float(S[k] / (float(np.median(S)) + 1e-6))
        cote = [(P[:, 0] + s * 0.6 * N[:, 0], P[:, 1] + s * 0.6 * N[:, 1]) for s in (1, -1)]
        veg = float(np.mean((ndvi(*cote[0]) > 0.15) & (ndvi(*cote[1]) > 0.15)))
        omb = float(np.mean((gris(*cote[0]) < 55) & (gris(*cote[1]) < 55)))
        if veg > 0.5:
            v = "masque_vegetation"
        elif omb > 0.5:
            v = "masque_ombre"
        elif rap >= 1.6 and abs(D[k]) <= 0.4:
            v = "vu"
        elif rap >= 1.8:
            v = "decale?"
        else:
            v = "non_vu"
        D2, S2 = profil_bord(P, N, gris22, h=0.1)
        k2 = int(np.argmax(S2))
        rap2 = float(S2[k2] / (float(np.median(S2)) + 1e-6))
        vu22 = rap2 >= 1.6 and abs(D2[k2]) <= 0.4
        if v == "vu" and vu22 and abs(D2[k2] - D[k]) <= 0.3:
            v2 = "vu_2022_2024"
        elif v == "vu":
            v2 = "vu_2024_seul"
        else:
            v2 = v
        xm, ym = P[len(P) // 2]
        dt_, dv = contexte(xm, ym)
        res["bordures"][p["id"]] = {"verdict_auto": v, "verdict_2_dates": v2, "d_pic_2022_m": float(D2[k2]),
                                    "rapport_pic_2022": round(rap2, 2), "d_pic_m": float(D[k]), "rapport_pic": round(rap, 2),
                                    "reponse_0": round(float(S[np.argmin(np.abs(D))]), 1), "reponse_pic": round(float(S[k]), 1),
                                    "vegetation": round(veg, 2), "ombre": round(omb, 2), "n_ech": int(len(P)),
                                    "longueur_m": round(float(p.get("longueur_m") or 0), 2),
                                    "zone_travaux_2025": bool(p.get("zone_travaux_2025")),
                                    "milieu_l93": [round(float(xm), 2), round(float(ym), 2)],
                                    "normale": [round(float(N[len(N) // 2][0]), 3), round(float(N[len(N) // 2][1]), 3)],
                                    "d_zone_travaux_m": dt_, "d_axe_vercors_m": dv, "d_batiment_recent_m": d_bat(xm, ym)}
    for f in C["marquages"]:
        g, p = f["geometry"], f["properties"]
        co = np.asarray([c[:2] for c in _coords(g)])
        if not len(co) or not (BBOX[0] < co[:, 0].mean() < BBOX[2] and BBOX[1] < co[:, 1].mean() < BBOX[3]):
            continue
        r_ = _contraste_marquage(g, p, gris)
        if r_ is None:
            continue
        contr, lum = r_
        xm, ym = co.mean(axis=0)
        veg = float(np.mean(ndvi(co[:, 0], co[:, 1]) > 0.15))
        v = "masque_vegetation" if veg >= 0.3 else (
            "vu" if contr >= 15 else ("absent?" if contr < 4 and lum > 60 else "incertain"))
        dt_, dv = contexte(xm, ym)
        res["marquages"][p["id"]] = {"verdict_auto": v, "contraste": round(contr, 1), "luminance": round(lum, 1),
                                     "vegetation": round(veg, 2), "longueur_m": round(float(p.get("longueur_m") or 0), 2),
                                     "etat": p.get("etat"), "classe": p.get("classe"), "type": p.get("type"),
                                     "milieu_l93": [round(float(xm), 2), round(float(ym), 2)],
                                     "d_zone_travaux_m": dt_, "d_axe_vercors_m": dv}
    import collections
    for fam in res:
        print(fam, dict(collections.Counter(v["verdict_auto"] for v in res[fam].values())))
    print("bordures (2 dates)", dict(collections.Counter(v["verdict_2_dates"] for v in res["bordures"].values())))
    ecrire_json(SORTIE / "controles_2024.json", {"image": REF_2024, "date": "2024-08-09", "genere": "orthos_recentes.py --controles",
                                                 "regles": controles_2024.__doc__, **res})
    return res


COUL_V = {"vu_2022_2024": (40, 255, 40), "vu_2024_seul": (190, 255, 120), "vu": (40, 255, 40), "decale?": (255, 160, 0), "non_vu": (255, 40, 40), "masque_vegetation": (40, 120, 255),
          "masque_ombre": (150, 150, 255), "absent?": (255, 40, 40), "incertain": (255, 230, 0)}


def planches_controle(noms=None, px=800):
    """2024 brut | 2024 + bordures et marquages colorés par verdict automatique, étiquetés."""
    ctl = lire_json(SORTIE / "controles_2024.json")
    C = couches_description()
    t24 = NATIVES[REF_2024]["tag"]
    f_ = _police(11)
    for nom, b in fenetres().items():
        if noms and nom not in noms:
            continue
        p0 = Panneau(t24, b, px, "IGN 2024-08-09")
        p0.grille()
        p1 = Panneau(t24, b, px, "contrôle auto 2024")
        for f in C["bordures"]:
            r_ = ctl["bordures"].get(f["properties"]["id"])
            if not r_:
                continue
            col = COUL_V[r_.get("verdict_2_dates", r_["verdict_auto"])] + (255,)
            p1._ligne(f["geometry"]["coordinates"], col, 2)
            x, y = r_["milieu_l93"]
            if r_["longueur_m"] >= 1.0 and b[0] <= x <= b[2] and b[1] <= y <= b[3]:
                u, v = p1.P(x, y)
                p1.d.text((u + 3, v - 6), f["properties"]["id"][2:], fill=col, font=f_)
        for f in C["marquages"]:
            r_ = ctl["marquages"].get(f["properties"]["id"])
            if not r_:
                continue
            col = COUL_V[r_["verdict_auto"]] + (230,)
            g = f["geometry"]
            if g["type"] == "LineString":
                p1._ligne(g["coordinates"], col, 1)
            elif g["type"] == "MultiLineString":
                for l_ in g["coordinates"]:
                    p1._ligne(l_, col, 1)
            else:
                for poly in polygones(g):
                    p1._ligne(poly[0] + [poly[0][0]], col, 1)
            x, y = r_["milieu_l93"]
            if b[0] <= x <= b[2] and b[1] <= y <= b[3]:
                u, v = p1.P(x, y)
                p1.d.text((u + 3, v + 2), f["properties"]["id"], fill=col, font=f_)
        p1.grille()
        w, h = p0.im.size
        im = Image.new("RGB", (2 * w + 6, h + 22), (25, 25, 25))
        im.paste(p0.im, (0, 22))
        im.paste(p1.im, (w + 6, 22))
        d = ImageDraw.Draw(im)
        d.text((4, 3), f"{nom} : vert vu 2022+2024 (vert clair 2024 seul), orange décalé ?, rouge non vu / absent ?, bleu masqué (végétation / ombre), "
                       f"jaune incertain ; bordures étiquetées sans le préfixe K-", fill=(255, 255, 255), font=_police(14))
        s = SORTIE / "planches" / f"controle_{nom}.jpg"
        im.save(s, quality=90)
        print(rel(s))


def _entite(fam, id_):
    for f in couches_description()[fam]:
        if f["properties"].get("id") == id_:
            return f
    return None


def planche_vignettes(fam, ids, nom, cote=12.0, px=260, sources=("pcrs2022", None), ncol=3):
    """Planche-contact : pour chaque entité, vignettes PCRS 2022 | IGN 2024 centrées sur elle (cote m),
    géométrie de la description en trait fin translucide ; id et verdict automatique en légende."""
    t24 = NATIVES[REF_2024]["tag"]
    srcs = [s or t24 for s in sources]
    ctl = lire_json(SORTIE / "controles_2024.json").get(fam, {})
    cel = []
    for id_ in ids:
        f = _entite(fam, id_)
        if f is None:
            continue
        co = np.asarray([c[:2] for c in _coords(f["geometry"])])
        xc, yc = (ctl.get(id_, {}).get("milieu_l93") or co.mean(axis=0).tolist())
        b = (xc - cote / 2, yc - cote / 2, xc + cote / 2, yc + cote / 2)
        ims = []
        for s in srcs:
            p = Panneau(s, b, px)
            g = f["geometry"]
            col = (255, 0, 255, 150)
            if g["type"] == "Point":
                u, v = p.P(*g["coordinates"][:2])
                rr = max(0.3, (f["properties"].get("diametre_couronne_m") or 1.0) / 2) / p.res
                p.d.ellipse([u - rr, v - rr, u + rr, v + rr], outline=col, width=1)
                p.d.line([(u - 4, v), (u + 4, v)], fill=col)
                p.d.line([(u, v - 4), (u, v + 4)], fill=col)
            elif g["type"] == "LineString":
                p._ligne(g["coordinates"], col, 1)
            elif g["type"] == "MultiLineString":
                for l_ in g["coordinates"]:
                    p._ligne(l_, col, 1)
            else:
                for poly in polygones(g):
                    p._ligne(poly[0] + [poly[0][0]], col, 1)
            p.grille(pas=1.0 if cote <= 15 else 5.0, etiquette=5.0)
            ims.append(p.im)
        c = Image.new("RGB", (len(ims) * px + (len(ims) - 1) * 3, px + 16), (20, 20, 20))
        for k, im in enumerate(ims):
            c.paste(im, (k * (px + 3), 16))
        r_ = ctl.get(id_, {})
        txt = f"{id_} {r_.get('verdict_2_dates', r_.get('verdict_auto', ''))} " + (
            f"c={r_.get('contraste')}" if "contraste" in r_ else f"d24={r_.get('d_pic_m')} d22={r_.get('d_pic_2022_m')}")
        ImageDraw.Draw(c).text((3, 1), txt, fill=(255, 255, 255), font=_police(12))
        cel.append(c)
    if not cel:
        return None
    w, h = cel[0].size
    nl = math.ceil(len(cel) / ncol)
    im = Image.new("RGB", (ncol * w + (ncol - 1) * 8, nl * h + (nl - 1) * 8), (60, 60, 60))
    for k, c in enumerate(cel):
        im.paste(c, ((k % ncol) * (w + 8), (k // ncol) * (h + 8)))
    s = SORTIE / "planches" / "vignettes" / f"{nom}.jpg"
    s.parent.mkdir(parents=True, exist_ok=True)
    im.save(s, quality=90)
    return rel(s)


# --------------------------------------------------------------------------- observations (format OBS)
SOURCES_OBS = {
    "ign2024": {"tag": NATIVES[REF_2024]["tag"], "couche": REF_2024, "date": None, "libelle": "BD ORTHO IGN 2024 (20 cm)"},
    "irc2024": {"tag": NATIVES["ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024"]["tag"], "couche": "ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024",
                "date": None, "libelle": "BD ORTHO IRC 2024 (20 cm)"},
    "pleiades2025": {"tag": NATIVES["ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025"]["tag"], "couche": "ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025",
                     "date": None, "libelle": "Pléiades 2025 (50 cm)"},
}


def _date_source(cle, xy):
    cat = lire_json(SORTIE / "catalogue_orthos.json")
    if cle in ("ign2024", "irc2024"):
        g = lire_json(SORTIE / "graphe_bdortho_2024.json")["polygones"]
        return date_au_point(g, *xy) or "2024-08"
    e = {c["couche"]: c for c in cat["couches"]}.get(SOURCES_OBS[cle]["couche"], {})
    return (e.get("dates") or ["2025"])[0]


def pixel_tuile(tag, x, y):
    """Dalle et pixel continu (u, v) du point L93 (x, y) lu sur la couche (décalage de recalage ajouté)."""
    m = mosaique(tag)
    dx, dy = decalages().get(tag, (0.0, 0.0))
    xs, ys = x + dx, y + dy
    for f, gx, gy, r, W, H in m.dalles:
        u, v = (xs - gx) / r, (gy - ys) / r
        if 0 <= u < W and 0 <= v < H:
            return rel(f), [round(u, 1), round(v, 1)]
    return None, None


def zone_travaux(x, y):
    """Libellé de la zone de travaux 2025 / construite 2023-2024 au point (surfaces v1, bordures)."""
    C = couches_description()
    for f in C["surfaces_v1"]:
        for poly in polygones(f["geometry"]):
            if dans_anneau(x, y, poly[0]):
                e = f["properties"].get("etat")
                return {"modifie_2025": "zone de travaux 2025", "construit_2023_2024": "secteur construit 2023-2024"}.get(
                    e, "hors zone de travaux 2025")
    return "hors zone de travaux 2025"


def _fenetre_de(x, y):
    for nom, b in fenetres().items():
        if b[0] <= x < b[2] and b[1] <= y < b[3]:
            return nom
    return None


def _validite_auto(v, x, y):
    z = zone_travaux(x, y)
    if v.get("d_zone_travaux_m", 1e9) <= 3 or z == "zone de travaux 2025":
        return {"valeur": "incertain", "raison": "à moins de 3 m de la zone de travaux 2025 (image d'août 2024)", "zone_travaux_2025": z}
    if v.get("d_axe_vercors_m", 1e9) <= 15:
        return {"valeur": "incertain", "raison": "abords de l'avenue du Vercors (trottoirs refaits jusqu'au 30/01/2026)", "zone_travaux_2025": z}
    return {"valeur": True, "raison": "hors zone de travaux 2025 ; image du 09/08/2024 postérieure aux constructions 2023-2024", "zone_travaux_2025": z}


def _obs_auto(id_, lien, classe, sous_type, v, attributs, controle, confiance):
    x, y = v["milieu_l93"]
    t24 = NATIVES[REF_2024]["tag"]
    tuile, uv = pixel_tuile(t24, x, y)
    fen = _fenetre_de(x, y)
    return {"id": id_, "source": f"ortho_recente:{REF_2024}", "date_image": "2024-08-09", "classe": classe, "sous_type": sous_type,
            "attributs": attributs, "position": {"l93": [round(x, 3), round(y, 3)], "local": local(x, y), "precision_m": 0.3,
                                                 "methode": "pixel_ortho"},
            "lien_description": lien, "statut": "confirme", "valide_2026": _validite_auto(v, x, y), "confiance": confiance,
            "preuve": {"planche": rel(SORTIE / "planches" / f"controle_{fen}.jpg") if fen else None, "dalle": tuile, "pixels": uv,
                       "recalage_m": decalages().get(t24, (0.0, 0.0)), "fichier": rel(SORTIE / "controles_2024.json")},
            "controle": controle}


def construire_obs():
    """Observations au format OBS -> obs_ortho_recentes.json.

    1. relevés visuels de Claude (saisie/observations.json : coordonnées locales lues sur la grille des planches,
       déjà dans le cadre PCRS) ;
    2. bordures confirmées : revue visuelle (secteur construit 2023-2024, IGN 2024 seul) ou contrôle automatique
       sur deux dates (PCRS 2022 + IGN 2024, même bord à 0,3 m près, longueur >= 2 m, à plus de 12 m des immeubles
       neufs dont les toits déversés créent de faux bords), hors zone de travaux 2025 et hors rejets visuels ;
    3. marquages « conservés » vus sur l'IGN 2024 (seconde date indépendante du PCRS 2022), hors rejets visuels.
    Aucune absence n'est émise automatiquement."""
    import collections
    saisie = lire_json(SORTIE / "saisie/observations.json")
    rev = lire_json(SORTIE / "saisie/revue_controles.json")
    ctl = lire_json(SORTIE / "controles_2024.json")
    out = []
    for s in saisie["observations"]:
        src = SOURCES_OBS[s["source"]]
        xl, yl = s["xy_local"]
        x, y = l93(xl, yl)
        tuile, uv = pixel_tuile(src["tag"], x, y)
        date = s.get("date_image") or _date_source(s["source"], (x, y))
        o = {"id": s["id"], "source": f"ortho_recente:{src['couche']}", "date_image": date,
             "classe": s["classe"], "sous_type": s.get("sous_type"), "attributs": s.get("attributs", {}),
             "position": {"l93": [x, y], "local": [round(xl, 3), round(yl, 3)], "precision_m": s.get("precision_m", 0.5),
                          "methode": "pixel_ortho"},
             "lien_description": s.get("lien_description"), "statut": s["statut"],
             "valide_2026": dict(s["valide_2026"], zone_travaux_2025=zone_travaux(x, y)),
             "confiance": s.get("confiance", "moyenne"),
             "preuve": {"planche": s.get("planche"), "dalle": tuile, "pixels": uv,
                        "recalage_m": decalages().get(src["tag"], (0.0, 0.0)), "fichier": s.get("planche")},
             "controle": "visuel"}
        if s.get("geometrie_local"):
            o["geometrie_l93"] = [l93(a, b) for a, b in s["geometrie_local"]]
        out.append(o)
    liens_manuels = {s.get("lien_description") for s in saisie["observations"]}
    rb = rev["bordures"]
    rej = set(rb["rejetees_visuel"]["ids"]) | set(rb["rejetees_echantillon_2_dates"]["ids"]) | liens_manuels
    vis = set(rb["confirmees_visuel"]["ids"])
    n_k = {"visuel": 0, "automatique_2_dates": 0}
    for kid, v in sorted(ctl["bordures"].items()):
        if kid in rej or v["zone_travaux_2025"]:
            continue
        if kid in vis:
            controle = "visuel"
        elif (v.get("verdict_2_dates") == "vu_2022_2024" and v["longueur_m"] >= 2.0
              and v.get("d_batiment_recent_m", 1e9) > 12.0):
            controle = "automatique_2_dates"
        else:
            continue
        if zone_travaux(*v["milieu_l93"]) == "zone de travaux 2025":
            continue
        att = {"observe": "arête de bordure visible le long de la ligne décrite"
                          + (" en 2022 et en 2024" if controle == "automatique_2_dates" else " en août 2024"),
               "ecart_normal_2024_m": v["d_pic_m"], "rapport_pic_2024": v["rapport_pic"], "longueur_m": v["longueur_m"],
               "methode": "profil de gradient normal (−1,2..+1,2 m) ; pic à |d| <= 0,4 m"}
        if controle == "automatique_2_dates":
            att.update(ecart_normal_2022_m=v["d_pic_2022_m"], rapport_pic_2022=v["rapport_pic_2022"],
                       precision_echantillon="16 / 20 corrects après filtres (17 / 23 avant) : planches bordures_2dates_echantillon_*")
        out.append(_obs_auto(f"OR-{kid}", kid, "bordure", "arete_visible", v, att, controle, "moyenne"))
        n_k[controle] += 1
    rm = rev["marquages"]
    rejm = set(rm["rejetes_visuel"]["ids"]) | liens_manuels
    n_m = 0
    for mid, v in sorted(ctl["marquages"].items()):
        if mid in rejm or v["etat"] != "conserve" or v["verdict_auto"] != "vu" or v.get("d_zone_travaux_m", 1e9) <= 1.0:
            continue
        fort = v["contraste"] >= 25 and ((v.get("longueur_m") or 0) >= 2.0 or v["classe"] in ("fleche", "symbole", "zone"))
        att = {"observe": "peinture visible sur l'IGN du 09/08/2024 à l'emplacement décrit (seconde date après le PCRS 2022)",
               "contraste_2024": v["contraste"], "luminance_2024": v["luminance"], "longueur_m": v.get("longueur_m"),
               "methode": "contraste peinture − abords (± 0,5 m) >= 15 niveaux ; NDVI IRC 2024 < 0,15",
               "precision_echantillon": "18 / 22 corrects (planches marquages_conserve_vu_echantillon_*) ; erreurs : voiture blanche, feuillage"}
        out.append(_obs_auto(f"OR-{mid}", mid, "marquage", "peinture_visible_2024", v, att, "automatique_2e_date",
                             "moyenne" if fort else "faible"))
        n_m += 1
    ecrire_json(OBS, out)
    meta = {"agent": "ORTHOS-RECENTES", "n": len(out), "genere": "recon/pcg/enrichir/orthos_recentes.py --obs",
            "images": {k: v["libelle"] for k, v in SOURCES_OBS.items()},
            "comptes": {"visuel_manuel": len(saisie["observations"]), "bordures": n_k, "marquages_automatique_2e_date": n_m,
                        "statuts": dict(collections.Counter(o["statut"] for o in out)),
                        "valide_2026": dict(collections.Counter(str(o["valide_2026"]["valeur"]) for o in out))},
            "saisie_sha256": sha256(SORTIE / "saisie/observations.json"),
            "revue_sha256": sha256(SORTIE / "saisie/revue_controles.json"),
            "controles_sha256": sha256(SORTIE / "controles_2024.json")}
    ecrire_json(SORTIE / "meta_obs.json", meta)
    print(f"{len(out)} observations -> {rel(OBS)}", meta["comptes"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decouvrir", action="store_true")
    ap.add_argument("--telecharger", action="store_true")
    ap.add_argument("--couches", nargs="*")
    ap.add_argument("--recaler", action="store_true")
    ap.add_argument("--planches", action="store_true")
    ap.add_argument("--fenetres", nargs="*")
    ap.add_argument("--decoupe", nargs=4, type=float, metavar=("XL0", "YL0", "XL1", "YL1"),
                    help="planche libre en coordonnées locales")
    ap.add_argument("--px", type=int, default=600)
    ap.add_argument("--controles", action="store_true")
    ap.add_argument("--obs", action="store_true")
    a = ap.parse_args()
    if a.decouvrir:
        decouvrir()
    if a.telecharger:
        telecharger(a.couches)
    if a.recaler:
        recaler()
    if a.planches:
        planches(a.fenetres, a.px)
    if a.decoupe:
        b = (O[0] + a.decoupe[0], O[1] + a.decoupe[1], O[0] + a.decoupe[2], O[1] + a.decoupe[3])
        nom = "decoupe_" + "_".join(f"{v:+.0f}" for v in a.decoupe)
        print(planche(nom, b, a.px)["planche"])
    if a.controles:
        controles_2024()
        planches_controle(a.fenetres)
    if a.obs:
        construire_obs()


if __name__ == "__main__":
    main()
