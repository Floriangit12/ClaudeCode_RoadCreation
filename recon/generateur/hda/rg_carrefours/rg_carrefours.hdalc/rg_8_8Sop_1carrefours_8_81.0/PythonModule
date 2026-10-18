"""Lecture des carrefours du modèle modele_voie/0.1 (module Python de l'HDA rg::carrefours ; entrées-sorties seulement).

Python SOP « carrefours » : aucune opération géométrique, les valeurs du modèle (carrefours, branches, îlots, passages,
lignes transversales) et les balayages des véhicules (lot L3a, calculés par le pilote) sont rangés en attributs ;
Lambert-93 -> local (origine du repère) -> Houdini (x, 0, −y), comme rg::lire_modele.

Géométrie produite :
  points du groupe « branche »   : carrefour, branche, route, extremite, s_front, azimut, rayon_coin, regle_coin, rang
                                   (ordre trigonométrique des azimuts), regime, ligne_type, ligne_distance, passage,
                                   ilot, centre (local, vecteur)
  points du groupe « passage »   : id, route, carrefour, s, largeur (longueur des bandes), axe0, axe1 (locaux),
                                   refuge, abaisses, bev
  primitives « ligne »           : marquages ligne_transversale (polyligne locale) : id, gabarit, couleur, route,
                                   carrefour, branche, s
  primitives « passage_libre »   : marquages passage_pieton sans route (traversée d'une voie directe) : id, carrefour,
                                   branche, couleur
  primitives « ilot »            : îlots du modèle (polygone) : id, type, carrefour, porte (1 : bande du profil),
                                   pp_route, pp_bande, pp_s0, pp_s1, nez_rayon, materiau, surelevation, ceinture,
                                   ceinture_vue, refuge_largeur, contour (marquage de contour, JSON)
  primitives « balayage »        : enveloppes balayées (polygones) : trajectoire, vehicule, carrefour, mouvement,
                                   de_branche, vers_branche, faisable
  primitives « trajectoire »     : trajectoires du modèle (polylignes) : id, carrefour, mouvement, de_branche,
                                   vers_branche
Détail : rg_carrefours (fichier, sha256, comptes), origine.
"""
import hashlib
import json
import math
import os

import hou


def _hda(sop):
    n = sop
    while n is not None and n.type().definition() is None:
        n = n.parent()
    return n


def _txt(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _attr(geo, classe, nom, defaut):
    if classe == "point" and geo.findPointAttrib(nom) is None:
        geo.addAttrib(hou.attribType.Point, nom, defaut)
    elif classe == "prim" and geo.findPrimAttrib(nom) is None:
        geo.addAttrib(hou.attribType.Prim, nom, defaut)


def _poly(geo, pts, ferme):
    pp = geo.createPoints(pts)
    pr = geo.createPolygon(is_closed=ferme)
    for p in pp:
        pr.addVertex(p)
    return pr



def _zones_passage(m, route, s, o):
    """Zones peintes du passage d'une branche (marquages passage_pieton du modèle, un polygone par groupe de bandes)
    en local : (xy aplatis, nombre de points par zone) ; correction après le contrôle de l'étape 2 (bandes prolongées
    dans les congés de coin par rg::carrefours_sol)."""
    xy, nz, ids = [], [], []
    for x in m.get("marquages", []):
        an = x.get("ancrage") or {}
        if x.get("type") != "passage_pieton" or an.get("route") != route or an.get("s") is None:
            continue
        if abs(float(an["s"]) - float(s)) > 0.05:
            continue
        ext = list((x.get("geometrie") or {}).get("exterieur") or [])
        if len(ext) > 1 and ext[0] == ext[-1]:
            ext = ext[:-1]
        if len(ext) < 3:
            continue
        for q in ext:
            xy += [float(q[0]) - o[0], float(q[1]) - o[1]]
        nz.append(len(ext))
        ids.append(x["id"])
    return xy, nz, ids

def lire(sop):
    hda = _hda(sop)
    chemin = hda.evalParm("fichier")
    brut = open(chemin, "rb").read()
    m = json.loads(brut.decode("utf-8"))
    o = m["repere"]["origine_l93"]
    geo = sop.geometry()

    def h(q):
        return (float(q[0]) - o[0], 0.0, -(float(q[1]) - o[1]))

    def loc(q):
        return (float(q[0]) - o[0], float(q[1]) - o[1], 0.0)

    for nom, d in (("carrefour", ""), ("branche", ""), ("route", ""), ("extremite", ""), ("regle_coin", ""),
                   ("regime", ""), ("ligne_type", ""), ("passage", ""), ("ilot", ""), ("id", ""), ("refuge", "")):
        _attr(geo, "point", nom, d)
    for nom in ("s_front", "azimut", "rayon_coin", "ligne_distance", "s", "largeur"):
        _attr(geo, "point", nom, 0.0)
    for nom in ("rang", "abaisses", "bev"):
        _attr(geo, "point", nom, 0)
    for nom in ("centre", "axe0", "axe1"):
        _attr(geo, "point", nom, (0.0, 0.0, 0.0))
    for nom, d in (("id", ""), ("gabarit", ""), ("couleur", ""), ("route", ""), ("carrefour", ""), ("branche", ""),
                   ("type", ""), ("pp_route", ""), ("pp_bande", ""), ("materiau", ""), ("ceinture", ""),
                   ("contour", ""), ("trajectoire", ""), ("vehicule", ""), ("mouvement", ""), ("de_branche", ""),
                   ("vers_branche", ""), ("remplissage", "")):
        _attr(geo, "prim", nom, d)
    for nom in ("s", "pp_s0", "pp_s1", "nez_rayon", "surelevation", "ceinture_vue", "refuge_largeur"):
        _attr(geo, "prim", nom, 0.0)
    for nom in ("porte", "faisable"):
        _attr(geo, "prim", nom, 0)
    g_br = geo.createPointGroup("branche")
    geo.addArrayAttrib(hou.attribType.Point, "pp_zxy", hou.attribData.Float)
    geo.addArrayAttrib(hou.attribType.Point, "pp_zn", hou.attribData.Int)
    geo.addArrayAttrib(hou.attribType.Point, "pp_zid", hou.attribData.String)
    g_pa = geo.createPointGroup("passage")
    g_li = geo.createPrimGroup("ligne")
    g_pl = geo.createPrimGroup("passage_libre")
    g_il = geo.createPrimGroup("ilot")
    g_ba = geo.createPrimGroup("balayage")
    g_tr = geo.createPrimGroup("trajectoire")
    n_br = 0
    for c in m.get("carrefours", []):
        if c.get("type") in ("giratoire", "mini_giratoire", "bifurcation"):
            continue                                   # lots giratoires et autoroutes
        cid = c["id"]
        ctr = loc(c["centre"])
        brs = sorted(c["branches"], key=lambda b: float(b.get("azimut_deg", 0.0)) % 360.0)
        for k, b in enumerate(brs):
            p = geo.createPoint()
            g_br.add(p)
            n_br += 1
            p.setPosition(h(c["centre"]))
            la = b.get("ligne_arret") or {}
            cd = b.get("coin_droit") or {}
            vals = {"carrefour": cid, "branche": b["id"], "route": b["route"], "extremite": b.get("extremite", ""),
                    "regime": b.get("regime", ""), "ligne_type": la.get("type", ""), "passage": b.get("passage_pieton", "") or "",
                    "ilot": b.get("ilot_separateur", "") or "", "regle_coin": cd.get("regle", "")}
            for kk, v in vals.items():
                p.setAttribValue(kk, str(v))
            p.setAttribValue("s_front", float(b.get("s_frontiere_m", -1.0)))
            p.setAttribValue("azimut", float(b.get("azimut_deg", 0.0)) % 360.0)
            p.setAttribValue("rayon_coin", float(cd.get("rayon_m", -1.0)))
            p.setAttribValue("ligne_distance", float(la.get("distance_m", 0.0) or 0.0))
            p.setAttribValue("rang", k)
            p.setAttribValue("centre", ctr)
        for pp_ in c.get("passages_pieton", []):
            p = geo.createPoint()
            g_pa.add(p)
            ax = pp_.get("axe") or [c["centre"], c["centre"]]
            p.setPosition(h(ax[0]))
            p.setAttribValue("id", pp_["id"])
            p.setAttribValue("route", pp_.get("route", ""))
            p.setAttribValue("carrefour", cid)
            p.setAttribValue("s", float(pp_.get("s", 0.0)))
            p.setAttribValue("largeur", float(pp_.get("largeur_m", 4.0)))
            p.setAttribValue("axe0", loc(ax[0]))
            p.setAttribValue("axe1", loc(ax[-1]))
            p.setAttribValue("refuge", str(pp_.get("refuge") or ""))
            p.setAttribValue("abaisses", 1 if pp_.get("abaisses", True) else 0)
            p.setAttribValue("bev", 1 if pp_.get("bev", True) else 0)
            zxy, zn, zid = _zones_passage(m, pp_.get("route", ""), pp_.get("s", 0.0), o)
            p.setAttribValue("pp_zxy", zxy)
            p.setAttribValue("pp_zn", zn)
            p.setAttribValue("pp_zid", zid)
        for t in c.get("trajectoires", []):
            g = t.get("geometrie") or []
            if len(g) < 2:
                continue
            pr = _poly(geo, [h(q) for q in g], False)
            g_tr.add(pr)
            pr.setAttribValue("id", t["id"])
            pr.setAttribValue("carrefour", cid)
            pr.setAttribValue("mouvement", t.get("mouvement", ""))
            pr.setAttribValue("de_branche", (t.get("de") or {}).get("branche", ""))
            pr.setAttribValue("vers_branche", (t.get("vers") or {}).get("branche", ""))
    for x in m.get("marquages", []):
        an = x.get("ancrage") or {}
        g = x.get("geometrie")
        if x.get("type") == "ligne_transversale" and isinstance(g, list) and len(g) >= 2:
            pr = _poly(geo, [h(q) for q in g], False)
            g_li.add(pr)
            for kk, v in (("id", x["id"]), ("gabarit", x.get("gabarit", "")), ("couleur", x.get("couleur", "blanc")),
                          ("route", an.get("route", "")), ("carrefour", an.get("carrefour", "")),
                          ("branche", an.get("branche", "")), ("type", x["type"])):
                pr.setAttribValue(kk, str(v))
            pr.setAttribValue("s", float(an.get("s", -1.0) if an.get("s") is not None else -1.0))
        elif x.get("type") == "passage_pieton" and not an.get("route") and isinstance(g, dict):
            ext = g.get("exterieur") or []
            if ext and ext[0] == ext[-1]:
                ext = ext[:-1]
            if len(ext) < 3:
                continue
            pr = _poly(geo, [h(q) for q in ext], True)
            g_pl.add(pr)
            for kk, v in (("id", x["id"]), ("couleur", x.get("couleur", "blanc")), ("carrefour", an.get("carrefour", "")),
                          ("branche", an.get("branche", "")), ("type", x["type"])):
                pr.setAttribValue(kk, str(v))
    for i in m.get("ilots", []):
        pg = (i.get("polygone") or {}).get("exterieur") or []
        if pg and pg[0] == pg[-1]:
            pg = pg[:-1]
        if len(pg) < 3:
            continue
        pr = _poly(geo, [h(q) for q in pg], True)
        g_il.add(pr)
        tp = i.get("terre_plein") or {}
        pp_ = i.get("porte_par_profil") or {}
        nez = i.get("nez") or []
        ce = tp.get("ceinture") or {}
        rem = tp.get("remplissage") or {}
        for kk, v in (("id", i["id"]), ("type", i.get("type", "")), ("carrefour", i.get("carrefour", "")),
                      ("pp_route", pp_.get("route", "")), ("pp_bande", pp_.get("bande", "")),
                      ("materiau", rem.get("materiau_id", "")), ("remplissage", rem.get("type", "")),
                      ("ceinture", ce.get("profil", "")),
                      ("contour", _txt(tp.get("marquage_contour")) if tp.get("marquage_contour") else "")):
            pr.setAttribValue(kk, str(v))
        pr.setAttribValue("porte", 1 if pp_ else 0)
        pr.setAttribValue("pp_s0", float(pp_.get("s0", 0.0)))
        pr.setAttribValue("pp_s1", float(pp_.get("s1", 0.0)))
        pr.setAttribValue("nez_rayon", float(nez[0].get("rayon_m", 0.5)) if nez else 0.5)
        pr.setAttribValue("surelevation", float(tp.get("surelevation_m", 0.0) or 0.0))
        pr.setAttribValue("ceinture_vue", float(ce.get("vue_m", tp.get("surelevation_m", 0.0)) or 0.0))
        pr.setAttribValue("refuge_largeur", float((i.get("refuge") or {}).get("largeur_m", 0.0) or 0.0))
    # balayages des véhicules (lot L3a), calculés par le pilote : polygones (anneau extérieur) en local
    fb = hda.evalParm("balayages")
    n_ba = 0
    if fb and os.path.exists(fb):
        bal = json.loads(open(fb, "rb").read().decode("utf-8"))
        for e in bal.get("balayages", []):
            ext = e.get("exterieur") or []
            if len(ext) < 3:
                continue
            pr = _poly(geo, [(float(x), 0.0, -float(y)) for x, y in ext], True)
            g_ba.add(pr)
            n_ba += 1
            for kk, v in (("trajectoire", e.get("trajectoire", "")), ("vehicule", e.get("vehicule", "")),
                          ("carrefour", e.get("carrefour", "")), ("mouvement", e.get("mouvement", "")),
                          ("de_branche", e.get("de_branche", "")), ("vers_branche", e.get("vers_branche", ""))):
                pr.setAttribValue(kk, str(v))
            pr.setAttribValue("faisable", 1 if e.get("faisable") else 0)
    geo.addAttrib(hou.attribType.Global, "rg_carrefours", "")
    geo.setGlobalAttribValue("rg_carrefours", _txt({
        "fichier": chemin.replace("\\", "/"), "sha256": hashlib.sha256(brut).hexdigest(),
        "branches": n_br, "balayages": n_ba, "origine_l93": [o[0], o[1]]}))
