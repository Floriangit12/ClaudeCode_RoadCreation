"""Outils communs de l'inventaire des changements 2022 -> 2025 (avant travaux).

Lecture seule des données du dépôt ; réutilise les mosaïques et le recalage de
recon/pcg/enrichir/orthos_recentes.py (convention : position cadre PCRS 2022 = position lue
sur la couche − (dx, dy)). Repère local = L93 − O(917279.43, 6460289.98).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[7]
sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
import orthos_recentes as OR  # noqa: E402

O = OR.O
ICI = Path(__file__).resolve().parents[1]           # dossier changements/
PLANCHES = ICI / "planches"
DONNEES = ICI / "donnees"
PHOTOS_NV = ICI / "photos_non_versionnees"

TAG = {"2022": "pcrs2022", "2024": OR.NATIVES[OR.REF_2024]["tag"],
       "2024irc": OR.NATIVES["ORTHOIMAGERY.ORTHOPHOTOS.IRC.2024"]["tag"],
       "2025": OR.NATIVES["ORTHOIMAGERY.ORTHO-SAT.PLEIADES.2025"]["tag"],
       "spot2022": "ign_spot_2022_150cm", "spot2023": "ign_spot_2023_150cm",
       "spot2024": "ign_spot_2024_150cm", "spot2025": "ign_spot_2025_150cm"}
LIB = {"2022": "PCRS 5 cm 10/05/2022", "2024": "IGN BD ORTHO 20 cm 09/08/2024",
       "2025": "Pléiades 50 cm 2025 (avant 23/06 ?)", "2024irc": "IGN IRC 09/08/2024",
       "spot2022": "SPOT 2022 (1,5 m)", "spot2023": "SPOT 2023 (1,5 m)",
       "spot2024": "SPOT 2024 (1,5 m)", "spot2025": "SPOT 2025 (1,5 m)"}


def police(t):
    for n in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(n, t)
        except OSError:
            pass
    return ImageFont.load_default()


def l93(xl, yl):
    return (xl + O[0], yl + O[1])


def boite_locale(x0, y0, x1, y1):
    return (O[0] + x0, O[1] + y0, O[0] + x1, O[1] + y1)


def lire(cle, b, res, filtre=Image.BICUBIC):
    """Image RGB de la boîte L93 b à res m/px, recalée dans le cadre PCRS 2022."""
    tag = TAG[cle]
    dx, dy = OR.decalages().get(tag, (0.0, 0.0))
    return OR.mosaique(tag).fenetre(b[0] + dx, b[1] + dy, b[2] + dx, b[3] + dy, res=res, filtre=filtre)


class Vue:
    """Panneau image d'une boîte L93 avec grille locale, titre et tracés en coordonnées locales."""

    def __init__(self, cle, b, px=600, titre=None, im=None):
        self.b, self.px = b, px
        self.res = (b[2] - b[0]) / px
        self.im = im if im is not None else lire(cle, b, self.res)
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.titre = titre if titre is not None else LIB.get(cle, cle)

    def P(self, xl, yl):
        return ((xl + O[0] - self.b[0]) / self.res, (self.b[3] - (yl + O[1])) / self.res)

    def grille(self, pas=10.0, etiquette=50.0):
        f = police(12)
        x0l, y0l, x1l, y1l = self.b[0] - O[0], self.b[1] - O[1], self.b[2] - O[0], self.b[3] - O[1]
        for v in np.arange(math.ceil(x0l / pas) * pas, x1l + 1e-6, pas):
            u = self.P(v, 0)[0]
            fort = abs(v / etiquette - round(v / etiquette)) < 1e-6
            self.d.line([(u, 0), (u, self.im.height)], fill=(255, 255, 0, 100 if fort else 45), width=1)
            if fort:
                self.d.text((u + 2, self.im.height - 14), f"{v:+.0f}", fill=(255, 255, 0, 255), font=f)
        for v in np.arange(math.ceil(y0l / pas) * pas, y1l + 1e-6, pas):
            w = self.P(0, v)[1]
            fort = abs(v / etiquette - round(v / etiquette)) < 1e-6
            self.d.line([(0, w), (self.im.width, w)], fill=(255, 255, 0, 100 if fort else 45), width=1)
            if fort:
                self.d.text((2, w + 1), f"{v:+.0f}", fill=(255, 255, 0, 255), font=f)
        if self.titre:
            ft = police(14)
            self.d.rectangle([0, 0, 8 * len(self.titre) + 8, 19], fill=(0, 0, 0, 180))
            self.d.text((3, 2), self.titre, fill=(255, 255, 255, 255), font=ft)
        return self

    def poly(self, pts, col=(255, 0, 255, 255), w=2, ferme=True, etiquette=None):
        q = [self.P(*p) for p in pts]
        if ferme:
            q = q + [q[0]]
        self.d.line(q, fill=col, width=w)
        if etiquette:
            u = min(p[0] for p in q)
            v = min(p[1] for p in q)
            f = police(13)
            self.d.rectangle([u, v - 16, u + 8 * len(etiquette) + 6, v], fill=(0, 0, 0, 170))
            self.d.text((u + 3, v - 15), etiquette, fill=col, font=f)
        return self

    def point(self, xl, yl, col=(255, 0, 255, 255), r=6, etiquette=None):
        u, v = self.P(xl, yl)
        self.d.ellipse([u - r, v - r, u + r, v + r], outline=col, width=2)
        if etiquette:
            self.d.text((u + r + 2, v - 7), etiquette, fill=col, font=police(13))
        return self


def assembler(panneaux, titre, ncol=None, marge=6, entete=24):
    ncol = ncol or len(panneaux)
    w, h = panneaux[0].size
    nl = math.ceil(len(panneaux) / ncol)
    im = Image.new("RGB", (ncol * w + (ncol - 1) * marge, nl * h + (nl - 1) * marge + entete), (25, 25, 25))
    for k, p in enumerate(panneaux):
        im.paste(p, ((k % ncol) * (w + marge), entete + (k // ncol) * (h + marge)))
    ImageDraw.Draw(im).text((4, 4), titre, fill=(255, 255, 255), font=police(15))
    return im


def lire_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def ecrire_json(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def rel(p):
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return str(p)
