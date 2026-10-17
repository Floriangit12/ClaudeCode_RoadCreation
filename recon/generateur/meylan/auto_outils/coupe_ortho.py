"""Coupes en travers mesurées sur l'ortho IGN 20 cm (lot B, relevé Meylan : autoroute et grands axes).

Pour chaque station d'un axe (polyligne L93), on redresse une bande de l'ortho (axe horizontal, sens de
circulation de gauche à droite, côté gauche du sens en haut) et on calcule, colonne par colonne en travers,
la moyenne le long de l'axe :
  - luminance (marquages blancs = pics étroits ; béton des GBA = plateau clair de 0,5-0,8 m) ;
  - indice de végétation 2G − R − B (herbe, arbres) ;
  - saturation (enrobé gris peu saturé).
Les pics de luminance (luminance − médiane glissante sur ± 1,5 m > seuil) donnent la position t des lignes ;
les écarts entre pics donnent les largeurs de voies. Les tuiles produites sont à la résolution native de
l'ortho suréchantillonnée 2 × (0,10 m/px, bilinéaire), ≤ 1092 px, avec une règle graduée en marge (hors image).

    python recon/generateur/meylan/auto_outils/coupe_ortho.py --site auto_a41_section_courante \
        --polyligne 917300,6459690 918100,6459880 --stations 100 300 500 --demi 25 --long 40

Sorties : recon/out/generateur/meylan/<site>/coupes/coupe_<s>.png et coupes.json (non versionnés).
"""
import argparse
import glob
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

RACINE = Path(__file__).resolve().parents[4]
OUT = RACINE / "recon" / "out" / "generateur" / "meylan"
MOTIF = str(OUT / "auto_travail_lotB" / "ortho" / "ign_hr" / "*.jpg")
Image.MAX_IMAGE_PIXELS = None


class Ortho:
    def __init__(self, motif=MOTIF):
        self.dalles = []
        for p in sorted(glob.glob(motif)):
            a, _, _, e, c, f = [float(v) for v in Path(p).with_suffix(".jgw").read_text().split()]
            self.dalles.append((p, a, e, c - a / 2, f - e / 2))   # coin haut-gauche
        self.cache = {}

    def _img(self, p):
        if p not in self.cache:
            self.cache[p] = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
        return self.cache[p]

    def echantillonner(self, X, Y):
        """Valeurs RVB bilinéaires aux points (X, Y) L93 (tableaux de même forme) ; NaN hors couverture."""
        out = np.full(X.shape + (3,), np.nan, np.float32)
        for p, a, e, x0, y1 in self.dalles:
            im = self._img(p)
            h, w = im.shape[:2]
            u = (X - x0) / a - 0.5
            v = (y1 - Y) / -e - 0.5
            m = (u >= 0) & (u < w - 1) & (v >= 0) & (v < h - 1)
            if not m.any():
                continue
            uu, vv = u[m], v[m]
            i0, j0 = np.floor(uu).astype(int), np.floor(vv).astype(int)
            du, dv = (uu - i0)[:, None], (vv - j0)[:, None]
            val = (im[j0, i0] * (1 - du) * (1 - dv) + im[j0, i0 + 1] * du * (1 - dv)
                   + im[j0 + 1, i0] * (1 - du) * dv + im[j0 + 1, i0 + 1] * du * dv)
            out[m] = val
        return out


def polyligne_abscisses(pts):
    pts = np.asarray(pts, float)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    return pts, d


def point_dir(pts, d, s):
    i = int(np.clip(np.searchsorted(d, s) - 1, 0, len(pts) - 2))
    t = (s - d[i]) / max(d[i + 1] - d[i], 1e-9)
    p = pts[i] + t * (pts[i + 1] - pts[i])
    u = (pts[i + 1] - pts[i]) / max(d[i + 1] - d[i], 1e-9)
    return p, u


def pics(prof, pas, seuil=12.0, larg_max=0.9):
    """Pics étroits de luminance : (t_centre, largeur, contraste)."""
    n = len(prof)
    k = int(round(1.5 / pas))
    med = np.array([np.nanmedian(prof[max(0, i - k):i + k + 1]) for i in range(n)])
    hp = prof - med
    res = []
    i = 0
    while i < n:
        if hp[i] > seuil:
            j = i
            while j + 1 < n and hp[j + 1] > seuil:
                j += 1
            larg = (j - i + 1) * pas
            if larg <= larg_max:
                c = i + np.nanargmax(hp[i:j + 1])
                res.append((c, larg, float(np.nanmax(hp[i:j + 1]))))
            i = j + 1
        else:
            i += 1
    return res


def coupe(ortho, pts, d, s, demi, long_, pas=0.10):
    p, u = point_dir(pts, d, s)
    nrm = np.array([-u[1], u[0]])                     # gauche du sens
    na = int(round(long_ / pas))
    nt = int(round(2 * demi / pas))
    a = (np.arange(na) + 0.5) * pas - long_ / 2       # le long
    t = demi - (np.arange(nt) + 0.5) * pas            # en travers, gauche en haut
    A, Tt = np.meshgrid(a, t)
    X = p[0] + A * u[0] + Tt * nrm[0]
    Y = p[1] + A * u[1] + Tt * nrm[1]
    rgb = ortho.echantillonner(X, Y)
    lum = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    vert = 2 * rgb[..., 1] - rgb[..., 0] - rgb[..., 2]
    mx, mn = np.nanmax(rgb, axis=-1), np.nanmin(rgb, axis=-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    prof_l = np.nanmean(lum, axis=1)
    prof_v = np.nanmean(vert, axis=1)
    prof_s = np.nanmean(sat, axis=1)
    pk = pics(prof_l, pas)
    return {"p": p, "u": u, "nrm": nrm, "rgb": rgb, "t": t, "lum": prof_l, "vert": prof_v, "sat": prof_s,
            "pics": [{"t": round(float(t[c]), 2), "largeur": round(w, 2), "contraste": round(h, 1)} for c, w, h in pk]}


def image_coupe(c, pas, fichier, titre=""):
    rgb = np.nan_to_num(c["rgb"], nan=0).clip(0, 255).astype(np.uint8)
    nt, na = rgb.shape[:2]
    marge = 60
    W, H = na + marge, nt
    im = Image.new("RGB", (W, H), (255, 255, 255))
    im.paste(Image.fromarray(rgb), (marge, 0))
    dr = ImageDraw.Draw(im)
    t = c["t"]
    for k in range(int(math.floor(t[-1])), int(math.ceil(t[0])) + 1):
        j = int(round((t[0] - k) / pas))
        if 0 <= j < H:
            L = 18 if k % 5 == 0 else 8
            dr.line([(marge - L, j), (marge - 1, j)], fill=(0, 0, 0))
            if k % 5 == 0:
                dr.text((2, max(0, j - 6)), "%+d" % k, fill=(0, 0, 0))
    im.save(fichier)
    assert W <= 1092 and H <= 1092, (W, H)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--polyligne", nargs="+", required=True, help="x,y L93 ...")
    ap.add_argument("--stations", nargs="+", type=float, required=True)
    ap.add_argument("--demi", type=float, default=25.0)
    ap.add_argument("--long", type=float, default=40.0)
    ap.add_argument("--nom", default="coupe")
    a = ap.parse_args()
    pts, d = polyligne_abscisses([[float(v) for v in s.split(",")] for s in a.polyligne])
    ortho = Ortho()
    out = OUT / a.site / "coupes"
    out.mkdir(parents=True, exist_ok=True)
    res = []
    pas = 0.10
    for s in a.stations:
        c = coupe(ortho, pts, d, s, a.demi, a.long, pas)
        f = out / ("%s_s%04d.png" % (a.nom, int(round(s))))
        image_coupe(c, pas, f)
        ech = []
        for k in range(0, len(c["t"]), 5):   # profil tous les 0,5 m
            ech.append([round(float(c["t"][k]), 2), round(float(np.nan_to_num(c["lum"][k])), 1),
                        round(float(np.nan_to_num(c["vert"][k])), 1), round(float(np.nan_to_num(c["sat"][k])), 3)])
        res.append({"station_m": s, "centre_l93": [round(float(c["p"][0]), 2), round(float(c["p"][1]), 2)],
                    "cap_axe_deg": round((math.degrees(math.atan2(c["u"][0], c["u"][1])) + 360) % 360, 2),
                    "image": f.name, "pics_lum": c["pics"], "profil_t_lum_vert_sat_pas05": ech})
        print("s=%6.1f  pics t :" % s, " ".join("%+.2f" % q["t"] for q in c["pics"]))
    jf = out / ("%s.json" % a.nom)
    jf.write_text(json.dumps({"polyligne_l93": pts.tolist(), "demi_largeur_m": a.demi, "longueur_moyenne_m": a.long,
                              "pas_m": pas, "source": "IGN HR.ORTHOIMAGERY.ORTHOPHOTOS 20 cm (WMS Géoplateforme, Etalab 2.0)",
                              "coupes": res}, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
