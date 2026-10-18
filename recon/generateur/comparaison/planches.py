"""Planches de comparaison (≤ 1092 px, entrée native sans réduction), plan du site et gabarit de la grille d'écarts.

Par photo (photos_non_versionnees/planches/) :
- planche_<id8>.png (1056 × 1116 px, aire ≤ 1092²) : 4 panneaux de 528 px (vues de 1092 px réduites de moitié,
  lecture d'ensemble) : photo | rendu / superposition des contours (photo en cyan, rendu en magenta, communs en
  blanc) | arêtes du modèle projetées (pose initiale en jaune, pose affinée en vert) ;
- à la résolution native (1092 px, une tuile chacune) : vue_<id8>.png (photo), rendu_<id8>.png,
  superposition_<id8>.png, aretes_<id8>.png : ce sont elles qu'on regarde pour conclure sur un détail.
Synthèse du site : planche_synthese.png (vignettes appariées photo | rendu, 3 paires par ligne, ≤ 1092 px).
Plan du site (sans photo) : plan_site.png (modèle vu de dessus, positions GNSS et affinées, cônes de vue).
"""
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import modele as MO

COUL_Q = {"+x": (230, 120, 30), "-x": (40, 120, 230), "gauche": (40, 170, 70), "droite": (200, 50, 160)}


def police(t=14):
    for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf"):
        if Path(f).exists():
            return ImageFont.truetype(f, t)
    return ImageFont.load_default()


def contours(img):
    g = cv2.cvtColor(np.asarray(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    g = cv2.GaussianBlur(g, (0, 0), 1.2)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    hi = float(np.percentile(np.hypot(gx, gy), 88))
    return cv2.Canny(g, 0.4 * hi, hi, apertureSize=3, L2gradient=True) > 0


def superposition(photo, rendu, masque):
    """Photo assombrie en gris ; contours de la photo en cyan, du rendu en magenta, communs (à 2 px) en blanc."""
    a = np.asarray(photo.convert("L"), dtype=np.float32)
    base = np.repeat((a * 0.35)[..., None], 3, axis=2)
    cp = contours(photo) & masque
    cr = contours(rendu) & masque
    k = np.ones((5, 5), np.uint8)
    cp_d = cv2.dilate(cp.astype(np.uint8), k) > 0
    cr_d = cv2.dilate(cr.astype(np.uint8), k) > 0
    out = base.copy()
    out[cp] = (0, 210, 230)
    out[cr] = (235, 50, 210)
    out[(cp & cr_d) | (cr & cp_d)] = (255, 255, 255)
    out[~masque] *= 0.5
    st = {"contours_photo_px": int(cp.sum()), "contours_rendu_px": int(cr.sum()),
          "rendu_retrouves_dans_photo": round(float((cr & cp_d).sum() / max(1, cr.sum())), 4),
          "photo_retrouves_dans_rendu": round(float((cp & cr_d).sum() / max(1, cp.sum())), 4)}
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)), st


def planche_photo(dst, titre, panneaux, legendes):
    """4 panneaux (PIL, même taille) réduits à 528 px, en 2 × 2, titre ; aire ≤ 1092²."""
    c = 528
    ht, hl = 24, 18
    W, H = 2 * c, ht + 2 * (hl + c)
    pl = Image.new("RGB", (W, H), (22, 22, 26))
    d = ImageDraw.Draw(pl)
    d.text((6, 4), titre[:175], fill=(235, 235, 235), font=police(13))
    for k, (im, leg) in enumerate(zip(panneaux, legendes)):
        x, y = (k % 2) * c, ht + (k // 2) * (hl + c)
        d.text((x + 4, y + 2), leg[:80], fill=(210, 210, 210), font=police(12))
        r = im.convert("RGB").resize((c, int(round(im.size[1] * c / im.size[0]))), Image.LANCZOS)
        pl.paste(r, (x, y + hl))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    pl.save(dst)
    assert W * H <= 1092 * 1092 and max(W, H) <= 1568
    return dst


def planche_synthese(dst, titre, paires):
    """Vignettes appariées photo | rendu (176 px), 3 paires par ligne ; paires = [(photo, rendu, légende)]."""
    v, gap, hl, ht = 176, 8, 16, 26
    par_ligne = 3
    lignes = max(1, math.ceil(len(paires) / par_ligne))
    W = par_ligne * (2 * v) + (par_ligne - 1) * gap
    H = ht + lignes * (hl + v + gap)
    if W * H > 1092 * 1092:
        raise RuntimeError("planche de synthèse trop grande")
    pl = Image.new("RGB", (W, H), (22, 22, 26))
    d = ImageDraw.Draw(pl)
    d.text((6, 5), titre[:170], fill=(235, 235, 235), font=police(13))
    for k, (ph, re, leg) in enumerate(paires):
        x = (k % par_ligne) * (2 * v + gap)
        y = ht + (k // par_ligne) * (hl + v + gap)
        d.text((x + 2, y + 1), leg[:58], fill=(210, 210, 210), font=police(11))
        for j, im in enumerate((ph, re)):
            if im is None:
                continue
            r = im.convert("RGB").resize((v, int(round(im.size[1] * v / im.size[0]))), Image.LANCZOS)
            pl.paste(r, (x + j * v, y + hl))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    pl.save(dst)
    return dst


def plan_site(dst, modele, poses, titre, m_par_px=None):
    """Plan (repère du modèle, s vers la droite, t vers le haut) : faces du modèle par classe, positions GNSS (cercle
    creux) et affinées (disque), cônes de vue colorés par quadrant, identifiants."""
    xs = [modele.s_min, modele.s_max] + [p["camera_initiale"]["C_modele"][0] for p in poses]
    ys = [modele.t_min, modele.t_max] + [p["camera_initiale"]["C_modele"][1] for p in poses]
    x0, x1 = min(xs) - 12, max(xs) + 12
    y0, y1 = min(ys) - 12, max(ys) + 12
    k = m_par_px or max((x1 - x0) / 1060.0, (y1 - y0) / 1000.0, 0.05)
    W, H = int((x1 - x0) / k) + 1, int((y1 - y0) / k) + 1 + 30
    im = Image.new("RGB", (W, H), (245, 244, 238))
    d = ImageDraw.Draw(im)

    def px(x, y):
        return ((x - x0) / k, 30 + (y1 - y) / k)

    for poly, cls in modele.faces_plan():
        d.polygon([px(*q) for q in poly], fill=MO.COULEURS_CLASSES.get(cls, (180, 180, 180)))
    P, _, typ = modele.aretes()
    for q, t in zip(P[::2], typ[::2]):
        if t == 3:
            x, y = px(q[0], q[1])
            d.point((x, y), fill=(255, 255, 255))
    for p in poses:
        q = p["vue"]["quadrant"]
        col = COUL_Q.get(q, (0, 0, 0))
        ci, cf = p["camera_initiale"], p.get("camera_affinee") or p["camera_initiale"]
        for cam, plein in ((ci, False), (cf, True)):
            x, y = px(*cam["C_modele"][:2])
            r = 4
            d.ellipse((x - r, y - r, x + r, y + r), outline=col, fill=col if plein else None, width=2)
        x, y = px(*cf["C_modele"][:2])
        for s in (-1, 1):
            a = math.radians(cf["lacet_deg"] + s * cf["champ_h_deg"] / 2)
            d.line((x, y, x + 14 / k * math.cos(a), y - 14 / k * math.sin(a)), fill=col, width=1)
        a = math.radians(cf["lacet_deg"])
        d.line((x, y, x + 8 / k * math.cos(a), y - 8 / k * math.sin(a)), fill=col, width=2)
        xi, yi = px(*ci["C_modele"][:2])
        d.line((xi, yi, x, y), fill=(0, 0, 0), width=1)
        d.text((x + 6, y - 14), p["id8"], fill=(0, 0, 0), font=police(11))
    d.text((6, 6), titre[:160] + f"  —  1 px = {k:.3f} m ; s → droite, t ↑ ; cercle : GNSS, disque : affinée",
           fill=(20, 20, 20), font=police(12))
    if W * H > 1092 * 1092 or max(W, H) > 1568:
        f = min(math.sqrt(1092 * 1092 / (W * H)), 1568 / max(W, H))
        im = im.resize((int(W * f), int(H * f)), Image.LANCZOS)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)
    return dst


def gabarit_ecarts(site, sel, pose, modele, mesures_superposition):
    """Grille d'écarts d'une photo : contexte, mesures automatiques et rubriques à remplir par l'agent qui regarde
    les planches (constat : « conforme » | « différent » | « absent » | « en trop » | « non visible »)."""
    cam = pose.get("camera_affinee") or pose["camera_initiale"]
    # section du modèle regardée : point du sol au centre bas de l'image (rayon du pixel (W/2, 0,7 H))
    s_vise = min(max(cam["C_modele"][0] + 15.0 * math.cos(math.radians(cam["lacet_deg"])), modele.s_min), modele.s_max)
    prof = modele.profil(s_vise)
    voies = [b for b in prof["bandes"] if b["type"] == "voie_circulation"]
    rub = lambda modele_dit: {"modele": modele_dit, "constat": None, "detail": None}  # noqa: E731
    return {
        "id": sel["id"], "id8": sel["id8"], "date": sel["date"], "auteur": sel["auteur"], "licence": sel["licence"],
        "type": sel["type"], "porteur": sel["porteur"], "quadrant": sel["vue"]["quadrant"],
        "position_modele": sel["position_modele"],
        "mesures_automatiques": {"avant_affinage": pose.get("mesures_initiales"), "apres_affinage": pose.get("mesures_affinees"),
                                 "correction": pose.get("correction"), "confiance": pose.get("confiance"),
                                 "superposition_rendu_photo": mesures_superposition},
        "profil_modele_vise": prof,
        "grille": {
            "geometrie": {
                "nombre_de_voies": rub(f"{len(voies)} voie(s) : " + ", ".join(f"{b['bande']} {b['largeur_m']} m" for b in voies)),
                "largeurs_relatives": rub(" | ".join(f"{b['type']} {b['largeur_m']}" for b in prof["bandes"])),
                "terre_plein": rub([b["bande"] for b in prof["bandes"] if b["type"] in ("terre_plein", "zone_neutralisee")]),
                "ilots": rub("voir la description (évènements de profil)"),
                "bordures": rub(prof["bordures"]),
            },
            "marquages": rub("voir l2b/table_marques.json"),
            "materiaux": rub(sorted({b["materiau"] for b in prof["bandes"]})),
            "elements_manquants": [],
            "elements_en_trop": [],
        },
        "visibilite": None,
        "synthese": None,
    }
