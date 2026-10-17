"""Contours des plaques de signalisation relevés sur les faces officielles (PNG RGBA de convertir_panneaux.py).

    python -P recon/pcg/assets_route/signalisation/contours_faces_panneaux.py            # tous les signaux plaques
    python -P recon/pcg/assets_route/signalisation/contours_faces_panneaux.py --codes AB3a B1 Dc29_ex1

Pour chaque signal « plaque » du catalogue assets/specs/route/panneaux_fr_catalogue.json (familles A, AB, B, C, CE, D,
E/EB, H, SR, M, AK, G/J à forme de plaque ; les symboles, idéogrammes, feux et balises cylindriques sont exclus) :
  1. masque d'opacité (alpha > 127) de la face ; composantes connexes (8-connexité) ; les petites (< 0,2 % de l'image)
     et les supports dessinés (composantes très élancées) sont écartés ;
  2. une composante peu « pleine » (aire / enveloppe convexe < 0,85 : plaques réunies par un poteau dessiné) est ouverte
     par un élément structurant horizontal (supprime les poteaux verticaux) puis re-découpée ;
  3. enveloppe convexe de chaque plaque (sommets des pixels de bord), simplifiée (Douglas-Peucker 0,8 px) ; si la plaque
     remplit moins de 95 % de son enveloppe (J13, G1 bis…), contour réel (OpenCV, approximation 1,0 px) ;
  4. échelle (m par pixel) à la gamme normale, par ordre de priorité :
     a) dimensions spécifiques de l'IISR 1 art. 5-3 (B30, B51, B56, B58, C3, C14, C25a/b, C117) : largeur de la plaque
        principale ;
     b) disque 850, octogone 800 (entre côtés), carré 700 (côté) : largeur de la plaque principale (IISR 1 art. 5-3 p. 10) ;
     c) triangles, losanges, panonceaux, autres plaques à dimensions définies : cadre du PDF × 4,99 (échelle des dessins
        du Cerema, contrôlée sur A13a : 926 mm pour 925 mm attendus d'un triangle de 1000 à angles arrondis) ;
     d) panneaux à dimensions variables (D, E/EB, H, SR) : la plus petite plaque du dessin reçoit la hauteur minimale de
        250 mm (IISR 1 art. 5-3 2) p. 11) — ESTIMATION, à ajuster au texte réel ;
  5. facteurs des gammes (rapport à la gamme normale) pour les formes à gammes.
Sortie (non versionnée, régénérable) : assets/lib/route_fr/panneaux_3d/contours_faces.json
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import ConvexHull

RACINE = Path(__file__).resolve().parents[4]
CAT = RACINE / "assets/specs/route/panneaux_fr_catalogue.json"
SORTIE = RACINE / "assets/lib/route_fr/panneaux_3d/contours_faces.json"
FAMILLES = {"danger_A", "intersection_priorite_AB", "prescription_B", "indication_C", "services_CE", "reperage_direction_D",
            "localisation_E_EB", "touristique_H", "securite_routiere_SR", "panonceau_M", "temporaire_K",
            "passage_niveau_G_balises_J"}
FORMES_EXCLUES = {"symbole", "feu_boitier", "balise_cylindrique"}
VARIABLES = {"reperage_direction_D", "localisation_E_EB", "touristique_H", "securite_routiere_SR"}
ECHELLE_DESSIN = 4.99


def douglas(pts, eps):
    if len(pts) < 4:
        return pts
    a, b = np.array(pts[0], float), np.array(pts[-1], float)
    d = b - a
    n = np.hypot(*d) or 1.0
    dist = [abs(d[0] * (a[1] - p[1]) - d[1] * (a[0] - p[0])) / n for p in pts[1:-1]]
    i = int(np.argmax(dist)) + 1
    if dist[i - 1] > eps:
        return douglas(pts[:i + 1], eps)[:-1] + douglas(pts[i:], eps)
    return [pts[0], pts[-1]]


def enveloppe(mask):
    bord = mask & ~ndimage.binary_erosion(mask)
    ys, xs = np.nonzero(bord)
    pts = np.stack([xs + 0.5, ys + 0.5], 1)
    # coins des pixels de bord : enveloppe exacte de l'emprise
    coins = np.concatenate([pts + d for d in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5))])
    h = ConvexHull(coins)
    poly = [tuple(coins[k]) for k in h.vertices]
    # Douglas-Peucker sur un contour fermé : coupé au sommet le plus éloigné du premier
    p0 = np.array(poly[0])
    i = int(np.argmax([np.hypot(*(np.array(q) - p0)) for q in poly]))
    poly = douglas(poly[:i + 1], 0.8)[:-1] + douglas(poly[i:] + [poly[0]], 0.8)[:-1]
    return poly, float(h.volume)


def contour_reel(mask):
    """Contour extérieur exact d'une plaque non convexe (OpenCV findContours + approxPolyDP 1,0 px), sens quelconque."""
    import cv2
    cs, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, 1.0, True)[:, 0, :].astype(float) + 0.5
    return [tuple(p) for p in ap]


def plaques(alpha):
    H, W = alpha.shape
    m = alpha > 127
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    out, ecartes = [], []
    for k in range(1, n + 1):
        c = lab == k
        aire = int(c.sum())
        if aire < 0.002 * H * W:
            continue
        ys, xs = np.nonzero(c)
        w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        if h > 6 * w and w < 0.06 * W:
            ecartes.append("support dessiné")
            continue
        poly, ah = enveloppe(c)
        if aire / ah < 0.85:
            k_l = max(9, int(0.05 * W))
            ouv = ndimage.binary_opening(c, structure=np.ones((1, k_l)))
            lab2, n2 = ndimage.label(ouv, structure=np.ones((3, 3)))
            for j in range(1, n2 + 1):
                c2 = lab2 == j
                if c2.sum() < 0.002 * H * W:
                    continue
                # récupère les bords arrondis : pixels d'origine à moins de k_l px de la composante ouverte
                c2 = ndimage.binary_dilation(c2, structure=np.ones((3, k_l))) & c
                p2, a2 = enveloppe(c2)
                out.append(dict(contour_px=[[round(x, 2), round(y, 2)] for x, y in p2], aire_px=int(c2.sum()),
                                remplissage=round(c2.sum() / a2, 3)))
            ecartes.append("composante ouverte (poteau dessiné supprimé)")
            continue
        rem = aire / ah
        convexe = rem >= 0.95
        if not convexe:                          # plaque non convexe : contour réel (route::panneau triangule la face)
            poly = contour_reel(c)
        out.append(dict(contour_px=[[round(x, 2), round(y, 2)] for x, y in poly], aire_px=aire, remplissage=round(rem, 3),
                        convexe=convexe))
    return out, ecartes


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def analyser(s, meta):
    png = RACINE / s["fichier"]
    im = Image.open(png)
    alpha = np.asarray(im.convert("RGBA"))[..., 3]
    H, W = alpha.shape
    pl, ecartes = plaques(alpha)
    if not pl:
        return None
    pl.sort(key=lambda p: -p["aire_px"])
    principale = pl[0]
    x0, y0, x1, y1 = bbox(principale["contour_px"])
    wpx, hpx = x1 - x0, y1 - y0
    forme, code = s["forme"], s["code"]
    spec = meta["gammes_iisr"]["specifiques"].get(code) or meta["gammes_iisr"]["specifiques"].get(s["id"])
    gam = meta["gammes_iisr"]["valeurs_mm"]
    regle, conf = "", "moyenne"
    if spec and "normale" in spec:
        e = spec["normale"][0] / 1000.0 / wpx
        regle = f"dimensions spécifiques IISR 1 art. 5-3 : {spec['normale'][0]} × {spec['normale'][1]} mm (largeur de la plaque)"
        conf = "haute"
    elif forme == "disque":
        e = gam["disque"]["normale"] / 1000.0 / wpx
        regle, conf = "disque, gamme normale 850 mm (largeur de la plaque)", "haute"
    elif forme == "octogone":
        e = gam["octogone"]["normale"] / 1000.0 / wpx
        regle, conf = "octogone, gamme normale 800 mm entre côtés opposés", "haute"
    elif forme == "carre" and s["famille"] not in VARIABLES and s["famille"] != "panonceau_M" and s["dimensions"]["type"] in ("cote_nominal_mm",):
        e = gam["carre"]["normale"] / 1000.0 / wpx
        regle, conf = "carré, gamme normale 700 mm de côté", "haute"
    elif s["famille"] in VARIABLES or s["dimensions"]["type"] == "variable":
        hmin = min(bbox(p["contour_px"])[3] - bbox(p["contour_px"])[1] for p in pl)
        e = 0.25 / hmin
        regle, conf = "dimensions variables : plus petite plaque à la hauteur minimale de 250 mm (IISR 1 art. 5-3 2) p. 11)", "estimation"
    else:
        e = s["pdf_cadre_mm"][0] * ECHELLE_DESSIN / 1000.0 / W
        regle = f"cadre du dessin PDF × {ECHELLE_DESSIN} (échelle des dessins Cerema, gamme normale)"
    # gammes
    cle = {"triangle": "triangle", "triangle_pointe_en_bas": "triangle", "triangle_pointe_en_bas+panonceau": "triangle",
           "disque": "disque", "octogone": "octogone", "carre": "carre", "carre_sur_pointe": "carre"}.get(forme)
    gammes = {"normale": 1.0}
    if cle and s["dimensions"]["type"] in ("cote_nominal_mm", "diametre_mm", "entre_cotes_opposes_mm") and s["famille"] != "panonceau_M":
        ref = gam[cle]["normale"]
        for g in ("miniature", "petite", "normale", "grande", "tres_grande"):
            if g in gam[cle]:
                gammes[g] = round(gam[cle][g] / ref, 5)
    # contrôle : cadre × 4,99 contre l'échelle retenue ; écart > 3 % sur une règle « haute » -> confiance moyenne
    e_dessin = s["pdf_cadre_mm"][0] * ECHELLE_DESSIN / 1000.0 / W
    if conf == "haute" and abs(e / e_dessin - 1) > 0.03:
        conf = "moyenne"
        regle += f" ; le dessin du Cerema est à une autre échelle ({100 * (e / e_dessin - 1):+.0f} %)"
    composite = any(p["remplissage"] < 0.9 for p in pl)
    if composite and s.get("exemple_de_composition"):
        return dict(id=s["id"], exclu="exemple de composition à plaques jointives (illustration) : non fabriqué")
    return dict(id=s["id"], code=code, nom=s.get("nom"), famille=s["famille"], forme=forme, png=s["fichier"], png_px=[W, H],
                m_par_px=e, regle_echelle=regle, confiance=conf, ecart_echelle_dessin_pct=round(100 * (e / e_dessin - 1), 1),
                gammes=gammes, pivot_px=[(x0 + x1) / 2, y1], plaques=pl, ecartes=ecartes,
                taille_normale_m=[round(wpx * e, 3), round(hpx * e, 3)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--codes", nargs="*")
    a = ap.parse_args()
    cat = json.loads(CAT.read_text(encoding="utf-8"))
    out, refus = [], []
    for s in cat["signaux"]:
        if a.codes and s["id"] not in a.codes:
            continue
        if s["famille"] not in FAMILLES or s["forme"] in FORMES_EXCLUES:
            continue
        if s["famille"] == "temporaire_K" and s["forme"] != "triangle":
            continue
        try:
            r = analyser(s, cat["meta"])
        except Exception as e:  # noqa: BLE001
            refus.append((s["id"], repr(e)))
            continue
        if r and r.get("exclu"):
            refus.append((r["id"], r["exclu"]))
        elif r:
            out.append(r)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(json.dumps(dict(schema="route_fr/contours_faces/1.0", source=str(CAT.relative_to(RACINE)).replace("\\", "/"),
                                      script="recon/pcg/assets_route/signalisation/contours_faces_panneaux.py",
                                      signaux=out, refus=refus), ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(out), "signaux ;", len(refus), "refus", refus[:5])


if __name__ == "__main__":
    main()
