#!/usr/bin/env python3
"""Planches de contrôle 1000x1000 : face rasterisée (assets/specs/panneaux/faces) à côté d'extraits
des photos Panoramax du site montrant le MÊME panneau (data/raw/panoramax/...).

Sortie : assets/qa/panneaux_feux/<nom>.jpg (JPEG q85, 1000x1000).
Les extraits sont pris dans l'image HD d'origine (coordonnées pixel HD : boîtes des annotations
Panoramax ou relevées sur les tuiles 1000x1000), agrandis pour remplir leur cadre.
Usage : python3 assets/specs/panneaux/planches_controle.py [--seulement NOM,...]
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
FACES = ICI / "faces"
PX = RACINE / "data/raw/panoramax"
SORTIE = RACINE / "assets/qa/panneaux_feux"
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def photo(nom):
    for d in (PX / "paquet_jardin", PX / "complements"):
        c = sorted(d.glob(f"{nom}*_hd.jpg"))
        if c:
            return c[0]
    raise FileNotFoundError(nom)


# nom de planche : (titre, [faces], [(photo, (x0, y0, x1, y1) en px HD, légende)])
PLANCHES = {
    "B21a1": ("panneau_B21a1 — disque B21a1 Ø ≈ 450 sur balise d'îlot souple", ["B21a1"], [
        ("2025-05-18_119d9094", (505, 1525, 625, 1645), "2025-05-18 119d9094 : îlot pavé (corps blanc, embase noire)"),
        ("2025-05-18_31d16b8e", (213, 1509, 273, 1569), "2025-05-18 31d16b8e (annotation FR:B21a1)")]),
    "J5": ("panneau_J5 — balise de tête d'îlot (carré 700 probable)", ["J5"], [
        ("2025-08-31_fdc59178", (560, 1040, 780, 1260), "2025-08-31 fdc59178 : nez du TPC de Verdun NE"),
        ("2025-05-18_734a0da6", (365, 1526, 455, 1616), "2025-05-18 734a0da6 (annotation FR:J5)")]),
    "C113": ("panneau_C113 — piste cyclable conseillée (carré 500)", ["C113"], [
        ("2025-08-31_78424004", (3020, 430, 3400, 810), "2025-08-31 78424004 (annotation FR:C113)"),
        ("2025-05-18_e5d79de9", (4785, 1308, 4945, 1468), "2025-05-18 e5d79de9 : début piste NE")]),
    "mat_reviree_C114_AB3a_M9c": ("Mât chemin du Ruisseau : C114 + AB3a + M9c", ["C114", "AB3a", "M9c"], [
        ("2025-08-31_10ec04d5", (3700, 940, 3960, 1250), "2025-08-31 10ec04d5 (annotations FR:C114, FR:AB3a)"),
        ("2025-05-18_e5d79de9", (4110, 1330, 4260, 1480), "2025-05-18 e5d79de9 (annotation FR:C114)")]),
    "mats_acces_NE_B2b_B1_B2a_AB3a": ("Accès NE : mât B2b + B1 et mât B2a + AB3a + M9c", ["B2b", "B1", "B2a", "AB3a", "M9c"], [
        ("2025-08-31_bb9c05ff", (2250, 690, 2550, 1170), "2025-08-31 bb9c05ff (annotations B2b, B1, B2a, AB3a)"),
        ("2025-08-31_9ef861d4", (3440, 340, 3760, 780), "2025-08-31 9ef861d4 (annotation FR:B2a)")]),
    "AB3a_AB4_allee_horloge": ("Sortie allée des Mitaillères / L'Horloge : AB3a et AB4 (STOP)", ["AB3a", "AB4"], [
        ("2026-07-28_f8d91bb1", (3520, 1395, 3640, 1515), "2026-07-28 f8d91bb1 : AB3a (annotation FR:AB3)"),
        ("2026-07-28_f8d91bb1", (3420, 1395, 3500, 1475), "2026-07-28 f8d91bb1 : AB4 au loin (≈ 1,3°)")]),
    "B1_horloge": ("panneau_B1 — sens interdit (sortie parking L'Horloge, gamme miniature probable)", ["B1"], [
        ("2026-07-28_ffc2e8ac", (700, 1290, 865, 1455), "2026-07-28 ffc2e8ac (annotation FR:B1)"),
        ("2026-07-28_05089869", (36, 1336, 116, 1416), "2026-07-28 05089869 (annotation FR:B1)")]),
    "B6a1_C13a": ("B6a1 + C13a (portrait observé ; carré IISR en bas), candélabre 0456", ["B6a1", "C13a_portrait", "C13a"], [
        ("2026-07-28_ded07efa", (5560, 1250, 5760, 1450), "2026-07-28 ded07efa : B6a1 + C13a (portrait)"),
        ("2026-07-28_ded07efa", (1955, 1320, 2075, 1440), "2026-07-28 ded07efa : B6a1 parking L'Horloge")]),
    "A17": ("panneau_A17 — annonce de feux (triangle 700) sur candélabre, approche NE", ["A17"], [
        ("2025-08-31_f6297e9f", (2400, 820, 2820, 1240), "2025-08-31 f6297e9f (complément, annotation FR:A17)")]),
    "M12a": ("panneau_M12a (probable) — panonceau sous le feu du Vercors", ["M12a"], [
        ("2025-01-12_a1ffea74", (820, 1460, 920, 1560), "2025-01-12 a1ffea74 : panonceau triangulaire (illisible)")]),
    "D21a": ("panneau_D21a_la_reviree_college + panneau_D21a_commerces_reviree", ["D21a_la_reviree_college", "D21a_commerces_reviree"], [
        ("2025-08-31_ab4cfacd", (2225, 850, 2485, 1050), "2025-08-31 ab4cfacd : refuge de la Revirée")]),
    "plaque_rue": ("plaque_rue_avenue_de_verdun — sur le mât de feux n° 3150", ["plaque_rue_avenue_de_verdun"], [
        ("2024-08-24_2ab4efbc", (3850, 1100, 4100, 1350), "2024-08-24 2ab4efbc")]),
    "chantier_B2b_AK5_chevrons": ("Chantier (scénarios travaux) : B2b fond jaune, AK5, chevrons", ["B2b_temporaire", "AK5", "balise_chevrons_chantier"], [
        ("2025-08-31_1d999186", (85, 1027, 185, 1127), "2025-08-31 1d999186 : B2b sur fond jaune"),
        ("2020-05-21_0fe67f82", (1750, 1135, 1910, 1295), "2020-05-21 0fe67f82 : AK5 sur chevalet"),
        ("2025-08-31_ab4cfacd", (1930, 1110, 2170, 1290), "2025-08-31 ab4cfacd : chevrons")]),
}


def coller(fond, im, boite):
    x0, y0, x1, y1 = boite
    im = im.copy()
    k = min((x1 - x0) / im.size[0], (y1 - y0) / im.size[1])
    im = im.resize((max(1, int(im.size[0] * k)), max(1, int(im.size[1] * k))), Image.LANCZOS)
    pos = (x0 + (x1 - x0 - im.size[0]) // 2, y0 + (y1 - y0 - im.size[1]) // 2)
    if im.mode == "RGBA":
        fond.paste(im, pos, im)
    else:
        fond.paste(im, pos)
    return pos, im.size


def planche(nom, titre, faces, photos):
    W = 1000
    can = Image.new("RGB", (W, W), (40, 44, 48))
    d = ImageDraw.Draw(can)
    d.text((14, 12), titre, font=ImageFont.truetype(FB, 20), fill=(240, 240, 240))
    d.text((14, 40), "gauche : face rasterisée (assets/specs/panneaux/faces)   droite : photo réelle du site",
           font=ImageFont.truetype(F, 14), fill=(180, 180, 180))
    # colonne faces
    d.rectangle((10, 66, 380, 990), fill=(128, 132, 136))
    n = len(faces)
    h = (990 - 66 - 10) // n
    for i, f in enumerate(faces):
        y0 = 72 + i * h
        im = Image.open(FACES / f"{f}.png").convert("RGBA")
        coller(can, im, (24, y0 + 4, 366, y0 + h - 30))
        d.text((24, y0 + h - 26), f"{f}.png  {im.size[0]}x{im.size[1]}", font=ImageFont.truetype(F, 14), fill=(20, 20, 20))
    # colonne photos
    m = len(photos)
    hp = (990 - 66 - 10) // m
    for j, (nm, box, leg) in enumerate(photos):
        y0 = 66 + j * (hp + 5)
        src = Image.open(photo(nm)).convert("RGB").crop(box)
        coller(can, src, (392, y0, 990, y0 + hp - 26))
        d.text((396, y0 + hp - 22), leg + f"  [px HD {box[0]}-{box[2]} x {box[1]}-{box[3]}]",
               font=ImageFont.truetype(F, 13), fill=(230, 230, 230))
    SORTIE.mkdir(parents=True, exist_ok=True)
    out = SORTIE / f"planche_{nom}.jpg"
    can.save(out, quality=85, optimize=True)
    return out


# ------------------------------------------------------------------ feux
FEUX_TYPES = [
    ("2025-05-18_e5d79de9", (4280, 980, 4760, 1460), "R11v de dos : 3 modules gris clair, visières noires"),
    ("2025-05-18_9834f494", (2395, 1245, 2525, 1375), "R11v de face (approche NE, au vert), mât sombre"),
    ("2025-05-18_e5d79de9", (4320, 1320, 4510, 1510), "R12 horizontal : 2 figurines côte à côte"),
    ("2024-05-01_3fc0ff2e", (3620, 1100, 4120, 1600), "R12 en module rond (rouge) + tête masquée (2024)"),
    ("2025-05-18_e5d79de9", (4340, 1560, 4660, 1880), "répétiteur Ø 100, bouton, fourreau jaune"),
    ("2025-05-18_31d16b8e", (1960, 1040, 2340, 1660), "mât à crosse, caméra dôme, R11v"),
]


def planche_feux_types():
    can = Image.new("RGB", (1000, 1000), (40, 44, 48))
    d = ImageDraw.Draw(can)
    d.text((14, 12), "Feux du carrefour : types observés (feux.json)", font=ImageFont.truetype(FB, 20), fill=(240, 240, 240))
    for k, (nm, box, leg) in enumerate(FEUX_TYPES):
        c, r = k % 3, k // 3
        x0, y0 = 8 + c * 330, 50 + r * 475
        src = Image.open(photo(nm)).convert("RGB").crop(box)
        coller(can, src, (x0, y0, x0 + 322, y0 + 420))
        d.text((x0 + 2, y0 + 424), leg, font=ImageFont.truetype(F, 12), fill=(230, 230, 230))
        d.text((x0 + 2, y0 + 440), f"{nm} [HD {box[0]}-{box[2]} x {box[1]}-{box[3]}]", font=ImageFont.truetype(F, 11), fill=(170, 170, 170))
    out = SORTIE / "planche_feux_types.jpg"
    can.save(out, quality=85, optimize=True)
    return out


def planche_feux_mesures():
    """Mât feu_NE_droite (angle Revirée) : hauteurs mesurées sur la photo 360° e5d79de9
    (caméra à d = 2,505 m du mât, hauteur caméra 2,06 m, calées sur le pied et le sommet 3,4 m du LiDAR)."""
    import math
    box = (3750, 950, 5150, 2350)
    k = 1000 / (box[2] - box[0])
    src = Image.open(photo("2025-05-18_e5d79de9")).convert("RGB").crop(box).resize((1000, 1000), Image.LANCZOS)
    d = ImageDraw.Draw(src)
    D, HC, H = 2.505, 2.06, 2880

    def y_de_h(h):
        elev = math.degrees(math.atan((h - HC) / D))
        return ((0.5 - elev / 180) * H - box[1]) * k
    for h in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
        y = y_de_h(h)
        d.line((470, y, 600, y), fill=(255, 255, 0), width=1)
        d.text((605, y - 7), f"{h:.1f} m", font=ImageFont.truetype(F, 14), fill=(255, 255, 0))
    for (a, b, lab, col) in [(2.37, 3.47, "tête R11v 2,37-3,47", (255, 80, 80)), (1.98, 2.28, "R12 1,98-2,28", (80, 255, 120)),
                             (1.14, 1.65, "répétiteur 1,14-1,65", (80, 200, 255)), (0.93, 1.08, "bouton 0,93-1,08", (255, 160, 60)),
                             (0.58, 0.93, "fourreau 0,58-0,93", (255, 255, 255))]:
        ya, yb = y_de_h(b), y_de_h(a)
        d.rectangle((300, ya, 330, yb), outline=col, width=3)
        d.text((150, (ya + yb) / 2 - 7), lab, font=ImageFont.truetype(F, 13), fill=col)
    d.rectangle((0, 0, 1000, 34), fill=(30, 30, 30))
    d.text((10, 8), "feu_NE_droite (angle Revirée) — hauteurs mesurées, photo 360° 2025-05-18 e5d79de9", font=ImageFont.truetype(FB, 16), fill=(240, 240, 240))
    out = SORTIE / "planche_feux_mesures_mat_NE_droite.jpg"
    src.save(out, quality=85, optimize=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seulement")
    a = ap.parse_args()
    for nom, (titre, faces, photos) in PLANCHES.items():
        if a.seulement and nom not in a.seulement.split(","):
            continue
        print(planche(nom, titre, faces, photos).relative_to(RACINE))
    if not a.seulement or "feux" in a.seulement:
        print(planche_feux_types().relative_to(RACINE))
        print(planche_feux_mesures().relative_to(RACINE))


if __name__ == "__main__":
    main()
