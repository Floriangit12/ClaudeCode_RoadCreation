"""overlay.py : superposition de la description v2 sur les dalles ortho PCRS 5 cm 2022.

Agent VISION-ORTHO-B (recensement visuel). Lit la description courante (base/*.geojson, y compris
une description sol plein site si elle existe), les bordures plein site de la cohérence, les objets
du paquet (mobilier, arbres), les corrections et propositions de la cohérence, les zones de travaux
2025, puis dessine le tout sur la dalle (géoréférencement .jgw, Lambert-93).

Repère : pixel continu (u, v) de la dalle, u vers l'est, v vers le sud ; le pixel (i, j) couvre
[i, i+1[ ; X = x_hg + u * 0,05 ; Y = y_hg - v * 0,05 (x_hg, y_hg = coin haut-gauche du pixel 0).
Local = L93 - O(917279.43, 6460289.98).

Usage (depuis n'importe où) :
  python overlay.py --tuiles 917300_6460250 917250_6460300   # vues entières + quadrants 2x
  python overlay.py --toutes                                  # les 24 dalles de l'agent B
  python overlay.py --zoom 917300_6460250 420 610 [--taille 250 --echelle 2 --brut] --sortie f.jpg
  python overlay.py --mosaique                                # aperçu 0,5 m/px de l'emprise B
API :
  from overlay import Dalle, rendre, px_vers_l93, l93_vers_px, legende
"""
import argparse
import json
import zlib
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[7]
O = (917279.43, 6460289.98)
ORTHO = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
OBJ = RACINE / "recon/out/paquet_jardin/package/donnees/objets"
DONNEES = RACINE / "recon/out/paquet_jardin/package/donnees"
ICI = Path(__file__).resolve().parent
PAS = 0.05

TUILES_B = ["917100_6460150", "917100_6460250", "917100_6460350", "917150_6460100", "917150_6460200",
            "917150_6460300", "917150_6460400", "917200_6460150", "917200_6460250", "917200_6460350",
            "917250_6460100", "917250_6460200", "917250_6460300", "917250_6460400", "917300_6460150",
            "917300_6460250", "917300_6460350", "917350_6460100", "917350_6460200", "917350_6460300",
            "917350_6460400", "917400_6460150", "917400_6460250", "917400_6460350"]

# ----------------------------------------------------------------------------- styles
PROFILS = {"A2": (255, 140, 0), "P1": (255, 0, 255), "T2": (255, 0, 0), "T2_bateau": (255, 255, 0),
           "T3": (170, 90, 40), "CS1": (0, 255, 128), "CS2": (0, 255, 128)}
SRC_BORD = {"gam": (0, 255, 255), "pcrs2019": (0, 150, 255), "plan2025": (255, 105, 180)}
CL_MARQ = {"ligne": (0, 110, 255), "fleche": (255, 30, 30), "symbole": (255, 0, 255),
           "passage": (255, 160, 0), "zone": (255, 255, 0), "transversale": (0, 255, 0),
           "fantome": (170, 170, 170)}
CL_SURF_V1 = {"chaussee": (200, 200, 200), "trottoir": (255, 215, 140), "espace_vert": (90, 230, 90),
              "parking": (140, 140, 255), "piste_cyclable": (255, 128, 0), "acces_riverain": (230, 230, 120),
              "batiment": (255, 80, 80), "terre_plein_vegetal": (40, 200, 120), "ilot": (0, 255, 0),
              "quai_bus": (0, 220, 255), "autre": (180, 120, 255)}
CL_MOB = {"lampadaire": (255, 255, 0), "panneau": (255, 40, 40), "support_feux": (0, 255, 0),
          "potelet": (255, 255, 255), "arbre": (0, 200, 0)}
ABREV = [("lamp_", "L"), ("potelet_", "pt"), ("arbre_", "a"), ("pan_", "P"), ("feu_", "F"),
         ("poteau_reseau_", "PR"), ("poteau_incendie_", "PI"), ("poteau_arret_", "PA"),
         ("stationnement_velos_", "SV"), ("corbeille_", "cb"), ("portail_", "por"), ("cloture_", "cl"),
         ("barriere_levante_", "BL"), ("mat_camera_", "cam"), ("panneau_information_", "PInf"),
         ("abri_bus_", "abri"), ("mobilier_publicitaire_", "pub"), ("distributeur_", "dist")]


def abrege(i):
    for a, b in ABREV:
        if i.startswith(a):
            r = i[len(a):]
            if r.isdigit() and len(r) > 5:
                r = r[-4:]
            return b + r
    return i if len(i) <= 16 else i[:16]


@lru_cache(None)
def police(t):
    for f in ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(f, t)
        except OSError:
            pass
    return ImageFont.load_default()


# ----------------------------------------------------------------------------- géoréférencement
class Dalle:
    def __init__(self, tuile):
        self.tuile = tuile
        self.jpg = ORTHO / f"pcrs5cm_{tuile}.jpg"
        a = [float(x) for x in (ORTHO / f"pcrs5cm_{tuile}.jgw").read_text().split()]
        self.pas_x, self.pas_y = a[0], a[3]
        self.x_hg = a[4] - a[0] / 2          # bord gauche du pixel 0
        self.y_hg = a[5] - a[3] / 2          # bord haut du pixel 0 (a[3] < 0)
        self._img = None

    @property
    def img(self):
        if self._img is None:
            self._img = Image.open(self.jpg).convert("RGB")
        return self._img

    def l93_vers_px(self, xy):
        xy = np.asarray(xy, float)
        return np.stack([(xy[..., 0] - self.x_hg) / self.pas_x, (xy[..., 1] - self.y_hg) / self.pas_y], -1)

    def px_vers_l93(self, uv):
        uv = np.asarray(uv, float)
        return np.stack([self.x_hg + uv[..., 0] * self.pas_x, self.y_hg + uv[..., 1] * self.pas_y], -1)

    def emprise(self):
        return (self.x_hg, self.y_hg + 1000 * self.pas_y, self.x_hg + 1000 * self.pas_x, self.y_hg)


def px_vers_l93(tuile, u, v):
    return [round(float(c), 3) for c in Dalle(tuile).px_vers_l93([u, v])]


def l93_vers_px(tuile, x, y):
    return [round(float(c), 2) for c in Dalle(tuile).l93_vers_px([x, y])]


# ----------------------------------------------------------------------------- données
def _lire(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as f:
        return json.load(f).get("features", [])


def _anneaux(g):
    """Liste de polylignes (np (N,2)) et indicateur polygone, quelle que soit la géométrie."""
    if not g:
        return [], False
    t, c = g["type"], g["coordinates"]
    if t == "Point":
        return [np.array([c[:2]])], False
    if t == "MultiPoint":
        return [np.array([p[:2]]) for p in c], False
    if t == "LineString":
        return [np.array(c)[:, :2]], False
    if t == "MultiLineString":
        return [np.array(l)[:, :2] for l in c], False
    if t == "Polygon":
        return [np.array(r)[:, :2] for r in c], True
    if t == "MultiPolygon":
        return [np.array(r)[:, :2] for p in c for r in p], True
    return [], False


def _sous_ligne(xy, s0, s1):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    s0, s1 = max(0, s0), min(d[-1], s1)
    if s1 <= s0:
        return None
    ss = np.r_[s0, d[(d > s0) & (d < s1)], s1]
    return np.stack([np.interp(ss, d, xy[:, 0]), np.interp(ss, d, xy[:, 1])], -1)


@lru_cache(None)
def charger():
    """Toutes les couches en L93 : liste de dicts {couche, id, anneaux, poly, style...}."""
    E = []

    def ajoute(couche, f, **kw):
        an, poly = _anneaux(f.get("geometry"))
        if not an:
            return
        p = f.get("properties", {})
        E.append(dict(couche=couche, id=p.get("id"), anneaux=an, poly=poly, props=p, **kw))

    # zones de travaux 2025 / chaussée 2026
    for f in _lire(DONNEES / "relief/relief_zones_2026.geojson"):
        z = f["properties"].get("zone")
        ajoute("zones", f, couleur=(200, 0, 255) if z != "chaussee_2026" else (255, 255, 255),
               tiret=True, ep=1, etiq=None)
    # surfaces v1 plein site (paquet)
    for f in _lire(DONNEES / "surfaces/surfaces_2026.geojson"):
        p = f["properties"]
        ajoute("surfaces_v1", f, couleur=CL_SURF_V1.get(p.get("classe"), (255, 255, 255)),
               tiret=p.get("etat") == "modifie_2025", ep=1,
               etiq=f"{p.get('id','')[5:]}:{(p.get('classe') or '')[:6]}/{(p.get('materiau') or '')[:5]}")
    # description v2 : couches sol (pilote et plein site si régénérées)
    base = DESC / "base"
    palette = {}
    for f in _lire(base / "surfaces.geojson"):
        p = f["properties"]
        if p.get("classe") == "emprise_bordure":
            continue
        m = (p.get("revetement") or {}).get("materiau_id") or "?"
        if m not in palette:
            h = zlib.crc32(m.encode()) % 360
            palette[m] = tuple(int(c) for c in np.array(_hsv(h / 360, 0.9, 1.0)) * 255)
        ajoute("surfaces", f, couleur=palette[m], ep=1, tiret=False, etiq=f"{p.get('id')}:{m[:12]}")
    for f in _lire(base / "ilots.geojson"):
        p = f["properties"]
        ajoute("ilots", f, couleur=(0, 255, 0), ep=3, tiret=False,
               etiq=f"{p.get('id')}:{(p.get('remplissage') or {}).get('materiau_id')}")
    v2_ids = set()
    for f in _lire(base / "bordures.geojson"):
        p = f["properties"]
        v2_ids.add(p.get("id"))
        xy = np.array(f["geometry"]["coordinates"])[:, :2]
        for iv in p.get("intervalles", []):
            seg = _sous_ligne(xy, iv["s0"], iv["s1"])
            if seg is not None:
                E.append(dict(couche="bordures", id=p["id"], anneaux=[seg], poly=False, props=p,
                              couleur=PROFILS.get(iv["profil"], (255, 255, 255)), ep=3, tiret=False,
                              etiq=f"{p['id']}:{iv['profil']}"))
        for ab in p.get("abaisses", []):
            seg = _sous_ligne(xy, ab["s0"], ab["s1"])
            if seg is not None:
                E.append(dict(couche="abaisses", id=ab["id"], anneaux=[seg], poly=False, props=ab,
                              couleur=(255, 255, 255), ep=1, tiret=True, etiq=None))
    for f in _lire(DESC / "coherence/carte/bordures_site.geojson"):
        p = f["properties"]
        if p.get("id") in v2_ids:
            continue
        src = p.get("source", "")
        ajoute("bordures_site", f, couleur=SRC_BORD.get(src, (210, 210, 210)), ep=2,
               tiret=bool(p.get("zone_travaux_2025")), etiq=None)
    for f in _lire(base / "ponctuels_sol.geojson"):
        ajoute("ponctuels_sol", f, couleur=(170, 40, 255), ep=2, tiret=False, etiq=f["properties"].get("id"))
    for f in _lire(base / "marquages.geojson"):
        p = f["properties"]
        cl = p.get("classe")
        col = CL_MARQ.get(cl, (255, 255, 255))
        if cl == "ligne" and p.get("type") == "discontinue":
            col = (0, 210, 255)
        ajoute("marquages", f, couleur=col, ep=1, tiret=p.get("etat") in ("neuf_2025", "fantome"),
               etiq=p.get("id") if cl in ("fleche", "symbole", "passage", "zone", "transversale") else None)
    # objets
    for f in _lire(OBJ / "mobilier.geojson"):
        p = f["properties"]
        t = p.get("type")
        ajoute("mobilier", f, couleur=CL_MOB.get(t, (0, 255, 255)) if t != "cloture" else (190, 110, 40),
               ep=2, tiret=t == "cloture", etiq=abrege(p.get("id", "")))
    for f in _lire(OBJ / "arbres.geojson"):
        p = f["properties"]
        ajoute("arbres", f, couleur=(0, 230, 0) if p.get("instancier", True) else (230, 120, 0), ep=1,
               tiret=False, etiq=abrege(p.get("id", "")), rayon_m=(p.get("diametre_couronne_m") or 0) / 2)
    # cohérence : corrections (flèches) et propositions
    for f in _lire(DESC / "coherence/corrections.geojson"):
        p = f["properties"]
        a, b = p.get("p_source_local"), p.get("p_resolu_local")
        if a and b:
            seg = np.array([[a[0] + O[0], a[1] + O[1]], [b[0] + O[0], b[1] + O[1]]])
            E.append(dict(couche="corrections", id=p.get("id"), anneaux=[seg], poly=False, props=p,
                          couleur=(255, 60, 60), ep=2, tiret=False, fleche=True,
                          etiq=f"C:{abrege(p.get('id',''))}"))
    for f in _lire(DESC / "coherence/propositions_ajouts.geojson"):
        p = f["properties"]
        ajoute("ajouts", f, couleur=(255, 255, 255), ep=1, tiret=True, etiq=f"+{p.get('id','')[:18]}")
    for e in E:
        allxy = np.vstack(e["anneaux"])
        r = e.get("rayon_m", 0) or 0
        e["bbox"] = (allxy[:, 0].min() - r, allxy[:, 1].min() - r, allxy[:, 0].max() + r, allxy[:, 1].max() + r)
    return E


def _hsv(h, s, v):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)][i]


COUCHES_DEFAUT = ("zones", "surfaces", "ilots", "bordures", "abaisses",
                  "ponctuels_sol", "marquages", "mobilier", "arbres", "corrections", "ajouts")


# ----------------------------------------------------------------------------- dessin
def _tirets(dr, pts, col, ep, pas=8):
    for a, b in zip(pts[:-1], pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / pas))
        for k in range(0, n, 2):
            t0, t1 = k / n, min(1, (k + 1) / n)
            dr.line([(a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0),
                     (a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1)], fill=col, width=ep)


def _texte(dr, xy, t, col, taille):
    f = police(taille)
    x, y = xy
    bb = dr.textbbox((x, y), t, font=f)
    dr.rectangle([bb[0] - 1, bb[1] - 1, bb[2] + 1, bb[3] + 1], fill=(0, 0, 0, 150))
    dr.text((x, y), t, font=f, fill=col + (255,))


def rendre(tuile, u0=0, v0=0, w=1000, h=1000, echelle=1.0, couches=COUCHES_DEFAUT, brut=False,
           grille=True, etiquettes=True, titre=True):
    """Découpe [u0, u0+w[ x [v0, v0+h[ de la dalle, agrandie `echelle` fois, avec la description.
    Renvoie (image PIL, liste des entités dessinées avec leurs pixels de dalle)."""
    D = Dalle(tuile)
    W, H = int(round(w * echelle)), int(round(h * echelle))
    base = D.img.crop((u0, v0, u0 + w, v0 + h)).resize((W, H), Image.BICUBIC if echelle > 1 else Image.LANCZOS)
    M = 44 if grille else 0
    T = 18 if titre else 0
    can = Image.new("RGB", (W + M, H + M + T), (30, 30, 30))
    can.paste(base, (M, M + T))
    dessin = []
    if not brut:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        x0, y0, x1, y1 = D.emprise()
        X0, Y1 = D.x_hg + u0 * PAS, D.y_hg - v0 * PAS
        X1, Y0 = X0 + w * PAS, Y1 - h * PAS
        tl = 11 if echelle <= 1 else 12

        def px(xy):
            uv = D.l93_vers_px(xy)
            return [((a - u0) * echelle, (b - v0) * echelle) for a, b in uv]
        for e in charger():
            if e["couche"] not in couches:
                continue
            bx = e["bbox"]
            if bx[2] < X0 - 1 or bx[0] > X1 + 1 or bx[3] < Y0 - 1 or bx[1] > Y1 + 1:
                continue
            col = e["couleur"] + (255,)
            ep = max(1, int(round(e["ep"] * (1 if echelle <= 1 else echelle / 1.5))))
            for an in e["anneaux"]:
                P = px(an)
                if len(P) == 1:
                    cx, cy = P[0]
                    r = 3 * max(1, echelle) if e["couche"] != "arbres" else 2.5 * max(1, echelle)
                    if e["couche"] == "arbres" and e.get("rayon_m"):
                        rr = e["rayon_m"] / PAS * echelle
                        dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(0, 140, 0, 160), width=1)
                    dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2)
                    dr.line([cx - 1, cy, cx + 1, cy], fill=(0, 0, 0, 255))
                    if etiquettes and e.get("etiq"):
                        _texte(dr, (cx + r + 1, cy - r - 2), e["etiq"], e["couleur"], tl)
                else:
                    if e.get("tiret"):
                        _tirets(dr, P, col, ep, pas=6 * max(1, echelle))
                    else:
                        dr.line(P, fill=col, width=ep, joint="curve")
                    if e.get("fleche"):
                        (ax, ay), (bx2, by2) = P[0], P[-1]
                        ang = math.atan2(by2 - ay, bx2 - ax)
                        for da in (2.6, -2.6):
                            dr.line([(bx2, by2), (bx2 + 8 * math.cos(ang + da), by2 + 8 * math.sin(ang + da))],
                                    fill=col, width=2)
                        dr.ellipse([ax - 3, ay - 3, ax + 3, ay + 3], outline=col, width=1)
            if etiquettes and e.get("etiq") and len(e["anneaux"][0]) > 1 and (echelle > 1 or e["couche"] in (
                    "marquages", "corrections", "ilots", "mobilier")):
                pts = np.vstack(e["anneaux"])
                c = pts.mean(0) if e["poly"] else pts[len(pts) // 2]
                (cx, cy), = px(c[None])
                if 0 <= cx <= W and 0 <= cy <= H:
                    _texte(dr, (cx + 2, cy + 2), e["etiq"], e["couleur"], tl - 1)
            uv = D.l93_vers_px(np.vstack(e["anneaux"]).mean(0))
            dessin.append(dict(couche=e["couche"], id=e["id"], etiq=e.get("etiq"),
                               uv=[round(float(uv[0]), 1), round(float(uv[1]), 1)]))
        fond = can.crop((M, M + T, M + W, M + T + H)).convert("RGBA")
        can.paste(Image.alpha_composite(fond, ov).convert("RGB"), (M, M + T))
    dr = ImageDraw.Draw(can)
    if grille:
        f = police(11)
        pas = 50 if w > 120 else 10
        for k in range(int(math.ceil(u0 / pas)) * pas, u0 + w + 1, pas):
            x = (k - u0) * echelle + M
            dr.line([x, M + T - 6, x, M + T], fill=(255, 255, 255), width=1)
            dr.line([x, M + T + H, x, M + T + H + 4], fill=(255, 255, 255), width=1)
            dr.text((x - 10, M + T - 18), str(k), font=f, fill=(255, 255, 255))
            for y in range(M + T, M + T + H, 6):
                can.putpixel((int(min(x, W + M - 1)), y), (255, 255, 255)) if (y // 6) % 4 == 0 else None
        for k in range(int(math.ceil(v0 / pas)) * pas, v0 + h + 1, pas):
            y = (k - v0) * echelle + M + T
            dr.line([M - 6, y, M, y], fill=(255, 255, 255), width=1)
            dr.text((2, y - 6), str(k), font=f, fill=(255, 255, 255))
            for x in range(M, M + W, 6):
                can.putpixel((x, int(min(y, H + M + T - 1))), (255, 255, 255)) if (x // 6) % 4 == 0 else None
    if titre:
        xa, ya = D.px_vers_l93([u0, v0])
        dr.text((4, 2), f"{tuile}  u{u0}-{u0 + w} v{v0}-{v0 + h}  x{echelle:g}  HG L93 {xa:.2f} {ya:.2f}  "
                        f"(ortho 2022-05-10){'  BRUT' if brut else ''}", font=police(12), fill=(255, 255, 0))
    return can, dessin


def legende(tuile, couches=COUCHES_DEFAUT):
    """Entités de la description présentes sur la dalle, avec pixel (u, v) du centroïde."""
    return rendre(tuile, couches=couches, grille=False, titre=False)[1]


def sorties_dalle(tuile, dossier=ICI / "vues"):
    dossier.mkdir(parents=True, exist_ok=True)
    im, ent = rendre(tuile)
    im.save(dossier / f"{tuile}_ov.jpg", quality=90)
    with open(dossier / f"{tuile}_entites.json", "w", encoding="utf-8") as f:
        json.dump(ent, f, ensure_ascii=False, indent=0)
    for r in (0, 1):
        for c in (0, 1):
            for b in (False, True):
                im, _ = rendre(tuile, 500 * c, 500 * r, 500, 500, 2.0, brut=b)
                im.save(dossier / f"{tuile}_q{r}{c}_{'brut' if b else 'ov'}.jpg", quality=88)
    return ent


def mosaique(sortie=ICI / "vues/mosaique_B.jpg", res=0.5):
    xs = sorted({int(t.split("_")[0]) for t in TUILES_B})
    ys = sorted({int(t.split("_")[1]) for t in TUILES_B})
    x0, x1, y0, y1 = xs[0], xs[-1] + 50, ys[0], ys[-1] + 50
    n = int(50 / res)
    can = Image.new("RGB", (int((x1 - x0) / res), int((y1 - y0) / res)), (0, 0, 0))
    dr = ImageDraw.Draw(can)
    for t in TUILES_B:
        D = Dalle(t)
        x, y = int(t.split("_")[0]), int(t.split("_")[1])
        can.paste(D.img.resize((n, n), Image.LANCZOS), (int((x - x0) / res), int((y1 - y - 50) / res)))
        dr.rectangle([int((x - x0) / res), int((y1 - y - 50) / res), int((x - x0) / res) + n - 1,
                      int((y1 - y - 50) / res) + n - 1], outline=(255, 255, 0))
        dr.text((int((x - x0) / res) + 3, int((y1 - y - 50) / res) + 3), t, font=police(11), fill=(255, 255, 0))
    for e in charger():
        if e["couche"] not in ("bordures", "bordures_site", "marquages", "ilots"):
            continue
        for an in e["anneaux"]:
            P = [((a - x0) / res, (y1 - b) / res) for a, b in an]
            if len(P) > 1:
                dr.line(P, fill=e["couleur"], width=1)
    can.save(sortie, quality=90)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuiles", nargs="*", default=[])
    ap.add_argument("--toutes", action="store_true")
    ap.add_argument("--zoom", nargs=3)
    ap.add_argument("--taille", type=int, default=250)
    ap.add_argument("--echelle", type=float, default=2.0)
    ap.add_argument("--brut", action="store_true")
    ap.add_argument("--sortie")
    ap.add_argument("--mosaique", action="store_true")
    a = ap.parse_args()
    if a.mosaique:
        (ICI / "vues").mkdir(parents=True, exist_ok=True)
        mosaique()
    for t in (TUILES_B if a.toutes else a.tuiles):
        n = len(sorties_dalle(t))
        print(t, n, "entités")
    if a.zoom:
        t, u, v = a.zoom[0], int(a.zoom[1]), int(a.zoom[2])
        s = a.taille
        im, _ = rendre(t, max(0, u - s // 2), max(0, v - s // 2), s, s, a.echelle, brut=a.brut)
        im.save(a.sortie or (ICI / f"preuves/{t}_{u}_{v}{'_brut' if a.brut else ''}.jpg"), quality=90)
