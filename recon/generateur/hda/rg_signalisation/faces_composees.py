# -*- coding: utf-8 -*-
"""Faces des panneaux à inscriptions de la scène (lot L6) : EB10, EB20, E42, D21, D42a, D42b, D43, D31, D41, C24b,
panonceaux M1, M5, M9z — dessinées avec PIL d'après le plan de signalisation (plan_signalisation.py, clé « faces »).

    python recon/generateur/hda/rg_signalisation/faces_composees.py <dossier l6 de la scène>

Couleurs relevées sur les faces officielles du catalogue (assets/lib/route_fr/panneaux, PDF Cerema détourés) : blanc
(255), noir (27, 25, 24), rouge (255, 0, 0), vert (0, 144, 53), bleu des panneaux D d'autoroute (0, 106, 179), bleu des
panneaux C (0, 0, 255), jaune des cartouches E42 (255, 237, 0). Compositions conformes aux principes de l'IISR5 (mentions
en capitales sur fond blanc pour les pôles locaux, fond vert pour les itinéraires, flèches ; D21 à pointe de flèche ;
EB10 à listel rouge, EB20 barré d'une bande rouge ; IISR5 art. 83, 99-2). Police : Bahnschrift (dessin DIN 1451), à
défaut des caractères L1 et L4 de l'IISR (non disponibles) : choix [G] déclaré. Les faces sont des fichiers de la
scène (recon/out, non versionnés), pas des signaux officiels.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

POLICE = Path("C:/Windows/Fonts/bahnschrift.ttf")          # lecture seule
BLANC, NOIR, ROUGE = (255, 255, 255, 255), (27, 25, 24, 255), (255, 0, 0, 255)
VERT, BLEU_D, BLEU_C, JAUNE = (0, 144, 53, 255), (0, 106, 179, 255), (0, 0, 255, 255), (255, 237, 0, 255)
PX_PAR_M = 512                                              # 1 m de panneau = 512 px (≤ 1600 px de côté)


def police(px, style="SemiBold"):
    f = ImageFont.truetype(str(POLICE), max(8, int(px)))
    try:
        f.set_variation_by_name(style)
    except (OSError, ValueError):
        pass
    return f


def _taille(l, h):
    s = PX_PAR_M if max(l, h) * PX_PAR_M <= 1600 else 1600 / max(l, h)
    return max(16, int(round(l * s))), max(16, int(round(h * s))), s


def _ajuster(d, txt, larg_px, haut_px, style="SemiBold"):
    """Police la plus grande qui fait tenir txt dans (larg_px, haut_px)."""
    px = haut_px
    while px > 8:
        f = police(px, style)
        b = d.textbbox((0, 0), txt, font=f)
        if b[2] - b[0] <= larg_px and b[3] - b[1] <= haut_px:
            return f, b
        px -= 2
    f = police(8, style)
    return f, d.textbbox((0, 0), txt, font=f)


def _texte_centre(d, txt, boite, couleur, style="SemiBold", espacement=0):
    x0, y0, x1, y1 = boite
    f, b = _ajuster(d, txt, x1 - x0, y1 - y0, style)
    w, h = b[2] - b[0], b[3] - b[1]
    d.text((x0 + (x1 - x0 - w) / 2 - b[0], y0 + (y1 - y0 - h) / 2 - b[1]), txt, font=f, fill=couleur)


def _cadre(img, fond, liseré, ep, rayon):
    d = ImageDraw.Draw(img)
    W, H = img.size
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=rayon, fill=liseré)
    d.rounded_rectangle((ep, ep, W - 1 - ep, H - 1 - ep), radius=max(1, rayon - ep), fill=fond)
    return d


def _fleche(d, cx, cy, taille, angle_deg, couleur, epaisseur=0.28):
    """Flèche pleine (tige + pointe) centrée en (cx, cy), longueur taille, angle depuis +x (sens trigonométrique,
    y image vers le bas)."""
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), -math.sin(a)
    vx, vy = -uy, ux
    L = taille
    e = taille * epaisseur / 2
    tete = taille * 0.45
    lt = taille * 0.42
    p0 = (cx - ux * L / 2, cy - uy * L / 2)
    pt = (cx + ux * L / 2, cy + uy * L / 2)
    pb = (pt[0] - ux * tete, pt[1] - uy * tete)
    poly = [(p0[0] + vx * e, p0[1] + vy * e), (pb[0] + vx * e, pb[1] + vy * e), (pb[0] + vx * lt, pb[1] + vy * lt), pt,
            (pb[0] - vx * lt, pb[1] - vy * lt), (pb[0] - vx * e, pb[1] - vy * e), (p0[0] - vx * e, p0[1] - vy * e)]
    d.polygon(poly, fill=couleur)


ANGLE_MVT = {"TAG": 180.0, "TD": 90.0, "TAD": 0.0}


def face_eb(f, W, H, s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ep = int(0.05 * s)
    d = _cadre(img, BLANC, ROUGE, ep, int(0.06 * s))
    m = ep + int(0.05 * s)
    _texte_centre(d, f["texte"].upper(), (m, m, W - m, H - m), NOIR)
    if f["type"] == "EB20":
        # bande rouge oblique (du bas à gauche au haut à droite), IISR5 art. 99-2
        e = 0.06 * s
        d.polygon([(ep, H - ep - e), (W - ep - e * 2.5, ep), (W - ep, ep), (W - ep, ep + e), (ep + e * 2.5, H - ep),
                   (ep, H - ep)], fill=ROUGE)
    return img


def face_e42(f, W, H, s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=int(0.04 * s), fill=JAUNE)
    m = int(0.03 * s)
    _texte_centre(d, f["texte"], (m, m, W - m, H - m), NOIR, style="Bold")
    return img


def face_d21(f, W, H, s):
    """D21 à pointe de flèche (la pointe indique la direction) ; mention en capitales noires sur fond blanc."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    p = H * 0.5
    gauche = f.get("pointe") == "gauche"
    if gauche:
        poly = [(0, H / 2), (p, 0), (W - 1, 0), (W - 1, H - 1), (p, H - 1)]
    else:
        poly = [(0, 0), (W - 1 - p, 0), (W - 1, H / 2), (W - 1 - p, H - 1), (0, H - 1)]
    d.polygon(poly, fill=NOIR)
    ep = 0.035 * s
    k = ep / math.sin(math.atan2(H / 2, p))
    if gauche:
        inner = [(k, H / 2), (p + ep * 0.4, ep), (W - 1 - ep, ep), (W - 1 - ep, H - 1 - ep), (p + ep * 0.4, H - 1 - ep)]
    else:
        inner = [(ep, ep), (W - 1 - p - ep * 0.4, ep), (W - 1 - k, H / 2), (W - 1 - p - ep * 0.4, H - 1 - ep), (ep, H - 1 - ep)]
    d.polygon(inner, fill=BLANC)
    m = int(0.05 * s)
    x0, x1 = (int(p + m), W - m) if gauche else (m, int(W - p - m))
    _texte_centre(d, f["texte"].upper(), (x0, m + int(ep), x1, H - m - int(ep)), NOIR)
    return img


def face_d43(f, W, H, s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fond = {"blanc": BLANC, "vert": VERT, "bleu": BLEU_D}.get(f.get("fond", "blanc"), BLANC)
    enc = NOIR if fond == BLANC else BLANC
    d = _cadre(img, fond, NOIR if fond == BLANC else BLANC, int(0.025 * s), int(0.05 * s))
    m = int(0.05 * s)
    fl = f.get("fleche", "TD")
    a = H - 2 * m
    if fl == "TAG":
        _fleche(d, m + a / 2, H / 2, a, 180.0, enc)
        _texte_centre(d, f["texte"].upper(), (m * 2 + a, m, W - m, H - m), enc)
    else:
        _fleche(d, W - m - a / 2, H / 2, a, ANGLE_MVT.get(fl, 90.0), enc)
        _texte_centre(d, f["texte"].upper(), (m, m, W - 2 * m - a, H - m), enc)
    return img


def _fleche_epaisse(d, x0, y0, x1, y1, ep, tete_l, tete_w, couleur):
    """Tige de (x0, y0) à la base de la pointe, pointe triangulaire en (x1, y1)."""
    L = math.hypot(x1 - x0, y1 - y0) or 1.0
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    vx, vy = -uy, ux
    bx, by = x1 - ux * tete_l, y1 - uy * tete_l
    d.polygon([(x0 + vx * ep / 2, y0 + vy * ep / 2), (bx + vx * ep / 2, by + vy * ep / 2),
               (bx - vx * ep / 2, by - vy * ep / 2), (x0 - vx * ep / 2, y0 - vy * ep / 2)], fill=couleur)
    d.polygon([(bx + vx * tete_w / 2, by + vy * tete_w / 2), (x1, y1), (bx - vx * tete_w / 2, by - vy * tete_w / 2)],
              fill=couleur)


def face_diagramme(f, W, H, s, giratoire=True):
    """D42b (giratoire) et D42a (carrefour complexe) : diagramme noir sur fond blanc, une flèche et une mention par
    branche (azimut relatif à l'usager : 90° = tout droit). Mentions au-dessus des flèches (gauche, haut, droite)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = _cadre(img, BLANC, NOIR, int(0.025 * s), int(0.05 * s))
    cx, cy = W / 2, H * 0.62
    r = min(W, H) * 0.11
    ep = max(4, int(0.055 * s))
    d.line([(cx, H - int(0.03 * s)), (cx, cy + (r if giratoire else 0))], fill=NOIR, width=ep)
    if giratoire:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=NOIR, width=ep)
    th = H * 0.11
    for b in f.get("branches") or []:
        az = float(b["azimut"]) % 360.0
        a = math.radians(az)
        ux, uy = math.cos(a), -math.sin(a)
        r0 = r if giratoire else 0.0
        l = min(W * 0.36, H * 0.34)
        x0, y0 = cx + ux * r0, cy + uy * r0
        x1, y1 = cx + ux * (r0 + l), cy + uy * (r0 + l)
        _fleche_epaisse(d, x0, y0, x1, y1, ep, ep * 2.2, ep * 3.0, NOIR)
        txt = str(b["texte"]).upper()
        m = 0.05 * s
        if 45.0 <= az <= 135.0:                    # tout droit : mention au-dessus de la pointe
            boite = (m, max(m, y1 - th - ep * 2.5), W - m, max(m + th, y1 - ep * 2.5))
        elif az < 45.0 or az > 315.0:              # à droite : au-dessus de la flèche, côté droit
            boite = (cx + r0 + ep, y1 - th - ep * 2.2, W - m, y1 - ep * 2.2)
        else:                                      # à gauche : au-dessus de la flèche, côté gauche
            boite = (m, y1 - th - ep * 2.2, cx - r0 - ep, y1 - ep * 2.2)
        _texte_centre(d, txt, boite, NOIR)
    return img


def face_c24b(f, W, H, s):
    """C24b : une flèche d'affectation par voie, au-dessus de l'axe de la voie (IISR5 art. 72-3)."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=int(0.03 * s), fill=BLEU_C)
    voies = f.get("voies") or ["TD"]
    n = len(voies)
    marge = 0.06 * W
    pas = (W - 2 * marge) / n
    ep = max(4, int(W * 0.055 / max(1, n / 2)))
    tl, tw = H * 0.13, ep * 2.6
    base, haut, mid = H * 0.92, H * 0.10, H * 0.52
    for k, v in enumerate(voies):
        cx = marge + pas * (k + 0.5)
        dirs = {"TD": [90], "TAG": [180], "TAD": [0], "TD_TAD": [90, 0], "TD_TAG": [90, 180]}.get(v, [90])
        if 90 in dirs:
            _fleche_epaisse(d, cx, base, cx, haut, ep, tl, tw, BLANC)
        else:
            d.rectangle((cx - ep / 2, mid, cx + ep / 2, base), fill=BLANC)
        for a in dirs:
            if a == 90:
                continue
            sx = -1 if a == 180 else 1
            L = min(pas * 0.45, (mid - haut))
            _fleche_epaisse(d, cx, mid + ep / 2, cx + sx * L * 0.75, mid - L * 0.75, ep, tl * 0.8, tw, BLANC)
    return img


def face_d31(f, W, H, s):
    """D31d / D41a : registre blanc du numéro de sortie et de la flèche, registre vert (ou blanc) des destinations."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    h1 = H * 0.36
    ep = int(0.03 * s)
    d.rounded_rectangle((0, 0, W - 1, int(h1)), radius=int(0.05 * s), fill=NOIR)
    d.rounded_rectangle((ep, ep, W - 1 - ep, int(h1) - ep), radius=int(0.04 * s), fill=BLANC)
    m = int(0.06 * s)
    if f.get("numero"):
        bw = W * 0.38
        d.rounded_rectangle((m, m, m + bw, h1 - m), radius=int((h1 - 2 * m) / 2), outline=NOIR, width=ep)
        _texte_centre(d, f"SORTIE {f['numero']}", (m * 2, m * 1.4, m + bw - m, h1 - m * 1.4), NOIR)
    if f["type"] == "D41" and f.get("distance"):
        _texte_centre(d, f"{f['distance']} m", (W * 0.45, m * 1.3, W * 0.75, h1 - m * 1.3), NOIR)
    a = h1 - 2 * m
    _fleche(d, W - m - a / 2, h1 / 2, a, -45.0 if f["type"] == "D31" else 90.0, NOIR)
    y = h1 + ep * 2
    dests = f.get("destinations") or []
    hh = (H - y) / max(1, len(dests))
    for k, t in enumerate(dests):
        fond = VERT if k == 0 else BLANC
        y0, y1 = int(y + k * hh), int(y + (k + 1) * hh - ep)
        d.rounded_rectangle((0, y0, W - 1, y1), radius=int(0.05 * s), fill=NOIR if fond == BLANC else BLANC)
        d.rounded_rectangle((ep, y0 + ep, W - 1 - ep, y1 - ep), radius=int(0.04 * s), fill=fond)
        _texte_centre(d, str(t).upper(), (m, y0 + m, W - m, y1 - m), BLANC if fond == VERT else NOIR)
    return img


def face_panonceau(f, W, H, s):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = _cadre(img, BLANC, NOIR, int(0.02 * s), int(0.03 * s))
    m = int(0.04 * s)
    _texte_centre(d, f["texte"], (m, m, W - m, H - m), NOIR)
    return img


def face_d62(f, W, H, s):
    """D62c : confirmation de filante au-dessus des voies : registre vert, mention, une flèche vers le bas par voie."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = _cadre(img, VERT, BLANC, int(0.03 * s), int(0.06 * s))
    m = int(0.08 * s)
    _texte_centre(d, str(f["texte"]).upper(), (m, m, W - m, int(H * 0.55)), BLANC)
    n = max(1, int(f.get("voies") or 1))
    pas = (W - 2 * m) / n
    for k in range(n):
        cx = m + pas * (k + 0.5)
        _fleche_epaisse(d, cx, H * 0.60, cx, H - m, max(4, int(0.05 * s)), H * 0.12, H * 0.16, BLANC)
    return img


DESSINS = {"D62": face_d62, "EB10": face_eb, "EB20": face_eb, "E42": face_e42, "D21": face_d21, "D43": face_d43,
           "D42b": lambda f, W, H, s: face_diagramme(f, W, H, s, True),
           "D42a": lambda f, W, H, s: face_diagramme(f, W, H, s, False),
           "C24b": face_c24b, "D31": face_d31, "D41": face_d31, "panonceau": face_panonceau}


def dessiner(faces, dossier_l6):
    """Écrit chaque face (PNG RGBA, alpha hors du contour) ; renvoie {fichier: (largeur px, hauteur px)}."""
    out = {}
    for f in faces:
        W, H, s = _taille(f["l"], f["h"])
        fn = DESSINS.get(f["type"])
        if fn is None:
            raise SystemExit(f"face composée sans dessin : {f['type']}")
        img = fn(f, W, H, s)
        cible = Path(dossier_l6) / f["fichier"]
        cible.parent.mkdir(parents=True, exist_ok=True)
        img.save(cible, optimize=False)
        out[f["fichier"]] = [W, H]
    return out


if __name__ == "__main__":
    d = Path(sys.argv[1])
    plan = json.loads((d / "plan_signalisation.json").read_text(encoding="utf-8"))
    print(dessiner(plan["faces"], d))
