"""Planches de contrôle des marquages v2 sur l'ortho du paquet : polygones v1 (contour rouge / jaune,
fantômes en magenta) contre la peinture reconstruite depuis les PARAMÈTRES v2 (blanc / jaune plein :
tirets selon modulation et phase, bandes de zébra, tuiles, gabarits posés, hachures, zigzags).

Usage :
    python recon/pcg/decrire/marquages_apercu.py [--base DOSSIER_BASE] [--dossier SORTIE_PNG] [--res 0.02]
Vues : a_verdun_sw_traversee, b_centre, c_verdun_ne, d_vercors (+ site.png à 0,15 m/px).
"""
import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
from apercu import fond_ortho, police  # noqa: E402
from commun import RACINE, SORTIE, anneaux, lire_geojson, repere, sous_polyligne  # noqa: E402
from marquages_controles import _pieces  # noqa: E402

VUES = {
    "a_verdun_sw_traversee": (-34.0, -36.0, 6.0, -4.0),
    "b_centre": (-16.0, -14.0, 20.0, 18.0),
    "c_verdun_ne": (8.0, 4.0, 58.0, 44.0),
    "d_vercors": (-4.0, -66.0, 36.0, -14.0),
}
DOSSIER = RACINE / "recon/pc/rendus/v2_marquages"
COUL = {"blanc": (250, 250, 250, 255), "jaune": (255, 215, 40, 255), "ocre": (230, 140, 60, 255)}


class Toile:
    def __init__(self, emprise, res):
        self.x0, self.y0, self.x1, self.y1 = emprise
        self.res = res
        fond = fond_ortho(*emprise, res)
        self.img = Image.blend(fond, Image.new("RGB", fond.size, (0, 0, 0)), 0.45).convert("RGBA")
        self.calque = Image.new("RGBA", self.img.size, (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.calque, "RGBA")

    def px(self, P):
        P = np.atleast_2d(P)
        return [((x - self.x0) / self.res, (self.y1 - y) / self.res) for x, y in P[:, :2]]

    def poly(self, r, fill=None, outline=None, width=1):
        if len(r) >= 3:
            self.d.polygon(self.px(r), fill=fill, outline=outline, width=width)

    def ligne(self, P, coul, w_m):
        if len(P) >= 2:
            self.d.line(self.px(P), fill=coul, width=max(1, int(round(w_m / self.res))), joint="curve")

    def fin(self):
        return Image.alpha_composite(self.img, self.calque).convert("RGB")


def _rect(c, u, L, W):
    v = np.array([-u[1], u[0]])
    return np.array([c + u * a * L / 2 + v * b * W / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))])


def peindre(t, f):
    """Peinture d'une entité v2 depuis ses paramètres (repère local)."""
    p, g = f["properties"], f["geometry"]
    coul = COUL.get(p["couleur"], COUL["blanc"])
    cl = p["classe"]
    if cl in ("ligne", "transversale"):
        P = repere(np.asarray(g["coordinates"], float))
        q = dict(p)
        if cl == "transversale":
            q["type"] = "discontinue"
        for a, b in _pieces(q, P):
            t.ligne(sous_polyligne(P, a, b), coul, p["largeur_m"])
    elif cl == "passage" and p["type"] == "zebra":
        A, B = repere(np.asarray(g["coordinates"], float))
        h = math.radians(p["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        for k in range(p["nb_emplacements"]):
            if k not in p["coupures"]:
                t.poly(_rect(A + ax * k * p["pas_axe_m"], u, p["longueur_bande_m"], p["largeur_bande_m"]), fill=coul)
    elif cl == "passage":
        for fl in p["files"]:
            A, B = repere(np.asarray(fl["axe_l93"], float))
            h = math.radians(fl["cap_deg"])
            d = np.array([math.cos(h), math.sin(h)])
            c_ = COUL.get(fl["couleur"], coul)
            for k in range(fl["nb"] + len(fl["absents"])):
                if k in fl["absents"]:
                    continue
                c = A + d * k * fl["pas_m"]
                if "gabarit" in fl:
                    for poly in M.gabarit(fl["gabarit"]):
                        t.poly(M.poser(poly[0], c, fl["cap_deg"]), fill=c_)
                else:
                    tm = fl["tuile_m"]
                    t.poly(_rect(c, np.array([-d[1], d[0]]), tm["perp_file"], tm["le_long_file"]), fill=c_)
    elif cl == "fleche" or (cl == "symbole" and p["type"] == "velo"):
        o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        for poly in M.gabarit(p["gabarit"]):
            t.poly(M.poser(poly[0], o, p["pose"]["cap_deg"], p.get("echelle", 1.0)), fill=coul)
            for tr in poly[1:]:
                t.poly(M.poser(tr, o, p["pose"]["cap_deg"], p.get("echelle", 1.0)), fill=(0, 0, 0, 0))
    elif cl == "symbole" and p["type"] == "dent_requin":
        o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        b, h = p["triangle"]["base_m"], p["triangle"]["hauteur_m"]
        t.poly(M.poser(np.array([[-b / 2, 0], [b / 2, 0], [0, h]]), o, p["pose"]["cap_deg"]), fill=coul)
    elif cl == "symbole" and p["type"] == "chevron":
        o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        c = p["chevron"]
        a = math.radians(c["ouverture_deg"] / 2)
        for sg in (-1, 1):
            br = np.array([[0, 0], [sg * math.sin(a) * c["branche_m"], -math.cos(a) * c["branche_m"]]])
            t.ligne(M.poser(br, o, p["pose"]["cap_deg"]), coul, c["trait_m"])
    elif cl == "symbole" and p["type"] in ("barre", "a_vectoriser"):
        o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        h = math.radians(p["pose"]["cap_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        dims = p.get("rectangle") or p.get("boite")
        r = _rect(o, u, dims["longueur_m"], dims["largeur_m"])
        if p["type"] == "barre":
            t.poly(r, fill=coul)
        else:
            t.poly(r, outline=(0, 220, 255, 255), width=2)
    elif cl == "symbole" and p["type"] == "point":
        o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        rr = p["disque"]["diametre_m"] / 2
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        t.poly(o + rr * np.c_[np.cos(a), np.sin(a)], fill=coul)
    elif cl == "zone" and p["type"] == "hachures":
        poly = [repere(r) for r in anneaux(g)[0]]
        h = math.radians(p["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        n = np.array([-u[1], u[0]])
        o = repere(np.asarray(p["origine_bandes_l93"], float)[None])[0]
        masque = Image.new("L", t.img.size, 0)
        ImageDraw.Draw(masque).polygon(t.px(poly[0]), fill=255)
        bandes = Image.new("L", t.img.size, 0)
        db = ImageDraw.Draw(bandes)
        ext = float(np.max(np.hypot(*(poly[0] - o).T))) + 2.0
        for k in range(-int(ext / p["pas_m"]) - 1, int(ext / p["pas_m"]) + 2):
            c = o + n * k * p["pas_m"]
            db.line(t.px(np.vstack([c - u * ext, c + u * ext])), fill=255, width=max(1, int(p["bande_m"] / t.res)))
        m = np.minimum(np.asarray(masque), np.asarray(bandes))
        t.calque.paste(Image.new("RGBA", t.img.size, coul), (0, 0), Image.fromarray(m))
        if p.get("contour_peint"):
            t.ligne(np.vstack([poly[0], poly[0][:1]]), coul, p["contour_largeur_m"] or 0.15)
    elif cl == "zone" and p["type"] == "zigzag":
        A, B = repere(np.asarray(g["coordinates"], float))
        L = float(np.hypot(*(B - A)))
        u = (B - A) / L
        n = np.array([-u[1], u[0]]) * p["cote"]
        demi = p["periode_m"] / 2
        k = int(round(L / demi))
        pts = [A]
        for i in range(k + 1):
            pts.append(A + u * i * demi + n * (p["amplitude_m"] if i % 2 == 0 else 0.0))
        pts.append(B)
        t.ligne(np.array(pts), coul, p["trait_m"])
    else:
        for poly in anneaux(g):
            r = repere(poly[0])
            if cl == "fantome":
                t.poly(r, fill=(200, 200, 200, 70), outline=(255, 0, 255, 255))
            else:
                t.poly(r, fill=coul)


def planche(fichier, emprise, base, res=0.02, etiquettes=True):
    t = Toile(emprise, res)
    x0, y0, x1, y1 = emprise
    # v1 : contours
    for m in M.v1():
        r = m["r"]
        if r[:, 0].max() < x0 or r[:, 0].min() > x1 or r[:, 1].max() < y0 or r[:, 1].min() > y1:
            continue
        c = (255, 0, 255, 255) if m["p"]["type"] == "fantome" else ((255, 60, 60, 255) if m["p"]["couleur"] == "blanc" else (255, 170, 0, 255))
        for poly in m["polys"]:
            t.d.line(t.px(np.vstack([poly[0], poly[0][:1]])), fill=c, width=1)
    feats = lire_geojson(Path(base) / "marquages.geojson")
    for f in feats:
        bb = _bbox(f)
        if bb[2] < x0 or bb[0] > x1 or bb[3] < y0 or bb[1] > y1:
            continue
        if f["properties"]["classe"] == "fantome":
            peindre(t, f)
    for f in feats:
        bb = _bbox(f)
        if bb[2] < x0 or bb[0] > x1 or bb[3] < y0 or bb[1] > y1 or f["properties"]["classe"] == "fantome":
            continue
        peindre(t, f)
    img = t.fin()
    d = ImageDraw.Draw(img)
    if etiquettes:
        ft = police(max(10, int(0.25 / res * 0.5)))
        for f in feats:
            bb = _bbox(f)
            c = np.array([(bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2])
            if x0 < c[0] < x1 and y0 < c[1] < y1 and f["properties"]["classe"] != "fantome":
                d.text(t.px(c)[0], f["properties"]["id"], fill=(0, 255, 120), font=ft)
    ft = police(16)
    d.rectangle([0, 0, img.size[0], 26], fill=(0, 0, 0))
    d.text((6, 4), f"{Path(fichier).stem} : v1 contours (rouge/jaune, fantômes magenta) / v2 paramétrique (peinture) — {res * 100:.0f} cm/px, x {x0:.0f}..{x1:.0f}, y {y0:.0f}..{y1:.0f}",
           fill=(255, 255, 255), font=ft)
    Path(fichier).parent.mkdir(parents=True, exist_ok=True)
    img.save(fichier, optimize=True)
    return fichier


def _bbox(f):
    g = f["geometry"]
    def pts(c):
        return np.vstack([np.asarray(x, float).reshape(-1, 2) for x in _aplatir(c)])
    P = repere(pts(g["coordinates"]))
    return (*P.min(axis=0), *P.max(axis=0))


def _aplatir(c):
    if isinstance(c[0], (int, float)):
        return [c[:2]]
    out = []
    for x in c:
        out += _aplatir(x)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default=str(SORTIE / "base"))
    ap.add_argument("--dossier", default=str(DOSSIER))
    ap.add_argument("--res", type=float, default=0.02)
    ap.add_argument("--vues", nargs="*", default=list(VUES))
    a = ap.parse_args()
    for nom in a.vues:
        print(planche(Path(a.dossier) / f"{nom}.png", VUES[nom], a.base, a.res))
    print(planche(Path(a.dossier) / "site.png", (-150.0, -150.0, 150.0, 150.0), a.base, 0.15, etiquettes=False))


if __name__ == "__main__":
    main()
