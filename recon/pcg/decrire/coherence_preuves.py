"""Planches de preuve du solveur de cohérence v2 : photos calées (P1), porte géométrique (P2), orthos.

Planche d'une décision (déplacement > 0,3 m, réorientation > 20°, mesure appliquée, anomalie, non résolu,
conflit de spec, indice d'ombre) :
- jusqu'à 4 vignettes de photos CALÉES (coherence_poses : Panoramax 2024-2025 et 2026, Mapillary calées),
  valides à la date de l'objet, décisives d'abord ; axes des hypothèses A (origine, magenta), C (résolue,
  cyan), S (spec, orange), T (triangulée, vert), M (mesure retenue, blanc), F (fusion en revue, jaune),
  O (pied par l'ombre, rouge) ; bordure de référence (jaune) ; pied de chaque vignette : séparation
  angulaire A↔C rapportée au σ de la pose (« 2,7σ ») et décisivité (P2) ;
- tableau de la porte géométrique pour chaque paire (A, X) sur TOUTES les photos calées valides : nombre
  de photos discriminantes (> 3σ, pose décisive), angle d'intersection maximal, verdict (complet / latéral /
  non observable) et composante validée ;
- ortho PCRS 5 cm 2022 graduée tous les 0,25 m le long de A -> C (lecture chiffrée, P16), ombre détectée
  (P10) ; ortho IGN 20 cm 2024.
Les vignettes de photos de tiers restent locales (*.jpg ignorés par git) ; l'attribution est écrite.
"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw

import coherence_poses as PO
from coherence_carte import COHERENCE, azimut, ecart_angle
from commun import RACINE, point_a

sys.path.insert(0, str(RACINE / "recon/pcg/enrichir"))
from projection import camera_virtuelle, reechantillonner  # noqa: E402

PLANCHES = COHERENCE / "planches"


def _police(taille=13):
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
COUL = {"A": (255, 0, 255), "C": (0, 230, 255), "S": (255, 170, 0), "T": (0, 255, 0), "M": (255, 255, 255),
        "F": (255, 255, 0), "O": (255, 60, 60), "R": (160, 160, 255)}


def _vignette(p, hyps, h, bordures, azimuts, gates, taille=TAILLE):
    """Vue perspective centrée sur les hypothèses, axes projetés, pied : porte A↔X de cette photo."""
    cam = p["cam"]
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
    img = reechantillonner(cam, PO.image_rgb(p).astype(np.float32), cv)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for B in bordures:
        uv, ok, _ = cv.projeter(B)
        pts = [tuple(x) for x, k in zip(uv, ok) if k]
        if len(pts) > 1:
            dr.line(pts, fill=(255, 255, 0), width=1)
    faces = []
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
        if azimuts and q.get("az") is not None:
            cam_az = azimut(cam.C[:2] - A[:2])
            e = ecart_angle(q["az"], cam_az)
            faces.append(f"{q['cle']}:{'face' if e < 80 else 'dos' if e > 100 else 'tranche'} {e:.0f}°")
    dr.rectangle([0, 0, taille, 14], fill=(0, 0, 0))
    dr.text((2, 0), f"{p['id']} {p['date']} d={dist:.1f} m {'décisive' if p['decisive'] else 'non décisive'}",
            fill=(255, 255, 255), font=POLICE_P)
    pied = []
    for cle, g in gates:
        x = [l for l in g["photos"] if l["photo"] == p["id"]]
        if x:
            pied.append(f"A-{cle} {x[0]['separation_deg']:.2f}°={x[0]['rapport']:.1f}σ")
    lignes = ["  ".join(pied)] + (["  ".join(faces)] if faces else [])
    y0 = taille - 14 * len(lignes)
    dr.rectangle([0, y0, taille, taille], fill=(0, 0, 0))
    for k, l in enumerate(lignes):
        dr.text((2, y0 + 14 * k), l[:70], fill=(255, 255, 255), font=POLICE_P)
    return im


def _ortho(nom, hyps, bordures, cote_m, taille=TAILLE, graduer=None, ombre=None):
    import coherence_ombres as CO
    P = np.array([q["p3"][:2] for q in hyps])
    c = P.mean(axis=0)
    demi = max(cote_m / 2, float(np.max(np.abs(P - c))) + 2.0)
    g = np.linspace(-demi, demi, taille)
    X, Y = np.meshgrid(g, -g)
    V = CO.echantillonner(nom, np.stack([c[0] + X, c[1] + Y], -1))
    im = Image.fromarray((np.clip(np.nan_to_num(V), 0, 1) * 255).astype(np.uint8)).convert("RGB")
    sc = taille / (2 * demi)
    to = lambda x, y: ((x - c[0] + demi) * sc, (c[1] - y + demi) * sc)
    dr = ImageDraw.Draw(im)
    for B in bordures:
        dr.line([to(*q) for q in B[:, :2]], fill=(255, 40, 40), width=1)
    if graduer is not None:
        A, Cc = np.asarray(graduer[0], float), np.asarray(graduer[1], float)
        L = float(np.hypot(*(Cc - A)))
        if L > 0.05:
            u = (Cc - A) / L
            n = np.array([-u[1], u[0]])
            dr.line([to(*A), to(*Cc)], fill=(255, 255, 255), width=1)
            for k, s in enumerate(np.arange(0.0, L + 1e-6, 0.25)):
                q = A + u * s
                lg = 0.18 if k % 4 == 0 else 0.08
                dr.line([to(*(q - n * lg)), to(*(q + n * lg))], fill=(255, 255, 255), width=1)
    if ombre is not None:
        q = np.asarray(ombre["xy"], float)
        a = math.radians(ombre["az_ombre_grille"])
        e = q + 2.0 * np.array([math.sin(a), math.cos(a)])
        dr.line([to(*q), to(*e)], fill=COUL["O"], width=1)
    for q in hyps:
        u, v = to(*q["p3"][:2])
        col = COUL.get(q["cle"], (255, 255, 255))
        dr.ellipse([u - 5, v - 5, u + 5, v + 5], outline=col, width=2)
        dr.text((u + 6, v - 14), q["cle"], fill=col, font=POLICE)
        if q.get("az") is not None:
            a_ = math.radians(q["az"])
            Lp = 1.4 * sc
            dr.line([(u, v), (u + Lp * math.sin(a_), v - Lp * math.cos(a_))], fill=col, width=2)
    dr.rectangle([0, 0, taille, 13], fill=(0, 0, 0))
    lib = "ortho PCRS 5 cm 2022-05-10" if nom == "pcrs2022" else "ortho IGN 20 cm 2024-08-09"
    dr.text((2, 0), f"{lib}  {2 * demi:.0f} m  graduation 0,25 m A→C", fill=(255, 255, 255), font=POLICE_P)
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


def portes(hyps, photos):
    """Porte géométrique (P2) de chaque hypothèse X ≠ A contre A, sur toutes les photos valides."""
    A = [q for q in hyps if q["cle"] == "A"]
    if not A:
        return []
    out = []
    for q in hyps:
        if q["cle"] == "A" or float(np.hypot(*(np.asarray(q["p"]) - np.asarray(A[0]["p"])))) < 0.05:
            continue
        out.append((q["cle"], PO.porte(A[0]["p"], q["p"], photos)))
    return out


def planche(carte, ident, titre, hyps, h, valide, chemin, azimuts=False, n=4, notes=(), ombre=None, faire=True):
    """hyps : [dict(cle, p (2,), az)] ; renvoie (chemin, photos utilisées, portes)."""
    for q in hyps:
        p = np.asarray(q["p"], float)
        q["p3"] = np.r_[p, float(carte.z_sol(p[None])[0])]
    photos = PO.photos_pour([q["p3"] for q in hyps], h, valide, dmax=40.0)
    gates = portes(hyps, photos)
    # vignettes : poses décisives ou calées sur GCP ; les poses Mapillary recalées sur les bordures (erreurs de 1 à
    # 3 m constatées sur les planches) restent dans la porte (non décisives) mais ne sont pas montrées
    sel = [x for x in photos if x[1]["statut_pose"] != "calee_bordures"][:n]
    info = [dict(photo=p["id"], date=p["date"], plateforme=p["plateforme"], statut_pose=p["statut_pose"],
                 decisive=p["decisive"], distance_m=round(d, 1), attribution=p["attribution"]) for _, p, d in sel]
    if not faire:
        return chemin, info, gates
    c = np.mean([q["p"] for q in hyps], axis=0)
    B = bordures_proches(carte, c)
    vign = [_vignette(p, hyps, h, B, azimuts, gates) for _, p, d in sel]
    A = [q for q in hyps if q["cle"] == "A"]
    Cq = [q for q in hyps if q["cle"] == "C"] or [q for q in hyps if q["cle"] in ("M", "S", "T", "F", "O")]
    grad = (A[0]["p"], Cq[0]["p"]) if A and Cq else None
    o22 = _ortho("pcrs2022", hyps, B, 8.0, graduer=grad, ombre=ombre)
    o24 = _ortho("ign2024", hyps, B, 8.0, graduer=grad)
    W = TAILLE * max(4, len(vign))
    H = 34 + (TAILLE if vign else 0) + TAILLE
    out = Image.new("RGB", (W, H), (25, 25, 25))
    dr = ImageDraw.Draw(out)
    for k, ligne in enumerate(titre[:2]):
        dr.text((4, 2 + 15 * k), ligne[:230], fill=(255, 255, 255), font=POLICE)
    for k, v in enumerate(vign):
        out.paste(v, (k * TAILLE, 34))
    y = 34 + (TAILLE if vign else 0)
    out.paste(o22, (0, y))
    out.paste(o24, (TAILLE, y))
    x0 = 2 * TAILLE + 10
    lig = ["A magenta : origine ; C cyan : résolue ; S orange : spec ; T vert : triangulée ; M blanc : mesure ;",
           "F jaune : fusion (revue) ; O rouge : pied par l'ombre (trait = ombre) ; jaune : bordure de référence",
           "Porte P2 (toutes photos calées valides) : discriminante si séparation > 3σ de la pose ; décisive si LOO ≤ 0,5°"]
    for cle, g in gates:
        lig.append(f"A→{cle} {g['d_AC_m']:.2f} m : {g['n_photos']} photos, {g['n_discriminantes']} discriminantes décisives, "
                   f"angle {g['angle_intersection_max_deg']}° -> {g['verdict']} (validé {g['composante_validee_m']:+.2f} m)")
    lig += [str(x) for x in notes]
    for k, l in enumerate(lig[:20]):
        dr.text((x0, y + 8 + 16 * k), l[:150], fill=(230, 230, 230) if k < 3 else (255, 230, 150), font=POLICE)
    if not vign:
        dr.text((x0, y + TAILLE - 22), "aucune photo calée valide pour cet objet (date, champ ou distance > 40 m)",
                fill=(255, 120, 120), font=POLICE)
    PLANCHES.mkdir(parents=True, exist_ok=True)
    out.save(chemin, quality=88)
    return chemin, info, gates


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
