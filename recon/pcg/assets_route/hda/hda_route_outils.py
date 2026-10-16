"""Outils de construction des HDA route::* (bibliothèque d'assets de la route, hython Houdini 22 Indie).

Même principe que recon/pcg/houdini/hda/commun/pj_hda_outils.py (format développé versionné, signature de
construction pour éviter les diffs parasites des HDA Indie), avec l'espace de noms « route » :

    import hda_route_outils as O
    sub = O.sous_reseau("extrusion_profil")
    ... hou.createNode / setInput / parm().set() ...
    O.creer_hda(sub, "extrusion_profil", "Route Extrusion de profil", parms, O.DOSSIER)   # -> hda/route_extrusion_profil.hdalc/

Python n'est utilisé que pour construire les réseaux (hou.createNode) ; toute la géométrie est produite par les nœuds
SOP et les wrangles VEX à la cuisson.
"""
import hashlib
import shutil
import tempfile
from pathlib import Path

import hou

DOSSIER = Path(__file__).resolve().parent                 # recon/pcg/assets_route/hda
ESPACE = "route"
VERSION = "1.0"
VERSION_OUTILS = "1"


def nom_type(nom):
    return f"{ESPACE}::{nom}::{VERSION}"


def sous_reseau(nom):
    obj = hou.node("/obj/_construction_route") or hou.node("/obj").createNode("geo", "_construction_route")
    for c in obj.children():
        if c.name() == nom:
            c.destroy()
    return obj.createNode("subnet", nom)


def wrangle(sub, nom, code, classe="point", entree=None, entrees=()):
    w = sub.createNode("attribwrangle", nom)
    w.parm("class").set({"detail": 0, "primitive": 1, "point": 2, "sommet": 3}[classe])
    w.parm("snippet").set(code)
    if entree is not None:
        w.setInput(0, entree)
    for k, e in enumerate(entrees):
        if e is not None:
            w.setInput(k + 1, e)
    return w


def sortie(sub, source, index=0, nom=None):
    o = sub.createNode("output", nom or f"sortie_{index + 1}")
    o.parm("outputidx").set(index)
    o.setInput(0, source)
    return o


def _aide(etiquette, resume, parms, details=""):
    L = [f"= {etiquette} =", "", f'"""{resume}"""', ""]
    if details:
        L += [details, ""]
    L += ["@parameters", ""]

    def parcourir(tpls):
        for t in tpls:
            if isinstance(t, hou.FolderParmTemplate):
                L.append(f"== {t.label()} ==")
                L.append("")
                parcourir(t.parmTemplates())
            elif not isinstance(t, (hou.SeparatorParmTemplate, hou.LabelParmTemplate)):
                L.append(f"{t.label()}:")
                L.append(f"    #id: {t.name()}")
                L.append(f"    {t.help() or ''}")
                L.append("")
    parcourir(parms)
    return "\n".join(L) + "\n"


def creer_hda(sub, nom, etiquette, parms, dossier=DOSSIER, entrees=(0, 0), aide="", details=""):
    """Convertit `sub` en HDA route::<nom>::1.0, l'enregistre, la développe en <dossier>/route_<nom>.hdalc/ et l'installe."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / f"route_{nom}.hdalc"
    signature = hashlib.sha256("\n".join([
        hou.applicationVersionString(), sub.asCode(brief=False, recurse=True),
        hou.ParmTemplateGroup(parms).asDialogScript(), aide, details, repr(entrees), VERSION_OUTILS]).encode("utf-8")).hexdigest()
    existante = list(cible.glob("*/RouteSignature")) if cible.exists() else []
    if existante and existante[0].read_text(encoding="utf-8").strip() == signature:
        sub.destroy()
        hou.hda.installFile(str(cible))
        return cible
    tmp = Path(tempfile.mkdtemp(prefix="route_hda_")) / f"route_{nom}.hdalc"
    nt = nom_type(nom)
    ancien = hou.nodeType(hou.sopNodeTypeCategory(), nt)
    if ancien is not None and ancien.definition() is not None:
        for d in ancien.allInstalledDefinitions():
            try:
                hou.hda.uninstallFile(d.libraryFilePath())
            except hou.OperationFailed:
                pass
    noeud = sub.createDigitalAsset(name=nt, hda_file_name=str(tmp), description=etiquette, min_num_inputs=entrees[0],
                                   max_num_inputs=entrees[1], ignore_external_references=True, change_node_type=True,
                                   create_backup=False)
    d = noeud.type().definition()
    d.setParmTemplateGroup(hou.ParmTemplateGroup(parms))
    d.setIcon("SOP_subnet")
    d.setVersion(VERSION)
    d.setComment(f"{etiquette} (recon/pcg/assets_route/hda, bibliothèque route_fr)")
    d.addSection("Help", _aide(etiquette, aide, parms, details))
    d.addSection("RouteSignature", signature + "\n")
    o = d.options()
    o.setCompressContents(False)
    o.setLockContents(True)
    o.setSaveInitialParmsAndContents(False)
    o.setUnlockNewInstances(False)
    d.setOptions(o)
    d.updateFromNode(noeud)
    d.save(str(tmp), noeud, o)
    for f in (cible, tmp):
        try:
            hou.hda.uninstallFile(str(f))
        except hou.OperationFailed:
            pass
    if cible.exists():
        shutil.rmtree(cible)
    hou.hda.expandToDirectory(str(tmp), str(cible))
    shutil.rmtree(tmp.parent, ignore_errors=True)
    hou.hda.installFile(str(cible))
    return cible


def installer_tout(dossier=DOSSIER):
    for c in sorted(Path(dossier).glob("route_*.hdalc")):
        hou.hda.installFile(str(c))


# ---------------------------------------------------------------------------------------------- VEX communs
VEX_UV_BOITE = r"""
// UV en mètres par projection « boîte » selon la normale de la face (vertex wrangle)
vector n = prim_normal(0, @primnum, 0.5, 0.5);
vector a = abs(n);
vector p = @P;
if (a.y >= a.x && a.y >= a.z)      v@uv = set(p.x, -p.z * sign(n.y), 0);
else if (a.x >= a.z)               v@uv = set(-p.z * sign(n.x), p.y, 0);
else                               v@uv = set(p.x * sign(n.z), p.y, 0);
"""


def chaine_finale(sub, source, cusp_parm="../cusp", lod_parm="../lod_pourcentage"):
    """Normales à angle de coupure, réduction LOD (PolyReduce, si < 100 %), normales finales, sortie 1."""
    mv = sub.createNode("attribwrangle", "materiau_par_defaut")
    mv.parm("class").set(1)
    mv.parm("snippet").set('if (s@materiau == "") s@materiau = chs("../materiau");')
    mv.setInput(0, source)
    source = mv
    uvf = sub.createNode("attribwrangle", "uv_manquants")
    uvf.parm("class").set(3)
    uvf.parm("snippet").set("if (length(v@uv) < 1e-9) {" + VEX_UV_BOITE + "}")
    uvf.setInput(0, source)
    source = uvf
    red = sub.createNode("polyreduce::2.0", "lod_reduction")
    red.setInput(0, source)
    red.parm("target").set("poly_percent")
    red.parm("percentage").setExpression(f'ch("{lod_parm}")')
    sw = sub.createNode("switch", "si_lod")
    sw.setInput(0, source)
    sw.setInput(1, red)
    sw.parm("input").setExpression(f'ch("{lod_parm}") < 99.999')
    nm = sub.createNode("normal", "normales")
    nm.setInput(0, sw)
    nm.parm("type").set("typevertex")
    nm.parm("cuspangle").setExpression(f'ch("{cusp_parm}")')
    nett = sub.createNode("attribdelete", "nettoyer")
    nett.setInput(0, nm)
    nett.parm("ptdel").set("s pc rref Cd")
    nett.parm("primdel").set("piece couleur picto")
    return sortie(sub, nett, 0)


def parms_communs(T=hou, cusp=35.0, lod=100.0, materiau=""):
    return [
        T.FloatParmTemplate("cusp", "Angle de coupure des normales (°)", 1, default_value=(cusp,), min=0.0, max=180.0,
                            help="Arêtes plus vives que cet angle : normales dures ; en dessous (congés), normales lissées."),
        T.FloatParmTemplate("lod_pourcentage", "LOD : polygones conservés (%)", 1, default_value=(lod,), min=1.0, max=100.0,
                            help="100 = LOD0 (aucune réduction) ; LOD1 ≈ 50 %, LOD2 ≈ 20 % (PolyReduce 2.0)."),
        T.StringParmTemplate("materiau", "Matériau", 1, default_value=(materiau,),
                             help="Nom du matériau (bibliothèque route_fr ou assets/lib/materiaux) posé dans l'attribut "
                                  "de primitive « materiau »."),
    ]
