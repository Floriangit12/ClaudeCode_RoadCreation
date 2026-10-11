"""Recontrôle chiffré des critiques de la relecture adverse de PLAN_AVANT_TRAVAUX.md (11/10/2026).

Lecture seule. Lancer depuis n'importe où avec :
    python -I recon/out/paquet_jardin/v2_avant_travaux/inventaire/revision/outils/verifier_critiques.py
(-I : le script lit des fichiers téléchargés, notamment la réponse STAC Panoramax.)

Écrit uniquement :
    inventaire/revision/verifications_revision.json
    inventaire/revision/chg019_coeur_poses.jpg   (fond : ortho PCRS 5 cm 2022, Licence Ouverte ; aucune photo de tiers)
"""
import collections
import datetime as dt
import glob
import json
import math
import os
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
REV = ICI.parent
INV = REV.parent
DEPOT = INV.parents[4]
O = (917279.43, 6460289.98)
CENTRE = (-1.57, -5.09)            # centre des couronnes de changements/donnees/statistiques.json
ENR = DEPOT / "recon/out/paquet_jardin/v2/enrichi"


def lire(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------ rastérisation des emprises
RES, X0, Y0, N = 0.25, -150.0, -150.0, 1200
xs = X0 + (np.arange(N) + 0.5) * RES
ys = Y0 + N * RES - (np.arange(N) + 0.5) * RES
XX, YY = np.meshgrid(xs, ys)
COEUR = np.hypot(XX - CENTRE[0], YY - CENTRE[1]) <= 40.0


def polygones(g):
    if g["type"] == "Polygon":
        return [g["coordinates"]]
    if g["type"] == "MultiPolygon":
        return g["coordinates"]
    return []


def masque(g):
    im = Image.new("L", (N, N), 0)
    dr = ImageDraw.Draw(im)
    for P in polygones(g):
        for k, anneau in enumerate(P):
            dr.polygon([((x - O[0] - X0) / RES, (Y0 + N * RES - (y - O[1])) / RES) for x, y, *_ in anneau],
                       fill=0 if k else 1)
    return np.array(im, bool)


def dans(m, x, y):
    i, j = int((Y0 + N * RES - y) / RES), int((x - X0) / RES)
    return 0 <= i < N and 0 <= j < N and bool(m[i, j])


CHG = {f["properties"]["id"]: f for f in lire(INV / "changements/changements_2022_2025.geojson")["features"]}
M = {k: masque(f["geometry"]) for k, f in CHG.items()}
A = COEUR.sum()
res = {"genere": "revision/outils/verifier_critiques.py", "date": "2026-10-11", "raster_m": RES,
       "centre_coeur_local": CENTRE}

# ------------------------------------------------------------------ CHG-019 (F3, F4)
m19 = M["CHG-019"]
geo = np.zeros_like(m19)
for k in ("CHG-001", "CHG-002", "CHG-003", "CHG-004", "CHG-005", "CHG-006"):
    geo |= M[k]
d19 = np.hypot(XX[m19] - CENTRE[0], YY[m19] - CENTRE[1])
res["chg019"] = {
    "aire_m2": round(float(m19.sum() * RES * RES)),
    "x": [round(float(XX[m19].min()), 1), round(float(XX[m19].max()), 1)],
    "y": [round(float(YY[m19].min()), 1), round(float(YY[m19].max()), 1)],
    "distance_min_au_centre_m": round(float(d19.min()), 1),
    "part_coeur_r40": round(float((m19 & COEUR).sum() / A), 4),
    "statistiques_json_risque_non_observe_r40_m2": lire(INV / "changements/donnees/statistiques.json")
    ["surfaces_m2"]["risque_non_observe"]["r<=40"],
}
res["coeur_r40_geometrie_2022"] = {
    "invalide_CHG001_006": round(float((geo & COEUR).sum() / A), 4),
    "invalide_ou_incertaine_avec_CHG019": round(float(((geo | m19) & COEUR).sum() / A), 4),
    "valable_et_certaine_T_2025_05_18": round(1 - float(((geo | m19) & COEUR).sum() / A), 4),
    "valable_et_certaine_T_2024_08_24": round(1 - float((geo & COEUR).sum() / A), 4),
}

# ------------------------------------------------------------------ poses (F1, F4, F7, F8)
pp = lire(ENR / "poses/poses.json")
pm = lire(ENR / "recensement/mapillary/poses/poses_mapillary.json")["images"]
res["poses_criteres_panoramax"] = pp["criteres"]
res["px_par_degre_960_90"] = round(960 / 90, 3)
res["seuil_360_en_px_960_90"] = round(pp["criteres"]["seuil_360_deg"] * 960 / 90, 2)
res["panoramax_par_date_accepte_pose"] = collections.Counter(
    f"{p['date']}|{p['accepte']}|{p['pose'] is not None}" for p in pp["photos"])
vues = []
for p in pp["photos"]:
    if p["accepte"]:
        vues.append(dict(date=p["date"], statut="panoramax", id=p["id8"], x=p["pose"]["x"], y=p["pose"]["y"]))
for m in pm:
    if m["statut"] in ("calee_bordures", "calee_gcp"):
        vues.append(dict(date=m["date"], statut=m["statut"], id=m["id"], x=m["pose"]["x"], y=m["pose"]["y"]))
for v in vues:
    v["r"] = math.hypot(v["x"], v["y"])
    v["dans_chg019"] = dans(m19, v["x"], v["y"])
res["vues_distinctes"] = {
    "total": len(vues),
    "par_date": collections.Counter(v["date"] for v in vues),
    "r_le_35": collections.Counter(v["date"] for v in vues if v["r"] <= 35),
    "r_le_80": collections.Counter(v["date"] for v in vues if v["r"] <= 80),
    "calee_bordures_40_80m": sum(1 for v in vues if v["statut"] == "calee_bordures" and 40 < v["r"] <= 80),
    "dans_chg019": [f"{v['date']} {v['statut']} ({v['x']:.1f} ; {v['y']:.1f})" for v in vues if v["dans_chg019"]],
}

inv = lire(INV / "sources/photos_inventaire.json")["photos"]
uniq = [p for p in inv if p.get("doublon_de") is None]
res["photos_uniques_r_le_80"] = {
    "fenetre_2024_08_24_2025_06_22": collections.Counter(
        p["date"] for p in uniq if "2024-08-24" <= p["date"] <= "2025-06-22" and math.hypot(p["x"], p["y"]) <= 80),
    "avant_2024_08_24": collections.Counter(
        p["date"] for p in uniq if "2022" <= p["date"] < "2024-08-24" and math.hypot(p["x"], p["y"]) <= 80),
}
res["photos_uniques_par_secteur"] = {
    d: collections.Counter(p["secteur"] for p in uniq if p["date"] == d)
    for d in ("2024-08-24", "2025-01-12", "2025-05-18")}

# horodatage Panoramax (fichier téléchargé : données, lues seulement)
stac = DEPOT / "data/sites/paquet_jardin/avant_travaux/panoramax/search_site_tout.json"
ts = collections.defaultdict(list)
for f in lire(stac).get("features", []):
    t = (f.get("properties") or {}).get("datetime") or ""
    if t[:10] in ("2024-08-24", "2025-01-12", "2025-05-18"):
        ts[t[:10]].append(t)
res["seances_panoramax_utc"] = {d: [len(v), min(v), max(v)] for d, v in ts.items()}


# ------------------------------------------------------------------ soleil (F5)
def soleil(t, lat=45.2073, lon=5.7677):
    jd = (t - dt.datetime(2000, 1, 1, 12)).total_seconds() / 86400.0
    g = math.radians((357.529 + 0.98560028 * jd) % 360)
    q = (280.459 + 0.98564736 * jd) % 360
    L = math.radians((q + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)) % 360)
    e = math.radians(23.439 - 0.00000036 * jd)
    ra = math.atan2(math.cos(e) * math.sin(L), math.cos(L))
    dec = math.asin(math.sin(e) * math.sin(L))
    ha = math.radians(((18.697374558 + 24.06570982441908 * jd) % 24) * 15 + lon) - ra
    la = math.radians(lat)
    el = math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = math.atan2(-math.sin(ha), math.tan(dec) * math.cos(la) - math.sin(la) * math.cos(ha))
    return round(math.degrees(az) % 360, 1), round(math.degrees(el), 1)


res["soleil_az_haut_deg"] = {s: soleil(dt.datetime.fromisoformat(s)) for s in (
    "2024-08-09T10:30", "2025-04-25T10:30", "2025-05-03T10:30", "2025-05-18T10:30", "2025-06-21T10:30",
    "2025-07-15T10:30", "2025-08-08T10:30", "2025-05-18T13:37:08", "2025-05-18T13:38:10",
    "2024-08-24T15:05:21", "2024-08-24T15:11:01")}

# ------------------------------------------------------------------ marques v1 et objets (F16, F17)
v1 = lire(DEPOT / "recon/out/paquet_jardin/package/donnees/marquages/marquages_2026.geojson")["features"]
c = collections.Counter()
for f in v1:
    p = f["properties"]
    if p["etat"] not in ("conserve", "fantome", "refait_2025_identique"):
        continue
    g = f["geometry"]
    cs = g["coordinates"][0] if g["type"] == "Polygon" else (
        g["coordinates"] if g["type"] == "LineString" else g["coordinates"][0][0])
    x, y = sum(q[0] for q in cs) / len(cs) - O[0], sum(q[1] for q in cs) / len(cs) - O[1]
    if not (-150 <= x <= 150 and -150 <= y <= 150):
        continue
    c["reference_v1_690"] += 1
    for k in ("CHG-002", "CHG-003", "CHG-008", "CHG-009", "CHG-019"):
        if dans(M[k], x, y):
            c[k] += 1
res["marques_v1_reference_dans_changements"] = c

ob = [f["properties"] for f in lire(INV / "objets/objets_avant_travaux.geojson")["features"]]
res["objets"] = {
    "origine_position": collections.Counter(p["origine_position"] for p in ob),
    "description_2026_dans_emprise_travaux_d_le_0": sum(
        1 for p in ob if p["origine_position"] == "description_2026" and p.get("d_zone_travaux_m") is not None
        and p["d_zone_travaux_m"] <= 0),
    "feux_statut_2026": collections.Counter(p.get("statut_2026") for p in ob if p["type"] == "feu"),
}

# ------------------------------------------------------------------ datation GAM (F2)
dr = lire(INV / "sol/datation/datation_resume.json")["longueurs_m_par_source_secteur_classe"]["gam"]
tot = collections.Counter()
for sect in dr.values():
    tot.update(sect)
L = sum(tot.values())
res["gam_bordures_classes"] = {"longueur_m": round(L, 1), **{k: round(v / L, 4) for k, v in tot.items()}}
res["gam_bordures_indetermine_part"] = round((tot["relief_seul"] + tot["terrain_remanie_2021"] + tot["masquee"]) / L, 4)

# ------------------------------------------------------------------ recalage IGN 2024 (F19)
rc = lire(ENR / "recensement/ortho_recentes/recalage.json")["couches"]["ign_bdortho_2024_rvb_20cm"]
fen = [f for f in rc["fenetres_[x,y,dx,dy,rapport_pic,retenue]"] if f[5]]
res["recalage_ign2024"] = {"translation_m": [rc["dx_m"], rc["dy_m"]], "mad_m": rc["mad_m"],
                           "fenetres_retenues": len(fen),
                           "max_norme_fenetre_m": round(max(math.hypot(f[2], f[3]) for f in fen), 3)}

# ------------------------------------------------------------------ BD TOPO et levé GAM, secteur est (F12)
try:
    from pyproj import Transformer
    T = Transformer.from_crs(4326, 2154, always_xy=True)
    V = DEPOT / "data/sites/paquet_jardin/vector"

    def ctr(g):
        t, cc = g["type"], g["coordinates"]
        pts = {"Point": lambda: [cc], "LineString": lambda: cc, "MultiPoint": lambda: cc,
               "Polygon": lambda: [p for r in cc for p in r], "MultiLineString": lambda: [p for r in cc for p in r],
               "MultiPolygon": lambda: [p for P in cc for r in P for p in r]}[t]()
        x, y = T.transform(sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        return x - O[0], y - O[1]

    def est(x, y):
        return 37 <= x <= 156 and -67 <= y <= 92

    bd = lire(V / "bdtopo_batiment.geojson")["features"]
    cr = [f for f in bd if str(f["properties"].get("date_creation", ""))[:10] == "2025-07-04"]
    res["bdtopo_batiments"] = {
        "total": len(bd), "date_creation_2025_07_04": len(cr),
        "dont_secteur_est": sum(1 for f in cr if est(*ctr(f["geometry"]))),
        "dont_hauteur_nulle_secteur_est": sum(1 for f in cr if est(*ctr(f["geometry"]))
                                              and f["properties"].get("hauteur") is None)}
    res["gam_secteur_est_boite_x37_156_y-67_92"] = {
        n: sum(1 for f in lire(V / f"gam_topo_sol_{n}.geojson")["features"] if est(*ctr(f["geometry"])))
        for n in ("batiment_lin", "escalier_rampe_lin", "talus_bas_lin", "talus_haut_lin")}
except ImportError:
    res["bdtopo_batiments"] = "pyproj absent"

(REV / "verifications_revision.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------------------------------------------ planche : CHG-019 au cœur et poses
DEMI, PAS = 70.0, 0.10          # ±70 m autour de l'origine, 10 cm / px
W = int(2 * DEMI / PAS)
fond = Image.new("RGB", (W, W), (40, 40, 40))
for jpg in glob.glob(str(DEPOT / "data/sites/paquet_jardin/ortho5cm_2022/*.jpg")):
    jgw = [float(v) for v in open(jpg[:-4] + ".jgw").read().split()]
    x0, y0 = jgw[4] - jgw[0] / 2 - O[0], jgw[5] - jgw[3] / 2 - O[1]
    im = Image.open(jpg)
    tw = im.width * jgw[0]
    if x0 > DEMI or x0 + tw < -DEMI or y0 < -DEMI or y0 - tw > DEMI:
        continue
    k = int(round(tw / PAS))
    fond.paste(im.resize((k, k), Image.BILINEAR), (int(round((x0 + DEMI) / PAS)), int(round((DEMI - y0) / PAS))))
fond = Image.blend(fond, Image.new("RGB", fond.size, (0, 0, 0)), 0.25)
dr = ImageDraw.Draw(fond, "RGBA")


def px(x, y):
    return ((x + DEMI) / PAS, (DEMI - y) / PAS)


for k, coul in (("CHG-001", (255, 0, 255)), ("CHG-002", (255, 0, 255)), ("CHG-003", (255, 0, 255)),
                ("CHG-004", (255, 0, 255)), ("CHG-005", (255, 0, 255)), ("CHG-006", (255, 0, 255)),
                ("CHG-008", (255, 160, 0)), ("CHG-019", (255, 255, 255))):
    for P in polygones(CHG[k]["geometry"]):
        pts = [px(x - O[0], y - O[1]) for x, y, *_ in P[0]]
        if k == "CHG-019":
            dr.polygon(pts, fill=(255, 255, 255, 60), outline=(255, 255, 255, 255))
        else:
            dr.line(pts + [pts[0]], fill=coul + (255,), width=3)
cx, cy = px(*CENTRE)
r40 = 40 / PAS
dr.ellipse([cx - r40, cy - r40, cx + r40, cy + r40], outline=(0, 255, 120, 255), width=4)
for v in vues:
    if abs(v["x"]) > DEMI or abs(v["y"]) > DEMI:
        continue
    u, w = px(v["x"], v["y"])
    coul = (0, 220, 255) if v["date"] == "2024-08-24" else (255, 230, 0)
    if v["statut"] == "calee_bordures":
        dr.line([u - 12, w - 12, u + 12, w + 12], fill=coul, width=4)
        dr.line([u - 12, w + 12, u + 12, w - 12], fill=coul, width=4)
    else:
        dr.ellipse([u - 10, w - 10, u + 10, w + 10], outline=coul, width=4)
try:
    fnt = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 30)
except OSError:
    fnt = ImageFont.load_default()
leg = ["Fond : ortho PCRS 5 cm du 10/05/2022 (assombrie). Repère local, ±70 m.",
       f"Blanc : CHG-019 (travaux Vercors annoncés, non observés) : {res['chg019']['part_coeur_r40'] * 100:.1f} % du cœur r ≤ 40 m (vert)",
       "Magenta : CHG-001 à 006 (géométrie 2022 non valable) ; orange : CHG-008 (marquages)",
       "Poses acceptées : rond = Panoramax / GCP ; croix = Mapillary calée sur bordures GAM 2026",
       "Cyan : 24/08/2024 ; jaune : 18/05/2025"]
dr.rectangle([0, 0, W, 40 * len(leg) + 10], fill=(0, 0, 0, 190))
for i, t in enumerate(leg):
    dr.text((12, 8 + 40 * i), t, fill=(255, 255, 255), font=fnt)
fond.save(REV / "chg019_coeur_poses.jpg", quality=85)
print(json.dumps({k: res[k] for k in ("chg019", "coeur_r40_geometrie_2022", "vues_distinctes")}, ensure_ascii=False,
                 indent=1, default=str))
