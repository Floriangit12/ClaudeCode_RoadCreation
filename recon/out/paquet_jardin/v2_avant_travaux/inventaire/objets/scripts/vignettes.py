"""Vignettes photo (Mapillary : boîtes de détection ; Panoramax : découpe à l'azimut de l'objet) pour contrôle visuel.

Usage : python -I vignettes.py [id_objet ...]
Sorties (photos de tiers, NON versionnées) : objets/photos_non_versionnees/<id>__<source>_<image>.jpg et planche_*.jpg.
Licences : Mapillary CC-BY-SA 4.0 ; Panoramax CC-BY-SA 4.0 (auteurs dans les noms de fichiers et dans vignettes_index.json).
"""
from __future__ import annotations

import base64
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun_at import DEBUT_TRAVAUX, O, RACINE, SORTIE, TELE, Batiments, ecrire, lire  # noqa: E402

PNV = SORTIE / "photos_non_versionnees"
MLY_IMG = RACINE / "data/raw/mapillary/paquet_jardin/img"
PNX_IMG = RACINE / "data/raw/panoramax/paquet_jardin"
DET = TELE / "mapillary_map_features/detections"
try:
    FT = ImageFont.truetype("arial.ttf", 15)
except OSError:
    FT = ImageFont.load_default()


# ----------------------------------------------------------------------------- MVT minimal (géométrie des détections)
def _varint(b, i):
    r, s = 0, 0
    while True:
        c = b[i]
        i += 1
        r |= (c & 0x7F) << s
        s += 7
        if not c & 0x80:
            return r, i


def _champs(b):
    i, out = 0, []
    while i < len(b):
        k, i = _varint(b, i)
        f, w = k >> 3, k & 7
        if w == 0:
            v, i = _varint(b, i)
        elif w == 2:
            n, i = _varint(b, i)
            v, i = b[i:i + n], i + n
        elif w == 5:
            v, i = b[i:i + 4], i + 4
        elif w == 1:
            v, i = b[i:i + 8], i + 8
        else:
            raise ValueError("wire type")
        out.append((f, v))
    return out


def mvt_bbox(geom_b64):
    """Boîte normalisée [0,1] (x0, y0, x1, y1) de la géométrie MVT d'une détection Mapillary."""
    b = base64.b64decode(geom_b64)
    xs, ys = [], []
    for f, lay in _champs(b):
        if f != 3:
            continue
        ext = 4096
        feats = []
        for g, v in _champs(lay):
            if g == 5:
                ext = v
            elif g == 2:
                feats.append(v)
        for ft in feats:
            for g, v in _champs(ft):
                if g != 4:
                    continue
                vals, j = [], 0
                while j < len(v):
                    x, j = _varint(v, j)
                    vals.append(x)
                k, x, y = 0, 0, 0
                while k < len(vals):
                    cmd, cnt = vals[k] & 7, vals[k] >> 3
                    k += 1
                    if cmd in (1, 2):
                        for _ in range(cnt):
                            dx, dy = vals[k], vals[k + 1]
                            k += 2
                            x += (dx >> 1) ^ -(dx & 1)
                            y += (dy >> 1) ^ -(dy & 1)
                            xs.append(x / ext)
                            ys.append(y / ext)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# ----------------------------------------------------------------------------- découpes
def vignette_mly(oid, fid, imd, nmax=2):
    fp = DET / f"{fid}.json"
    if not fp.exists():
        return []
    dets = lire(fp)
    if not isinstance(dets, list):
        return []
    res = []
    cand = []
    for d in dets:
        iid = (d.get("image") or {}).get("id")
        m = imd.get(iid or "")
        if not m or not (MLY_IMG / f"{iid}.jpg").exists():
            continue
        import datetime
        date = datetime.datetime.fromtimestamp(m["captured_at"] / 1000, datetime.UTC).strftime("%Y-%m-%d")
        if date >= DEBUT_TRAVAUX:
            continue
        bb = mvt_bbox(d["geometry"]) if d.get("geometry") else None
        if bb is None:
            continue
        cand.append(((bb[2] - bb[0]) * (bb[3] - bb[1]), date, iid, bb, m))
    cand.sort(key=lambda c: (-(c[1] >= "2023"), -c[0]))
    vus = set()
    for area, date, iid, bb, m in cand:
        if date in vus and len(cand) > nmax:
            continue
        im = Image.open(MLY_IMG / f"{iid}.jpg").convert("RGB")
        W, H = im.size
        x0, y0, x1, y1 = bb[0] * W, bb[1] * H, bb[2] * W, bb[3] * H
        w, h = max(x1 - x0, 20), max(y1 - y0, 20)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        s = max(w, h) * 1.6 + 60
        box = [int(max(0, cx - s)), int(max(0, cy - s * 1.2)), int(min(W, cx + s)), int(min(H, cy + s * 1.2))]
        cr = im.crop(box)
        dr = ImageDraw.Draw(cr)
        dr.rectangle([x0 - box[0], y0 - box[1], x1 - box[0], y1 - box[1]], outline=(255, 0, 255), width=3)
        cr = _hauteur(cr, 360)
        auteur = (m.get("creator") or {}).get("username", "?")
        lab = f"{oid} | Mapillary {iid} {date} (c) {auteur} CC-BY-SA"
        out = PNV / f"{oid}__mly_{iid}.jpg"
        _etiquette(cr, lab).save(out, quality=88)
        res.append({"objet": oid, "source": "mapillary", "image": iid, "date": date, "auteur": auteur,
                    "licence": "CC-BY-SA 4.0", "lien": f"https://www.mapillary.com/app/?pKey={iid}", "fichier": out.name})
        vus.add(date)
        if len(res) >= nmax:
            break
    return res


def vignette_pnx(o, poses, bat, nmax=2, dmin=3.0, dmax=40.0):
    g = o["geometry"]
    if g["type"] != "Point":
        return []
    x, y = g["coordinates"][:2]
    h = o["properties"].get("hauteur_m") or 3.0
    cands = []
    for ph in poses:
        p = ph.get("pose")
        if not p or not ("2023-01-01" <= ph["date"] < DEBUT_TRAVAUX) or ph["modele"] != "equirect":
            continue
        cx, cy = p["x"] + O[0], p["y"] + O[1]
        d = math.hypot(x - cx, y - cy)
        if not (dmin <= d <= dmax) or bat.occulte((cx, cy), (x, y)):
            continue
        cands.append((d, ph))
    cands.sort(key=lambda c: c[0])
    res, dates = [], set()
    for d, ph in cands:
        if ph["date"] in dates and len(cands) > nmax:
            continue
        f = PNX_IMG / ph["fichier"]
        if not f.exists():
            continue
        p = ph["pose"]
        cx, cy = p["x"] + O[0], p["y"] + O[1]
        az = math.degrees(math.atan2(x - cx, y - cy)) % 360
        lon = ((az - p["lacet"] + 180) % 360) - 180
        ch = p.get("z", 2.0) - (o["properties"].get("z_local") or 0.0) if False else 2.0
        e_bas = math.degrees(math.atan2(-ch, d))
        e_haut = math.degrees(math.atan2(max(h, 1.0) - ch, d))
        im = Image.open(f)
        W, H = im.size
        demi = max(math.degrees(math.atan2(2.5 + 0.2 * h, d)), 5.0)
        u = W * (0.5 + lon / 360.0)
        v_h = H * (0.5 - (e_haut + 4) / 180.0)
        v_b = H * (0.5 - (e_bas - 4) / 180.0)
        du = W * demi / 360.0
        box = [int(u - du), int(v_h), int(u + du), int(v_b)]
        if box[0] < 0 or box[2] > W:
            continue
        cr = im.crop(box).convert("RGB")
        dr = ImageDraw.Draw(cr)
        uu = u - box[0]
        dr.line([uu, 0, uu, 12], fill=(255, 0, 255), width=3)
        dr.line([uu, cr.size[1] - 12, uu, cr.size[1]], fill=(255, 0, 255), width=3)
        cr = _hauteur(cr, 360)
        lab = f"{o['properties']['id']} | Panoramax {ph['id8']} {ph['date']} d={d:.0f} m CC-BY-SA"
        out = PNV / f"{o['properties']['id']}__pnx_{ph['id8']}.jpg"
        _etiquette(cr, lab).save(out, quality=88)
        res.append({"objet": o["properties"]["id"], "source": "panoramax", "image": ph["id"], "date": ph["date"],
                    "licence": "CC-BY-SA 4.0", "distance_m": round(d, 1), "azimut_grille_deg": round(az, 1),
                    "pose_acceptee": ph.get("accepte"), "fichier": out.name})
        dates.add(ph["date"])
        if len(res) >= nmax:
            break
    return res


def _hauteur(im, H):
    w, h = im.size
    return im.resize((max(1, int(w * H / h)), H), Image.LANCZOS)


def _etiquette(im, txt):
    w, h = im.size
    out = Image.new("RGB", (max(w, 420), h + 22), (0, 0, 0))
    out.paste(im, (0, 22))
    ImageDraw.Draw(out).text((4, 3), txt[:80], fill=(255, 255, 255), font=FT)
    return out


def planche(nom, fichiers, larg=1800):
    ims = [Image.open(PNV / f) for f in fichiers if (PNV / f).exists()]
    if not ims:
        return None
    lignes, ligne, lw = [], [], 0
    for im in ims:
        if lw + im.size[0] > larg and ligne:
            lignes.append(ligne)
            ligne, lw = [], 0
        ligne.append(im)
        lw += im.size[0] + 6
    if ligne:
        lignes.append(ligne)
    H = sum(max(i.size[1] for i in l) + 6 for l in lignes)
    W = max(sum(i.size[0] + 6 for i in l) for l in lignes)
    pl = Image.new("RGB", (W, H), (40, 40, 40))
    y = 0
    for l in lignes:
        x = 0
        for i in l:
            pl.paste(i, (x, y))
            x += i.size[0] + 6
        y += max(i.size[1] for i in l) + 6
    out = PNV / f"planche_{nom}.jpg"
    pl.save(out, quality=85)
    return out


GROUPES = {
    "arrets_reviree": ["abri_SE_0396", "abri_NO_0021", "AT-OSM-node-6569621813", "banc_12321340512", "corbeille_1959017544",
                       "corbeille_1959017517", "mobilier_publicitaire_12507622173", "mobilier_publicitaire_12507625761"],
    "feux": ["feu_NE_TPC", "feu_NE_droite", "feu_SW_droite", "feu_VERC_ilot", "feu_SW_TPC", "feu_SW_cycles_SE",
             "AT-MLY-157992260473455", "AT-MLY-157992267140121"],
    "disparus_arbres": ["arbre_184", "arbre_229", "arbre_230", "arbre_018", "arbre_114", "arbre_365"],
    "mapillary_seul": ["AT-MLY-1528374764610675", "AT-MLY-501385605820412", "AT-MLY-330311029995205",
                       "AT-MLY-705943245063354", "AT-MLY-705943221730023", "AT-MLY-501385672487072"],
}


def revue_mapillary_seul(feats, imd, par_planche=16):
    """Une vignette Mapillary par objet connu seulement de Mapillary (contrôle de classe), planches de 16."""
    L = [f for f in feats.values() if f["properties"].get("origine_position") == "mapillary"
         and f["properties"]["etat_avant_travaux"] in ("present", "present_presume", "incertain")]
    L.sort(key=lambda f: (f["properties"]["type"], f["properties"]["id"]))
    fichiers, index = [], []
    for f in L:
        oid = f["properties"]["id"]
        r = []
        for fid in f["properties"].get("mapillary_ids", []):
            r = vignette_mly(oid, fid, imd, nmax=1)
            if r:
                break
        if not r:
            print("sans image locale :", oid)
        index += r
        fichiers += [x["fichier"] for x in r]
    for k in range(0, len(fichiers), par_planche):
        print(planche(f"mapillary_seul_{k // par_planche + 1:02d}", fichiers[k:k + par_planche], larg=1700))
    return index


def main(ids=None):
    PNV.mkdir(parents=True, exist_ok=True)
    feats = {f["properties"]["id"]: f for f in lire(SORTIE / "objets_avant_travaux.geojson")["features"]}
    feats.update({f["properties"]["id"]: f for f in lire(SORTIE / "objets_exclus.geojson")["features"]})
    imd = lire(TELE / "mapillary_map_features/images_detection.json")
    poses = lire(RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/poses.json")["photos"]
    bat = Batiments()
    if ids == ["--mapillary-seul"]:
        idx = revue_mapillary_seul(feats, imd)
        ecrire(PNV / "vignettes_mapillary_seul_index.json", {"licence": "photos de tiers CC-BY-SA 4.0 : ne pas versionner",
                                                             "vignettes": idx})
        return
    groupes = {"selection": ids} if ids else GROUPES
    index = []
    for g, L in groupes.items():
        fichiers = []
        for oid in L:
            o = feats.get(oid)
            if not o:
                print("absent :", oid)
                continue
            r = vignette_pnx(o, poses, bat)
            for fid in o["properties"].get("mapillary_ids", [])[:3]:
                if len(r) >= 3:
                    break
                r += vignette_mly(oid, fid, imd, nmax=1)
            if not r:
                print("aucune vignette :", oid)
            index += r
            fichiers += [x["fichier"] for x in r]
        p = planche(g, fichiers)
        print(g, len(fichiers), p)
    ecrire(PNV / "vignettes_index.json", {"licence": "photos de tiers CC-BY-SA 4.0 : ne pas versionner", "vignettes": index})


if __name__ == "__main__":
    main(sys.argv[1:] or None)
