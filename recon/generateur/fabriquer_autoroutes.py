"""Pilote du lot « autoroutes » (hython Houdini 22) : chaîne L1 + L2 + L2b avec l'HDA rg::autoroute.

    hython recon/generateur/fabriquer_autoroutes.py SCENE.yaml [SCENE.yaml ...] [--sortie DOSSIER] [--rendus]
                                                    [--construire-hda] [--verifier-determinisme]

Même chaîne que fabriquer_generateur.py --l2b (fonctions importées sans modification ; l'agent d'intégration fusionnera),
avec l'HDA du lot (recon/generateur/hda/rg_autoroute) :
    rg::lire_modele ─► rg::graphe ─► rg::profils ─────────────────────────────┐ (limites)
                     └► rg::nivellement ─► rg::sol ─► rg::autoroute ◄────────┤ zones, nœuds, références
                                                        ├─ 1 SOL (bretelles raccordées en Z + sol des musoirs) = sol total
                                                        ├─ 2 ÉQUIPEMENTS (GBA / DBA, glissières) ─► USD route_l2 /Monde/Equipements
                                                        ├─ 3 MARQUES (aplats, chevrons) + rg::marquages (sortie 2) ─► pj::marquage_solide
                                                        └─ 4 CONTRÔLES
Sorties : celles des lots L1, L2, L2b dans recon/out/generateur/<scene>/ et autoroute/ (equipements.json, musoirs.json,
manifest_autoroute.json) ; rendus (2 vues ; 3 pour A3) et planche ≤ 1092 px.
Ajouts en mémoire (à reporter par l'agent d'intégration) : F2B.cuire décide du contournement de pj::marquage_solide
d'après son entrée réelle (marques du musoir sans flèche ni symbole) ; matériau de rendu « beton_prefa_lisse » (GBA)
recalé comme le béton clair des bordures (rendu_l2b.ECHELLE_ALBEDO) ; couche Equipements ajoutée à route_l2.usda.
Le pilote se relance avec HOUDINI_VEX_DISABLE_JIT=1 et les dossiers temporaires sur D: (rien n'est écrit sur C:).
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                 # recon/generateur
DEPOT = ICI.parents[1]
TMP = ICI / "tmp" / "hython"
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"

if os.environ.get("RG_PILOTE_ENV") != "1":
    TMP.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, RG_PILOTE_ENV="1", PYTHONDONTWRITEBYTECODE="1", TEMP=str(TMP), TMP=str(TMP),
               HOUDINI_TEMP_DIR=str(TMP).replace("\\", "/"), HOUDINI_VEX_DISABLE_JIT="1")
    sys.exit(subprocess.call([sys.executable] + sys.argv, env=env))

import tempfile  # noqa: E402

tempfile.tempdir = str(TMP)
import hou  # noqa: E402

sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI / "hda" / "commun"))
sys.path.insert(0, str(ICI / "rendu"))
import rg_hda_outils as R  # noqa: E402
import fabriquer_generateur as FG  # noqa: E402
import fabriquer_l2 as F2  # noqa: E402
import fabriquer_l2b as F2B  # noqa: E402

VERSION = "fabriquer_autoroutes/1.0 (lot autoroutes)"
TMP_A = ICI / "tmp" / "autoroutes"


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    sigs = FG.construire_hda(forcer=forcer, l2=True)
    sigs.update(F2.installer_pj())
    sigs.update(F2B.construire_hda(forcer=forcer))
    spec = importlib.util.spec_from_file_location("construire_rg_autoroute", ICI / "hda" / "rg_autoroute" / "construire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    a = mod.construire(ICI / "hda" / "rg_autoroute")
    sigs[f"rg::autoroute::{R.VERSION}"] = R.signature(a)
    return sigs


# ------------------------------------------------------------------------------------------------------- réseau
def _sous_reseau(obj, nom, entrees, construction):
    sub = obj.createNode("subnet", nom)
    for k, (n, o) in enumerate(entrees):
        sub.setInput(k, n, o)
    ind = sub.indirectInputs()
    sorties = construction(sub, ind)
    for k, n in enumerate(sorties):
        out = sub.createNode("output", f"sortie_{k}")
        out.setInput(0, n)
        out.parm("outputidx").set(k)
    sub.layoutChildren()
    return sub


def reseau():
    lire, graphe, prof = FG.reseau()
    obj = lire.parent()
    n2 = F2.reseau(obj, lire, graphe, R.nom_type)
    inserer_sol(obj, lire, graphe, prof, n2)
    n2b = F2B.reseau(obj, lire, graphe, n2)
    inserer_marques(obj, n2, n2b)
    return lire, graphe, prof, n2, n2b


def inserer_sol(obj, lire, graphe, prof, n2):
    """rg::autoroute après le sol (n2["sol"] : celui de rg::sol, ou le sol total du lot L3) ; le sol total (routes
    raccordées + musoirs) remplace n2["sol"] avant la chaîne L2b. Réutilisée par fabriquer_generateur.py."""
    zn = obj.createNode("merge", "zones_et_noeuds")
    zn.setInput(0, lire, 2)
    zn.setInput(1, lire, 1)
    au = obj.createNode(R.nom_type("autoroute"), "autoroute")
    for k, (n, o) in enumerate(((prof, 0), (n2["sol"], 0), (zn, 0), (graphe, 0))):
        au.setInput(k, n, o)
    # sol total : routes raccordées + musoirs (entrée 0 = références : le rendu lit la route 0 sur l'entrée du sol)
    sol_w = _sous_reseau(obj, "sol_total", [(graphe, 0), (au, 0), (n2["sol"], 1)], lambda sub, ind: (ind[1], ind[2]))
    n2["controle_heightfield"].setInput(0, sol_w, 0)
    n2["sol_routes"] = n2["sol"]
    n2["sol"] = sol_w
    n2["autoroute"] = au
    return au


def inserer_marques(obj, n2, n2b):
    """Marques des musoirs (sortie 3 de rg::autoroute) fusionnées à l'entrée de la peinture des marques."""
    au = n2["autoroute"]
    src = n2b["peinture_marques"].inputConnections()[0]
    mm = obj.createNode("merge", "marques_et_musoirs")
    mm.setInput(0, src.inputNode(), src.outputIndex())
    mm.setInput(1, au, 2)
    n2b["peinture_marques"].setInput(0, mm)
    n2b["marques_entree"] = mm
    obj.layoutChildren()
    return mm


_CUIRE_L2B = F2B.cuire


def cuire_l2b(noeuds, scene):
    """F2B.cuire, puis contournement de pj::marquage_solide décidé d'après son entrée réelle (rg::marquages sans marque
    mais musoir à chevrons : la peinture des marques doit être faite)."""
    _CUIRE_L2B(noeuds, scene)
    mm = noeuds.get("marques_entree")
    if mm is None:
        return
    mm.cook(force=True)
    vide = len(mm.geometry().prims()) == 0
    if noeuds["peinture_marques"].isBypassed() != vide:
        noeuds["peinture_marques"].bypass(vide)
        for nom in ("peinture_marques", "mesure"):
            try:
                noeuds[nom].cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {e}" for c in (noeuds[nom],) + noeuds[nom].allSubChildren() for e in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson (marques du musoir)" + chr(10) + chr(10).join(err[:20]))


# F2B.cuire = cuire_l2b  (intégration de l'étape 2 : comportement repris dans le code commun)
_ECRIRE_USD_L2 = F2.ecrire_usd
_EQUIPEMENTS = {}


def ecrire_usd_l2(noeuds, dossier):
    """F2.ecrire_usd, puis couche /Monde/Equipements (sortie 2 de rg::autoroute : dispositifs de retenue), double face,
    matériaux de la bibliothèque route_fr (beton_prefa_lisse, acier_galvanise)."""
    res = _ECRIRE_USD_L2(noeuds, dossier)
    au = noeuds.get("autoroute")
    if au is None:
        return res
    geo = au.geometry(1)
    if geo is None or not len(geo.prims()):
        return res
    import rendre_l2 as RL
    from pxr import Usd, UsdGeom
    f = Path(dossier) / "route_l2.usda"
    stage = Usd.Stage.Open(str(f))
    d = RL.maillages(geo, "Equipements")
    liaisons, sources = RL.materiaux(stage, set(d), Path(dossier), racine="/Monde/Looks")
    RL.ecrire_couche(stage, "/Monde/Equipements", d, liaisons)
    for mid in d:
        nom = "".join(c if c.isalnum() else "_" for c in mid)
        UsdGeom.Mesh(stage.GetPrimAtPath(f"/Monde/Equipements/{nom}")).CreateDoubleSidedAttr(True)
    stage.GetRootLayer().Save()
    res = dict(res)
    res["materiaux"] = dict(res.get("materiaux", {}), **sources)
    res["equipements"] = {mid: len(v["n"]) for mid, v in d.items()}
    return res


# F2.ecrire_usd = ecrire_usd_l2  (intégration de l'étape 2 : comportement repris dans le code commun)


# ------------------------------------------------------------------------------------------------------- exports
def _det(geo, nom, defaut=None):
    a = geo.findGlobalAttrib(nom)
    if a is None:
        return defaut
    v = geo.attribValue(nom)
    if isinstance(v, tuple):
        return [(_r(x) if isinstance(x, float) else x) for x in v]
    return _r(v) if isinstance(v, float) else v


def exporter_autoroute(au, dossier):
    dossier.mkdir(parents=True, exist_ok=True)
    ctl = au.geometry(3)
    eq = au.geometry(1)
    sol = au.geometry(0)
    mq = au.geometry(2)
    noms_m = ("ra_m_noeuds", "ra_m_genres", "ra_m_cles", "ra_m_sJ", "ra_m_s5", "ra_m_sfar", "ra_m_s_aplat",
              "ra_m_s_fin_chevrons", "ra_m_aire_musoir", "ra_m_aire_tpl", "ra_m_chevrons", "ra_m_aire_aplat",
              "ra_m_angle_bissectrice_deg", "ra_m_u", "ra_m_largeur_contour_principale", "ra_m_largeur_contour_bretelle")
    noms_s = ("ra_s_ids", "ra_s_modeles", "ra_s_routes", "ra_s_cotes", "ra_s_longueur", "ra_s_modules", "ra_s_base",
              "ra_s_hauteur", "ra_s_pas_module")
    raccord = {k: _det(ctl, k, []) for k in ("ra_bretelles", "ra_dz", "ra_principales", "ra_genres")}
    musoirs = {k[5:]: _det(ctl, k, []) for k in noms_m}
    seps = {k[5:]: _det(ctl, k, []) for k in noms_s}
    # sol des musoirs et marques (polygones locaux x, y, z)
    gore, marques = [], []
    for pr in sol.prims():
        r = pr.attribValue("route")
        if not r.startswith("C-"):
            continue
        gore.append({"carrefour": r, "classe": pr.attribValue("classe"), "materiau_id": pr.attribValue("materiau_id"),
                     "P": [[_r(v.point().position()[0], 4), _r(-v.point().position()[2], 4), _r(v.point().position()[1], 4)]
                           for v in pr.vertices()],
                     "st": [[_r(v.point().attribValue("s"), 4), _r(v.point().attribValue("t"), 4)] for v in pr.vertices()]})
    for pr in mq.prims():
        marques.append({"pj_entite": pr.attribValue("pj_entite"), "classe": pr.attribValue("classe"),
                        "type": pr.attribValue("type"), "carrefour": pr.attribValue("carrefour"),
                        "materiau_id": pr.attribValue("materiau_id"),
                        "P": [[_r(v.point().position()[0], 4), _r(-v.point().position()[2], 4)] for v in pr.vertices()],
                        "st": [[_r(v.point().attribValue("s"), 4), _r(v.point().attribValue("t"), 4)] for v in pr.vertices()]})
    (dossier / "musoirs.json").write_text(json.dumps({"schema": "rg_musoirs/0.1", "raccord_bretelles": raccord,
                                                      "musoirs": musoirs, "sol": gore, "marques": marques},
                                                     ensure_ascii=False) + "\n", encoding="utf-8")
    # équipements : comptes par classe, points (x, y, z, s) des faces par classe pour le contrôle (coupes)
    par_classe = {}
    for pr in eq.prims():
        par_classe[pr.attribValue("classe")] = par_classe.get(pr.attribValue("classe"), 0) + 1
    pts = [[_r(p.position()[0], 4), _r(-p.position()[2], 4), _r(p.position()[1], 4), _r(p.attribValue("s"), 4)]
           for p in eq.points()]
    cls = []
    for p in eq.points():
        prs = p.prims()
        cls.append(prs[0].attribValue("classe") if prs else "")
    (dossier / "equipements.json").write_text(json.dumps({
        "schema": "rg_equipements/0.1", "separateurs": seps, "faces_par_classe": par_classe,
        "points": pts, "classes_points": cls}, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"musoirs": len(musoirs.get("noeuds", [])), "faces_musoir": len(gore), "marques_musoir": len(marques),
            "separateurs": len(seps.get("ids", [])), "faces_equipements": len(eq.prims()), "faces_par_classe": par_classe,
            "raccord_bretelles": raccord}


# ------------------------------------------------------------------------------------------------------- rendus
def _projeter(graphe_geo, x, y):
    pr = graphe_geo.prims()[0]
    pts = pr.points()
    S = [p.attribValue("s") for p in pts]
    P = [(p.position()[0], -p.position()[2]) for p in pts]
    best = None
    n = len(P)
    for i in range(n - 1):
        (ax, ay), (bx, by) = P[i], P[i + 1]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        if L2 < 1e-12:
            continue
        u = ((x - ax) * vx + (y - ay) * vy) / L2
        if i > 0:
            u = max(u, 0.0)
        if i < n - 2:
            u = min(u, 1.0)
        fx, fy = ax + u * vx, ay + u * vy
        d = math.hypot(x - fx, y - fy)
        if best is None or d < best[0]:
            L = math.sqrt(L2)
            best = (d, S[i] + u * (S[i + 1] - S[i]), ((x - fx) * (-vy) + (y - fy) * vx) / L)
    return best[1], best[2]


def _route_pt(graphe_geo, rid, s, t):
    for pr in graphe_geo.prims():
        if pr.attribValue("id") != rid:
            continue
        pts = pr.points()
        for i in range(len(pts) - 1):
            s0, s1 = pts[i].attribValue("s"), pts[i + 1].attribValue("s")
            if s0 <= s <= s1 or i == len(pts) - 2:
                u = (s - s0) / max(s1 - s0, 1e-12)
                a, b = pts[i].position(), pts[i + 1].position()
                ga, gb = pts[i].attribValue("gauche"), pts[i + 1].attribValue("gauche")
                x = a[0] + u * (b[0] - a[0])
                y = -(a[2] + u * (b[2] - a[2]))
                gx, gy = ga[0] + u * (gb[0] - ga[0]), -(ga[2] + u * (gb[2] - ga[2]))
                n = math.hypot(gx, gy)
                return x + t * gx / n, y + t * gy / n
    raise KeyError(rid)


def vues_scene(m, graphe_geo, scene, musoirs):
    """Caméras (repère (s, t, h) de la route 0 du rendu) et vue de dessus (centre local, largeur)."""
    routes = {r["id"]: r for r in m["routes"]}
    p0 = m["routes"][0]
    L = float(p0["ligne_reference"].get("longueur_m") or 0.0) or graphe_geo.prims()[0].attribValue("longueur_m")
    # voie de droite du sens « avant » de la route 0 (t du milieu de la voie la plus à droite)
    sec = p0["sections"][0]
    pr = next(x for x in m["profils"] if x["id"] == sec["profil"])
    w = [float(b["largeur"]) if isinstance(b["largeur"], (int, float)) else 3.5 for b in pr["bandes"]]
    ref = int(pr["reference"]["limite"])
    T = [0.0] * (len(w) + 1)
    T[ref] = -float(pr["reference"].get("decalage_m", 0.0))
    for i in range(ref - 1, -1, -1):
        T[i] = T[i + 1] + w[i]
    for i in range(ref + 1, len(w) + 1):
        T[i] = T[i - 1] - w[i - 1]
    voies = [(0.5 * (T[i] + T[i + 1])) for i, b in enumerate(pr["bandes"]) if b["type"].startswith("voie") and b.get("sens") == "avant"]
    t_droite = min(voies) if voies else -1.75
    t_gauche = max(voies) if voies else -1.75
    tmin, tmax = min(T), max(T)
    propres = {}
    if not musoirs.get("noeuds"):
        s_c = min(150.0, 0.25 * L) if L > 400 else 0.5 * L
        cx, cy = _route_pt(graphe_geo, p0["id"], s_c + 10.0, 0.5 * (tmin + tmax))
        largeur = 84.0
        propres["conducteur"] = ((s_c - 40.0, t_droite, 1.20), (s_c + 30.0, t_droite + 0.4, 0.9), 24)
        return propres, (cx, cy), largeur, f"voie de droite (t = {t_droite:.2f} m), s = {s_c - 40:.0f} m"
    sJ, s5, sfar = musoirs["sJ"][0], musoirs["s5"][0], musoirs["sfar"][0]
    genre = musoirs["genres"][0]
    b = next(r for r in m["routes"] if r.get("categorie") == "bretelle")
    Lb = float(b["ligne_reference"]["longueur_m"])
    # dessus : du nez du terre-plein latéral à 40 m au-delà de la jonction, centré sur le musoir
    s_mid = 0.5 * (sfar + sJ)
    xm, ym = _route_pt(graphe_geo, p0["id"], s_mid, tmin + 1.0)
    largeur = min(max(abs(sJ - sfar) + 30.0, 120.0), 200.0)
    if genre == "entree":
        # conducteur sur la bretelle, 70 m avant la jonction, voie de la bretelle (1,50 m à gauche de sa référence)
        oe = _route_pt(graphe_geo, b["id"], Lb - 70.0, 1.5)
        ci = _route_pt(graphe_geo, p0["id"], sJ + 20.0, t_droite - 1.0)
        so, to = _projeter(graphe_geo, *oe)
        sc_, tc = _projeter(graphe_geo, *ci)
        propres["conducteur"] = ((so, to, 1.20), (sc_, tc, 0.9), 24)
        leg = f"conducteur (1,20 m) sur la bretelle, 70 m avant la jonction"
    else:
        so = sJ - 70.0
        propres["conducteur"] = ((so, t_droite, 1.20), (sJ + 25.0, t_droite - 3.0, 0.9), 24)
        leg = f"conducteur (1,20 m), voie de droite de la principale, 70 m avant la divergence"
    # oblique 3/4 du musoir, depuis l'arrière droit (côté bretelle), 14 m de haut, à 45° environ
    s_cible = 0.5 * (s5 + sJ)
    xc, yc = _route_pt(graphe_geo, p0["id"], s_cible + 6.0, tmin + 2.0)
    xo, yo = _route_pt(graphe_geo, p0["id"], s_cible - 32.0, tmin - 30.0)
    so2, to2 = _projeter(graphe_geo, xo, yo)
    sc2, tc2 = _projeter(graphe_geo, xc, yc)
    propres["oblique"] = ((so2, to2, 14.0), (sc2, tc2, 0.0), 24)
    return propres, (xm, ym), largeur, leg


NOMS = {"conducteur": "conducteur_autoroute", "oblique": "oblique_autoroute"}


def installer_rendu(vues, propres, centre, largeur, legende):
    import rendu_l2b as RB
    import planches as PL
    # béton des séparateurs (catalogue : beton_prefa_lisse, albédo 0,242) recalé comme le béton gris des bordures
    # (rendu_l2b : bordure 0,349, gris chaud ~30°) : rendu seulement, matériau inchangé
    RB.ECHELLE_ALBEDO.setdefault("beton_prefa_lisse", RB.ECHELLE_ALBEDO["beton_bordure_gris"])
    RB.ATTENUER_NORMALE.setdefault("beton_prefa_lisse", 0.35)
    origine = RB.rendre_scene
    dessus_origine = RB._dessus
    res_origine = RB.RES_DESSUS

    def rendre_scene(n2, n2b, sc, dossier, parent, decor_etape2=False, echantillons=None):
        def dessus(stage, c, z, larg, res):
            return dessus_origine(stage, centre, z, largeur, res)
        RB._dessus = dessus
        RB.RES_DESSUS = (1092, 546)
        noms = [NOMS.get(v, v) for v in vues]
        vp = {NOMS[k]: v for k, v in propres.items() if k in NOMS}
        try:
            origine(n2, n2b, sc, dossier, parent, vues=vp, decor_etape2=decor_etape2, seulement=noms,
                    echantillons=echantillons)
        finally:
            RB._dessus = dessus_origine
            RB.RES_DESSUS = res_origine
        d = Path(dossier) / "rendus"
        pngs = {p.stem: p for p in d.glob("*.png") if not p.stem.startswith("planche")}
        PL.planche_vues(sc, pngs, [v for v in noms if v in pngs], d / f"planche_{sc}.png",
                        legendes={"dessus": f"dessus ({largeur:.0f} m de large)", "conducteur_autoroute": legende,
                                  "oblique_autoroute": "vue oblique 3/4 du musoir (14 m de haut)"})
    return rendre_scene


# ------------------------------------------------------------------------------------------------------- pilote
VUES = {"A3_bretelle_entree": ("dessus", "oblique", "conducteur")}


def fabriquer(entrees, sortie, signatures, rendus=False):
    lire, graphe, prof, n2, n2b = reseau()
    produits = []
    for e in entrees:
        scene, chemin_modele, info = FG.preparer_entree(e, sortie)
        dsc = Path(sortie) / scene
        d1 = dsc / "l1"
        da = dsc / "autoroute"
        d1.mkdir(parents=True, exist_ok=True)
        lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
        for n in (lire, graphe, prof):
            try:
                n.cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {x}" for c in (n,) + n.allSubChildren() for x in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err))
        donnees = FG.extraire(lire, graphe, prof)
        courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene, "lot": "L1 (lot autoroutes)",
                   "modele": {"fichier": FG.rel(chemin_modele), "sha256": FG.sha256(chemin_modele)}}
        courbes.update(donnees)
        (d1 / "courbes_controle.json").write_text(json.dumps(courbes, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
        man1 = {"schema": "rg_manifest/0.1", "pilote": VERSION, "scene": scene, "entree": info, "modele": courbes["modele"],
                "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
                "hda": signatures, "parametres": donnees["parametres"], "comptes": donnees["comptes"],
                "avertissements": FG.avertissements(lire, graphe, prof),
                "fichiers": {"courbes_controle.json": FG.sha256(d1 / "courbes_controle.json")}}
        (d1 / "manifest_l1.json").write_text(json.dumps(man1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        au = n2["autoroute"]
        try:
            au.cook(force=True)
        except hou.OperationFailed:
            pass
        err = [f"{c.path()} : {x}" for c in (au,) + au.allSubChildren() for x in c.errors()]
        if err:
            raise SystemExit(f"{scene} : erreurs de cuisson (rg::autoroute)" + chr(10) + chr(10).join(err[:20]))
        d2, man2 = F2.fabriquer_scene(n2, scene, dsc, signatures, info)
        d2b, man2b = F2B.fabriquer_scene(n2b, scene, dsc, signatures, info)
        ca = exporter_autoroute(au, da)
        fichiers = {p.name: sha256(p) for p in sorted(da.iterdir()) if p.is_file() and p.name != "manifest_autoroute.json"}
        man = {"schema": "rg_manifest_autoroute/0.1", "pilote": VERSION, "scene": scene, "entree": info,
               "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": ca,
               "avertissements": sorted({w for c in (au,) + au.allSubChildren() for w in c.warnings()
                                         if "mis-match of attributes" not in w}),
               "fichiers": fichiers}
        (da / "manifest_autoroute.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{scene} : autoroute {ca['separateurs']} séparateur(s), {ca['faces_equipements']} faces d'équipement, "
              f"{ca['musoirs']} musoir(s) ({ca['faces_musoir']} faces de sol, {ca['marques_musoir']} marques), raccord "
              f"{ca['raccord_bretelles']} ; L2 sol {man2['controles_houdini']['faces_sol']} faces -> {FG.rel(dsc)}")
        if rendus:
            m = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
            mus = json.loads((da / "musoirs.json").read_text(encoding="utf-8"))["musoirs"]
            vv = VUES.get(scene, ("dessus", "conducteur"))
            propres, centre, largeur, leg = vues_scene(m, graphe.geometry(), scene, mus)
            print(f"{scene} : rendus {list(vv)} ; dessus {largeur:.0f} m centré {centre}")
            installer_rendu(vv, propres, centre, largeur, leg)(n2, n2b, scene, dsc, lire.parent())
        produits.append(str(dsc))
    return produits


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="+")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    a = ap.parse_args()
    signatures = construire_hda(forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    produits = fabriquer(a.entrees, a.sortie, signatures, rendus=a.rendus)
    if a.verifier_determinisme:
        autre = TMP_A / "determinisme"
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)],
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer([str(Path(p) / "l1") for p in produits], autre, True, True)
        # fichiers du lot (manifeste : chemins de sortie retirés)
        for p in produits:
            for f in sorted((Path(p) / "autoroute").glob("*.json")):
                if f.name.startswith("manifest"):
                    continue
                g = autre / Path(p).name / "autoroute" / f.name
                n += 1
                if not g.exists() or g.read_bytes() != f.read_bytes():
                    ecarts.append(f"{Path(p).name}/autoroute/{f.name}")
        print("déterminisme :", f"identique ({n} fichiers)" if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
