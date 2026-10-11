"""Planches avant / après des 10 changements les plus significatifs de la résolution.

Chaque planche : à gauche l'ortho PCRS 2022 (5 cm, antérieure aux travaux 2025) avec, en jaune, les arêtes avant des
bordures 2026 de la description (base 0.3), l'avant en rouge et l'après en cyan ; à droite, pour un objet, jusqu'à
deux vues perspectives tirées des photos Panoramax à pose calée (les photos citées par la décision d'abord, puis
celles du 28/07/2026, puis les plus proches), avec l'axe vertical du mât à la position avant (rouge, « A ») et après
(cyan, « C »), ou la boîte de l'objet non instancié. Sélection : d'abord les décisions prises contre la cohérence
(RES-POS-007, RES-MQ-004), puis les décisions nouvelles ou modifiées par rapport à la résolution précédente, puis
les plus significatives (portée) ; un seul membre par groupe de support.

Les planches contiennent une imagerie tierce (ortho, photos) : elles restent locales (planches/*.jpg ignorés par git).
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from commun import O, abscisses, anneaux, point_a, repere
import marquages_couverture as MC

RES = 0.025
TAILLE_M = (20.0, 15.0)
N_PLANCHES = 10
QUOTAS = {"deplacement": 5, "non_instancie_absent_2026": 1, "recalage_fleche": 1, "retrait": 2, "arret_a_l_arete": 1,
          "reorientation": 1}
REGLES_CONTRE_COHERENCE = ("RES-POS-007", "RES-MQ-004")
NATURES_OBJET = ("deplacement", "non_instancie_absent_2026", "reorientation")
HAUTEURS = {"lampadaire": 6.0, "mat_camera": 6.0, "panneau": 2.6, "support_feux": 3.2, "poteau_reseau": 6.0,
            "feuillu": 5.0, "arbre": 5.0, "arbuste": 2.0, "conifere": 6.0, "souche": 0.5, "abri_bus": 2.5}
VIGNETTE = 300
ROUGE, CYAN, JAUNE, BLANC, VERT = (255, 60, 60), (0, 230, 255), (255, 220, 0), (255, 255, 255), (60, 255, 90)


def selection(J, n=N_PLANCHES):
    def prio(e):
        if any(r in e["regles"] for r in REGLES_CONTRE_COHERENCE):
            return 0
        if e.get("comparaison_r1") in ("nouvelle", "modifiee"):
            return 1
        return 2
    choisis, vus = [], []
    compte = {}
    for e in sorted(J.appliquees, key=lambda e: (prio(e), -e["portee"], e["famille"], e["id"])):
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
    def __init__(self, cx, cy, res=RES):
        w, h = TAILLE_M
        self.res = res
        self.w, self.h = w * res / RES, h * res / RES
        self.x0, self.y1 = cx - self.w / 2, cy + self.h / 2
        self.im = MC.ortho_rgb(cx - self.w / 2, cy - self.h / 2, cx + self.w / 2, cy + self.h / 2, res).convert("RGB")
        self.d = ImageDraw.Draw(self.im, "RGBA")
        self.fp = MC.police(13)

    def px(self, x, y):
        return ((x - self.x0) / self.res, (self.y1 - y) / self.res)

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
        r = r_m / self.res
        self.d.ellipse([u - r, v - r, u + r, v + r], outline=col, width=w)

    def croix(self, x, y, r_m, col, w=4):
        u, v = self.px(x, y)
        r = r_m / self.res
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
        L = (2.0 if self.res >= RES else 1.0) / self.res
        self.d.rectangle([12, H - 30, 12 + L, H - 24], fill=BLANC)
        self.d.text((12, H - 50), "2 m" if self.res >= RES else "1 m", fill=BLANC, font=self.fp, stroke_width=2,
                    stroke_fill=(0, 0, 0))
        self.d.line([W - 24, 40, W - 24, 14], fill=BLANC, width=3)
        self.d.text((W - 30, 42), "N", fill=BLANC, font=self.fp, stroke_width=2, stroke_fill=(0, 0, 0))


def _bordures(t, S):
    for f in S.base["bordures"]["features"]:
        P = repere(np.asarray(f["geometry"]["coordinates"], float)[:, :2])
        if (P[:, 0].max() < t.x0 or P[:, 0].min() > t.x0 + t.w or P[:, 1].max() < t.y1 - t.h or P[:, 1].min() > t.y1):
            continue
        t.ligne(P, JAUNE, 1)


def _lignes_decrites(t, S, sauf=()):
    """Lignes de marquage fabriquées de la description résolue (vert fin) : bords de voie réellement décrits."""
    for f in S.base["marquages"]["features"]:
        p = f["properties"]
        if p.get("classe") != "ligne" or p["id"] in sauf or (p.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        g = f["geometry"]
        parts = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for c in parts:
            P = repere(np.asarray(c, float)[:, :2])
            if (P[:, 0].max() < t.x0 or P[:, 0].min() > t.x0 + t.w or P[:, 1].max() < t.y1 - t.h or P[:, 1].min() > t.y1):
                continue
            t.ligne(P, VERT, 1)
            k = len(P) // 2
            u, v = t.px(*P[k])
            if 0 <= u < t.im.size[0] - 60 and 0 <= v < t.im.size[1]:
                t.d.text((u + 3, v + 2), p["id"], fill=VERT, font=t.fp, stroke_width=1, stroke_fill=(0, 0, 0))


def _geom_locale(g):
    if g["type"] == "LineString":
        return [repere(np.asarray(g["coordinates"], float)[:, :2])]
    if g["type"] == "MultiLineString":
        return [repere(np.asarray(c, float)[:, :2]) for c in g["coordinates"]]
    return [repere(r) for poly in anneaux(g) for r in poly]


# --------------------------------------------------------------------------- vues photo
class Photos:
    """Photos Panoramax à pose calée du catalogue de la cohérence (lecture seule), images chargées à la demande."""

    def __init__(self, mnt):
        import coherence_poses as PO
        self.PO = PO
        self.cat = [p for p in PO.catalogue() if str(p["plateforme"]).startswith("panoramax")]
        self.mnt = mnt
        self._img = {}

    def z(self, xy):
        return float(self.mnt(np.array([xy[0] + O[0]]), np.array([xy[1] + O[1]]))[0]) - O[2]

    def rgb(self, p):
        if p["id"] not in self._img:
            self._img = {p["id"]: np.asarray(self.PO.image_rgb(p)).astype(np.float32)}
        return self._img[p["id"]]

    def choisir(self, pts, h, cites, n=2, dmax=30.0):
        out = []
        for p in self.cat:
            cam = p["cam"]
            P = np.array([np.r_[q[:2], q[2]] for q in pts] + [np.r_[q[:2], q[2] + h] for q in pts])
            uv, ok, _ = cam.projeter(P)
            if not ok.all():
                continue
            d = float(min(np.hypot(q[0] - cam.C[0], q[1] - cam.C[1]) for q in pts))
            if d < 1.5 or d > dmax:
                continue
            out.append(((p["id"] not in cites, not str(p["date"]) >= "2026", round(d, 1), p["id"]), p, d))
        out.sort(key=lambda t: t[0])
        return [(p, d) for _, p, d in out[:n]]

    def vignette(self, p, A, C, h, mode, titre):
        from projection import camera_virtuelle, reechantillonner
        cam = p["cam"]
        A3 = np.r_[A[:2], self.z(A)]
        C3 = np.r_[C[:2], self.z(C)]
        P = np.array([A3, A3 + [0, 0, h], C3, C3 + [0, 0, h]])
        M = P.mean(axis=0)
        d3 = M - cam.C
        dist = float(np.linalg.norm(d3))
        azs = [math.degrees(math.atan2(q[0] - cam.C[0], q[1] - cam.C[1])) for q in (A3, C3)]
        sep = abs((azs[0] - azs[1] + 180) % 360 - 180)
        fov = float(np.clip(max(3.0 * sep, math.degrees(2 * math.atan((h * 0.7 + 1.0) / max(dist, 1.0)))), 8.0, 80.0))
        lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
        tan = math.degrees(math.atan2(d3[2], math.hypot(d3[0], d3[1])))
        cv = camera_virtuelle(cam, lac, tan, fov, VIGNETTE)
        img = reechantillonner(cam, self.rgb(p), cv)
        out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
        dr = ImageDraw.Draw(out)
        f = MC.police(12)
        reperes = (((A3, ROUGE, "A"), (C3, CYAN, "C")) if mode == "deplacement" else ((C3, ROUGE, "X"),))
        for X, col, lab in reperes:
            seg = X[None, :] + np.linspace(0.0, h, 41)[:, None] * np.array([0.0, 0.0, 1.0])
            uv, ok, _ = cv.projeter(seg)
            vis = ok & (uv[:, 0] >= -50) & (uv[:, 0] <= VIGNETTE + 50) & (uv[:, 1] >= -50) & (uv[:, 1] <= VIGNETTE + 50)
            pts = [tuple(q) for q, k in zip(uv, vis) if k]
            if len(pts) >= 2:
                dr.line(pts, fill=col, width=1)
                if vis[0]:
                    dr.line([(uv[0, 0] - 5, uv[0, 1]), (uv[0, 0] + 5, uv[0, 1])], fill=col, width=2)
                u1, v1 = pts[-1]
                dr.text((u1 + 3, max(16.0, v1 - 2)), lab, fill=col, font=f, stroke_width=1, stroke_fill=(0, 0, 0))
            if mode != "deplacement":
                ang = np.linspace(0, 2 * np.pi, 25)
                for zz in (0.0, h):
                    ring = np.c_[X[0] + 1.0 * np.cos(ang), X[1] + 1.0 * np.sin(ang), np.full(25, X[2] + zz)]
                    uvr, okr, _ = cv.projeter(ring)
                    pts = [tuple(q) for q, k in zip(uvr, okr) if k]
                    if len(pts) > 1:
                        dr.line(pts, fill=ROUGE, width=1)
        dr.rectangle([0, 0, VIGNETTE, 14], fill=(0, 0, 0))
        dr.text((3, 1), titre[:52], fill=BLANC, font=f)
        dr.rectangle([0, VIGNETTE - 14, VIGNETTE, VIGNETTE], fill=(0, 0, 0))
        dr.text((3, VIGNETTE - 13), f"{p['id']} {p['date']} d={dist:.1f} m fov {fov:.0f}°", fill=BLANC, font=f)
        return out, p


def _legende(im, lignes):
    W, H = im.size
    h = 21 * len(lignes) + 12
    out = Image.new("RGB", (W, H + h), (20, 20, 20))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f = MC.police(14)
    for k, l in enumerate(lignes):
        d.text((10, H + 6 + 21 * k), l[:150], fill=BLANC, font=f)
    return out


def _hauteur(S, e):
    """Hauteur de l'objet (paquet), sinon a priori par classe."""
    for fc in (S.mobilier, S.arbres):
        for f in fc["features"]:
            if f["properties"]["id"] == e["id"] and f["properties"].get("hauteur_m"):
                return float(f["properties"]["hauteur_m"])
    return HAUTEURS.get(e.get("classe") or "", 3.0)


def planche(S, e, rang, dossier, photos):
    a, b = e.get("xy_avant_local"), e["xy_apres_local"]
    cx, cy = (b if a is None else [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2])
    nat = e["nature"]
    d_m = math.hypot(b[0] - a[0], b[1] - a[1]) if (a is not None and nat == "deplacement") else None
    t = Toile(cx, cy, RES / 2 if (d_m is not None and d_m < 0.5) else RES)
    _bordures(t, S)
    if e["famille"] == "marquages":
        _lignes_decrites(t, S, sauf={e["id"]})
    F = {f["properties"]["id"]: f for f in S.base["marquages"]["features"]}
    if nat == "deplacement":
        t.cercle(*a, 0.25 if t.res >= RES else 0.12, ROUGE)
        t.cercle(*b, 0.25 if t.res >= RES else 0.12, CYAN)
        t.fleche(a, b, CYAN, 2)
        t.texte(*a, "avant (A)", ROUGE)
        t.texte(*b, "après (C)", CYAN)
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
    im = t.im
    vues = []
    if nat in NATURES_OBJET and photos is not None:
        h = _hauteur(S, e)
        A = a if a is not None else b
        cites = {o for o in e.get("observations", []) if str(o).startswith("pnx:")}
        pts = [np.r_[A[:2], photos.z(A)], np.r_[b[:2], photos.z(b)]]
        for p, d in photos.choisir(pts, h, cites):
            if nat == "deplacement":
                titre = f"{e['id']} : A rouge, C cyan"
            elif nat == "reorientation":
                rel = math.degrees(math.atan2(p["cam"].C[0] - b[0], p["cam"].C[1] - b[1])) % 360
                titre = f"{e['id']} : caméra au {rel:.0f}° (face {(e['apres'] or {}).get('azimut_deg')}°)"
            else:
                titre = f"{e['id']} : boîte (rouge)"
            v, p = photos.vignette(p, A, b, h, "deplacement" if nat == "deplacement" else "boite", titre)
            vues.append((v, p))
    if vues:
        W, H = im.size
        can = Image.new("RGB", (W + VIGNETTE, max(H, VIGNETTE * len(vues))), (20, 20, 20))
        can.paste(im, (0, 0))
        for k, (v, p) in enumerate(vues):
            can.paste(v, (W, k * VIGNETTE))
        im = can
    d = f" ; {d_m:.2f} m" if d_m is not None else ""
    lignes = [f"#{rang:02d}  {e['id']} ({e.get('classe') or e['famille']}) — {nat}{d} — confiance {e['conf']} — "
              f"par rapport à r1 : {e.get('comparaison_r1') or '-'}",
              f"règles : {', '.join(e['regles'])}",
              f"preuves : {', '.join(e['observations'][:6]) or '-'}",
              f"motif : {e['motif'][:145]}",
              f"revue : {(e.get('revue') or '-')[:145]}",
              f"seconde lecture : {(e.get('seconde_lecture') or '-')[:135]}",
              "fond : ortho PCRS 5 cm du 2022-05-10 (antérieure aux travaux) ; jaune : arêtes des bordures 2026"
              + (" ; vert : lignes de marquage décrites" if e["famille"] == "marquages" else "")
              + f" ; échelle {'1 m' if t.res < RES else '2 m'}"]
    if vues:
        lignes.append("photos : " + " ; ".join(p["attribution"] for _, p in vues))
    im = _legende(im, lignes)
    nom = f"av_ap_{rang:02d}_{e['id']}_{nat}.jpg"
    im.save(dossier / nom, quality=88, optimize=True)
    return nom, im, [p["id"] for _, p in vues]


def planches(sortie, S, J, mnt=None):
    dossier = sortie / "planches"
    dossier.mkdir(parents=True, exist_ok=True)
    for p in dossier.glob("*.jpg"):
        p.unlink()
    photos = None
    if mnt is not None:
        try:
            photos = Photos(mnt)
        except Exception as ex:          # catalogue indisponible : planches ortho seules
            print(f"planches : vues photo indisponibles ({type(ex).__name__})")
    out, ims = [], []
    for k, e in enumerate(selection(J), 1):
        nom, im, vues = planche(S, e, k, dossier, photos)
        out.append({"rang": k, "id": e["id"], "nature": e["nature"], "fichier": f"planches/{nom}", "portee": e["portee"],
                    "photos": vues, "comparaison_r1": e.get("comparaison_r1")})
        ims.append(im)
    if ims:
        w = max(i.size[0] for i in ims) // 2
        h = max(i.size[1] for i in ims) // 2
        cols = 2
        rows = int(math.ceil(len(ims) / cols))
        mos = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
        for k, im in enumerate(ims):
            mos.paste(im.resize((im.size[0] // 2, im.size[1] // 2)), ((k % cols) * w, (k // cols) * h))
        mos.save(dossier / "av_ap_00_index.jpg", quality=85, optimize=True)
    return out
