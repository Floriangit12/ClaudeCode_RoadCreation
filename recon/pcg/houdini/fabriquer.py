"""Fabrication déterministe de la zone pilote v2 (hython Houdini 22.0.459, sans interface).

    hython recon/pcg/houdini/fabriquer.py                       # tout, dans recon/out/paquet_jardin/v2/fabrique
    hython recon/pcg/houdini/fabriquer.py --sortie DOSSIER      # ailleurs (essais, contrôle de déterminisme)
    hython recon/pcg/houdini/fabriquer.py --comparer AUTRE/manifest_fabrication.json

Étapes (pj_*) : pose des bordures et caniveaux (pj_bordure_pose) -> prototypes d'éléments
(pj_bordure_prototypes, verbes SOP) -> bordures.usda + points/bordures.json ; limites de surfaces
régularisées (pj_limites) ; sol (pj_sol, Triangulate 2D) -> sol.usda ; îlots (pj_ilot) -> ilots.usda +
ilots_couverture.usdc + points/ilots_epars.json + zones/ilots.json ; pontages et zébras provisoires
(pj_decals) -> decals_sol.usda + marquages_pilote.usda ; matériaux CC0 (pj_materiaux) ->
materiaux_v2.usda ; masque du v1 et instances v1 réassises (pj_contexte) -> contexte/masque_v1_pilote.usdc ;
caméras (recon/pc/houdini/cameras_v2_pilote.usda), ciel, décor et racine de rendu (pj_rendu) ->
ciel/ciel_clair.hdr, contexte/decor_rendu.usda, rendu_pilote.usda ; manifest_fabrication.json (hashes des
entrées et des sorties, comptes, contrôles mesurés sur la géométrie posée, seuils de la phase 1).
--strict : code de sortie 3 si un contrôle de la phase 1 n'est pas conforme.
Les chemins d'assets écrits dans les USD sont relatifs à l'emplacement canonique (fabrique/), même
quand --sortie écrit ailleurs : deux exécutions donnent des fichiers identiques à l'octet.
"""
import argparse
import hashlib
import math
import json
import os
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.dont_write_bytecode = True

import hou                                                     # noqa: E402
import numpy as np                                             # noqa: E402
from pxr import Usd                                            # noqa: E402

import pj_bordure_pose as PO                                   # noqa: E402
import pj_bordure_prototypes as BP                             # noqa: E402
import pj_commun as K                                          # noqa: E402
import pj_contexte as CX                                       # noqa: E402
import pj_controles as CT                                      # noqa: E402
import pj_decals as DC                                         # noqa: E402
import pj_limites as LI                                        # noqa: E402
import pj_ilot as IL                                           # noqa: E402
import pj_materiaux as M                                       # noqa: E402
import pj_rendu as RD                                          # noqa: E402
import pj_sol as SO                                            # noqa: E402

CAMERAS = K.PC_HOUDINI / "cameras_v2_pilote.usda"
CONTROLE = K.PC_HOUDINI / "rendu_controle.usda"


def journal(*a):
    print(*a, flush=True)


def fichiers_sortie(dossier):
    out = []
    for p in sorted(Path(dossier).rglob("*")):
        if p.is_file() and p.name != "manifest_fabrication.json" and                 not any(x.startswith("_verif") for x in p.relative_to(dossier).parts):
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description="Fabrication v2 de la zone pilote (hython)")
    ap.add_argument("--sortie", default=str(K.FABRIQUE))
    ap.add_argument("--description", default=str(K.DESCRIPTION))
    ap.add_argument("--comparer", help="manifest_fabrication.json d'une autre exécution à comparer")
    ap.add_argument("--sans-cameras", action="store_true", help="n'écrit pas recon/pc/houdini/cameras_v2_pilote.usda")
    ap.add_argument("--strict", action="store_true", help="code de sortie 3 si un contrôle de la phase 1 échoue")
    ap.add_argument("--verifier-determinisme", action="store_true",
                    help="relance la fabrication dans fabrique/_verif_determinisme (autre processus), compare les "
                         "hashes des sorties, écrit le résultat dans le manifeste puis supprime la copie")
    a = ap.parse_args()
    t0 = time.time()
    sortie = Path(a.sortie).resolve()
    if sortie.exists():                                        # pas de sortie périmée dans le manifeste
        import shutil
        for f in sorted(sortie.iterdir()):
            if f.name.startswith("_verif"):
                continue
            shutil.rmtree(f) if f.is_dir() else f.unlink()
    sortie.mkdir(parents=True, exist_ok=True)
    canon = K.FABRIQUE                                         # base des chemins relatifs écrits

    specs = K.Specs()
    desc = K.Description(a.description, specs)
    journal(f"description {desc.hash[:12]} : {len(desc.bordures)} bordures, {len(desc.surfaces)} surfaces, "
            f"{len(desc.ilots)} îlots ; emprise {desc.zone}")

    # ---------------------------------------------------------------- bordures
    journal("pj_bordure_pose")
    po = PO.Poseur(desc, specs)
    elements, joints = po.poser()
    canivx, joints_c = po.caniveaux, po.joints_caniveaux
    PO.choisir_variantes(desc, elements, specs)
    PO.poses(desc, specs, elements, joints, canivx, joints_c)
    dem = PO.demandes(desc, specs, elements, joints, canivx, joints_c)
    journal(f"   {len(elements)} éléments, {len(joints)} joints, {len(canivx)} caniveaux ; {len(dem)} prototypes demandés")
    journal("pj_bordure_prototypes")
    index = BP.fabriquer(specs, dem, sortie / "prototypes", log=journal)
    protos = {n: sortie / d["fichier"] for n, d in index.items()}
    protos_canon = {n: canon / d["fichier"] for n, d in index.items()}
    K.ecrire_json(sortie / "prototypes/index.json", {
        "schema": "pj_prototypes/0.1", "role": "prototypes de bordure (pj_bordure_prototypes.py)",
        "repere": "X = s, Y = u (0 = face vue, + vers l'arrière), Z = v (0 = dessous du bloc) ; pivot au milieu, "
                  "sur la face vue, sous le bloc (chartières : sous le bloc du profil courant) ; mètres, Z haut ; "
                  "UE : X = 100 s, Y = −100 u, Z = 100 v",
        "prototypes": index})
    pts_b = PO.points_json(desc, elements, joints, canivx, joints_c)
    K.ecrire_points(sortie / "points/bordures.json", "bordures", pts_b, desc.hash, {
        "repere": "local (L93 − O, z = NGF − 216,30), m, Z haut",
        "convention_rpy": "rpy_deg = [r, p, y] ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r), rotations directes (p > 0 "
                          "abaisse l'avant +X ; y trigo depuis +x) : convention de recon/pcg/ue/pj_tools/pj_tools/repere.py ; "
                          "UE : Rotator(roll = r, pitch = −p, yaw = −y)",
        "pivot": "milieu de l'élément, face vue, dessous du bloc (prototypes/index.json)",
        "cd": "éléments et caniveaux : [usure (épaufrures), salissure, mousse_joints, herbe_joints, teinte] "
              "(x.couleur : gain RVB de dérive de teinte) ; joints : [] (x.mortier : sombre en retrait | clair à fleur ; "
              "s[0] = largeur du joint / 6 mm, à 4 mm près)",
        "bibliotheque": "asset = nom de prototype (prototypes/<asset>.usda, UE /Game/PJ/Lib/Bordures/SM_<asset>)"})
    # pose : écrit avec les chemins canoniques
    PO.ecrire_usd(elements, joints, protos_canon, sortie / "bordures.usda", canon / "bordures.usda", canivx, joints_c)

    # ---------------------------------------------------------------- sol
    journal("pj_limites")
    ctl_lim = LI.regulariser(desc)
    journal(f"   {ctl_lim['arcs']} arcs, {ctl_lim['sommets_avant']} -> {ctl_lim['sommets_apres']} sommets, "
            f"écart max {ctl_lim['ecart_max_m']} m")
    journal("pj_sol")
    sol = SO.Sol(desc, specs, log=journal)
    ctl_sol = sol.fabriquer(sortie / "sol.usda")
    ctl_sol["limites"] = ctl_lim
    ctl_sol["massifs_decaisses_sommets"] = getattr(sol, "n_decaisses", 0)

    # ---------------------------------------------------------------- îlots
    journal("pj_ilot")
    se = IL.Semis(desc, specs, sol, log=journal, elements=elements)
    pts_i = se.semer()
    pe = se.prototypes(sortie / "prototypes", canon)
    pe_canon = {n: (canon / "prototypes/eclats" / f"{n}.usda", m) for n, (f, m) in pe.items()}
    se.ecrire_usd(sortie / "ilots.usda", pe_canon, canon / "ilots.usda", sortie / "ilots_couverture.usdc",
                  canon / "ilots_couverture.usdc")
    K.ecrire_points(sortie / "points/ilots_epars.json", "ilots_epars",
                    [{k: v for k, v in p.items() if not k.startswith("_")} for p in pts_i], desc.hash,
                    {"repere": "local, m, Z haut", "cd": "[teinte, gain R, gain V, gain B]",
                     "asset": "prototypes/eclats/<asset>.usda (taille unitaire, origine au centre, s = taille en m)",
                     "perimetre": "éclats épars (débordement sur la chaussée, tête de bordure) ; la couverture dense "
                                  "des remplissages est dans ilots_couverture.usdc (UE : PG_Ilots depuis zones/ilots.json)"})

    # ---------------------------------------------------------------- pontages, zébras
    journal("pj_decals")
    ctl_dec = DC.Decals(desc, sol, log=journal).ecrire(sortie / "decals_sol.usda", sortie / "marquages_pilote.usda",
                                                       elements=elements, joints=joints)
    journal(f"   pontages {ctl_dec['pontages']['longueur_fissures_m']} m + reprise {ctl_dec['pontages']['joint_reprise_neuf_ancien_m']} m ; "
            f"{ctl_dec['zebras']['bandes']} bandes de zébra")
    K.ecrire_json(sortie / "zones/ilots.json", {"schema": "pj_zones/0.1", "famille": "ilots", "source_hash": desc.hash,
                                                "zones": se.zones()})

    # ---------------------------------------------------------------- matériaux
    journal("pj_materiaux")
    ids = set(ctl_sol["maillages"]) | {"beton_bordure_gris", "beton_bordure_clair", "mortier_joint", "mortier_clair",
                                       "bitume_pontage", "peinture_blanche", "herbe_touffe", "bev_podotactile"}
    if canivx:
        ids.add("caniveau_beton")
    eclats = {cfg["materiau"]: cfg["source"] for cfg in IL.ECLATS.values()}
    faits = M.ecrire(specs, ids, sortie / "materiaux_v2.usda", eclats=eclats, ref=canon / "materiaux_v2.usda")
    journal(f"   {len(faits)} matériaux")

    # ---------------------------------------------------------------- contexte v1
    journal("pj_contexte")
    v1 = Usd.Stage.Open(str(K.PAQUET_V1 / "paquet_jardin_2026.usda"))
    masque = CX.masquer(v1, desc.zone, sol, sortie / "contexte/masque_v1_pilote.usdc", log=journal)
    masque["reassis_controle"] = _ctl_mobilier(v1, sortie / "contexte/masque_v1_pilote.usdc", desc.zone, sol)

    # ---------------------------------------------------------------- caméras et racine
    journal("pj_rendu")
    cams = None
    if not a.sans_cameras:
        cams = RD.ecrire_cameras(desc, sol, CAMERAS)
    ciel = RD.ecrire_ciel(sortie / "ciel/ciel_clair.hdr")
    decor = RD.ecrire_decor(v1, desc.zone, sortie / "contexte/decor_rendu.usda", ref=canon / "contexte/decor_rendu.usda")
    couches = [canon / n for n in ("ilots_couverture.usdc", "ilots.usda", "marquages_pilote.usda", "decals_sol.usda",
                                   "bordures.usda", "sol.usda", "materiaux_v2.usda", "contexte/masque_v1_pilote.usdc",
                                   "contexte/decor_rendu.usda")]
    RD.ecrire_racine(sortie / "rendu_pilote.usda", CAMERAS, couches, CONTROLE, ref=canon / "rendu_pilote.usda",
                     ciel=canon / "ciel/ciel_clair.hdr")

    # ---------------------------------------------------------------- comptes et manifeste
    comptes = _comptes(elements, joints, pts_i, index)
    cv = {}
    for _, fam, lot in se.couverture:
        cv[fam] = cv.get(fam, 0) + int(len(lot["taille"]))
    comptes["eclats_couverture"] = dict(sorted(cv.items()))
    comptes["caniveaux"] = len(canivx)
    entrees = {K.rel(f): K.sha256(f) for f in desc.fichiers() + specs.fichiers +
               [K.fichier_mnt(), K.C.DONNEES / "relief/heightmap_3025_10cm.json",
                K.PAQUET_V1 / "paquet_jardin_2026.usda"] + sorted((K.PAQUET_V1 / "layers").glob("*"))}
    scripts = {f.name: K.sha256(f) for f in sorted(ICI.glob("*.py"))}
    sorties = {f.relative_to(sortie).as_posix(): K.sha256(f) for f in fichiers_sortie(sortie)}
    man = {"schema": "pj_manifest_fabrication/0.1", "version_regles": K.VERSION,
           "houdini": hou.applicationVersionString(), "licence": str(hou.licenseCategory()).split(".")[-1],
           "usd": Usd.GetVersion(), "description": {"hash": desc.hash, "dossier": K.rel(desc.dossier)},
           "zone": desc.zone, "entrees": entrees, "scripts": scripts,
           "comptes": comptes, "controles": {"sol": ctl_sol, "bordures": _ctl_bordures(desc, specs, elements, joints, sol),
                                             "pose_reelle": _ctl_pose(desc, specs, elements, joints, sol, index),
                                             "conformite": _ctl_conformite(desc, specs, sol, elements, canivx),
                                             "decals": ctl_dec, "masque_v1": masque, "rendu": {"ciel": ciel, "decor": decor}},
           "cameras": cams, "sorties": sorties,
           "hash_sorties": hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(sorties.items())).encode()).hexdigest()}
    man["phase1"] = _phase1(man["controles"])
    K.ecrire_json(sortie / "manifest_fabrication.json", man)
    for x in INTERSTICES:
        journal("   interstice arrière > 5 mm :", x)
    for k, v in man["phase1"].items():
        journal(f"   phase 1 {k} : {'conforme' if v['conforme'] else 'NON CONFORME'} ({v['mesure']})")
    journal(f"fabrication terminée en {time.time() - t0:.0f} s ; hash des sorties {man['hash_sorties'][:16]}")
    if a.verifier_determinisme:
        import shutil
        import subprocess
        verif = sortie / "_verif_determinisme"
        t1 = time.time()
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--sortie", str(verif), "--description",
                            a.description, "--sans-cameras", "--comparer", str(sortie / "manifest_fabrication.json")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        autre = K.lire_json(verif / "manifest_fabrication.json")
        diff = sorted(k for k in set(sorties) | set(autre["sorties"]) if sorties.get(k) != autre["sorties"].get(k))
        man["determinisme"] = {"methode": "deuxième exécution complète dans un autre processus hython, même description "
                                          "et mêmes specs ; comparaison sha256 fichier par fichier",
                               "fichiers_compares": len(sorties), "differences": diff,
                               "identique_a_l_octet": not diff and r.returncode == 0,
                               "hash_sorties_execution_2": autre["hash_sorties"], "duree_s": round(time.time() - t1)}
        K.ecrire_json(sortie / "manifest_fabrication.json", man)
        shutil.rmtree(verif, ignore_errors=True)
        journal(f"déterminisme : {len(sorties)} fichiers comparés, {len(diff)} différence(s)")
    if a.comparer:
        autre = K.lire_json(a.comparer)
        diff = sorted(k for k in set(sorties) | set(autre["sorties"]) if sorties.get(k) != autre["sorties"].get(k))
        journal(f"comparaison avec {a.comparer} : {len(sorties)} fichiers, {len(diff)} différences")
        for k in diff[:20]:
            journal("   ≠", k)
        sys.exit(1 if diff else 0)
    if a.strict and not all(v["conforme"] for v in man["phase1"].values()):
        sys.exit(3)


def _ctl_conformite(desc, specs, sol, elements, caniveaux):
    """Contrôles de pj_controles sur la géométrie posée (sol = maillage fabriqué)."""
    loc = getattr(sol, "_loc", None) or DC.Localisateur(sol.P3, sol.T)
    return {"fidelite": CT.fidelite(desc, specs, elements),
            "interstices_denses": CT.interstices_denses(desc, specs, sol, elements, caniveaux, loc),
            "rampes_marchables": CT.rampes_marchables(desc, specs, sol, elements, loc),
            "faces_arriere": CT.faces_arriere(desc, specs, sol, elements, loc),
            "remplissages": CT.remplissages(desc, specs, sol, elements, loc),
            "vues_traversees": CT.vues_traversees(desc, specs, elements, loc)}


def _bouts(e, specs, index, desc):
    """Abouts d'un élément posé : pour le début et la fin, 4 coins de la face d'about (pied et haut de la
    face vue, haut et pied de l'arrière, à 5 mm des arêtes) et normale d'about (+s), transformés par la
    pose réelle (pivot, rpy, échelle X). Pièces courbes : chemin de la face, abouts radiaux ou en onglet
    (biais) ; chartières : hauteur de chaque extrémité."""
    R = K.rotation_rpy(e["rpy"])
    p = np.asarray(e["p"])
    sx = e["s"][0]
    c = specs.contour(e["profil"])
    base, H = specs.dims(e["profil"])
    i_top = int(np.argmax(c[:, 1] >= H - 1e-9))
    u_haut = float(c[i_top, 0])
    if e["type"] == "chartiere":
        bas = H - (max(e["vue"], e["vue_fin"]) - min(e["vue"], e["vue_fin"]))
        h0, h1 = (H, bas) if e["sens"] == "desc" else (bas, H)
        base = min(base, specs.dims(e["profil_bas"])[0])
    else:
        h0 = h1 = H
    uv = lambda h: [(0.005, 0.04), (u_haut + 0.005, h - 0.005), (base - 0.005, h - 0.005), (base - 0.005, 0.04)]
    if PO.sur_mesure(e):
        ch = PO.chemin_courbe(desc.par_id[e["bordure"]], e) * [sx, 1.0]
        out = []
        for k, sg, b, h in ((0, 1.0, e.get("biais_debut", 0.0), h0), (-1, -1.0, e.get("biais_fin", 0.0), h1)):
            d = ch[1] - ch[0] if k == 0 else ch[-1] - ch[-2]
            t = d / max(np.hypot(*d), 1e-12)
            nl = np.array([-t[1], t[0]])
            nrm = t * math.cos(b) + nl * math.sin(b) * (-sg)
            loc = np.array([[*(ch[k] + nl * u + sg * t * u * math.tan(b)), v] for u, v in uv(h)])
            out.append((p + (R @ loc.T).T, R @ np.r_[nrm, 0.0]))
        return out
    Lp = float(index[e["asset"]]["longueur"]) * sx
    out = []
    for x, h in ((-Lp / 2, h0), (Lp / 2, h1)):
        loc = np.array([[x, u, v] for u, v in uv(h)])
        out.append((p + (R @ loc.T).T, R @ np.array([1.0, 0.0, 0.0])))
    return out


def _stat(a, nd=4):
    a = np.asarray(a, dtype=float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "min": round(float(a.min()), nd), "p5": round(float(np.percentile(a, 5)), nd),
            "mediane": round(float(np.median(a)), nd), "p95": round(float(np.percentile(a, 95)), nd),
            "max": round(float(a.max()), nd)}


def _ctl_pose(desc, specs, elements, joints, sol, index):
    """Contrôles sur la géométrie POSÉE (revue conformité r1 : les contrôles de planification donnaient de
    faux « conformes ») :
    - joints réels entre abouts transformés d'éléments consécutifs (pied de face) et marche de tête ;
    - tête − sol devant (6 cm devant la face) et derrière (3 cm derrière la base), sol = maillage fabriqué ;
    - recouvrement de bandes de bordures (doublons) ;
    - mobilier v1 : base − sol v2 dans l'emprise."""
    loc = DC.Localisateur(sol.P3, sol.T)
    par_b = {}
    for e in elements:
        par_b.setdefault(e["bordure"], []).append(e)
    jts, jts_max, marches, details_j, details_m = [], [], [], [], []
    angles = 0
    for bid in sorted(par_b):
        els = sorted(par_b[bid], key=lambda e: e["index"])
        for e0, e1 in zip(els[:-1], els[1:]):
            if e1["s0"] - e0["s1"] > 0.02:
                continue
            (_, _), (c0, n0) = _bouts(e0, specs, index, desc)
            (c1, n1), (_, _) = _bouts(e1, specs, index, desc)
            if abs(e0.get("biais_fin", 0.0)) > 0.1:            # about en onglet (> 6°) : angle vif ou coude
                angles += 1
            # écart aux 4 coins (revue conformité r2 : le pied de face seul cachait les joints en coin) :
            # coins de l'about de e0 au plan d'about de e1, et inversement
            g8 = np.r_[(c1[0] - c0) @ n1, (c1 - c0[0]) @ n0]
            gmin, gmax = float(g8.min()), float(g8.max())
            B = desc.par_id[bid]
            m = float(c1[2, 2] - c0[2, 2] - (B.z_fe(e1["s0"]) - B.z_fe(e0["s1"])))
            jts.append(gmin)
            jts_max.append(gmax)
            marches.append(abs(m))
            if gmin < 0.003 or gmax > 0.010:
                details_j.append([e0["id"], round(gmin * 1000, 1), round(gmax * 1000, 1)])
            if abs(m) > 0.010:
                details_m.append([e0["id"], e1["id"], round(m * 1000, 1)])
    # tête − sol de part et d'autre
    av, ar, enterres, dessous = [], [], [], []
    massifs = {}
    for e in elements:
        if e["type"] == "courbe":
            continue
        B = desc.par_id[e["bordure"]]
        base, H = specs.dims(e["profil"])
        for s in np.linspace(e["s0"] + 0.1 * e["longueur"], e["s1"] - 0.1 * e["longueur"], 3):
            q, tg = B.point(s)
            q, n = q[0], np.array([-tg[0, 1], tg[0, 0]])
            tete = float(B.z_fe(s) + B.vue(s)[0]) + e["jitter"]["dz"]
            uf = float(sol.bandes[B.id].interp(sol.bandes[B.id].uf, s))
            _, zr = loc.trouver((q + n * min(-0.06, uf - 0.04))[None])
            tb, zb = loc.trouver((q + n * (base + 0.03))[None])
            if tb[0] >= 0 and sol.cl[tb[0]] in SO.DECAISSE and not sol.ilot_tri[tb[0]]:
                massifs.setdefault(sol.cl[tb[0]], []).append(tete - zb[0])
            if np.isfinite(zr[0]):
                av.append(tete - zr[0])
                if tete - zr[0] < -0.005:
                    enterres.append([e["id"], round((tete - zr[0]) * 1000, 1)])
            if np.isfinite(zb[0]):
                ar.append(tete - zb[0])
                if tete - zb[0] < -0.005:
                    dessous.append([e["id"], round((tete - zb[0]) * 1000, 1)])
    # recouvrement de bandes (doublons)
    recouv = []
    for B in desc.bordures:
        s = np.arange(0.1, B.L - 0.1, 0.25)
        if len(s) == 0:
            continue
        q, tg = B.point(s)
        mid = q + np.c_[-tg[:, 1], tg[:, 0]] * 0.04
        for B2 in desc.bordures:
            if B2.id == B.id:
                continue
            b2 = sol.bandes[B2.id]
            lo, hi = b2.bbox
            m = (mid[:, 0] > lo[0]) & (mid[:, 0] < hi[0]) & (mid[:, 1] > lo[1]) & (mid[:, 1] < hi[1])
            if not m.any():
                continue
            s2, dl, d, ex = b2.projeter(mid[m])
            dedans = (ex <= 0) & (dl > b2.interp(b2.uf, s2) + 0.01) & (dl < b2.interp(b2.ub, s2) - 0.01)
            if dedans.sum() >= 2:
                recouv.append([B.id, B2.id, round(0.25 * float(dedans.sum()), 2)])
    jts = np.array(jts)
    # pas alternés 1,0 / 0,5 / 1,0 dans une même file (revue r1 : K-0385 E008-E017)
    alt = 0
    for bid in sorted(par_b):
        els = sorted(par_b[bid], key=lambda e: e["index"])
        L = [round(e["longueur"], 1) for e in els]
        alt += sum(1 for a, b, c in zip(L, L[1:], L[2:]) if a >= 0.9 and b <= 0.6 and c >= 0.9)
    # longueur posée / décrite des anneaux d'îlots (pointes conservées)
    anneaux = {}
    for il in desc.ilots:
        for bid in il["p"].get("ceinture", []):
            B = desc.par_id.get(bid)
            if B is not None:
                anneaux[bid] = {"decrit_m": round(float(B.p["longueur_m"]), 2),
                                "pose_m": round(float(sum(e["longueur"] + e["joint"] for e in par_b.get(bid, []))), 2)}
    return {"methode": "abouts (4 coins par face d'about) et têtes des prototypes transformés par la pose réelle ; "
                       "sol = maillage sol.usda ; joint_reel_mm = écart minimal aux 4 coins, joint_reel_max_coins_mm = maximal",
            "triplets_pas_alternes_1_05_1": alt, "ceintures_ilots_longueurs": anneaux,
            "retrait_massifs_derriere_bordure_m": {k: _stat(v) for k, v in sorted(massifs.items())},
            "joint_reel_mm": _stat(jts * 1000, 2), "joint_reel_max_coins_mm": _stat(np.array(jts_max) * 1000, 2),
            "joints_hors_3_10_mm": details_j[:40], "angles_vifs_onglet": angles,
            "n_joints_hors_3_10_mm": len(details_j),
            "marche_tete_mm": _stat(np.array(marches) * 1000, 2), "marches_sup_10_mm": details_m[:40],
            "n_marches_sup_10_mm": len(details_m),
            "tete_moins_sol_devant_m": _stat(av), "elements_enterres": enterres[:40], "n_elements_enterres": len(enterres),
            "tete_moins_sol_derriere_m": _stat(ar), "sol_au_dessus_de_la_tete": dessous[:40],
            "n_sol_au_dessus_de_la_tete": len(dessous), "recouvrements_de_bandes": recouv}


def _ctl_mobilier(v1, couche, R, sol):
    """Instances v1 posées au sol (mobilier, végétation) de l'emprise : base − appui v2 (max du sol et des
    têtes de bordure sous l'empreinte, pj_contexte.z_appui), après réassise ; les instances portées en
    hauteur (têtes de feux, panneaux) sont exclues. Flottante ou enterrée : |écart| > 2 cm."""
    from pxr import Sdf, UsdGeom
    st = Usd.Stage.Open(Sdf.Layer.FindOrOpen(str(couche)))
    ec, cas = [], []
    for racine in ("/World/Mobilier", "/World/Vegetation"):
        rp = v1.GetPrimAtPath(racine)
        if not rp:
            continue
        for p in sorted(rp.GetChildren(), key=lambda q: q.GetName()):
            if not p.IsA(UsdGeom.PointInstancer):
                continue
            o = st.GetPrimAtPath(p.GetPath())
            src = UsdGeom.PointInstancer(o) if o and UsdGeom.PointInstancer(o).GetPositionsAttr().HasAuthoredValue() \
                else UsdGeom.PointInstancer(p)
            P = np.array(src.GetPositionsAttr().Get(), dtype=np.float64)
            P0 = np.array(UsdGeom.PointInstancer(p).GetPositionsAttr().Get(), dtype=np.float64)
            pose_au_sol = (P0[:, 2] - K.mnt_local(P0[:, 0], P0[:, 1])) < 0.3     # têtes de feux, panneaux : en hauteur
            m = np.where((P[:, 0] > R[0]) & (P[:, 0] < R[2]) & (P[:, 1] > R[1]) & (P[:, 1] < R[3]) & pose_au_sol)[0]
            if not len(m):
                continue
            z = CX.z_appui(sol, P[m, :2])
            for k, i in enumerate(m):
                d = float(P[i, 2] - z[k])
                ec.append(d)
                if abs(d) > 0.02:
                    cas.append([p.GetName(), int(i), K.r3(P[i], 2), round(d * 1000, 1)])
    return {"base_moins_appui_v2_m": _stat(ec), "instances": len(ec), "n_sup_2cm": len(cas), "cas_sup_2cm": cas[:20]}


def _phase1(ctl):
    """Critères chiffrés de la phase 1 (architecture_v2 §2), mesurés sur la géométrie posée, chacun avec son
    seuil d'origine (revue conformité r2)."""
    pr, so, cf = ctl["pose_reelle"], ctl["sol"], ctl["conformite"]
    out = {}
    j, jm = pr["joint_reel_mm"], pr["joint_reel_max_coins_mm"]
    out["joints_3_10_mm"] = {"conforme": pr["n_joints_hors_3_10_mm"] == 0,
                             "mesure": f"4 coins de chaque about : min {j['min']} mm, max {jm['max']} mm (médianes {j['mediane']} / "
                                       f"{jm['mediane']}), {pr['n_joints_hors_3_10_mm']} joint(s) hors 3-10 mm sur {j['n']}"}
    out["marches_tete"] = {"conforme": pr["n_marches_sup_10_mm"] == 0,
                           "mesure": f"{pr['n_marches_sup_10_mm']} marche(s) de tête > 10 mm"}
    out["enterres"] = {"conforme": pr["n_elements_enterres"] == 0 and pr["n_sol_au_dessus_de_la_tete"] == 0,
                       "mesure": f"{pr['n_elements_enterres']} tranche(s) avec la chaussée au-dessus de la tête, "
                                 f"{pr['n_sol_au_dessus_de_la_tete']} avec le sol arrière au-dessus"}
    v = cf["vues_traversees"]
    out["vue_traversees"] = {"conforme": not v["hors_0_02_pm_0_005"],
                             "mesure": f"vue réelle {v['vue_reelle_m']['min']}-{v['vue_reelle_m']['max']} m (médiane "
                                       f"{v['vue_reelle_m']['mediane']}) ; hors 0,02 ± 0,005 : {len(v['hors_0_02_pm_0_005'])} élément(s)"}
    rp = cf["rampes_marchables"]["abaisses"]
    p95 = {k: r["pente_p95_pct"] for k, r in rp.items() if r["pente_p95_pct"] is not None}
    pmax = max(p95.values() or [0])
    out["rampes_5pct"] = {"conforme": pmax <= 5.0, "mesure": f"p95 sur profils marchables : max {pmax} % ; > 5 % : "
                                                          f"{sorted((k, v_) for k, v_ in p95.items() if v_ > 5.0)}"}
    it = cf["interstices_denses"]
    out["interstices_5mm"] = {"conforme": it["points_trou_avant"] == 0 and it["points_trou_arriere"] == 0,
                              "mesure": f"sondes tous les 2 cm : {it['points_trou_avant']} trou(s) devant, "
                                        f"{it['points_trou_arriere']} derrière"}
    rem = cf["remplissages"]
    out["remplissages_3_5cm"] = {"conforme": all(r["n_hors_3_5cm"] == 0 for r in rem.values()),
                                 "mesure": "; ".join(f"{k} {r['retrait_m']['mediane'] if r['retrait_m'] else '-'} m, "
                                                     f"{r['n_hors_3_5cm']}/{r['n_sondes']} hors 3-5 cm" for k, r in sorted(rem.items()))}
    out["doublons"] = {"conforme": not pr["recouvrements_de_bandes"],
                       "mesure": f"{len(pr['recouvrements_de_bandes'])} recouvrement(s) de bandes"}
    fi = cf["fidelite"]
    out["z_fil_eau_1cm"] = {"conforme": fi["n_ecart_z_sup_1cm"] == 0,
                            "mesure": f"fil d'eau posé − décrit {fi['fil_eau_pose_moins_decrit_m']['min']} à "
                                      f"{fi['fil_eau_pose_moins_decrit_m']['max']} m ; {fi['n_ecart_z_sup_1cm']} élément(s) > 1 cm"}
    ep = fi["ecart_plan_m"]
    out["plan_2cm_p95_5cm_max"] = {"conforme": ep["p95"] <= 0.02 and ep["max"] <= 0.05,
                                   "mesure": f"écart en plan face posée − levé : p95 {ep['p95']} m, max {ep['max']} m (nez exclus)"}
    mo = ctl["masque_v1"]["reassis_controle"]
    out["mobilier_2cm"] = {"conforme": mo["n_sup_2cm"] == 0,
                           "mesure": f"{mo['n_sup_2cm']} instance(s) v1 posée(s) au sol à plus de 2 cm de leur appui v2"}
    fa = cf["faces_arriere"]
    out["faces_arriere_3cm"] = {"conforme": fa["n_sup_3cm"] == 0,
                                "mesure": f"{fa['n_sup_3cm']} élément(s) avec plus de 3 cm de face arrière à nu"}
    return out


def _comptes(elements, joints, pts_i, index):
    par = {}
    for e in elements:
        k = f"{e['profil']}/{e['type']}" + ("/coupe" if e["coupe"] else "")
        par[k] = par.get(k, 0) + 1
    lon = {}
    for e in elements:
        lon[e["profil"]] = lon.get(e["profil"], 0.0) + e["longueur"]
    eclats = {}
    for p in pts_i:
        k = p["asset"].rsplit("_v", 1)[0]
        eclats[k] = eclats.get(k, 0) + 1
    return {"elements": len(elements), "joints": len(joints), "elements_par_profil_type": dict(sorted(par.items())),
            "longueur_elements_par_profil_m": {k: round(v, 2) for k, v in sorted(lon.items())},
            "variantes": {f"v{v}": sum(1 for e in elements if e.get("variante", 0) == v) for v in range(4)},
            "prototypes": len(index), "prototypes_courbes": sum(1 for n in index if n.startswith("courbe_")),
            "eclats_epars": dict(sorted(eclats.items()))}


INTERSTICES = []


def _ctl_bordures(desc, specs, elements, joints, sol):
    """Contrôles mesurés sur la géométrie posée : joints, coupes, flèches ; interstices sol / élément
    (face avant au niveau de la chaussée et face arrière sous la tête, 7 points par élément, transformés
    par la pose réelle, comparés aux bords du sol) ; vue réelle des bateaux de traversée (tête de
    l'élément − sol 5 cm devant la face)."""
    jo = np.array([j["ecart"] for j in joints]) if joints else np.zeros(1)
    coupes = [e["longueur"] for e in elements if e["coupe"]]
    fl = [e["fleche_mm"] for e in elements if e["type"] not in ("courbe",)]
    gav, gar, vues = [], [], []
    par_b = {}
    for e in elements:
        par_b.setdefault(e["bordure"], []).append(e["index"])
    for e in elements:
        if PO.sur_mesure(e):
            continue
        B = desc.par_id[e["bordure"]]
        if B.ferme and e["index"] in (min(par_b[B.id]), max(par_b[B.id])):
            continue                            # anneau : projection ambiguë à la fermeture
        b = sol.bandes[e["bordure"]]
        prof = e["profil"]
        base, H = specs.dims(prof)
        vue = max(e["vue"], e.get("vue_fin", e["vue"]))
        ur = SO.u_route(specs, prof, vue)
        Lx = e["longueur"] * 0.5 * 0.96
        xs = np.linspace(-Lx, Lx, 7)
        R = K.rotation_rpy(e["rpy"])
        sx = e["s"][0]
        av = np.c_[xs / sx * sx, np.full(7, ur), np.full(7, H - vue)]
        ar = np.c_[xs, np.full(7, base), np.full(7, H - 0.01)]
        Wav = e["p"] + (R @ (av * [sx, 1, 1]).T).T
        War = e["p"] + (R @ (ar * [sx, 1, 1]).T).T
        if e["type"] == "chartiere":            # face avant : profil courant à l'extrémité haute seulement
            Wav = Wav[:2] if e["sens"] == "desc" else Wav[-2:]
        s, dl, d, ex = b.projeter(Wav[:, :2])
        if B.caniveau_a(0.5 * (e["s0"] + e["s1"])) is None:      # devant un caniveau : la face s'appuie sur lui
            gav += list(np.maximum(dl - b.interp(b.uf, s), 0.0) * (ex <= 0))
        s, dl, d, ex = b.projeter(War[:, :2])
        g = np.maximum(b.interp(b.ub, s) - dl, 0.0) * (ex <= 0)
        g[(s < e["s0"] - 0.5) | (s > e["s1"] + 0.5)] = 0.0   # anneau : dos à dos avec l'autre côté de la pointe
        for bid2, m2, s2, dl2, d2, ex2 in sol.projections(War[:, :2], rayon=0.5):
            if bid2 == e["bordure"]:
                continue
            b2 = sol.bandes[bid2]
            dans = (ex2 <= 0) & (dl2 > b2.interp(b2.uf, s2)) & (dl2 < b2.interp(b2.ub, s2) + 0.012)
            g[m2[dans]] = 0.0                   # dos à dos (pointe d'îlot) : couvert par l'autre bordure
        gar += list(g)
        if g.max() > 0.005:
            INTERSTICES.append((e["id"], e["type"], round(float(g.max()) * 1000, 1)))
        if e["type"] == "bateau" and e["vue"] <= 0.03:
            haut = e["p"] + R @ np.array([0.0, 0.04, H])
            devant = e["p"][:2] + (R @ np.array([0.0, -0.05, 0.0]))[:2]
            vues.append(float(haut[2] - sol.z_points(devant[None])[0]))
    gav, gar = np.array(gav) * 1000, np.array(gar) * 1000
    return {"joint_mm": {"min": round(float(jo.min()) * 1000, 2), "max": round(float(jo.max()) * 1000, 2),
                         "median": round(float(np.median(jo)) * 1000, 2)},
            "coupes": {"n": len(coupes), "min_m": round(min(coupes), 3) if coupes else None},
            "fleche_elements_droits_mm": {"max": max(fl) if fl else None, "p95": round(float(np.percentile(fl, 95)), 2) if fl else None},
            "recouvrement_sol_sous_bordure_mm": SO.MARGE * 1000,
            "interstice_face_avant_mm": {"max": round(float(gav.max()), 2), "p99": round(float(np.percentile(gav, 99)), 2),
                                         "points_sup_5mm": int((gav > 5).sum()), "points": int(len(gav))},
            "interstice_face_arriere_mm": {"max": round(float(gar.max()), 2), "p99": round(float(np.percentile(gar, 99)), 2),
                                           "points_sup_5mm": int((gar > 5).sum()), "points": int(len(gar)),
                                           "elements_sup_5mm": [list(x) for x in INTERSTICES[:20]]},
            "vue_bateaux_traversee_m": {"n": len(vues), "min": round(min(vues), 4) if vues else None,
                                        "max": round(max(vues), 4) if vues else None,
                                        "mediane": round(float(np.median(vues)), 4) if vues else None}}


if __name__ == "__main__":
    main()
