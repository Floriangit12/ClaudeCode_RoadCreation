"""Vue de dessus de la comparaison v2 : rendu de dessus du modèle | ortho, à la même échelle et sur la même emprise,
superposition des contours du modèle sur l'ortho, planches découpées en tuiles natives ; une planche dédiée au
CENTRE (zoom sur la zone de conflit et ses îlots, passages, traversées). Images diffusables : aucune photo de tiers
(rendu du modèle et orthos sous licence ouverte).

Orthos :
- PCRS 5 cm de Grenoble-Alpes Métropole (CRAIG, 10/05/2022, licence ouverte) quand ses dalles couvrent toute
  l'emprise (`decoupe.SOURCES_ORTHO["pcrs2022"]`, seulement le carré de Paquet Jardin) ;
- IGN BD ORTHO 20 cm partout (WMS Géoplateforme, couche ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO, Licence Ouverte Etalab
  2.0), date de prise de vue lue sur le graphe de mosaïquage (WFS) ; réponses en cache sous
  <sortie>/_orthos/ (non versionné).
Rendu : Karma XPU (rendu_hython.py) par une caméra quasi orthographique à 2 000 m (comme rendu_l2b._dessus : la
caméra orthographique de Karma XPU 22.0.459 ne lance aucun rayon), soleil à la date de l'ortho principale à 10 h 30
UTC. Contours du modèle (repère du modèle = L93 − origine pour les sites de Meylan) : bordures en rouge, limites de
matériau en jaune, marquages en cyan.

Planches (chaque fichier entre sans réduction) : par emprise (« site », « centre ») et par ortho, grille de tuiles de
740 px (recouvrement 20 % ; une dimension qui tient en une tuile un peu plus grande n'est pas recoupée) ;
`planche_dessus_<emprise>_<ortho>_tNN.png` = rendu | ortho (≈ 1 488 × 780 px) ;
`contours_<emprise>_<ortho>_tNN.png` = ortho + contours, même tuile (740 px). Images entières et manifeste
`dessus.json` (emprises L93 et locales de chaque tuile, sources, licences).
"""
import hashlib
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

import planches as PL

Image.MAX_IMAGE_PIXELS = None
TUILE = 740
GAP = 8
TITRE = 40
ALTITUDE = 2000.0
WMS = "https://data.geopf.fr/wms-r"
WFS = "https://data.geopf.fr/wfs"
COUCHE_IGN = "ORTHOIMAGERY.ORTHOPHOTOS.BDORTHO"
COUL_ARETES = {0: (255, 40, 40), 1: (255, 40, 40), 2: (255, 220, 0), 3: (0, 230, 255)}


def _get(url, timeout=120):
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ClaudeCode_RoadCreation/1.0 (comparaison)"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), r.headers.get("content-type", "")
        except Exception:  # réseau : nouvel essai
            if essai == 3:
                raise
            time.sleep(3 * (essai + 1))


# ------------------------------------------------------------------------------------------------ emprises
def emprises(zones, marge=6.0):
    """Emprises (repère du modèle) : « site » = toutes les zones ; « centre » = cœur (zone centrale ou anneau et îlot
    central) + îlots et passages à moins de 15 m du cœur."""
    from shapely.ops import unary_union
    tout = unary_union([z.poly for z in zones])
    coeur = [z for z in zones if z.type in ("centre", "anneau", "ilot_central")]
    out = {"site": tout.bounds}
    if coeur:
        u = unary_union([z.poly for z in coeur])
        voisins = [z.poly for z in zones if z.type in ("ilot", "passage") and z.poly.distance(u) <= 15.0]
        out["centre"] = unary_union([u] + voisins).bounds
    res = {}
    for k, (x0, y0, x1, y1) in out.items():
        m = marge if k == "site" else 4.0
        res[k] = (math.floor(x0 - m), math.floor(y0 - m), math.ceil(x1 + m), math.ceil(y1 + m))
    return res


# ------------------------------------------------------------------------------------------------ orthos
def ortho_pcrs(e_l93, pas=0.05):
    """Mosaïque PCRS 5 cm sur l'emprise L93 si elle la couvre entièrement (sinon None)."""
    import decoupe
    motif = decoupe.SOURCES_ORTHO["pcrs2022"][0]
    if not decoupe.dalles(motif):
        return None
    img, vu = decoupe.mosaique(motif, *e_l93, pas)
    if vu.mean() < 0.995:
        return None
    return {"image": Image.fromarray(img), "pas": pas, "nom": "pcrs2022",
            "libelle": "PCRS 5 cm Grenoble-Alpes Métropole (CRAIG), 10/05/2022", "date": "2022-05-10",
            "licence": "Licence Ouverte (CRAIG / Grenoble-Alpes Métropole)", "source": motif}


def date_ign(x, y):
    """Date de prise de vue de la BD ORTHO 20 cm au point (graphe de mosaïquage, WFS) ou None."""
    from shapely.geometry import Point, shape
    try:
        p = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
             "TYPENAMES": "ORTHOIMAGERY.ORTHOPHOTOS.GRAPHE-MOSAIQUAGE:graphe_bdortho", "SRSNAME": "EPSG:2154",
             "BBOX": f"{x - 5:.1f},{y - 5:.1f},{x + 5:.1f},{y + 5:.1f},EPSG:2154", "OUTPUTFORMAT": "application/json",
             "COUNT": 20}
        d = json.loads(_get(WFS + "?" + urllib.parse.urlencode(p), timeout=60)[0])
        # (18/10/2026 : le graphe porte « echelle » = 50 sur Meylan pour la mosaïque 20 cm ; le filtre sur echelle = 20
        # rendait toujours « date inconnue » : on garde le polygone qui contient le point, quelle que soit l'échelle)
        for f in d.get("features", []):
            pr = f["properties"]
            if shape(f["geometry"]).contains(Point(x, y)):
                return str(pr.get("date_vol", ""))[:10] or None
    except Exception:  # service indisponible : date inconnue
        return None
    return None


def ortho_ign(e_l93, cache, pas=0.20):
    """BD ORTHO 20 cm (WMS Géoplateforme) sur l'emprise L93, en cache (image + métadonnées)."""
    x0, y0, x1, y1 = e_l93
    cle = hashlib.sha256(json.dumps([round(v, 2) for v in e_l93] + [pas, COUCHE_IGN]).encode()).hexdigest()[:12]
    cache = Path(cache)
    f, fj = cache / f"ign_{cle}.png", cache / f"ign_{cle}.json"
    if f.exists() and fj.exists():
        meta = json.loads(fj.read_text(encoding="utf-8"))
        return dict(meta, image=Image.open(f).convert("RGB"))
    W, H = int(round((x1 - x0) / pas)), int(round((y1 - y0) / pas))
    im = Image.new("RGB", (W, H))
    bloc = 2000
    for j0 in range(0, H, bloc):
        for i0 in range(0, W, bloc):
            w, h = min(bloc, W - i0), min(bloc, H - j0)
            bx0, by1 = x0 + i0 * pas, y1 - j0 * pas
            p = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": COUCHE_IGN, "STYLES": "",
                 "FORMAT": "image/png", "CRS": "EPSG:2154", "WIDTH": w, "HEIGHT": h,
                 "BBOX": f"{bx0:.3f},{by1 - h * pas:.3f},{bx0 + w * pas:.3f},{by1:.3f}"}
            b, ct = _get(WMS + "?" + urllib.parse.urlencode(p))
            if not ct.startswith("image"):
                raise RuntimeError("WMS IGN : " + b[:200].decode("utf-8", "replace"))
            import io
            im.paste(Image.open(io.BytesIO(b)).convert("RGB"), (i0, j0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dv = date_ign(cx, cy)
    meta = {"pas": pas, "nom": "ign", "libelle": f"IGN BD ORTHO 20 cm ({COUCHE_IGN}), prise de vue {dv or 'date inconnue'}",
            "date": dv, "licence": "Licence Ouverte Etalab 2.0 — IGN, Géoplateforme (data.geopf.fr)",
            "source": WMS + " " + COUCHE_IGN, "emprise_l93": list(e_l93), "telecharge_le": time.strftime("%Y-%m-%d")}
    cache.mkdir(parents=True, exist_ok=True)
    im.save(f)
    fj.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return dict(meta, image=im)


# ------------------------------------------------------------------------------------------------ rendu
def camera_dessus(cx, cy, z, largeur, W, H):
    """Caméra quasi orthographique (perspective à 2 000 m) pour rendu_hython : X image = +x, Y image = +y (nord en
    haut), visée vers le bas."""
    m = [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0], [float(cx), float(cy), float(z + ALTITUDE), 1.0]]
    return {"focale_mm": 36.0 * ALTITUDE / largeur, "ouverture_h_mm": 36.0, "ouverture_v_mm": 36.0 * H / W,
            "resolution": [int(W), int(H)], "matrice": m}


# ------------------------------------------------------------------------------------------------ contours
def limites_materiaux(modele, e_loc, pas):
    """Masque (H, W) des limites entre matériaux du sol du modèle, par rastérisation des faces (vue de dessus) : marche
    aussi quand les maillages voisins ne partagent pas leurs arêtes (anneau et îlot d'un giratoire, cœur d'un
    carrefour), ce que `modele.aretes` ne voit pas."""
    x0, y0, x1, y1 = e_loc
    W, H = int(round((x1 - x0) / pas)), int(round((y1 - y0) / pas))
    lab = np.zeros((H, W), np.int32)
    off = modele._off
    mats = {m: k + 1 for k, m in enumerate(sorted({str(v) for v in modele.mat_face[modele.utile]}))}
    for n in np.unique(modele.C):
        sel = np.nonzero((modele.C == n) & modele.utile)[0]
        if not len(sel):
            continue
        pts = np.stack([modele.P[modele.F[off[sel] + k], :2] for k in range(int(n))], 1)
        px = np.stack([(pts[..., 0] - x0) / pas, (y1 - pts[..., 1]) / pas], -1)
        dedans = (px[..., 0].max(1) >= 0) & (px[..., 0].min(1) < W) & (px[..., 1].max(1) >= 0) & (px[..., 1].min(1) < H)
        mf = modele.mat_face[sel]
        for m in np.unique(mf[dedans]):
            q = np.round(px[dedans & (mf == m)] * 4).astype(np.int32)
            cv2.fillPoly(lab, list(q), int(mats[str(m)]), lineType=cv2.LINE_8, shift=2)
    bord = np.zeros((H, W), bool)
    bord[:, 1:] |= lab[:, 1:] != lab[:, :-1]
    bord[1:, :] |= lab[1:, :] != lab[:-1, :]
    bord &= lab > 0
    return bord


def dessiner_contours(img, modele, e_loc, pas, epaisseur=1):
    """Ortho (PIL) + arêtes du modèle (repère du modèle, emprise e_loc, pas m/px) : limites de matériau jaunes
    (rastérisation des faces du sol), bordures rouges, marquages cyan (petits segments le long de la tangente de
    chaque point d'arête)."""
    P, T, typ = modele.aretes()
    x0, y0, x1, y1 = e_loc
    a = np.asarray(img.convert("RGB")).copy()
    try:
        bord = limites_materiaux(modele, e_loc, pas)
        if bord.shape == a.shape[:2]:
            a[bord] = COUL_ARETES[2]
    except Exception:  # modèle sans faces exploitables : arêtes seules
        pass
    ok = (P[:, 0] >= x0) & (P[:, 0] <= x1) & (P[:, 1] >= y0) & (P[:, 1] <= y1)
    demi = 0.09
    for k in (0, 1, 3):
        sel = ok & (typ == k)
        A = P[sel, :2] - demi * T[sel, :2]
        B = P[sel, :2] + demi * T[sel, :2]
        ua = np.c_[(A[:, 0] - x0) / pas, (y1 - A[:, 1]) / pas]
        ub = np.c_[(B[:, 0] - x0) / pas, (y1 - B[:, 1]) / pas]
        lignes = np.stack([ua, ub], 1).round().astype(np.int32)
        cv2.polylines(a, list(lignes), False, COUL_ARETES[k], epaisseur, lineType=cv2.LINE_8)
    return Image.fromarray(a)


# ------------------------------------------------------------------------------------------------ planches
def grille(W, H, t=TUILE, rec=0.2):
    import decoupe
    return decoupe.grille(W, H, t, rec)


def _boites(W, H):
    """Tuiles (x0, y0, x1, y1) : 740 px par défaut ; une dimension qui tient en une tuile un peu plus large (≤ 760 px
    de large, ou la hauteur permise par l'aire d'une planche à deux panneaux) n'est pas recoupée (évite 4 tuiles
    presque identiques pour une image de 750 × 820 px)."""
    import decoupe
    tw = W if W <= 760 else TUILE
    th_max = int(1092 * 1092 // (2 * tw + GAP)) - TITRE - 1
    th = H if H <= th_max else min(TUILE, th_max)
    return [(x, y, min(x + tw, W), min(y + th, H))
            for y in decoupe.positions(H, th, 0.2) for x in decoupe.positions(W, tw, 0.2)], tw, th


def planches_tuiles(dossier, nom, rendu, ortho, contours, e_loc, pas, origine_l93, titre):
    """Tuiles appariées rendu | ortho et tuiles de contours ; renvoie la liste des tuiles (manifeste)."""
    W, H = rendu.size
    out = []
    boites, tw, th = _boites(W, H)
    for k, (px0, py0, px1, py1) in enumerate(boites):
        w, h = px1 - px0, py1 - py0
        pl = Image.new("RGB", (2 * tw + GAP, th + TITRE), (22, 22, 26))
        d = ImageDraw.Draw(pl)
        lx0, ly1 = e_loc[0] + px0 * pas, e_loc[3] - py0 * pas
        lx1, ly0 = e_loc[0] + px1 * pas, e_loc[3] - py1 * pas
        d.text((6, 3), f"{titre} | tuile t{k:02d} : x {lx0:.1f} à {lx1:.1f} m, y {ly0:.1f} à {ly1:.1f} m "
                       f"(repère du site), {pas * 100:.0f} cm/px", fill=(235, 235, 235), font=PL.police(13))
        d.text((6, 21), "gauche : rendu Karma du modèle (vue de dessus) ; droite : ortho, même emprise, même échelle",
               fill=(200, 200, 200), font=PL.police(12))
        pl.paste(rendu.crop((px0, py0, px1, py1)), (0, TITRE))
        pl.paste(ortho.crop((px0, py0, px1, py1)), (tw + GAP, TITRE))
        f1 = Path(dossier) / f"planche_dessus_{nom}_t{k:02d}.png"
        pl.save(f1)
        f2 = Path(dossier) / f"contours_{nom}_t{k:02d}.png"
        contours.crop((px0, py0, px1, py1)).save(f2)
        assert pl.size[0] * pl.size[1] <= 1092 * 1092 and max(pl.size) <= 1568
        out.append({"tuile": f"t{k:02d}", "planche": f1.name, "contours": f2.name, "boite_px": [px0, py0, px1, py1],
                    "local": [round(lx0, 2), round(ly0, 2), round(lx1, 2), round(ly1, 2)],
                    "l93": [round(lx0 + origine_l93[0], 2), round(ly0 + origine_l93[1], 2),
                            round(lx1 + origine_l93[0], 2), round(ly1 + origine_l93[1], 2)]})
    return out


def apercu(dst, rendu, ortho, titre):
    """Aperçu d'ensemble rendu | ortho réduit pour entrer sans réduction (lecture d'ensemble seulement)."""
    W, H = rendu.size
    k = min(1.0, (1560 - GAP) / (2 * W), math.sqrt(1092 * 1092 * 0.98 / ((2 * W + GAP) * (H + TITRE))))
    w, h = max(1, int(W * k)), max(1, int(H * k))
    while (2 * w + GAP) * (h + TITRE) > 1092 * 1092 or 2 * w + GAP > 1568:   # bandeau et marge ne se réduisent pas
        k *= 0.98
        w, h = max(1, int(W * k)), max(1, int(H * k))
    pl = Image.new("RGB", (2 * w + GAP, h + TITRE), (22, 22, 26))
    d = ImageDraw.Draw(pl)
    d.text((6, 3), titre[:170], fill=(235, 235, 235), font=PL.police(13))
    d.text((6, 21), f"aperçu réduit ({k:.2f}) : ne pas conclure sur un détail, voir les tuiles", fill=(200, 200, 200),
           font=PL.police(12))
    pl.paste(rendu.resize((w, h), Image.LANCZOS), (0, TITRE))
    pl.paste(ortho.resize((w, h), Image.LANCZOS), (w + GAP, TITRE))
    pl.save(dst)
    return dst
