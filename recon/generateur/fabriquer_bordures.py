"""Pilote du lot « bordures » (hython Houdini 22) : fabrication avec tous les types de bordures et de caniveaux.

    hython recon/generateur/fabriquer_bordures.py ENTREE [ENTREE ...] [--sortie DOSSIER] [--rendus] [--vues V1,V2]
                                                  [--verifier-determinisme] [--construire-hda]

Même chaîne que fabriquer_generateur.py (--l2b), dont il importe les fonctions sans les modifier (l'agent
d'intégration fusionnera), avec les ajouts du lot (recon/generateur/commun/bordures_catalogue.py) :
  - description compilée avec l'extension du vocabulaire, des règles par défaut et du schéma (types T4, I3, I4, P4,
    CS4, GR_*, *_basse, *_surbaissee, ACCESBUS…) : `python commun/bordures_catalogue.py --compiler` ;
  - rg::nivellement construit (dans tmp/bordures/hda, sans toucher à hda/rg_nivellement) avec la table étendue ;
  - pj::bordure::2.1 et pj::caniveau::2.2 (table étendue) à la place de 2.0 et 2.1 ;
  - rg::vers_entites (lot bordures) : pièce d'abaissé de chaque type (paramètre pieces_abaisse) ;
  - elements.json : asset du catalogue route_fr de chaque élément posé (asset_id, motif ; pièces d'angle sortant /
    rentrant, raccords, équivalents) ;
  - rendus : 2 vues par scène (dessus, conducteur 1,20 m), vues propres à B01 (vue de dessus de toute la rue, vues
    rapprochées) ; planche ≤ 1092 px par scène.
Le pilote se relance avec HOUDINI_VEX_DISABLE_JIT=1 et les dossiers temporaires sur D: (rien n'est écrit sur C:).
"""
import argparse
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
TMP_HDA = ICI / "tmp" / "bordures" / "hda"
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
sys.path.insert(0, str(ICI / "commun"))
import rg_hda_outils as R  # noqa: E402
import fabriquer_generateur as FG  # noqa: E402
import fabriquer_l2 as F2  # noqa: E402
import bordures_catalogue as BC  # noqa: E402

VERSION = "fabriquer_bordures/1.0 (lot bordures)"
VUES_DEFAUT = ("dessus", "conducteur")
VUE_MAX_BATEAU = 0.05            # abaissés et entrées charretières (RF-MA-TRO-015 : 0,05) : pièce d'abaissé du type


def _charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------------------------------- description
def preparer_entree(entree, sortie):
    """FG.preparer_entree avec le compilateur étendu (commun/bordures_catalogue.py --compiler)."""
    entree = Path(entree).resolve()
    if entree.suffix.lower() not in (".yaml", ".yml"):
        return _preparer_entree_origine(entree, sortie)
    r = subprocess.run([FG.python_systeme(), "-B", str(ICI / "commun" / "bordures_catalogue.py"), "--compiler",
                        str(entree)], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=FG.env_systeme(), cwd=str(DEPOT))
    lignes = [x for x in r.stdout.splitlines() if " → " in x]
    if r.returncode or not lignes or " 0 erreur(s) de validation" not in lignes[-1]:
        raise SystemExit(f"{entree.name} : compilation en échec\n{r.stdout}\n{r.stderr}")
    dossier = Path(lignes[-1].split(" → ")[-1].strip())
    if not dossier.is_absolute():
        dossier = DEPOT / dossier
    scene = lignes[-1].split(" : ")[0].strip()
    from commun import conformite as CF
    comp = json.loads((dossier / "compilation.json").read_text(encoding="utf-8"))
    if CF.erreurs(comp) or CF.bloquants(comp):
        raise SystemExit(f"{entree.name} : fabrication refusée\n{CF.resume(comp)}")
    return scene, dossier / "modele_voie.json", {"description": FG.rel(entree), "sha256_description": FG.sha256(entree),
                                                 "compilation": FG.rel(dossier / "compilation.json"),
                                                 "compilateur": "commun/bordures_catalogue.py --compiler"}


_preparer_entree_origine = FG.preparer_entree


# ---------------------------------------------------------------------------------------------------- HDA
def construire_hda(forcer=False, l2=True):
    """HDA rg::* du dépôt (FG.construire_hda), rg::vers_entites reconstruite (lot bordures), rg::nivellement à table
    étendue construite dans tmp/bordures/hda (hda/rg_nivellement inchangée)."""
    sigs = _construire_hda_origine(forcer=forcer, l2=l2)
    d = ICI / "hda" / "rg_vers_entites"
    cible = _charger("construire_rg_vers_entites_b", d / "construire.py").construire(d)
    sigs[f"rg::vers_entites::{R.VERSION}"] = R.signature(cible)
    F2.installer_pj()                                  # pj::* d'origine et versions 2.0 / 2.1 (table d'origine)
    BC.installer_table_etendue()                       # table étendue pour les HDA construites ensuite
    cible = _charger("construire_rg_nivellement_b", ICI / "hda" / "rg_nivellement" / "construire.py").construire(
        TMP_HDA / "rg_nivellement")
    sigs[f"rg::nivellement::{R.VERSION} (table étendue, tmp/bordures/hda)"] = R.signature(cible)
    sigs.pop(f"rg::nivellement::{R.VERSION}", None)
    return sigs


_construire_hda_origine = FG.construire_hda


def installer_pj(forcer=False):
    """pj::* (F2.installer_pj, appelé par construire_hda) + pj::bordure::2.1 et pj::caniveau::2.2 (lot bordures)."""
    sigs = {}
    for dossier, fichier, cle in (("pj_bordure_v2_1", "pj_bordure_2.1.hdalc", "pj::bordure::2.1"),
                                  ("pj_caniveau_v2_2", "pj_caniveau_2.2.hdalc", "pj::caniveau::2.2")):
        d = ICI / "hda" / dossier
        cible = _charger(f"construire_{dossier}", d / "construire.py").construire(d)
        sigs[cle] = R.signature(cible)
    return sigs


def reseau(obj, lire, graphe, nom_type):
    n = _reseau_origine(obj, lire, graphe, nom_type)
    n["bordures"] = n["bordures"].changeNodeType("pj::bordure::2.1", keep_parms=True, keep_network_contents=False)
    n["caniveaux"] = n["caniveaux"].changeNodeType("pj::caniveau::2.2", keep_parms=True, keep_network_contents=False)
    ve = n["vers_entites"]
    ve.parm("pieces_abaisse").set(",".join(f"{k}:{v}" for k, v in sorted(BC.table_pieces_abaisse().items())))
    ve.parm("vue_max_bateau").set(VUE_MAX_BATEAU)
    return n


_reseau_origine = F2.reseau


# ---------------------------------------------------------------------------------------------------- éléments
ATTRS_SUP = ("angle_debut", "angle_fin", "sens", "fleche_mm", "proto_type")


def points_instances(geo, famille):
    out = _points_instances_origine(geo, famille)
    noms = {a.name() for a in geo.pointAttribs()}
    for d, p in zip(out, geo.points()):
        for k in ATTRS_SUP:
            if k in noms:
                v = p.attribValue(k)
                d[k] = F2._r(v) if isinstance(v, float) else v
        if "asset" in noms:
            d["prototype_pj"] = p.attribValue("asset")
    return out


_points_instances_origine = F2._points_instances


def _files(ent):
    """{id de file: (s cumulés, xy)} des courbes de bordure (rg::vers_entites, repère local)."""
    out = {}
    for pr in ent.geometry(0).prims():
        xy = [(p.position()[0], -p.position()[2]) for p in pr.points()]
        s = [0.0]
        for a, b in zip(xy, xy[1:]):
            s.append(s[-1] + math.dist(a, b))
        out[pr.attribValue("id")] = (s, xy)
    return out


def _cap(s, xy, x):
    """Cap (rad) de la file à l'abscisse x (segment non dégénéré le plus proche)."""
    for i in range(len(s) - 1):
        if s[i] - 1e-9 <= x <= s[i + 1] + 1e-9 and s[i + 1] - s[i] > 1e-6:
            return math.atan2(xy[i + 1][1] - xy[i][1], xy[i + 1][0] - xy[i][0])
    i = 0 if x < s[0] else len(s) - 2
    while i > 0 and s[i + 1] - s[i] <= 1e-6:
        i -= 1
    return math.atan2(xy[i + 1][1] - xy[i][1], xy[i + 1][0] - xy[i][0])


def exporter_elements(bor, can, dossier, ent=None):
    """F2.exporter_elements + asset du catalogue route_fr de chaque élément (asset_id, asset_motif) ; pièces d'angle :
    sens (sortant si la file tourne vers le trottoir, à gauche : angle saillant vu de la chaussée ; rentrant sinon) et
    déviation."""
    comptes = _exporter_elements_origine(bor, can, dossier, ent)
    f = Path(dossier) / "elements.json"
    el = json.loads(f.read_text(encoding="utf-8"))
    files = _files(ent) if ent is not None else {}
    lg = {"catalogue": 0.0, "sur_mesure": 0.0}
    for e in el:
        if e.get("famille") == "bordure" and (e.get("angle_debut") or e.get("angle_fin")) and e.get("bordure") in files:
            s, xy = files[e["bordure"]]
            sc = e["s0"] if e.get("angle_debut") else e["s1"]
            a1, a2 = _cap(s, xy, sc - 0.06), _cap(s, xy, sc + 0.06)
            dv = math.degrees(math.atan2(math.sin(a2 - a1), math.cos(a2 - a1)))
            e["angle_sens"] = "sortant" if dv > 0 else "rentrant"
            e["angle_deviation_deg"] = F2._r(dv, 2)
        a, motif = BC.asset_element(e)
        e["asset_id"] = a
        e["asset_motif"] = motif
        if e.get("kind") == "element":
            lg["catalogue" if a else "sur_mesure"] += float(e.get("longueur") or 0.0)
    f.write_text(json.dumps(el, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    comptes["longueur_assets_catalogue_m"] = F2._r(lg["catalogue"], 3)
    comptes["longueur_sur_mesure_m"] = F2._r(lg["sur_mesure"], 3)
    return comptes


_exporter_elements_origine = F2.exporter_elements


# ---------------------------------------------------------------------------------------------------- rendus
VUES_SCENE = {}          # scène -> {nom: ((s, t, h), (s, t, h), focale)} (vues rapprochées)
DESSUS_SCENE = {}        # scène -> (largeur m, (W, H))
RES_SCENE = {}           # scène -> résolution des vues perspectives
SUJET_SCENE = {}
ETIQUETTES_SCENE = {}    # scène -> étiquettes des tronçons (nuancier : planches annotées de la vue de dessus)


def charger_vues(fichier_yaml):
    """Vues propres d'une description (clé « vues_bordures » d'un fichier JSON voisin <scene>.vues.json)."""
    j = Path(fichier_yaml).with_suffix(".vues.json")
    if not j.exists():
        return
    d = json.loads(j.read_text(encoding="utf-8"))
    sc = d["scene"]
    VUES_SCENE[sc] = {k: (tuple(v[0]), tuple(v[1]), v[2]) for k, v in d.get("vues", {}).items()}
    if d.get("dessus"):
        DESSUS_SCENE[sc] = (d["dessus"]["largeur_m"], tuple(d["dessus"]["resolution"]))
    if d.get("resolution"):
        RES_SCENE[sc] = tuple(d["resolution"])
    if d.get("sujet_s") is not None:
        SUJET_SCENE[sc] = d["sujet_s"]
    e = Path(fichier_yaml).with_suffix(".etiquettes.json")
    if e.exists():
        ETIQUETTES_SCENE[sc] = json.loads(e.read_text(encoding="utf-8"))


def _v(x):
    return f"{x:.2f}".replace(".", ",")


def planches_etiquettes(scene, d, PL):
    """Vue de dessus du nuancier en planches annotées à la résolution native (une par moitié de rue)."""
    et = ETIQUETTES_SCENE.get(scene)
    man = json.loads((d / "manifest_rendus.json").read_text(encoding="utf-8"))
    if not et or "dessus" not in man["cameras"]:
        return []
    lab = []
    for e in et["troncons"]:
        if e["rangee"] == "D":
            txt = f"{e['profil']} {_v(e['vue_m'])} + {e['caniveau']}" + chr(10) + f"{e['bordurette']} {_v(e['bordurette_vue_m'])}"
        else:
            txt = f"{e['profil']}" + chr(10) + f"{_v(e['vue_m'])}"
        lab.append({"rangee": e["rangee"], "s0": e["s0"], "s1": e["s1"], "texte": txt})
    L = et["longueur_m"]
    mpp = man["cameras"]["dessus"]["m_par_px"]
    largeur = 1092 * mpp
    out = []
    for k, x0 in enumerate((-2.0, L + 2.0 - largeur)):
        out.append(PL.planche_etiquettes(d / "dessus.png", man["cameras"]["dessus"], lab,
                                         d / f"planche_{scene}_etiquettes_{k + 1}.png", x0, x0 + largeur,
                                         f"{scene} — type de bordure et vue (m) de chaque tronçon, vue de dessus "
                                         f"({mpp * 100:.1f} cm/px), partie {k + 1}/2",
                                         lignes_t={"G": 7.0, "C": 0.0, "D": -8.6}))
    return out


def installer_rendu(vues_demandees):
    import rendu_l2b as RB
    import planches as PL
    origine = RB.rendre_scene
    dessus_origine = RB._dessus

    def rendre_scene(n2, n2b, scene, dossier, parent, vues=None, decor_etape2=False, seulement=None, echantillons=None):
        res0, resd0 = RB.RES, RB.RES_DESSUS
        propres = VUES_SCENE.get(scene, {})
        if scene in SUJET_SCENE:
            RB.SUJET[scene] = SUJET_SCENE[scene]
        if scene in RES_SCENE:
            RB.RES = RES_SCENE[scene]
        larg = None
        if scene in DESSUS_SCENE:
            larg, RB.RES_DESSUS = DESSUS_SCENE[scene]

        def dessus(stage, centre, z, largeur, res):
            return dessus_origine(stage, centre, z, larg or largeur, res)
        RB._dessus = dessus
        try:
            seul = list(vues_demandees) + [k for k in propres if k not in vues_demandees]
            origine(n2, n2b, scene, dossier, parent, vues=propres or None, decor_etape2=decor_etape2, seulement=seul,
                    echantillons=echantillons)
        finally:
            RB.RES, RB.RES_DESSUS, RB._dessus = res0, resd0, dessus_origine
        d = Path(dossier) / "rendus"
        pngs = {p.stem: p for p in d.glob("*.png") if not p.stem.startswith("planche")}
        PL.planche_vues(scene, pngs, [v for v in vues_demandees if v in pngs], d / f"planche_{scene}.png")
        planches_etiquettes(scene, d, PL)
        if propres:
            # planches de détail de 4 vues (2 × 2, ≤ 1092 px) : conducteur puis vues rapprochées
            liste = ["conducteur"] + [k for k in propres if k in pngs]
            for f in d.glob(f"planche_{scene}_detail*.png"):
                f.unlink()
            for j in range(0, len(liste), 4):
                PL.planche_vues(scene, pngs, liste[j:j + 4], d / f"planche_{scene}_detail_{j // 4 + 1}.png",
                                titre=f"vues rapprochées des bordures ({j // 4 + 1}/{(len(liste) + 3) // 4})")
    RB.rendre_scene = rendre_scene


# ---------------------------------------------------------------------------------------------------- pilote
def installer(vues):
    # intégration de l'étape 2 : vocabulaire, schéma, saut de niveau « autre », table étendue de rg::nivellement,
    # pj::bordure::2.1, pj::caniveau::2.2, pièces d'abaissé et assets de elements.json sont dans le code commun
    # (description/, commun/profil.py, hda/rg_nivellement, fabriquer_l2.py) : seuls les rendus du lot restent ici
    installer_rendu(vues)


_installer_pj_origine = F2.installer_pj


def _installer_pj_complet(forcer=False):
    sigs = _installer_pj_origine(forcer)
    sigs.update(installer_pj(forcer))
    return sigs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrees", nargs="+")
    ap.add_argument("--sortie", default=str(SORTIE_DEFAUT))
    ap.add_argument("--rendus", action="store_true")
    ap.add_argument("--vues", default=",".join(VUES_DEFAUT), help="vues standard rendues (défaut : dessus,conducteur)")
    ap.add_argument("--construire-hda", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    a = ap.parse_args()
    vues = [v for v in a.vues.split(",") if v]
    installer(vues)
    for e in a.entrees:
        charger_vues(e)
    signatures = FG.construire_hda(forcer=a.construire_hda, l2=True)
    print("HDA :", ", ".join(f"{k} ({v[:12]})" for k, v in signatures.items()))
    produits = FG.fabriquer(a.entrees, a.sortie, signatures, l2=True, l2b=True, rendus=a.rendus,
                            construire=a.construire_hda)
    if a.verifier_determinisme:
        autre = ICI / "tmp" / "bordures" / "determinisme"
        r = subprocess.run([sys.executable, __file__] + a.entrees + ["--sortie", str(autre)],
                           env=dict(os.environ, RG_PILOTE_ENV=""), capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        if r.returncode:
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("second processus en échec")
        from commun import determinisme as DET
        ecarts, n = DET.comparer(produits, autre, True, True)
        print("déterminisme :", f"identique ({n} fichiers ; .usda : chemins relatifs des matériaux normalisés)"
              if not ecarts else f"DIFFÉRENT : {ecarts}")
        return 1 if ecarts else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
