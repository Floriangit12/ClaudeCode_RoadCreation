#!/usr/bin/env python3
"""Contrôle automatique d'un marquage sur ortho, avec masque véhicules / ombres (contrat FUS-AUTO-02 de la fusion).

Une confirmation automatique de marquage n'est acceptée par fusion_recensement.py que si l'observation porte
`attributs.controle_auto` avec masque_vehicules_ombres = true, part_masquee ≤ 0,2 et une réponse de peinture :
reponse_ligne_fine = true (ligne : trait de 0,10 à 0,15 m qui répond sur toute la longueur) ou reponse_peinture = true
(flèche, symbole, bande : part peinte du polygone). Ce module calcule ce bloc ; il ne décide rien d'autre.

  masque_vehicules_ombres(L, rgb, res_m) : taches claires ou sombres de plus de 3 m² et d'au moins 1,2 m de large
      (voitures, camionnettes, bâches) et ombres portées (sombres et bleutées), dilatées de 0,3 m ;
  reponse_ligne_fine(...) : profils perpendiculaires tous les 0,25 m ; un profil répond si un trait clair de 0,10 à
      0,15 m (pic cherché à ± 0,25 m de l'axe décrit) dépasse ses deux abords de 15 niveaux ; exige 5 cm/pixel ;
  controle_marquage(eid) : bloc controle_auto d'une entité de la description, sur le PCRS 5 cm de 2022 ou sur une
      couche datée (dossier de dalles .jpg + .jgw).

Essai sur le PCRS 2022 (10/10/2026, planche description/enrichi/controle_auto_essai.jpg) : les quatre fausses
confirmations relevées par la critique (ML-0294 sur une voiture blanche, ML-0295 sur une ombre de bâtiment, ML-0119
devant une voiture sombre, ML-5360 entre une voiture et des conteneurs) sont masquées ; quatre lignes réelles
(ML-0125, ML-0136, ML-0206, ML-0239) et une flèche (MF-5042) sont confirmées ; ML-0481 (sous l'ombre d'un arbre :
masqué) et ML-0526 (axe décalé de 0,4 m : incertain) ne sont pas confirmés.

Numpy + Pillow, déterministe. Usage :
  python controle_auto.py --entites ML-0294 ML-0295 [--ortho pcrs2022|<dossier>] [--planche fichier.jpg]
"""
from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

VERSION = "controle_auto.py/0.1"
ROOT = Path(__file__).resolve().parents[3]
PCRS = ROOT / "data/sites/paquet_jardin/ortho5cm_2022"

SEUIL_TACHE = 35.0          # écart à la luminance de fond (niveaux) d'une tache claire ou sombre
SURFACE_MIN_M2 = 3.0
LARGEUR_MIN_M = 1.2
DILATATION_M = 0.3
RAYON_FOND_M = 2.5
SEUIL_TRAIT = 15.0          # contraste minimal du trait sur ses deux abords
PART_REPONSE_MIN = 0.8      # « sur toute la longueur » : 80 % des profils non masqués
PART_PEINTE_MIN = 0.3
RES_MAX_LIGNE_M = 0.06      # un trait de 0,10-0,15 m n'est pas résolu au-delà de 6 cm/pixel


# --------------------------------------------------------------------------------------------- lecture de l'ortho

def lire_ortho(x0, y0, x1, y1, ortho="pcrs2022"):
    """Découpe RGB (uint8) et résolution d'une emprise L93 ; ortho = 'pcrs2022' ou dossier de dalles .jpg + .jgw."""
    if ortho == "pcrs2022":
        res = 0.05
        W, H = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
        can = Image.new("RGB", (W, H))
        for tx in range(int(x0 // 50 * 50), int(x1) + 1, 50):
            for ty in range(int(y0 // 50 * 50), int(y1) + 1, 50):
                fp = PCRS / f"pcrs5cm_{tx}_{ty}.jpg"
                if fp.exists():
                    can.paste(Image.open(fp).convert("RGB"), (int(round((tx - x0) / res)), int(round((y1 - (ty + 50)) / res))))
        return np.asarray(can), res, (x0, y1)
    d = Path(ortho)
    res = None
    morceaux = []
    for jgw in sorted(d.glob("*.jgw")):
        a = [float(v) for v in jgw.read_text().split()]
        res = a[0]
        im = Image.open(jgw.with_suffix(".jpg")).convert("RGB")
        gx0, gy1 = a[4] - a[0] / 2, a[5] - a[3] / 2
        gx1, gy0 = gx0 + im.size[0] * a[0], gy1 + im.size[1] * a[3]
        if gx1 < x0 or gx0 > x1 or gy1 < y0 or gy0 > y1:
            continue
        morceaux.append((gx0, gy1, im))
    if res is None:
        raise FileNotFoundError(f"aucune dalle géoréférencée dans {d}")
    W, H = int(math.ceil((x1 - x0) / res)), int(math.ceil((y1 - y0) / res))
    can = Image.new("RGB", (W, H))
    for gx0, gy1, im in morceaux:
        can.paste(im, (int(round((gx0 - x0) / res)), int(round((y1 - gy1) / res))))
    return np.asarray(can), res, (x0, y1)


def luminance(rgb):
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def flou(L, rayon_px):
    im = Image.fromarray(np.clip(L, 0, 255).astype(np.uint8), "L")
    return np.asarray(im.filter(ImageFilter.GaussianBlur(radius=max(1.0, rayon_px))), dtype=np.float64)


# --------------------------------------------------------------------------------------------- masque

def _ouverture(m, k):
    im = Image.fromarray((m * 255).astype(np.uint8), "L")
    im = im.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    return np.asarray(im) > 127


def _dilater(m, k):
    im = Image.fromarray((m * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(k))
    return np.asarray(im) > 127


def _grandes_composantes(m, n_min):
    """Composantes 4-connexes d'au moins n_min pixels (parcours en largeur, ordre de balayage : déterministe)."""
    H, W = m.shape
    vu = np.zeros_like(m, dtype=bool)
    out = np.zeros_like(m, dtype=bool)
    for i0, j0 in zip(*np.nonzero(m)):
        if vu[i0, j0]:
            continue
        pile = deque([(i0, j0)])
        vu[i0, j0] = True
        comp = []
        while pile:
            i, j = pile.popleft()
            comp.append((i, j))
            for a, b in ((i + 1, j), (i - 1, j), (i, j + 1), (i, j - 1)):
                if 0 <= a < H and 0 <= b < W and m[a, b] and not vu[a, b]:
                    vu[a, b] = True
                    pile.append((a, b))
        if len(comp) >= n_min:
            ii, jj = zip(*comp)
            out[list(ii), list(jj)] = True
    return out


def _fermeture(m, k):
    im = Image.fromarray((m * 255).astype(np.uint8), "L")
    im = im.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    return np.asarray(im) > 127


def masque_vehicules_ombres(L, rgb, res_m):
    """Masque booléen des véhicules (taches claires ou sombres ≥ 3 m², largeur ≥ 1,2 m) et des ombres portées.

    Une voiture est un assemblage de carrosserie claire (ou sombre), de vitres sombres et de reflets : les écarts
    clairs et sombres au fond sont réunis, les trous de moins de 0,3 m bouchés (fermeture), puis seules les taches
    d'au moins 1,2 m de large (ouverture) et 3 m² sont gardées ; les traits peints (0,10-0,50 m) et les bandes de
    zébra (séparées de 0,5 m) disparaissent à l'ouverture."""
    fond = flou(L, RAYON_FOND_M / res_m)
    d = L - fond
    R, B = rgb[..., 0].astype(float), rgb[..., 2].astype(float)
    tache = (np.abs(d) > SEUIL_TACHE) | ((L < 70.0) & (B >= R))   # ombres portées : sombres et bleutées
    tache = _fermeture(tache, int(math.ceil(0.3 / res_m)) | 1)
    k = int(math.ceil(LARGEUR_MIN_M / res_m)) | 1
    n_min = int(math.ceil(SURFACE_MIN_M2 / res_m ** 2))
    m = _grandes_composantes(_ouverture(tache, k), n_min)
    return _dilater(m, int(math.ceil(2 * DILATATION_M / res_m)) | 1)


# --------------------------------------------------------------------------------------------- réponses

def _bilin(L, x, y):
    H, W = L.shape
    x = np.clip(x, 0, W - 1.001)
    y = np.clip(y, 0, H - 1.001)
    i, j = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = y - i, x - j
    return (L[i, j] * (1 - fx) * (1 - fy) + L[i, j + 1] * fx * (1 - fy) + L[i + 1, j] * (1 - fx) * fy + L[i + 1, j + 1] * fx * fy)


def reponse_ligne_fine(L, masque, res_m, axe_px, pas_m=0.25):
    """Part des profils perpendiculaires non masqués où un trait fin répond ; part des profils masqués."""
    if res_m > RES_MAX_LIGNE_M:
        return {"reponse_ligne_fine": None, "fraction_reponse": None, "part_masquee": None, "n_profils": 0,
                "note": f"résolution {res_m:.2f} m : trait de 0,10-0,15 m non résolu"}
    P = np.asarray(axe_px, float)
    offs = np.arange(-0.6, 0.6001, res_m / 2.0)
    rep, msk, n = 0, 0, 0
    for a, b in zip(P[:-1], P[1:]):
        L_seg = float(np.hypot(*(b - a))) * res_m
        if L_seg <= 0:
            continue
        t = (b - a) / np.hypot(*(b - a))
        nrm = np.array([-t[1], t[0]])
        for s in np.arange(pas_m / 2.0, L_seg, pas_m):
            c = a + t * (s / res_m)
            n += 1
            i, j = int(round(c[1])), int(round(c[0]))
            if 0 <= i < masque.shape[0] and 0 <= j < masque.shape[1] and masque[i, j]:
                msk += 1
                continue
            prof = _bilin(L, c[0] + nrm[0] * offs / res_m, c[1] + nrm[1] * offs / res_m)
            best = None
            for c0 in offs[np.abs(offs) <= 0.25]:
                centre = prof[np.abs(offs - c0) <= 0.075].mean()
                g = prof[(offs - c0 >= -0.45) & (offs - c0 <= -0.2)]
                dr = prof[(offs - c0 >= 0.2) & (offs - c0 <= 0.45)]
                if len(g) == 0 or len(dr) == 0:
                    continue
                v = centre - max(g.mean(), dr.mean())
                best = v if best is None else max(best, v)
            if best is not None and best >= SEUIL_TRAIT:
                rep += 1
    libres = n - msk
    frac = rep / libres if libres else 0.0
    return {"reponse_ligne_fine": bool(libres and frac >= PART_REPONSE_MIN), "fraction_reponse": round(frac, 3),
            "part_masquee": round(msk / n, 3) if n else None, "n_profils": n}


def reponse_peinture(L, masque, res_m, poly_px):
    """Part peinte (plus claire que le fond de 25 niveaux) d'un polygone de marquage, hors masque."""
    H, W = L.shape
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in poly_px], fill=255)
    dedans = np.asarray(im) > 127
    if not dedans.any():
        return {"reponse_peinture": None, "part_peinte": None, "part_masquee": None}
    fond = flou(L, 1.0 / res_m)
    libre = dedans & ~masque
    pm = 1.0 - libre.sum() / dedans.sum()
    part = float(((L - fond) > 25.0)[libre].mean()) if libre.any() else 0.0
    return {"reponse_peinture": bool(libre.any() and part >= PART_PEINTE_MIN), "part_peinte": round(part, 3),
            "part_masquee": round(float(pm), 3)}


# --------------------------------------------------------------------------------------------- entité

def controle_marquage(eid, ortho="pcrs2022", ix=None, retour_image=False):
    """Bloc attributs.controle_auto d'un marquage de la description (FUS-AUTO-02)."""
    import fusion_recensement as FR
    ix = ix or FR.charger_index()
    e = ix.E[eid]
    G = e["G"]
    bx0, by0, bx1, by1 = G["bbox"]
    marge = 4.0
    rgb, res, (ox, oy) = lire_ortho(bx0 - marge, by0 - marge, bx1 + marge, by1 + marge, ortho)
    L = luminance(rgb.astype(np.float64))
    M = masque_vehicules_ombres(L, rgb, res)

    def px(C):
        return np.c_[(C[:, 0] - ox) / res, (oy - C[:, 1]) / res]

    out = {"outil": VERSION, "ortho": ortho if ortho == "pcrs2022" else Path(ortho).name, "resolution_m": res,
           "masque_vehicules_ombres": True}
    if G["lignes"] and e["type"] in ("ligne", "transversale"):
        r = reponse_ligne_fine(L, M, res, px(max(G["lignes"], key=len)))
        out.update(r)
        out["reponse_peinture"] = None
    elif G["polys"]:
        R = max((pg[0] for pg in G["polys"]), key=len)
        if e["type"] in ("ligne", "transversale"):
            # ligne décrite par son polygone : axe = plus long côté du rectangle orienté (approximation)
            Q = px(R)
            r = reponse_ligne_fine(L, M, res, Q)
            out.update(r)
            out["reponse_peinture"] = None
        else:
            out.update(reponse_peinture(L, M, res, px(R)))
            out["reponse_ligne_fine"] = None
    else:
        out.update({"reponse_ligne_fine": None, "reponse_peinture": None, "part_masquee": None,
                    "note": f"type {e['type']} décrit par un axe ({G['type']}) : non traité (bandes de passage, zones)"})
    ok = (out.get("part_masquee") is not None and out["part_masquee"] <= 0.2
          and (out.get("reponse_ligne_fine") is True or out.get("reponse_peinture") is True))
    out["verdict"] = "confirme" if ok else ("masque" if (out.get("part_masquee") or 0) > 0.2 else "incertain")
    if retour_image:
        return out, rgb, M, px, G
    return out


def planche(eids, ortho, chemin, ix=None):
    """Planche de contrôle : découpe brute | masque (rouge) + géométrie décrite (magenta), verdict."""
    import fusion_recensement as FR
    ix = ix or FR.charger_index()
    vignettes = []
    for eid in eids:
        out, rgb, M, px, G = controle_marquage(eid, ortho, ix, retour_image=True)
        brut = Image.fromarray(rgb).convert("RGB")
        ann = brut.copy()
        rouge = Image.new("RGB", brut.size, (220, 40, 40))
        ann.paste(rouge, (0, 0), Image.fromarray((M * 110).astype(np.uint8), "L"))
        d = ImageDraw.Draw(ann)
        for C in G["lignes"] + [pg[0] for pg in G["polys"]]:
            d.line([tuple(p) for p in px(C)], fill=(255, 0, 255), width=1)
        s = 300.0 / max(brut.size)
        taille = (max(1, int(brut.size[0] * s)), max(1, int(brut.size[1] * s)))
        v = Image.new("RGB", (620, 340), (250, 250, 250))
        v.paste(brut.resize(taille), (5, 5))
        v.paste(ann.resize(taille), (315, 5))
        txt = (f"{eid} : {out['verdict']} ; masqué {out.get('part_masquee')} ; ligne {out.get('fraction_reponse')} ; "
               f"peinte {out.get('part_peinte')}")
        ImageDraw.Draw(v).text((5, 315), txt, fill=(10, 10, 10))
        vignettes.append(v)
    if not vignettes:
        return
    can = Image.new("RGB", (620 * 2, 340 * ((len(vignettes) + 1) // 2)), (250, 250, 250))
    for k, v in enumerate(vignettes):
        can.paste(v, ((k % 2) * 620, (k // 2) * 340))
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    can.save(chemin, quality=90)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--entites", nargs="+", required=True)
    ap.add_argument("--ortho", default="pcrs2022")
    ap.add_argument("--planche")
    a = ap.parse_args()
    import fusion_recensement as FR
    ix = FR.charger_index()
    for eid in a.entites:
        print(eid, json.dumps(controle_marquage(eid, a.ortho, ix), ensure_ascii=False))
    if a.planche:
        planche(a.entites, a.ortho, a.planche, ix)


if __name__ == "__main__":
    main()
