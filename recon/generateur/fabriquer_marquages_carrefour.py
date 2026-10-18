"""Pilote du lot L4 (marquages, trajectoires, conflits et zone de conflit des carrefours plans ; hython Houdini 22).

    hython recon/generateur/fabriquer_marquages_carrefour.py SCENE.yaml [SCENE.yaml ...] [--sortie DOSSIER] [--rendus]
                                                             [--construire-hda] [--verifier-determinisme]

Même chaîne que fabriquer_carrefours.py (lot L3 : fonctions importées sans modification), complétée par l'HDA du lot
(recon/generateur/hda/rg_marquages_carrefour) :
    rg::carrefours (SOLVEUR) + rg::nivellement (NIVEAUX) + rg::graphe + rg::marquages (LIGNES)
        -> rg::marquages_carrefour -> 1 LIGNES (section filtrée + guidage + axe prolongé) -> pj::marquage_solide (2 mm)
                                    -> 2 MARQUES (flèches, figurines des sas) + MARQUES de rg::marquages et du carrefour
                                       -> pj::marquage_solide (3 mm)
                                    -> 3 DONNÉES (voies, trajectoires, conflits, zone de conflit) -> exports l4/
    les flèches des branches de carrefour du modèle ne sont plus posées par rg::marquages (ponctuels filtrés) : l'HDA du
    lot les pose au gabarit exact, à 1,50 m de la ligne qui couvre la voie.
Sorties : celles des lots L1-L3 dans recon/out/generateur/<scene>/ et l4/ : trajectoires.json, conflits.json,
zone_conflit.json, guidage.json, graphe_voies.json, marques_l4.json (empreintes et table), lignes_retirees.json,
mesures_l4.json, manifest_l4.json ; rendus (J5 : dessus, oblique 3/4, conducteur sur deux approches ; J1-J4 : 2 vues).
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
import fabriquer_carrefours as FC  # noqa: E402

FG, F2, F2B = FC.FG, FC.F2, FC.F2B
VERSION = "fabriquer_marquages_carrefour/1.0 (lot L4)"
TMP_L4 = ICI / "tmp" / "l4"
TAGS = ("vehicule", "velo", "pieton", "feux", "cedez", "stop", "prioritaire", "voie_affectee", "guidage", "sas")


def _r(x, n=6):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False):
    sigs = FC.construire_hda(forcer=forcer)
    spec = importlib.util.spec_from_file_location("construire_rg_marquages_carrefour",
                                                  ICI / "hda" / "rg_marquages_carrefour" / "construire.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    c = mod.construire(ICI / "hda" / "rg_marquages_carrefour")
    sigs[f"rg::marquages_carrefour::{R.VERSION}"] = R.signature(c)
    return sigs


# ------------------------------------------------------------------------------------------------------- réseau
VEX_SANS_FLECHES = r"""
// flèches d'affectation des branches de carrefour (modèle : marquages « fleche » ancrés à un carrefour) : posées par
// rg::marquages_carrefour (lot L4), retirées ici des ponctuels lus par rg::marquages
if (s@famille_modele == "marquage" && s@type == "fleche" && find(s@props, "\"carrefour\"") >= 0) removepoint(0, @ptnum);
"""


def reseau():
    lire, car, graphe, prof, n2, n2b = FC.reseau()
    inserer(lire, car, graphe, prof, n2, n2b)
    return lire, car, graphe, prof, n2, n2b


def inserer(lire, car, graphe, prof, n2, n2b):
    """rg::marquages_carrefour ajoutée au réseau du lot L3 (ou L3 + L5) : réutilisée par fabriquer_generateur.py."""
    obj = lire.parent()
    mq = n2b["marquages"]
    sf = obj.createNode("attribwrangle", "ponctuels_sans_fleches_carrefour")
    sf.parm("class").set(2)
    sf.parm("snippet").set(VEX_SANS_FLECHES)
    sf.setInput(0, lire, 3)
    mq.setInput(3, sf)
    mc = obj.createNode(R.nom_type("marquages_carrefour"), "marquages_carrefour")
    mc.setInput(0, car, 2)
    mc.setInput(1, n2["nivellement"], 0)
    mc.setInput(2, graphe, 0)
    lm = obj.createNode("merge", "lignes_et_marques_l2b")
    lm.setInput(0, mq, 0)
    lm.setInput(1, mq, 1)
    mc.setInput(3, lm, 0)
    mc.parm("fichier").setExpression('chs("../lire_modele/fichier")', hou.exprLanguage.Hscript)
    n2b["peinture_lignes"].setInput(0, mc, 0)
    mm = obj.node("marques_et_carrefour")
    mm.setInput(0, mc, 1)                 # marques de rg::marquages filtrées + marques du lot L4
    n2b["marquages_carrefour"] = mc
    n2b["ponctuels_sans_fleches"] = sf
    obj.layoutChildren()
    return mc


_CUIRE_L2B = F2B.cuire


def cuire_l2b(noeuds, scene):
    """F2B.cuire, puis contournement de pj::marquage_solide décidé sur son entrée réelle (lignes filtrées et marques du
    carrefour comprises) et contrôle des erreurs de rg::marquages_carrefour."""
    mc = noeuds["marquages_carrefour"]
    try:
        mc.cook(force=True)
    except hou.OperationFailed:
        pass
    err = [f"{c.path()} : {e}" for c in (mc,) + mc.allSubChildren() for e in c.errors()]
    if err:
        raise SystemExit(f"{scene} : erreurs de cuisson (lot L4)" + chr(10) + chr(10).join(err[:20]))
    _CUIRE_L2B(noeuds, scene)
    change = False
    for nom in ("peinture_lignes", "peinture_marques"):
        n = noeuds[nom]
        src = n.inputs()[0] if n.inputs() else None
        vide = src is None or len(src.geometry().prims()) == 0
        if n.isBypassed() != vide:
            n.bypass(vide)
            change = True
    if change:
        for nom in ("peinture_lignes", "peinture_marques", "mesure"):
            noeuds[nom].cook(force=True)


# F2B.cuire = cuire_l2b  (intégration de l'étape 2 : comportement repris dans le code commun)


# ------------------------------------------------------------------------------------------------------- exports
def _val(o, nom):
    try:
        v = o.attribValue(nom)
    except hou.OperationFailed:
        return None
    if isinstance(v, float):
        return _r(v)
    if isinstance(v, tuple):
        return [(_r(x) if isinstance(x, float) else x) for x in v]
    return v


def _xy(p):
    q = p.position()
    return [_r(q[0]), _r(-q[2])]


def _prims(geo, groupe, attrs=None):
    g = geo.findPrimGroup(groupe)
    if g is None:
        return []
    noms = attrs or sorted(a.name() for a in geo.primAttribs())
    return [{"points": [_xy(p) for p in pr.points()], **{n: _val(pr, n) for n in noms}} for pr in g.prims()]


def _points(geo, groupe, attrs=None):
    g = geo.findPointGroup(groupe)
    if g is None:
        return []
    noms = attrs or sorted(a.name() for a in geo.pointAttribs() if a.name() != "P")
    return [{"xy": _xy(p), **{n: _val(p, n) for n in noms}} for p in g.points()]


def _ecrire(f, d):
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


ATTR_VOIE = ("carrefour", "branche", "route", "bande", "type", "entrante", "t_axe", "t0", "t1", "largeur", "s_end",
             "s_j", "d_j", "h")
ATTR_TRAJ = ("id", "carrefour", "mouvement", "de_branche", "de_bande", "vers_branche", "vers_bande", "tags", "vehicule",
             "rayon", "rayon_min", "regle_rayon", "angle_deg", "longueur", "ext_entree", "ext_sortie", "dev_entree",
             "dev_sortie", "ecart_lateral", "guide", "guidage", "garde_guidage", "priorite", "phases", "faisable")


def exporter_l4(n2b, car_geo, d4, modele, scene):
    mc = n2b["marquages_carrefour"]
    g = mc.geometry(2)
    o = modele["repere"]["origine_l93"]
    voies = _points(g, "voie", ATTR_VOIE)
    traj = _prims(g, "trajectoire_l4", ATTR_TRAJ)
    conf = _points(g, "conflit", ("type", "a", "b", "carrefour", "famille", "n_points", "meme_phase"))
    zone = _prims(g, "zone_conflit", ("carrefour", "partie", "branche", "aire_m2", "s_arret"))
    guid = _prims(g, "guidage", ("id", "carrefour", "modulation", "largeur_m", "mouvements", "rayon_raccord",
                                 "angle_oblique_deg", "longueur"))
    br4 = _points(g, "br4", ("carrefour", "branche", "route", "regime", "ligne_type", "ligne_distance", "s_end",
                             "s_front", "s_j", "d_j", "s_tan_g", "s_tan_d", "t_g", "t_d", "azimut", "rayon_coin_g",
                             "rayon_coin_d", "droit_g", "droit_d", "sas_prof", "entrantes", "sortantes", "bandes_ids",
                             "bandes_sens", "bandes_types", "Pe", "dir", "nrm", "centre"))
    axes = _prims(g, "voie_axe", ("carrefour", "branche", "route", "bande", "v_type", "v_entrante", "s0", "s1"))
    table = _points(g, "table_l4")
    det = {}
    for nom in ("rg_l4_conflits", "rg_l4_zone_m2", "rg_l4_avertissements", "rg_l4_axe", "rg_l4_modele"):
        v = _val(g, nom) if g.findGlobalAttrib(nom) else None
        det[nom[6:]] = list(v) if isinstance(v, (tuple, list)) else v
    gl = mc.geometry(0)
    gm = mc.geometry(1)
    noms = ("pj_entite", "id", "classe", "type", "gabarit", "materiau_id", "route", "cle", "modulation", "largeur_m",
            "s0", "s1", "rang", "partie", "anneau", "rg_l4")
    lignes = [{"xy": [_xy(p) for p in pr.points()], **{n: _val(pr, n) for n in noms}} for pr in gl.prims()]
    marques = [{"xy": [_xy(p) for p in pr.points()], **{n: _val(pr, n) for n in noms}} for pr in gm.prims()
               if _val(pr, "rg_l4") == 1]
    gc = mc.geometry(3)
    retirees = [{"xy": [_xy(p) for p in pr.points()], **{n: _val(pr, n) for n in
                                                          ("pj_entite", "route", "cle", "modulation", "s0", "s1",
                                                           "rg_l4_raison", "classe")}}
                for pr in gc.prims() if pr.attribValue("rg_l4_retire") > 0]
    entete = {"scene": scene, "repere": {"origine_l93": o, "local": "x, y = L93 − origine"}}
    _ecrire(d4 / "trajectoires.json", {"schema": "rg_trajectoires_l4/0.1", **entete, "branches": br4, "voies": voies,
                                       "trajectoires": traj, "details": det})
    _ecrire(d4 / "conflits.json", {"schema": "rg_conflits_l4/0.1", **entete, "conflits": conf,
                                   "resume": det.get("conflits")})
    _ecrire(d4 / "zone_conflit.json", {"schema": "rg_zone_conflit_l4/0.1", **entete, "zones": zone,
                                       "aire_m2": det.get("zone_m2")})
    _ecrire(d4 / "guidage.json", {"schema": "rg_guidage_l4/0.1", **entete, "lignes": guid})
    _ecrire(d4 / "marques_l4.json", {"schema": "rg_marques_l4/0.1", **entete,
                                     "lignes_finales": lignes, "marques_l4": marques, "table": table,
                                     "axe_prioritaire": det.get("axe")})
    _ecrire(d4 / "lignes_retirees.json", {"schema": "rg_lignes_retirees_l4/0.1", **entete, "morceaux": retirees})
    graphe = graphe_voies(axes, traj, zone, car_geo, br4, entete)
    _ecrire(d4 / "graphe_voies.json", graphe)
    return {"voies": len(voies), "trajectoires": len(traj), "conflits": len(conf), "zones": len(zone),
            "guidage": len(guid), "lignes_finales": len(lignes), "marques_l4": len(marques),
            "lignes_retirees": len(retirees), "graphe": graphe["comptes"], "avertissements": det.get("avertissements")}


def graphe_voies(axes, traj, zone, car_geo, br4, entete):
    """graphe_voies.json (ZoneGraph, routage) : voies (axes des bandes de la route jusqu'à la limite de jonction s_j),
    connecteurs (trajectoires L4), zones de conflit, traversées piétonnes ; ≤ 32 étiquettes (12M § 7)."""
    reg = {(b["carrefour"], b["branche"]): b["regime"] for b in br4}
    voies = []
    for a in axes:
        vid = f"{a['route']}/{a['bande']}"
        tags = ["velo"] if a["v_type"] == "bande_cyclable" else ["vehicule"]
        if a["v_type"] == "voie_tourne_gauche":
            tags.append("voie_affectee")
        voies.append({"id": vid, "route": a["route"], "bande": a["bande"], "branche": a["branche"],
                      "carrefour": a["carrefour"], "sens": "entrante" if a["v_entrante"] else "sortante",
                      "type": a["v_type"], "s0": a["s0"], "s1": a["s1"], "tags": tags, "polyligne": a["points"],
                      "successeurs": [], "predecesseurs": []})
    par_id = {v["id"]: v for v in voies}
    route_de = {(b["carrefour"], b["branche"]): b["route"] for b in br4}
    conn = []
    for t in traj:
        de = par_id.get(f"{route_de.get((t['carrefour'], t['de_branche']))}/{t['de_bande']}")
        ve = par_id.get(f"{route_de.get((t['carrefour'], t['vers_branche']))}/{t['vers_bande']}")
        tags = [t["tags"]] if t["tags"] in TAGS else ["vehicule"]
        rg = reg.get((t["carrefour"], t["de_branche"]), "")
        if rg in TAGS:
            tags.append(rg)
        if t["guide"]:
            tags.append("guidage")
        c = {"id": t["id"], "carrefour": t["carrefour"], "de": de["id"] if de else None, "vers": ve["id"] if ve else None,
             "mouvement": t["mouvement"], "rayon_m": t["rayon"], "longueur_m": t["longueur"], "phases": t["phases"] or [],
             "priorite": t["priorite"], "tags": tags, "polyligne": t["points"]}
        conn.append(c)
        if de:
            de["successeurs"].append(t["id"])
        if ve:
            ve["predecesseurs"].append(t["id"])
    passages = []
    gp = car_geo.findPointGroup("passage")
    for p in (gp.points() if gp else []):
        a0, a1 = p.attribValue("axe0"), p.attribValue("axe1")
        passages.append({"id": p.attribValue("id"), "route": p.attribValue("route"), "carrefour": p.attribValue("carrefour"),
                         "axe": [[_r(a0[0]), _r(a0[1])], [_r(a1[0]), _r(a1[1])]], "largeur_m": _r(p.attribValue("largeur")),
                         "tags": ["pieton"]})
    zones = [{"carrefour": z["carrefour"], "partie": z["partie"], "branche": z["branche"], "polygone": z["points"],
              "tags": ["vehicule", "velo"]} for z in zone]
    tags = sorted({x for v in voies for x in v["tags"]} | {x for c in conn for x in c["tags"]} | {"pieton"} if passages
                  else {x for v in voies for x in v["tags"]} | {x for c in conn for x in c["tags"]})
    entrantes = [v for v in voies if v["sens"] == "entrante"]
    sans = [v["id"] for v in entrantes if not v["successeurs"]]
    comptes = {"voies": len(voies), "voies_entrantes": len(entrantes), "entrantes_sans_successeur": sans,
               "connecteurs": len(conn), "connecteurs_sans_voie": [c["id"] for c in conn if not c["de"] or not c["vers"]],
               "passages": len(passages), "zones": len(zones), "etiquettes": len(tags)}
    return {"schema": "rg_graphe_voies/0.1", **entete, "etiquettes": tags, "voies": voies, "connecteurs": conn,
            "zones": zones, "passages": passages, "comptes": comptes,
            "regles": {"etiquettes_max": 32, "source": "12M § 7 (ZoneGraph : 32 étiquettes au plus)"}}


def mesurer_peinture(n2b, d4):
    """Dessus de la peinture des marques du lot L4 − sol fabriqué (rayon vertical) : sommets et centres des faces du
    dessus (mesure de fabriquer_l2b : nœud « mesure »), entités ML_L4_* (guidage, axe) et MQ_L4_* (flèches, sas)."""
    g = n2b["mesure"].geometry()
    au = g.pointFloatAttribValues("au_dessus")
    de = g.pointIntAttribValues("dessus")
    res = {}
    for pr in g.prims():
        ent = pr.attribValue("pj_entite")
        if not (ent.startswith("ML_L4_") or ent.startswith("MQ_L4_")):
            continue
        fam = "lignes_l4" if ent.startswith("ML_L4_") else "marques_l4"
        r = res.setdefault(fam, {"entites": set(), "sommets": [], "centres": [], "sans_sol": 0})
        r["entites"].add(ent)
        for p in pr.points():
            k = p.number()
            if de[k] == 1:
                if au[k] < -1e8:
                    r["sans_sol"] += 1
                else:
                    r["sommets"].append(au[k])
        if pr.attribValue("dessus") == 1 and pr.attribValue("au_dessus_centre") > -1e8:
            r["centres"].append(pr.attribValue("au_dessus_centre"))
    out = {}
    for fam, r in res.items():
        s, c = r["sommets"], r["centres"]
        out[fam] = {"entites": len(r["entites"]), "sommets_dessus": len(s), "sans_sol": r["sans_sol"],
                    "au_dessus_min_m": _r(min(s), 5) if s else None, "au_dessus_max_m": _r(max(s), 5) if s else None,
                    "centres_min_m": _r(min(c), 5) if c else None, "centres_max_m": _r(max(c), 5) if c else None}
    m = {"schema": "rg_mesures_l4/0.1", "peinture": out,
         "note": "TQ-MQG-005 : dessus de la peinture à +2 à +3 mm du sol fabriqué (lignes 2 mm, marques 3 mm)"}
    _ecrire(d4 / "mesures_l4.json", m)
    return m


# ------------------------------------------------------------------------------------------------------- rendus
def vues_j5(donnees, graphe_geo):
    """Caméras propres de la scène phare : conducteur (1,20 m) sur deux approches (artère ouest dans la voie de TAG ;
    rue sud dans sa voie entrante), 34 m avant l'embouchure (s_end), regard 12 m au-delà."""
    out = {}
    g = donnees
    for nom, br, bande in (("conducteur_ouest_tag", "B-ouest", "tag1"), ("conducteur_sud", "B-sud", "v2")):
        for p in g.findPointGroup("voie").points():
            if p.attribValue("branche") == br and p.attribValue("bande") == bande and p.attribValue("entrante") == 1:
                P = p.position()
                h = p.attribValue("h")
                dj = p.attribValue("d_j")                  # le point de voie est à s_j = s_end − d_j
                x, y = P[0], -P[2]
                oe = (x + (dj - 34.0) * h[0], y + (dj - 34.0) * h[1])
                ci = (x + (dj + 12.0) * h[0], y + (dj + 12.0) * h[1])
                s0, t0 = FC.st_route0(graphe_geo, *oe)
                s1, t1 = FC.st_route0(graphe_geo, *ci)
                out[nom] = ((s0, t0, 1.20), (s1, t1, 0.5), 24)
    return out


LEGENDES = {"conducteur_carrefour": "conducteur (1,20 m)", "oblique_carrefour": "vue oblique 3/4 du carrefour",
            "conducteur_ouest_tag": "conducteur (1,20 m), artère ouest, voie de TAG",
            "conducteur_sud": "conducteur (1,20 m), rue sud"}


def rendre(n2, n2b, scene, dsc, parent, modele, car, graphe):
    import rendu_l2b as RB
    import planches as PL
    phare = scene.startswith("J5")
    vv = ("dessus", "conducteur", "oblique") if phare else ("dessus", "conducteur")
    propres, centre, largeur, bcond = FC.vues_carrefour(modele, car.geometry(2), graphe.geometry(), vv)
    if phare:
        propres.pop("conducteur_carrefour", None)
        propres.update(vues_j5(n2b["marquages_carrefour"].geometry(2), graphe.geometry()))
        noms = ["dessus", "oblique_carrefour", "conducteur_ouest_tag", "conducteur_sud"]
    else:
        noms = ["dessus", "conducteur_carrefour"]
    dessus_origine = RB._dessus

    def dessus(stage, c, z, larg, res):
        return dessus_origine(stage, centre, z, largeur, res)
    RB._dessus = dessus
    try:
        RB.rendre_scene(n2, n2b, scene, dsc, parent, vues=propres, seulement=noms)
    finally:
        RB._dessus = dessus_origine
    d = Path(dsc) / "rendus"
    pngs = {p.stem: p for p in d.glob("*.png") if not p.stem.startswith("planche")}
    leg = dict(LEGENDES)
    leg["conducteur_carrefour"] = f"conducteur (1,20 m), branche {bcond}"
    PL.planche_vues(scene, pngs, [v for v in noms if v in pngs], d / f"planche_{scene}.png", legendes=leg)
    return noms


# ------------------------------------------------------------------------------------------------------- pilote
def fabriquer(entrees, sortie, signatures, rendus=False, avec_balayages=True):
    lire, car, graphe, prof, n2, n2b = reseau()
    mc = n2b["marquages_carrefour"]
    produits = []
    for e in entrees:
        scene, chemin_modele, info = FG.preparer_entree(e, sortie)
        dsc = Path(sortie) / scene
        d1, d3, d4 = dsc / "l1", dsc / "l3", dsc / "l4"
        for d in (d1, d3, d4):
            d.mkdir(parents=True, exist_ok=True)
        info_bal = []
        if avec_balayages:
            fb, bal = FC.balayages(chemin_modele, FC.TMP_L3 / scene)
            car.parm("balayages").set(str(fb).replace("\\", "/"))
            info_bal = [{k: v for k, v in b.items() if k != "exterieur"} for b in bal]
        else:
            car.parm("balayages").set("")
        lire.parm("fichier").set(str(chemin_modele).replace("\\", "/"))
        for n in (lire, car, graphe, prof):
            try:
                n.cook(force=True)
            except hou.OperationFailed:
                pass
            err = [f"{c.path()} : {x}" for c in (n,) + n.allSubChildren() for x in c.errors()]
            if err:
                raise SystemExit(f"{scene} : erreurs de cuisson" + chr(10) + chr(10).join(err))
        donnees = FG.extraire(lire, graphe, prof)
        courbes = {"schema": "rg_courbes_controle/0.1", "scene": scene, "lot": "L1 (+ L3 : routes coupées au carrefour)",
                   "modele": {"fichier": FG.rel(chemin_modele), "sha256": FG.sha256(chemin_modele)}}
        courbes.update(donnees)
        (d1 / "courbes_controle.json").write_text(json.dumps(courbes, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
        man1 = {"schema": "rg_manifest/0.1", "pilote": VERSION, "scene": scene, "entree": info, "modele": courbes["modele"],
                "houdini": hou.applicationVersionString(), "vex_jit": os.environ.get("HOUDINI_VEX_DISABLE_JIT") != "1",
                "hda": signatures, "parametres": donnees["parametres"], "comptes": donnees["comptes"],
                "avertissements": FG.avertissements(lire, car, graphe, prof),
                "fichiers": {"courbes_controle.json": FG.sha256(d1 / "courbes_controle.json")}}
        (d1 / "manifest_l1.json").write_text(json.dumps(man1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        FC.cuire(n2, scene)
        # usure des marques ajoutées : celle des lignes de rg::marquages (classe d'usure du modèle)
        mq = n2b["marquages"]
        try:
            mq.cook(force=True)
        except hou.OperationFailed:
            pass
        gl = mq.geometry(0)
        us = gl.prims()[0].attribValue("usure") if gl is not None and gl.prims() else 0.0
        mc.parm("usure_peinture").set(float(us))
        d2, man2 = F2.fabriquer_scene(n2, scene, dsc, signatures, info)
        d2b, man2b = F2B.fabriquer_scene(n2b, scene, dsc, signatures, info)
        c3 = FC.exporter_carrefours(n2, d3, info_bal)
        m3 = FC.mesurer_raccords(n2, d3)
        f3 = {p.name: sha256(p) for p in sorted(d3.iterdir()) if p.is_file() and p.name != "manifest_l3.json"}
        (d3 / "manifest_l3.json").write_text(json.dumps(
            {"schema": "rg_manifest_l3/0.1", "pilote": VERSION, "scene": scene, "entree": info,
             "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": c3, "raccords": m3,
             "fichiers": f3}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        modele = json.loads(Path(chemin_modele).read_text(encoding="utf-8"))
        c4 = exporter_l4(n2b, car.geometry(2), d4, modele, scene)
        m4 = mesurer_peinture(n2b, d4)
        f4 = {p.name: sha256(p) for p in sorted(d4.iterdir()) if p.is_file() and p.name != "manifest_l4.json"}
        (d4 / "manifest_l4.json").write_text(json.dumps(
            {"schema": "rg_manifest_l4/0.1", "pilote": VERSION, "scene": scene, "entree": info,
             "houdini": hou.applicationVersionString(), "hda": signatures, "comptes": c4, "peinture": m4["peinture"],
             "usure_peinture": _r(us), "fichiers": f4}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{scene} : L4 {json.dumps({k: v for k, v in c4.items() if k != 'avertissements'}, ensure_ascii=False)}")
        if c4.get("avertissements"):
            print(f"{scene} : avertissements L4 : {c4['avertissements']}")
        if rendus:
            noms = rendre(n2, n2b, scene, dsc, lire.parent(), modele, car, graphe)
            print(f"{scene} : rendus {noms}")
        produits.append(str(dsc))
    return produits


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="+")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    ap.add_argument("--sans-balayages", action="store_true")
    a = ap.parse_args()
    signatures = construire_hda(forcer=a.construire_hda)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    produits = fabriquer(a.entrees, a.sortie, signatures, rendus=a.rendus, avec_balayages=not a.sans_balayages)
    if a.verifier_determinisme:
        autre = TMP_L4 / "determinisme"
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)],
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer([str(Path(p) / "l1") for p in produits], autre, True, True)
        for p in produits:
            for lot in ("l3", "l4"):
                for f in sorted((Path(p) / lot).glob("*.json")):
                    if f.name.startswith("manifest_"):
                        continue
                    g = autre / Path(p).name / lot / f.name
                    n += 1
                    if not g.exists() or g.read_bytes() != f.read_bytes():
                        ecarts.append(str(f))
        print("déterminisme :", f"identique ({n} fichiers)" if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
