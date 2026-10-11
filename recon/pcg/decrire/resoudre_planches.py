"""Planches avant / après sur l'ortho PCRS 2022 (5 cm) des 15 changements les plus significatifs de la résolution.

Fond : ortho 2022 (antérieure aux travaux 2025) ; en jaune, les arêtes avant des bordures 2026 de la description
(base 0.3) ; avant en rouge, après en cyan. Les planches contiennent une imagerie tierce : elles restent locales.
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from commun import O, abscisses, anneaux, point_a, repere
import marquages_couverture as MC

RES = 0.025
TAILLE_M = (20.0, 15.0)
QUOTAS = {"deplacement": 8, "non_instancie_absent_2026": 3, "recalage_fleche": 2, "retrait": 1, "arret_a_l_arete": 1,
          "reorientation": 1}
ROUGE, CYAN, JAUNE, BLANC, VERT = (255, 60, 60), (0, 230, 255), (255, 220, 0), (255, 255, 255), (60, 255, 90)


def selection(J, n=15):
    choisis, vus = [], []
    compte = {}
    for e in sorted(J.appliquees, key=lambda e: (-e["portee"], e["famille"], e["id"])):
        q = QUOTAS.get(e["nature"], 0)
        if compte.get(e["nature"], 0) >= q or e.get("xy_apres_local") is None:
            continue
        b = e["xy_apres_local"]
        if any(math.hypot(b[0] - v[0], b[1] - v[1]) < 0.3 and e["nature"] == nat for v, nat in vus):
            continue
        choisis.append(e)
        vus.append((b, e["nature"]))
        compte[e["nature"]] = compte.get(e["nature"], 0) + 1
        if len(choisis) >= n:
            break
    return choisis


class Toile:
    def __init__(self, cx, cy):
        w, h = TAILLE_M
        self.x0, self.y1 = cx - w / 2, cy + h / 2
        self.im = MC.ortho_rgb(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, RES).convert("RGB")
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.f = MC.police(15)
        self.fp = MC.police(13)

    def px(self, x, y):
        return ((x - self.x0) / RES, (self.y1 - y) / RES)

    def ligne(self, P, col, w=2):
        pts = [self.px(*p[:2]) for p in P]
        if len(pts) >= 2:
            self.d.line(pts, fill=col, width=w)

    def poly(self, R, col, w=2, fond=None):
        pts = [self.px(*p[:2]) for p in R]
        if len(pts) >= 3:
            self.d.polygon(pts, outline=col, fill=fond)
            self.d.line(pts + [pts[0]], fill=col, width=w)

    def cercle(self, x, y, r_m, col, w=3):
        u, v = self.px(x, y)
        r = r_m / RES
        self.d.ellipse([u - r, v - r, u + r, v + r], outline=col, width=w)

    def croix(self, x, y, r_m, col, w=4):
        u, v = self.px(x, y)
        r = r_m / RES
        self.d.line([u - r, v - r, u + r, v + r], fill=col, width=w)
        self.d.line([u - r, v + r, u + r, v - r], fill=col, width=w)

    def fleche(self, a, b, col, w=3):
        self.ligne([a, b], col, w)
        u0, v0 = self.px(*a)
        u1, v1 = self.px(*b)
        ang = math.atan2(v1 - v0, u1 - u0)
        for s in (2.6, -2.6):
            self.d.line([u1, v1, u1 - 14 * math.cos(ang + s), v1 - 14 * math.sin(ang + s)], fill=col, width=w)

    def texte(self, x, y, t, col=BLANC):
        u, v = self.px(x, y)
        self.d.text((u + 6, v - 18), t, fill=col, font=self.fp, stroke_width=2, stroke_fill=(0, 0, 0))

    def echelle(self):
        W, H = self.im.size
        L = 2.0 / RES
        self.d.rectangle([12, H - 30, 12 + L, H - 24], fill=BLANC)
        self.d.text((12, H - 50), "2 m", fill=BLANC, font=self.fp, stroke_width=2, stroke_fill=(0, 0, 0))
        self.d.line([W - 24, 40, W - 24, 14], fill=BLANC, width=3)
        self.d.text((W - 30, 42), "N", fill=BLANC, font=self.fp, stroke_width=2, stroke_fill=(0, 0, 0))


def _bordures(t, S):
    for f in S.base["bordures"]["features"]:
        P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
        if (P[:, 0].max() < t.x0 or P[:, 0].min() > t.x0 + TAILLE_M[0] or P[:, 1].max() < t.y1 - TAILLE_M[1]
                or P[:, 1].min() > t.y1):
            continue
        t.ligne(P, JAUNE, 1)


def _geom_locale(g):
    if g["type"] == "LineString":
        return [repere(np.asarray(g["coordinates"], float)[:, :2])]
    if g["type"] == "MultiLineString":
        return [repere(np.asarray(c, float)[:, :2]) for c in g["coordinates"]]
    return [repere(r) for poly in anneaux(g) for r in poly]


def _legende(im, lignes):
    W, H = im.size
    h = 22 * len(lignes) + 12
    out = Image.new("RGB", (W, H + h), (20, 20, 20))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f = MC.police(14)
    for k, l in enumerate(lignes):
        d.text((10, H + 6 + 22 * k), l[:118], fill=BLANC, font=f)
    return out


def planche(S, e, rang, dossier):
    a, b = e.get("xy_avant_local"), e["xy_apres_local"]
    cx, cy = (b if a is None else [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
    t = Toile(cx, cy)
    _bordures(t, S)
    nat = e["nature"]
    F = {f["properties"]["id"]: f for f in S.base["marquages"]["features"]}
    if nat == "deplacement":
        t.cercle(*a, 0.25, ROUGE)
        t.cercle(*b, 0.25, CYAN)
        t.fleche(a, b, CYAN, 2)
        t.texte(*a, "avant", ROUGE)
        t.texte(*b, "après", CYAN)
    elif nat == "non_instancie_absent_2026":
        t.croix(*b, 0.6, ROUGE)
        t.cercle(*b, 1.5, ROUGE, 2)
        t.texte(*b, "non instancié (absent 2026)", ROUGE)
    elif nat == "recalage_fleche":
        for g, col, fond in ((e.get("geometrie_avant_l93"), ROUGE, None), (e.get("geometrie_apres_l93"), CYAN, (0, 230, 255, 70))):
            if g:
                for R in _geom_locale(g):
                    t.poly(R, col, 2, fond)
        t.texte(*b, "après (cyan) / avant (rouge)", CYAN)
    elif nat == "retrait":
        g = e.get("geometrie_l93")
        if g:
            for R in _geom_locale(g):
                if g["type"] in ("Polygon", "MultiPolygon"):
                    t.poly(R, ROUGE, 3)
                else:
                    t.ligne(R, ROUGE, 4)
        t.croix(*b, 0.4, ROUGE)
        t.texte(*b, "non fabriqué (retiré)", ROUGE)
    elif nat == "arret_a_l_arete":
        f = F.get(e["id"])
        if f:
            P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
            L = float(abscisses(P)[-1])
            ivs = f["properties"].get("interruptions", [])
            s = np.linspace(0, L, max(3, int(L / 0.05)))
            Q, _ = point_a(P, s)
            hors = np.zeros(len(s), bool)
            for i0, i1 in ivs:
                hors |= (s >= i0) & (s <= i1)
            for k in range(len(s) - 1):
                t.ligne([Q[k], Q[k + 1]], ROUGE if hors[k] else VERT, 4)
        t.texte(*b, "peint (vert) / non peint au-delà de l'arête (rouge)", BLANC)
    elif nat == "reorientation":
        a0 = (e["avant"] or {}).get("azimut_deg")
        a1 = (e["apres"] or {}).get("azimut_deg")
        t.cercle(*b, 0.2, BLANC)
        for az, col in ((a0, ROUGE), (a1, CYAN)):
            if az is None:
                continue
            r = math.radians(float(az))
            t.fleche(b, [b[0] + 2.0 * math.sin(r), b[1] + 2.0 * math.cos(r)], col, 3)
        t.texte(*b, f"face {a0}° (rouge) -> {a1}° (cyan)", BLANC)
    t.echelle()
    d = ""
    if a is not None and nat == "deplacement":
        d = f" ; {math.hypot(b[0] - a[0], b[1] - a[1]):.2f} m"
    lignes = [f"#{rang:02d}  {e['id']} ({e.get('classe') or e['famille']}) — {nat}{d} — confiance {e['conf']}",
              f"règles : {', '.join(e['regles'])}",
              f"preuves : {', '.join(e['observations'][:6]) or '-'}",
              f"motif : {e['motif']}",
              f"revue : {(e.get('revue') or '-')[:200]}",
              "fond : ortho PCRS 5 cm du 2022-05-10 (antérieure aux travaux) ; jaune : arêtes des bordures 2026 décrites"]
    im = _legende(t.im, lignes)
    nom = f"{rang:02d}_{e['id']}_{nat}.jpg"
    im.save(dossier / nom, quality=88, optimize=True)
    return nom, im


def planches(sortie, S, J):
    dossier = sortie / "planches"
    dossier.mkdir(parents=True, exist_ok=True)
    for p in dossier.glob("*.jpg"):
        p.unlink()
    out, ims = [], []
    for k, e in enumerate(selection(J), 1):
        nom, im = planche(S, e, k, dossier)
        out.append({"rang": k, "id": e["id"], "nature": e["nature"], "fichier": f"planches/{nom}", "portee": e["portee"]})
        ims.append(im)
    if ims:
        w, h = ims[0].size[0] // 2, max(i.size[1] for i in ims) // 2
        cols = 3
        rows = int(math.ceil(len(ims) / cols))
        mos = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
        for k, im in enumerate(ims):
            mos.paste(im.resize((w, int(im.size[1] / 2))), ((k % cols) * w, (k // cols) * h))
        mos.save(dossier / "00_index.jpg", quality=85, optimize=True)
    return out
