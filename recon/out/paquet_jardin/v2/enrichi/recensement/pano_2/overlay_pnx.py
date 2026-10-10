"""overlay_pnx.py : découpes perspective Panoramax + superposition de la description v2 (agent VISION-PANORAMAX-2).

Projette dans des découpes gnomoniques (1200×900, FOV 70–90°) d'une photo Panoramax :
- bordures v2 (arête avant haute, zone pilote) en jaune ; bordures GAM 2026 hors zone pilote en orange ;
- îlots v2 (ceinture au niveau du dessus de bordure) en cyan ;
- marquages v2 (site complet) : neuf_2025 magenta, conservés / refaits rose clair, fantômes gris ;
- ponctuels au sol (BEV) en bleu clair ;
- objets (instances.json) : supports en rouge (verticale pied -> hauteur attendue), têtes de feux et
  panneaux en rectangle aux dimensions nominales, arbres en vert (tronc jusqu'à h + couronne) ;
- corrections du solveur de cohérence (p_source -> p_resolu) en bleu (verticale au point résolu).
Chaque découpe produit <id8>_v<k>_a<azimut>.jpg (superposition), ..._brut.jpg (photo seule) et
..._proj.json (pixels des entités : pied, sommet, distance), pour pointer ensuite les preuves.

Pose : 'auto' = calée acceptée (poses.json) > calée par VISION-PANORAMAX-2 (poses_pano2.json) >
calée refusée (poses.json) > brute GNSS. Le statut de pose est écrit sur chaque découpe.

Usage (depuis n'importe où, Python 3.11 système) :
  python overlay_pnx.py <id8> [--vues auto|az1,az2,..] [--tangage -8] [--fov 80] [--pose auto|calee|pano2|refusee|brute]
  python overlay_pnx.py --zoom <id8> x y z [--fov 14] [--taille 900] [--nom suffixe]   (vue étroite vers un point local)
  python overlay_pnx.py --pixel <id8> <crop_json> u v      (pixel d'une découpe -> rayon -> point au sol local)
"""
import argparse
import functools
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
sys.path.insert(0, str(RACINE / "recon/pcg"))
from camera import (O, Camera, camera, camera_calee, charger_poses, intrinseques, mnt,  # noqa: E402
                    photo, pose_brute)
from projection import camera_virtuelle, decoupe_perspective, intersection_sol, visee  # noqa: E402

ICI = Path(__file__).resolve().parent
CROPS = ICI / "crops"
POSES_PANO2 = ICI / "poses_pano2.json"
PKG = RACINE / "recon/out/paquet_jardin/package/donnees"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
GAM = RACINE / "data/sites/paquet_jardin/etat_2026"
FONT = "C:/Windows/Fonts/arial.ttf"

HAUT_NOMINAL = {"feu_mat": 1.0, "poteau_panneau": 1.0, "lampadaire_crosse_simple": 10.0,
                "lampadaire_crosse_double": 10.0, "lampadaire_mat_droit": 6.0, "arbre_feuillu": 10.0,
                "arbre_conifere": 12.0, "arbre_jeune_tuteure": 4.5, "arbuste_bosquet": 3.0, "souche": 0.4,
                "poteau_reseau": 9.0, "banc": 1.8, "corbeille": 0.6, "stationnement_velos": 0.8,
                "distributeur": 1.8, "conteneur_verre": 1.8, "fontaine": 1.1, "boite_aux_lettres": 1.3,
                "panneau_information": 2.2, "mobilier_publicitaire": 2.6, "armoire": 1.4, "mat_camera": 6.0,
                "poteau_incendie": 0.9, "potelet": 1.0, "portail": 1.6, "barriere_levante": 1.1, "chicane": 1.1,
                "balise_J11": 1.0, "abri_bus_JCDecaux": 2.5, "poteau_arret_bus": 2.8, "totem_PR": 2.8}
COURONNE_NOMINALE = {"arbre_feuillu": 6.0, "arbre_conifere": 5.0, "arbre_jeune_tuteure": 1.8, "arbuste_bosquet": 2.5}
# dimensions (l, h) des têtes et faces de panneaux (m)
DIM_TETE = {"feu_tete_R11v": (0.30, 0.95), "feu_tete_R11v_rep": (0.15, 0.45), "feu_tete_R12": (0.30, 0.65),
            "feu_tete_R13c": (0.15, 0.45), "panonceau_M12": (0.35, 0.30), "panonceau_AB3a": (0.35, 0.30),
            "panneau_B21a1": (0.45, 0.45), "panneau_J5": (0.30, 0.80), "panneau_AB3a": (0.70, 0.61),
            "panneau_AB4": (0.70, 0.70), "panneau_C113": (0.5, 0.5), "panneau_C114": (0.5, 0.5),
            "panneau_D21": (1.2, 0.7), "panneau_B1": (0.65, 0.65), "panneau_B2a": (0.65, 0.65),
            "panneau_B2b": (0.65, 0.65), "panneau_B6a1": (0.65, 0.65), "panneau_C13a": (0.5, 0.5),
            "panneau_M9": (0.5, 0.15), "panneau_A17": (1.0, 0.87)}
COUL = dict(bordure=(255, 220, 0), bordure_gam=(255, 140, 0), ilot=(0, 230, 255), mq_neuf=(255, 0, 255),
            mq_cons=(255, 160, 220), mq_fantome=(150, 150, 150), bev=(120, 180, 255), support=(255, 40, 40),
            tete=(255, 255, 255), arbre=(40, 255, 60), correction=(60, 120, 255), texte=(255, 255, 255))


def local(c):
    a = np.asarray(c, dtype=np.float64)
    o = np.array(O[:a.shape[-1]])
    return a - o


@functools.lru_cache(maxsize=1)
def _mnt():
    return mnt()


def z_mnt(x, y):
    return np.asarray(_mnt()(np.asarray(x) + O[0], np.asarray(y) + O[1]), dtype=np.float64) - O[2]


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _anneaux(g):
    if g["type"] == "Polygon":
        return [g["coordinates"][0]]
    if g["type"] == "MultiPolygon":
        return [p[0] for p in g["coordinates"]]
    if g["type"] == "LineString":
        return [g["coordinates"]]
    if g["type"] == "MultiLineString":
        return list(g["coordinates"])
    return []


def densifier(P, pas=0.3):
    P = np.asarray(P, dtype=np.float64)
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b[:2] - a[:2]) / pas)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


@functools.lru_cache(maxsize=1)
def entites():
    """Liste d'entités projetables (repère local)."""
    E = []
    # bordures v2 (3D, arête avant haute)
    zone_pilote = None
    d = lire(DESC / "base/bordures.geojson")
    xs, ys = [], []
    for f in d["features"]:
        p = f["properties"]
        P = local(np.array(f["geometry"]["coordinates"])[:, :3])
        xs += list(P[:, 0]); ys += list(P[:, 1])
        prof = ",".join(sorted({i["profil"] for i in p.get("intervalles", [])}))
        vue = ",".join(sorted({f"{i['vue_m']:.2f}" for i in p.get("intervalles", [])}))
        E.append(dict(id=p["id"], fam="bordure", kind="ligne", P=densifier(P), coul=COUL["bordure"],
                      lab=f"{p['id']} {prof} v{vue} {p.get('materiau', '')}", ep=2))
    zone_pilote = (min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1)
    # bordures GAM 2026 hors zone pilote
    g = lire(GAM / "bordure_lin_L93.geojson")
    for k, f in enumerate(g["features"]):
        for r in _anneaux(f["geometry"]):
            P = local(np.array(r)[:, :2])
            c = P.mean(0)
            if zone_pilote[0] < c[0] < zone_pilote[2] and zone_pilote[1] < c[1] < zone_pilote[3]:
                continue
            P = densifier(P, 0.5)
            P = np.c_[P, z_mnt(P[:, 0], P[:, 1]) + 0.12]
            E.append(dict(id=f"GAMK{k}", fam="bordure_gam", kind="ligne", P=P, coul=COUL["bordure_gam"], lab=None, ep=1))
    # îlots
    for f in lire(DESC / "base/ilots.geojson")["features"]:
        p = f["properties"]
        zt = (p.get("niveau") or {}).get("z_dessus_bordure_ngf")
        for r in _anneaux(f["geometry"]):
            P = densifier(local(np.array(r)[:, :2]))
            z = (zt - O[2]) if zt else z_mnt(P[:, 0], P[:, 1]) + 0.12
            P = np.c_[P, np.broadcast_to(z, len(P))]
            rem = (p.get("remplissage") or {}).get("materiau_id")
            E.append(dict(id=p["id"], fam="ilot", kind="ligne", P=P, coul=COUL["ilot"],
                          lab=f"{p['id']} {p.get('type')} {rem}", ep=2))
    # marquages
    for f in lire(DESC / "base/marquages.geojson")["features"]:
        p = f["properties"]
        et = p.get("etat")
        coul = COUL["mq_neuf"] if et == "neuf_2025" else COUL["mq_fantome"] if et == "fantome" else COUL["mq_cons"]
        lab = None
        if p.get("classe") in ("fleche", "symbole", "passage", "transversale", "zone"):
            lab = f"{p['id']} {p.get('gabarit') or p.get('type')}"
        for r in _anneaux(f["geometry"]):
            P = densifier(local(np.array(r)[:, :2]), 0.25)
            P = np.c_[P, z_mnt(P[:, 0], P[:, 1]) + 0.01]
            E.append(dict(id=p["id"], fam="marquage", kind="ligne", P=P, coul=coul, lab=lab, ep=1,
                          classe=p.get("classe"), etat=et))
            lab = None
    # ponctuels au sol
    for f in lire(DESC / "base/ponctuels_sol.geojson")["features"]:
        p = f["properties"]
        for r in _anneaux(f["geometry"]):
            P = local(np.array(r))
            if P.shape[1] == 2:
                P = np.c_[P, z_mnt(P[:, 0], P[:, 1])]
            E.append(dict(id=p["id"], fam="ponctuel", kind="ligne", P=densifier(P), coul=COUL["bev"],
                          lab=p["id"], ep=1))
    # objets
    mob = {f["properties"]["id"]: f["properties"] for f in lire(PKG / "objets/mobilier.geojson")["features"]}
    arb = {f["properties"]["id"]: f["properties"] for f in lire(PKG / "objets/arbres.geojson")["features"]}
    ins = lire(PKG / "objets/instances.json")["instances"]
    for x in ins:
        pr = x["prototype"]
        foot = np.array([x["x"], x["y"], x["z"]])
        st = (x.get("statut") or "")[:14]
        if pr in DIM_TETE:
            l, h = DIM_TETE[pr]
            E.append(dict(id=x["id"], fam="tete", kind="tete", C=foot, l=l, h=h, yaw=x.get("yaw_deg", 0.0),
                          coul=COUL["tete"], lab=f"{x['id']} {x.get('type_tete') or x.get('code') or pr}"))
            continue
        if pr.startswith("arbre") or pr in ("arbuste_bosquet", "souche"):
            a = arb.get(x["id"], {})
            h = a.get("hauteur_m") or HAUT_NOMINAL.get(pr, 10) * x["scale"][2]
            cour = a.get("diametre_couronne_m") or COURONNE_NOMINALE.get(pr, 2) * x["scale"][0]
            ess = a.get("essence") or ""
            E.append(dict(id=x["id"], fam="arbre", kind="arbre", foot=foot, h=float(h), cour=float(cour),
                          coul=COUL["arbre"], lab=f"{x['id']} h{h:.0f} c{cour:.0f} {ess[:18]} {st}"))
            continue
        m = mob.get(x["id"], {})
        h = m.get("hauteur_m") or HAUT_NOMINAL.get(pr, 1.0) * (x["scale"][2] if pr in ("feu_mat", "poteau_panneau") else 1.0)
        if pr in ("feu_mat", "poteau_panneau"):
            h = HAUT_NOMINAL[pr] * x["scale"][2]
        typ = m.get("lamp_type") or m.get("sous_type") or ""
        E.append(dict(id=x["id"], fam="support", kind="mat", foot=foot, h=float(h), coul=COUL["support"],
                      lab=f"{x['id']} {pr.replace('lampadaire_', 'lamp_')} h{h:.1f} {typ} {st}"))
    # clôtures (instances.json : lignes) : base et sommet
    for l in lire(PKG / "objets/instances.json").get("lignes", []):
        P = densifier(np.array(l["points"], dtype=np.float64), 0.5)
        z = z_mnt(P[:, 0], P[:, 1])
        h = float(l.get("hauteur_m") or 1.5)
        for dz, lab in ((0.02, None), (h, f"{l['id']} h{h:.1f}")):
            E.append(dict(id=l["id"], fam="cloture", kind="ligne", P=np.c_[P, z + dz], coul=(200, 120, 255), lab=lab, ep=1))
    # corrections de cohérence
    try:
        for f in lire(DESC / "coherence/corrections.geojson")["features"]:
            p = f["properties"]
            if not p.get("p_resolu_local") or p.get("d_m") in (None, 0):
                continue
            ps, pr_ = np.array(p["p_source_local"]), np.array(p["p_resolu_local"])
            z = float(z_mnt(pr_[0], pr_[1]))
            E.append(dict(id="COR:" + p["id"], fam="correction", kind="correction",
                          A=np.r_[ps, z_mnt(ps[0], ps[1])], B=np.r_[pr_, z], coul=COUL["correction"],
                          lab=f"->{p['id']} {p.get('d_m')}m"))
    except FileNotFoundError:
        pass
    return E


# --------------------------------------------------------------------------- poses
def poses_pano2():
    return lire(POSES_PANO2)["photos"] if POSES_PANO2.exists() else {}


def camera_photo(pid, mode="auto"):
    ph = photo(pid)
    P = charger_poses()
    rec = P.get(ph.id8)
    if mode in ("auto", "calee") and rec and rec.get("accepte") and rec.get("pose"):
        cam, st = camera_calee(ph.id8)
        return cam, "calee (poses.json, acceptee)"
    p2 = poses_pano2().get(ph.id8)
    if mode in ("auto", "pano2") and p2 and p2.get("qualite") != "rejetee":
        intr = {**intrinseques(ph), **(p2.get("intrinseques") or {})}
        q = p2["pose"]
        return camera(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]], intr), \
            f"calee VISION-PANORAMAX-2 ({p2.get('methode')}, {p2.get('qualite')})"
    if mode in ("auto", "refusee") and rec and rec.get("pose"):
        cam, st = camera_calee(ph.id8, accepte_seulement=False)
        return cam, "calee REFUSEE (poses.json) : a utiliser avec prudence"
    return camera(ph), "brute GNSS (non calee)"


# --------------------------------------------------------------------------- dessin
def _police(t):
    try:
        return ImageFont.truetype(FONT, t)
    except OSError:
        return ImageFont.load_default()


def _proj(cv, P):
    c = cv.monde_vers_cam(P)
    a = c[:, 1]
    uv = np.c_[cv.cx + cv.f * c[:, 0] / np.where(a > 1e-6, a, 1), cv.cy - cv.f * c[:, 2] / np.where(a > 1e-6, a, 1)]
    return uv, a, np.linalg.norm(c, axis=1)


def _dans(uv, W, H, m=0):
    return (uv[:, 0] >= -m) & (uv[:, 0] < W + m) & (uv[:, 1] >= -m) & (uv[:, 1] < H + m)


def dessiner(img, cv, dmax=45.0, dlab=30.0, familles=None, ids=None):
    """Superpose les entités ; renvoie (image, liste des entités projetées)."""
    im = img.copy()
    dr = ImageDraw.Draw(im)
    W, H = im.size
    fnt = _police(12)
    C = cv.C
    projs, labels = [], []
    for e in entites():
        if familles and e["fam"] not in familles:
            continue
        if ids and e["id"] not in ids and not e["id"].startswith(tuple(ids)):
            continue
        if e["kind"] == "ligne":
            P = e["P"]
            dd = np.hypot(P[:, 0] - C[0], P[:, 1] - C[1])
            if dd.min() > dmax:
                continue
            uv, a, dist = _proj(cv, P)
            ok = (a > 0.5) & (dd <= dmax) & _dans(uv, W, H, 400)
            vis = False
            for k in range(len(P) - 1):
                if ok[k] and ok[k + 1]:
                    dr.line([tuple(uv[k]), tuple(uv[k + 1])], fill=e["coul"], width=e.get("ep", 1))
                    if _dans(uv[k:k + 1], W, H)[0]:
                        vis = True
            if vis:
                inn = np.nonzero(ok & _dans(uv, W, H))[0]
                k = inn[len(inn) // 2]
                projs.append(dict(id=e["id"], fam=e["fam"], uv=[round(float(uv[k, 0]), 1), round(float(uv[k, 1]), 1)],
                                  d=round(float(dist[k]), 1)))
                if e.get("lab") and dist[k] <= dlab:
                    labels.append((uv[k], e["lab"], e["coul"], dist[k]))
        elif e["kind"] in ("mat", "arbre"):
            f = e["foot"]
            dd = math.hypot(f[0] - C[0], f[1] - C[1])
            if dd > (dmax + 15 if e["kind"] == "arbre" else dmax + 10):
                continue
            top = f + np.array([0, 0, e["h"]])
            uv, a, dist = _proj(cv, np.vstack([f, top]))
            if a.min() < 0.5 or not _dans(uv, W, H, 50).any():
                continue
            ep = 3 if e["kind"] == "mat" else 2
            dr.line([tuple(uv[0]), tuple(uv[1])], fill=e["coul"], width=ep)
            dr.line([(uv[0, 0] - 6, uv[0, 1]), (uv[0, 0] + 6, uv[0, 1])], fill=e["coul"], width=2)
            dr.line([(uv[1, 0] - 4, uv[1, 1]), (uv[1, 0] + 4, uv[1, 1])], fill=e["coul"], width=2)
            if e["kind"] == "arbre":
                t = np.linspace(0, 2 * np.pi, 25)
                r = e["cour"] / 2
                ring = np.c_[f[0] + r * np.cos(t), f[1] + r * np.sin(t), np.full(25, f[2] + 0.62 * e["h"])]
                u2, a2, _ = _proj(cv, ring)
                if (a2 > 0.5).all():
                    dr.line([tuple(p) for p in u2], fill=e["coul"], width=1)
            projs.append(dict(id=e["id"], fam=e["fam"], pied=[round(float(uv[0, 0]), 1), round(float(uv[0, 1]), 1)],
                              sommet=[round(float(uv[1, 0]), 1), round(float(uv[1, 1]), 1)], h=e["h"],
                              d=round(float(dist[0]), 1)))
            if dd <= dlab + (10 if e["kind"] == "mat" else 0):
                labels.append((uv[0] + np.array([4, -4]), e["lab"], e["coul"], dist[0]))
        elif e["kind"] == "tete":
            c0 = e["C"]
            dd = math.hypot(c0[0] - C[0], c0[1] - C[1])
            if dd > dmax:
                continue
            uv, a, dist = _proj(cv, c0[None])
            if a[0] < 0.5 or not _dans(uv, W, H, 20)[0]:
                continue
            s = cv.f / dist[0]
            w2, h2 = e["l"] * s / 2, e["h"] * s / 2
            # face vers la caméra ? (yaw : sens trigo depuis +X)
            n = np.array([math.cos(math.radians(e["yaw"])), math.sin(math.radians(e["yaw"]))])
            v = (C[:2] - c0[:2]) / max(1e-6, np.linalg.norm(C[:2] - c0[:2]))
            face = float(n @ v)
            col = (255, 255, 255) if face > 0.3 else (255, 255, 120) if face > -0.3 else (160, 160, 160)
            dr.rectangle([uv[0, 0] - w2, uv[0, 1] - h2, uv[0, 0] + w2, uv[0, 1] + h2], outline=col, width=1)
            projs.append(dict(id=e["id"], fam="tete", uv=[round(float(uv[0, 0]), 1), round(float(uv[0, 1]), 1)],
                              d=round(float(dist[0]), 1), face_vers_camera=round(face, 2)))
            if dd <= dlab:
                labels.append((uv[0] + np.array([w2 + 2, -6]), e["lab"] + ("" if face > 0.3 else " (dos)" if face < -0.3 else " (tranche)"), col, dist[0]))
        elif e["kind"] == "correction":
            A, B = e["A"], e["B"]
            if math.hypot(B[0] - C[0], B[1] - C[1]) > dmax:
                continue
            uv, a, dist = _proj(cv, np.vstack([A, B, B + [0, 0, 2.5]]))
            if a.min() < 0.5 or not _dans(uv, W, H, 50).any():
                continue
            dr.line([tuple(uv[0]), tuple(uv[1])], fill=e["coul"], width=2)
            dr.line([tuple(uv[1]), tuple(uv[2])], fill=e["coul"], width=2)
            projs.append(dict(id=e["id"], fam="correction", pied=[round(float(uv[1, 0]), 1), round(float(uv[1, 1]), 1)],
                              d=round(float(dist[1]), 1)))
            labels.append((uv[2], e["lab"], e["coul"], dist[1]))
    # étiquettes (proches d'abord, sans recouvrement grossier)
    occ = []
    for uv, t, col, d in sorted(labels, key=lambda x: x[3]):
        x, y = float(uv[0]), float(uv[1])
        if not (0 <= x < W and 0 <= y < H):
            continue
        bb = dr.textbbox((x, y), t, font=fnt)
        for _ in range(8):
            if not any(not (bb[2] < o[0] or bb[0] > o[2] or bb[3] < o[1] or bb[1] > o[3]) for o in occ):
                break
            y += 14
            bb = dr.textbbox((x, y), t, font=fnt)
        occ.append(bb)
        dr.rectangle(bb, fill=(0, 0, 0))
        dr.text((x, y), t, fill=col, font=fnt)
    return im, projs


def cartouche(im, texte):
    dr = ImageDraw.Draw(im)
    f = _police(15)
    bb = dr.textbbox((6, 4), texte, font=f)
    dr.rectangle(bb, fill=(0, 0, 0))
    dr.text((6, 4), texte, fill=(255, 255, 0), font=f)
    return im


# --------------------------------------------------------------------------- choix des vues
def vues_auto(cam, n=4, fov=80.0, rayon=35.0):
    C = cam.C
    poids = np.zeros(360)
    for e in entites():
        if e["kind"] == "ligne":
            P = e["P"][::4]
            w = {"ilot": 3.0, "marquage": 0.5, "bordure": 0.4, "bordure_gam": 0.3, "ponctuel": 1.0}.get(e["fam"], 0.3)
        elif e["kind"] in ("mat", "arbre"):
            P = e["foot"][None]
            w = 3.0 if e["kind"] == "mat" else 0.7
        elif e["kind"] == "tete":
            P = e["C"][None]
            w = 2.0
        else:
            continue
        d = np.hypot(P[:, 0] - C[0], P[:, 1] - C[1])
        k = (d < rayon) & (d > 1.5)
        if not k.any():
            continue
        az = (np.degrees(np.arctan2(P[k, 0] - C[0], P[k, 1] - C[1])) % 360).astype(int)
        np.add.at(poids, az, w / (1 + d[k] / 12))
    cap = cam.pose[3]
    lis = np.convolve(np.r_[poids[-40:], poids, poids[:40]], np.ones(int(fov * 0.8)), "same")[40:400]
    choix = [int(round(cap)) % 360]
    while len(choix) < n:
        sc = lis.copy()
        for c in choix:
            dd = np.abs(((np.arange(360) - c) + 180) % 360 - 180)
            sc[dd < 70] = -1
        k = int(np.argmax(sc))
        if sc[k] <= 0:
            break
        choix.append(k)
    return choix


# --------------------------------------------------------------------------- commandes
def traiter(pid, vues="auto", tangage=-4.0, fov=80.0, mode="auto", taille=(1200, 900), sortie=CROPS, dmax=45.0):
    ph = photo(pid)
    cam, statut = camera_photo(ph.id8, mode)
    sortie.mkdir(parents=True, exist_ok=True)
    if not ph.is360:
        # photo à plat : une vue dans l'axe, au champ de la photo
        hf = math.degrees(2 * math.atan((cam.W / 2) / cam.f))
        lst = [(cam.pose[3], cam.pose[4], hf, (1200, int(round(1200 * cam.H / cam.W))))]
    else:
        azs = vues_auto(cam, fov=fov) if vues == "auto" else [float(a) for a in str(vues).split(",")]
        lst = [(a, tangage, fov, taille) for a in azs]
    res = []
    for k, (az, tg, fv, ts) in enumerate(lst):
        img, cv = decoupe_perspective(ph.id8, az, tg, fv, ts, cam=cam)
        nom = f"{ph.id8}_v{k}_a{int(round(az)) % 360:03d}"
        img.save(sortie / f"{nom}_brut.jpg", quality=92)
        titre = f"{ph.id8} {ph.date} {'360' if ph.is360 else 'plat'} | az {az:.0f} tg {tg:.0f} fov {fv:.0f} | pose {statut}"
        ov, projs = dessiner(img, cv, dmax=dmax, familles=("support", "tete", "arbre", "correction", "cloture"))
        cartouche(ov, titre + " | OBJETS")
        ov.save(sortie / f"{nom}_obj.jpg", quality=90)
        ov2, projs2 = dessiner(img, cv, dmax=dmax, familles=("bordure", "bordure_gam", "ilot", "marquage", "ponctuel"))
        cartouche(ov2, titre + " | SOL")
        ov2.save(sortie / f"{nom}_sol.jpg", quality=90)
        projs = projs + projs2
        ov3, _ = dessiner(img, cv, dmax=dmax, dlab=0, familles=("bordure", "bordure_gam", "ilot", "marquage", "ponctuel"))
        ov3, _ = dessiner(ov3, cv, dmax=dmax, dlab=30, familles=("support", "tete", "arbre", "cloture"))
        cartouche(ov3, titre + " | TOUT")
        ov3.save(sortie / f"{nom}_tout.jpg", quality=88)
        meta = dict(photo=ph.id8, date=ph.date, datetime=ph.datetime, fichier=ph.jpg.name, pose_statut=statut,
                    pose=[round(float(v), 4) for v in cam.pose], vue=dict(lacet=az, tangage=tg, fov=fv, taille=list(ts)),
                    cam_virtuelle=dict(pose=[round(float(v), 5) for v in cv.pose], f=cv.f, W=cv.W, H=cv.H),
                    entites=projs)
        (sortie / f"{nom}_proj.json").write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")
        res.append(nom)
        print(nom, statut, len(projs))
    return res


def cam_depuis_json(js):
    m = lire(js)
    q = m["cam_virtuelle"]
    return Camera("stenope", int(q["W"]), int(q["H"]), np.array(q["pose"]), f=q["f"], cx=q["W"] / 2, cy=q["H"] / 2), m


def pixel_vers_sol(js, u, v):
    """Pixel (u, v) d'une découpe -> point au sol (MNT 2026) local."""
    cv, m = cam_depuis_json(js)
    d = cv.rayons(np.array([[u, v]], float))
    t = intersection_sol(cv.C, d)
    if not np.isfinite(t[0]):
        return None
    X = cv.C + t[0] * d[0]
    return X


def rayon_decoupe(js, u, v):
    cv, m = cam_depuis_json(js)
    d = cv.rayons(np.array([[u, v]], float))[0]
    return cv.C.copy(), d


def zoom(pid, x, y, z, fov=14.0, taille=900, nom=None, mode="auto", sortie=CROPS, superposer=True):
    ph = photo(pid)
    cam, statut = camera_photo(ph.id8, mode)
    lac, tg = visee(cam, np.array([x, y, z]))
    img, cv = decoupe_perspective(ph.id8, lac, tg, fov, (taille, taille), cam=cam)
    nom = nom or f"{ph.id8}_zoom_{x:.1f}_{y:.1f}"
    img.save(sortie / f"{nom}_brut.jpg", quality=94)
    meta = dict(photo=ph.id8, date=ph.date, pose_statut=statut, cible=[x, y, z],
                vue=dict(lacet=lac, tangage=tg, fov=fov, taille=[taille, taille]),
                cam_virtuelle=dict(pose=[round(float(v), 5) for v in cv.pose], f=cv.f, W=cv.W, H=cv.H))
    if superposer:
        ov, projs = dessiner(img, cv, dmax=60, dlab=60)
        cartouche(ov, f"{ph.id8} {ph.date} zoom fov {fov:.0f} -> ({x:.1f},{y:.1f},{z:.1f}) | {statut[:30]}")
        ov.save(sortie / f"{nom}.jpg", quality=92)
        meta["entites"] = projs
    (sortie / f"{nom}_proj.json").write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")
    print(nom, statut)
    return nom


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("photo", nargs="?")
    ap.add_argument("--vues", default="auto")
    ap.add_argument("--tangage", type=float, default=-4.0)
    ap.add_argument("--fov", type=float, default=80.0)
    ap.add_argument("--pose", default="auto")
    ap.add_argument("--dmax", type=float, default=45.0)
    ap.add_argument("--zoom", nargs=4, metavar=("ID8", "X", "Y", "Z"))
    ap.add_argument("--taille", type=int, default=900)
    ap.add_argument("--nom")
    ap.add_argument("--pixel", nargs=3, metavar=("JSON", "U", "V"))
    a = ap.parse_args(argv)
    if a.zoom:
        zoom(a.zoom[0], float(a.zoom[1]), float(a.zoom[2]), float(a.zoom[3]), fov=a.fov if a.fov != 80 else 14.0,
             taille=a.taille, nom=a.nom, mode=a.pose)
    elif a.pixel:
        X = pixel_vers_sol(a.pixel[0], float(a.pixel[1]), float(a.pixel[2]))
        print(None if X is None else [round(float(v), 3) for v in X],
              None if X is None else [round(float(X[0] + O[0]), 3), round(float(X[1] + O[1]), 3)])
    else:
        traiter(a.photo, a.vues, a.tangage, a.fov, a.pose, dmax=a.dmax)


if __name__ == "__main__":
    main()
