"""Découpes perspective des photos Panoramax + superposition des entités de la description v2.

Agent VISION-PANORAMAX-1 (recensement). Réutilisable : python overlay_pnx.py <id8> [options]

Pour chaque vue (lacet grille, tangage, fov horizontal), produit dans preuves/ :
- <id8>_v<k>.jpg        découpe 1200×900 avec superposition (bordures, îlots, marquages,
                        mobilier et arbres en verticales sol -> hauteur attendue, corrections du
                        solveur de cohérence en magenta, bordures GAM 2026 hors zone pilote) ;
- <id8>_v<k>_brut.jpg   la même découpe sans superposition (lecture des faces de panneaux, etc.) ;
- <id8>_v<k>.json       paramètres de la vue (pose utilisée et sa source, caméra virtuelle) et
                        pixels de chaque entité projetée (étiquette -> id, uv pied / sommet).

Pose : ordre de préférence (--pose auto) : calée acceptée (enrichi/poses/poses.json) > calée
acceptée par l'agent (pano_1/poses_pano1/<id8>.json) > calée refusée (indicative) > a priori de
séquence > brute GNSS. La source est écrite dans la légende et dans le .json : une projection
avec une pose non acceptée n'est qu'indicative (aucun écart de position n'en est déduit).

API (mesures dans une vue déjà produite) :
    from overlay_pnx import rayon_vue, sol_vue, trianguler_vues, verticale_vues
    C, d = rayon_vue("119d9094", 2, (u, v))           # rayon local depuis un pixel de la vue v2
    P = sol_vue("119d9094", 2, (u, v))                # point au sol (MNT 2026) du pixel
    r = trianguler_vues([("119d9094", 2, (u1, v1)), ("2ab4efbc", 1, (u2, v2))])
    r = verticale_vues([...])                         # axe vertical d'un mât (pixels sur l'axe)

Repère : local = L93 − O(917279,43 ; 6460289,98), z = NGF − 216,30 (decrire/commun.py).
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path("D:/ClaudeCode_RoadCreation")
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
sys.path.insert(0, str(RACINE / "recon/pcg"))
from camera import (O, Camera, camera, charger_poses, intrinseques, photo, pose_brute,  # noqa: E402
                    z_sol)
from projection import camera_virtuelle, intersection_sol, reechantillonner  # noqa: E402
from camera import image_rgb  # noqa: E402

ICI = Path(__file__).resolve().parent
PREUVES = ICI / "preuves"
POSES_AGENT = ICI / "poses_pano1"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
OBJ = RACINE / "recon/out/paquet_jardin/package/donnees/objets"
GAM = RACINE / "data/sites/paquet_jardin/etat_2026"
ZP = dict(x_min=-11.0, y_min=-28.0, x_max=60.0, y_max=72.0)   # zone pilote ZP-01 (local)
Z0 = 216.30


def _lire(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _police(t):
    for nom in ("arialbd.ttf", "arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            continue
    return ImageFont.load_default()


# --------------------------------------------------------------------------- pose
def pose_photo(id8, mode="auto"):
    """(Camera, source) ; source ∈ calee | calee_agent | calee_refusee | calee_refusee_agent |
    sequence | brute."""
    ph = photo(id8)
    P = charger_poses()
    p = P.get(ph.id8)
    agent = POSES_AGENT / f"{ph.id8}.json"
    ra = _lire(agent) if agent.exists() else None

    def cam_de(rec):
        q = rec["pose"]
        intr = {**intrinseques(ph), **(rec.get("intrinseques") or {})}
        return camera(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]], intr)

    if mode.startswith("fichier:"):
        return cam_de(_lire(mode[8:])), "fichier"
    ordre = {"auto": ["calee", "calee_agent", "calee_refusee", "calee_refusee_agent", "sequence", "brute"],
             "calee": ["calee"], "agent": ["calee_agent", "calee_refusee_agent"],
             "refusee": ["calee_refusee", "calee_refusee_agent"], "sequence": ["sequence"],
             "brute": ["brute"]}[mode]
    for s in ordre:
        if s == "calee" and p and p.get("accepte") and p.get("pose"):
            return cam_de(p), s
        if s == "calee_agent" and ra and ra.get("accepte") and ra.get("pose"):
            return cam_de(ra), s
        if s == "calee_refusee" and p and p.get("pose") and not p.get("accepte"):
            return cam_de(p), s
        if s == "calee_refusee_agent" and ra and ra.get("pose") and not ra.get("accepte"):
            return cam_de(ra), s
        if s == "sequence":
            for rec in (p, ra):
                if rec and rec.get("a_priori_sequence"):
                    q = rec["a_priori_sequence"]["pose"]
                    return camera(ph, [q["x"], q["y"], q["z"], q["lacet"], q["tangage"], q["roulis"]]), s
        if s == "brute":
            return camera(ph, pose_brute(ph)["pose"]), s
    return camera(ph, pose_brute(ph)["pose"]), "brute"


# --------------------------------------------------------------------------- entités
_CACHE = {}


def _loc2(c):
    a = np.asarray(c, dtype=np.float64)
    return a[..., :2] - np.array(O[:2])


def _avec_z(xy, z=None):
    xy = np.atleast_2d(xy)
    if z is None:
        z = np.array([z_sol(x, y) for x, y in xy])
    return np.c_[xy, z]


def _densifier(P, pas=0.3):
    out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(np.ceil(np.linalg.norm(b[:2] - a[:2]) / pas)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    return np.array(out)


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


def entites():
    """Toutes les entités projetables, une fois : liste de dict(id, fam, lignes [(N,3)], mats [(pied, h)],
    lab, style, xy (centre local))."""
    if "e" in _CACHE:
        return _CACHE["e"]
    E = []
    # bordures v2 (zone pilote) : arête avant 3D + pied (z - vue)
    f = DESC / "base/bordures.geojson"
    if f.exists():
        for ft in _lire(f)["features"]:
            p = ft["properties"]
            c = np.asarray(ft["geometry"]["coordinates"], dtype=np.float64)
            P = np.c_[_loc2(c), c[:, 2] - Z0]
            iv = p.get("intervalles") or [{}]
            vue = float(np.median([i.get("vue_m", 0.1) or 0.0 for i in iv]))
            prof = "/".join(sorted({str(i.get("profil")) for i in iv}))
            E.append(dict(id=p["id"], fam="bordure", lignes=[P, P - [0, 0, vue]], mats=[],
                          lab=f"{p['id']} {prof} {vue:.2f}m {p.get('materiau', '')}", style="bordure",
                          xy=P[:, :2].mean(0)))
    # bordures GAM 2026 hors zone pilote
    f = GAM / "bordure_lin_L93.geojson"
    if f.exists():
        for k, ft in enumerate(_lire(f)["features"]):
            xy = _loc2(ft["geometry"]["coordinates"])
            if ((xy[:, 0] > ZP["x_min"]) & (xy[:, 0] < ZP["x_max"]) & (xy[:, 1] > ZP["y_min"])
                    & (xy[:, 1] < ZP["y_max"])).all():
                continue
            E.append(dict(id=f"GAM_bord_{k}", fam="bordure_gam", lignes=[_avec_z(xy)], mats=[], lab="",
                          style="gam", xy=xy.mean(0)))
    # îlots
    f = DESC / "base/ilots.geojson"
    if f.exists():
        for ft in _lire(f)["features"]:
            p = ft["properties"]
            for r in _anneaux(ft["geometry"]):
                xy = _loc2(r)
                E.append(dict(id=p["id"], fam="ilot", lignes=[_avec_z(xy) + [0, 0, 0.12]], mats=[],
                              lab=f"{p['id']} {p.get('type')} {(p.get('remplissage') or {}).get('materiau_id', '')}",
                              style="ilot", xy=xy.mean(0)))
    # BEV et ponctuels
    f = DESC / "base/ponctuels_sol.geojson"
    if f.exists():
        for ft in _lire(f)["features"]:
            p = ft["properties"]
            for r in _anneaux(ft["geometry"]):
                xy = _loc2(r)
                E.append(dict(id=p["id"], fam="ponctuel", lignes=[_avec_z(xy) + [0, 0, 0.02]], mats=[],
                              lab=p["id"], style="bev", xy=xy.mean(0)))
    # marquages (tout le site)
    f = DESC / "base/marquages.geojson"
    if f.exists():
        for ft in _lire(f)["features"]:
            p = ft["properties"]
            et = p.get("etat")
            sty = "fantome" if (p.get("classe") == "fantome" or et == "fantome") else (
                "marq_jaune" if p.get("couleur") == "jaune" else "marq")
            lab = ""
            if p.get("classe") in ("fleche", "passage", "symbole", "transversale") or p.get("type") in ("zebra",):
                lab = f"{p['id']} {p.get('type')}{'/' + p['gabarit'] if p.get('gabarit') else ''} {et or ''}"
            lignes = [_avec_z(_loc2(r)) + [0, 0, 0.01] for r in _anneaux(ft["geometry"])]
            if not lignes:
                continue
            E.append(dict(id=p["id"], fam="marquage", lignes=lignes, mats=[], lab=lab, style=sty,
                          xy=np.vstack([l[:, :2] for l in lignes]).mean(0), etat=et))
    # mobilier
    for ft in _lire(OBJ / "mobilier.geojson")["features"]:
        p = ft["properties"]
        if p.get("type") == "cloture":
            continue
        pied = np.array([p["x_local"], p["y_local"], p.get("z_local") or z_sol(p["x_local"], p["y_local"])])
        h = float(p.get("hauteur_m") or 2.0)
        tetes = [t.get("hauteur_centre_m") for t in (p.get("tetes") or []) if t.get("hauteur_centre_m")]
        code = p.get("code") or p.get("code_panneau") or ""
        E.append(dict(id=p["id"], fam="mobilier", lignes=[], mats=[(pied, h, tetes)],
                      lab=f"{p['id']} {p.get('type')} {code} h{h:.1f}", style="mob", xy=pied[:2],
                      statut=p.get("statut_2026")))
    # clôtures : lignes à 1 m (si LineString), sinon ignorées
    for ft in _lire(OBJ / "mobilier.geojson")["features"]:
        p = ft["properties"]
        if p.get("type") != "cloture" or ft["geometry"]["type"] not in ("LineString", "MultiLineString"):
            continue
        for r in _anneaux(ft["geometry"]):
            xy = _loc2(r)
            E.append(dict(id=p["id"], fam="cloture", lignes=[_avec_z(xy) + [0, 0, float(p.get("hauteur_m") or 1.2)]],
                          mats=[], lab="", style="cloture", xy=xy.mean(0)))
    # arbres
    for ft in _lire(OBJ / "arbres.geojson")["features"]:
        p = ft["properties"]
        pied = np.array([p["x_local"], p["y_local"], p.get("z_local") or z_sol(p["x_local"], p["y_local"])])
        h = float(p.get("hauteur_m") or 6.0)
        ess = (p.get("essence") or p.get("type") or "")[:22]
        E.append(dict(id=p["id"], fam="arbre", lignes=[], mats=[(pied, h, [])],
                      couronne=float(p.get("diametre_couronne_m") or 0.0),
                      lab=f"{p['id']} {ess} h{h:.0f} c{float(p.get('diametre_couronne_m') or 0):.0f}",
                      style="arbre", xy=pied[:2], statut=p.get("statut_2026")))
    # corrections du solveur de cohérence (positions résolues)
    f = DESC / "coherence/corrections.geojson"
    if f.exists():
        idx = {e["id"]: e for e in E if e["fam"] in ("mobilier", "arbre")}
        for ft in _lire(f)["features"]:
            p = ft["properties"]
            if not p.get("p_resolu_local") or p.get("nature", "").startswith("reorientation"):
                continue
            src = idx.get(p["id"])
            if src is None:
                continue
            xy = np.asarray(p["p_resolu_local"], dtype=np.float64)
            pied = np.array([xy[0], xy[1], (p.get("z_resolu_ngf") or (z_sol(*xy) + Z0)) - Z0])
            E.append(dict(id=p["id"] + "*", fam="correction", lignes=[], mats=[(pied, src["mats"][0][1], [])],
                          lab=f"{p['id']}* corr {p.get('d_m')}m", style="corr", xy=xy))
    _CACHE["e"] = E
    return E


# --------------------------------------------------------------------------- dessin
STYLES = {
    "bordure": ((255, 140, 0), 2), "gam": ((255, 230, 0), 1), "ilot": ((255, 0, 255), 2),
    "bev": ((255, 255, 255), 1), "marq": ((0, 255, 255), 1), "marq_jaune": ((255, 255, 0), 1),
    "fantome": ((150, 150, 150), 1), "mob": ((255, 40, 40), 2), "arbre": ((60, 255, 60), 2),
    "corr": ((255, 0, 255), 2), "cloture": ((200, 120, 255), 1),
}


def _proj(cv, P):
    """Projection sans masque d'image : (uv (N,2), devant (N,))."""
    c = cv.monde_vers_cam(P)
    a = c[:, 1]
    ok = a > 0.3
    a_ = np.where(ok, a, 1.0)
    uv = np.c_[cv.cx + cv.f * c[:, 0] / a_, cv.cy - cv.f * c[:, 2] / a_]
    return uv, ok


def _dans(uv, W, H, m=0):
    return (uv[:, 0] >= -m) & (uv[:, 0] < W + m) & (uv[:, 1] >= -m) & (uv[:, 1] < H + m)


def _etiquette(dr, xy, txt, col, police, places):
    if not txt:
        return
    x, y = int(xy[0]) + 4, int(xy[1]) - 8
    bb = dr.textbbox((x, y), txt, font=police)
    for _ in range(12):  # évite les chevauchements simples
        if not any(not (bb[2] < q[0] or bb[0] > q[2] or bb[3] < q[1] or bb[1] > q[3]) for q in places):
            break
        y += 13
        bb = dr.textbbox((x, y), txt, font=police)
    places.append(bb)
    dr.rectangle(bb, fill=(0, 0, 0))
    dr.text((x, y), txt, fill=col, font=police)


def dessiner(img, cv, C, dmax=60.0, familles=None, etiquettes=True):
    """Superpose les entités ; renvoie (image, liste des entités projetées)."""
    W, H = img.size
    out = img.copy()
    dr = ImageDraw.Draw(out)
    police = _police(13)
    places = []
    vus = []
    for e in entites():
        if familles and e["fam"] not in familles:
            continue
        if np.hypot(*(e["xy"] - C[:2])) > dmax + 30:
            continue
        col, w = STYLES[e["style"]]
        rec = None
        for k, L in enumerate(e["lignes"]):
            if len(L) < 2:
                continue
            Ld = _densifier(L, 0.3)
            dist = np.hypot(Ld[:, 0] - C[0], Ld[:, 1] - C[1])
            uv, ok = _proj(cv, Ld)
            ok &= dist <= dmax
            vis = ok & _dans(uv, W, H)
            if not vis.any():
                continue
            ww = w if k == 0 else 1
            for i in range(len(Ld) - 1):
                if ok[i] and ok[i + 1] and (vis[i] or vis[i + 1]):
                    if e["style"] == "fantome" and i % 2:
                        continue
                    dr.line([tuple(uv[i]), tuple(uv[i + 1])], fill=col, width=ww)
            if rec is None:
                j = np.nonzero(vis)[0]
                jm = j[len(j) // 2]
                rec = dict(id=e["id"], fam=e["fam"], uv=[round(float(uv[jm, 0]), 1), round(float(uv[jm, 1]), 1)],
                           dist_m=round(float(dist[jm]), 1), lab=e["lab"])
        for pied, h, tetes in e["mats"]:
            dist = float(np.hypot(*(pied[:2] - C[:2])))
            if dist > dmax:
                continue
            P = np.array([pied, pied + [0, 0, h]])
            uv, ok = _proj(cv, P)
            if not ok.all() or not _dans(uv, W, H, 50).any():
                continue
            dr.line([tuple(uv[0]), tuple(uv[1])], fill=col, width=w)
            r = 4
            dr.ellipse([uv[0, 0] - r, uv[0, 1] - r, uv[0, 0] + r, uv[0, 1] + r], outline=col, width=2)
            for ht in tetes:
                q, okq = _proj(cv, np.array([pied + [0, 0, ht]]))
                if okq[0]:
                    dr.rectangle([q[0, 0] - 5, q[0, 1] - 7, q[0, 0] + 5, q[0, 1] + 7], outline=(255, 255, 0), width=2)
            if e.get("couronne"):
                rr = e["couronne"] / 2
                zc = pied[2] + max(h * 0.62, h - rr)
                ang = np.linspace(0, 2 * np.pi, 25)
                Q = np.c_[pied[0] + rr * np.cos(ang), pied[1] + rr * np.sin(ang), np.full(25, zc)]
                q, okq = _proj(cv, Q)
                if okq.all():
                    dr.line([tuple(x) for x in q], fill=(60, 200, 60), width=1)
            rec = dict(id=e["id"], fam=e["fam"], uv_pied=[round(float(uv[0, 0]), 1), round(float(uv[0, 1]), 1)],
                       uv_sommet=[round(float(uv[1, 0]), 1), round(float(uv[1, 1]), 1)], dist_m=round(dist, 1),
                       h_m=h, lab=e["lab"])
        if rec is not None:
            vus.append(rec)
            lim = {"marquage": 25.0, "arbre": 30.0, "bordure": 25.0, "ilot": 40.0}.get(e["fam"], 60.0)
            if etiquettes and rec.get("lab") and rec["dist_m"] <= lim:
                xy = rec.get("uv_sommet") or rec.get("uv")
                if _dans(np.array([xy]), W, H).all():
                    _etiquette(dr, xy, rec["lab"], col, police, places)
    return out, vus


# --------------------------------------------------------------------------- vues automatiques
def _poids(C, dmax=40.0):
    az, w = [], []
    for e in entites():
        d = np.hypot(*(e["xy"] - C[:2]))
        if d > dmax or d < 1.0:
            continue
        a = math.degrees(math.atan2(e["xy"][0] - C[0], e["xy"][1] - C[1])) % 360
        p = {"mobilier": 3.0, "arbre": 1.0, "ilot": 2.0, "marquage": 0.6, "bordure": 1.0, "ponctuel": 0.5,
             "bordure_gam": 0.3}.get(e["fam"], 0.0)
        p *= 1.0 if d < 25 else 0.5
        az.append(a)
        w.append(p)
    return np.array(az), np.array(w)


def vues_auto(cam, n=4, fov=80.0, tangage=-4.0):
    """Choix glouton de n directions (lacet) couvrant le plus d'entités, espacées d'au moins 0,8·fov.
    360° : la direction de marche et son opposée sont favorisées (le long de la route)."""
    if cam.modele != "equirect":
        hf = math.degrees(2 * math.atan(cam.W / 2 / cam.f))
        return [(float(cam.pose[3]), float(cam.pose[4]), min(hf * 0.98, 85.0))]
    az, w = _poids(cam.C)
    cap = float(cam.pose[3])
    cand = np.arange(0, 360, 5.0)
    sc = []
    for a in cand:
        dd = np.abs(((az - a) + 180) % 360 - 180)
        s = w[dd < fov / 2 * 0.9].sum()
        dc = min(abs(((a - cap) + 180) % 360 - 180), abs(((a - cap - 180) + 180) % 360 - 180))
        s += 4.0 if dc < 10 else 0.0
        sc.append(s)
    sc = np.array(sc)
    choix = []
    for _ in range(n):
        o = np.argsort(-sc)
        for i in o:
            a = cand[i]
            if all(abs(((a - b) + 180) % 360 - 180) >= 0.8 * fov for b in choix):
                choix.append(float(a))
                break
    return [(a, tangage, fov) for a in choix]


# --------------------------------------------------------------------------- vues et mesures
def produire(id8, vues=None, n=4, taille=(1200, 900), dmax=60.0, mode="auto", prefixe=None, familles=None):
    ph = photo(id8)
    cam, src = pose_photo(id8, mode)
    if vues is None:
        vues = vues_auto(cam, n=n)
    PREUVES.mkdir(parents=True, exist_ok=True)
    img_src = image_rgb(ph.id8).astype(np.float32)
    produits = []
    for k, (lac, tg, fov) in enumerate(vues):
        if cam.modele == "equirect" or True:
            cv = camera_virtuelle(cam, lac, tg, fov, taille)
            arr = reechantillonner(cam, img_src, cv)
            im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        nom = f"{prefixe or ph.id8}_v{k}"
        im.save(PREUVES / f"{nom}_brut.jpg", quality=90)
        ov, vus = dessiner(im, cv, cam.C, dmax=dmax, familles=familles)
        dr = ImageDraw.Draw(ov)
        leg = (f"{ph.id8} {ph.datetime[:16]} {'360' if cam.modele == 'equirect' else 'plat'} | pose {src} | "
               f"vue {k}: lacet {lac:.0f} tangage {tg:.0f} fov {fov:.0f} | C=({cam.C[0]:.1f};{cam.C[1]:.1f})")
        bb = dr.textbbox((6, taille[1] - 22), leg, font=_police(15))
        dr.rectangle(bb, fill=(0, 0, 0))
        dr.text((6, taille[1] - 22), leg, fill=(255, 255, 255), font=_police(15))
        ov.save(PREUVES / f"{nom}.jpg", quality=88)
        meta = dict(photo=ph.id8, photo_id=ph.id, date=ph.datetime, modele=cam.modele, pose_source=src,
                    pose=[round(float(x), 4) for x in cam.pose], intrinseques=dict(f=cam.f, cx=cam.cx, cy=cam.cy, k1=cam.k1),
                    vue=dict(k=k, lacet=lac, tangage=tg, fov=fov, taille=list(taille)), entites=vus)
        with open(PREUVES / f"{nom}.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=0)
        produits.append(str(PREUVES / f"{nom}.jpg"))
        print(f"{nom}.jpg  lacet {lac:.0f}  {len(vus)} entités  pose {src}")
    return produits


def zoom_entite(id8, eid, fov=18.0, taille=(900, 900), mode="auto", frac=0.75, dz=None):
    """Vue serrée vers une entité ponctuelle (mobilier/arbre) : visée à frac·hauteur (ou pied + dz).
    Produit preuves/<id8>_z_<eid>_v0.jpg (+ _brut, .json) ; renvoie le chemin."""
    e = next(x for x in entites() if x["id"] == eid)
    cam, _ = pose_photo(id8, mode)
    pied, h, _t = e["mats"][0]
    P = pied + [0, 0, (dz if dz is not None else frac * h)]
    d = P - cam.C
    lac = math.degrees(math.atan2(d[0], d[1])) % 360
    tg = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return produire(id8, vues=[(lac, tg, fov)], taille=taille, mode=mode, prefixe=f"{photo(id8).id8}_z_{eid}")[0]


def zoom_point(id8, P, fov=18.0, taille=(900, 900), mode="auto", tag="pt"):
    """Vue serrée vers un point local P (x, y, z)."""
    cam, _ = pose_photo(id8, mode)
    d = np.asarray(P, float) - cam.C
    lac = math.degrees(math.atan2(d[0], d[1])) % 360
    tg = math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return produire(id8, vues=[(lac, tg, fov)], taille=taille, mode=mode, prefixe=f"{photo(id8).id8}_z_{tag}")[0]


def _cam_vue(id8, k, prefixe=None):
    m = _lire(PREUVES / f"{prefixe or id8}_v{k}.json")
    ph = photo(id8)
    intr = {**intrinseques(ph), **m["intrinseques"]}
    cam = camera(ph, m["pose"], intr)
    v = m["vue"]
    return camera_virtuelle(cam, v["lacet"], v["tangage"], v["fov"], tuple(v["taille"])), m


def rayon_vue(id8, k, uv, prefixe=None):
    cv, _ = _cam_vue(id8, k, prefixe)
    return cv.C.copy(), cv.rayons(np.asarray(uv, float)[None])[0]


def sol_vue(id8, k, uv, prefixe=None):
    """Point au sol (MNT 2026, local) vu au pixel uv de la vue k."""
    C, d = rayon_vue(id8, k, uv, prefixe)
    t = intersection_sol(C, d[None])[0]
    return None if not np.isfinite(t) else C + t * d


def trianguler_vues(obs):
    """obs = [(id8, k, (u, v)) ou (id8, k, (u, v), prefixe)] -> point le plus proche des rayons, résidus (m)."""
    C, D = [], []
    for o in obs:
        c, d = rayon_vue(o[0], o[1], o[2], o[3] if len(o) > 3 else None)
        C.append(c)
        D.append(d)
    A = np.zeros((3, 3))
    b = np.zeros(3)
    for c, d in zip(C, D):
        M = np.eye(3) - np.outer(d, d)
        A += M
        b += M @ c
    P = np.linalg.solve(A, b)
    res = [float(np.linalg.norm((np.eye(3) - np.outer(d, d)) @ (P - c))) for c, d in zip(C, D)]
    az = [math.degrees(math.atan2(d[0], d[1])) for d in D]
    ang = max(abs(((a - b_) + 180) % 360 - 180) for a in az for b_ in az)
    return dict(point=P.tolist(), residus_m=res, angle_max_deg=min(ang, 180 - ang) if ang > 90 else ang)


def verticale_vues(obs):
    """Axe vertical (x, y) depuis des pixels sur l'axe d'un mât (plans verticaux caméra-axe)."""
    N, b = [], []
    for o in obs:
        c, d = rayon_vue(o[0], o[1], o[2], o[3] if len(o) > 3 else None)
        n = np.cross(d, [0, 0, 1.0])[:2]
        n /= np.linalg.norm(n)
        N.append(n)
        b.append(n @ c[:2])
    X = np.linalg.lstsq(np.array(N), np.array(b), rcond=None)[0]
    res = (np.array(N) @ X - np.array(b)).tolist()
    return dict(xy=X.tolist(), residus_m=res)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("id8")
    ap.add_argument("--vues", help="'lacet,tangage,fov;...' (sinon choix automatique)")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--pose", default="auto")
    ap.add_argument("--dmax", type=float, default=60.0)
    ap.add_argument("--prefixe")
    ap.add_argument("--taille", default="1200x900")
    ap.add_argument("--zoom", help="id d'entité ponctuelle : vue serrée")
    ap.add_argument("--fov", type=float, default=18.0)
    a = ap.parse_args(argv)
    if a.zoom:
        print(zoom_entite(a.id8, a.zoom, fov=a.fov, mode=a.pose))
        return
    vues = None
    if a.vues:
        vues = [tuple(float(x) for x in v.split(",")) for v in a.vues.split(";")]
    taille = tuple(int(x) for x in a.taille.split("x"))
    produire(a.id8, vues=vues, n=a.n, taille=taille, dmax=a.dmax, mode=a.pose, prefixe=a.prefixe)


if __name__ == "__main__":
    main()


# --------------------------------------------------------------------------- planches de zooms
def planche_zooms(id8, cibles, nom=None, taille=400, n_col=3, mode="auto", fov=None, superposer=True):
    """Mosaïque de vues serrées (une tuile par cible). cibles : ids d'entités ponctuelles ou
    tuples ('tag', (x, y, z), hauteur_m). Tuile k : sidecar preuves/<nom>_v<k>.json (mesurable avec
    rayon_vue(id8, k, uv, prefixe=nom)). Pixel de mosaïque (X, Y) -> tuile k = (Y//taille)*n_col + X//taille."""
    ph = photo(id8)
    cam, src = pose_photo(id8, mode)
    nom = nom or f"{ph.id8}_P"
    img_src = image_rgb(ph.id8).astype(np.float32)
    E = {e["id"]: e for e in entites()}
    n = len(cibles)
    n_lig = int(math.ceil(n / n_col))
    mos = Image.new("RGB", (n_col * taille, n_lig * taille), (0, 0, 0))
    pol = _police(13)
    for k, c in enumerate(cibles):
        if isinstance(c, str):
            e = E[c]
            pied, h, tetes = e["mats"][0]
            tag = c
        else:
            tag, pied, h = c[0], np.asarray(c[1], float), float(c[2])
            e, tetes = None, []
        d = np.hypot(*(pied[:2] - cam.C[:2]))
        P = pied + [0, 0, 0.5 * h]
        v = P - cam.C
        lac = math.degrees(math.atan2(v[0], v[1])) % 360
        tg = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))
        f_ = fov or float(np.clip(1.7 * math.degrees(math.atan2(max(h, 1.5), max(d, 0.5))), 6.0, 70.0))
        cv = camera_virtuelle(cam, lac, tg, f_, (taille, taille))
        arr = reechantillonner(cam, img_src, cv)
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(im)
        if superposer:
            for pp, col in [(pied, (255, 60, 60))] + ([(E[c + '*']['mats'][0][0], (255, 0, 255))]
                                                     if isinstance(c, str) and c + '*' in E else []):
                Q = np.array([pp, pp + [0, 0, h]])
                uv, ok = _proj(cv, Q)
                if ok.all():
                    # trait discret décalé : ne masque pas l'objet
                    dr.line([(uv[0, 0], uv[0, 1]), (uv[0, 0], uv[0, 1] + 12)], fill=col, width=2)
                    dr.line([(uv[1, 0], uv[1, 1] - 12), (uv[1, 0], uv[1, 1])], fill=col, width=2)
                    dr.line([(uv[0, 0] - 8, uv[0, 1]), (uv[0, 0] + 8, uv[0, 1])], fill=col, width=2)
                    dr.line([(uv[1, 0] - 8, uv[1, 1]), (uv[1, 0] + 8, uv[1, 1])], fill=col, width=2)
            for ht in tetes:
                q, okq = _proj(cv, np.array([pied + [0, 0, ht]]))
                if okq[0]:
                    dr.line([(q[0, 0] + 10, q[0, 1]), (q[0, 0] + 18, q[0, 1])], fill=(255, 255, 0), width=2)
        for t in range(0, taille + 1, 25):   # graduations (tuile) : 25 px, longues tous les 100 px
            L = 10 if t % 100 == 0 else 4
            for a, b in (((t, 0), (t, L)), ((t, taille - 1), (t, taille - 1 - L)), ((0, t), (L, t)),
                         ((taille - 1, t), (taille - 1 - L, t))):
                dr.line([a, b], fill=(255, 255, 0), width=1)
        txt = f"{k}: {tag} d{d:.1f} h{h:.1f} fov{f_:.0f}"
        bb = dr.textbbox((3, 3), txt, font=pol)
        dr.rectangle(bb, fill=(0, 0, 0))
        dr.text((3, 3), txt, fill=(255, 255, 255), font=pol)
        mos.paste(im, ((k % n_col) * taille, (k // n_col) * taille))
        meta = dict(photo=ph.id8, photo_id=ph.id, date=ph.datetime, modele=cam.modele, pose_source=src,
                    pose=[round(float(x), 4) for x in cam.pose], intrinseques=dict(f=cam.f, cx=cam.cx, cy=cam.cy, k1=cam.k1),
                    vue=dict(k=k, lacet=lac, tangage=tg, fov=f_, taille=[taille, taille]), cible=tag, entites=[])
        with open(PREUVES / f"{nom}_v{k}.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
    out = PREUVES / f"{nom}.jpg"
    mos.save(out, quality=90)
    print(out, f"pose {src}")
    return str(out)


def tuile(X, Y, taille=400, n_col=3):
    """Pixel de mosaïque -> (k, (u, v)) dans la tuile."""
    k = int(Y // taille) * n_col + int(X // taille)
    return k, (X - (X // taille) * taille, Y - (Y // taille) * taille)


def sol_planche(id8, nom, X, Y, taille=400, n_col=3):
    """Point au sol (local) du pixel (X, Y) d'une planche de zooms."""
    k, uv = tuile(X, Y, taille, n_col)
    return sol_vue(id8, k, uv, prefixe=nom)


def azdist(id8, nom, k, uv, dist_h):
    """Point du rayon (pixel uv de la vue k) à la distance horizontale dist_h de la caméra (z au sol)."""
    C, d = rayon_vue(id8, k, uv, prefixe=nom)
    t = dist_h / max(1e-6, math.hypot(d[0], d[1]))
    P = C + t * d
    return np.array([P[0], P[1], z_sol(P[0], P[1])])


def ecart_lateral(id8, nom, k, uv, P_ref):
    """Décalage horizontal (m) entre le rayon du pixel et le point P_ref, perpendiculairement à la visée,
    et point corrigé (même distance que P_ref)."""
    C, d = rayon_vue(id8, k, uv, prefixe=nom)
    dh = np.array([d[0], d[1]]) / math.hypot(d[0], d[1])
    v = np.asarray(P_ref[:2], float) - C[:2]
    dist = float(v @ dh)
    lat = float(dh[0] * v[1] - dh[1] * v[0])
    Q = C[:2] + dist * dh
    return lat, np.array([Q[0], Q[1], z_sol(Q[0], Q[1])]), dist


def ortho_crop(xy, rayon_m=15.0, nom=None, marques=None, px=600, rayons=None):
    """Extrait de l'ortho PCRS 5 cm 2022 (RVB) centré sur xy local, avec les entités ponctuelles
    (mobilier rouge, arbres vert, corrections magenta) et des marques [(tag, (x, y), couleur)].
    rayons : [(id8, (x, y) caméra, azimut_deg)] tracés en jaune. Sauve preuves/ortho_<nom>.jpg."""
    from projection import ORTHO
    x0, y0 = xy[0] - rayon_m, xy[1] - rayon_m
    x1, y1 = xy[0] + rayon_m, xy[1] + rayon_m
    pas = 2 * rayon_m / px
    out = Image.new("RGB", (px, px))
    for t in sorted(ORTHO.glob("pcrs5cm_*.jpg")):
        tx, ty = int(t.stem.split("_")[1]) - O[0], int(t.stem.split("_")[2]) - O[1]
        if tx > x1 or tx + 50 < x0 or ty > y1 or ty + 50 < y0:
            continue
        im = Image.open(t).convert("RGB")
        # dalle : coin haut-gauche (tx, ty + 50), 0,05 m/px
        sc = 0.05 / pas
        im = im.resize((int(round(im.width * sc)), int(round(im.height * sc))))
        out.paste(im, (int(round((tx - x0) / pas)), int(round((y1 - (ty + 50)) / pas))))
    dr = ImageDraw.Draw(out)
    pol = _police(12)

    def P(x, y):
        return ((x - x0) / pas, (y1 - y) / pas)
    for e in entites():
        if e["fam"] not in ("mobilier", "arbre", "correction"):
            continue
        x, y = e["xy"]
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            continue
        col = {"mobilier": (255, 50, 50), "arbre": (60, 255, 60), "correction": (255, 0, 255)}[e["fam"]]
        u, v = P(x, y)
        dr.ellipse([u - 4, v - 4, u + 4, v + 4], outline=col, width=2)
        dr.text((u + 5, v - 6), e["id"].replace("arbre_", "a").replace("lamp_", "L")[:20], fill=col, font=pol)
    for tag, (x, y), col in (marques or []):
        u, v = P(x, y)
        dr.line([(u - 7, v), (u + 7, v)], fill=col, width=2)
        dr.line([(u, v - 7), (u, v + 7)], fill=col, width=2)
        dr.text((u + 6, v + 2), tag, fill=col, font=pol)
    for pid, (cx, cy), az in (rayons or []):
        a = math.radians(az)
        u0, v0 = P(cx, cy)
        u1, v1 = P(cx + 80 * math.sin(a), cy + 80 * math.cos(a))
        dr.line([(u0, v0), (u1, v1)], fill=(255, 255, 0), width=1)
    dr.text((4, px - 16), f"ortho PCRS 2022 | centre ({xy[0]:.1f};{xy[1]:.1f}) | {2 * rayon_m:.0f} m", fill=(255, 255, 0), font=pol)
    nom = nom or f"{xy[0]:.0f}_{xy[1]:.0f}"
    out.save(PREUVES / f"ortho_{nom}.jpg", quality=90)
    return str(PREUVES / f"ortho_{nom}.jpg")


def hauteur(id8, nom, k, uv, xy):
    """Hauteur au-dessus du sol (MNT 2026) du point de visée uv (vue k de `nom`) à l'aplomb de xy local
    (plan vertical perpendiculaire à la visée passant par xy)."""
    C, d = rayon_vue(id8, k, uv, prefixe=nom)
    dh = np.array([d[0], d[1]])
    n = np.linalg.norm(dh)
    v = np.asarray(xy[:2], float) - C[:2]
    t = (v @ dh) / (n * n)
    P = C + t * d
    return float(P[2] - z_sol(xy[0], xy[1]))


# --------------------------------------------------------------------------- calage manuel (relèvement)
def pixel_origine(id8, k, uv, prefixe=None):
    """Pixel d'une vue (découpe) -> pixel de la photo d'origine (indépendant de l'erreur de pose)."""
    m = _lire(PREUVES / f"{prefixe or id8}_v{k}.json")
    ph = photo(id8)
    intr = {**intrinseques(ph), **m["intrinseques"]}
    cam0 = camera(ph, m["pose"], intr)
    v = m["vue"]
    cv = camera_virtuelle(cam0, v["lacet"], v["tangage"], v["fov"], tuple(v["taille"]))
    d = cv.rayons(np.asarray(uv, float)[None])
    uv0, _ = cam0.cam_vers_pixel(d @ cam0.R.T)
    return uv0[0]


def releve(id8, points, pose0=None, sig_xy=4.0, sig_h=0.3, h0=None, iter=30, focale_libre=False):
    """Relèvement 6 ddl (x, y, z, lacet, tangage, roulis [+ f]) sur des points pointés à la main.
    points : [(P_local (3,), (k, (u, v), prefixe)), ...] ; P connu (pied/sommet de mât, coin de marquage).
    Moindres carrés sur les erreurs angulaires + a priori GNSS (sig_xy) et hauteur au-dessus du sol.
    Renvoie dict(pose, residus_deg, loo_deg, n)."""
    ph = photo(id8)
    intr = intrinseques(ph)
    if pose0 is None:
        cam0, _ = pose_photo(id8)
        pose0 = cam0.pose.copy()
    pose0 = np.asarray(pose0, float)
    h_ap = h0 if h0 is not None else float(pose0[2] - z_sol(pose0[0], pose0[1]))
    PX = np.array([np.asarray(p, float) for p, _ in points])
    UV = np.array([pixel_origine(id8, o[0], o[1], o[2] if len(o) > 2 else None) for _, o in points])

    def cam_de(q):
        it = dict(intr)
        if focale_libre:
            it["f"] = q[6]
        return camera(ph, q[:6], it)

    def residus(q, masque=None):
        c = cam_de(q)
        dobs = c.pixel_vers_cam(UV)
        dpre = c.monde_vers_cam(PX)
        dpre /= np.linalg.norm(dpre, axis=1, keepdims=True)
        # erreur angulaire en 2 composantes (plan tangent)
        e = np.cross(dobs, dpre)[:, [0, 2]] if False else (dpre - dobs)[:, :]
        r = e.ravel()
        if masque is not None:
            r = (e[masque]).ravel()
        pri = [(q[0] - pose0[0]) / sig_xy * 0.01, (q[1] - pose0[1]) / sig_xy * 0.01,
               (q[2] - z_sol(q[0], q[1]) - h_ap) / sig_h * 0.01]
        return np.r_[r, pri]

    def lm(q, masque=None):
        lam = 1e-3
        r = residus(q, masque)
        for _ in range(iter):
            J = np.zeros((len(r), len(q)))
            for j in range(len(q)):
                dq = np.zeros(len(q))
                dq[j] = 1e-4 if j < 3 else (1e-3 if j < 6 else 1.0)
                J[:, j] = (residus(q + dq, masque) - r) / dq[j]
            A = J.T @ J
            g = J.T @ r
            while True:
                step = -np.linalg.solve(A + lam * np.diag(np.diag(A) + 1e-12), g)
                qn = q + step
                rn = residus(qn, masque)
                if rn @ rn < r @ r:
                    q, r, lam = qn, rn, lam * 0.3
                    break
                lam *= 10
                if lam > 1e8:
                    return q
            if np.abs(step).max() < 1e-7:
                break
        return q

    q0 = pose0.copy() if not focale_libre else np.r_[pose0, intr["f"]]
    q = lm(q0)
    c = cam_de(q)

    def ang(cq, i):
        dobs = cq.pixel_vers_cam(UV[i:i + 1])[0]
        dpre = cq.monde_vers_cam(PX[i:i + 1])[0]
        return math.degrees(math.acos(np.clip(dobs @ dpre / np.linalg.norm(dpre), -1, 1)))
    res = [ang(c, i) for i in range(len(PX))]
    loo = []
    for i in range(len(PX)):
        m = np.ones(len(PX), bool)
        m[i] = False
        qi = lm(q.copy(), m)
        loo.append(ang(cam_de(qi), i))
    return dict(pose=q[:6].tolist(), f=float(q[6]) if focale_libre else None, residus_deg=res, loo_deg=loo,
                n=len(PX), uv_origine=UV.tolist())


def enregistrer_releve(id8, r, points_desc, seuil_deg=0.6):
    """Écrit poses_pano1/<id8>.json (format proche de poses.json) ; acceptée si n ≥ 5, résidu moyen
    ≤ seuil et validation croisée moyenne ≤ 2·seuil."""
    ph = photo(id8)
    ok = r["n"] >= 5 and np.mean(r["residus_deg"]) <= seuil_deg and np.mean(r["loo_deg"]) <= 2 * seuil_deg
    q = r["pose"]
    intr = intrinseques(ph)
    if r.get("f"):
        intr["f"] = r["f"]
    pb = pose_brute(ph)["pose"]
    rec = dict(id8=ph.id8, id=ph.id, date=ph.date, datetime=ph.datetime, modele=intr["modele"],
               intrinseques=dict(f=intr["f"], cx=intr["cx"], cy=intr["cy"], k1=intr.get("k1", 0.0), source=intr["source"]),
               pose_brute=dict(x=pb[0], y=pb[1], z=pb[2], lacet=pb[3], tangage=pb[4], roulis=pb[5]),
               pose=dict(x=q[0], y=q[1], z=q[2], lacet=q[3] % 360, tangage=q[4], roulis=q[5]),
               methode="relevement manuel (agent VISION-PANORAMAX-1) : points d'appui pointés visuellement",
               points=points_desc, qualite=dict(n=r["n"], residu_moy_deg=float(np.mean(r["residus_deg"])),
                                                residu_max_deg=float(np.max(r["residus_deg"])),
                                                loo_moy_deg=float(np.mean(r["loo_deg"])),
                                                decalage_gps_m=float(math.hypot(q[0] - pb[0], q[1] - pb[1]))),
               accepte=bool(ok), raison="ok" if ok else "résidus ou validation croisée insuffisants")
    POSES_AGENT.mkdir(exist_ok=True)
    with open(POSES_AGENT / f"{ph.id8}.json", "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1, default=float)
    return rec
