# Python SOP pour Houdini 22 : crée le profil de bordure choisi depuis assets/specs/bordures.json,
# prêt à servir de section (2e entrée) d'un Sweep SOP.
#
# Mise en place : Geometry › Python SOP › coller ce code dans « Python Code », puis ajouter sur le nœud
# (Edit Parameter Interface) les paramètres :
#   json    (String)  chemin de bordures.json, ex. $HIP/../assets/specs/bordures.json
#   profil  (String)  T1, T2, T3, T2_bateau, A1, A2, P1, P2, P3, CS1, CS2, CC1, CC2, I1, I2, IL, QUAI_BUS, PAVES_GRANIT
#   vue     (Float)   hauteur de vue en m (0 = profil « bloc », origine sous le bloc)
# Repère produit : plan XY de Houdini, X = u (vers l'arrière de la bordure / le trottoir), Y = v (haut),
# origine = pied de la face vue au niveau de la chaussée si vue > 0 (sinon coin avant bas du bloc).
# Sweep : 1re entrée = courbe de bordure (Y-up), 2e entrée = ce profil ; Up Vector = +Y monde ; si la face
# vue regarde le mauvais côté, mettre un Reverse sur la courbe. Pour une vue variable le long de la
# courbe (abaissés, chartières), utiliser vue = 0 puis décaler le Sweep par point (attribut « vue »).
import json

import hou

node = hou.pwd()
geo = node.geometry()


def _parm(nom, defaut):
    p = node.parm(nom)
    return p.eval() if p is not None else defaut


chemin = hou.text.expandString(_parm("json", "$HIP/../assets/specs/bordures.json"))
nom = _parm("profil", "T2") or "T2"
vue = float(_parm("vue", 0.14))

with open(chemin, "r", encoding="utf-8") as f:
    data = json.load(f)
profils = data["profils"]
if nom not in profils:
    raise hou.NodeError("profil inconnu : %s (disponibles : %s)" % (nom, ", ".join(sorted(profils))))
prof = profils[nom]
contour = prof["contour"]

if nom.startswith("CS") or nom.startswith("CC"):
    # caniveau : dessus côté chaussée au niveau de la chaussée
    dv = -max(contour[1][1], contour[2][1]) if vue > 0 else 0.0
else:
    H = max(v for _, v in contour)
    dv = -(H - vue) if vue > 0 else 0.0

poly = geo.createPolygon()
for u, v in contour:
    pt = geo.createPoint()
    pt.setPosition((u, v + dv, 0.0))
    poly.addVertex(pt)
poly.setIsClosed(True)

geo.addAttrib(hou.attribType.Global, "profil", "")
geo.addAttrib(hou.attribType.Global, "vue_m", 0.0)
geo.addAttrib(hou.attribType.Global, "section_cm", "")
geo.setGlobalAttribValue("profil", nom)
geo.setGlobalAttribValue("vue_m", vue)
geo.setGlobalAttribValue("section_cm", prof.get("section_cm", ""))
