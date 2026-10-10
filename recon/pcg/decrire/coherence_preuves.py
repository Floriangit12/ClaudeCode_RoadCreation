"""Preuves des corrections du solveur de cohérence : planches Panoramax + ortho 2022, triangulation.

Planche d'une correction (déplacement > 0,3 m ou réorientation > 20°) :
- 2 à 4 photos Panoramax CALÉES (poses acceptées de enrichi/poses/poses.json) dont la date rend
  l'objet valide (objet inchangé : toute date ; objet posé ou déduit pour 2026 : aucune) et qui
  voient les deux positions à moins de 30 m ; vignette perspective avec l'axe du support à la
  position d'origine (magenta, « A ») et à la position corrigée (cyan, « C »), arête avant de la
  bordure de référence projetée (jaune) ; pour une réorientation : face vue ou dos attendu pour
  chaque hypothèse ;
- ortho 5 cm 2022 avec les deux positions, les flèches de face, les bordures et les zones.
La décision est prise par lecture des planches (revue_coherence.json, verdicts de Claude) ; une
planche ambiguë garde la position d'origine si elle est légale, sinon la correction par la règle
avec une confiance faible.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

from coherence_carte import COHERENCE, azimut, ecart_angle
from commun import RACINE, point_a

sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
from camera import camera_calee, charger_poses, image_rgb, photo  # noqa: E402
from projection import camera_virtuelle, ortho_mosaique, projeter, reechantillonner  # noqa: E402

PLANCHES = COHERENCE / "planches"


def _police(taille=13):
    """Police TrueType avec accents (Arial de Windows ou DejaVu), sinon police bitmap par défaut."""
    from PIL import ImageFont
    for nom in ("arial.ttf", "C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


POLICE = _police(13)
POLICE_P = _police(11)
TAILLE = 360
COUL = {"A": (255, 0, 255), "C": (0, 230, 255), "S": (255, 170, 0), "T": (0, 255, 0)}


def _poses():
    if not hasattr(_poses, "c"):
        _poses.c = charger_poses()
    return _poses.c


def photos_calees(P, h, valide, n=4, dmax=40.0):
    """Photos calées acceptées, valides pour l'objet, voyant le pied et le sommet de toutes les
    positions P (liste de (x, y, z)) à moins de dmax : [(score, pid, d, cam)] triés."""
    out = []
    for pid, rec in sorted(_poses().items()):
        if not rec.get("accepte") or not valide(rec["date"]):
            continue
        cam, st = camera_calee(pid, _poses())
        if st != "calee":
            continue
        pts = np.vstack([np.asarray(P, float), np.asarray(P, float) + [0, 0, h]])
        r = projeter(pts, pid, cam=cam, dmax=dmax)
        if not r["visible"].all():
            continue
        c = cam.monde_vers_cam(pts)
        lat = np.degrees(np.arctan2(c[:, 2], np.hypot(c[:, 0], c[:, 1])))
        lat_min = photo(pid).seq.get("lat_min", -30.0)
        if np.any(lat < lat_min + 1.0):
            continue
        d = float(r["distance"].min())
        if d < 1.5:
            continue
        res_px = rec["qualite"]["residu_moy_px"]
        out.append((cam.px_par_rad / d / (1 + res_px / 4), pid, d, cam))
    out.sort(key=lambda t: (-t[0], t[1]))
    return out[:n]


def _vignette(pid, cam, hyps, h, bordures, azimuts, taille=TAILLE):
    """Vue perspective centrée sur les hypothèses ; axes des supports et bordure projetés."""
    P = np.array([q["p3"] for q in hyps])
    M = P.mean(axis=0) + [0, 0, h / 2]
    d3 = M - cam.C
    dist = float(np.linalg.norm(d3))
    spread = float(np.max(np.hypot(*(P[:, :2] - P[:, :2].mean(0)).T))) if len(P) > 1 else 0.0
    fov = math.degrees(2 * math.atan((spread + 1.6) / dist))
    fov = max(fov, math.degrees(2 * math.atan((h / 2 + 0.8) / dist)))
    fov = float(np.clip(fov * 1.1, 8.0, 75.0))
    lac = math.degrees(math.atan2(d3[0], d3[1])) % 360
    tan = math.degrees(math.atan2(d3[2], math.hypot(d3[0], d3[1])))
    cv = camera_virtuelle(cam, lac, tan, fov, taille)
    img = reechantillonner(cam, image_rgb(pid).astype(np.float32), cv)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for B in bordures:
        uv, ok, _ = cv.projeter(B)
        pts = [tuple(x) for x, k in zip(uv, ok) if k]
        if len(pts) > 1:
            dr.line(pts, fill=(255, 255, 0), width=1)
    lignes = []
    for q in hyps:
        A = q["p3"]
        S = A + [0, 0, h]
        seg = A + np.linspace(0, 1, 25)[:, None] * (S - A)
        uv, ok, _ = cv.projeter(seg)
        uv = uv[ok]
        col = COUL.get(q["cle"], (255, 255, 255))
        if len(uv) > 1:
            dr.line([tuple(x) for x in uv], fill=col, width=2)
            u, v = uv[0]
            dr.line([(u - 6, v), (u + 6, v)], fill=col, width=2)
            dr.text((uv[-1][0] + 3, uv[-1][1] - 12), q["cle"], fill=col, font=POLICE)
        if q.get("az") is not None:
            cam_az = azimut(cam.C[:2] - A[:2])
            e = ecart_angle(q["az"], cam_az)
            lignes.append(f"{q['cle']}: {'FACE' if e < 80 else 'DOS' if e > 100 else 'TRANCHE'} ({e:.0f}°)")
    dr.rectangle([0, 0, taille, 14], fill=(0, 0, 0))
    ph = photo(pid)
    dr.text((2, 0), f"{pid} {ph.date} d={dist:.1f} m", fill=(255, 255, 255), font=POLICE_P)
    if lignes:
        dr.rectangle([0, taille - 14, taille, taille], fill=(0, 0, 0))
        dr.text((2, taille - 13), "  ".join(lignes), fill=(255, 255, 255), font=POLICE_P)
    return im


def _ortho(carte, hyps, bordures, cote_m, taille=TAILLE):
    img, ox0, oy1 = ortho_mosaique()
    P = np.array([q["p3"][:2] for q in hyps])
    c = P.mean(axis=0)
    demi = max(cote_m / 2, float(np.max(np.abs(P - c))) + 3.0)
    x0, y0, x1, y1 = c[0] - demi, c[1] - demi, c[0] + demi, c[1] + demi
    pas = 0.05
    c0, c1 = int((x0 - ox0) / pas), int((x1 - ox0) / pas)
    r0, r1 = int((oy1 - y1) / pas), int((oy1 - y0) / pas)
    a = (np.clip(img[max(r0, 0):r1, max(c0, 0):c1], 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(a).convert("RGB").resize((taille, taille))
    sc = taille / (2 * demi)
    to = lambda x, y: ((x - x0) * sc, (y1 - y) * sc)
    dr = ImageDraw.Draw(im)
    # zones dérivées (contours légers) : passages, abaissés, îlots peints
    for B in bordures:
        dr.line([to(*p) for p in B[:, :2]], fill=(255, 40, 40), width=2)
    for q in hyps:
        u, v = to(*q["p3"][:2])
        col = COUL.get(q["cle"], (255, 255, 255))
        dr.ellipse([u - 6, v - 6, u + 6, v + 6], outline=col, width=2)
        dr.text((u + 7, v - 14), q["cle"], fill=col, font=POLICE)
        if q.get("az") is not None:
            a_ = math.radians(q["az"])
            L = 1.6 * sc
            dr.line([(u, v), (u + L * math.sin(a_), v - L * math.cos(a_))], fill=col, width=2)
    dr.rectangle([0, 0, taille, 13], fill=(0, 0, 0))
    dr.text((2, 0), f"ortho 5 cm 2022  {2 * demi:.0f} m  (bordures 2026 en rouge)", fill=(255, 255, 255), font=POLICE_P)
    return im


def bordures_proches(carte, c, rayon=9.0):
    out = []
    for kb in carte.bordures:
        P = kb["P"]
        d = np.hypot(*(P - c).T)
        if d.min() > rayon:
            continue
        s = np.arange(0, kb["L"] + 1e-9, 0.25)
        q, _ = point_a(P, s)
        q = q[np.hypot(*(q - c).T) <= rayon]
        if len(q) > 1:
            z = carte.z_sol(q)
            out.append(np.c_[q, z])
    return out


def planche(carte, ident, titre, hyps, h, valide, chemin, azimuts=False, n=4, notes=()):
    """hyps : [dict(cle 'A'|'C'|'S'|'T', p (2,), az)] ; renvoie (chemin, photos utilisées)."""
    for q in hyps:
        p = np.asarray(q["p"], float)
        q["p3"] = np.r_[p, float(carte.z_sol(p[None])[0])]
    c = np.mean([q["p"] for q in hyps], axis=0)
    B = bordures_proches(carte, c)
    sel = photos_calees([q["p3"] for q in hyps], h, valide, n=n)
    vign = [_vignette(pid, cam, hyps, h, B, azimuts) for _, pid, d, cam in sel]
    orth = _ortho(carte, hyps, B, 10.0)
    W = TAILLE * max(4, len(vign))
    H = 34 + (TAILLE if vign else 0) + TAILLE
    out = Image.new("RGB", (W, H), (25, 25, 25))
    dr = ImageDraw.Draw(out)
    for k, ligne in enumerate(titre[:2]):
        dr.text((4, 2 + 15 * k), ligne[:230], fill=(255, 255, 255), font=POLICE)
    for k, v in enumerate(vign):
        out.paste(v, (k * TAILLE, 34))
    y = 34 + (TAILLE if vign else 0)
    out.paste(orth, (0, y))
    leg = ["A (magenta) : position / face d'origine", "C (cyan) : position / face corrigée",
           "S (orange) : hypothèse d'une spec (feux.json / panneaux.json)", "T (vert) : position triangulée",
           "jaune : arête avant de la bordure de référence", "FACE / DOS : côté du panneau attendu vers la caméra"]
    for k, l in enumerate(leg):
        dr.text((TAILLE + 10, y + 10 + 17 * k), l, fill=(230, 230, 230), font=POLICE)
    for k, l in enumerate(notes):
        dr.text((TAILLE + 10, y + 125 + (25 if not vign else 0) + 17 * k), str(l)[:150], fill=(255, 230, 150), font=POLICE)
    if not vign:
        dr.text((TAILLE + 10, y + 130), "aucune photo calée valide pour cet objet (date de l'objet, champ ou distance > 40 m)", fill=(255, 120, 120), font=POLICE)
    PLANCHES.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=88)
    return chemin, [dict(photo=pid, date=photo(pid).date, distance_m=round(d, 1)) for _, pid, d, _ in sel]


def trianguler(o, p_a, p_c, valide_de):
    """Triangulation de l'axe d'un mât cherché entre les deux hypothèses (enrichir/triangulation)."""
    import triangulation as T
    import gcp as G
    mid = (np.asarray(p_a) + np.asarray(p_c)) / 2
    h = float(o.get("hauteur") or 3.0)
    z = float(o.get("z0") or 0.0)
    g = dict(id="MAT-coh-" + o["id"], famille="mat", type=o["type"], objets=[o["id"]],
             pied=[mid[0], mid[1], z], sommet=[mid[0], mid[1], z + max(h - 0.6, 0.8)], hauteur_m=h,
             diametre_m=G.DIAMETRES.get(o["type"], 0.12), sigma_m=1.0, poids=1.0, valide_de=valide_de,
             valide_a=G.DATE_MAX, source="coherence", confiance=o.get("confiance"))
    rayon = float(np.hypot(*(np.asarray(p_a) - np.asarray(p_c)))) / 2 + 1.0
    r = T.verifier_mat(g, laisser_de_cote=False, rayon_recherche_m=rayon)
    if not r.get("position_triangulee"):
        return dict(conclusion=r.get("conclusion"), n_photos=r.get("n_photos_pointees"))
    X = np.array(r["position_triangulee"])
    da, dc = float(np.hypot(*(X - p_a))), float(np.hypot(*(X - p_c)))
    if not r.get("fiable"):
        concl = "triangulation indicative (géométrie insuffisante) : non utilisée"
    elif da <= 0.35 and da < dc:
        concl = f"position d'origine confirmée (axe triangulé à {da:.2f} m de A, {dc:.2f} m de l'autre hypothèse)"
    elif dc <= 0.35 and dc < da:
        concl = f"autre hypothèse confirmée (axe triangulé à {dc:.2f} m, {da:.2f} m de A)"
    else:
        concl = f"axe triangulé à {da:.2f} m de A et {dc:.2f} m de l'autre hypothèse : un autre support a pu être retenu"
    return dict(position=[round(float(v), 3) for v in X], fiable=bool(r.get("fiable")), n_inliers=r.get("n_inliers"),
                angle_intersection_deg=r.get("angle_intersection_deg"), ecart_type_m=r.get("ecart_type_m"),
                d_origine_m=round(da, 3), d_alternative_m=round(dc, 3), conclusion=concl)
