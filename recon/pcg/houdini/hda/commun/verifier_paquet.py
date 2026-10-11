"""Vérifie que le paquet d'HDA pour Unreal est autonome (hython Houdini 22, session neuve).

    hython recon/pcg/houdini/hda/commun/verifier_paquet.py PAQUET.hdalc DOSSIER_DESCRIPTION_BASE

N'installe QUE le paquet, cuit pj::lire_description (emprise pilote), puis pj::niveau_z et pj::preparer_export sur les
îlots, et imprime une ligne « PJ_JSON{...} ». L'essai par HAPI direct (essai_houdini_engine.py) est refusé par la
licence Houdini Engine Indie hors plugins agréés : l'essai Houdini Engine proprement dit se fait dans Unreal.
"""
import json
import sys

import hou

paquet, description = sys.argv[1], sys.argv[2]
hou.hda.installFile(paquet)
g = hou.node("/obj").createNode("geo")
lire = g.createNode("pj::lire_description::1.0")
lire.parm("emprise").set("pilote")
lire.parm("dossier").set(description)
b = g.createNode("blast")
b.setInput(0, lire)
b.parm("group").set("f_ilots")
b.parm("negate").set(1)
tri = g.createNode("triangulate2d::3.0")
tri.setInput(0, b)
tri.parm("useconstrpolys").set(1)
tri.parm("constrpolys").set("*")
tri.parm("removefromconstrpolys").set(1)
z = g.createNode("pj::niveau_z::1.0")
z.setInput(0, tri)
z.setInput(1, lire, 1)
e = g.createNode("pj::preparer_export::1.0")
e.setInput(0, z)
r = {"entites": lire.geometry(0).intrinsicValue("primitivecount"),
     "volumes": lire.geometry(1).intrinsicValue("primitivecount"),
     "export_primitives": e.geometry().intrinsicValue("primitivecount"),
     "erreurs": [n.path() for n in (lire, z, e) if n.errors()],
     "bibliotheques": sorted({t.definition().libraryFilePath() for t in hou.sopNodeTypeCategory().nodeTypes().values()
                              if t.name().startswith("pj::") and t.definition()})}
print("PJ_JSON" + json.dumps(r, ensure_ascii=False))
