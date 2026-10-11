"""Pilote batch de la fabrication procédurale v2 (hython Houdini 22.0.459, Indie) : scène maîtresse
recon/pcg/houdini/paquet_jardin_pcg.hip, HDA pj::* (recon/pcg/houdini/hda, README_HDA.md).

    hython recon/pcg/houdini/fabriquer_hda.py --construire-hda [--toutes]   # HDA communes + lecteur (+ branches)
    hython recon/pcg/houdini/fabriquer_hda.py --construire-hip              # (re)construit paquet_jardin_pcg.hip
    hython recon/pcg/houdini/fabriquer_hda.py [--emprise site|pilote] [--tuiles 64] [--sortie DIR]
                                              [--apercu] [--verifier-determinisme] [--branches b1,b2]
                                              [--comparer MANIFESTE]   # sorties identiques à celles d'un autre processus
    hython recon/pcg/houdini/fabriquer_hda.py --essai-export DIR            # chaîne d'export validée sur un réseau d'essai

Le pilote ne fait aucune géométrie : il ouvre la scène, règle les variables $PJ_DESCRIPTION / $PJ_SORTIE et l'emprise
du lecteur, cuit les réseaux, lance les USD ROP des branches dont l'HDA est installée, écrit les points pj_points/0.1
(bouton des HDA pj::exporter_points), la couche de matériaux, le paquet d'HDA pour Unreal et le manifeste.
Lancer avec PYTHONDONTWRITEBYTECODE=1.

Déterminisme entre processus : le JIT natif de VEX (HOUDINI_VEX_JIT_OPTIMIZE « native=on », réglage par défaut) donne,
d'un processus hython à l'autre, des résultats qui diffèrent au dernier bit (deux familles de résultats sur six
processus, mesuré le 11/10/2026 sur le nœud poser de pj::bordure), amplifiés ensuite jusqu'au mm par les Boolean et
PolyBevel. Le pilote se relance donc avec HOUDINI_VEX_DISABLE_JIT=1 (VEX interprété : six processus identiques à
l'octet), sauf option --vex-jit.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

if os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1" and "--vex-jit" not in sys.argv:
    sys.exit(subprocess.call([sys.executable] + sys.argv,
                             env=dict(os.environ, HOUDINI_VEX_DISABLE_JIT="1", PYTHONDONTWRITEBYTECODE="1")))

import hou  # noqa: E402

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[2]
HDA = ICI / "hda"
sys.path.insert(0, str(HDA / "commun"))
import pj_hda_outils as O  # noqa: E402

HIP = ICI / "paquet_jardin_pcg.hip"
DESCRIPTION = RACINE / "recon/out/paquet_jardin/v2/description/base"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
MATERIAUX_SOL = RACINE / "assets/specs/materiaux_sol.json"
PEINTURE = RACINE / "assets/specs/peinture.json"
VERIFIER_USD = RACINE / "recon/pcg/ue/contrat/verifier_usd.py"
GEO = "/obj/paquet_jardin"

# branche -> couche USD (/World/<couche>) ; HDA attendue pj::<branche>::1.0 sauf surcharge dans hda/commun/branches.json
BRANCHES = [("sol", "PJ_Sol"), ("bordures", "PJ_Bordures"), ("caniveaux", "PJ_Caniveaux"), ("ilots", "PJ_Ilots"),
            ("marquages_lignes", "PJ_Marquages"), ("passages", "PJ_Marquages"), ("symboles", "PJ_Marquages"),
            ("zones", "PJ_Marquages")]
# matériaux maison admis par le vérificateur (verifier_usd.MATERIAUX_MAISON) : albédo linéaire d'aperçu, rugosité
MAISON = {"mortier_joint": ((0.22, 0.22, 0.21), 0.9), "mortier_clair": ((0.42, 0.41, 0.38), 0.9),
          "bitume_pontage": ((0.035, 0.035, 0.035), 0.55), "herbe_touffe": ((0.06, 0.085, 0.035), 0.8),
          "eclat_brf": ((0.12, 0.08, 0.05), 0.85), "eclat_gravier": ((0.2, 0.2, 0.19), 0.8),
          "PJ_Neutre": ((0.5, 0.5, 0.5), 0.8)}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    try:
        return Path(p).resolve().relative_to(RACINE).as_posix()
    except ValueError:
        return Path(p).as_posix()


def types_branches():
    """branche -> nom de type d'HDA (défaut pj::<branche>::1.0, surcharges dans hda/commun/branches.json)."""
    t = {b: O.nom_type(b) for b, _ in BRANCHES}
    f = HDA / "commun" / "branches.json"
    if f.exists():
        t.update(json.loads(f.read_text(encoding="utf-8")).get("branches", {}))
    return t


def hda_installee(nom):
    nt = hou.nodeType(hou.sopNodeTypeCategory(), nom)
    return nt is not None and nt.definition() is not None


# ------------------------------------------------------------------------------------------------ construction
def construire_hda(toutes=False):
    sys.path.insert(0, str(HDA / "pj_lire_description"))
    import construire_commun
    import construire as construire_lecteur
    faits = [str(p) for p in construire_commun.construire()] + [str(construire_lecteur.construire())]
    if toutes:                                     # HDA des branches (agents F) : hda/<branche>/construire.py
        for s in sorted(HDA.glob("*/construire*.py")):
            if s.parent.name in ("commun", "pj_lire_description"):
                continue
            r = subprocess.run([sys.executable, str(s)], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            faits.append(f"{rel(s)} : code {r.returncode}")
    return faits


def _variables(description=DESCRIPTION, sortie=SORTIE):
    hou.hscript(f'set -g PJ_DESCRIPTION = "{Path(description).as_posix()}"')
    hou.hscript(f'set -g PJ_SORTIE = "{Path(sortie).as_posix()}"')
    hou.hscript("varchange")


def construire_hip(chemin=HIP):
    """Scène maîtresse : lecteur -> branches (HDA ou emplacements Null) -> préparation USD et points -> Solaris."""
    hou.hipFile.clear(suppress_save_prompt=True)
    O.installer_tout()
    _variables()
    tb = types_branches()
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "paquet_jardin")
    geo.setComment("Fabrication procédurale Paquet Jardin (README_HDA.md) : description v2 -> HDA pj::* -> USD + points")
    lire = geo.createNode("pj::lire_description::1.0", "lire_description")
    lire.parm("dossier").set("$PJ_DESCRIPTION")
    ent = geo.createNode("null", "ENTITES")
    ent.setInput(0, lire, 0)
    niv = geo.createNode("null", "NIVEAU")
    niv.setInput(0, lire, 1)
    vide = geo.createNode("null", "VIDE")
    vide.setComment("Géométrie vide : entrée des exports de points des branches sans sortie d'instances")
    for b, couche in BRANCHES:
        e = geo.createNode("blast", f"entrees_{b}")
        e.setInput(0, ent)
        e.parm("group").set(f"b_{b}")
        e.parm("negate").set(1)
        t = tb[b]
        if hda_installee(t):
            fab = geo.createNode(t, f"fab_{b}")
            n_ent = fab.type().maxNumInputs()
            etiq = fab.inputLabels() if hasattr(fab, "inputLabels") else ()
            for k, src in enumerate((e, niv, ent)[:n_ent]):
                # entrée « Sol fabriqué » (HDA de marquage) : sortie de pj::sol, la peinture suit le sol maillé
                # (TQ-MQG-005, revues du 11/10/2026) ; branches créées après « sol » (ordre de BRANCHES)
                if k < len(etiq) and etiq[k].startswith("Sol fabriqué") and geo.node("SORTIE_sol") is not None:
                    src = geo.node("SORTIE_sol")
                fab.setInput(k, src)
            fab.setUserData("pj_emplacement", "0")
            n_sorties = fab.type().maxNumOutputs()
        else:
            fab = geo.createNode("null", f"fab_{b}")
            fab.setInput(0, e)
            fab.setUserData("pj_emplacement", "1")
            fab.setComment(f"Emplacement : remplacer par l'HDA {t} (entrées : entités b_{b}, NIVEAU, ENTITES)")
            fab.setGenericFlag(hou.nodeFlag.DisplayComment, True)
            n_sorties = 1
        s = geo.createNode("null", f"SORTIE_{b}")
        s.setInput(0, fab, 0)
        prep = geo.createNode("pj::preparer_export::1.0", f"export_{b}")
        prep.setInput(0, s)
        prep.parm("couche_defaut").set(couche)
        u = geo.createNode("null", f"USD_{b}")
        u.setInput(0, prep)
        pts = geo.createNode("pj::exporter_points::1.0", f"points_{b}")
        if n_sorties >= 2:
            pts.setInput(0, fab, 1)
        else:
            pts.setInput(0, vide)
        pts.parm("famille").set(b)
        pts.parm("fichier").set(f"$PJ_SORTIE/points/{b}.json")
        for p_fab, p_pts in (("pivot_prototypes", "pivot"), ("sens_cd", "doc_cd")):   # déclarés par l'HDA de branche
            if fab.parm(p_fab) is not None:
                pts.parm(p_pts).set(fab.evalParm(p_fab))
        if n_sorties >= 3:                         # sortie 3 : prototypes de bibliothèque (README_HDA.md § 4 et § 7)
            sp = geo.createNode("null", f"SORTIE_PROTO_{b}")
            sp.setInput(0, fab, 2)
            pp = geo.createNode("pj::preparer_export::1.0", f"export_proto_{b}")
            pp.setInput(0, sp)
            pp.parm("couche_defaut").set("PJ_Lib")
            up = geo.createNode("null", f"USD_PROTO_{b}")
            up.setInput(0, pp)
    geo.layoutChildren()
    lire.setDisplayFlag(True)
    ent.setDisplayFlag(True)
    ent.setRenderFlag(True)

    st = hou.node("/stage")
    mat = st.createNode("sublayer", "materiaux")
    mat.parm("filepath1").set("$PJ_SORTIE/materiaux_ue.usda")
    chaines = [(b, b, f"{GEO}/USD_{b}", f"$PJ_SORTIE/{b}.usda") for b, _ in BRANCHES]
    chaines += [(f"proto_{b}", b, f"{GEO}/USD_PROTO_{b}", f"$PJ_SORTIE/prototypes/{b}.usda")
                for b, _ in BRANCHES if geo.node(f"USD_PROTO_{b}") is not None]
    for b, branche, soppath, fichier in chaines:
        si = st.createNode("sopimport", f"import_{b}")
        si.setInput(0, mat)
        si.parm("soppath").set(soppath)
        for p, v in (("copycontents", "on"), ("bindmaterials", "bind"), ("enable_savepath", 0),
                     ("enable_pathattr", 1), ("pathattr", "path"), ("enable_prefixabsolutepaths", 1),
                     ("prefixabsolutepaths", 0), ("enable_kindschema", 1), ("kindschema", "nestedgroup"),
                     ("enable_attribs", 1), ("attribs", "P N uv Cd"), ("enable_reversepolygons", 1),
                     ("reversepolygons", 1), ("enable_polygonsassubd", 1), ("polygonsassubd", 0)):
            si.parm(p).set(v)
        k = st.createNode("configureprimitive", f"kind_{b}")
        k.setInput(0, si)
        k.parm("primpattern").set("/World")
        k.parm("setkind").set(1)
        k.parm("kind").set("assembly")
        x = st.createNode("configureprimitive", f"etendues_{b}")
        x.setInput(0, k)
        x.parm("primpattern").set("%type:Mesh")
        x.parm("setextents").set(1)
        c = st.createNode("configurelayer", f"couche_{b}")
        c.setInput(0, x)
        for p, v in (("setupaxis", 1), ("upaxis", "z"), ("setmetersperunit", 1), ("metersperunit", 1.0),
                     ("setdefaultprim", 1), ("defaultprim", "/World")):
            c.parm(p).set(v)
        donnees = (("pj:contrat", "string", "pj_usd/0.1"), ("pj:cusp_deg", "float", 30.0),
                   ("pj:source", "string", f"recon/pcg/houdini/paquet_jardin_pcg.hip /obj/paquet_jardin/fab_{branche}"),
                   ("pj:branche", "string", b),
                   ("pj:hash_description", "string", f'`details("{GEO}/ENTITES", "pj_hash_description")`'))
        c.parm("customdatacount").set(len(donnees))
        for i, (n, ty, v) in enumerate(donnees, 1):
            c.parm(f"customdataname{i}").set(n)
            c.parm(f"customdatatype{i}").set(ty)
            c.parm(f"customdata{'str' if ty == 'string' else 'float'}value{i}").set(v)
        r = st.createNode("usd_rop", f"rop_{b}")
        r.setInput(0, c)
        for p, v in (("lopoutput", fichier), ("clearhoudinicustomdata", 1), ("savetimeinfo", 0),
                     ("flattensoplayers", 1), ("defaultprim", "/World"), ("requiredefaultprim", 1)):
            r.parm(p).set(v)
    st.layoutChildren()
    construire_apercu()
    hou.hipFile.save(str(chemin))
    return chemin


# ------------------------------------------------------------------------------------------------ aperçu Karma
# vues orthographiques de dessus : centre (x, y locaux) et largeur (m)
VUES_APERCU = {"site": (0.0, 0.0, 300.0), "centre": (0.0, 0.0, 70.0), "pilote": (24.5, 22.0, 100.0)}
# vue oblique (perspective) : position et cible en repère local (x, y, z), focale (mm)
VUE_OBLIQUE = {"oblique_pilote": ((-12.0, -22.0, 14.0), (22.0, 14.0, 0.0), 24.0)}
VEX_APERCU_COULEURS = r"""
// Aperçu : couleur et rayon des tubes par famille (vue de dessus des courbes brutes du lecteur).
string fam = s@famille;
vector c = {0.6, 0.6, 0.6};
float r = 0.035;
if (fam == "bordures") { c = {0.85, 0.12, 0.08}; r = 0.09; }
else if (fam == "surfaces") { c = {0.92, 0.92, 0.88}; r = 0.03; }
else if (fam == "ilots") { c = {0.1, 0.75, 0.2}; r = 0.08; }
else if (fam == "ponctuels_sol") { c = {0.9, 0.1, 0.9}; r = 0.07; }
else if (fam == "marquages") { c = {1.0, 0.82, 0.05}; r = 0.05; }
v@Cd = c;
f@pj_rayon = r;
"""
VEX_APERCU_RAYON = r"""
// Rayon et couleur portés par les points (une seule couleur de sommet dans le maillage fusionné de l'aperçu).
int prs[] = pointprims(0, @ptnum);
f@pscale = len(prs) > 0 ? prim(0, "pj_rayon", prs[0]) : 0.03;
v@Cd = len(prs) > 0 ? prim(0, "Cd", prs[0]) : {0.6, 0.6, 0.6};
@P.y += 0.25;
"""
VEX_APERCU_RELIEF = r"""
// Aperçu du nivellement : teinte hypsométrique douce (z local -3 .. +3 m), relief par l'éclairage rasant.
float t = fit(@P.y, -2.5, 2.5, 0, 1);
vector bas = {0.16, 0.22, 0.30};
vector mil = {0.34, 0.38, 0.30};
vector haut = {0.55, 0.48, 0.36};
v@Cd = t < 0.5 ? lerp(bas, mil, t * 2) : lerp(mil, haut, (t - 0.5) * 2);
"""


def construire_apercu():
    """/obj/apercu_lecteur (tubes des courbes brutes sur le HeightField) et /stage/apercu (Karma, vue de dessus)."""
    obj = hou.node("/obj")
    geo = obj.createNode("geo", "apercu_lecteur")
    geo.setComment("Contrôle visuel du lecteur : courbes brutes en tubes fins sur le HeightField de nivellement")
    om = geo.createNode("object_merge", "entites")
    om.parm("objpath1").set(f"{GEO}/ENTITES")
    col = geo.createNode("attribwrangle", "couleurs")
    col.setInput(0, om)
    col.parm("class").set(1)
    col.parm("snippet").set(VEX_APERCU_COULEURS)
    ray = geo.createNode("attribwrangle", "rayons")
    ray.setInput(0, col)
    ray.parm("class").set(2)
    ray.parm("snippet").set(VEX_APERCU_RAYON)
    tub = geo.createNode("polywire", "tubes")
    tub.setInput(0, ray)
    tub.parm("radius").set(1.0)
    tub.parm("usescaleattrib").set(1)
    tub.parm("scaleattrib").set("pscale")
    tub.parm("div").set(6)
    on = geo.createNode("object_merge", "nivellement")
    on.parm("objpath1").set(f"{GEO}/NIVEAU")
    rs = geo.createNode("heightfield_resample", "reechantillonner")
    rs.setInput(0, on)
    rs.parm("fixedresample").set(1)                 # résolution exacte : pas de 0,5 m (aperçu)
    rs.parm("divisionmode").set("size")
    rs.parm("gridspacing").set(0.5)
    cv = geo.createNode("convertheightfield", "relief")
    cv.setInput(0, rs)
    teinte = geo.createNode("attribwrangle", "teinte")
    teinte.setInput(0, cv)
    teinte.parm("class").set(2)
    teinte.parm("snippet").set(VEX_APERCU_RELIEF)
    nor = geo.createNode("normal", "normales")
    nor.setInput(0, teinte)
    for n_, src in (("attributs_relief", nor), ("attributs_tubes", tub)):
        ad = geo.createNode("attribdelete", n_)
        ad.setInput(0, src)
        ad.parm("negate").set(1)
        for c, v in (("ptdel", "Cd N"), ("vtxdel", "N"), ("primdel", ""), ("dtldel", "")):
            ad.parm(c).set(v)
        if src is nor:
            nor_f = ad
        else:
            tub_f = ad
    m = geo.createNode("merge", "fusion")
    m.setInput(0, nor_f)
    m.setInput(1, tub_f)
    out = geo.createNode("null", "OUT_APERCU")
    out.setInput(0, m)
    out.setDisplayFlag(True)
    out.setRenderFlag(True)
    geo.layoutChildren()

    st = hou.node("/stage")
    ap = st.createNode("subnet", "apercu")
    ap.setComment("Vue de dessus Karma XPU des courbes du lecteur sur le nivellement (fabriquer_hda.py --apercu)")
    si = ap.createNode("sopimport", "geometrie")
    si.parm("soppath").set("/obj/apercu_lecteur/OUT_APERCU")
    si.parm("enable_savepath").set(0)
    si.parm("copycontents").set("on")
    si.parm("enable_pathprefix").set(1)
    si.parm("pathprefix").set("/apercu/geo")
    precedent = si
    for nom, (cx, cy, largeur) in VUES_APERCU.items():
        cam = ap.createNode("camera", f"camera_{nom}")
        cam.setInput(0, precedent)
        cam.parm("primpath").set(f"/apercu/camera_{nom}")
        cam.parm("projection").set("orthographic")
        cam.parm("tx").set(cx)                       # repère Houdini : (x, z, -y) local
        cam.parm("ty").set(300)
        cam.parm("tz").set(-cy)
        cam.parm("rx").set(-90)
        cam.parm("aspectratiox").set(1.0)
        cam.parm("aspectratioy").set(1.0)
        # USD : ouverture orthographique en dixièmes d'unité de scène ; le paramètre LOP est en mm (x 1/100)
        cam.parm("horizontalAperture").set(largeur * 1000.0)
        cam.parm("clippingRange1").set(1.0)
        cam.parm("clippingRange2").set(1000.0)
        precedent = cam
    for nom, (pos, cible, focale) in VUE_OBLIQUE.items():
        cam = ap.createNode("camera", f"camera_{nom}")
        cam.setInput(0, precedent)
        cam.parm("primpath").set(f"/apercu/camera_{nom}")
        for k, v in zip(("tx", "ty", "tz"), (pos[0], pos[2], -pos[1])):
            cam.parm(k).set(v)
        cam.parm("lookatenable").set(1)
        for k, v in zip(("lookatpositionx", "lookatpositiony", "lookatpositionz"), (cible[0], cible[2], -cible[1])):
            cam.parm(k).set(v)
        cam.parm("aspectratiox").set(1.0)
        cam.parm("aspectratioy").set(1.0)
        cam.parm("focalLength").set(focale)
        cam.parm("horizontalAperture").set(36.0)
        cam.parm("clippingRange1").set(0.1)
        cam.parm("clippingRange2").set(2000.0)
        precedent = cam
    ml = ap.createNode("materiallibrary", "materiau_apercu")
    ml.setInput(0, precedent)
    sh = ml.createNode("mtlxstandard_surface", "couleur_sommets")
    lu = ml.createNode("mtlxgeompropvalue", "lire_couleur")
    lu.parm("signature").set("color3")
    lu.parm("geomprop").set("displayColor")
    sh.setInput(sh.inputIndex("base_color"), lu)
    sh.parm("specular").set(0.05)
    sh.parm("specular_roughness").set(0.7)
    ml.parm("materials").set(1)
    ml.parm("matnode1").set("couleur_sommets")
    ml.parm("matpath1").set("/apercu/materiaux/couleur_sommets")
    ml.parm("assign1").set(1)
    ml.parm("geopath1").set("/apercu/geo/*")
    sol = ap.createNode("distantlight::2.0", "soleil")
    sol.setInput(0, ml)
    sol.parm("primpath").set("/apercu/soleil")
    sol.parm("rx").set(-38)
    sol.parm("ry").set(-135)
    sol.parm("xn__inputsintensity_i0a").set(2.2)
    dome = ap.createNode("domelight::3.0", "ciel")
    dome.setInput(0, sol)
    dome.parm("primpath").set("/apercu/ciel")
    dome.parm("xn__inputsintensity_i0a").set(0.45)
    kp = ap.createNode("karmarenderproperties", "rendu")
    kp.setInput(0, dome)
    kp.parm("camera").set("/apercu/camera_site")
    kp.parm("engine").set("xpu")
    kp.parm("res_mode").set("manual")
    for n in ("resolutionx", "resolutiony"):          # resolutiony est verrouillée par une expression d'aspect
        kp.parm(n).lock(False)
        kp.parm(n).deleteAllKeyframes()
        kp.parm(n).set(2000)
    kp.parm("samplesperpixel").set(16)
    r = ap.createNode("usd_rop", "rop_apercu")
    r.setInput(0, kp)
    for p, v in (("lopoutput", "$PJ_SORTIE/controle/apercu_lecteur.usdc"), ("savetimeinfo", 0),
                 ("flattensoplayers", 1), ("clearhoudinicustomdata", 1)):
        r.parm(p).set(v)
    ap.layoutChildren()
    st.layoutChildren()


def rendre_apercu(sortie, res=2000):
    """Écrit l'USD d'aperçu (ROP /stage/apercu/rop_apercu) et rend chaque vue avec husk (Karma XPU) en PNG."""
    rop = hou.node("/stage/apercu/rop_apercu")
    rop.render()
    usd = Path(sortie) / "controle" / "apercu_lecteur.usdc"
    husk = Path(sys.executable).parent / "husk.exe"
    env = dict(os.environ, KARMA_XPU_DISABLE_MIPMAPS="1")
    images = []
    for nom in list(VUES_APERCU) + list(VUE_OBLIQUE):
        png = Path(sortie) / "controle" / f"apercu_lecteur_{nom}.png"
        cmd = [str(husk), "-R", "BRAY_HdKarmaXPU", "--settings", "/Render/rendersettings", "--camera",
               f"/apercu/camera_{nom}", "--res", str(res), str(res), "--frame", "1", "--output", png.as_posix(),
               "--make-output-path", "--verbose", "1", usd.as_posix()]
        t = time.time()
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0 or not png.exists():
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit(f"rendu d'aperçu {nom} en échec")
        print(f"   aperçu {nom} : {time.time() - t:.0f} s -> {png}")
        images.append(rel(png))
    return images


# ------------------------------------------------------------------------------------------------ matériaux
def ecrire_materiaux(chemin):
    """Couche /World/Looks/<materiau_id> (UsdPreviewSurface + outputs:unreal:surface -> MI_<id>) : sous-couche
    commune de tous les USD de branche (CONTRAT_EXPORT.md § 5, E5). Écriture déterministe (texte trié)."""
    from pxr import Gf, Sdf, Usd, UsdShade
    spec = json.loads(MATERIAUX_SOL.read_text(encoding="utf-8"))["materiaux"]
    pei = json.loads(PEINTURE.read_text(encoding="utf-8"))
    mats = {}
    for mid, m in spec.items():
        alb = m.get("albedo_cible_lineaire") or (m.get("texture_mesuree") or {}).get("albedo_moyen_lineaire") or [0.3] * 3
        rug = (m.get("rugosite") or {}).get("valeur", 0.8) if isinstance(m.get("rugosite"), dict) else 0.8
        mats[mid] = (alb, rug)
    mats.update(MAISON)
    couv = pei["lien_scene"]["couverture_scene"]
    rug_p = pei["rugosite"]["peinture_par_usure"]
    for c in ("blanc", "jaune"):
        neuf = pei["couleurs"][c]["neuf"]["albedo_lineaire"]
        for u in ("0", "1", "2", "3", "F"):
            k = float(couv[u])
            mats[f"PJ_Peinture_{c}_u{u}"] = ([round(k * a + (1 - k) * 0.15, 4) for a in neuf], rug_p.get(u) or 0.8)
    lay = Sdf.Layer.CreateAnonymous(".usda")
    st = Usd.Stage.Open(lay)
    st.SetMetadata("upAxis", "Z")
    st.SetMetadata("metersPerUnit", 1.0)
    w = st.DefinePrim("/World", "Xform")
    st.SetDefaultPrim(w)
    st.DefinePrim("/World/Looks", "Scope")
    for mid in sorted(mats):
        alb, rug = mats[mid]
        p = f"/World/Looks/{mid}"
        m = UsdShade.Material.Define(st, p)
        ap = UsdShade.Shader.Define(st, p + "/Apercu")
        ap.CreateIdAttr("UsdPreviewSurface")
        ap.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*[float(a) for a in alb]))
        ap.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(rug))
        m.CreateSurfaceOutput().ConnectToSource(ap.ConnectableAPI(), "surface")
        ue = UsdShade.Shader.Define(st, p + "/Unreal")
        ue.CreateImplementationSourceAttr(UsdShade.Tokens.sourceAsset)
        ue.SetSourceAsset(Sdf.AssetPath(f"/Game/PJ/Materials/MI_{mid}.MI_{mid}"), "unreal")
        m.CreateSurfaceOutput("unreal").ConnectToSource(ue.ConnectableAPI(), "out")
    lay.customLayerData = {"pj:contrat": "pj_usd/0.1", "pj:source": "recon/pcg/houdini/fabriquer_hda.py ecrire_materiaux"}
    Path(chemin).parent.mkdir(parents=True, exist_ok=True)
    Path(chemin).write_text(lay.ExportToString(), encoding="utf-8", newline="\n")
    return sorted(mats)


# ------------------------------------------------------------------------------------------------ fabrication
def regler_emprise(emprise, tuile=None, taille=64.0):
    lire = hou.node(f"{GEO}/lire_description")
    if tuile is not None:
        lire.parm("emprise").set("tuile")
        lire.parm("tuile_taille").set(taille)
        lire.parmTuple("tuile_index").set((int(tuile[0]), int(tuile[1])))
    else:
        lire.parm("emprise").set(emprise)


def aplatir_donnees_calque(chemin):
    """Configure Layer range les clés « pj:x » de customLayerData en dictionnaire imbriqué {pj: {x}} ; le contrat
    (et verifier_usd : customLayerData['pj:cusp_deg']) attend des clés plates « pj:x ». Réécriture Sdf du calque."""
    from pxr import Sdf
    lay = Sdf.Layer.FindOrOpen(str(chemin))
    d = dict(lay.customLayerData or {})
    pj = d.pop("pj", None)
    if isinstance(pj, dict):
        for k in sorted(pj):
            d[f"pj:{k}"] = pj[k]
        lay.customLayerData = d
        lay.Save()
    del lay
    canoniser_usdc(chemin)


def canoniser_usdc(chemin):
    """Calque binaire (.usdc) identique à l'octet d'un processus à l'autre. Le writer « crate » range les specs dans
    l'ordre de tables hachées sur les adresses des SdfPath : le même contenu donne des octets différents d'un processus
    à l'autre (vérifié : texte USD identique, .usdc différents). Le calque est donc relu en texte canonique (usda), puis
    réécrit en .usdc depuis ce texte : ordre d'écriture fixé par le texte (vérifié : deux processus -> mêmes octets)."""
    from pxr import Sdf
    chemin = Path(chemin)
    if chemin.suffix != ".usdc":
        return
    texte = Sdf.Layer.OpenAsAnonymous(str(chemin)).ExportToString()
    tmp = Sdf.Layer.CreateAnonymous(".usda")
    tmp.ImportFromString(texte)
    f = chemin.with_name(chemin.stem + "_canonique.usdc")
    f.unlink(missing_ok=True)
    out = Sdf.Layer.CreateNew(str(f))
    out.TransferContent(tmp)
    out.Save()
    del out, tmp, texte
    os.replace(f, chemin)
    lay = Sdf.Layer.Find(str(chemin))
    if lay is not None:
        lay.Reload(force=True)


def verifier_usd(chemin):
    sys.path.insert(0, str(VERIFIER_USD.parent))
    import verifier_usd as V
    r = V.verifier(str(chemin))
    return {"ok": r["ok"], "erreurs": len(r["erreurs"]), "avertissements": len(r.get("avertissements", [])),
            "exemples_erreurs": r["erreurs"][:5]}


DUREES = {}          # durées (s) de la dernière passe : hors bilan (le bilan reste déterministe), manifeste « durees_s »


def produits(bilan, sortie):
    """Fichiers écrits par une passe (chemins relatifs à la sortie) : base de la comparaison de déterminisme (les
    fichiers d'une passe antérieure restés dans la sortie, ex. avec --branches, n'y entrent pas)."""
    out = {"materiaux_ue.usda"}
    for info in bilan.get("branches", {}).values():
        for f in (info.get("usd"), (info.get("prototypes") or {}).get("usd"), info.get("points")):
            if f:
                p = Path(f) if Path(f).is_absolute() else RACINE / f
                out.add(p.resolve().relative_to(Path(sortie).resolve()).as_posix())
    return out


def fabriquer(sortie=SORTIE, emprise="site", suffixe="", tuile=None, taille=64.0, branches=None):
    """Une passe : cuisson, USD des branches fabriquées, points ; renvoie le bilan (sans durées : déterministe ;
    les durées vont dans DUREES). branches : sous-ensemble de branches à fabriquer (--branches), les autres sont
    notées « non demandée »."""
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    DUREES.clear()
    t0 = time.time()
    _variables(DESCRIPTION, sortie)
    regler_emprise(emprise, tuile, taille)
    ecrire_materiaux(sortie / "materiaux_ue.usda")
    geo = hou.node(GEO)
    ent = geo.node("ENTITES").geometry()
    geo.node("NIVEAU").geometry()
    DUREES["lecteur"] = round(time.time() - t0, 1)
    bilan = {"lecteur": {"comptes": ent.attribValue("pj_comptes"), "emprise": list(ent.attribValue("pj_emprise")),
                         "primitives": ent.intrinsicValue("primitivecount"),
                         "points": ent.intrinsicValue("pointcount"),
                         "hash_description": ent.attribValue("pj_hash_description"),
                         "empreinte_entites": empreinte(ent),
                         "empreinte_nivellement": empreinte(geo.node("NIVEAU").geometry())},
             "branches": {}}
    for b, couche in BRANCHES:
        fab = geo.node(f"fab_{b}")
        emplacement = fab.userData("pj_emplacement") == "1"
        info = {"noeud": fab.path(), "type": fab.type().name(), "emplacement": emplacement,
                "entrees": geo.node(f"entrees_{b}").geometry().intrinsicValue("primitivecount")}
        tb = time.time()
        if branches and b not in branches:
            info["non_demandee"] = True
        elif not emplacement:
            g = geo.node(f"USD_{b}").geometry()
            DUREES[f"{b}:cuisson"] = round(time.time() - tb, 1)
            info["primitives_maillage"] = g.intrinsicValue("primitivecount")
            info["empreinte_sop"] = empreinte(g)             # géométrie cuite avant export (diagnostic de déterminisme)
            if info["primitives_maillage"] > 0:
                rop = hou.node(f"/stage/rop_{b}")
                # format déclaré par l'HDA de branche (paramètre format_usd : usdc pour les gros maillages), sinon usda
                ext = fab.parm("format_usd").evalAsString() if fab.parm("format_usd") is not None else "usda"
                usd = sortie / f"{b}{suffixe}.{ext}"
                autre = sortie / f"{b}{suffixe}.{'usda' if ext == 'usdc' else 'usdc'}"
                autre.unlink(missing_ok=True)                 # pas de couche périmée dans l'autre format
                rop.parm("lopoutput").set(usd.as_posix())
                rop.render()
                rop.parm("lopoutput").set(f"$PJ_SORTIE/{b}.usda")
                aplatir_donnees_calque(usd)
                info["usd"] = rel(usd)
                info["verifier_usd"] = verifier_usd(usd)
            gp = geo.node(f"USD_PROTO_{b}")                  # prototypes de bibliothèque (sortie 3 de l'HDA)
            if gp is not None and gp.geometry().intrinsicValue("primitivecount") > 0:
                rop = hou.node(f"/stage/rop_proto_{b}")
                usd = sortie / "prototypes" / f"{b}{suffixe}.usda"
                rop.parm("lopoutput").set(usd.as_posix())
                rop.render()
                rop.parm("lopoutput").set(f"$PJ_SORTIE/prototypes/{b}.usda")
                aplatir_donnees_calque(usd)
                info["prototypes"] = {"usd": rel(usd), "verifier_usd": verifier_usd(usd)}
            pts = geo.node(f"points_{b}")
            n = pts.geometry().intrinsicValue("pointcount")
            if n > 0:
                info["empreinte_points_sop"] = empreinte(pts.geometry())
            if n > 0:
                pts.parm("fichier").set((sortie / "points" / f"{b}{suffixe}.json").as_posix())
                info["points"] = rel(pts.hdaModule().ecrire(pts))
                pts.parm("fichier").set(f"$PJ_SORTIE/points/{b}.json")
                info["n_points"] = n
            DUREES[f"{b}:total"] = round(time.time() - tb, 1)
        bilan["branches"][b] = info
    DUREES["passe"] = round(time.time() - t0, 1)
    return bilan


def empreinte(geo):
    """sha256 de la géométrie cuite (positions, id, materiau_id, groupes, voxels) : preuve de déterminisme du lecteur."""
    h = hashlib.sha256()
    h.update(geo.pointFloatAttribValuesAsString("P"))
    for nom in ("id", "materiau_id", "famille"):
        if geo.findPrimAttrib(nom) is not None:
            h.update("".join(geo.primStringAttribValues(nom)).encode("utf-8"))
    for g in geo.primGroups():
        h.update(g.name().encode("utf-8"))
        h.update(bytes(str([p.number() for p in g.prims()]), "utf-8"))
    for pr in geo.prims():
        if pr.type() == hou.primType.Volume:
            h.update(pr.allVoxelsAsString())
    return h.hexdigest()


def bibliotheques_unitaires(dossier, hda):
    """Une bibliothèque compacte à une seule définition par HDA SOP sans HDA pj:: imbriquée (pj_bordure.hdalc…) :
    Houdini Engine instancie la première définition d'une bibliothèque et ouvre, dans l'éditeur, une boîte de choix
    quand elle en contient plusieurs. Les HDA imbriquées (marquages) passent par le paquet. hda : bilan « hda »."""
    import tempfile
    out = {}
    for nom in sorted(hda):
        if any(t.startswith("pj::") for t in hda[nom]["par_type"]):
            continue
        d = hou.nodeType(hou.sopNodeTypeCategory(), nom).definition()
        if d is None:
            continue
        f = Path(dossier) / f"pj_{nom.split('::')[1]}.hdalc"
        tmp = Path(tempfile.mkdtemp(prefix="pj_unitaire_")) / f.name
        d.copyToHDAFile(str(tmp))
        f.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(tmp, f)
        shutil.rmtree(tmp.parent, ignore_errors=True)
        out[nom] = {"fichier": rel(f), "definitions": [x.nodeTypeName() for x in hou.hda.definitionsInFile(str(f))]}
    return out


def verifier_paquet(fichier):
    """Le paquet pour Unreal est autonome : un hython neuf n'installe QUE ce fichier et cuit lecteur, niveau_z et
    preparer_export (hda/commun/verifier_paquet.py)."""
    r = subprocess.run([sys.executable, str(HDA / "commun" / "verifier_paquet.py"), str(fichier), str(DESCRIPTION)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    lignes = [x for x in r.stdout.splitlines() if x.startswith("PJ_JSON")]
    return json.loads(lignes[-1][7:]) if lignes else {"echec": (r.stdout + r.stderr)[-1500:]}


def comptes_noeuds():
    out = {}
    for cat, nom in O.types_pj():
        c = O.compter_noeuds(nom)
        d = hou.nodeType(hou.sopNodeTypeCategory(), nom).definition()
        out[nom] = dict(c, bibliotheque=rel(d.libraryFilePath()))
    return out


def hash_sorties(sortie):
    out = {}
    for p in sorted(Path(sortie).rglob("*")):
        if p.is_file() and "hda" not in p.relative_to(sortie).parts and p.name != "manifest_fabrication_hda.json" \
                and p.suffix in (".usda", ".usdc", ".json"):
            out[p.relative_to(sortie).as_posix()] = sha(p)
    return out


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--toutes", action="store_true", help="avec --construire-hda : aussi hda/*/construire*.py")
    ap.add_argument("--construire-hip", action="store_true")
    ap.add_argument("--emprise", default="site", choices=("site", "pilote"))
    ap.add_argument("--tuiles", type=float, default=0.0, help="taille des tuiles (m) : un USD par branche et tuile")
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--apercu", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    ap.add_argument("--essai-export", default="")
    ap.add_argument("--branches", default="", help="branches à fabriquer, séparées par des virgules (défaut : toutes)")
    ap.add_argument("--comparer", default="", help="manifeste d'une passe d'un autre processus : sorties identiques ?")
    ap.add_argument("--vex-jit", action="store_true", help="garder le JIT natif de VEX (plus rapide, non déterministe "
                                                          "d'un processus à l'autre au dernier bit)")
    a = ap.parse_args()
    choix = set(x for x in a.branches.split(",") if x)
    t0 = time.time()
    if a.construire_hda:
        for f in construire_hda(a.toutes):
            print("   HDA", f)
        if not (a.construire_hip or a.apercu or a.verifier_determinisme or a.essai_export):
            return 0
    if a.construire_hip or not HIP.exists():
        print("   scène", construire_hip())
        if a.construire_hip and not (a.apercu or a.verifier_determinisme):
            return 0
    if a.essai_export:
        return essai_export(Path(a.essai_export))
    hou.hipFile.load(str(HIP), suppress_save_prompt=True, ignore_load_warnings=True)
    O.installer_tout()
    sortie = Path(a.sortie)
    bilan = {"schema": "pj_manifest_fabrication_hda/0.1", "houdini": hou.applicationVersionString(),
             "licence": hou.licenseCategory().name(), "scene": rel(HIP), "description": rel(DESCRIPTION),
             "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
             "hda": comptes_noeuds()}
    durees = {"chargement_scene": round(time.time() - t0, 1)}
    faits = set()
    if a.tuiles > 0:
        n = int(round(300.0 / a.tuiles))
        bilan["tuiles"] = {}
        for i in range(n):
            for j in range(n):
                bilan["tuiles"][f"t{i}_{j}"] = fabriquer(sortie, suffixe=f"_t{i}_{j}", tuile=(i, j), taille=a.tuiles,
                                                         branches=choix)
                durees[f"t{i}_{j}"] = dict(DUREES)
                faits |= produits(bilan["tuiles"][f"t{i}_{j}"], sortie)
    else:
        bilan["fabrication"] = fabriquer(sortie, a.emprise, branches=choix)
        durees["fabrication"] = dict(DUREES)
        faits = produits(bilan["fabrication"], sortie)
    t1 = time.time()
    paquet = sortie / "hda" / "pj_paquet_jardin.hdalc"
    bilan["paquet_ue"] = {"fichier": rel(paquet), "definitions": O.empaqueter(paquet)}
    bilan["paquet_ue"]["verification"] = verifier_paquet(paquet)
    bilan["paquet_ue"]["unitaires"] = bibliotheques_unitaires(paquet.parent, bilan["hda"])
    durees["paquet_ue"] = round(time.time() - t1, 1)
    if a.apercu:
        bilan["apercu"] = rendre_apercu(sortie)
    bilan["sorties"] = hash_sorties(sortie)
    bilan["produits"] = sorted(faits)
    if a.verifier_determinisme:
        t1 = time.time()
        tmp = sortie.parent / (sortie.name + "_verif")
        shutil.rmtree(tmp, ignore_errors=True)
        hou.hipFile.load(str(HIP), suppress_save_prompt=True, ignore_load_warnings=True)
        b2 = fabriquer(tmp, a.emprise, branches=choix)
        h2 = hash_sorties(tmp)
        for k in ("empreinte_entites", "empreinte_nivellement"):
            if b2["lecteur"][k] != bilan["fabrication"]["lecteur"][k]:
                h2[f"lecteur:{k}"] = b2["lecteur"][k]
        # comparaison sur les fichiers écrits par les deux passes (pas les restes d'une passe --branches antérieure)
        cles = faits | produits(b2, tmp) | {k for k in h2 if k.startswith("lecteur:")}
        diff = sorted(k for k in cles if bilan["sorties"].get(k) != h2.get(k))
        bilan["determinisme"] = {"identique": not diff, "differences": diff, "fichiers": len(cles)}
        shutil.rmtree(tmp, ignore_errors=True)
        durees["verification_determinisme"] = round(time.time() - t1, 1)
    if a.comparer:                                 # passe d'un autre processus (manifeste copié) : même sortie à l'octet
        autre = json.loads(Path(a.comparer).read_text(encoding="utf-8"))
        cles = faits | set(autre.get("produits", []))
        diff = sorted(k for k in cles if bilan["sorties"].get(k) != autre.get("sorties", {}).get(k))
        for k in ("empreinte_entites", "empreinte_nivellement"):
            if (autre.get("fabrication") or {}).get("lecteur", {}).get(k) != (bilan.get("fabrication") or {}).get(
                    "lecteur", {}).get(k):
                diff.append(f"lecteur:{k}")
        bilan["comparaison_processus"] = {"manifeste": rel(a.comparer), "identique": not diff, "differences": diff,
                                          "fichiers": len(cles)}
    durees["total"] = round(time.time() - t0, 1)
    bilan["durees_s"] = durees                     # seule partie non déterministe du manifeste
    (sortie / "manifest_fabrication_hda.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1),
                                                         encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in bilan.items() if k not in ("hda", "sorties", "produits")}, ensure_ascii=False,
                     indent=1)[:4000])
    print(f"   durée {time.time() - t0:.0f} s")
    return 0


# ------------------------------------------------------------------------------------------------ essai d'export
def essai_export(dossier):
    """Valide la chaîne preparer_export -> Solaris -> USD -> verifier_usd sur un réseau d'essai (îlots triangulés,
    drapés par pj::niveau_z) branché à la place de l'emplacement fab_ilots, sans toucher à la scène enregistrée."""
    hou.hipFile.load(str(HIP), suppress_save_prompt=True, ignore_load_warnings=True)
    O.installer_tout()
    _variables(DESCRIPTION, dossier)
    regler_emprise("pilote")
    geo = hou.node(GEO)
    e = geo.node("entrees_ilots")
    tri = geo.createNode("triangulate2d::3.0", "essai_trianguler")
    tri.setInput(0, e)
    tri.parm("useconstrpolys").set(1)
    tri.parm("constrpolys").set("*")
    tri.parm("removefromconstrpolys").set(1)
    nz = geo.createNode("pj::niveau_z::1.0", "essai_niveau")
    nz.setInput(0, tri)
    nz.setInput(1, geo.node("NIVEAU"))
    w = geo.createNode("attribwrangle", "essai_attributs")
    w.setInput(0, nz)
    w.parm("class").set(1)
    w.parm("snippet").set('s@pj_couche = "PJ_Ilots"; s@pj_entite = s@id;')
    geo.node("SORTIE_ilots").setInput(0, w)
    ecrire_materiaux(Path(dossier) / "materiaux_ue.usda")
    rop = hou.node("/stage/rop_ilots")
    usd = Path(dossier) / "essai_ilots.usda"
    rop.parm("lopoutput").set(usd.as_posix())
    rop.render()
    aplatir_donnees_calque(usd)
    r = verifier_usd(usd)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(principal())
