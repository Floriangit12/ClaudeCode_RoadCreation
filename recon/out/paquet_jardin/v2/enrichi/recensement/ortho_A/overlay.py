#!/usr/bin/env python
"""Superposition de la description v2 sur l'ortho PCRS 5 cm du 10/05/2022 (agent VISION-ORTHO-A).

Lit tout ce qui existe de la description (base/*.geojson, cohérence, objets du paquet, carte des
bordures du site) et le dessine, géoréférencé par les .jgw, sur l'ortho (mosaïque à la volée : une
découpe peut chevaucher plusieurs dalles de 50 m). numpy + Pillow seulement.

Usage (depuis n'importe où) :
  python overlay.py tuile 917250_6460250 [...]   -> overlays/<tuile>_overlay.jpg (1000 px, 5 cm/px)
  python overlay.py toutes                          -> les 25 dalles de la liste A
  python overlay.py decoupe X0 Y0 [--cote 12.5] [--zoom 2] [--brut] [--sortie f.jpg] [--marques "x,y;x,y"]
        X0 Y0 : coin bas-gauche L93 ; cote en m (12,5 m = 250 px à 5 cm) ; zoom 2 -> 40 px/m.
        Graduations L93 tous les 1 m (étiquette tous les 5 m) ; --brut : sans couches.
  python overlay.py px2l93 <tuile> u v              -> L93 du pixel (u, v) continu de la dalle
  python overlay.py l932px <tuile> x y
  python overlay.py travaux x y                     -> état de la zone travaux 2025 au point

Repère pixel : pixel (i, j) = [i, i+1[ ; x = X_gauche + u·0,05 ; y = Y_haut − v·0,05 (jgw = centre
du pixel haut-gauche). Local = L93 − O(917279.43, 6460289.98).
"""
import argparse
import colorsys
import hashlib
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[7]
ORTHO = RACINE / "data/sites/paquet_jardin/ortho5cm_2022"
DESC = RACINE / "recon/out/paquet_jardin/v2/description"
OBJETS = RACINE / "recon/out/paquet_jardin/package/donnees/objets"
DONNEES = RACINE / "recon/out/paquet_jardin/package/donnees"
GAM26 = RACINE / "data/sites/paquet_jardin/etat_2026"
ICI = Path(__file__).resolve().parent
O = (917279.43, 6460289.98)
PAS = 0.05
DATE_ORTHO = "2022-05-10"

TUILES_A = ["917100_6460100", "917100_6460200", "917100_6460300", "917100_6460400", "917150_6460150",
            "917150_6460250", "917150_6460350", "917200_6460100", "917200_6460200", "917200_6460300",
            "917200_6460400", "917250_6460150", "917250_6460250", "917250_6460350", "917300_6460100",
            "917300_6460200", "917300_6460300", "917300_6460400", "917350_6460150", "917350_6460250",
            "917350_6460350", "917400_6460100", "917400_6460200", "917400_6460300", "917400_6460400"]

PROFILS = {"A2": (0, 229, 255), "P1": (255, 212, 0), "T2": (255, 59, 48), "T2_bateau": (255, 149, 0),
           "T3": (255, 45, 212), "T1": (180, 120, 255), "CS1": (90, 160, 255), "CS2": (90, 160, 255)}
SRC_BORD = {"gam": (245, 245, 245), "pcrs2019": (120, 200, 255), "plan2025": (255, 160, 40)}
CL_MARQ = {"ligne": (124, 252, 0), "fantome": (255, 0, 255), "passage": (0, 191, 255), "fleche": (255, 64, 64),
           "symbole": (255, 255, 0), "zone": (255, 165, 0), "transversale": (65, 105, 255)}
MOB = {"lampadaire": ((255, 230, 0), "o"), "support_feux": ((255, 40, 40), "s"), "panneau": ((40, 120, 255), "t"),
       "potelet": ((255, 255, 255), "."), "balise_J11": ((255, 255, 255), "."), "poteau_reseau": ((200, 140, 60), "o"),
       "mat_camera": ((255, 230, 0), "s"), "abri_bus": ((0, 255, 255), "s"), "poteau_arret": ((0, 255, 255), "o")}


def _police(t):
    for nom in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, t)
        except OSError:
            pass
    return ImageFont.load_default()


def _lire(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _feats(p):
    p = Path(p)
    return _lire(p)["features"] if p.exists() else []


def couleur_hash(s):
    h = int(hashlib.md5(str(s).encode()).hexdigest()[:6], 16) / 0xFFFFFF
    r, g, b = colorsys.hsv_to_rgb(h, 0.85, 1.0)
    return int(r * 255), int(g * 255), int(b * 255)


# --------------------------------------------------------------------------- ortho
def jgw(tuile):
    a = [float(v) for v in (ORTHO / f"pcrs5cm_{tuile}.jgw").read_text().split()]
    return {"A": a[0], "E": a[3], "x_g": a[4] - a[0] / 2, "y_h": a[5] - a[3] / 2}


def px2l93(tuile, u, v):
    g = jgw(tuile)
    return g["x_g"] + u * g["A"], g["y_h"] + v * g["E"]


def l932px(tuile, x, y):
    g = jgw(tuile)
    return (x - g["x_g"]) / g["A"], (y - g["y_h"]) / g["E"]


@lru_cache(maxsize=16)
def _dalle(tuile):
    p = ORTHO / f"pcrs5cm_{tuile}.jpg"
    return np.asarray(Image.open(p).convert("RGB")) if p.exists() else None


def mosaique(x0, y0, x1, y1):
    """Image RGB 5 cm de la boîte L93 [x0, x1] x [y0, y1] (bords arrondis au pixel)."""
    c0, c1 = int(math.floor(x0 / PAS + 1e-6)), int(math.ceil(x1 / PAS - 1e-6))
    r0, r1 = int(math.floor(y0 / PAS + 1e-6)), int(math.ceil(y1 / PAS - 1e-6))
    W, H = c1 - c0, r1 - r0
    out = np.zeros((H, W, 3), np.uint8)
    for tx in range(int(x0 // 50) * 50, int(math.ceil(x1 / 50)) * 50, 50):
        for ty in range(int(y0 // 50) * 50, int(math.ceil(y1 / 50)) * 50, 50):
            d = _dalle(f"{tx}_{ty}")
            if d is None:
                continue
            # colonnes globales de la dalle : tx/PAS .. +1000 ; lignes (du haut) : (ty+50)/PAS
            gx0, gy_h = round(tx / PAS), round((ty + 50) / PAS)
            a0, a1 = max(c0, gx0), min(c1, gx0 + 1000)
            # ligne globale "du haut" : top = r1 (y1) ; ligne r (du haut) = r1 - 1 - k
            b0, b1 = max(r0, gy_h - 1000), min(r1, gy_h)
            if a0 >= a1 or b0 >= b1:
                continue
            out[r1 - b1:r1 - b0, a0 - c0:a1 - c0] = d[gy_h - b1:gy_h - b0, a0 - gx0:a1 - gx0]
    return out, (c0 * PAS, r1 * PAS)


# --------------------------------------------------------------------------- couches
@lru_cache(maxsize=1)
def couches():
    C = {}
    base = DESC / "base"
    C["bordures"] = _feats(base / "bordures.geojson")
    C["surfaces"] = _feats(base / "surfaces.geojson")
    C["ilots"] = _feats(base / "ilots.geojson")
    C["ponctuels"] = _feats(base / "ponctuels_sol.geojson")
    C["marquages"] = _feats(base / "marquages.geojson")
    # schéma ≥ 0.3 : les fantômes (marques 2022 effacées en 2025) ne sont plus dans marquages.geojson ;
    # on les reprend des indices v1 pour la lecture de l'ortho 2022 (dessinés en magenta, non décrits)
    if not any(f["properties"].get("classe") == "fantome" for f in C["marquages"]):
        C["marquages"] = C["marquages"] + [f for f in _feats(base / "marquages_indices_v1.geojson")
                                           if f["properties"].get("classe") == "fantome"]
    # familles du sol « site entier » si l'atelier concurrent les a déjà écrites (lues telles quelles)
    for nom in ("vegetation", "signaux", "mobilier"):
        C["desc_" + nom] = _feats(base / f"{nom}.geojson")
    ids_v2 = {f["properties"]["id"] for f in C["bordures"]}
    C["bordures_site"] = [f for f in _feats(DESC / "coherence/carte/bordures_site.geojson")
                          if f["properties"]["id"] not in ids_v2]
    C["surfaces_v1"] = _feats(DONNEES / "surfaces/surfaces_2026.geojson")
    C["mobilier"] = _feats(OBJETS / "mobilier.geojson")
    C["arbres"] = _feats(OBJETS / "arbres.geojson")
    C["corrections"] = _feats(DESC / "coherence/corrections.geojson")
    C["ajouts"] = _feats(DESC / "coherence/propositions_ajouts.geojson")
    C["caniveaux_gam"] = _feats(GAM26 / "caniveau_lin_L93.geojson")
    return C


@lru_cache(maxsize=1)
def zone_pilote_bbox():
    try:
        d = _lire(DESC / "description_scene_v2.json")["zone_pilote"]["emprise_l93"]
        return d["x_min"], d["y_min"], d["x_max"], d["y_max"]
    except Exception:
        return None


# --------------------------------------------------------------------------- zone de travaux 2025
TRAV_PAS = 0.1
TRAV_X0, TRAV_Y0, TRAV_N = 917050.0, 6460050.0, 4500     # 450 m x 450 m à 10 cm


@lru_cache(maxsize=1)
def masque_travaux():
    """uint8 bits : 1 surface modifiée 2025 (surfaces_2026 etat) ; 2 zone relief rehaussée / abaissée 2025 ;
    4 bordure modifiée 2025 (± 1,0 m) ; 8 marquage neuf 2025 (± 0,5 m) ; 16 marquage refait identique 2025."""
    im = {b: Image.new("L", (TRAV_N, TRAV_N), 0) for b in (1, 2, 4, 8, 16)}
    dr = {b: ImageDraw.Draw(im[b]) for b in im}

    def P(x, y):
        return ((x - TRAV_X0) / TRAV_PAS, (TRAV_Y0 + TRAV_N * TRAV_PAS - y) / TRAV_PAS)

    def poly(d, coords):
        for k, ring in enumerate(coords):
            d.polygon([P(c[0], c[1]) for c in ring], fill=255 if k == 0 else 0)

    for f in _feats(DONNEES / "surfaces/surfaces_2026.geojson"):
        if f["properties"].get("etat") == "modifie_2025":
            poly(dr[1], f["geometry"]["coordinates"])
    for f in _feats(DONNEES / "relief/relief_zones_2026.geojson"):
        z = f["properties"].get("zone", "")
        if z in ("ancienne_chaussee_rehaussee_2025", "traversee_bordure_abaissee", "ancienne_chaussee_trottoir_par_defaut"):
            g = f["geometry"]
            for pc in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
                poly(dr[2], pc)
    for f in _feats(DESC / "coherence/carte/bordures_site.geojson"):
        p = f["properties"]
        if p.get("modifiee_2025") or p.get("zone_travaux_2025"):
            dr[4].line([P(c[0], c[1]) for c in f["geometry"]["coordinates"]], fill=255, width=int(2.0 / TRAV_PAS))
    for f in _feats(DONNEES / "marquages/marquages_2026.geojson"):
        p = f["properties"]
        b = 8 if p.get("etat") == "neuf_2025" else (16 if p.get("etat") == "refait_2025_identique" else 0)
        if not b:
            continue
        g = f["geometry"]
        for pc in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            ring = [P(c[0], c[1]) for c in pc[0]]
            dr[b].polygon(ring, fill=255)
            dr[b].line(ring + [ring[0]], fill=255, width=int(1.0 / TRAV_PAS))
    m = np.zeros((TRAV_N, TRAV_N), np.uint8)
    for b, i in im.items():
        m |= (np.asarray(i) > 0).astype(np.uint8) * b
    return m


def etat_travaux(x, y, r=0.0):
    """Bits de la zone de travaux au point (OU sur un disque de rayon r)."""
    m = masque_travaux()
    c, l = int((x - TRAV_X0) / TRAV_PAS), int((TRAV_Y0 + TRAV_N * TRAV_PAS - y) / TRAV_PAS)
    k = int(math.ceil(r / TRAV_PAS))
    w = m[max(0, l - k):l + k + 1, max(0, c - k):c + k + 1]
    return int(np.bitwise_or.reduce(w.ravel())) if w.size else 0


def libelle_travaux(bits):
    t = []
    if bits & 1: t.append("surface modifiée 2025")
    if bits & 2: t.append("zone rehaussée/abaissée 2025")
    if bits & 4: t.append("bordure modifiée 2025")
    if bits & 8: t.append("marquage neuf 2025")
    if bits & 16: t.append("marquage refait identique 2025")
    return ", ".join(t) or "hors zone de travaux 2025"


# --------------------------------------------------------------------------- rendu
class Rendu:
    def __init__(self, x0, y0, x1, y1, ppm=20.0, brut=False, travaux=True):
        img, (xg, yh) = mosaique(x0, y0, x1, y1)
        self.xg, self.yh, self.ppm = xg, yh, ppm
        H, W = img.shape[:2]
        z = ppm * PAS
        self.im = Image.fromarray(img)
        if abs(z - 1) > 1e-6:
            self.im = self.im.resize((round(W * z), round(H * z)), Image.BICUBIC)
        self.bbox = (xg, yh - H * PAS, xg + W * PAS, yh)
        self.brut = brut
        if not brut and travaux:
            self._travaux()
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.f = _police(max(10, int(11 * ppm / 20)))
        self.fp = _police(max(9, int(9 * ppm / 20)))

    def P(self, x, y):
        return ((x - self.xg) * self.ppm, (self.yh - y) * self.ppm)

    def dedans(self, x, y, marge=2.0):
        a, b, c, d = self.bbox
        return a - marge <= x <= c + marge and b - marge <= y <= d + marge

    def _travaux(self):
        m = masque_travaux()
        a, b, c, d = self.bbox
        c0, c1 = int((a - TRAV_X0) / TRAV_PAS), int(math.ceil((c - TRAV_X0) / TRAV_PAS))
        l0, l1 = int((TRAV_Y0 + TRAV_N * TRAV_PAS - d) / TRAV_PAS), int(math.ceil((TRAV_Y0 + TRAV_N * TRAV_PAS - b) / TRAV_PAS))
        sub = m[max(l0, 0):l1, max(c0, 0):c1]
        if not sub.any():
            return
        msk = Image.fromarray(((sub & (1 | 2 | 4)) > 0).astype(np.uint8) * 255).resize(self.im.size, Image.NEAREST)
        hach = Image.new("RGBA", self.im.size, (0, 0, 0, 0))
        dh = ImageDraw.Draw(hach)
        W, H = self.im.size
        pas = max(14, int(self.ppm * 0.9))
        for k in range(-H, W, pas):
            dh.line([(k, H), (k + H, 0)], fill=(255, 0, 200, 70), width=1)
        self.im = self.im.convert("RGBA")
        self.im.paste(hach, (0, 0), Image.fromarray(np.minimum(np.asarray(msk), np.asarray(hach)[:, :, 3])))
        self.im = self.im.convert("RGB")

    # primitives -------------------------------------------------------------
    def ligne(self, coords, col, w=1, alpha=255):
        pts = [self.P(c[0], c[1]) for c in coords]
        if len(pts) >= 2:
            self.d.line(pts, fill=col + (alpha,), width=w)

    def anneaux(self, g):
        if g is None:
            return []
        t = g["type"]
        if t == "Polygon":
            return g["coordinates"]
        if t == "MultiPolygon":
            return [r for p in g["coordinates"] for r in p]
        if t == "LineString":
            return [g["coordinates"]]
        if t == "MultiLineString":
            return g["coordinates"]
        return []

    def texte(self, x, y, s, col, petit=False):
        X, Y = self.P(x, y)
        f = self.fp if petit else self.f
        self.d.text((X + 3, Y - 3), s, fill=col + (255,), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))

    def fleche(self, a, b, col, w=2):
        A, B = self.P(*a), self.P(*b)
        self.d.line([A, B], fill=col + (255,), width=w)
        ang = math.atan2(B[1] - A[1], B[0] - A[0])
        L = 7 * self.ppm / 20 + 4
        for s in (-0.45, 0.45):
            self.d.line([B, (B[0] - L * math.cos(ang + s), B[1] - L * math.sin(ang + s))], fill=col + (255,), width=w)

    def marqueur(self, x, y, col, forme="o", r=None):
        X, Y = self.P(x, y)
        r = r or max(3, self.ppm * 0.18)
        if forme == "o":
            self.d.ellipse([X - r, Y - r, X + r, Y + r], outline=col + (255,), width=2)
        elif forme == "s":
            self.d.rectangle([X - r, Y - r, X + r, Y + r], outline=col + (255,), width=2)
        elif forme == "t":
            self.d.polygon([(X, Y - r), (X - r, Y + r), (X + r, Y + r)], outline=col + (255,))
        elif forme == "x":
            self.d.line([(X - r, Y - r), (X + r, Y + r)], fill=col + (255,), width=2)
            self.d.line([(X - r, Y + r), (X + r, Y - r)], fill=col + (255,), width=2)
        elif forme == "+":
            self.d.line([(X - r, Y), (X + r, Y)], fill=col + (255,), width=1)
            self.d.line([(X, Y - r), (X, Y + r)], fill=col + (255,), width=1)
        else:
            self.d.ellipse([X - 2, Y - 2, X + 2, Y + 2], fill=col + (255,))

    # couches ----------------------------------------------------------------
    def _proche(self, g):
        for r in self.anneaux(g):
            for c in r[:: max(1, len(r) // 20)] + [r[-1]]:
                if self.dedans(c[0], c[1], 10):
                    return True
        if g and g["type"] == "Point":
            return self.dedans(*g["coordinates"][:2], 5)
        return False

    def dessiner(self, etiquettes=True):
        if self.brut:
            return self
        C = couches()
        zp = zone_pilote_bbox()
        # surfaces v1 hors zone pilote (fines)
        for f in C["surfaces_v1"]:
            if not self._proche(f["geometry"]):
                continue
            p = f["properties"]
            col = couleur_hash(p.get("materiau"))
            for r in self.anneaux(f["geometry"]):
                self.ligne(r, col, 1, 110)
        # surfaces v2 (matériau)
        for f in C["surfaces"]:
            if not self._proche(f["geometry"]):
                continue
            p = f["properties"]
            mid = (p.get("revetement") or {}).get("materiau_id", "?")
            col = couleur_hash(mid)
            for r in self.anneaux(f["geometry"]):
                self.ligne(r, col, 2, 200)
            if etiquettes:
                r0 = self.anneaux(f["geometry"])[0]
                pt = _point_interieur(r0)
                if pt and self.dedans(*pt, 0):
                    self.texte(pt[0], pt[1], f"{p['id']} {mid}", col, petit=True)
        # îlots v2
        for f in C["ilots"]:
            if not self._proche(f["geometry"]):
                continue
            p = f["properties"]
            for r in self.anneaux(f["geometry"]):
                self.ligne(r, (255, 140, 0), 3)
            if etiquettes:
                pt = _point_interieur(self.anneaux(f["geometry"])[0])
                if pt:
                    self.texte(pt[0], pt[1], f"{p['id']} {(p.get('remplissage') or {}).get('materiau_id')}", (255, 140, 0))
        # caniveaux GAM 2026 (pointillés bleus)
        for f in C["caniveaux_gam"]:
            if self._proche(f["geometry"]):
                self.ligne([c[:2] for c in f["geometry"]["coordinates"]], (80, 160, 255), 1, 200)
        # bordures du site (hors v2)
        for f in C["bordures_site"]:
            if not self._proche(f["geometry"]):
                continue
            p = f["properties"]
            col = SRC_BORD.get(p.get("source"), (255, 60, 60))
            co = f["geometry"]["coordinates"]
            self.ligne(co, col, 1 if self.ppm <= 20 else 2, 230)
            self._tics(co, col)
            if etiquettes and self.ppm > 20:
                m = co[len(co) // 2]
                if self.dedans(m[0], m[1], 0):
                    self.texte(m[0], m[1], p["id"], col, petit=True)
        # bordures v2 par profil
        for f in C["bordures"]:
            if not self._proche(f["geometry"]):
                continue
            p = f["properties"]
            co = [c[:2] for c in f["geometry"]["coordinates"]]
            s = _abscisses(co)
            for it in p.get("intervalles", []):
                seg = _sous_ligne(co, s, it["s0"], it["s1"])
                self.ligne(seg, PROFILS.get(it.get("profil"), (255, 255, 255)), 2 if self.ppm <= 20 else 3)
            for ab in p.get("abaisses", []):
                seg = _sous_ligne(co, s, ab["s0"], ab["s1"])
                self.ligne(seg, (255, 255, 255), 4 if self.ppm > 20 else 3, 180)
            self._tics(co, (255, 255, 255))
            if etiquettes:
                m = co[len(co) // 2]
                if self.dedans(m[0], m[1], 0):
                    prof = "/".join(sorted({it.get("profil", "?") for it in p.get("intervalles", [])}))
                    self.texte(m[0], m[1], f"{p['id']} {prof} {p.get('materiau', '')}", PROFILS.get(prof.split('/')[0], (255, 255, 255)), petit=True)
        # BEV
        for f in C["ponctuels"]:
            if self._proche(f["geometry"]):
                for r in self.anneaux(f["geometry"]):
                    self.ligne(r + [r[0]], (190, 90, 255), 2)
        # marquages
        for f in C["marquages"]:
            g = f["geometry"]
            if not self._proche(g):
                continue
            p = f["properties"]
            col = CL_MARQ.get(p.get("classe"), (255, 255, 255))
            if p.get("classe") == "ligne" and p.get("type") in ("discontinue", "segment"):
                col = (0, 255, 160)
            if p.get("etat") == "neuf_2025" and p.get("classe") != "fantome":
                col = tuple(int(0.55 * c + 0.45 * 255) for c in col)   # pâli : posé en 2025, invisible en 2022
            w = 1
            for r in self.anneaux(g):
                ferme = g["type"] in ("Polygon", "MultiPolygon")
                self.ligne(r + ([r[0]] if ferme else []), col, w + (1 if self.ppm > 20 else 0))
            if etiquettes and p.get("classe") in ("fleche", "symbole", "passage", "zone", "transversale", "fantome"):
                r = self.anneaux(g)[0] if self.anneaux(g) else None
                if r:
                    xs, ys = [c[0] for c in r], [c[1] for c in r]
                    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
                    if self.dedans(cx, cy, 0) and (self.ppm > 20 or p.get("classe") != "fantome"):
                        lab = p["id"] + (f" {p.get('gabarit')}" if p.get("gabarit") else "")
                        self.texte(cx, cy, lab, col, petit=True)
            elif etiquettes and self.ppm > 20 and p.get("classe") == "ligne":
                r = self.anneaux(g)[0]
                m = r[len(r) // 2]
                if self.dedans(m[0], m[1], 0):
                    self.texte(m[0], m[1], f"{p['id']} {p.get('type')}", col, petit=True)
        # mobilier
        for f in C["mobilier"]:
            g = f["geometry"]
            p = f["properties"]
            if g["type"] == "LineString":
                if self._proche(g):
                    self.ligne(g["coordinates"], (160, 82, 45), 2, 220)
                continue
            x, y = g["coordinates"][:2]
            if not self.dedans(x, y, 1):
                continue
            col, forme = MOB.get(p.get("type"), ((200, 200, 200), "o"))
            self.marqueur(x, y, col, forme)
            if etiquettes:
                lab = p["id"] + (f" {p.get('code')}" if p.get("code") and p["code"] not in p["id"] else "")
                self.texte(x, y, lab, col, petit=True)
        # arbres
        for f in C["arbres"]:
            x, y = f["geometry"]["coordinates"][:2]
            if not self.dedans(x, y, 8):
                continue
            p = f["properties"]
            rc = (p.get("diametre_couronne_m") or 0) / 2
            X, Y = self.P(x, y)
            if rc:
                R = rc * self.ppm
                self.d.ellipse([X - R, Y - R, X + R, Y + R], outline=(60, 255, 60, 120), width=1)
            self.marqueur(x, y, (60, 255, 60), "+", r=max(4, self.ppm * 0.25))
            if etiquettes and self.dedans(x, y, 0):
                self.texte(x, y, p["id"].replace("arbre_", "a"), (60, 255, 60), petit=True)
        # corrections de cohérence
        for f in C["corrections"]:
            g = f["geometry"]
            p = f["properties"]
            if g["type"] == "LineString":
                a, b = g["coordinates"][0][:2], g["coordinates"][-1][:2]
                if self.dedans(*a, 3) or self.dedans(*b, 3):
                    self.fleche(a, b, (255, 80, 0), 2)
            elif g["type"] == "Point":
                x, y = g["coordinates"][:2]
                if self.dedans(x, y, 1):
                    self.marqueur(x, y, (255, 80, 0), "x", r=6)
                    if etiquettes:
                        self.texte(x, y, f"{p['id']} {p.get('nature')}", (255, 80, 0), petit=True)
        for f in C["ajouts"]:
            g = f["geometry"]
            p = f["properties"]
            if g["type"] == "Point":
                x, y = g["coordinates"][:2]
                if self.dedans(x, y, 1):
                    self.marqueur(x, y, (255, 0, 255), "s", r=4)
            elif self._proche(g):
                for r in self.anneaux(g):
                    self.ligne(r, (255, 0, 255), 1)
        if zp:
            a, b, c, d = zp
            self.ligne([(a, b), (c, b), (c, d), (a, d), (a, b)], (255, 255, 255), 1, 120)
        return self

    def _tics(self, co, col):
        """Petits traits côté haut (gauche de la ligne) tous les 3 m."""
        s = _abscisses(co)
        L = s[-1] if len(s) else 0
        k = 1.5
        while k < L:
            i = int(np.searchsorted(s, k)) - 1
            i = min(max(i, 0), len(co) - 2)
            (xa, ya), (xb, yb) = co[i][:2], co[i + 1][:2]
            t = (k - s[i]) / max(s[i + 1] - s[i], 1e-9)
            x, y = xa + t * (xb - xa), ya + t * (yb - ya)
            n = math.hypot(xb - xa, yb - ya) or 1
            nx, ny = -(yb - ya) / n, (xb - xa) / n
            self.ligne([(x, y), (x + nx * 0.35, y + ny * 0.35)], col, 1, 200)
            k += 3.0

    def grille(self, pas=1.0, etiquette=5.0):
        a, b, c, d = self.bbox
        W, H = self.im.size
        g = ImageDraw.Draw(self.im, "RGBA")
        f = _police(11)
        x = math.ceil(a / pas) * pas
        while x <= c:
            X = (x - self.xg) * self.ppm
            L = 12 if abs(x / etiquette - round(x / etiquette)) < 1e-6 else 6
            g.line([(X, 0), (X, L)], fill=(255, 255, 0, 255), width=1)
            g.line([(X, H - L), (X, H)], fill=(255, 255, 0, 255), width=1)
            if L == 12:
                g.text((X + 2, 12), f"{x:.0f}"[-3:], fill=(255, 255, 0, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
            x += pas
        y = math.ceil(b / pas) * pas
        while y <= d:
            Y = (self.yh - y) * self.ppm
            L = 12 if abs(y / etiquette - round(y / etiquette)) < 1e-6 else 6
            g.line([(0, Y), (L, Y)], fill=(255, 255, 0, 255), width=1)
            g.line([(W - L, Y), (W, Y)], fill=(255, 255, 0, 255), width=1)
            if L == 12:
                g.text((14, Y - 6), f"{y:.0f}"[-3:], fill=(255, 255, 0, 255), font=f, stroke_width=2, stroke_fill=(0, 0, 0, 255))
            y += pas
        return self

    def marques(self, pts, col=(0, 255, 255)):
        for i, (x, y) in enumerate(pts):
            X, Y = self.P(x, y)
            self.d = ImageDraw.Draw(self.im, "RGBA")
            self.d.line([(X - 8, Y), (X - 3, Y)], fill=col + (255,), width=1)
            self.d.line([(X + 3, Y), (X + 8, Y)], fill=col + (255,), width=1)
            self.d.line([(X, Y - 8), (X, Y - 3)], fill=col + (255,), width=1)
            self.d.line([(X, Y + 3), (X, Y + 8)], fill=col + (255,), width=1)
            self.d.text((X + 6, Y + 4), str(i + 1), fill=col + (255,), font=_police(11), stroke_width=2, stroke_fill=(0, 0, 0, 255))
        return self

    def sauver(self, chemin, q=90):
        Path(chemin).parent.mkdir(parents=True, exist_ok=True)
        self.im.save(chemin, quality=q)
        return chemin


def _abscisses(co):
    a = np.asarray([c[:2] for c in co], float)
    if len(a) < 2:
        return np.zeros(len(a))
    return np.concatenate([[0], np.cumsum(np.hypot(*np.diff(a, axis=0).T))])


def _sous_ligne(co, s, s0, s1):
    out = []
    for i in range(len(co) - 1):
        a, b = s[i], s[i + 1]
        if b < s0 or a > s1:
            continue
        def interp(t):
            k = (t - a) / max(b - a, 1e-9)
            return (co[i][0] + k * (co[i + 1][0] - co[i][0]), co[i][1] + k * (co[i + 1][1] - co[i][1]))
        if not out:
            out.append(interp(max(s0, a)))
        out.append(interp(min(s1, b)))
    return out


def _point_interieur(r):
    xs, ys = [c[0] for c in r], [c[1] for c in r]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    if _dans(cx, cy, r):
        return cx, cy
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for k in range(1, 9):
        for j in range(1, 9):
            x, y = x0 + (x1 - x0) * k / 9, y0 + (y1 - y0) * j / 9
            if _dans(x, y, r):
                return x, y
    return None


def _dans(x, y, r):
    ins = False
    n = len(r)
    for i in range(n):
        x1, y1 = r[i][:2]
        x2, y2 = r[(i + 1) % n][:2]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-15) + x1:
            ins = not ins
    return ins


def legende(chemin):
    im = Image.new("RGB", (520, 470), (25, 25, 25))
    d = ImageDraw.Draw(im)
    f = _police(13)
    y = 8
    def l(col, txt, w=3):
        nonlocal y
        d.line([(10, y + 8), (50, y + 8)], fill=col, width=w)
        d.text((60, y), txt, fill=(235, 235, 235), font=f)
        y += 20
    d.text((10, y), "Superposition description v2 / ortho PCRS 5 cm (10/05/2022)", fill=(255, 255, 255), font=f); y += 24
    for k, v in PROFILS.items():
        l(v, f"bordure v2 profil {k} (traits côté haut tous les 3 m)")
    l((255, 255, 255), "abaissé v2 (blanc épais)", 5)
    for k, v in SRC_BORD.items():
        l(v, f"bordure site ({k}), carte de cohérence", 1)
    l((80, 160, 255), "caniveau GAM 2026", 1)
    l((255, 140, 0), "îlot v2")
    l((190, 90, 255), "BEV v2")
    for k, v in CL_MARQ.items():
        l(v, f"marquage {k} (pâli : neuf_2025, invisible en 2022)", 2)
    l((0, 255, 160), "marquage ligne discontinue / segment", 2)
    l((255, 80, 0), "correction de cohérence (flèche source -> résolu ; X non instancié)")
    l((60, 255, 60), "arbre (croix = tronc, cercle = couronne)", 1)
    l((255, 0, 200), "hachures magenta : zone modifiée par les travaux 2025", 1)
    im.save(chemin)


def tuile_overlay(t, sortie=None):
    x0, y0 = (float(v) for v in t.split("_"))
    R = Rendu(x0, y0, x0 + 50, y0 + 50, ppm=20).dessiner()
    R.grille(pas=5.0, etiquette=10.0)
    sortie = sortie or ICI / "overlays" / f"{t}_overlay.jpg"
    return R.sauver(sortie)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("args", nargs="*")
    ap.add_argument("--cote", type=float, default=12.5)
    ap.add_argument("--zoom", type=float, default=2.0)
    ap.add_argument("--brut", action="store_true")
    ap.add_argument("--sans-etiquettes", action="store_true")
    ap.add_argument("--sortie")
    ap.add_argument("--marques", default="")
    a = ap.parse_args()
    if a.cmd == "tuile":
        for t in a.args:
            print(tuile_overlay(t))
    elif a.cmd == "toutes":
        legende(ICI / "overlays" / "legende.png")
        for t in TUILES_A:
            print(tuile_overlay(t))
    elif a.cmd == "decoupe":
        x0, y0 = float(a.args[0]), float(a.args[1])
        R = Rendu(x0, y0, x0 + a.cote, y0 + a.cote, ppm=20 * a.zoom, brut=a.brut)
        R.dessiner(etiquettes=not a.sans_etiquettes)
        R.grille()
        if a.marques:
            R.marques([tuple(float(v) for v in p.split(",")) for p in a.marques.split(";") if p])
        s = a.sortie or f"decoupe_{x0:.1f}_{y0:.1f}{'_brut' if a.brut else ''}.jpg"
        print(R.sauver(s))
    elif a.cmd == "paire":
        # brut | superposé, côte à côte (même boîte, mêmes graduations)
        x0, y0 = float(a.args[0]), float(a.args[1])
        mk = [tuple(float(v) for v in p.split(",")) for p in a.marques.split(";") if p]
        A = Rendu(x0, y0, x0 + a.cote, y0 + a.cote, ppm=20 * a.zoom, brut=True).grille()
        B = Rendu(x0, y0, x0 + a.cote, y0 + a.cote, ppm=20 * a.zoom).dessiner(etiquettes=not a.sans_etiquettes).grille()
        if mk:
            A.marques(mk)
            B.marques(mk)
        W, H = A.im.size
        im = Image.new("RGB", (2 * W + 6, H), (255, 255, 255))
        im.paste(A.im, (0, 0))
        im.paste(B.im, (W + 6, 0))
        s = a.sortie or f"paire_{x0:.1f}_{y0:.1f}.jpg"
        Path(s).parent.mkdir(parents=True, exist_ok=True)
        im.save(s, quality=90)
        print(s)
    elif a.cmd == "px2l93":
        print("%.3f %.3f" % px2l93(a.args[0], float(a.args[1]), float(a.args[2])))
    elif a.cmd == "l932px":
        print("%.1f %.1f" % l932px(a.args[0], float(a.args[1]), float(a.args[2])))
    elif a.cmd == "travaux":
        b = etat_travaux(float(a.args[0]), float(a.args[1]), float(a.args[2]) if len(a.args) > 2 else 0)
        print(b, libelle_travaux(b))
    else:
        ap.error("commande inconnue")


if __name__ == "__main__":
    main()
