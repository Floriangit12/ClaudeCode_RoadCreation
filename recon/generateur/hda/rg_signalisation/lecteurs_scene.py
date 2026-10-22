"""Lecteurs des sorties fabriquées d'une scène pour le pilote du lot L6 (Python SOP d'entrées-sorties, README_HDA
préambule) : aucune opération géométrique, conversion local (x, y, z) Z haut -> Houdini (x, z, −y) une seule fois.

    lire_sol(sop, dossier)          l2/sol_*.npy (sol total fabriqué : routes, carrefours, giratoires, autoroute)
    lire_references(sop, dossier)   l1/courbes_controle.json (références échantillonnées : prims « id », points « s »)
    lire_obstacles(sop, dossier)    autoroute/equipements.json (points des dispositifs de retenue -> carrés de 0,20 m)
"""
import json
from pathlib import Path

import hou
import numpy as np


def lire_sol(sop, dossier):
    d = Path(dossier) / "l2"
    geo = sop.geometry()
    geo.clear()
    pts = np.load(d / "sol_points.npy")
    faces = np.load(d / "sol_faces.npy")
    comptes = np.load(d / "sol_comptes.npy")
    attrs = np.load(d / "sol_attributs.npy")
    voc = json.loads((d / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    P = np.column_stack([pts[:, 0], pts[:, 2], -pts[:, 1]]).astype(np.float64)
    geo.createPoints([hou.Vector3(*p) for p in P])
    polys, k = [], 0
    for n in comptes:
        polys.append(tuple(int(i) for i in faces[k:k + n]))
        k += n
    geo.createPolygons(polys, True)
    geo.addAttrib(hou.attribType.Prim, "classe", "")
    geo.addAttrib(hou.attribType.Prim, "materiau_id", "")
    cl = [voc["classe"][int(a[4])] for a in attrs]
    mt = [voc["materiau_id"][int(a[5])] for a in attrs]
    geo.setPrimStringAttribValues("classe", cl)
    geo.setPrimStringAttribValues("materiau_id", mt)
    geo.addAttrib(hou.attribType.Global, "rg_sol_faces", len(comptes))


def lire_references(sop, dossier):
    c = json.loads((Path(dossier) / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    geo = sop.geometry()
    geo.clear()
    geo.addAttrib(hou.attribType.Prim, "id", "")
    geo.addAttrib(hou.attribType.Point, "s", 0.0)
    for r in c["routes"]:
        ref = r["reference"]
        pr = geo.createPolygon(is_closed=False)
        for s, x, y in zip(ref["s"], ref["x"], ref["y"]):
            p = geo.createPoint()
            p.setPosition(hou.Vector3(float(x), 0.0, -float(y)))
            p.setAttribValue("s", float(s))
            pr.addVertex(p)
        pr.setAttribValue("id", r["id"])


def lire_obstacles(sop, dossier):
    f = Path(dossier) / "autoroute" / "equipements.json"
    geo = sop.geometry()
    geo.clear()
    if not f.exists():
        return
    d = json.loads(f.read_text(encoding="utf-8"))
    pts = d.get("points") or []
    h = 0.10
    vus = set()
    for q in pts:
        cle = (round(q[0] / 0.2), round(q[1] / 0.2))     # un carré par maille de 0,20 m (emprise au sol)
        if cle in vus:
            continue
        vus.add(cle)
        x, y = float(q[0]), float(q[1])
        pr = geo.createPolygon()
        for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h)):
            p = geo.createPoint()
            p.setPosition(hou.Vector3(x + dx, 0.0, -(y + dy)))
            pr.addVertex(p)
