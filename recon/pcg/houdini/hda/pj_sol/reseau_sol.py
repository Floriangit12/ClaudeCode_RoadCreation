"""Éléments de réseau partagés par pj::sol et pj::ilot (scripts de construction, hython Houdini 22) : corps des
wrangles (sections « //@@ <nom> » des fichiers vex/*.vfl), en-têtes VEX, Blast, boucle compilée de triangulation
contrainte par surface (Triangulate 2D, TQ-SOL-002)."""
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
HDA = ICI.parent
sys.path.insert(0, str(HDA / "commun"))
import pj_hda_outils as O  # noqa: E402

VEX = ICI / "vex"
VEX_B = HDA / "pj_bordure" / "vex"


def corps(fichier, section, dossier=VEX):
    t = (Path(dossier) / fichier).read_text(encoding="utf-8")
    for p in t.split("//@@ ")[1:]:
        nom, _, reste = p.partition(chr(10))
        if nom.strip() == section:
            return reste
    raise KeyError(section)


def entetes(courbe=False, sol=False):
    t = O.vex("pj_niveau.h", "pj_repere.h")
    if courbe:
        t += (VEX_B / "pj_courbe.h").read_text(encoding="utf-8") + chr(10)
    if sol:
        t += (VEX / "pj_sol.h").read_text(encoding="utf-8") + chr(10)
    return t


def blast(sub, nom, src, groupe, garder=True, points=False):
    b = sub.createNode("blast", nom)
    b.setInput(0, src)
    b.parm("group").set(groupe)
    b.parm("negate").set(1 if garder else 0)
    if points:
        b.parm("grouptype").set(3)
    return b


def boucle_triangulation(sub, ech):
    """Boucle compilée For-Each par id : Triangulate 2D contraint et raffiné (arête cible 1 sur la géométrie divisée par
    arete_cible), trous retirés, attributs de la surface ; renvoie echelle_inverse (géométrie à l'échelle, Y = 0)."""
    # ---- boucle compilée : une triangulation contrainte par surface
    cb = sub.createNode("compile_begin", "compile_debut")
    cb.setInput(0, ech)
    fb = sub.createNode("block_begin", "pour_chaque_surface")
    fb.setInput(0, cb)
    fb.parm("method").set(1)                  # pièce
    # trous (anneau >= 1) retournés : le lecteur oriente TOUS les anneaux en +Y (faces de sol) ; Triangulate 2D ne
    # retire un polygone de contrainte que s'il est d'enroulement opposé à l'extérieur. Sans ce retournement, l'aire
    # de l'extérieur était maillée en entier (S-0094a : 14 722 m² au lieu de 11 598 m², sol en double couche sous
    # S-0129*, S-0163 ; revues conformité et réalisme 11/10/2026, TQ-SOL-009, TQ-SOL-001).
    rt = sub.createNode("reverse", "retourner_trous")
    rt.setInput(0, fb)
    rt.parm("group").set("@anneau>0")
    tri = sub.createNode("triangulate2d::3.0", "trianguler")
    tri.setInput(0, rt)
    for p, v in (("planepossrc", 1), ("dirx", 0.0), ("diry", 1.0), ("dirz", 0.0), ("useconstrpolys", 1),
                 ("constrpolys", "*"), ("removefromconstrpolys", 1), ("refine", 1), ("trianglesize", 2),
                 ("targetedgelength", 1.0), ("minedgelength", 0.02), ("allowconstrsplit", 0), ("maxnewpts", 2000000),
                 ("updatenmls", 0)):
        tri.parm(p).set(v)
    tri.parm("minangle").setExpression('ch("../angle_min")')
    trous = blast(sub, "trous_piece", fb, "@anneau>0")
    tr = O.wrangle(sub, "trous", corps("sol.vfl", "trous"), "primitive", tri, entrees=(trous,))
    at = O.wrangle(sub, "attributs", corps("sol.vfl", "attributs"), "primitive", tr, entrees=(fb,))
    fe = sub.createNode("block_end", "fin_pour_chaque")
    fe.setInput(0, at)
    for p, v in (("itermethod", 1), ("method", 1), ("class", 0), ("useattrib", 1), ("attrib", "id"),
                 ("blockpath", "../pour_chaque_surface"), ("templatepath", "../pour_chaque_surface"), ("multithread", 1)):
        fe.parm(p).set(v)
    fb.parm("blockpath").set("../fin_pour_chaque")
    ce = sub.createNode("compile_end", "compile_fin")
    ce.setInput(0, fe)
    cb.parm("blockpath").set("../compile_fin")
    inv = O.wrangle(sub, "echelle_inverse", corps("sol.vfl", "echelle_inverse"), "point", ce)
    return inv
