"""rg::signalisation : module Python embarqué (section PythonModule de l'HDA) — lecture du plan de signalisation.

Seul Python de l'HDA (README_HDA, préambule : Python réservé aux entrées-sorties) : le plan `rg_plan_signalisation/0.1`
(JSON, repère local de la scène, écrit par plan_signalisation.py) devient des points à attributs ; aucune opération
géométrique ici (placement, projection, contrôles : VEX). Conversion local (x, y) -> Houdini (x, 0, −y) une seule fois.

    lire_ensembles(sop)   un point par ensemble (support) : ancrage, support, hauteur, éléments en tableaux
    lire_exclusions(sop)  une polyligne par abaissé (bordure fabriquée, rôle bateau / chartière)
"""
import json
import os

import hou

SCHEMA = "rg_plan_signalisation/0.1"
_CACHE = {}


def _plan(sop):
    f = sop.parent().evalParm("fichier")
    if not f:
        raise hou.NodeError("paramètre « Plan de signalisation » vide")
    if not os.path.exists(f):
        raise hou.NodeError(f"plan introuvable : {f}")
    cle = (f, os.path.getmtime(f), os.path.getsize(f))
    if _CACHE.get("cle") != cle:
        with open(f, encoding="utf-8") as h:
            d = json.load(h)
        if d.get("schema") != SCHEMA:
            raise hou.NodeError(f"schéma {d.get('schema')} au lieu de {SCHEMA}")
        _CACHE.clear()
        _CACHE.update(cle=cle, d=d)
    return _CACHE["d"]


def _h(xy):
    return hou.Vector3(float(xy[0]), 0.0, -float(xy[1]))


PRIORITE = {"feu": 0, "potence": 1, "portique": 1}
CODES_REGIME = ("AB3a", "AB4", "AB25", "B21-1", "AB2", "J5", "J3", "J14a", "EB10", "EB20")


def priorite(e):
    """Ordre de pose (déterministe) : régimes et feux d'abord (ils prennent les meilleures places), puis le reste."""
    codes = [x["code"] for x in e["elements"]]
    if e["famille"] == "feu":
        return 0
    if any(c in CODES_REGIME for c in codes):
        return 1
    if e["famille"] in ("potence", "portique"):
        return 2
    return 3


def lire_ensembles(sop):
    d = _plan(sop)
    geo = sop.geometry()
    geo.clear()
    S, I, F, V = "s", "i", "f", "v"
    attrs = {"id": S, "famille": S, "source": S, "regles": S, "anc_type": S, "route": S, "s": F, "sens": I, "cote": S,
             "fen0": F, "fen1": F, "surface": S, "rayon": F, "dir": V, "vise": V, "a_vise": I, "face_az": F,
             "a_face_az": I, "support_type": S, "support_asset": S, "support_r": F, "support_h": F, "double": I,
             "bas": F, "regle_hauteur": S, "exclusif": I, "priorite": I, "l_max": F, "potence_voie": S,
             "portee": F, "portee_asset": F, "bas_asset": F, "n_el": I, "rural_plan": I}
    tab = {"el_code": "s[]", "el_kind": "s[]", "el_asset": "s[]", "el_gamme": "s[]", "el_face": "s[]", "el_l": "f[]",
           "el_h": "f[]", "el_zmin": "f[]", "el_zmax": "f[]", "el_z": "f[]", "el_rot": "f[]", "el_u": "f[]",
           "el_azabs": "f[]", "el_a_azabs": "i[]", "el_vise_arret": "i[]", "el_signal": "s[]", "el_echelle": "f[]", "el_voie": "s[]"}
    for n, t in attrs.items():
        geo.addAttrib(hou.attribType.Point, n, {"s": "", "i": 0, "f": 0.0, "v": (0.0, 0.0, 0.0)}[t])
    for n, t in tab.items():
        if t == "s[]":
            geo.addArrayAttrib(hou.attribType.Point, n, hou.attribData.String)
        elif t == "f[]":
            geo.addArrayAttrib(hou.attribType.Point, n, hou.attribData.Float)
        else:
            geo.addArrayAttrib(hou.attribType.Point, n, hou.attribData.Int)
    ens = sorted(d["ensembles"], key=lambda e: (priorite(e), e["id"]))
    for e in ens:
        a = e["ancrage"]
        p = geo.createPoint()
        if a["type"] == "xy":
            p.setPosition(_h(a["xy"]))
            dd = a.get("dir") or [1.0, 0.0]
            p.setAttribValue("dir", (float(dd[0]), 0.0, -float(dd[1])))
            p.setAttribValue("rayon", float(a.get("rayon", 3.0)))
        else:
            p.setAttribValue("route", a["route"])
            p.setAttribValue("s", float(a["s"]))
            p.setAttribValue("sens", int(a.get("sens", 1)))
            p.setAttribValue("cote", a.get("cote", "droite"))
            p.setAttribValue("fen0", float(a.get("fenetre", [-3.0, 1.0])[0]))
            p.setAttribValue("fen1", float(a.get("fenetre", [-3.0, 1.0])[1]))
            p.setAttribValue("rayon", float(a.get("rayon", 8.0)))
        if a.get("vise") is not None:
            p.setAttribValue("vise", (float(a["vise"][0]), 0.0, -float(a["vise"][1])))
            p.setAttribValue("a_vise", 1)
        if a.get("face_az") is not None:
            p.setAttribValue("face_az", float(a["face_az"]))
            p.setAttribValue("a_face_az", 1)
        p.setAttribValue("anc_type", e["famille"] if e["famille"] in ("potence", "portique") else a["type"])
        p.setAttribValue("surface", a.get("surface", "auto"))
        for k in ("id", "famille", "source"):
            p.setAttribValue(k, str(e[k]))
        p.setAttribValue("regles", " ".join(e.get("regles") or []))
        sup = e.get("support") or {}
        p.setAttribValue("support_type", sup.get("type", "poteau"))
        p.setAttribValue("support_asset", sup.get("asset", ""))
        p.setAttribValue("support_r", 0.5 * float(sup.get("diametre_m", 0.0603)))
        p.setAttribValue("support_h", float(sup.get("hauteur_m", 0.0)))
        p.setAttribValue("double", 1 if sup.get("double") else 0)
        p.setAttribValue("portee", float(sup.get("portee_m", 0.0)))
        p.setAttribValue("portee_asset", float(sup.get("portee_m", 16.0)))
        p.setAttribValue("bas_asset", float(sup.get("bas_asset_m", 0.0)))
        p.setAttribValue("potence_voie", (e.get("potence") or {}).get("voie", ""))
        p.setAttribValue("bas", float(e["bas"]))
        p.setAttribValue("regle_hauteur", str(e.get("regle_hauteur", "")))
        p.setAttribValue("exclusif", 1 if e.get("exclusif") else 0)
        p.setAttribValue("priorite", priorite(e))
        p.setAttribValue("rural_plan", 1 if e.get("rural") else 0)
        el = e["elements"]
        p.setAttribValue("n_el", len(el))
        p.setAttribValue("l_max", 0.0 if e["famille"] in ("potence", "portique") else
                         max([float(x["l"]) for x in el if x["kind"] in ("plaque", "plaque_composee", "balise")] or [0.0]))
        p.setAttribValue("el_code", [x["code"] for x in el])
        p.setAttribValue("el_kind", [x["kind"] for x in el])
        p.setAttribValue("el_asset", [x.get("asset") or "" for x in el])
        p.setAttribValue("el_gamme", [x.get("gamme") or "" for x in el])
        p.setAttribValue("el_face", [x.get("face") or "" for x in el])
        for k, n in (("l", "el_l"), ("h", "el_h"), ("zmin", "el_zmin"), ("zmax", "el_zmax"), ("z", "el_z"),
                     ("rot", "el_rot"), ("u", "el_u")):
            p.setAttribValue(n, [float(x.get(k, 0.0)) for x in el])
        p.setAttribValue("el_azabs", [float(x.get("az_abs", 0.0)) for x in el])
        p.setAttribValue("el_a_azabs", [1 if x.get("az_abs") is not None else 0 for x in el])
        p.setAttribValue("el_vise_arret", [int(x.get("vise_arret", 0)) for x in el])
        p.setAttribValue("el_signal", [x.get("signal") or "" for x in el])
        p.setAttribValue("el_echelle", [float(x.get("echelle", 1.0)) for x in el])
        p.setAttribValue("el_voie", [x.get("voie") or "" for x in el])
    geo.addAttrib(hou.attribType.Global, "rg_plan_scene", d.get("scene", ""))
    geo.addAttrib(hou.attribType.Global, "rg_plan_ensembles", len(ens))


def lire_exclusions(sop):
    d = _plan(sop)
    geo = sop.geometry()
    geo.clear()
    geo.addAttrib(hou.attribType.Prim, "id", "")
    geo.addAttrib(hou.attribType.Prim, "profondeur", 0.0)
    geo.addAttrib(hou.attribType.Prim, "debord", 0.0)
    for x in d.get("exclusions") or []:
        pts = x["polyligne"]
        if len(pts) < 2:
            continue
        pr = geo.createPolygon(is_closed=False)
        for q in pts:
            pt = geo.createPoint()
            pt.setPosition(_h(q))
            pr.addVertex(pt)
        pr.setAttribValue("id", x["id"])
        pr.setAttribValue("profondeur", float(x.get("profondeur", 1.5)))
        pr.setAttribValue("debord", float(x.get("debord", 0.3)))
