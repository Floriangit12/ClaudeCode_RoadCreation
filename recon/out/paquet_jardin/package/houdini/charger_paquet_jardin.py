"""Houdini 22 — charge la scène « Paquet Jardin, octobre 2026 » (USD) dans Solaris et en SOP.

Lancement (au choix) :
  - File > Run Script... puis choisir ce fichier ;
  - Windows > Python Shell :
        exec(open(r"C:/.../package/houdini/charger_paquet_jardin.py", encoding="utf-8").read())

Le script crée :
  /stage/paquet_jardin        Sublayer LOP sur paquet_jardin_2026.usda (scène complète, matériaux)
  /stage/lumieres             soleil + ciel (pour un premier rendu Karma)
  /obj/paquet_jardin_sop      LOP Import + Unpack USD -> géométrie SOP éditable (attributs USD
                              conservés : classe, etat, type, usure, couverture...), passée en Y-up
Rien n'est écrasé : si les nœuds existent déjà, ils sont recréés avec un suffixe.

Repère : la scène est en mètres, Z vers le haut (métadonnée USD upAxis = Z), origine locale
O = Lambert-93 (917279.43, 6460289.98) / NGF-IGN69 216.30 m. Le côté SOP de Houdini étant Y-up,
le réseau SOP applique une rotation de -90° autour de X : (x, y, z) -> (x, z, -y).
Si, dans Solaris, la scène apparaît couchée, passe ROTATION_SOLARIS à True.
"""
import os

import hou

PKG = None               # dossier « package » ; détecté automatiquement si None
ROTATION_SOLARIS = False # True : ajoute un Transform LOP -90° autour de X (vue Y-up)
CREER_SOP = True


def trouver_paquet():
    if PKG:
        return PKG
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass
    f = hou.ui.selectFile(title="Choisir paquet_jardin_2026.usda", pattern="*.usda",
                          file_type=hou.fileType.Any)
    if not f:
        raise SystemExit("aucun fichier choisi")
    return os.path.dirname(hou.text.expandString(f))


def creer(parent, type_noeud, nom):
    try:
        return parent.createNode(type_noeud, nom)
    except hou.OperationFailed:
        return parent.createNode(type_noeud, nom + "_1")


def regler(noeud, noms, valeur):
    """Règle le premier paramètre existant parmi « noms » (les noms varient selon les versions)."""
    for n in noms:
        p = noeud.parm(n)
        if p is not None:
            p.set(valeur)
            return n
    print("  [attention] paramètre introuvable sur", noeud.path(), ":", noms)
    return None


def main():
    pkg = trouver_paquet().replace("\\", "/")
    usda = f"{pkg}/paquet_jardin_2026.usda"
    if not os.path.exists(usda):
        raise SystemExit(f"introuvable : {usda}")
    print("Paquet :", pkg)

    # --- Solaris ---------------------------------------------------------------------------
    stage = hou.node("/stage")
    sub = creer(stage, "sublayer", "paquet_jardin")
    regler(sub, ["filepath1", "filepath"], usda)
    dernier = sub
    if ROTATION_SOLARIS:
        xf = creer(stage, "xform", "vers_y_up")
        xf.setInput(0, dernier)
        regler(xf, ["primpattern"], "/World")
        regler(xf, ["rx"], -90)
        dernier = xf
    try:
        sun = creer(stage, "distantlight", "soleil")
        sun.setInput(0, dernier)
        regler(sun, ["xn__inputsintensity_i0a", "intensity"], 3.0)
        regler(sun, ["rx"], -50)
        regler(sun, ["ry"], 35)
        dome = creer(stage, "domelight", "ciel")
        dome.setInput(0, sun)
        regler(dome, ["xn__inputsintensity_i0a", "intensity"], 0.6)
        dernier = dome
    except Exception as e:  # noqa: BLE001
        print("  [info] lumières non créées :", e)
    dernier.setDisplayFlag(True)
    stage.layoutChildren()
    print("Solaris :", sub.path(), "->", dernier.path())

    # --- SOP ---------------------------------------------------------------------------------
    if CREER_SOP:
        geo = creer(hou.node("/obj"), "geo", "paquet_jardin_sop")
        imp = creer(geo, "lopimport", "import_usd")
        regler(imp, ["loppath"], sub.path())
        unp = creer(geo, "unpackusd", "deballer")
        unp.setInput(0, imp)
        regler(unp, ["output"], "polygons")
        xf = creer(geo, "xform", "vers_y_up")
        xf.setInput(0, unp)
        regler(xf, ["rx"], -90)
        out = creer(geo, "null", "OUT_paquet_jardin")
        out.setInput(0, xf)
        out.setDisplayFlag(True)
        out.setRenderFlag(True)
        geo.layoutChildren()
        print("SOP :", out.path(), "(attributs USD conservés : classe, etat, type, usure...)")
        print("  Exemples de raffinement : Group by attribute 'classe'=='bordure' -> PolyBevel ;")
        print("  Scatter sur 'espace_vert' -> herbe ; Labs Road/Decal tools sur les marquages.")
    print("Terminé.")


main()
