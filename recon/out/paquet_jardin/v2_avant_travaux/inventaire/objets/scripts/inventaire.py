"""Recensement des OBJETS de l'état avant travaux (printemps 2025, avant le 23/06/2025) et de leurs preuves.

Usage (depuis la racine du dépôt) :
    python -I recon/out/paquet_jardin/v2_avant_travaux/inventaire/objets/scripts/inventaire.py

Entrées (lecture seule) :
  - description 2026 résolue : recon/out/paquet_jardin/v2/description/resolue/objets/{mobilier,arbres}.geojson
  - observations V2 : recon/out/paquet_jardin/v2/enrichi/recensement/obs_*.json (seules celles < 23/06/2025 valent preuve)
  - triangulations V2 : recensement/mapillary/triangulation_mixte.json
  - constats : analysis/paquet_jardin/constats_verifies.json (dates des constats cités en source)
  - poses : enrichi/poses/poses.json (Panoramax), recensement/mapillary/poses/poses_mapillary.json
  - téléchargements (données publiques, traitées comme non fiables) : data/sites/paquet_jardin/avant_travaux/
      mapillary_map_features/, osm_historique/, panoramax_semantique/
Sorties : objets_avant_travaux.geojson, objets_exclus.geojson, inventaire_stats.json (dossier objets/).
"""
from __future__ import annotations

import collections
import datetime
import math
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_at import (DEBUT_TRAVAUX, FENETRE, FENETRE_PHOTOS, O, RACINE, SORTIE, SUPPORTS, TELE, TYPES,  # noqa: E402
                       Batiments, Zones, dans_emprise, ecrire, lire, type_desc_2026, type_mapillary, type_osm,
                       wgs_l93)

R2026 = RACINE / "recon/out/paquet_jardin/v2/description/resolue/objets"
REC = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement"
GAMMA = -2.0086          # azimut grille du nord vrai au site (azimut_L93 = azimut_vrai + GAMMA)
D_ORTHO22 = "2022-05-10"
D_LIDAR = "2021-08-12"
D_ORTHO24 = "2024-08-09"
D_PNX_2026 = "2026-07-28"

Z = Zones()
BAT = Batiments()


def dans_fenetre(d, f=FENETRE):
    return bool(d) and f[0] <= d[:10] < f[1]


def ms_date(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime("%Y-%m-%d")


# ============================================================================ index des photos Panoramax (id8 -> date)
PNX_INDEX = lire(RACINE / "data/sites/paquet_jardin/panoramax_pictures.geojson")
ID8_DATE = {}
for f in PNX_INDEX["features"]:
    p = f["properties"]
    ID8_DATE[p["id"][:8]] = p["datetime"][:10]
for ph in lire(RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json")["photos"]:
    ID8_DATE.setdefault(ph["id8"], ph["date"])

CONSTATS = {}
_SRC_DATE = {"street_p2025_05_360": "2025-05-18", "street_p2025_01_vercors": "2025-01-12",
             "street_p2025_08_travaux": "2025-08-31", "street_p2026_07_ign": D_PNX_2026, "lidar_historique": D_LIDAR}
for c in lire(RACINE / "analysis/paquet_jardin/constats_verifies.json"):
    sa = c.get("source_analyse", "")
    d = c.get("date_source") or _SRC_DATE.get(sa) or (D_ORTHO22 if sa.startswith("ortho") else None)
    CONSTATS[c["id"]] = (sa, (d or "")[:10] or None)

# ============================================================================ objets
OBJ = []          # liste de dicts
PAR_ID = {}


def nouvel(oid, typ, st, x, y, origine, sigma, geom=None, **kw):
    o = {"id": oid, "type": typ, "sous_type": st, "x": float(x), "y": float(y), "origine": origine, "sigma_m": sigma,
         "geom": geom or {"type": "Point", "coordinates": [round(float(x), 3), round(float(y), 3)]},
         "preuves": [], "absences": [], "osm_ids": set(), "mly_ids": set(), "notes": [], "lien_2026": None,
         "statut_2026": None, "code": None, "hauteur_m": None, "hauteur_src": None, "azimut_face_deg": None,
         "azimut_src": None, "fusionnes": []}
    o.update(kw)
    OBJ.append(o)
    PAR_ID[oid] = o
    return o


def preuve(o, source, ref, date, nature, **kw):
    """nature : photo | detection_auto | ortho | lidar | osm | leve_gam | inventaire | plan_projet | post_travaux |
    pendant_travaux | constat"""
    e = {"source": source, "id": ref, "date": date, "nature": nature}
    e.update({k: v for k, v in kw.items() if v is not None})
    for x in o["preuves"]:
        if x["source"] == source and x["id"] == ref and x["nature"] == nature:
            return x
    o["preuves"].append(e)
    return e


def plus_proche(x, y, typ, rayon, compat=None, exclure=None):
    best, bd = None, rayon
    types = {typ} | (compat or set())
    for o in OBJ:
        if o["type"] not in types or o is exclure:
            continue
        if o["geom"]["type"] == "LineString":
            P = np.asarray(o["geom"]["coordinates"], float)
            A, B = P[:-1], P[1:]
            AB = B - A
            L2 = np.maximum((AB ** 2).sum(1), 1e-12)
            t = np.clip(((np.array([x, y]) - A) * AB).sum(1) / L2, 0, 1)
            Q = A + t[:, None] * AB
            d = float(np.hypot(*(np.array([x, y]) - Q).T).min())
        else:
            d = math.hypot(o["x"] - x, o["y"] - y)
        if d < bd:
            best, bd = o, d
    return best, bd


# ---------------------------------------------------------------------------- 1. description 2026 résolue
RX_DATE = re.compile(r"(20\d\d-\d\d(?:-\d\d)?)")
RX_HEX8 = re.compile(r"\b([0-9a-f]{8})\b")
RX_OSM = re.compile(r"(node|way)/(\d+)(?:\s*\((20\d\d-\d\d-\d\d)\))?")
RX_OBS = re.compile(r"\b(ORTHO[_-][AB]?-?\d+|PANO2026-\d+|VISION-PANORAMAX-\d-\d+|MLY-[A-Z]+-\d+|OR-[A-Z]-\d+|pano_\d-\d+)\b")
RX_CONSTAT = re.compile(r"\b((?:reviree_no|p20\d\d_\d\d_[a-z0-9]+|coeur|verdun_ne|verdun_so|vercors_s|abords_est|hist)-\d+)\b")

OBS = {}   # id observation -> observation (toutes dates)
for fobs in sorted(REC.glob("obs_*.json")):
    for ob in lire(fobs):
        ob["_fichier"] = fobs.name
        OBS[ob["id"]] = ob


def date_obs(ob):
    d = (ob.get("date_image") or "")[:10]
    if d == "2025":                 # Pléiades 2025 (date non publiée, probablement avant le 23/06/2025)
        return "2025"
    return d or None


def nature_obs(ob):
    s = ob.get("source", "")
    if s.startswith("ortho2022"):
        return "ortho", "ortho PCRS 5 cm 2022"
    if s.startswith("ortho_recente"):
        return "ortho", "ortho récente (IGN 09/08/2024 ou Pléiades 2025)"
    if s.startswith("mly:"):
        return "photo", "Mapillary"
    return "photo", "Panoramax"


PRESENCE = {"confirme", "attribut_corrige", "position_corrigee", "absent_de_description"}


def lier_obs(o, oid, ob):
    """Preuve (ou absence) tirée d'une observation V2 liée à l'objet."""
    nat, lib = nature_obs(ob)
    d = date_obs(ob)
    if ob.get("statut") == "absent_sur_image":
        o["absences"].append({"source": lib, "id": oid, "date": d, "detail": "objet absent sur l'image"})
        return
    if d and d != "2025" and d >= DEBUT_TRAVAUX:
        nat = "pendant_travaux" if d < "2025-12-05" else "post_travaux"
    elif ob.get("statut") not in PRESENCE:
        nat = "indice"
    preuve(o, lib, oid, d, nat, statut=ob.get("statut"))
    a = ob.get("attributs") or {}
    tr = str(a.get("type_reel") or a.get("type_observe") or "")
    if tr and nat in ("photo", "ortho", "indice"):
        o["notes"].append(f"{oid} ({d}) : {tr[:160]}")
        if o["type"] == "lampadaire" and "sans luminaire" in tr and "poteau" in tr:
            o["type"], o["sous_type"] = "poteau", "reseau_bois"
            o["notes"].append(f"type corrigé lampadaire -> poteau de réseau d'après {oid}")


def parse_source(o, s, champ="source"):
    """Preuves datées tirées du champ texte « source » d'un objet de la description 2026."""
    if not s:
        return
    for seg in re.split(r";", s):
        sl = seg.lower()
        dates = RX_DATE.findall(seg)
        for typ, num, dd in RX_OSM.findall(seg):
            o["osm_ids"].add(f"{typ}/{num}")
            if dd:
                nat = "osm" if dd < DEBUT_TRAVAUX else "post_travaux"
                preuve(o, "osm", f"{typ}/{num}", dd, nat, detail="version OSM citée par la description 2026")
        if "lidar" in sl:
            preuve(o, "lidar2021", "LiDAR HD IGN (vols 12/08 et 06/09/2021)", D_LIDAR, "lidar", detail=seg.strip()[:160])
        if ("ortho" in sl and "2022" in seg) or "ombre" in sl or re.search(r"ortho\s*#?\s*\(", sl):
            if "2024" in seg and "2022" not in seg:
                preuve(o, "ortho_ign_2024", "BD ORTHO IGN 09/08/2024", D_ORTHO24, "ortho", detail=seg.strip()[:160])
            else:
                preuve(o, "ortho_pcrs_2022", "PCRS 5 cm 10/05/2022", D_ORTHO22, "ortho", detail=seg.strip()[:160])
        if "ortho ign 2024" in sl or "ortho 2024" in sl:
            preuve(o, "ortho_ign_2024", "BD ORTHO IGN 09/08/2024", D_ORTHO24, "ortho", detail=seg.strip()[:160])
        if ("panoramax" in sl or "photo" in sl) and "pano2026" not in sl:
            ids = [h for h in RX_HEX8.findall(seg) if h in ID8_DATE]
            for h in ids:
                d = ID8_DATE[h]
                nat = "photo" if d < DEBUT_TRAVAUX else ("pendant_travaux" if d < "2025-12-05" else "post_travaux")
                if "annotation" in sl:
                    nat = "detection_auto" if d < DEBUT_TRAVAUX else nat
                preuve(o, "panoramax", h, d, nat, detail=seg.strip()[:160])
            if not ids and dates:
                for d in dates:
                    d10 = d if len(d) == 10 else d + "-15"
                    nat = "photo" if d10 < DEBUT_TRAVAUX else ("pendant_travaux" if d10 < "2025-12-05" else "post_travaux")
                    preuve(o, "panoramax", f"photo {d}", d10, nat, detail=seg.strip()[:160])
        if "plan" in sl and "2025" in seg:
            preuve(o, "plan_projet_2025", "plan projet 2025 calé", "2025", "plan_projet", detail=seg.strip()[:160])
        if "gam" in sl and "plan" not in sl:
            preuve(o, "gam_leve_topo", "Meylan_Topo.dwg (gam_topo_sol_*)", None, "leve_gam",
                   detail="levé GAM identique à data/sites/paquet_jardin/etat_2026 (date de levé non publiée)")
        if "gtfs sem 2026" in sl:
            preuve(o, "gtfs_sem_2026", "GTFS SEM 2026", "2026", "post_travaux")
        if "inventaire" in sl:
            preuve(o, "inventaire_arbres_gam", "inventaire des arbres de la Métropole", None, "inventaire", detail=seg.strip()[:120])
        for oid in RX_OBS.findall(seg):
            ob = OBS.get(oid)
            d = date_obs(ob) if ob else (D_PNX_2026 if oid.startswith("PANO2026") else None)
            if oid.startswith("PANO2026"):
                preuve(o, "panoramax", oid, D_PNX_2026, "post_travaux")
            elif ob is not None:
                lier_obs(o, oid, ob)
        for cid in RX_CONSTAT.findall(seg):
            sa, d = CONSTATS.get(cid, (None, None))
            if d is None:
                m = re.match(r"p(20\d\d)_(\d\d)", cid)
                d = f"{m.group(1)}-{m.group(2)}-15" if m else None
            if d:
                nat = "constat" if d < DEBUT_TRAVAUX else ("pendant_travaux" if d < "2025-12-05" else "post_travaux")
                preuve(o, f"constat ({sa or 'analyse'})", cid, d, nat)


desc_mob = lire(R2026 / "mobilier.geojson")
for f in desc_mob["features"]:
    p = f["properties"]
    typ, st = type_desc_2026(p)
    g = f["geometry"]
    if g["type"] == "Point":
        x, y = g["coordinates"][:2]
        geom = None
    else:
        P = np.asarray(g["coordinates"], float)[:, :2]
        x, y = P.mean(0)
        geom = {"type": "LineString", "coordinates": [[round(a, 3), round(b, 3)] for a, b in P]}
    if not dans_emprise(x, y, 5.0):
        continue
    sig = {"haute": 0.25, "moyenne": 0.6, "faible": 1.5}.get(p.get("confiance"), 1.0)
    o = nouvel(p["id"], typ, st, x, y, "description_2026", sig, geom=geom)
    o["lien_2026"] = p["id"]
    o["statut_2026"] = p.get("statut_2026")
    o["code"] = p.get("code")
    o["texte_panneau"] = p.get("texte")
    o["support"] = p.get("poteau") or p.get("support")
    o["hauteur_m"] = p.get("hauteur_m")
    o["hauteur_src"] = "description 2026 (" + ("LiDAR 2021" if p.get("hauteur_lidar_2021_m") else "attribut") + ")"
    if p.get("hauteur_lidar_2021_m"):
        o["hauteur_lidar_2021_m"] = p["hauteur_lidar_2021_m"]
        preuve(o, "lidar2021", "LiDAR HD IGN (vols 12/08 et 06/09/2021)", D_LIDAR, "lidar",
               detail=f"hauteur LiDAR 2021 {p['hauteur_lidar_2021_m']} m")
    if p.get("azimut_deg") is not None:
        o["azimut_face_deg"] = p["azimut_deg"]
        o["azimut_src"] = "description 2026 (azimut_deg, grille L93)"
    o["confiance_2026"] = p.get("confiance")
    o["remarque_2026"] = p.get("remarque")
    parse_source(o, p.get("source"))
    if p.get("osm_id"):
        o["osm_ids"].add(p["osm_id"])
    for dec in (p.get("resolution") or {}).get("decisions", []):
        for oid in dec.get("observations", []) or []:
            ob = OBS.get(oid)
            if ob:
                lier_obs(o, oid, ob)

desc_arb = lire(R2026 / "arbres.geojson")
for f in desc_arb["features"]:
    p = f["properties"]
    x, y = f["geometry"]["coordinates"][:2]
    if not dans_emprise(x, y, 5.0):
        continue
    st = p.get("type")
    if p.get("bosquet") or "sous-étage" in (p.get("etat_2026") or ""):
        st = (st or "") + " (sous-étage de bosquet)"
    sig = {"haute": 0.25, "moyenne": 0.6, "faible": 1.5}.get(p.get("confiance"), 1.0)
    o = nouvel(p["id"], "arbre", st, x, y, "description_2026", sig)
    o["lien_2026"] = p["id"]
    o["statut_2026"] = p.get("statut_2026")
    o["etat_2026_detail"] = p.get("etat_2026")
    o["essence"] = p.get("essence") or p.get("genre")
    o["hauteur_m"] = p.get("hauteur_m")
    o["diametre_couronne_m"] = p.get("diametre_couronne_m")
    h21 = p.get("hauteur_lidar_2021_m")
    o["hauteur_lidar_2021_m"] = h21
    o["hauteur_src"] = "LiDAR 2021 (MNH)" if h21 and h21 >= 2.5 else "défaut (jeune sujet / non mesuré)"
    o["confiance_2026"] = p.get("confiance")
    o["remarque_2026"] = p.get("remarque")
    src = p.get("source") or ""
    parse_source(o, src)
    if h21 is not None and h21 >= 2.5:
        preuve(o, "lidar2021", "LiDAR HD IGN (MNH 2021)", D_LIDAR, "lidar", detail=f"couronne {h21} m")
    elif h21 is not None and h21 < 2.5 and "LiDAR" not in src:
        o["absences"].append({"source": "lidar2021", "date": D_LIDAR, "detail": f"MNH 2021 {h21} m < 2,5 m (absent ou jeune sujet)"})
    v24 = p.get("controle_ortho2024_vegetation")
    if v24 is not None:
        if v24 >= 0.5:
            preuve(o, "ortho_ign_2024", "BD ORTHO IGN 09/08/2024 (contrôle de verdure)", D_ORTHO24, "ortho",
                   detail=f"verdure {v24} au droit du tronc")
        elif v24 < 0.3:
            o["absences"].append({"source": "ortho_ign_2024", "date": D_ORTHO24, "detail": f"verdure {v24} : couronne absente en 08/2024"})
    for dec in (p.get("resolution") or {}).get("decisions", []):
        for oid in dec.get("observations", []) or []:
            ob = OBS.get(oid)
            if ob:
                lier_obs(o, oid, ob)
    if "planté 2025" in (p.get("statut_2026") or ""):
        preuve(o, "plan_projet_2025", "plan projet 2025 (fosse d'arbre)", "2025", "plan_projet")

N_DESC = len(OBJ)

# ---------------------------------------------------------------------------- 2. observations V2 (images < 23/06/2025)
CLASSE_OBS = {"candelabre": "lampadaire", "panneau": "panneau", "feu": "feu", "potelet": "potelet", "abri_bus": "abri_bus",
              "autre_poteau": "poteau", "arbre": "arbre"}


def type_obs(ob):
    c, st = ob.get("classe"), (ob.get("sous_type") or "").lower()
    if c == "potelet" and "j11" in st:
        return "panneau", "balise_J11"
    if c == "potelet" and ("poteau_vide" in st):
        return "poteau", "poteau_vide"
    if c in CLASSE_OBS:
        return CLASSE_OBS[c], st or None
    if c in ("mobilier", "autre"):
        for k, t in (("banc", ("banc", None)), ("corbeille", ("corbeille", None)), ("armoire", ("armoire", st)),
                     ("coffret", ("armoire", st)), ("incendie", ("borne", "incendie")), ("velo", ("arceaux_velos", None)),
                     ("barriere_levante", ("barriere", "barriere_levante")), ("chicane", ("barriere", "chicane")),
                     ("portail", ("barriere", "portail")), ("poteau_arret", ("poteau_arret", None)),
                     ("potelet", ("potelet", None)), ("poteau", ("poteau", st)), ("totem", ("autre_mobilier", st)),
                     ("conteneur", ("autre_mobilier", st)), ("bloc", ("autre_mobilier", st)),
                     ("portique", ("autre_mobilier", st)), ("trottinette", ("autre_mobilier", st))):
            if k in st:
                return t
    return None, None


n_obs_lien, n_obs_new = 0, 0
for oid, ob in OBS.items():
    d = date_obs(ob)
    typ, st = type_obs(ob)
    if typ is None:
        continue
    nat, lib = nature_obs(ob)
    pre = d is not None and d < DEBUT_TRAVAUX
    if not pre:
        nat = "pendant_travaux" if (d and d < "2025-12-05") else "post_travaux"
    liens = [x.strip() for x in re.split(r"[;,]", ob.get("lien_description") or "") if x.strip()]
    pos = (ob.get("position") or {}).get("l93")
    cibles = [PAR_ID[x] for x in liens if x in PAR_ID]
    if cibles:
        for o in cibles:
            lier_obs(o, oid, ob)
            if ob.get("statut") != "absent_sur_image":
                if pre and ob.get("statut") == "position_corrigee" and pos:
                    o.setdefault("positions_observees", []).append({"obs": oid, "l93": pos, "date": d,
                                                                   "precision_m": (ob.get("position") or {}).get("precision_m")})
        n_obs_lien += 1
        continue
    if not pre or not pos or ob.get("statut") not in ("absent_de_description", "confirme", "attribut_corrige", "position_corrigee"):
        continue
    x, y = pos[:2]
    if not dans_emprise(x, y, 2.0):
        continue
    r = TYPES[typ][0]
    o, dd = plus_proche(x, y, typ, r)
    if o is not None:
        preuve(o, lib, oid, d, nat, statut=ob.get("statut"), distance_m=round(dd, 2))
        continue
    prec = (ob.get("position") or {}).get("precision_m") or 1.0
    o = nouvel(f"AT-OBS-{oid}", typ, st, x, y, "observation_v2", float(prec))
    o["notes"].append(f"objet absent de la description 2026, vu le {d} ({lib}) : {str(ob.get('attributs'))[:200]}")
    preuve(o, lib, oid, d, nat, statut=ob.get("statut"))
    h = (ob.get("attributs") or {}).get("hauteur_estimee_m")
    if isinstance(h, (int, float)):
        o["hauteur_m"], o["hauteur_src"] = h, f"estimation visuelle {oid}"
    n_obs_new += 1

# triangulations V2 (positions multi-photos)
TRI = {}
for t in lire(REC / "mapillary/triangulation_mixte.json")["resultats"]:
    TRI[t["entite"]] = t
    o = PAR_ID.get(t["entite"])
    if not o:
        continue
    vues_pre = [v for v in t.get("vues", []) if (v.get("date") or "") < DEBUT_TRAVAUX]
    if vues_pre:
        o["triangulation_v2"] = {"xy_local": t["xy"], "l93": [round(t["xy"][0] + O[0], 3), round(t["xy"][1] + O[1], 3)],
                                 "n_vues": t["n_vues"], "n_inliers": t["n_inliers"],
                                 "ecart_type_m": t.get("ecart_type"), "angle_intersection_deg": t.get("angle_intersection_deg"),
                                 "ecart_description_m": t.get("ecart_description_m"),
                                 "dates_vues": sorted({v["date"] for v in vues_pre})}
        for v in vues_pre:
            src = v["source"]
            preuve(o, "triangulation V2 (" + src.split(":")[0] + ")", src.split(":")[1][:16], v["date"], "photo",
                   detail=f"visée az {v.get('az')}°, {v.get('d_m')} m")

# ---------------------------------------------------------------------------- 3. OSM historique
OSM_DIR = TELE / "osm_historique"
SNAP = {}
for fp in sorted(OSM_DIR.glob("osm_*.json")):
    nom = fp.stem[4:]
    try:
        SNAP[nom] = lire(fp)
    except Exception as e:  # noqa: BLE001
        print("OSM illisible", fp.name, e)
print("instantanés OSM :", sorted(SNAP))


def osm_xy(e):
    if e["type"] == "node":
        return wgs_l93(e["lon"], e["lat"])
    g = e.get("geometry") or []
    if not g:
        return None
    P = np.array([wgs_l93(q["lon"], q["lat"]) for q in g])
    return tuple(P.mean(0))


OSM_SNAP_IDS = {}
OSM_ELEM = {}
for nom, d in SNAP.items():
    ids = set()
    for e in d.get("elements", []):
        t = e.get("tags") or {}
        typ, st = type_osm(t)
        if typ is None:
            continue
        k = f"{e['type']}/{e['id']}"
        ids.add(k)
        xy = osm_xy(e)
        if xy is None or not dans_emprise(*xy, 2.0):
            continue
        OSM_ELEM.setdefault(k, {})[nom] = {"typ": typ, "st": st, "xy": xy, "tags": t, "ts": e.get("timestamp", "")[:10],
                                           "version": e.get("version"),
                                           "geom": [wgs_l93(q["lon"], q["lat"]) for q in e.get("geometry", [])] if e["type"] == "way" else None}
    OSM_SNAP_IDS[nom] = ids

PRE = [n for n in sorted(SNAP) if n != "actuel" and n < DEBUT_TRAVAUX]
REF_OSM = "2025-06-20" if "2025-06-20" in SNAP else (PRE[-1] if PRE else None)
osm_crees, osm_disparus_avant, osm_supprimes_travaux = [], [], []
by_osm = collections.defaultdict(list)
for o in OBJ:
    for k in o["osm_ids"]:
        by_osm[k].append(o)

for k, snaps in OSM_ELEM.items():
    pre_snaps = [n for n in PRE if n in snaps]
    if not pre_snaps:
        continue
    last = snaps[pre_snaps[-1]]
    typ, st = last["typ"], last["st"]
    cibles = by_osm.get(k, [])
    if not cibles:
        r = TYPES[typ][0]
        o, dd = plus_proche(last["xy"][0], last["xy"][1], typ, r, compat=(SUPPORTS if typ in SUPPORTS else None))
        if o is not None and o["type"] == typ:
            cibles = [o]
            o["osm_ids"].add(k)
    present_ref = REF_OSM in snaps if REF_OSM else False
    if not cibles:
        if not present_ref:
            osm_disparus_avant.append({"osm": k, "type": typ, "sous_type": st, "l93": [round(v, 2) for v in last["xy"]],
                                       "instantanes": pre_snaps, "tags": last["tags"]})
            continue
        geom = None
        if last.get("geom") and len(last["geom"]) >= 2:
            geom = {"type": "LineString", "coordinates": [[round(a, 3), round(b, 3)] for a, b in last["geom"]]}
        o = nouvel(f"AT-OSM-{k.replace('/', '-')}", typ, st, last["xy"][0], last["xy"][1], "osm_2025", 1.0, geom=geom)
        o["osm_ids"].add(k)
        o["notes"].append(f"élément OSM présent avant travaux ({', '.join(pre_snaps)}), absent de la description 2026")
        cibles = [o]
    for o in cibles:
        s = snaps[pre_snaps[-1]]
        preuve(o, "osm_historique", k, s["ts"] or None, "osm", instantanes=pre_snaps, version=s["version"],
               detail="présent dans les instantanés Overpass [date:...] " + ", ".join(pre_snaps))
        o.setdefault("osm_instantanes", sorted(set(o.get("osm_instantanes", [])) | set(pre_snaps)))
        if "actuel" in SNAP and k not in OSM_SNAP_IDS.get("actuel", set()) and present_ref:
            o["notes"].append(f"{k} supprimé d'OSM après le {REF_OSM}")
            osm_supprimes_travaux.append(k)
        if REF_OSM and not present_ref:
            o["absences"].append({"source": "osm", "id": k, "date": REF_OSM,
                                  "detail": f"élément OSM absent de l'instantané {REF_OSM} (présent {', '.join(pre_snaps)})"})

# éléments OSM créés après les travaux (pour la comparaison)
for k, snaps in OSM_ELEM.items():
    if "actuel" in snaps and not any(n in snaps for n in PRE):
        s = snaps["actuel"]
        osm_crees.append({"osm": k, "type": s["typ"], "sous_type": s["st"], "l93": [round(v, 2) for v in s["xy"]], "ts": s["ts"]})

# ---------------------------------------------------------------------------- 3b. position avant travaux
RX_DEPL = re.compile(r"décal|déplac|recal|bordure .*2026|plan( projet)? 2025", re.I)
n_pos_rev = 0
DEPLACEMENTS_OSM = []
for o in OBJ:
    o["position_source"] = {"description_2026": "description 2026 résolue", "observation_v2": "observation V2 (avant travaux)",
                            "osm_2025": "OSM (instantané avant travaux)", "mapillary": "Mapillary map feature (±3 m)"}[o["origine"]]
    if o["origine"] != "description_2026" or o["geom"]["type"] != "Point":
        continue
    cand = None
    # A. élément OSM déplacé de plus de 5 m après l'instantané de référence (relogement par les travaux)
    for k in sorted(o["osm_ids"]):
        snaps = OSM_ELEM.get(k, {})
        if REF_OSM in snaps and "actuel" in snaps:
            a, b = snaps[REF_OSM]["xy"], snaps["actuel"]["xy"]
            dmv = math.hypot(b[0] - a[0], b[1] - a[1])
            conf_photo = [q for q in o["preuves"] if q["nature"] in ("photo", "ortho") and q.get("statut") in ("confirme", "attribut_corrige")
                          and q.get("date") and q["date"][:10] < DEBUT_TRAVAUX and q["date"][:10] >= FENETRE[0]]
            if dmv >= 5.0 and conf_photo:
                o["notes"].append(f"{k} déplacé de {dmv:.1f} m dans OSM après le {REF_OSM}, mais la position 2026 est confirmée "
                                  f"avant travaux par {', '.join(q['id'] for q in conf_photo)} : correction OSM, position 2026 conservée")
                break
            if dmv >= 5.0:
                cand = (list(a), 1.0, f"OSM {k} : position de l'instantané {REF_OSM} (élément déplacé de {dmv:.1f} m dans OSM après les travaux)")
                o["deplacement_osm_apres_travaux"] = {"osm": k, "dx": round(b[0] - a[0], 2), "dy": round(b[1] - a[1], 2), "d_m": round(dmv, 2)}
                DEPLACEMENTS_OSM.append({"objet": o["id"], "osm": k, "d_m": round(dmv, 1)})
                if snaps[REF_OSM].get("geom"):
                    o["emprise_osm_avant_l93"] = [[round(u, 2), round(v, 2)] for u, v in snaps[REF_OSM]["geom"]]
                break
            elif dmv >= 1.0:
                o["notes"].append(f"{k} déplacé de {dmv:.1f} m dans OSM après le {REF_OSM} (correction probable) : position 2026 conservée")
    # B. objet dans l'emprise des travaux dont la position 2026 dépend de sources postérieures
    if cand is None:
        d_trav = Z.d_travaux((o["x"], o["y"]))
        txt = " ".join(str(o.get(k) or "") for k in ("remarque_2026", "statut_2026"))
        src_post = any(p["nature"] in ("plan_projet", "post_travaux") for p in o["preuves"]) and not any(
            p["nature"] in ("ortho", "lidar") for p in o["preuves"])
        if not (d_trav <= 3.0 and (RX_DEPL.search(txt) or src_post)):
            continue
        t = TRI.get(o["id"])
        vues_pre = [v for v in (t or {}).get("vues", []) if (v.get("date") or "") < DEBUT_TRAVAUX]
        if t and len(vues_pre) >= 2 and max(t.get("ecart_type") or [9]) <= 0.25 and (t.get("angle_intersection_deg") or 0) >= 20:
            cand = ([t["xy"][0] + O[0], t["xy"][1] + O[1]], 0.25,
                    "triangulation V2 multi-photos avant travaux (" + ", ".join(sorted({v['date'] for v in vues_pre})) + ")")
        elif o.get("positions_observees"):
            po = o["positions_observees"][-1]
            cand = (po["l93"][:2], po.get("precision_m") or 0.5, f"position corrigée sur photo {po['obs']} ({po['date']})")
        else:
            for k in sorted(o["osm_ids"]):
                snaps = OSM_ELEM.get(k, {})
                if REF_OSM in snaps:
                    cand = (list(snaps[REF_OSM]["xy"]), 1.0, f"OSM {k} dans l'instantané {REF_OSM}")
                    break
        if cand is None:
            o["notes"].append("dans l'emprise des travaux : position 2026 conservée faute de position avant travaux")
            continue
    (x, y), sg, lib = cand
    dd = math.hypot(x - o["x"], y - o["y"])
    if dd < 0.05:
        continue
    o["position_2026_l93"] = [round(o["x"], 3), round(o["y"], 3)]
    o["ecart_position_2026_m"] = round(dd, 2)
    o["x"], o["y"], o["sigma_m"] = float(x), float(y), max(sg, 0.1)
    o["geom"] = {"type": "Point", "coordinates": [round(x, 3), round(y, 3)]}
    o["position_source"] = lib
    n_pos_rev += 1
print("positions ramenées à l'état avant travaux :", n_pos_rev)

# ---------------------------------------------------------------------------- 4. Mapillary map features
MF = lire(TELE / "mapillary_map_features/map_features.json")["features"]
IMD = lire(TELE / "mapillary_map_features/images_detection.json")
DET_DIR = TELE / "mapillary_map_features/detections"


def mly_dates(f):
    ids = {x["id"] for x in (f.get("images") or {}).get("data", [])}
    fp = DET_DIR / f"{f['id']}.json"
    if fp.exists():
        try:
            dets = lire(fp)
            if isinstance(dets, list):
                for x in dets:
                    im = x.get("image") or {}
                    if im.get("id"):
                        ids.add(im["id"])
        except Exception:  # noqa: BLE001
            pass
    out = []
    for i in ids:
        m = IMD.get(i)
        if m and m.get("captured_at"):
            out.append((ms_date(m["captured_at"]), i, m.get("sequence")))
    return sorted(out)


CODE_MLY = {"regulatory--keep-right--g1": "B21a1", "regulatory--yield--g1": "AB3a", "regulatory--stop--g1": "AB4",
            "regulatory--no-left-turn--g1": "B2a", "regulatory--no-right-turn--g1": "B2b", "regulatory--no-entry--g1": "B1",
            "warning--traffic-signals--g1": "A17", "warning--roadworks--g1": "AK5", "regulatory--no-parking--g1": "B6a1",
            "regulatory--no-stopping--g1": "B6d", "information--dead-end--g1": "C13a", "regulatory--bicycles-only--g1": "B22a",
            "warning--pedestrians-crossing--g1": "A13b", "warning--road-narrows--g1": "A3", "warning--other-danger--g1": "A14",
            "warning--children--g1": "A13a", "regulatory--maximum-speed-limit-30--g1": "B14(30)",
            "regulatory--maximum-speed-limit-50--g1": "B14(50)", "regulatory--weight-limit--g1": "B13",
            "regulatory--speed-limit-zone--g1": "B30", "information--parking--g1": "C1a",
            "information--general-directions--g1": "D21/D42", "complementary--chevron-left--g2": "J4/J6"}

mly_assoc, mly_new, mly_ignores = 0, 0, collections.Counter()
mly_recs = []
for f in MF:
    typ, st = type_mapillary(f["object_value"])
    if typ is None:
        mly_ignores[f["object_value"].split("--")[0] + "--" + f["object_value"].split("--")[1]] += 1
        continue
    x, y = wgs_l93(*f["geometry"]["coordinates"][:2])
    if not dans_emprise(x, y, 5.0):
        continue
    dl = mly_dates(f)
    if not dl:
        dl = [(f["first_seen_at"][:10], None, None), (f["last_seen_at"][:10], None, None)]
    code = CODE_MLY.get(f["object_value"]) if f["object_type"] == "trafficsign" else None
    az = f.get("aligned_direction")
    mly_recs.append({"f": f, "typ": typ, "st": st, "x": x, "y": y, "dates": dl, "code": code,
                     "az": None if az is None else round((az + GAMMA) % 360, 1)})

# priorité : panneaux codés, puis détections les plus nombreuses
mly_recs.sort(key=lambda r: (r["code"] is None, -len(r["dates"])))
for r in mly_recs:
    f, typ = r["f"], r["typ"]
    d_pre = [d for d, _, _ in r["dates"] if d < DEBUT_TRAVAUX]
    d_win = [d for d in d_pre if d >= FENETRE[0]]
    rad = TYPES[typ][0] * 1.6 + 1.0
    compat = SUPPORTS if typ in ("poteau",) else ({"poteau"} if typ in ("panneau", "feu", "lampadaire") else None)
    o, dd = plus_proche(r["x"], r["y"], typ, rad, compat=compat)
    seqs = sorted({s for _, _, s in r["dates"] if s})
    info = dict(valeur=f["object_value"], type_mly=f["object_type"], distance_m=None,
                premiere_vue=r["dates"][0][0], derniere_vue=r["dates"][-1][0], n_images=len(r["dates"]),
                n_images_2022_2025=len(d_win), n_sequences=len(seqs))
    if o is not None:
        info["distance_m"] = round(dd, 2)
        nat = "detection_auto" if d_win else "detection_ancienne"
        preuve(o, "mapillary_map_feature", f["id"], r["dates"][-1][0], nat, **info)
        o["mly_ids"].add(f["id"])
        o.setdefault("mly_dates", set()).update(d for d, _, _ in r["dates"])
        o.setdefault("mly_images_fenetre", set()).update(i for d, i, _ in r["dates"] if i and FENETRE_PHOTOS[0] <= d < DEBUT_TRAVAUX)
        if r["code"] and not o.get("code"):
            o["code_mapillary"] = r["code"]
        if r["az"] is not None and o["azimut_face_deg"] is None and typ == "panneau" and r["code"]:
            o["azimut_face_deg"] = r["az"]
            o["azimut_src"] = f"Mapillary aligned_direction ({f['id']}), converti en grille L93"
        mly_assoc += 1
        continue
    # pas d'objet connu : nouvel objet si au moins 2 images détectantes (ou panneau codé)
    if len(r["dates"]) < 2 and not r["code"]:
        mly_ignores["isolée (1 image)"] += 1
        continue
    o = nouvel(f"AT-MLY-{f['id']}", typ, r["st"], r["x"], r["y"], "mapillary", 3.0)
    o["code"] = r["code"]
    if r["az"] is not None and typ in ("panneau",):
        o["azimut_face_deg"] = r["az"]
        o["azimut_src"] = f"Mapillary aligned_direction ({f['id']}), converti en grille L93"
    nat = "detection_auto" if d_win else "detection_ancienne"
    preuve(o, "mapillary_map_feature", f["id"], r["dates"][-1][0], nat, **info)
    o["mly_ids"].add(f["id"])
    o["mly_dates"] = {d for d, _, _ in r["dates"]}
    o["mly_images_fenetre"] = {i for d, i, _ in r["dates"] if i and FENETRE_PHOTOS[0] <= d < DEBUT_TRAVAUX}
    o["notes"].append(f"détection Mapillary {f['object_value']} absente des autres sources (position Mapillary ±3 m)")
    mly_new += 1

# ---------------------------------------------------------------------------- 5. annotations Panoramax (panneaux codés)
POSES = {ph["id"]: ph for ph in lire(RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json")["photos"]}
ANN = lire(TELE / "panoramax_semantique/annotations.json")["photos"]
ann_assoc, ann_libres = 0, []
for pid, a in ANN.items():
    d = a["datetime"][:10]
    if d >= DEBUT_TRAVAUX:
        continue
    ph = POSES.get(pid)
    pose = (ph or {}).get("pose")
    if not pose:
        continue
    cx, cy = pose["x"] + O[0], pose["y"] + O[1]
    W, H = a.get("width") or 5760, a.get("height") or 2880
    for an in a.get("annotations") or []:
        code = None
        for s in an.get("semantics", []):
            if s.get("key") == "osm|traffic_sign":
                code = s.get("value")
        if not code:
            continue
        P = np.asarray(an["shape"]["coordinates"][0], float)
        u, v = P[:, 0].mean(), P[:, 1].mean()
        lon = (u / W - 0.5) * 360.0
        az = (pose["lacet"] + lon) % 360
        best, bda = None, 2.5
        for o in OBJ:
            if o["type"] != "panneau":
                continue
            dx, dy = o["x"] - cx, o["y"] - cy
            dist = math.hypot(dx, dy)
            if dist > 40 or dist < 1:
                continue
            azo = math.degrees(math.atan2(dx, dy)) % 360
            da = abs((azo - az + 180) % 360 - 180)
            c2 = (code.replace("FR:", "") == (o.get("code") or ""))
            if da - (1.0 if c2 else 0) < bda:
                best, bda = o, da - (1.0 if c2 else 0)
        if best is not None:
            preuve(best, "panoramax_annotation", pid[:8] + "/" + an["id"][:8], d, "detection_auto", code=code,
                   ecart_azimut_deg=round(bda + (1.0 if code.replace("FR:", "") == (best.get("code") or "") else 0), 2))
            if not best.get("code") and code.startswith("FR:"):
                best["code_panoramax"] = code[3:]
            ann_assoc += 1
        else:
            ann_libres.append({"photo": pid, "date": d, "code": code, "azimut_grille_deg": round(az, 1),
                               "camera_l93": [round(cx, 2), round(cy, 2)]})

# ---------------------------------------------------------------------------- 6. fusion des doublons (même type, < 1 m ; ou Mapillary/OSM proches)
def fusionner(a, b):
    a["preuves"] += [p for p in b["preuves"] if p not in a["preuves"]]
    a["absences"] += b["absences"]
    a["osm_ids"] |= b["osm_ids"]
    a["mly_ids"] |= b["mly_ids"]
    a.setdefault("mly_dates", set()).update(b.get("mly_dates", set()))
    a.setdefault("mly_images_fenetre", set()).update(b.get("mly_images_fenetre", set()))
    a["fusionnes"].append(b["id"])
    a["notes"] += b["notes"]
    for k in ("code", "azimut_face_deg", "hauteur_m"):
        if a.get(k) is None and b.get(k) is not None:
            a[k] = b[k]
            if k == "azimut_face_deg":
                a["azimut_src"] = b.get("azimut_src")


ordre = {"description_2026": 0, "observation_v2": 1, "osm_2025": 2, "mapillary": 3}
OBJ.sort(key=lambda o: (ordre[o["origine"]], -len(o["preuves"])))
garde = []
for o in OBJ:
    if o["origine"] == "description_2026":
        # doublons de la description (GEN-06 : même type à moins de 1,0 m ; pas les panneaux d'un même mât)
        dbl = None
        if o["geom"]["type"] == "Point" and o["type"] not in ("panneau", "arbre", "feu"):
            for g in garde:
                if g["type"] == o["type"] and g["geom"]["type"] == "Point" and math.hypot(g["x"] - o["x"], g["y"] - o["y"]) < 1.0:
                    dbl = g
                    break
        if dbl is not None:
            fusionner(dbl, o)
            dbl["notes"].append(f"doublon fusionné : {o['id']} (GEN-06)")
        else:
            garde.append(o)
        continue
    r = 1.0 if o["origine"] == "observation_v2" else TYPES[o["type"]][0] * (1.6 if o["origine"] == "mapillary" else 1.0)
    cand = None
    for g in garde:
        if g["type"] != o["type"] or g["geom"]["type"] != "Point":
            continue
        if math.hypot(g["x"] - o["x"], g["y"] - o["y"]) < r:
            cand = g
            break
    if cand is not None:
        fusionner(cand, o)
    else:
        garde.append(o)
OBJ[:] = garde
PAR_ID = {o["id"]: o for o in OBJ}

# ---------------------------------------------------------------------------- 6b. revue visuelle des vignettes (Claude)
REVUE = SORTIE / "revue_visuelle_objets.json"
n_revue = collections.Counter()
if REVUE.exists():
    for v in lire(REVUE)["verdicts"]:
        o = PAR_ID.get(v["objet"])
        if o is None:
            n_revue["objet introuvable"] += 1
            continue
        for k in ("type", "sous_type", "code"):
            if v.get(k):
                o[k] = v[k]
        o["revue_visuelle"] = {"verdict": v["verdict"], "note": v.get("note"), "images": v.get("images"),
                               "fichier": "revue_visuelle_objets.json"}
        vd = v["verdict"]
        for src, img, d in v.get("images", []):
            if vd == "confirme":
                nat = "photo" if d < DEBUT_TRAVAUX else "post_travaux"
                preuve(o, f"revue visuelle ({src})", img, d, nat, detail=v.get("note", "")[:160])
            elif vd == "absent":
                o["absences"].append({"source": f"revue visuelle ({src})", "id": img, "date": d, "detail": v.get("note", "")[:160]})
        if vd == "doublon" and v.get("cible") in PAR_ID:
            fusionner(PAR_ID[v["cible"]], o)
            o["force_etat"] = ("doublon", f"fusionné dans {v['cible']} : {v.get('note', '')}")
        elif vd == "doublon":
            o["force_etat"] = ("doublon", v.get("note", ""))
        elif vd == "temporaire":
            o["force_etat"] = ("temporaire_chantier", v.get("note", ""))
        elif vd == "faux_positif":
            o["force_etat"] = ("faux_positif", v.get("note", ""))
        elif vd == "incertain":
            o["force_etat"] = ("incertain", v.get("note", ""))
        n_revue[vd] += 1
    # totems P+R retypés : rapprochement avec le totem de la description
    for o in OBJ:
        if o["origine"] == "mapillary" and o.get("sous_type") == "totem_PR" and "force_etat" not in o:
            t = PAR_ID.get("totem_PR")
            if t is not None and math.hypot(t["x"] - o["x"], t["y"] - o["y"]) < 8.0:
                fusionner(t, o)
                o["force_etat"] = ("doublon", "fusionné dans totem_PR (même totem P+R)")
print("revue visuelle :", dict(n_revue))
for o in OBJ:
    if "force_etat" not in o and (o.get("code") == "AK5" or o.get("sous_type") == "temporaire"):
        o["force_etat"] = ("temporaire_chantier", "signalisation ou barrière de chantier temporaire")

# ---------------------------------------------------------------------------- 7. état avant travaux
FORT = {"photo", "ortho"}
MOYEN = {"detection_auto", "constat"}


def evaluer(o):
    pv = o["preuves"]

    def dwin(p):
        d = p.get("date")
        return bool(d) and (d == "2025" or dans_fenetre(d if len(d) >= 10 else d + "-15"))

    fort = [p for p in pv if p["nature"] in FORT and dwin(p)]
    moyen = [p for p in pv if p["nature"] in MOYEN and dwin(p)]
    indice = [p for p in pv if p["nature"] == "indice" and dwin(p)]
    lidar = [p for p in pv if p["nature"] == "lidar"]
    osm_pre = [p for p in pv if p["nature"] == "osm" and p["source"] == "osm_historique"
               and any(n >= "2022" for n in p.get("instantanes", []))]
    old = [p for p in pv if p["nature"] == "detection_ancienne" or
           (p["nature"] in FORT | MOYEN | {"indice"} and p.get("date") and len(p["date"]) >= 7 and p["date"][:10] < FENETRE[0])]
    gam = [p for p in pv if p["nature"] == "leve_gam"]
    plan = [p for p in pv if p["nature"] == "plan_projet"]
    post = [p for p in pv if p["nature"] in ("post_travaux", "pendant_travaux")]
    d_trav = Z.d_travaux((o["x"], o["y"]))
    d_c23 = Z.d_c23((o["x"], o["y"]))
    o["d_zone_travaux_m"] = round(d_trav, 2) if math.isfinite(d_trav) else None
    o["d_constructions_2023_2024_m"] = round(d_c23, 2) if math.isfinite(d_c23) else None
    direct = fort + moyen + indice
    sources = {p["source"].split(" (")[0] for p in fort + moyen}
    dates_dir = sorted({p["date"][:10] for p in direct if p.get("date") and len(p["date"]) >= 7})
    o["vu_de"] = dates_dir[0] if dates_dir else None
    o["vu_a"] = dates_dir[-1] if dates_dir else None
    positif_pre = bool(direct or lidar or osm_pre or old)
    # absences constatées avant les travaux (hors LiDAR 2021 : un jeune sujet peut y manquer)
    abs_pre = [a for a in o["absences"] if a.get("date") and a["date"] < DEBUT_TRAVAUX and a["source"] != "lidar2021"]
    dern_pos = max([p["date"][:10] for p in direct + osm_pre if p.get("date") and len(p["date"]) >= 7] +
                   [p["date"] for p in lidar], default="")
    abs_apres = [a for a in abs_pre if a["date"] > dern_pos]
    raison = []
    if o.get("force_etat"):
        statut, txt = o["force_etat"]
        o["etat_avant_travaux"] = statut
        o["confiance"] = "faible" if statut == "incertain" else None
        o["raison"] = "revue visuelle : " + txt if o.get("revue_visuelle") else txt
        return o
    if o["type"] == "arbre" and "planté 2025" in (o.get("statut_2026") or "") and not direct and not lidar:
        statut, conf, raison = "absent_avant_travaux", None, ["planté 2025 (plan projet)"]
    elif abs_apres and positif_pre:
        statut, conf = "disparu_avant_travaux", None
        raison = [f"vu jusqu'au {dern_pos}, absent ({a['source']}) le {a['date']}" for a in abs_apres]
    elif abs_apres and gam and d_trav > 3 and max(a["date"] for a in abs_apres) <= D_ORTHO22:
        statut, conf = "incertain", "faible"
        raison = [f"absent sur l'ortho du {D_ORTHO22}, levé GAM (non daté) hors emprise des travaux : planté ou posé entre 05/2022 et le levé"
                  + (" (secteur construit 2023-2024)" if d_c23 == 0 else "")]
    elif abs_apres:
        statut, conf = "absent_avant_travaux", None
        raison = [f"absent ({a['source']}) le {a['date']}, aucune preuve positive avant travaux" for a in abs_apres]
    elif fort or len(sources) >= 2 or (moyen and (lidar or osm_pre or gam)):
        statut = "present"
        n_src = len(sources) + (1 if lidar else 0) + (1 if osm_pre else 0)
        conf = "haute" if (n_src >= 2 and fort and o["sigma_m"] <= 0.6) else "moyenne"
        raison.append(f"{len(fort + moyen)} preuve(s) directe(s) 2022-2025 ({', '.join(sorted(sources))})"
                      + (" + LiDAR 2021" if lidar else "") + (" + OSM avant travaux" if osm_pre else ""))
    elif moyen or indice or lidar or osm_pre:
        statut = "present_presume"
        n_sig = sum(bool(x) for x in (moyen, indice, lidar, osm_pre, gam and d_trav > 3, post and d_trav > 3))
        conf = "moyenne" if n_sig >= 2 else "faible"
        raison.append(" + ".join(x for x, c in (("détection automatique 2022-2025", moyen), ("indice photo 2022-2025", indice),
                                               ("LiDAR 2021", lidar), ("OSM avant travaux", osm_pre)) if c)
                      + " (aucune observation confirmée 2022-2025)")
    elif old and (gam or post) and d_trav > 3:
        statut, conf = "present_presume", "faible"
        raison.append("vu avant 2022 et attesté après travaux, hors emprise des travaux")
    elif old:
        statut, conf = "non_revu_2022_2025", None
        raison.append("vu seulement avant 2022 (" + ", ".join(sorted({p['date'][:4] for p in old if p.get('date')})) + "), non revu sur les images 2022-2025")
    elif gam and d_trav > 3:
        statut, conf = "present_presume", "faible"
        raison.append("levé GAM (non daté, identique à etat_2026) hors emprise des travaux, sans preuve datée")
    elif gam:
        statut, conf = "incertain", "faible"
        raison.append("levé GAM (non daté, identique à etat_2026) dans l'emprise des travaux (±3 m) : présence avant travaux non démontrée")
    elif plan:
        statut, conf = "absent_avant_travaux", None
        raison.append("seulement plan projet 2025" + (" et sources postérieures" if post else ""))
    elif post and d_trav > 3:
        statut, conf = "incertain", "faible"
        raison.append("attesté seulement après travaux (OSM/photo 2026), hors emprise : présence avant non démontrée")
    else:
        statut, conf = "absent_avant_travaux", None
        raison.append("aucune preuve antérieure aux travaux" + (" ; dans l'emprise des travaux" if d_trav <= 3 else ""))
    o["etat_avant_travaux"] = statut
    o["confiance"] = conf
    o["raison"] = " ; ".join(raison)
    return o


for o in OBJ:
    evaluer(o)

# ---------------------------------------------------------------------------- 8. couverture photo (poses calées, 2023 -> 22/06/2025)
CAMS = []
for pid, ph in POSES.items():
    if not ph.get("pose") or not (FENETRE_PHOTOS[0] <= ph["date"] < DEBUT_TRAVAUX):
        continue
    p = ph["pose"]
    CAMS.append({"src": "panoramax", "id": pid, "date": ph["date"], "xy": (p["x"] + O[0], p["y"] + O[1]),
                 "lacet": p["lacet"], "hfov": 360.0 if ph["modele"] == "equirect" else 70.0,
                 "calee": True, "acceptee": bool(ph.get("accepte"))})
MP = lire(REC / "mapillary/poses/poses_mapillary.json")["images"]
for im in MP:
    if not (FENETRE_PHOTOS[0] <= im["date"] < DEBUT_TRAVAUX):
        continue
    p = im["pose"]
    if im["camera_type"] in ("spherical", "equirectangular"):
        hf = 360.0
    else:
        fpar = (im.get("camera_parameters") or [0.8])[0] or 0.8
        hf = math.degrees(2 * math.atan(im["W"] / (2 * fpar * max(im["W"], im["H"]))))
    CAMS.append({"src": "mapillary", "id": im["id"], "date": im["date"], "xy": (p["x"] + O[0], p["y"] + O[1]),
                 "lacet": p["lacet"], "hfov": hf, "calee": im["statut"] != "a_priori", "acceptee": im["statut"] != "a_priori"})
# Panoramax sans pose (GNSS) dans la fenêtre : a priori
for f in PNX_INDEX["features"]:
    p = f["properties"]
    if p["id"] in POSES and POSES[p["id"]].get("pose"):
        continue
    d = p["datetime"][:10]
    if not (FENETRE_PHOTOS[0] <= d < DEBUT_TRAVAUX):
        continue
    x, y = wgs_l93(p["lon"], p["lat"])
    CAMS.append({"src": "panoramax", "id": p["id"], "date": d, "xy": (x, y), "lacet": (p.get("azimuth") or 0) + GAMMA,
                 "hfov": 360.0 if p.get("is_360") else float(p.get("field_of_view") or 70), "calee": False, "acceptee": False})
print("caméras 2023-2025 :", collections.Counter((c["src"], c["calee"]) for c in CAMS))

# distance maximale de visibilité utile (objet sur ≥ ~40 px d'une 360° GoPro 5760 px ou d'une image 2048 px)
DMAX = {"arbre": 40, "lampadaire": 45, "feu": 35, "panneau": 30, "potelet": 15, "barriere": 20, "banc": 25, "abri_bus": 50,
        "poteau_arret": 30, "borne": 20, "armoire": 30, "poteau": 40, "corbeille": 20, "arceaux_velos": 25, "autre_mobilier": 25}


def visibles(o):
    pts = np.asarray(o["geom"]["coordinates"], float) if o["geom"]["type"] == "LineString" else np.array([[o["x"], o["y"]]])
    res = []
    for c in CAMS:
        C = np.asarray(c["xy"])
        dd = np.hypot(*(pts - C).T)
        i = int(dd.argmin())
        dist = float(dd[i])
        if dist > DMAX[o["type"]] or dist < 0.8:
            continue
        P = pts[i]
        az = math.degrees(math.atan2(P[0] - C[0], P[1] - C[1])) % 360
        if c["hfov"] < 359:
            if abs((az - c["lacet"] + 180) % 360 - 180) > c["hfov"] / 2 - 2:
                continue
        if BAT.occulte(C, P):
            continue
        res.append(c)
    return res


for o in OBJ:
    v = visibles(o)
    cal = [c for c in v if c["calee"]]
    o["photos_visibles"] = sorted(f"{c['src'][:3]}:{c['id'][:16]}@{c['date']}" for c in cal)
    o["nb_photos_visibles"] = len(cal)
    o["nb_photos_visibles_acceptees"] = sum(1 for c in cal if c["acceptee"])
    o["nb_photos_visibles_a_priori"] = len(v) - len(cal)
    # détections réelles 2023-2025 (Mapillary, annotations et observations V2 datées)
    det = set(o.get("mly_images_fenetre", set()))
    for p in o["preuves"]:
        if p["nature"] in ("photo", "detection_auto") and p.get("date") and FENETRE_PHOTOS[0] <= p["date"][:10] < DEBUT_TRAVAUX \
                and p["source"] != "mapillary_map_feature":
            det.add(p["source"].split(" (")[0] + ":" + str(p["id"]).split("/")[0])
    o["nb_photos_detecte"] = len(det)

# ---------------------------------------------------------------------------- 9. sorties
GARDER = ("present", "present_presume", "incertain")
# exclus : absent_avant_travaux, disparu_avant_travaux, non_revu_2022_2025, doublon, temporaire_chantier, faux_positif


def r2(v):
    return None if v is None else round(float(v), 2)


def feature(o):
    pv = sorted(o["preuves"], key=lambda p: (p.get("date") or "0000", p["source"]))
    hauteur = o.get("hauteur_m")
    if hauteur is None:
        hauteur, hsrc = TYPES[o["type"]][1], "défaut par type"
    else:
        hsrc = o.get("hauteur_src")
    props = {
        "id": o["id"], "type": o["type"], "sous_type": o["sous_type"], "code": o.get("code") or o.get("code_panoramax") or o.get("code_mapillary"),
        "code_source": "description 2026" if o.get("code") else ("annotation Panoramax" if o.get("code_panoramax") else ("Mapillary" if o.get("code_mapillary") else None)),
        "hauteur_m": r2(hauteur), "hauteur_source": hsrc, "hauteur_lidar_2021_m": o.get("hauteur_lidar_2021_m"),
        "azimut_face_deg": r2(o.get("azimut_face_deg")), "azimut_source": o.get("azimut_src"),
        "etat_avant_travaux": o["etat_avant_travaux"], "confiance": o["confiance"], "raison": o["raison"],
        "sigma_position_m": r2(o["sigma_m"]), "origine_position": o["origine"], "position_source": o.get("position_source"),
        "position_2026_l93": o.get("position_2026_l93"), "ecart_position_2026_m": o.get("ecart_position_2026_m"),
        "vu_de": o.get("vu_de"), "vu_a": o.get("vu_a"),
        "nb_photos_visibles": o["nb_photos_visibles"], "nb_photos_visibles_acceptees": o["nb_photos_visibles_acceptees"],
        "nb_photos_visibles_a_priori": o["nb_photos_visibles_a_priori"], "nb_photos_detecte": o["nb_photos_detecte"],
        "photos_visibles": o["photos_visibles"][:40],
        "preuves": [{k: v for k, v in p.items()} for p in pv],
        "absences": o["absences"],
        "osm_ids": sorted(o["osm_ids"]), "osm_instantanes": o.get("osm_instantanes"),
        "mapillary_ids": sorted(o["mly_ids"]),
        "mapillary_dates": sorted(o.get("mly_dates", set()))[:1] + sorted(o.get("mly_dates", set()))[-1:] if o.get("mly_dates") else None,
        "lien_2026": o["lien_2026"], "statut_2026": o["statut_2026"],
        "d_zone_travaux_m": o.get("d_zone_travaux_m"), "d_constructions_2023_2024_m": o.get("d_constructions_2023_2024_m"),
        "triangulation_v2": o.get("triangulation_v2"), "positions_observees": o.get("positions_observees"),
        "deplacement_osm_apres_travaux": o.get("deplacement_osm_apres_travaux"), "emprise_osm_avant_l93": o.get("emprise_osm_avant_l93"),
        "essence": o.get("essence"), "diametre_couronne_m": o.get("diametre_couronne_m"),
        "fusionnes": o["fusionnes"] or None, "notes": o["notes"] or None, "revue_visuelle": o.get("revue_visuelle"),
        "x_local": round(o["x"] - O[0], 3), "y_local": round(o["y"] - O[1], 3),
    }
    props = {k: v for k, v in props.items() if v is not None}
    return {"type": "Feature", "properties": props, "geometry": o["geom"]}


entete = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2154"}}}
garde = [o for o in OBJ if o["etat_avant_travaux"] in GARDER]
exclus = [o for o in OBJ if o["etat_avant_travaux"] not in GARDER]
garde.sort(key=lambda o: (o["type"], o["id"]))
exclus.sort(key=lambda o: (o["type"], o["id"]))
meta = {"schema": "pj_objets_avant_travaux/0.1", "etat_cible": f"état avant travaux : printemps 2025 (avant le {DEBUT_TRAVAUX}), preuves 2022-2025",
        "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98) ; z = NGF - 216,30 ; UE : X = x*100, Y = -y*100, Z = z*100",
        "azimut": "azimut_face_deg : azimut grille L93 (0 = nord du quadrillage, sens horaire) de la face ; azimut_L93 = azimut_vrai - 2,0086°",
        "generateur": "recon/out/paquet_jardin/v2_avant_travaux/inventaire/objets/scripts/inventaire.py",
        "photos": "nb_photos_visibles = photos datées du 01/01/2023 au 22/06/2025 à pose calée (Panoramax poses.json, Mapillary calee_*) "
                  "qui voient géométriquement l'objet (distance max par type, champ, occultation par le bâti) ; "
                  "nb_photos_visibles_a_priori = idem avec pose a priori (SfM Mapillary, GNSS Panoramax) ; "
                  "nb_photos_detecte = images où l'objet est effectivement détecté ou observé (Mapillary, annotations Panoramax, observations V2)"}
ecrire(SORTIE / "objets_avant_travaux.geojson", {**entete, "name": "objets_avant_travaux", "meta": meta,
                                                  "features": [feature(o) for o in garde]}, indent=None)
ecrire(SORTIE / "objets_exclus.geojson", {**entete, "name": "objets_exclus_avant_travaux", "meta": meta,
                                          "features": [feature(o) for o in exclus]}, indent=None)

# statistiques
st = {"n_objets_total": len(OBJ), "n_avant_travaux": len(garde), "n_exclus": len(exclus),
      "par_type_etat": collections.Counter(f"{o['type']}|{o['etat_avant_travaux']}" for o in OBJ),
      "par_type_confiance": collections.Counter(f"{o['type']}|{o['confiance']}" for o in garde),
      "par_origine": collections.Counter(f"{o['origine']}|{o['etat_avant_travaux']}" for o in OBJ),
      "observations_liees": n_obs_lien, "observations_nouvelles": n_obs_new,
      "mapillary": {"features": len(MF), "associees": mly_assoc, "nouvelles": mly_new, "ignorees": mly_ignores},
      "panoramax_annotations": {"associees": ann_assoc, "libres": ann_libres},
      "positions_ramenees_avant_travaux": n_pos_rev, "deplacements_osm": DEPLACEMENTS_OSM,
      "osm": {"instantanes": sorted(SNAP), "reference": REF_OSM, "disparus_avant_reference": osm_disparus_avant,
              "crees_apres": osm_crees, "supprimes_apres_reference": sorted(set(osm_supprimes_travaux))},
      "cameras_fenetre": collections.Counter(f"{c['src']}|{'calee' if c['calee'] else 'a_priori'}" for c in CAMS),
      }
ecrire(SORTIE / "inventaire_stats.json", st)
print("objets :", len(OBJ), "avant travaux :", len(garde), "exclus :", len(exclus))
for k, v in sorted(collections.Counter(f"{o['type']}|{o['etat_avant_travaux']}" for o in OBJ).items()):
    print(" ", k, v)
print("mapillary associées", mly_assoc, "nouvelles", mly_new, "ignorées", dict(mly_ignores))
print("annotations Panoramax associées", ann_assoc, "libres", len(ann_libres))
