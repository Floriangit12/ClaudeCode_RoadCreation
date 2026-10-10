"""overlay_pnx.py : découpes perspective d'une photo Panoramax + superposition des entités projetées
de la description v2 (bordures, îlots, surfaces, marquages, BEV, mobilier, arbres, corrections de
cohérence), pour le recensement visuel (agent VISION-PANORAMAX-0).

Repère : local = L93 − O (917279.43, 6460289.98), z = NGF − 216,30 (decrire/commun.py).
Boîte à outils : recon/pcg/enrichir (camera, projection, triangulation) — lecture seule.

Pose utilisée, par ordre de priorité (le statut est écrit dans vues.json et dans le bandeau) :
  1. `calee`        : poses.json accepté (recon/out/.../enrichi/poses) ;
  2. `calee_pano0`  : calage refait par pano_0 (poses.caler, sortie redirigée vers pano_0/poses_pano0/) accepté ;
  3. `manuelle`     : poses_manuelles.json (ajustement à l'œil : Δlacet, Δx, Δy, Δz, tangage…) ;
  4. `sequence`     : a priori de séquence (voisins acceptés de la même prise de vue) ;
  5. `brute`        : GNSS + azimut Panoramax (± 4-5 m, ± 8-25°) : superposition indicative seulement.

Commandes (Python 3.11 système ; lancer avec `python -I`) :
  python -I overlay_pnx.py vues <id8> [--auto] [--vue nom lacet tangage fov] [--dmax 45]
      -> pano_0/vues/<id8>/<nom>.jpg (brut), <nom>_ov.jpg (superposition), vues.json (caméras)
  python -I overlay_pnx.py zoom <id8> --cible <entité|x,y,z> [--fov 14] [--taille 900] [--dz 2]
  python -I overlay_pnx.py sol <id8> <vue> u v           # rayon du pixel de la découpe -> sol (MNT 2026)
  python -I overlay_pnx.py tri <id8>:<vue>:u:v ...       # triangulation d'un point (>= 2 photos posées)
  python -I overlay_pnx.py axe <id8>:<vue>:u:v ...       # axe vertical d'un mât/tronc (>= 2 photos)
  python -I overlay_pnx.py pose <id8>                    # pose retenue et sa source
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(r"D:/ClaudeCode_RoadCreation")
ENRICHIR = RACINE / "recon/pcg/enrichir"
for p in (str(ENRICHIR), str(ENRICHIR.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

import camera as CAM  # noqa: E402
from camera import O, camera, catalogue, charger_poses, intrinseques, lire_json, mnt, photo, pose_brute  # noqa: E402
from projection import (camera_virtuelle, decoupe_perspective, intersection_sol,  # noqa: E402
                        occulte_par_batiments, reechantillonner)

ICI = Path(__file__).resolve().parent
VUES = ICI / "vues"
# calages refaits par pano_0 (même chaîne poses.caler, sortie redirigée) : 35a02e70 et 6d922988 acceptés,
# les autres refusés mais porteurs d'un a priori de séquence
SCRATCH_PAR_PHOTO = ICI / "poses_pano0"
POSES_MANUELLES = ICI / "poses_manuelles.json"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
OBJ = RACINE / "recon/out/paquet_jardin/package/donnees/objets"
GAM = RACINE / "data/sites/paquet_jardin/etat_2026"
OX, OY, OZ = O
POLICE = "C:/Windows/Fonts/arialbd.ttf"


# --------------------------------------------------------------------------- poses
def _pose_de(rec):
    q = rec["pose"]
    return [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]


def camera_pnx(pid):
    """(Camera, statut, info) selon la priorité décrite en tête de fichier."""
    ph = photo(pid)
    intr = intrinseques(ph)
    main = charger_poses().get(ph.id8)
    if main and main.get("accepte") and main.get("pose"):
        i2 = {**intr, **(main.get("intrinseques") or {})}
        return camera(ph, _pose_de(main), i2), "calee", dict(qualite=main.get("qualite"))
    f = SCRATCH_PAR_PHOTO / f"{ph.id8}.json"
    if f.exists():
        r = lire_json(f)
        if r.get("accepte") and r.get("pose") and r.get("date") == ph.date:
            i2 = {**intr, **(r.get("intrinseques") or {})}
            return camera(ph, _pose_de(r), i2), "calee_pano0", dict(qualite=r.get("qualite"))
    man = lire_json(POSES_MANUELLES).get(ph.id8) if POSES_MANUELLES.exists() else None
    base = None
    src_base = "brute"
    for rec in (main, lire_json(f) if f.exists() else None):
        if rec and rec.get("a_priori_sequence"):
            q = rec["a_priori_sequence"]["pose"]
            base = [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]
            src_base = "sequence"
            break
    if base is None:
        base = list(pose_brute(ph)["pose"])
    if man:
        if man.get("base") == "brute":
            base, src_base = list(pose_brute(ph)["pose"]), "brute"
        d = man.get("delta", {})
        p = list(base)
        p[0] += d.get("dx", 0.0)
        p[1] += d.get("dy", 0.0)
        p[2] += d.get("dz", 0.0)
        p[3] += d.get("dlacet", 0.0)
        p[4] = d.get("tangage", p[4])
        p[5] = d.get("roulis", p[5])
        i2 = dict(intr)
        if man.get("hfov") and not ph.is360:
            i2["f"] = (ph.W / 2.0) / math.tan(math.radians(man["hfov"]) / 2.0)
        return camera(ph, p, i2), "manuelle", dict(base=src_base, delta=d, note=man.get("note"))
    return camera(ph, base, intr), src_base, {}


# --------------------------------------------------------------------------- entités
def _z_mnt(xy):
    m = mnt()
    xy = np.asarray(xy, float)
    return np.asarray(m(xy[:, 0] + OX, xy[:, 1] + OY), float) - OZ


def _local3(coords, dz=0.0):
    a = np.asarray(coords, float)
    if a.ndim == 1:
        a = a[None]
    xy = a[:, :2] - [OX, OY]
    if a.shape[1] >= 3 and np.all(a[:, 2] > 100):
        z = a[:, 2] - OZ
    else:
        z = _z_mnt(xy)
    return np.c_[xy, z + dz]


def _anneaux(g):
    t = g["type"]
    c = g["coordinates"]
    if t == "Polygon":
        return [c[0]]
    if t == "MultiPolygon":
        return [p[0] for p in c]
    if t == "LineString":
        return [c]
    if t == "MultiLineString":
        return list(c)
    return []


def _densifier(P, pas=1.5):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(np.linalg.norm(b[:2] - a[:2]) / pas)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


_CACHE = {}


def entites():
    """Liste d'entités : dict(id, fam, lignes [N×3 local], pied (3,), h, label, couleur, extra)."""
    if "e" in _CACHE:
        return _CACHE["e"]
    E = []
    base = DESC / "base"
    # bordures v2 (zone pilote) : arête avant 3D
    for f in lire_json(base / "bordures.geojson")["features"]:
        p = f["properties"]
        iv = p.get("intervalles") or []
        prof = "/".join(sorted({i["profil"] for i in iv}))
        vue = max([i.get("vue_m") or 0 for i in iv] or [0])
        L = [_densifier(_local3(r), 1.0) for r in _anneaux(f["geometry"])]
        E.append(dict(id=p["id"], fam="bordure", lignes=L, label=f'{p["id"]} {prof} {vue:.2f} {p.get("materiau","")}',
                      couleur=(255, 230, 0), largeur=3, extra=dict(vue=vue)))
    # bordures GAM 2026 (tout le site), z = MNT
    for k, f in enumerate(lire_json(GAM / "bordure_lin_L93.geojson")["features"]):
        L = [_densifier(_local3(r), 1.0) for r in _anneaux(f["geometry"])]
        E.append(dict(id=f"GAMb{k}", fam="bordure_gam", lignes=L, label=None, couleur=(255, 140, 0), largeur=1))
    for f in lire_json(base / "ilots.geojson")["features"]:
        p = f["properties"]
        L = [_densifier(_local3(r, 0.12), 1.0) for r in _anneaux(f["geometry"])]
        E.append(dict(id=p["id"], fam="ilot", lignes=L,
                      label=f'{p["id"]} {p["type"]} {p["remplissage"]["materiau_id"]}', couleur=(255, 0, 255), largeur=2))
    for f in lire_json(base / "surfaces.geojson")["features"]:
        p = f["properties"]
        L = [_densifier(_local3(r, 0.02), 1.5) for r in _anneaux(f["geometry"])]
        E.append(dict(id=p["id"], fam="surface", lignes=L,
                      label=f'{p["id"]} {p["classe"]} {(p.get("revetement") or {}).get("materiau_id","")}',
                      couleur=(120, 200, 255), largeur=1))
    for f in lire_json(base / "ponctuels_sol.geojson")["features"]:
        p = f["properties"]
        L = [_local3(r, 0.02) for r in _anneaux(f["geometry"])]
        E.append(dict(id=p["id"], fam="bev", lignes=L, label=p["id"], couleur=(255, 255, 255), largeur=1))
    for f in lire_json(base / "marquages.geojson")["features"]:
        p = f["properties"]
        L = [_densifier(_local3(r, 0.01), 1.5) for r in _anneaux(f["geometry"])]
        cl = p["classe"]
        lab = None
        if cl in ("fleche", "passage", "symbole", "zone", "transversale"):
            lab = f'{p["id"]} {p["type"]}{" " + p["gabarit"] if p.get("gabarit") else ""} [{p.get("etat","")}]'
        et = p.get("etat", "")
        col = {"neuf_2025": (0, 255, 255), "fantome": (150, 150, 150), "refait_2025_identique": (120, 255, 200)}.get(et, (255, 255, 255))
        E.append(dict(id=p["id"], fam="marquage", classe=cl, lignes=L, label=lab, couleur=col, largeur=1, etat=et))
    # mobilier
    for f in lire_json(OBJ / "mobilier.geojson")["features"]:
        p = f["properties"]
        h = float(p.get("hauteur_m") or 1.0)
        if f["geometry"]["type"] != "Point":
            L = []
            for r in _anneaux(f["geometry"]):
                b = _densifier(_local3(r), 1.0)
                L += [b, b + [0, 0, h]]
            E.append(dict(id=p["id"], fam="cloture", lignes=L, label=f'{p["id"]} h{h:.1f}', couleur=(200, 120, 255), largeur=1))
            continue
        if p.get("x_local") is not None:
            pied = np.array([p["x_local"], p["y_local"], p["z_local"]], float)
        else:
            pied = _local3(f["geometry"]["coordinates"])[0]
        t = p["type"]
        col = {"support_feux": (255, 40, 40), "panneau": (40, 120, 255), "lampadaire": (60, 255, 60),
               "balise_J11": (40, 120, 255), "potelet": (255, 160, 0)}.get(t, (255, 120, 200))
        lab = f'{p["id"]} h{h:.1f}'
        if p.get("code"):
            lab = f'{p["id"]} [{p["code"]}] h{h:.1f}'
        tetes = []
        for i, te in enumerate(p.get("tetes") or []):
            tetes.append((pied + [0, 0, float(te.get("hauteur_centre_m") or 2.5)], f'{te["type"]}@{te.get("azimut_deg")}'))
        E.append(dict(id=p["id"], fam="mobilier", type=t, pied=pied, h=h, label=lab, couleur=col, largeur=2,
                      tetes=tetes, statut=p.get("statut_2026")))
    for f in lire_json(OBJ / "arbres.geojson")["features"]:
        p = f["properties"]
        pied = np.array([p["x_local"], p["y_local"], p["z_local"]], float)
        h = float(p.get("hauteur_m") or 5)
        ess = (p.get("essence") or p["type"])[:22]
        E.append(dict(id=p["id"], fam="arbre", pied=pied, h=h, couronne=float(p.get("diametre_couronne_m") or 3),
                      label=f'{p["id"]} {ess} h{h:.0f} c{float(p.get("diametre_couronne_m") or 0):.0f}',
                      couleur=(0, 200, 90), largeur=2, statut=p.get("statut_2026")))
    # positions résolues par le solveur de cohérence (mobilier et arbres déplacés)
    cor = DESC / "coherence/corrections.geojson"
    if cor.exists():
        for f in lire_json(cor)["features"]:
            p = f["properties"]
            if p.get("p_resolu_local") and p.get("nature", "").startswith("deplacement"):
                x, y = p["p_resolu_local"]
                pied = np.array([x, y, _z_mnt([[x, y]])[0]])
                E.append(dict(id="C:" + p["id"], fam="correction", pied=pied, h=2.5, label="C:" + p["id"],
                              couleur=(255, 0, 255), largeur=1))
    _CACHE["e"] = E
    return E


def par_id(eid):
    for e in entites():
        if e["id"] == eid:
            return e
    return None


# --------------------------------------------------------------------------- dessin
def _police(n):
    try:
        return ImageFont.truetype(POLICE, n)
    except OSError:
        return ImageFont.load_default()


def _proj_seg(cv, P):
    """Projette une polyligne 3D dans la caméra virtuelle sténopé (découpage au plan avant)."""
    c = (np.asarray(P, float) - cv.C) @ cv.R.T
    morceaux, cur = [], []
    near = 0.3
    for k in range(len(c)):
        a = c[k]
        if a[1] > near:
            if not cur and k > 0 and c[k - 1][1] <= near:
                b = c[k - 1]
                t = (near - b[1]) / (a[1] - b[1])
                cur.append(b + t * (a - b))
            cur.append(a)
        else:
            if cur:
                b = c[k - 1]
                t = (near - b[1]) / (a[1] - b[1])
                cur.append(b + t * (a - b))
                morceaux.append(cur)
                cur = []
    if cur:
        morceaux.append(cur)
    out = []
    for m in morceaux:
        m = np.array(m)
        x, y = m[:, 0] / m[:, 1], m[:, 2] / m[:, 1]
        out.append(np.c_[cv.cx + cv.f * x, cv.cy - cv.f * y])
    return out


def _dans(uv, w, h, marge=0):
    return (uv[0] >= -marge) & (uv[0] < w + marge) & (uv[1] >= -marge) & (uv[1] < h + marge)


FAM_SOL = ("bordure", "bordure_gam", "ilot", "surface", "bev", "marquage")
FAM_OBJ = ("mobilier", "arbre", "correction", "cloture")
LAB_MAX = dict(marquage=16.0, surface=14.0, bordure=30.0, ilot=40.0, bev=12.0, cloture=20.0,
               mobilier=40.0, arbre=22.0, correction=40.0)


def dessiner(img, cv, dmax=45.0, familles=None, labels_max=60.0, dmax_sol=35.0):
    """Superpose les entités sur l'image PIL de la vue cv. Renvoie (image, liste des entités vues)."""
    im = img.copy()
    dr = ImageDraw.Draw(im, "RGBA")
    W, H = im.size
    ft = _police(13)
    vus = []
    C = cv.C
    poses_lab = []

    def texte(u, v, s, col):
        if not s:
            return
        u, v = int(u), int(v)
        for (a, b) in poses_lab:
            if abs(a - u) < 120 and abs(b - v) < 14:
                v += 15
        poses_lab.append((u, v))
        bb = dr.textbbox((u, v), s, font=ft)
        dr.rectangle([bb[0] - 2, bb[1] - 1, bb[2] + 2, bb[3] + 1], fill=(0, 0, 0, 150))
        dr.text((u, v), s, fill=col, font=ft)

    for e in entites():
        if familles and e["fam"] not in familles:
            continue
        if "lignes" in e:
            dm = dmax_sol if e["fam"] in ("marquage", "surface", "bordure_gam", "bev") else dmax
            best = None
            for L in e["lignes"]:
                dd = np.hypot(L[:, 0] - C[0], L[:, 1] - C[1])
                if dd.min() > dm:
                    continue
                Lc = L[dd <= dm + 5]
                if len(Lc) < 2:
                    continue
                for m in _proj_seg(cv, Lc):
                    if len(m) < 2:
                        continue
                    if not np.any([_dans(q, W, H) for q in m]):
                        continue
                    dr.line([tuple(q) for q in m], fill=e["couleur"] + (230,), width=e["largeur"])
                    ok = [q for q in m if _dans(q, W, H, -20)]
                    if ok and best is None:
                        best = ok[len(ok) // 2]
                        dlab = float(dd.min())
            if best is not None:
                vus.append([e["id"], round(float(best[0]), 1), round(float(best[1]), 1), round(dlab, 1)])
                if e.get("label") and dlab <= LAB_MAX.get(e["fam"], 20.0):
                    texte(best[0] + 4, best[1] + 2, e["label"], (150, 210, 255) if e["fam"] == "surface" else e["couleur"])
        else:
            P = e["pied"]
            d = math.hypot(P[0] - C[0], P[1] - C[1])
            if d > dmax:
                continue
            haut = P + [0, 0, e["h"]]
            segs = _proj_seg(cv, np.array([P, haut]))
            if not segs:
                continue
            m = segs[0]
            if not (_dans(m[0], W, H) or _dans(m[-1], W, H)):
                continue
            occ = bool(occulte_par_batiments(C, P[None] + [0, 0, 0.5])[0])
            col = e["couleur"] + ((110,) if occ else (240,))
            dr.line([tuple(m[0]), tuple(m[-1])], fill=col, width=e["largeur"])
            u, v = m[0]
            dr.ellipse([u - 4, v - 4, u + 4, v + 4], outline=col, width=2)
            if e["fam"] == "arbre":
                # houppier : barre horizontale (diamètre) au 2/3 de la hauteur, perpendiculaire à la visée
                vd = np.array([P[0] - C[0], P[1] - C[1]])
                vd = vd / (np.linalg.norm(vd) + 1e-9)
                n = np.array([-vd[1], vd[0], 0.0]) * e["couronne"] / 2
                zc = P + [0, 0, e["h"] * 0.62]
                s2 = _proj_seg(cv, np.array([zc - n, zc + n]))
                if s2:
                    dr.line([tuple(s2[0][0]), tuple(s2[0][-1])], fill=col, width=1)
            for (T, lab) in e.get("tetes", []):
                s3 = _proj_seg(cv, np.array([T, T + [0, 0, 0.01]]))
                if s3:
                    a, b = s3[0][0]
                    dr.rectangle([a - 5, b - 9, a + 5, b + 9], outline=(255, 60, 60, 240), width=2)
                    if d < 25:
                        texte(a + 7, b - 8, lab, (255, 120, 120))
            vus.append([e["id"], round(float(u), 1), round(float(v), 1), round(d, 1)] + (["occ"] if occ else []))
            if d <= min(labels_max, LAB_MAX.get(e["fam"], 30.0)):
                texte(u + 5, min(v, H - 18), e["label"] + f" {d:.0f}m" + (" (occ)" if occ else ""), e["couleur"])
    return im, vus


def bandeau(im, txt):
    dr = ImageDraw.Draw(im, "RGBA")
    ft = _police(16)
    dr.rectangle([0, 0, im.size[0], 22], fill=(0, 0, 0, 170))
    dr.text((4, 2), txt, fill=(255, 255, 255), font=ft)
    return im


# --------------------------------------------------------------------------- vues
def vues_auto(pid, cam):
    ph = photo(pid)
    lac = float(cam.pose[3])
    if ph.is360:
        return [("av", lac, -8, 90), ("dr", lac + 90, -8, 90), ("ar", lac + 180, -8, 90), ("ga", lac - 90, -8, 90)]
    hf = 2 * math.degrees(math.atan((cam.W / 2) / cam.f))
    tg = float(cam.pose[4])
    return [("plein", lac, tg, hf), ("g", lac - hf / 4, tg, hf / 2 + 6), ("d", lac + hf / 4, tg, hf / 2 + 6)]


def faire_vues(pid, vues=None, dmax=45.0, taille=(1200, 900), dossier=None, familles=None):
    ph = photo(pid)
    cam, statut, info = camera_pnx(pid)
    vues = vues or vues_auto(pid, cam)
    dossier = Path(dossier or VUES / ph.id8)
    dossier.mkdir(parents=True, exist_ok=True)
    meta_f = dossier / "vues.json"
    meta = lire_json(meta_f) if meta_f.exists() else {}
    meta.update(dict(photo=ph.id, id8=ph.id8, date=ph.datetime, fichier=str(ph.jpg), modele=cam.modele,
                     pose_statut=statut, pose=[round(float(x), 4) for x in cam.pose], pose_info=info,
                     f=cam.f, W=cam.W, H=cam.H))
    meta.setdefault("vues", {})
    for (nom, lac, tg, fov) in vues:
        img, cv = decoupe_perspective(ph.id8, lac % 360, tg, fov, taille, cam=cam)
        img.save(dossier / f"{nom}.jpg", quality=90)
        vus = []
        for suff, fams in (("sol", FAM_SOL), ("obj", FAM_OBJ)):
            if familles:
                fams = tuple(f for f in fams if f in familles)
                if not fams:
                    continue
            ov, v_ = dessiner(img, cv, dmax=dmax, familles=fams)
            vus += v_
            bandeau(ov, f"{ph.id8} {ph.datetime[:16]} pose={statut} vue={nom} lacet={lac % 360:.1f} tg={tg:.1f} fov={fov:.0f} [{suff}]")
            ov.save(dossier / f"{nom}_{suff}.jpg", quality=88)
        meta["vues"][nom] = dict(lacet=round(lac % 360, 3), tangage=tg, fov=fov, taille=list(taille), entites_vues=vus)
    with open(meta_f, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    return meta


def cam_vue(pid, nom):
    ph = photo(pid)
    meta = lire_json(VUES / ph.id8 / "vues.json")
    v = meta["vues"][nom]
    cam, statut, _ = camera_pnx(pid)
    cv = camera_virtuelle(cam, v["lacet"], v["tangage"], v["fov"], tuple(v["taille"]))
    return cam, cv, statut


def zoom(pid, cible, fov=14.0, taille=900, dz=None, nom=None, dmax=60.0):
    ph = photo(pid)
    cam, statut, _ = camera_pnx(pid)
    if isinstance(cible, str) and "," not in cible:
        e = par_id(cible)
        P = e["pied"] + [0, 0, (e.get("h", 2.0) * 0.6 if dz is None else dz)] if "pied" in e else \
            np.mean(np.vstack(e["lignes"]), 0)
        nom = nom or f"zoom_{cible.replace(':', '_')}"
    else:
        P = np.array([float(x) for x in cible.split(",")])
        if len(P) == 2:
            P = np.r_[P, _z_mnt([P])[0] + (dz or 0.0)]
        nom = nom or f"zoom_{P[0]:.1f}_{P[1]:.1f}"
    d = P - cam.C
    lac = math.degrees(math.atan2(d[0], d[1])) % 360
    tg = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    vues = [(nom, lac, tg, fov)]
    return faire_vues(pid, vues, dmax=dmax, taille=(taille, taille))


def pixel_vers_rayon(pid, nom, u, v):
    cam, cv, statut = cam_vue(pid, nom)
    d = cv.rayons(np.array([[u, v]], float))[0]
    return cam.C.copy(), d, statut, cam


def sol(pid, nom, u, v):
    C, d, statut, cam = pixel_vers_rayon(pid, nom, u, v)
    t = intersection_sol(C, d[None])[0]
    if not np.isfinite(t):
        return None
    X = C + t * d
    return dict(local=[round(float(x), 3) for x in X], l93=[round(float(X[0] + OX), 3), round(float(X[1] + OY), 3)],
                distance_m=round(float(t), 2), pose=statut)


def _parse_obs(spec):
    pid, nom, u, v = spec.split(":")
    return pid, nom, float(u), float(v)


def trianguler_px(specs):
    """Point le plus proche de >= 2 rayons (moindres carrés), pondérés par 1/distance."""
    C, D, st = [], [], []
    for s in specs:
        c, d, statut, _ = pixel_vers_rayon(*_parse_obs(s))
        C.append(c)
        D.append(d)
        st.append(statut)
    C, D = np.array(C), np.array(D)
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for c, d in zip(C, D):
        M = np.eye(3) - np.outer(d, d)
        A += M
        b += M @ c
    P = np.linalg.solve(A, b)
    res = [float(np.linalg.norm(np.cross(P - c, d))) for c, d in zip(C, D)]
    az = [math.degrees(math.atan2(*(P[:2] - c[:2]))) for c in C]
    da = max(abs(((a - b_ + 180) % 360) - 180) for a in az for b_ in az)
    return dict(local=[round(float(x), 3) for x in P], l93=[round(float(P[0] + OX), 3), round(float(P[1] + OY), 3)],
                residus_m=[round(r, 3) for r in res], angle_max_deg=round(min(da, 180 - da) if da > 90 else da, 1),
                poses=st)


def axe_vertical(specs):
    """Axe vertical (x, y) d'un mât à partir de pixels sur son axe dans >= 2 photos (plans verticaux)."""
    C, N, st = [], [], []
    for s in specs:
        c, d, statut, _ = pixel_vers_rayon(*_parse_obs(s))
        n = np.cross(d, [0, 0, 1.0])[:2]
        N.append(n / np.linalg.norm(n))
        C.append(c[:2])
        st.append(statut)
    N, C = np.array(N), np.array(C)
    b = np.sum(N * C, axis=1)
    X = np.linalg.lstsq(N, b, rcond=None)[0]
    res = (N @ X - b).tolist()
    az = [math.degrees(math.atan2(*(X - c))) for c in C]
    da = 0.0
    for a in az:
        for b_ in az:
            x = abs(((a - b_ + 180) % 360) - 180)
            da = max(da, min(x, 180 - x))
    return dict(local=[round(float(x), 3) for x in X], l93=[round(float(X[0] + OX), 3), round(float(X[1] + OY), 3)],
                residus_m=[round(r, 3) for r in res], angle_intersection_deg=round(da, 1), poses=st)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--vue", nargs=4, action="append")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--dmax", type=float, default=45.0)
    ap.add_argument("--cible")
    ap.add_argument("--fov", type=float, default=14.0)
    ap.add_argument("--taille", type=int, default=900)
    ap.add_argument("--dz", type=float, default=None)
    ap.add_argument("--nom")
    a = ap.parse_args(argv)
    if a.cmd == "vues":
        for pid in a.args:
            vues = [(v[0], float(v[1]), float(v[2]), float(v[3])) for v in a.vue] if a.vue else None
            m = faire_vues(pid, vues, dmax=a.dmax)
            print(pid, m["pose_statut"], {k: len(v["entites_vues"]) for k, v in m["vues"].items()})
    elif a.cmd == "zoom":
        m = zoom(a.args[0], a.cible, fov=a.fov, taille=a.taille, dz=a.dz, nom=a.nom, dmax=a.dmax)
        print(json.dumps({k: v for k, v in m["vues"].items() if k.startswith(a.nom or "zoom")}, ensure_ascii=False)[:600])
    elif a.cmd == "sol":
        print(json.dumps(sol(a.args[0], a.args[1], float(a.args[2]), float(a.args[3]))))
    elif a.cmd == "tri":
        print(json.dumps(trianguler_px(a.args)))
    elif a.cmd == "axe":
        print(json.dumps(axe_vertical(a.args)))
    elif a.cmd == "pose":
        cam, st, info = camera_pnx(a.args[0])
        print(st, np.round(cam.pose, 3).tolist(), json.dumps(info, ensure_ascii=False)[:400])


if __name__ == "__main__" and sys.argv[1:2] not in (["planche"], ["multi"]):
    main()


# --------------------------------------------------------------------------- planche de zooms
def planche(pid, cibles, tuile=420, n_col=3, chemin=None, fov_min=5.0, fov_max=40.0, marge=1.6, dmax=80.0, h_max=99.0):
    """Planche de zooms sur des entités (axe projeté en trait fin) : une tuile par cible.
    cible = id d'entité ou 'x,y[,z]' (local) ; fov choisi pour que la hauteur de l'objet occupe ~60 %."""
    ph = photo(pid)
    cam, statut, _ = camera_pnx(pid)
    tuiles, meta = [], []
    for c in cibles:
        if "," in c:
            P = np.array([float(v) for v in c.split(",")])
            if len(P) == 2:
                P = np.r_[P, _z_mnt([P])[0]]
            h, e = 2.5, None
        else:
            e = par_id(c)
            if e is None:
                continue
            if "pied" in e:
                P, h = e["pied"].copy(), e.get("h", 2.5)
            else:
                L = np.vstack(e["lignes"])
                dd = np.hypot(L[:, 0] - cam.C[0], L[:, 1] - cam.C[1])
                P, h = L[np.argmin(dd)].copy(), 1.0
        hv = min(h, h_max)
        d3 = P + [0, 0, hv / 2] - cam.C
        dist = float(np.linalg.norm(d3[:2]))
        if dist > dmax:
            continue
        lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
        tg = math.degrees(math.atan2(d3[2], dist))
        fov = float(np.clip(2 * math.degrees(math.atan(marge * max(hv, 1.5) / 2 / max(dist, 0.5))), fov_min, fov_max))
        img, cv = decoupe_perspective(ph.id8, lac, tg, fov, (tuile, tuile), cam=cam)
        dr = ImageDraw.Draw(img, "RGBA")
        if e is not None and "pied" in e:
            s = _proj_seg(cv, np.array([P, P + [0, 0, h]]))
            if s:
                (a, b), (a2, b2) = s[0][0], s[0][-1]
                dr.line([(a, b), (a2, b2)], fill=(255, 0, 255, 150), width=1)
                dr.ellipse([a - 5, b - 5, a + 5, b + 5], outline=(255, 0, 255, 200), width=1)
                for (T, lab) in e.get("tetes", []):
                    s3 = _proj_seg(cv, np.array([T, T + [0, 0, 0.01]]))
                    if s3:
                        x, y = s3[0][0]
                        dr.rectangle([x - 4, y - 7, x + 4, y + 7], outline=(255, 60, 60, 160), width=1)
        ft = _police(13)
        lab = f"{c} d={dist:.1f}m fov={fov:.0f}"
        dr.rectangle([0, tuile - 18, tuile, tuile], fill=(0, 0, 0, 170))
        dr.text((3, tuile - 17), lab, fill=(255, 255, 255), font=ft)
        tuiles.append(img)
        meta.append(dict(cible=c, lacet=round(lac, 3), tangage=round(tg, 3), fov=round(fov, 3), taille=[tuile, tuile],
                         distance_m=round(dist, 2)))
    if not tuiles:
        return None
    n_lig = int(math.ceil(len(tuiles) / n_col))
    out = Image.new("RGB", (n_col * tuile, n_lig * tuile + 22), (0, 0, 0))
    for k, t in enumerate(tuiles):
        out.paste(t, ((k % n_col) * tuile, 22 + (k // n_col) * tuile))
    bandeau(out, f"{ph.id8} {ph.datetime[:16]} pose={statut} planche ({len(tuiles)} zooms)")
    chemin = Path(chemin or ICI / "preuves" / f"{ph.id8}_planche.jpg")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=88)
    # caméras des tuiles pour le pointage (vues.json, préfixe = nom de planche)
    dossier = VUES / ph.id8
    dossier.mkdir(parents=True, exist_ok=True)
    mf = dossier / "vues.json"
    m = lire_json(mf) if mf.exists() else dict(photo=ph.id, id8=ph.id8, date=ph.datetime, vues={})
    m.setdefault("vues", {})
    for k, mm in enumerate(meta):
        m["vues"][f"{chemin.stem}#{k}"] = dict(lacet=mm["lacet"], tangage=mm["tangage"], fov=mm["fov"],
                                              taille=mm["taille"], entites_vues=[], cible=mm["cible"])
    m["pose_statut"] = statut
    with open(mf, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=1)
    return str(chemin), meta


def _main_planche(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("pid")
    ap.add_argument("cibles", nargs="+")
    ap.add_argument("--nom")
    ap.add_argument("--tuile", type=int, default=420)
    ap.add_argument("--col", type=int, default=3)
    ap.add_argument("--marge", type=float, default=1.6)
    a = ap.parse_args(argv)
    ch = ICI / "preuves" / f"{photo(a.pid).id8}_{a.nom}.jpg" if a.nom else None
    r = planche(a.pid, a.cibles, tuile=a.tuile, n_col=a.col, chemin=ch, marge=a.marge)
    print(r[0] if r else "rien", [(m["cible"], m["distance_m"]) for m in (r[1] if r else [])])


if __name__ == "__main__" and sys.argv[1:2] == ["planche"]:
    _main_planche(sys.argv[2:])


# --------------------------------------------------------------------------- planche multi-photos
def photos_calees():
    """id8 des photos à pose calée acceptée (poses.json + calages pano_0)."""
    out = [k for k, p in charger_poses().items() if p.get("accepte")]
    if SCRATCH_PAR_PHOTO.exists():
        for f in SCRATCH_PAR_PHOTO.glob("*.json"):
            r = lire_json(f)
            if r.get("accepte") and r["id8"] not in out:
                out.append(r["id8"])
    return sorted(out)


def multi(cible, ids=None, dmax=45.0, tuile=380, n_col=4, chemin=None, marge=1.6, h=None, n_max=12):
    """Même cible vue depuis plusieurs photos calées : une tuile par photo (pour pointer puis trianguler)."""
    if "," in cible:
        P = np.array([float(v) for v in cible.split(",")])
        if len(P) == 2:
            P = np.r_[P, _z_mnt([P])[0]]
        hh = h or 2.5
        e = None
    else:
        e = par_id(cible)
        P, hh = e["pied"].copy(), (h or e.get("h", 2.5))
    cands = []
    for pid in (ids or photos_calees()):
        cam, st, _ = camera_pnx(pid)
        d = float(np.hypot(*(P[:2] - cam.C[:2])))
        if d <= dmax:
            cands.append((d, pid, cam, st))
    cands.sort(key=lambda x: x[0])
    tuiles, meta = [], []
    for d, pid, cam, st in cands[:n_max]:
        if bool(occulte_par_batiments(cam.C, (P + [0, 0, 0.5])[None])[0]):
            continue
        d3 = P + [0, 0, hh / 2] - cam.C
        lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
        tg = math.degrees(math.atan2(d3[2], d))
        fov = float(np.clip(2 * math.degrees(math.atan(marge * max(hh, 1.5) / 2 / max(d, 0.5))), 5.0, 50.0))
        img, cv = decoupe_perspective(pid, lac, tg, fov, (tuile, tuile), cam=cam)
        dr = ImageDraw.Draw(img, "RGBA")
        s = _proj_seg(cv, np.array([P, P + [0, 0, hh]]))
        if s:
            (a, b), (a2, b2) = s[0][0], s[0][-1]
            dr.line([(a, b), (a2, b2)], fill=(255, 0, 255, 140), width=1)
            dr.ellipse([a - 5, b - 5, a + 5, b + 5], outline=(255, 0, 255, 200), width=1)
        ph = photo(pid)
        dr.rectangle([0, tuile - 18, tuile, tuile], fill=(0, 0, 0, 170))
        dr.text((3, tuile - 17), f"{pid} {ph.date} d={d:.1f} fov={fov:.0f}", fill=(255, 255, 255), font=_police(13))
        tuiles.append(img)
        meta.append(dict(pid=pid, lacet=round(lac, 3), tangage=round(tg, 3), fov=round(fov, 3), taille=[tuile, tuile],
                         distance_m=round(d, 2), date=ph.date))
    if not tuiles:
        return None
    n_lig = int(math.ceil(len(tuiles) / n_col))
    out = Image.new("RGB", (n_col * tuile, n_lig * tuile + 22), (0, 0, 0))
    for k, t in enumerate(tuiles):
        out.paste(t, ((k % n_col) * tuile, 22 + (k // n_col) * tuile))
    nom = cible.replace(",", "_").replace(":", "_")
    bandeau(out, f"multi-photos {cible} ({len(tuiles)} photos calées)")
    chemin = Path(chemin or ICI / "preuves" / f"multi_{nom}.jpg")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=88)
    for k, mm in enumerate(meta):
        dossier = VUES / mm["pid"]
        dossier.mkdir(parents=True, exist_ok=True)
        mf = dossier / "vues.json"
        m = lire_json(mf) if mf.exists() else dict(photo=photo(mm["pid"]).id, id8=mm["pid"], vues={})
        m.setdefault("vues", {})
        m["vues"][f"{chemin.stem}#{k}"] = dict(lacet=mm["lacet"], tangage=mm["tangage"], fov=mm["fov"],
                                              taille=mm["taille"], entites_vues=[], cible=cible)
        with open(mf, "w", encoding="utf-8") as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
    return str(chemin), meta


if __name__ == "__main__" and sys.argv[1:2] == ["multi"]:
    _ap = argparse.ArgumentParser()
    _ap.add_argument("x")
    _ap.add_argument("cible")
    _ap.add_argument("--dmax", type=float, default=45.0)
    _ap.add_argument("--h", type=float, default=None)
    _ap.add_argument("--marge", type=float, default=1.6)
    _ap.add_argument("--n", type=int, default=12)
    _a = _ap.parse_args()
    _a.cible = _a.cible[1:] if _a.cible.startswith("p") and "," in _a.cible else _a.cible
    _r = multi(_a.cible, dmax=_a.dmax, h=_a.h, marge=_a.marge, n_max=_a.n)
    print(_r[0] if _r else "rien", [(m["pid"], m["date"], m["distance_m"]) for m in (_r[1] if _r else [])])
