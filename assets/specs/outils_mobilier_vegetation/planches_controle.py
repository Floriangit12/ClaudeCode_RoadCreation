"""Planches de contrôle 1000x1000 (JPEG) du lot mobilier / bordures / végétation / CARLA :
extraits NATIFS des tuiles Panoramax (recadrés, jamais redimensionnés) à côté des gabarits 2D
dessinés à l'échelle depuis les spécifications (mobilier.json, bordures.json), et vignettes
officielles du catalogue CARLA (réduites) à côté des photos du site.

Usage : python3 assets/specs/outils_mobilier_vegetation/planches_controle.py [--carla-vignettes <dossier .webp>]
Sortie : assets/qa/mobilier_vegetation_carla/qa_0*.jpg
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import ASSETS, COULEURS, QA, REPO, SPECS  # noqa: E402
from donnees_mobilier import (T_119D, T_1149, T_2374, T_2AB4, T_31D1, T_5C0D, T_734A, T_9834, T_9FC8, T_A1FF,  # noqa: E402
                              T_AB4C, T_BC579, T_D888, T_DED0, T_E5D7, T_F8D9, T_FFC2, T_DD2A, T_B401, T_0508, T_7A18)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(s):
    try:
        return ImageFont.truetype(FONT, s)
    except Exception:
        return ImageFont.load_default()


def tuile(stem, rc):
    return REPO / "data" / "raw" / "panoramax" / "paquet_jardin" / "tiles" / f"{stem}_hd" / f"{stem}_hd_{rc}.jpg"


def extrait(stem, rc, x0, y0, w, h):
    """Extrait natif (aucun redimensionnement) d'une tuile 1000x1000."""
    im = Image.open(tuile(stem, rc)).convert("RGB")
    x0 = max(0, min(x0, im.width - w))
    y0 = max(0, min(y0, im.height - h))
    return im.crop((x0, y0, x0 + w, y0 + h))


def rgb(c):
    h = COULEURS.get(c, {}).get("srgb", "#808080").lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def dessiner_gabarit(elements, w, h, ppm, h0=None, z0=0.0, fond=(245, 245, 240), personne=True, titre=None, cote=None):
    """Élévation à l'échelle ppm (px/m) ; h0 = abscisse (m) du bord gauche ; grille de 1 m."""
    im = Image.new("RGB", (w, h), fond)
    d = ImageDraw.Draw(im)
    marge_bas = 28
    if h0 is None:
        h0 = -w / 2 / ppm
    X = lambda u: (u - h0) * ppm                                   # noqa: E731
    Z = lambda v: h - marge_bas - (v - z0) * ppm                   # noqa: E731
    # grille 1 m
    m = int(h0) - 1
    while X(m) < w:
        d.line([(X(m), 0), (X(m), h - marge_bas)], fill=(222, 222, 215))
        m += 1
    for k in range(0, int((h - marge_bas) / ppm) + 2):
        d.line([(0, Z(k)), (w, Z(k))], fill=(222, 222, 215))
    d.line([(0, Z(0)), (w, Z(0))], fill=(90, 90, 90), width=2)
    if personne:                                                   # silhouette 1,75 m
        px = h0 + (w / ppm) - 0.45
        d.rectangle([X(px - 0.2), Z(1.45), X(px + 0.2), Z(0.0)], fill=(150, 170, 200))
        r = 0.12 * ppm
        d.ellipse([X(px) - r, Z(1.75) - 0.0, X(px) + r, Z(1.75) + 2 * r], fill=(150, 170, 200))
    for e in elements:
        t = e["t"]
        col = rgb(e.get("c"))
        if t == "rect":
            d.rectangle([X(e["h0"]), Z(e["z1"]), X(e["h1"]), Z(e["z0"])], fill=col, outline=(40, 40, 40))
        elif t == "trap":
            c, z0_, z1_, d0, d1 = e["h"], e["z0"], e["z1"], e["d0"], e["d1"]
            d.polygon([(X(c - d0 / 2), Z(z0_)), (X(c + d0 / 2), Z(z0_)), (X(c + d1 / 2), Z(z1_)), (X(c - d1 / 2), Z(z1_))], fill=col, outline=(40, 40, 40))
        elif t == "line":
            pts = [(X(p[0]), Z(p[1])) for p in e["p"]]
            lw = max(2, int(e["w"] * ppm))
            d.line(pts, fill=(40, 40, 40), width=lw + 2)            # liseré : éléments clairs visibles sur fond clair
            d.line(pts, fill=col, width=lw)
        elif t == "circ":
            r = max(2, e["r"] * ppm)
            d.ellipse([X(e["h"]) - r, Z(e["z"]) - r, X(e["h"]) + r, Z(e["z"]) + r], fill=col, outline=(40, 40, 40))
        elif t == "poly":
            d.polygon([(X(p[0]), Z(p[1])) for p in e["p"]], fill=col, outline=(40, 40, 40))
    d.rectangle([0, h - marge_bas, w, h], fill=(0, 0, 0))
    if titre:
        d.text((4, h - marge_bas + 2), titre, fill=(255, 230, 120), font=font(13))
    if cote:
        d.text((4, 4), cote, fill=(60, 60, 60), font=font(12))
    return im


def legende(im, texte, couleur=(255, 230, 120), hauteur=30):
    d = ImageDraw.Draw(im)
    d.rectangle([0, im.height - hauteur, im.width, im.height], fill=(0, 0, 0))
    for j, ligne in enumerate(texte.split("\n")[:2]):
        d.text((4, im.height - hauteur + 1 + 14 * j), ligne, fill=couleur, font=font(12))
    return im


def planche(titre, cellules, cols, rows, sortie):
    W = 1000
    top = 34
    cw, ch = W // cols, (W - top) // rows
    img = Image.new("RGB", (W, W), (25, 25, 25))
    d = ImageDraw.Draw(img)
    d.text((8, 7), titre, fill=(255, 255, 255), font=font(17))
    for i, c in enumerate(cellules):
        r, k = divmod(i, cols)
        if c is None:
            continue
        cc = c.copy()
        cc.thumbnail((cw - 4, ch - 4))                              # sans effet sur les extraits déjà à la bonne taille
        img.paste(cc, (k * cw + 2 + (cw - 4 - cc.width) // 2, top + r * ch + 2 + (ch - 4 - cc.height) // 2))
    QA.mkdir(parents=True, exist_ok=True)
    img.save(QA / sortie, quality=85)
    return QA / sortie


def fiche(mob, nom):
    return next(f for f in mob["modeles"] if f["asset"] == nom)


def gab(mob, nom, w, h, ppm, h0=None, titre=None, personne=True, cote=None):
    f = fiche(mob, nom)
    return dessiner_gabarit(f["gabarit_2d"]["elements"], w, h, ppm, h0=h0, titre=titre or f"{nom} ({f['gabarit_2d']['plan']})", personne=personne, cote=cote)


def p1_eclairage(mob):
    cw, chh = 246, 440
    cells = [
        legende(extrait(T_1149, "r01_c02", 560, 200, cw, chh), "photo 2024-05-01 1149e115 r01_c02\ndouble crosse en T (îlot NO)"),
        legende(extrait(T_5C0D, "r01_c03", 0, 80, cw, chh), "photo 2024-08-24 5c0d1d39 r01_c03\ncrosse simple + cadre lumineux"),
        legende(extrait(T_F8D9, "r01_c03", 470, 110, cw, chh), "photo 2026-07-28 f8d91bb1 r01_c03\nmât droit LED (réf. 0456)"),
        legende(extrait(T_2374, "r01_c03", 130, 0, cw, chh), "photo 2025-05-18 2374105b r01_c03\nmât acier brun + bras (câbles)"),
    ]
    ppm = 32
    cells += [gab(mob, "candelabre_double_crosse", cw, chh, ppm, titre="spec : double crosse 12 m, 2 x 2,4 m"),
              gab(mob, "candelabre_crosse_simple", cw, chh, ppm, h0=-1.6, titre="spec : crosse simple 10,3 m, 2,1 m"),
              gab(mob, "candelabre_mat_droit_led", cw, chh, ppm, h0=-3.0, titre="spec : mât droit LED 8 m"),
              gab(mob, "mat_illumination_cable", cw, chh, ppm, h0=-1.6, titre="spec : mât brun 9 m, bras 4,5 m")]
    return planche("QA 01 — éclairage : photos (extraits natifs) / gabarits à l'échelle (grille 1 m, personne 1,75 m)", cells, 4, 2, "qa_01_eclairage.jpg")


def p2_transport(mob):
    cells = [
        legende(extrait(T_BC579, "r01_c03", 150, 150, 496, 433), "photo 2025-05-18 bc579b89 r01_c03 : abri M réso, poteau d'arrêt (disque M,\n« La Revirée », C1), corbeille couvercle jaune, distributeur sous l'abri"),
    ]
    ab = fiche(mob, "abri_bus_m_reso")["gabarit_2d"]["elements"]
    cells.append(dessiner_gabarit(ab, 496, 433, 80, h0=-2.6, titre="spec abri_bus_m_reso (XZ) 4,4 x 1,75 x 2,5 m + poteau d'arrêt 3,9 m"))
    t1 = extrait(T_734A, "r00_c03", 330, 560, 496, 440)
    cells.append(legende(t1, "photo 2025-05-18 734a0da6 r00_c03 : sommet du totem P+R\n(+38,6° à ≈ 4 m → ≈ 5-6 m de haut)"))
    # gabarits groupés : totem, poteau d'arrêt, corbeille, banc, potelet
    im = Image.new("RGB", (496, 433), (245, 245, 240))
    g1 = gab(mob, "totem_pr_smmag", 140, 433, 64, h0=-1.1, titre="totem 5,5 m", personne=True)
    g2 = gab(mob, "poteau_arret_m_reso", 120, 433, 64, h0=-0.9, titre="poteau 3,9 m", personne=False)
    g3 = gab(mob, "corbeille_cylindrique", 80, 433, 64, h0=-0.6, titre="corbeille", personne=False)
    g4 = gab(mob, "banc_bois_metal", 80, 433, 64, h0=-0.6, titre="banc (YZ)", personne=False)
    g5 = gab(mob, "potelet_noir", 76, 433, 64, h0=-0.6, titre="potelet", personne=False)
    x = 0
    for g in (g1, g2, g3, g4, g5):
        im.paste(g, (x, 0))
        x += g.width
    cells.append(im)
    return planche("QA 02 — transport : abri, poteau d'arrêt, totem P+R (photos natives / gabarits à l'échelle)", cells, 2, 2, "qa_02_transport.jpg")


def p3_mobilier(mob):
    cw, chh = 246, 440
    cells = [
        legende(extrait(T_734A, "r01_c01", 0, 380, cw, chh), "photo 734a0da6 r01_c01\nbarrière à croisillons"),
        legende(extrait(T_2374, "r01_c03", 660, 360, cw, chh), "photo 2374105b r01_c03\narceaux vélo"),
        legende(extrait(T_FFC2, "r01_c00", 280, 330, cw, chh), "photo ffc2e8ac r01_c00\nbarrière levante"),
        legende(extrait(T_D888, "r01_c01", 20, 460, cw, chh), "photo d88855f2 r01_c01 : armoire\nbeige, poteau d'incendie, poteau bois"),
    ]
    cells += [gab(mob, "barriere_croix_saint_andre", cw, chh, 120, h0=-1.0, titre="spec barrière 1,5 x 1,0 m"),
              dessiner_gabarit(fiche(mob, "arceau_velo")["gabarit_2d"]["elements"] + [dict(e, h0=e["h0"] if "h0" in e else 0) for e in []],
                               cw, chh, 120, h0=-0.9, titre="spec arceau 0,8 x 0,85 m"),
              gab(mob, "barriere_levante", cw, chh, 48, h0=-0.5, titre="spec barrière levante 4,4 m"),
              None]
    # dernière cellule : armoire technique + poteau d'incendie + armoire des feux
    im = Image.new("RGB", (cw, chh), (245, 245, 240))
    a = gab(mob, "armoire_technique", 80, chh, 100, h0=-0.4, titre="arm. tech.", personne=False)
    b = gab(mob, "poteau_incendie", 70, chh, 100, h0=-0.35, titre="PI", personne=False)
    c = gab(mob, "armoire_commande_feux", 96, chh, 100, h0=-0.6, titre="arm. feux", personne=False)
    im.paste(a, (0, 0)); im.paste(b, (80, 0)); im.paste(c, (150, 0))
    cells[-1] = im
    return planche("QA 03 — mobilier : photos (extraits natifs) / gabarits à l'échelle", cells, 4, 2, "qa_03_mobilier.jpg")


def p4_profils(bor):
    noms = ["T1", "T2", "T3", "T2_bateau", "A1", "A2", "I1", "I2", "IL", "P1", "P2", "P3", "CS1", "CS2", "CC1", "CC2", "QUAI_BUS", "PAVES_GRANIT"]
    cells = []
    mmpx = 2.4 / 1000.0                     # 2,4 mm par pixel
    for n in noms:
        p = bor["profils"][n]
        w, h = 196, 236
        im = Image.new("RGB", (w, h), (245, 245, 240))
        d = ImageDraw.Draw(im)
        for k in range(0, 60):              # grille 5 cm
            d.line([(10 + k * 0.05 / mmpx, 0), (10 + k * 0.05 / mmpx, h)], fill=(225, 225, 218))
            d.line([(0, h - 40 - k * 0.05 / mmpx), (w, h - 40 - k * 0.05 / mmpx)], fill=(225, 225, 218))
        pts = [(10 + u / mmpx, h - 40 - v / mmpx) for u, v in p["contour"]]
        d.polygon(pts, fill=(189, 187, 179), outline=(30, 30, 30))
        pe = p.get("pose_exemple")
        if pe and "vue_m" in pe:
            H = max(v for _, v in p["contour"])
            zr = h - 40 - (H - pe["vue_m"]) / mmpx
            d.line([(0, zr), (10, zr)], fill=(40, 40, 40), width=3)
            d.text((12 + p["contour"][-1][0] / mmpx, zr - 7), f"route (vue {pe['vue_m']:.3f})", fill=(120, 40, 40), font=font(10))
        d.rectangle([0, h - 36, w, h], fill=(0, 0, 0))
        d.text((4, h - 35), f"{n}  {p.get('section_cm', '')}", fill=(255, 230, 120), font=font(12))
        d.text((4, h - 19), p.get("famille", "")[:30], fill=(200, 200, 200), font=font(10))
        cells.append(im)
    return planche("QA 04 — profils de bordures (bordures.json), échelle commune 2,4 mm/px, grille 5 cm, face vue à gauche", cells, 5, 4, "qa_04_bordures_profils.jpg")


def p5_bordures_site():
    cw, chh = 329, 460
    cells = [
        legende(extrait(T_2374, "r01_c03", 0, 500, cw, chh), "2374105b r01_c03 : bordure de quai bus\n(tête claire, face inclinée) → QUAI_BUS"),
        legende(extrait(T_9834, "r01_c02", 0, 460, cw, chh), "9834f494 r01_c02 : TPC de Verdun NE\nbordure T2 claire, vue ≈ 0,15 → T2"),
        legende(extrait(T_2AB4, "r01_c03", 0, 470, cw, chh), "2ab4efbc r01_c03 : bordures basses de la\npiste bidirectionnelle → A2"),
        legende(extrait(T_119D, "r01_c00", 380, 440, cw, chh), "119d9094 r01_c00 : anneau de pavés de\ngranit (îlot B21a1) → PAVES_GRANIT"),
        legende(extrait(T_AB4C, "r01_c02", 380, 540, cw, chh), "ab4cfacd r01_c02 (2025-08) : bordure basse\nvers l'abaissé + BEV gris clair à plots"),
        legende(extrait(T_31D1, "r01_c03", 671, 540, cw, chh), "31d16b8e r01_c03 : BEV béton clair,\nbordures basses de piste (A2)"),
    ]
    return planche("QA 05 — bordures sur le site (extraits natifs 1000x1000) : profil retenu", cells, 3, 2, "qa_05_bordures_site.jpg")


def p6_vegetation():
    cw, chh = 329, 309
    cells = [
        legende(extrait(T_5C0D, "r01_c03", 671, 0, cw, chh), "cèdre de l'Atlas (angle Revirée) + poteau bois"),
        legende(extrait(T_119D, "r01_c00", 390, 0, cw, chh), "peupliers noirs (Verdun NE), ≈ 23 m"),
        legende(extrait(T_2AB4, "r01_c03", 430, 200, cw, chh), "cyprès d'Italie (privé) + haie taillée"),
        legende(extrait(T_DED0, "r01_c02", 420, 0, cw, chh), "pin sylvestre probable (écorce orange en tête)"),
        legende(extrait(T_9FC8, "r01_c03", 671, 250, cw, chh), "têtard (peuplier d'après l'inventaire)"),
        legende(extrait(T_E5D7, "r01_c04", 180, 380, cw, chh), "haie taillée persistante ≈ 1,8 m"),
        legende(extrait(T_FFC2, "r01_c00", 0, 300, cw, chh), "jeunes sujets 2025 + paillage minéral (2026-07)"),
        legende(extrait(T_F8D9, "r01_c02", 671, 380, cw, chh), "ganivelles (fond, à droite) des plantations 2025"),
        legende(extrait(T_D888, "r01_c01", 110, 260, cw, chh), "cèdre de l'Himalaya prob. (Vercors E), janvier"),
    ]
    return planche("QA 06 — végétation : essences et formes de référence (extraits natifs)", cells, 3, 3, "qa_06_vegetation.jpg")


def p7_plan():
    src = REPO / "data" / "raw" / "docs" / "panneau_150dpi.png"
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(src).convert("RGB").crop((3700, 1780, 4700, 2780))       # extrait natif 1000x1000 (150 dpi)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 1000, 34], fill=(0, 0, 0))
    d.text((8, 7), "QA 07 — plan projet 2025 (150 dpi, extrait natif, 3 fosses sur 5 par bande) : bande NO « Ac, Gt, Ac », TPC « Cs?, Alc, As », noue « Qc/Oc, Qc/Oc, Ul »",
           fill=(255, 255, 255), font=font(13))
    QA.mkdir(parents=True, exist_ok=True)
    im.save(QA / "qa_07_plan_jeunes_sujets.jpg", quality=85)
    return QA / "qa_07_plan_jeunes_sujets.jpg"


def p8_carla(vign: Path | None):
    cw, chh = 246, 302
    paires = [
        ("bench01", "banc_bois_metal\nproche (bois trop clair)", (T_734A, "r01_c01", 744, 380)),
        ("trashcan03", "corbeille_cylindrique\nsilhouette seulement", (T_BC579, "r01_c03", 700, 500)),
        ("busstop", "abri_bus_m_reso\ntypologie proche, aspect différent", (T_BC579, "r01_c03", 170, 300)),
        ("chainbarrierend", "potelet_noir (au fond, Ø 9 cm)\nproche, sans tête blanche", (T_A1FF, "r01_c00", 130, 300)),
        ("cypress_tree", "cyprès d'Italie (privé)\nproche", (T_2AB4, "r01_c03", 470, 180)),
        ("streetbarrier", "chantier rouge/blanc (K2)\nCARLA à éviter (modèle US)", (T_AB4C, "r01_c02", 120, 300)),
    ]
    cells = []
    for nom, txt, (stem, rc, x0, y0) in paires:
        f = vign / f"{nom}.webp" if vign else None
        if f and f.exists():
            im = Image.open(f).convert("RGB").crop((420, 0, 1500, 1080))
            im.thumbnail((cw, chh - 30))
            c = Image.new("RGB", (cw, chh), (40, 40, 40))
            c.paste(im, ((cw - im.width) // 2, 0))
            bp = {"cypress_tree": "cypresstree"}.get(nom, nom)              # fichier de vignette ≠ identifiant du blueprint
            cells.append(legende(c, f"CARLA static.prop.{bp}\n(vignette officielle, réduite)"))
        else:
            cells.append(legende(Image.new("RGB", (cw, chh), (60, 60, 60)), f"CARLA static.prop.{nom}\n(vignette non disponible)"))
        cells.append(legende(extrait(stem, rc, x0, y0, cw, chh), f"site : {txt}"))
    return planche("QA 08 — doublures CARLA (catalogue officiel des props) / réel du site", cells, 4, 3, "qa_08_carla_vs_reel.jpg")


def _plan_cypres(w, h):
    """Relèvements du cyprès d'Italie (V2) : rayons depuis 3 photos, emprise, conifères de l'atelier, candidats V1."""
    import math
    from commun import OBJETS
    im = Image.new("RGB", (w, h), (245, 245, 240))
    d = ImageDraw.Draw(im)
    x0, x1, y0, y1 = -330.0, 170.0, -260.0, 240.0                 # m (repère local)
    k = min(w / (x1 - x0), (h - 30) / (y1 - y0))
    P = lambda x, y: ((x - x0) * k, (y1 - y) * k)                  # noqa: E731
    d.rectangle([P(-150, 150), P(150, -150)], outline=(80, 80, 80), width=2)
    d.text(P(-148, 148), "emprise 300 m", fill=(80, 80, 80), font=font(11))
    arb = json.loads((OBJETS / "arbres.geojson").read_text())["features"]
    v1 = {"arbre_108", "arbre_139", "arbre_140", "arbre_143", "arbre_164"}
    for f in arb:
        q = f["properties"]
        if q.get("type") != "conifere":
            continue
        X, Y = P(q["x_local"], q["y_local"])
        r = 5 if q["id"] in v1 else 3
        d.ellipse([X - r, Y - r, X + r, Y + r], fill=(200, 40, 40) if q["id"] in v1 else (40, 120, 40))
    rayons = [((-53.94, -54.79), 289.4, "bc579b89"), ((-39.59, -39.60), 273.4, "2374105b"), ((-11.13, -6.19), 272.1, "2ab4efbc")]
    for (px, py), az, nom in rayons:
        a = math.radians(az)
        d.line([P(px, py), P(px + 420 * math.sin(a), py + 420 * math.cos(a))], fill=(30, 60, 200), width=2)
        X, Y = P(px, py)
        d.ellipse([X - 4, Y - 4, X + 4, Y + 4], fill=(30, 60, 200))
        d.text((X + 4, Y + 2), nom, fill=(30, 60, 200), font=font(10))
    d.text((4, 4), "rayons : relèvements du cyprès (photos)\nrouge : candidats V1 ; vert : conifères atelier", fill=(40, 40, 40), font=font(11))
    return legende(im, "cyprès d'Italie : rayons quasi parallèles vers\nl'ouest → hors emprise (V1 corrigée)")


def p9_v2(mob):
    """Planche V2 : corrections et ajouts vérifiés sur photos natives."""
    cw, chh = 330, 318
    arceau_gab = dessiner_gabarit(fiche(mob, "arceau_velo")["gabarit_2d"]["elements"] + [
        {"t": "circ", "h": 1.2, "z": 0.34, "r": 0.34, "c": "noir_9005"}], cw, chh, 260, h0=-0.55, personne=False,
        titre="V2 : arceau 0,65 x 0,82 anthracite + roue 0,68", cote="grille 1 m")
    cells = [
        legende(extrait(T_DD2A, "r01_c00", 300, 330, cw, chh), "2024-05-01 dd2a9c8c r01_c00 : arceaux\nanthracite, l/h ≈ 0,72 (ciel couvert)"),
        arceau_gab,
        legende(extrait("2025-01-12_a1ffea74-72b7-4ebc-a34d-e1930f71ecc0", "r01_c00", 600, 400, cw, chh), "2025-01 a1ffea74 : îlot effilé du Vercors,\nbordures hautes très claires → bordure_T3"),
        legende(extrait(T_5C0D, "r01_c04", 600, 200, cw, chh), "2024-08 5c0d1d39 : arbre pourpre (arbre_273)\n→ arbre_prunus_cerasifera_pissardii_moyen"),
        legende(extrait(T_9834, "r01_c04", 90, 160, cw, chh), "2025-05 9834f494 r01_c04 : même arbre\npourpre derrière la haie"),
        legende(extrait(T_7A18, "r00_c05", 0, 380, cw, chh), "2025-05 7a182db7 r00_c05 : houppier haut\nà l'emplacement du Populus alba (424)"),
        legende(extrait(T_B401, "r01_c04", 300, 300, cw, chh), "2024-05 b4013696 : haie = laurier-cerise\n(grandes feuilles vernissées)"),
        legende(extrait(T_0508, "r01_c04", 520, 120, cw, chh), "2026-07 05089869 : grand feuillu voisin des\nmagnolias → hauteurs 8-9 m rejetées (5 m)"),
        _plan_cypres(cw, chh),
    ]
    return planche("QA 09 — V2 : corrections vérifiées sur photos (arceaux, T3, essences, hauteurs, cyprès)", cells, 3, 3, "qa_09_v2_corrections.jpg")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--carla-vignettes", type=Path, default=None, help="dossier des vignettes .webp du catalogue CARLA (docs)")
    a = ap.parse_args()
    mob = json.loads((SPECS / "mobilier.json").read_text())
    bor = json.loads((SPECS / "bordures.json").read_text())
    for p in (p1_eclairage(mob), p2_transport(mob), p3_mobilier(mob), p4_profils(bor), p5_bordures_site(), p6_vegetation(), p7_plan(),
              p8_carla(a.carla_vignettes), p9_v2(mob)):
        print(p.relative_to(ASSETS.parent), p.stat().st_size)
