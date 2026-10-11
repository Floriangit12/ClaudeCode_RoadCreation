"""Planches de contrôle de la régularisation géométrique (GQ-VAL-003) sur l'ortho 2022 du paquet.

Usage :
    python recon/pcg/decrire/regulariser_apercu.py [--dossier DESCRIPTION] [--sortie DOSSIER_PNG]
Défauts : recon/out/paquet_jardin/v2/description et <description>/regularisation.
Produit :
- avant_apres_<zoom>.png (6 zooms) : à gauche la géométrie source (base/regularisation_sources.geojson :
  bordures en rouge avec leurs sommets levés, limites de surfaces en orange, axes de marquage en magenta), à
  droite la géométrie régularisée (bordures : droites en blanc, arcs en cyan avec leur rayon, coins voulus en
  jaune, nœuds partagés en vert ; limites des surfaces reconstruites en orange ; axes en magenta) ;
- peignes_courbure.png : 5 bordures, peigne de courbure avant (courbure de Menger aux sommets levés) et après
  (courbure des primitives), même échelle ;
- regularisation_site.png : site complet, bordures colorées par écart max à la source.
"""
import argparse
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import regulariser_geometrie as RG
from apercu import fond_ortho, police
from commun import SORTIE, abscisses, anneaux, lire_geojson, repere

ZOOMS = {
    "coins_carrefour_so": (-20.0, -42.0, 4.0, -18.0),            # angles K-0379 (R 6) / K-0384 (R 3), îlot I-0339
    "nez_ilots_vercors": (-4.0, -28.0, 18.0, -6.0),              # I-0390 (gravier), I-0629, goutte I-0297
    "capture_7_verdun_so": (-44.0, -54.0, -14.0, -24.0),         # îlot BRF I-0333, flèche MF-6014 (capture 7.webp)
    "traversee_verdun_so": (-34.0, -30.0, -8.0, -4.0),           # zébras et abaissés de Verdun SO
    "trottoir_ne": (22.0, 18.0, 58.0, 54.0),                     # trottoir et piste de Verdun NE
    "arret_bus_verdun_so": (-54.0, -50.0, -26.0, -22.0),         # quai bus K-0382 (QUAI_BUS) et abri
}
PEIGNES = ["K-0666", "K-0380", "K-0390", "K-0382", "K-0379"]
COUL = {"droite": (255, 255, 255), "arc": (0, 230, 255), "clothoide": (255, 120, 255)}


def _dans(P, e, m=2.0):
    x0, y0, x1, y1 = e
    return not (P[:, 0].max() < x0 - m or P[:, 0].min() > x1 + m or P[:, 1].max() < y0 - m or P[:, 1].min() > y1 + m)


def panneau(e, res, titre, dessiner):
    x0, y0, x1, y1 = e
    img = fond_ortho(x0, y0, x1, y1, res)
    img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0.35)
    d = ImageDraw.Draw(img, "RGBA")
    tp = lambda P: [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(P)[:, :2]]
    dessiner(d, tp)
    f = police(18)
    d.rectangle([0, 0, img.width, 28], fill=(0, 0, 0, 180))
    d.text((8, 4), titre, fill=(255, 255, 255, 255), font=f)
    return img


def charger(dossier):
    base = Path(dossier) / "base"
    src = {}
    for x in lire_geojson(base / "regularisation_sources.geojson"):
        p = x["properties"]
        src.setdefault(p["famille"], []).append((p["entite"], repere(np.asarray(x["geometry"]["coordinates"])[:, :2]), p))
    K = lire_geojson(base / "bordures.geojson")
    S = lire_geojson(base / "surfaces.geojson")
    M = lire_geojson(base / "marquages.geojson") if (base / "marquages.geojson").exists() else []
    return src, K, S, M


def planche_zoom(nom, e, src, K, S, M, sortie, res=0.025):
    k = max(1, int(round(0.03 / res)))

    def avant(d, tp):
        for eid, P, p in src.get("limites", []):
            if _dans(P, e):
                d.line(tp(P), fill=(255, 150, 40, 230), width=k)
        for eid, P, p in src.get("marquages", []):
            if _dans(P, e):
                d.line(tp(P), fill=(255, 0, 255, 230), width=k)
        for eid, P, p in src.get("bordures", []):
            if not _dans(P, e):
                continue
            d.line(tp(P), fill=(255, 50, 50, 255), width=2 * k)
            for q in tp(RG.nettoyer(P)):
                d.ellipse([q[0] - 2 * k, q[1] - 2 * k, q[0] + 2 * k, q[1] + 2 * k], outline=(255, 255, 0, 255))

    def apres(d, tp):
        for f in S:
            for poly in anneaux(f["geometry"]):
                for r in poly:
                    R = repere(np.asarray(r)[:, :2])
                    if _dans(R, e):
                        d.line(tp(np.vstack([R, R[:1]])), fill=(255, 150, 40, 200), width=k)
        for f in M:
            p = f["properties"]
            if f["geometry"]["type"] != "LineString" or "geometrie_reguliere" not in p:
                continue
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            if _dans(P, e):
                d.line(tp(P), fill=(255, 0, 255, 240), width=k)
        fp = police(max(11, 6 * k))
        for f in K:
            p = f["properties"]
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            g = p.get("geometrie_reguliere")
            if not _dans(P, e) or not g:
                continue
            S_ = abscisses(P)
            for prim in g["primitives"]:
                m = (S_ >= prim["s0"] - 0.002) & (S_ <= prim["s1"] + 0.002)
                if m.sum() >= 2:
                    d.line(tp(P[m]), fill=COUL[prim["type"]] + (255,), width=2 * k)
                if prim["type"] == "arc" and prim["s1"] - prim["s0"] > 0.6 and prim["rayon_m"] < 200:
                    i = np.nonzero(m)[0]
                    q = tp(P[i[len(i) // 2]][None])[0]
                    d.text((q[0] + 4, q[1] + 2), f"R{prim['rayon_m']:.1f}", fill=(0, 230, 255, 255), font=fp)
            for c in g.get("coins", []):
                i = int(np.argmin(np.abs(S_ - c)))
                q = tp(P[i][None])[0]
                d.rectangle([q[0] - 4 * k, q[1] - 4 * k, q[0] + 4 * k, q[1] + 4 * k], outline=(255, 255, 0, 255), width=k)
            for nom_b, i in (("debut", 0), ("fin", -1)):
                t = g.get("noeuds", {}).get(nom_b, {}).get("type")
                q = tp(P[i][None])[0]
                if t == "noeud":
                    d.ellipse([q[0] - 3 * k, q[1] - 3 * k, q[0] + 3 * k, q[1] + 3 * k], fill=(0, 255, 0, 255))
                elif t == "t":
                    d.ellipse([q[0] - 3 * k, q[1] - 3 * k, q[0] + 3 * k, q[1] + 3 * k], fill=(0, 140, 255, 255))

    a = panneau(e, res, f"{nom} : AVANT (sources levées, sommets jaunes)", avant)
    b = panneau(e, res, f"{nom} : APRÈS (droites blanc, arcs cyan, coins jaune, nœuds vert, T bleu)", apres)
    out = Image.new("RGB", (a.width + b.width + 8, a.height), (40, 40, 40))
    out.paste(a, (0, 0))
    out.paste(b, (a.width + 8, 0))
    out.save(sortie / f"avant_apres_{nom}.png")
    return sortie / f"avant_apres_{nom}.png"


def menger(P):
    """Courbure de Menger aux sommets intérieurs (signée, 1/m)."""
    a, b, c = P[:-2], P[1:-1], P[2:]
    ab, bc, ca = np.hypot(*(b - a).T), np.hypot(*(c - b).T), np.hypot(*(a - c).T)
    cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    return 2 * cr / np.maximum(ab * bc * ca, 1e-12)


def peignes(src, K, sortie, ids=PEIGNES):
    """Peignes de courbure avant / après de 5 bordures (même échelle de peigne par bordure)."""
    Kd = {f["properties"]["id"]: f for f in K}
    S = {eid: P for eid, P, _ in src.get("bordures", [])}
    panneaux = []
    for kid in ids:
        if kid not in Kd or kid not in S:
            continue
        g = Kd[kid]["properties"]["geometrie_reguliere"]
        Pn = repere(np.asarray(Kd[kid]["geometry"]["coordinates"])[:, :2])
        Ps = RG.nettoyer(S[kid])
        # après : courbure des primitives, échantillonnée à 0,1 m
        ch = []
        for i in range(len(g["primitives"])):
            e = g["primitives"][i]
            x, y = repere(np.array([[e["x0"], e["y0"]]]))[0]
            ch.append(RG.Chaine(x, y, e["cap0_rad"], [[e["s1"] - e["s0"], e["k0"], e.get("k1", e["k0"])]]))
        Pa, Na, Ka = RG.peigne(ch, 0.1)
        kb = menger(Ps) if len(Ps) >= 3 else np.zeros(0)
        tb = Ps[2:] - Ps[:-2]
        tb /= np.maximum(np.hypot(*tb.T), 1e-12)[:, None]
        Nb = np.c_[-tb[:, 1], tb[:, 0]]
        A = np.vstack([Ps, Pn])
        x0, y0 = A.min(0) - 2
        x1, y1 = A.max(0) + 2
        L = max(x1 - x0, y1 - y0)
        res = L / 900.0
        kref = max(np.percentile(np.abs(Ka), 99) if len(Ka) else 0.0, 0.02)
        ech = 0.08 * L / kref                                      # longueur de dent = ech · k
        imgs = []
        for titre, P, Pc, Nc, Kc, coul in (("avant", Ps, Ps[1:-1], Nb, kb, (255, 80, 80)),
                                            ("après", Pn, Pa, Na, Ka, (0, 230, 255))):
            W, H = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
            im = Image.new("RGB", (W, H), (20, 20, 24))
            d = ImageDraw.Draw(im, "RGBA")
            tp = lambda Q: [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(Q)[:, :2]]
            for q, n, kk in zip(Pc, Nc, Kc):
                kk = float(np.clip(kk, -3 * kref, 3 * kref))
                d.line(tp(np.array([q, q - n * kk * ech])), fill=coul + (150,), width=1)
            d.line(tp(P), fill=(255, 255, 255, 255), width=2)
            f = police(16)
            d.text((6, 4), f"{kid} {titre}" + (f" : {len(Ps)} sommets levés" if titre == "avant" else
                                               f" : {g['n_primitives']}, écart max {g['ecart_max_m'] * 100:.1f} cm"),
                   fill=(255, 255, 255, 255), font=f)
            imgs.append(im)
        row = Image.new("RGB", (imgs[0].width * 2 + 8, imgs[0].height), (60, 60, 60))
        row.paste(imgs[0], (0, 0))
        row.paste(imgs[1], (imgs[0].width + 8, 0))
        panneaux.append(row)
    if not panneaux:
        return None
    W = max(p.width for p in panneaux)
    H = sum(p.height for p in panneaux) + 8 * (len(panneaux) - 1)
    out = Image.new("RGB", (W, H), (60, 60, 60))
    y = 0
    for p in panneaux:
        out.paste(p, (0, y))
        y += p.height + 8
    if out.height > 6000:
        out = out.resize((int(out.width * 6000 / out.height), 6000), Image.LANCZOS)
    out.save(sortie / "peignes_courbure.png")
    return sortie / "peignes_courbure.png"


def planche_site(K, sortie, res=0.12):
    e = (-150.0, -150.0, 150.0, 150.0)

    def dessin(d, tp):
        for f in K:
            g = f["properties"].get("geometrie_reguliere")
            if not g:
                continue
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            r = g["ecart_max_m"] / max(g["tolerance_m"], 1e-6)
            c = (0, 220, 0) if r <= 0.5 else (255, 230, 0) if r <= 1.0 else (255, 120, 0) if r <= 1.5 else (255, 0, 0)
            d.line(tp(P), fill=c + (255,), width=3)

    im = panneau(e, res, "bordures régularisées : écart max / T  (vert ≤ 0,5 ; jaune ≤ 1 ; orange ≤ 1,5 ; rouge > 1,5)", dessin)
    im.save(sortie / "regularisation_site.png")
    return sortie / "regularisation_site.png"


COUL_PLAN = {"chaussee": (178, 178, 182), "parking": (196, 196, 200), "acces_riverain": (190, 186, 196),
             "piste_cyclable": (150, 190, 205), "trottoir": (228, 214, 188), "quai_bus": (236, 200, 170),
             "ilot": (205, 190, 150), "terre_plein_vegetal": (150, 190, 130), "espace_vert": (170, 205, 150),
             "autre": (215, 215, 210), "emprise_bordure": (90, 90, 90), "chantier": (220, 200, 160)}


def plan_vrd(K, S, M, sortie, emprise=(-150.0, -150.0, 150.0, 150.0), res=0.1, nom="plan_vrd_site", rayons=False):
    """Plan de VRD (fond blanc) : surfaces par classe, bordures (arêtes avant) en noir, arcs en bleu avec leur
    rayon (zoom), axes des lignes de marquage et zébras en rouge : la description telle qu'elle sera fabriquée."""
    x0, y0, x1, y1 = emprise
    W, H = int((x1 - x0) / res), int((y1 - y0) / res)
    im = Image.new("RGB", (W, H), (255, 255, 255))
    d = ImageDraw.Draw(im, "RGBA")
    tp = lambda P: [((x - x0) / res, (y1 - y) / res) for x, y in np.asarray(P)[:, :2]]
    for f in S:
        c = COUL_PLAN.get(f["properties"]["classe"], (230, 230, 230))
        for poly in anneaux(f["geometry"]):
            R = repere(np.asarray(poly[0])[:, :2])
            if _dans(R, emprise, 0):
                d.polygon(tp(R), fill=c + (255,), outline=(120, 120, 120, 255))
                for h in poly[1:]:
                    d.polygon(tp(repere(np.asarray(h)[:, :2])), fill=(255, 255, 255, 255), outline=(120, 120, 120, 255))
    for f in M:
        p = f["properties"]
        g = f["geometry"]
        if g["type"] == "LineString" and p.get("classe") in ("ligne", "transversale", "passage"):
            P = repere(np.asarray(g["coordinates"])[:, :2])
            if _dans(P, emprise):
                d.line(tp(P), fill=(210, 30, 30, 255), width=max(1, int(0.12 / res)))
        elif g["type"] in ("Polygon", "MultiPolygon"):
            for poly in anneaux(g):
                R = repere(np.asarray(poly[0])[:, :2])
                if _dans(R, emprise):
                    d.polygon(tp(R), fill=(255, 255, 255, 255), outline=(210, 30, 30, 255))
    fp = police(max(10, int(0.6 / res)))
    for f in K:
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        g = f["properties"].get("geometrie_reguliere")
        if not _dans(P, emprise) or not g:
            continue
        S_ = abscisses(P)
        d.line(tp(P), fill=(0, 0, 0, 255), width=max(2, int(0.15 / res)))
        for prim in g["primitives"]:
            m = (S_ >= prim["s0"] - 0.002) & (S_ <= prim["s1"] + 0.002)
            if m.sum() < 2:
                continue
            arc = prim["type"] == "arc" and prim["rayon_m"] < 500
            if arc:
                d.line(tp(P[m]), fill=(20, 60, 200, 255), width=max(2, int(0.15 / res)))
            if rayons and arc and prim["s1"] - prim["s0"] > 0.8:
                i = np.nonzero(m)[0]
                q = tp(P[i[len(i) // 2]][None])[0]
                d.text((q[0] + 3, q[1] + 1), f"R{prim['rayon_m']:g}", fill=(20, 60, 200, 255), font=fp)
    d.rectangle([0, 0, W, int(1.6 / res) + 6], fill=(255, 255, 255, 230))
    d.text((6, 4), "Plan de VRD régularisé (description v2) : bordures droites en noir, arcs en bleu"
           + (" avec rayon" if rayons else "") + ", marquages en rouge ; surfaces par classe", fill=(0, 0, 0, 255),
           font=police(max(12, int(0.9 / res))))
    im.save(sortie / f"{nom}.png")
    return sortie / f"{nom}.png"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dossier", default=str(SORTIE))
    ap.add_argument("--sortie", default=None)
    ap.add_argument("--zooms", default=",".join(ZOOMS))
    a = ap.parse_args()
    sortie = Path(a.sortie or Path(a.dossier) / "regularisation")
    sortie.mkdir(parents=True, exist_ok=True)
    src, K, S, M = charger(a.dossier)
    for nom in a.zooms.split(","):
        print(planche_zoom(nom, ZOOMS[nom], src, K, S, M, sortie))
    print(peignes(src, K, sortie))
    print(planche_site(K, sortie))
    print(plan_vrd(K, S, M, sortie))
    print(plan_vrd(K, S, M, sortie, emprise=(-45.0, -45.0, 45.0, 45.0), res=0.03, nom="plan_vrd_centre", rayons=True))


if __name__ == "__main__":
    main()
