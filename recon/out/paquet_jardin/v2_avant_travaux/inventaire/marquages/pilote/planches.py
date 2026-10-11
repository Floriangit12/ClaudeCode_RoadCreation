"""Planches de superposition du pilote (ortho seulement ; aucune photo de tiers).

- planches/pilote_<zone>.jpg        : ortho PCRS 2022 à 5 cm, vecteurs ajustés (cyan : gabarits IISR posés ;
                                       jaune : axes de lignes ; orange : pavés jaunes ; bleu : carrés blancs) et levé
                                       GAM (magenta, fin) ;
- planches/pilote_<zone>_zooms.jpg  : agrandissements x5 (1 cm / px) des flèches et de passages : contour du gabarit
                                       normé (cyan), gabarit à échelle libre (vert), GAM (magenta) ;
- planches/pilote_<zone>_2024.jpg   : mêmes vecteurs 2022 sur la BD ORTHO IGN 2024 (20 cm, recalée sur le PCRS).
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

import commun_pilote as C
import zebras as Z

CYAN, JAUNE, ORANGE, BLEU, MAGENTA, VERT = (0, 255, 255), (255, 255, 0), (255, 140, 0), (60, 120, 255), (255, 0, 255), (0, 255, 0)


def _px(P, geo, X0, Y1, res):
    P = np.asarray(P)
    return list(zip(((P[:, 0] - X0) / res).tolist(), ((Y1 - P[:, 1]) / res).tolist()))


def _dessiner(d, ctx, X0, Y1, res, w=1, gam=True, emprise=None):
    rgb, geo, det, passages, fl_polys, lignes, jaunes, carres, bandes = ctx
    if gam:
        e = emprise or (X0, Y1 - 1e3, X0 + 1e3, Y1)
        for p, P in C.gam_dans(*e):
            d.line(_px(P, geo, X0, Y1, res), fill=MAGENTA, width=1)
    for b in bandes:
        if b["regularise"]:
            pts = _px(b["anneau"], geo, X0, Y1, res)
            d.polygon(pts, outline=CYAN)
            if w > 1:
                d.line(pts + pts[:1], fill=CYAN, width=w)
    for f in fl_polys:
        for poly in f["polys"]:
            pts = _px(poly[0], geo, X0, Y1, res)
            d.line(pts + pts[:1], fill=CYAN, width=w)
    for ln in lignes:
        d.line(_px(ln["axe_l93"], geo, X0, Y1, res), fill=JAUNE, width=w)
    for f in jaunes:
        th = f["axe_rad"]
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        for c in f["centres"]:
            Q = [np.array(c) + su * f["plein_m"] / 2 * eu + sv * (f["largeur_bande_m"] or 0.5) / 2 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            pts = _px(Q, geo, X0, Y1, res)
            d.line(pts + pts[:1], fill=ORANGE, width=w)
    import damiers as DM
    for f in carres:
        for poly in DM.polygones_file(f, 0.5, 0.5):
            pts = _px(poly[0], geo, X0, Y1, res)
            d.line(pts + pts[:1], fill=BLEU, width=w)


def _legende(d, H, titre):
    y = 6
    for c, t in ((CYAN, "gabarit IISR pose (bandes 0,50 regularisees, fleches)"), (JAUNE, "axe de ligne mesure"),
                 (ORANGE, "paves jaunes 2022 (periodicite)"), (BLEU, "carres blancs 0,50"), (MAGENTA, "leve GAM (Meylan_Topo.dwg)")):
        d.rectangle([6, y, 22, y + 10], fill=c)
        d.text((28, y - 1), t, fill=(255, 255, 255))
        y += 14
    d.text((6, H - 14), titre, fill=(255, 255, 255))


def planches_zone(nom, emp, ctx, r):
    rgb, geo, det, passages, fl_polys, lignes, jaunes, carres, bandes = ctx
    X0, Y0, X1, Y1 = emp
    out = C.SORTIE / "planches"
    out.mkdir(exist_ok=True)
    # vue d'ensemble 5 cm
    r0, c0 = C.l93_vers_px(X0, Y1, geo)
    r0, c0 = int(round(r0 + 0.5)), int(round(c0 + 0.5))
    H, W = int(round((Y1 - Y0) / C.PX)), int(round((X1 - X0) / C.PX))
    im = Image.fromarray(rgb[r0:r0 + H, c0:c0 + W].copy())
    d = ImageDraw.Draw(im)
    _dessiner(d, ctx, X0, Y1, C.PX, emprise=(X0, Y0, X1, Y1))
    _legende(d, H, f"Pilote {nom} - ortho PCRS 5 cm 10/05/2022 - 1 px = 5 cm - L93 {X0:.0f}-{X1:.0f} / {Y0:.0f}-{Y1:.0f}")
    im.save(out / f"pilote_{nom}.jpg", quality=92)
    # même chose sur 2024
    rgb24, g24 = C.mosaique_2024(X0, Y0, X1, Y1)
    im = Image.fromarray(rgb24)
    d = ImageDraw.Draw(im)
    _dessiner(d, ctx, X0, Y1, C.PX, gam=False)
    _legende(d, im.size[1], f"Vecteurs 2022 sur BD ORTHO IGN 2024 (20 cm, 09/08/2024, recalee {C.decalage_2024()[0]:+.3f} / {C.decalage_2024()[1]:+.3f} m) - {nom}")
    im.save(out / f"pilote_{nom}_2024.jpg", quality=92)
    # zooms x5
    vign = []
    cibles = [("fleche " + f["id"] + " " + f["type"], np.vstack([p[0] for p in f["polys"]]).mean(0), 6.0, f) for f in fl_polys]
    for p in passages[:4]:
        cibles.append(("passage " + p["id"] + f" ({p['n_bandes']} bandes, pas {p['pas_m']:.3f})", np.array(p["centre_l93"]), 8.0, None))
    for titre, c, taille, f in cibles:
        x0, y1 = c[0] - taille / 2, c[1] + taille / 2
        s = 5
        res = C.PX / s
        sub, sg = C.mosaique_2022(x0, y1 - taille, x0 + taille, y1)
        big = Image.fromarray(sub).resize((sub.shape[1] * s, sub.shape[0] * s), Image.BICUBIC)
        d = ImageDraw.Draw(big)
        X0z, Y1z = sg
        for pp, P in C.gam_dans(x0, y1 - taille, x0 + taille, y1):
            d.line(_px(P, sg, X0z, Y1z, res), fill=MAGENTA, width=2)
        if f is not None:
            for poly in f["polys_libre"]:
                pts = _px(poly[0], sg, X0z, Y1z, res)
                d.line(pts + pts[:1], fill=VERT, width=1)
            for poly in f["polys"]:
                pts = _px(poly[0], sg, X0z, Y1z, res)
                d.line(pts + pts[:1], fill=CYAN, width=2)
        else:
            for b in bandes:
                pts = _px(b["anneau"], sg, X0z, Y1z, res)
                d.line(pts + pts[:1], fill=CYAN if b["regularise"] else VERT, width=2 if b["regularise"] else 1)
        d.rectangle([0, 0, big.size[0], 16], fill=(0, 0, 0))
        d.text((4, 2), titre + f" - 1 px = {taille / 600 * 100:.1f} cm ; cyan norme, vert mesure/brut, magenta GAM", fill=(255, 255, 255))
        vign.append(big.resize((600, int(600 * big.size[1] / big.size[0])), Image.LANCZOS))
    if vign:
        ncol = 3
        nl = math.ceil(len(vign) / ncol)
        hmax = max(v.size[1] for v in vign)
        mos = Image.new("RGB", (600 * ncol, hmax * nl), (0, 0, 0))
        for i, v in enumerate(vign):
            mos.paste(v, ((i % ncol) * 600, (i // ncol) * hmax))
        mos.save(out / f"pilote_{nom}_zooms.jpg", quality=92)
