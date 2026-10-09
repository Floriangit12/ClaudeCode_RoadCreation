"""Houdini 22 — charge la scène « Paquet Jardin, octobre 2026 » (USD) dans Solaris et en SOP.

Lancement (au choix) :
  - File > Run Script... puis choisir ce fichier ;
  - Windows > Python Shell :
        exec(open(r"C:/.../package/houdini/charger_paquet_jardin.py", encoding="utf-8").read())
  - hython (sans interface), avec les surcharges ci-dessous en variables d'environnement.

Le script crée :
  /stage/paquet_jardin        Sublayer LOP sur paquet_jardin_2026.usda (scène complète, matériaux)
  /stage/soleil, /stage/ciel  Distant Light + Dome Light sous /World/Lumieres (premier rendu Karma)
  /obj/paquet_jardin_sop      LOP Import + Unpack USD -> géométrie SOP éditable, instances
                              (arbres, mobilier) développées ; primvars USD conservés en attributs
                              de primitive (classe, etat, type, usure, couverture, couleur,
                              classe_haute, path), st -> uv, st1 en attribut de point ; passée en Y-up
Rien n'est écrasé : si les nœuds existent déjà, Houdini ajoute un suffixe numérique aux nouveaux.

Repère : la scène est en mètres, Z vers le haut (métadonnée USD upAxis = Z), origine locale
O = Lambert-93 (917279.43, 6460289.98) / NGF-IGN69 216.30 m. Le côté SOP de Houdini étant Y-up,
le réseau SOP applique une rotation de -90° autour de X : (x, y, z) -> (x, z, -y).
Si, dans Solaris, la scène apparaît couchée, passe ROTATION_SOLARIS à True : /World (lumières et
caméras sous /World comprises) est alors tourné de -90° autour de X.

Surcharges sans éditer le fichier (utile depuis un script pilote, ex. recon/pc/houdini/creer_hip.py,
ou quand le script est lancé depuis recon/package_src/ où la détection par __file__ ne trouve pas
le paquet) :
  PAQUET_JARDIN_PKG=<dossier package>      dossier contenant paquet_jardin_2026.usda
  PAQUET_JARDIN_ROTATION_SOLARIS=1|0       remplace ROTATION_SOLARIS
  PAQUET_JARDIN_SOP=1|0                    remplace CREER_SOP
Testé avec Houdini 22.0.459 (types distantlight::2.0, domelight::3.0, lopimport::2.0, unpackusd::2.0).
"""
import os

import hou

PKG = None               # dossier « package » ; détecté automatiquement si None
ROTATION_SOLARIS = False # True : ajoute un Transform LOP -90° autour de X sur /World (vue Y-up)
CREER_SOP = True
SOLEIL_AZIMUT = 220      # direction d'où vient le soleil, degrés depuis le nord, sens horaire (220 = SO)
SOLEIL_ELEVATION = 50    # hauteur du soleil au-dessus de l'horizon, en degrés


def _oui(valeur, defaut):
    if valeur is None or valeur == "":
        return defaut
    return valeur.strip().lower() in ("1", "true", "oui", "yes", "on")


PKG = os.environ.get("PAQUET_JARDIN_PKG") or PKG
ROTATION_SOLARIS = _oui(os.environ.get("PAQUET_JARDIN_ROTATION_SOLARIS"), ROTATION_SOLARIS)
CREER_SOP = _oui(os.environ.get("PAQUET_JARDIN_SOP"), CREER_SOP)
USDA = "paquet_jardin_2026.usda"


def trouver_paquet():
    if PKG:
        return PKG
    try:
        ici = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # package/houdini/ -> package/ ; recon/package_src/houdini/ -> recon/out/paquet_jardin/package/
        for d in (ici, os.path.join(os.path.dirname(ici), "out", "paquet_jardin", "package")):
            if os.path.exists(os.path.join(d, USDA)):
                return os.path.normpath(d)
    except NameError:
        pass
    if not hou.isUIAvailable():
        raise SystemExit("paquet introuvable : définir PAQUET_JARDIN_PKG (dossier « package »)")
    f = hou.ui.selectFile(title="Choisir " + USDA, pattern="*.usda", file_type=hou.fileType.Any)
    if not f:
        raise SystemExit("aucun fichier choisi")
    return os.path.dirname(hou.text.expandString(f))


def creer(parent, type_noeud, nom):
    return parent.createNode(type_noeud, nom)  # Houdini ajoute un suffixe si le nom est pris


def regler(noeud, noms, valeur):
    """Règle le premier paramètre existant parmi « noms » (les noms varient selon les versions).
    Un tuple règle un paramètre vectoriel (couleur...)."""
    for n in noms:
        p = noeud.parmTuple(n) if isinstance(valeur, tuple) else noeud.parm(n)
        if p is not None:
            p.set(valeur)
            return n
    print("  [attention] paramètre introuvable sur", noeud.path(), ":", noms)
    return None


def lumiere(stage, type_noeud, nom, entree, intensite, exposition, couleur):
    """Lumière UsdLux sous /World/Lumieres (elle suit ROTATION_SOLARIS comme les caméras)."""
    n = creer(stage, type_noeud, nom)
    n.setInput(0, entree)
    regler(n, ["primpath"], f"/World/Lumieres/{nom}")
    regler(n, ["xn__inputsintensity_i0a", "intensity"], intensite)
    regler(n, ["xn__inputsexposure_vya", "exposure"], exposition)
    regler(n, ["xn__inputscolor_zta", "light_color"], couleur)
    return n


def main():
    pkg = trouver_paquet().replace("\\", "/")
    usda = f"{pkg}/{USDA}"
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
        # Soleil : une Distant Light UsdLux éclaire selon son axe local -Z. Dans la scène Z-up,
        # Rx = 90 - élévation incline cet axe vers le nord (soleil au sud), puis Rz = 180 - azimut
        # le tourne autour de la verticale (ordre de rotation par défaut : X puis Y puis Z).
        sun = lumiere(stage, "distantlight", "soleil", dernier, 1.0, 1.6, (1.0, 0.95, 0.88))
        regler(sun, ["rx"], 90 - SOLEIL_ELEVATION)
        regler(sun, ["ry"], 0)
        regler(sun, ["rz"], 180 - SOLEIL_AZIMUT)
        # Ciel : Dome Light uniforme bleuté, sans texture, visible en fond d'image dans Karma
        # (peu saturé : ombres à B/R ~1,4 comme sous un ciel clair réel)
        dome = lumiere(stage, "domelight", "ciel", sun, 1.0, -1.95, (0.7, 0.8, 1.0))
        regler(dome, ["xn__inputstexturefile_control_shbh"], "none")
        regler(dome, ["xn__inputskarmalightrenderlightgeo_control_y2bff"], "set")
        regler(dome, ["xn__inputskarmalightrenderlightgeo_xpbff"], 1)
        dernier = dome
    except Exception as e:  # noqa: BLE001
        print("  [info] lumières non créées :", e)
    dernier.setDisplayFlag(True)
    stage.layoutChildren()
    print("Solaris :", sub.path(), "->", dernier.path())

    # --- SOP ---------------------------------------------------------------------------------
    out = None
    if CREER_SOP:
        geo = creer(hou.node("/obj"), "geo", "paquet_jardin_sop")
        imp = creer(geo, "lopimport", "import_usd")
        regler(imp, ["loppath"], sub.path())
        # enfants des groupes /World/* : Houdini ne descend pas sous les prims sans type
        # (Marquages, Bordures, Batiments...) ; les PointInstancer sont développés.
        regler(imp, ["primpattern"], "/World/*/* - /World/Looks/*")
        regler(imp, ["importpointinstances"], 1)
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
    return {"sublayer": sub, "dernier_lop": dernier, "sop": out}


NOEUDS = main()
