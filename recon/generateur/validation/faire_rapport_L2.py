# -*- coding: utf-8 -*-
"""Rapport du lot L2 (nivellement, sol, bordures, caniveaux) : rejoue tout et écrit rapport_L2.json.

    python recon/generateur/validation/faire_rapport_L2.py [--sans-rendus] [--sans-fabrication]

Étapes (aucune date ni durée écrite : deux exécutions donnent le même rapport) :
1. HDA rg::nivellement, rg::sol, rg::vers_entites (--construire-hda --l2) et pj::caniveau::2.0 (nouvelle version,
   hda/pj_caniveau_v2, hda/pj_bordure_v2) construites deux fois : signatures et empreintes des dossiers développés
   identiques ;
   pj::bordure::1.0 et pj::caniveau::1.0 du dépôt réutilisées sans modification (empreintes relevées) ;
2. fabrication de S01-S12 avec --l2 --rendus --verifier-determinisme (second processus : fichiers l1/ et l2/ comparés
   à l'octet) ; --sans-fabrication relit les sorties déjà produites (le déterminisme n'est alors pas rejoué) ;
3. contrôles indépendants (controler_L2.py : Python hors Houdini, modèle analytique analytique_L2.py) ;
4. témoins négatifs : chaque témoin écrit une sortie fausse (copie sous tmp/l2/temoins) que le contrôle doit refuser ;
5. revue visuelle : tuiles natives des rendus Karma XPU (rendus/tuiles/<vue>/) ; constats relus dans
   constats_visuels_L2.json ;
6. critères du lot L2 (PLAN_GENERATEUR § 3) et contrôles TQ-SOL-* / TQ-BOR-* applicables à Houdini.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
TMP = GEN / "tmp" / "l2"
HYTHON = os.environ.get("HYTHON", "C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
PILOTE = GEN / "fabriquer_generateur.py"
sys.path.insert(0, str(ICI))
import controler_L2 as C  # noqa: E402
import controler_correction as CC  # noqa: E402

SCENES = sorted((GEN / "scenes_simples").glob("S*.yaml"))
HDA_L2 = ("rg_nivellement/rg_nivellement.hdalc", "rg_sol/rg_sol.hdalc", "rg_vers_entites/rg_vers_entites.hdalc",
          "pj_caniveau_v2/pj_caniveau_2.0.hdalc", "pj_bordure_v2/pj_bordure_2.0.hdalc",
          "pj_caniveau_v2_1/pj_caniveau_2.1.hdalc")
PJ_DEPOT = DEPOT / "recon" / "pcg" / "houdini" / "hda"


def rel(p):
    return str(Path(p).resolve().relative_to(DEPOT)).replace("\\", "/")


def lancer(cmd, **kw):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", HOUDINI_VEX_DISABLE_JIT="1")
    for k in ("TEMP", "TMP", "HOUDINI_TEMP_DIR"):                  # temporaires de hython sur D:
        env[k] = str(GEN / "tmp" / "hython")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(DEPOT), env=env, **kw)
    return r.returncode, r.stdout, r.stderr


def empreinte(dossiers):
    h = hashlib.sha256()
    for d in dossiers:
        for f in sorted(Path(d).glob("**/*")):
            if f.is_file():
                h.update(rel(f).encode())
                h.update(f.read_bytes())
    return h.hexdigest()


def signatures(sortie):
    lig = [x for x in sortie.splitlines() if x.startswith("HDA :")]
    return lig[-1][6:].strip() if lig else ""


# ------------------------------------------------------------------------------------------------ témoins négatifs
def _copie(scene, nom):
    d = TMP / "temoins" / nom / scene
    shutil.rmtree(d, ignore_errors=True)
    (d / "l2").mkdir(parents=True)
    shutil.copy2(OUT / scene / "modele_voie.json", d / "modele_voie.json")
    for f in (OUT / scene / "l2").iterdir():
        if f.is_file() and f.suffix in (".npy", ".json"):
            shutil.copy2(f, d / "l2" / f.name)
    return d


def _faces(d):
    F = np.load(d / "l2" / "sol_faces.npy")
    N = np.load(d / "l2" / "sol_comptes.npy")
    A = np.load(d / "l2" / "sol_attributs.npy")
    voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    off = np.concatenate([[0], np.cumsum(N)])
    return F, N, A, voc, off


def temoins():
    """Chaque témoin fabrique une sortie fausse ; le contrôle indépendant doit la refuser."""
    out = []
    # 1. une face visible de chaussée retirée du sol de S02 (trou intérieur)
    d = _copie("S02", "trou")
    F, N, A, voc, off = _faces(d)
    ch = voc["classe"].index("voie_circulation")
    i = int(np.where((A[:, 0] == 0) & (A[:, 4] == ch) & (A[:, 3] == 1))[0][500])
    keep = np.ones(len(N), bool)
    keep[i] = False
    Fn = np.concatenate([F[off[k]:off[k + 1]] for k in range(len(N)) if keep[k]])
    np.save(d / "l2" / "sol_faces.npy", Fn)
    np.save(d / "l2" / "sol_comptes.npy", N[keep])
    np.save(d / "l2" / "sol_attributs.npy", A[keep])
    r = C.controler_scene(d)
    v = r["etancheite"]["aretes_de_bord_hors_contour"]
    out.append({"temoin": "une face de chaussée retirée du sol (S02)", "mesure": f"{v} arêtes de bord hors contour",
                "detecte": v > 0})
    # 2. un sommet intérieur de la chaussée de S02 relevé de 2 mm
    d = _copie("S02", "sommet_2mm")
    F, N, A, voc, off = _faces(d)
    P = np.load(d / "l2" / "sol_points.npy")
    f = int(np.where((A[:, 0] == 0) & (A[:, 4] == ch) & (A[:, 3] == 1))[0][100])
    P[F[off[f]], 2] += 0.002
    np.save(d / "l2" / "sol_points.npy", P)
    r = C.controler_scene(d)
    v = r["z_sol"]["ecart_max_m"]
    out.append({"temoin": "un sommet de chaussée relevé de 2 mm (S02)", "mesure": f"écart Z max {v * 1000:.3f} mm",
                "detecte": v > 0.001})
    # 3. trottoirs de S02 basculés de 3 % en travers (t)
    d = _copie("S02", "devers_3pct")
    F, N, A, voc, off = _faces(d)
    P = np.load(d / "l2" / "sol_points.npy")
    tr = voc["classe"].index("trottoir")
    pts = np.unique(np.concatenate([F[off[k]:off[k + 1]] for k in np.where((A[:, 0] == 0) & (A[:, 4] == tr))[0]]))
    P[pts, 2] += 0.03 * P[pts, 4]
    np.save(d / "l2" / "sol_points.npy", P)
    r = C.controler_scene(d)
    v = r["trottoirs"]["devers_abs_pct"].get("max", 0.0)
    out.append({"temoin": "trottoirs de S02 basculés de 3 % en travers", "mesure": f"dévers max {v:.2f} %",
                "detecte": v > 2.0})
    # 4. trois éléments de bordure de S02 posés 6 mm trop haut (dessus mesuré relevé)
    d = _copie("S02", "vue_6mm")
    m = json.loads((d / "l2" / "mesures_l2.json").read_text(encoding="utf-8"))
    for e in m["elements"][10:13]:
        e["z_dessus"] += 0.006
    (d / "l2" / "mesures_l2.json").write_text(json.dumps(m), encoding="utf-8")
    r = C.controler_scene(d)
    v = r["bordures"]["vue_hors_5mm"]
    out.append({"temoin": "trois éléments de bordure de S02 posés 6 mm trop haut", "mesure": f"{v} sondes hors ± 5 mm",
                "detecte": v > 0})
    # 5. un joint de S08 transparent (rayon qui touche à 0,60 m derrière la face)
    d = _copie("S08", "joint_ouvert")
    m = json.loads((d / "l2" / "mesures_l2.json").read_text(encoding="utf-8"))
    m["joints"][5]["rayons"][2]["derriere_m"] = 0.60
    (d / "l2" / "mesures_l2.json").write_text(json.dumps(m), encoding="utf-8")
    r = C.controler_scene(d)
    v = r["joints"]["echecs"]
    out.append({"temoin": "un joint de S08 vu à travers (impact à 0,60 m derrière la face)", "mesure": f"{v} échec",
                "detecte": v > 0})
    # 6. un caniveau de S08 posé 5 mm trop bas
    d = _copie("S08", "caniveau_5mm")
    m = json.loads((d / "l2" / "mesures_l2.json").read_text(encoding="utf-8"))
    m["caniveaux"][7]["z_caniveau_2cm"] -= 0.005
    (d / "l2" / "mesures_l2.json").write_text(json.dumps(m), encoding="utf-8")
    r = C.controler_scene(d)
    v = r["caniveaux"]["hors_3mm"]
    out.append({"temoin": "un élément de caniveau de S08 posé 5 mm trop bas", "mesure": f"{v} hors ± 3 mm",
                "detecte": v > 0})
    # 7. une BEV de S08 retirée
    d = _copie("S08", "bev_absente")
    b = json.loads((d / "l2" / "bev.json").read_text(encoding="utf-8"))      # {id BEV: {dalles, plots}}
    b.pop(sorted(b)[0])
    (d / "l2" / "bev.json").write_text(json.dumps(b), encoding="utf-8")
    r = C.controler_scene(d)
    out.append({"temoin": "une bande d'éveil de vigilance de S08 retirée",
                "mesure": f"{r['bev']['bev']} BEV pour {r['bev']['attendues']} attendues",
                "detecte": r["bev"]["bev"] != r["bev"]["attendues"]})
    # 8. un arbre de S03 déplacé de 0,30 m le long de la bande
    d = _copie("S03", "arbre_deplace")
    v_ = json.loads((d / "l2" / "vegetation.json").read_text(encoding="utf-8"))
    (v_["arbres"] if isinstance(v_, dict) else v_)[3]["s"] += 0.30
    (d / "l2" / "vegetation.json").write_text(json.dumps(v_), encoding="utf-8")
    r = C.controler_scene(d)
    v = r["vegetation"]["position_ecart_max_m"]
    out.append({"temoin": "un arbre de S03 déplacé de 0,30 m", "mesure": f"écart de position max {v:.3f} m",
                "detecte": v > 0.001})
    return out


# ------------------------------------------------------------------------------------------------ rapport
def mm(v):
    return "—" if v is None else f"{v * 1000:.2f} mm".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-rendus", action="store_true")
    ap.add_argument("--sans-fabrication", action="store_true")
    ap.add_argument("--recomparer", action="store_true",
                    help="avec --sans-fabrication : refaire la comparaison des sorties des deux processus du dernier passage")
    ap.add_argument("--journal", help="avec --sans-fabrication : journal d'une fabrication complète (un processus par "
                                      "scène, --verifier-determinisme) dont on relit les verdicts de déterminisme")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    rapport = {"lot": "L2", "plan": "recon/generateur/PLAN_GENERATEUR.md § 3 (L2)", "etapes": {}}

    # 1. HDA
    dossiers = [GEN / "hda" / h for h in HDA_L2]
    c1, o1, s1 = lancer([HYTHON, PILOTE, "--construire-hda", "--l2"])
    p1, q1, _ = lancer([HYTHON, GEN / "hda" / "pj_caniveau_v2" / "construire.py"])
    b1, _, _ = lancer([HYTHON, GEN / "hda" / "pj_bordure_v2" / "construire.py"])
    r1, _, _ = lancer([HYTHON, GEN / "hda" / "pj_caniveau_v2_1" / "construire.py"])
    e1 = empreinte(dossiers)
    c2, o2, s2 = lancer([HYTHON, PILOTE, "--construire-hda", "--l2"])
    p2, q2, _ = lancer([HYTHON, GEN / "hda" / "pj_caniveau_v2" / "construire.py"])
    b2, _, _ = lancer([HYTHON, GEN / "hda" / "pj_bordure_v2" / "construire.py"])
    r2, _, _ = lancer([HYTHON, GEN / "hda" / "pj_caniveau_v2_1" / "construire.py"])
    e2 = empreinte(dossiers)
    sig_pj2 = [f.read_text(encoding="utf-8").strip() for f in (GEN / "hda" / HDA_L2[3]).glob("*/RgSignature")]
    pj_depot = {n: empreinte([PJ_DEPOT / n / f"{n}.hdalc"]) for n in ("pj_bordure", "pj_caniveau")}
    sig_pjb2 = [f.read_text(encoding="utf-8").strip() for f in (GEN / "hda" / HDA_L2[4]).glob("*/RgSignature")]
    hda = {"construction": [c1, c2, p1, p2, b1, b2, r1, r2], "signatures": signatures(o2),
           "pj_bordure_2_0": sig_pjb2[0] if sig_pjb2 else "",
           "signatures_stables": signatures(o1) == signatures(o2), "pj_caniveau_2_0": sig_pj2[0] if sig_pj2 else "",
           "dossiers_identiques": e1 == e2, "empreinte_dossiers": e2, "dossiers": [rel(p) for p in dossiers if p.exists()],
           "pj_depot_reutilisees": pj_depot}
    rapport["etapes"]["hda"] = hda
    print("HDA :", hda["signatures"], "stables" if hda["dossiers_identiques"] else "INSTABLES")

    # 2. fabrication S01-S12 (+ rendus) et déterminisme
    noms = [p.stem.split("_")[0] for p in SCENES]

    def empreintes_sorties():
        return {n: hashlib.sha256((OUT / n / "l2" / "manifest_l2.json").read_bytes()).hexdigest()
                for n in noms if (OUT / n / "l2" / "manifest_l2.json").exists()}

    if not a.sans_fabrication:
        cmd = [HYTHON, PILOTE] + SCENES + ["--l2", "--verifier-determinisme"] + ([] if a.sans_rendus else ["--rendus"])
        code, so, se = lancer(cmd)
        (TMP / "rapport_fabrication.log").write_text(so + "\n" + se, encoding="utf-8")
        det = "déterminisme : identique" in so
        ecarts = [x for x in so.splitlines() if x.startswith("déterminisme")]
        faites_passage = [n for n in noms if f"{n} : L2 sol" in so]
    else:
        # reprise : le résultat du déterminisme du rapport précédent vaut si les manifestes (empreintes de tous les
        # fichiers l2/) n'ont pas changé depuis
        code, det, ecarts = 0, None, ["non rejoué (--sans-fabrication)"]
        if a.recomparer:
            # comparaison seule des sorties existantes des deux processus du dernier passage (même code, même run)
            sys.path.insert(0, str(GEN))
            from commun import determinisme as DET
            autre = GEN / "tmp" / "l1" / "determinisme"
            dl1 = [OUT / n / "l1" for n in noms]
            ec, nf = DET.comparer(dl1, autre, True)
            det = not ec
            ecarts = [f"déterminisme : identique ({nf} fichiers ; .usda : chemins relatifs des matériaux normalisés ; "
                      f"comparaison refaite sur les sorties des deux processus du dernier passage)" if det
                      else f"déterminisme : DIFFÉRENT : {ec}"]
        f_prec = ICI / "rapport_L2.json"
        if f_prec.exists():
            prec = json.loads(f_prec.read_text(encoding="utf-8"))["etapes"].get("fabrication", {})
            if not a.recomparer and prec.get("manifestes") == empreintes_sorties() and prec.get("deterministe") is not None:
                code, det = prec["code"], prec["deterministe"]
                ecarts = [x for x in prec.get("determinisme", []) if "reprise" not in x] + [
                    "reprise du rapport précédent : manifestes l2/ inchangés"]
    if a.sans_fabrication and a.journal:
        import faire_rapport_L2b as RB
        det, ecarts = RB.journal_determinisme(Path(a.journal), noms)
    faites = [n for n in noms if (OUT / n / "l2" / "manifest_l2.json").exists()]
    if not a.sans_fabrication:
        faites = faites_passage                      # scènes fabriquées par ce passage (pas d'anciennes sorties)
    rapport["etapes"]["fabrication"] = {"descriptions": [rel(p) for p in SCENES], "code": code, "scenes": faites,
                                        "deterministe": det, "determinisme": ecarts,
                                        "manifestes": empreintes_sorties()}
    print("fabrication :", len(faites), "scènes ;", {True: "déterministe", False: "NON DÉTERMINISTE",
                                                     None: "déterminisme non rejoué"}[det])

    # 3. contrôles indépendants
    scenes = [C.controler_scene(OUT / n) for n in faites]
    bil = C.bilan(scenes)
    (ICI / "controles_L2.json").write_text(json.dumps({"bilan": bil, "scenes": scenes}, ensure_ascii=False, indent=1)
                                           + "\n", encoding="utf-8")
    rapport["etapes"]["controles"] = {"fichier": "recon/generateur/validation/controles_L2.json", "bilan": bil}
    mans = {n: json.loads((OUT / n / "l2" / "manifest_l2.json").read_text(encoding="utf-8")) for n in faites}

    # 4. témoins négatifs
    tem = temoins()
    rapport["etapes"]["temoins"] = tem

    # 5. revue visuelle
    # tuiles des scènes du catalogue seulement (le motif « S* » prenait aussi les rues de Meylan S_M*)
    tuiles = sorted(rel(p) for n in noms for p in (OUT / n / "rendus" / "tuiles").glob("*/*.png"))
    f_c = ICI / "constats_visuels_etape1.json"            # rendus refaits à l'étape 1 (route seule)
    if not f_c.exists():
        f_c = ICI / "constats_visuels_L2.json"
    constats = json.loads(f_c.read_text(encoding="utf-8")) if f_c.exists() else {"constats": []}
    vues = {t for c_ in constats["constats"] for t in c_["tuiles"]}
    regard = {t.split("/")[3] for t in vues & set(tuiles)}
    rendus = {n: json.loads((OUT / n / "rendus" / "manifest_rendus.json").read_text(encoding="utf-8"))
              for n in faites if (OUT / n / "rendus" / "manifest_rendus.json").exists()}
    rapport["etapes"]["revue_visuelle"] = {"scenes_rendues": sorted(rendus), "tuiles_produites": len(tuiles),
                                           "tuiles_regardees": len(vues), "tuiles_regardees_existantes": len(vues & set(tuiles)),
                                           "scenes_regardees": sorted(regard),
                                           "fichier": f"recon/generateur/validation/{f_c.name}"}

    # 6. critères
    b = bil
    n12 = len(noms)
    ral = {n: sum(1 for o in json.loads((OUT / n / "modele_voie.json").read_text(encoding="utf-8")).get("objets", [])
                  if o.get("type") in ("plateau", "dos_d_ane")) for n in faites}
    tq_sol = {
        "TQ-SOL-001 (aire(union) = somme(aires) à 1e-6 m² près, 0 recouvrement ; 0 doublon, 0 face inversée)":
            b["doublons"] == 0 and b["inversees"] == 0 and (b["recouvrement_st_max_m2"] or 0) <= 1e-6,
        "TQ-SOL-003 (lignes de rupture = arêtes contraintes)": b["ruptures_traversees"] == 0,
        "TQ-SOL-004 / TQ-SOL-013 (Z de chaque sommet = modèle unique, ≤ 1 mm)": (b["z_sol_ecart_max_m"] or 0) <= 0.001,
        "TQ-SOL-013 (6) (trottoir = tête − 4 mm ± 2 mm)": (b["retrait_trottoir_ecart_max_m"] or 0) <= 0.002,
        "TQ-SOL-013 (7) (bande plantée isolée = tête − 3 à 5 cm)":
            b["retrait_plantee_min_m"] is None or (0.03 <= b["retrait_plantee_min_m"] and b["retrait_plantee_max_m"] <= 0.05),
        "TQ-SOL-008 (normales des faces de bande = gradient analytique du modèle, ≤ 0,01°, seuil interne)":
            b["normales_sommets_testes"] > 0 and (b["normales_ecart_max_deg"] or 0) <= 0.01,
        "TQ-SOL-009 (étanchéité : 0 non-variété, 0 doublon, 0 aire < 1e-6 m², bords sur l'emprise seulement, 99 % des "
        "triangles à angle min ≥ 20°)": b["aretes_hors_contour"] == 0 and b["non_varietes"] == 0
                                        and b["degenerees"] == 0 and b["mal_orientees"] == 0 and b["doublons"] == 0
                                        and -(b["part_angle_min_ge_20_min"] or -1.0) >= 0.99,
    }
    tq_bor = {
        "TQ-BOR-002 (éléments rigides, coupe ≥ 0,20 m)": b["coupes_lt_0_20"] == 0,
        "TQ-BOR-005 (joints non transparents, 0 échec)": b["joints_echecs"] == 0,
        "TQ-BOR-007 (sol sous chaque élément ; caniveau affleurant ± 3 mm)": b["sol_sous_element_absent"] == 0
                                                                            and b["caniveaux_hors_3mm"] == 0,
    }
    hors = ("TQ-SOL-002 (règle de génération : appliquée par les paramètres de rg::sol, angle 25°, arête min 0,02 m, "
            "arête cible 0,25 m ; tuiles hors lot), TQ-SOL-007 (MNT des abords), TQ-SOL-010 à 012 (Unreal), TQ-SOL-014 "
            "(carrefour, lot L3) ; TQ-BOR-001, 003, 004, 006 (Unreal)")
    crit = [
        {"id": "L2-1 HDA rg::nivellement, rg::sol, rg::vers_entites, pj::caniveau::2.0, pj::caniveau::2.1 (second contrôle) "
               "et pj::bordure::2.0 (nouvelles versions, les 1.0 restent intactes) : dossiers développés, signatures "
               "stables, reconstruction identique",
         "valeur": f"{len(hda['dossiers'])} / 6 ; signatures {'stables' if hda['signatures_stables'] else 'instables'}, "
                   f"dossiers {'identiques' if hda['dossiers_identiques'] else 'différents'}",
         "seuil": "6 / 6", "atteint": len(hda["dossiers"]) == 6 and hda["signatures_stables"] and hda["dossiers_identiques"]
         and not any(hda["construction"])},
        {"id": "L2-2 fabrication de S01-S12 (sol, bordures, caniveaux, BEV, arbres, HeightField, USD) sans erreur",
         "valeur": f"{len(faites)} / {n12}", "seuil": "12 / 12",
         "atteint": (code == 0 or det is False) and len(faites) == n12 == 12},
        {"id": "L2-3 surfaces étanches : 0 arête libre intérieure (TQ-SOL-009)",
         "valeur": f"{b['aretes_hors_contour']} arête de bord hors contour, {b['non_varietes']} non-variété, "
                   f"{b['doublons']} doublon, {b['degenerees']} face d'aire < 1e-6 m², {b['mal_orientees']} mal "
                   f"orientée ; recouvrement en (s, t) {b['recouvrement_st_max_m2']:.1e} m²",
         "seuil": "0", "atteint": b["aretes_hors_contour"] == 0 and b["non_varietes"] == 0 and b["doublons"] == 0
         and b["degenerees"] == 0 and b["mal_orientees"] == 0},
        {"id": "L2-4 jointure entre surfaces ≤ 1 mm (marche visible hors éléments ; sol sous chaque élément)",
         "valeur": f"marche visible max {mm(b['marche_visible_max_m'])}, {b['murs_hors_elements']} mur visible hors "
                   f"élément ; {b['sol_sous_element_absent']} élément sans sol dessous",
         "seuil": "≤ 1 mm ; 0", "atteint": (b["marche_visible_max_m"] or 0) <= 0.001 and b["murs_hors_elements"] == 0
         and b["sol_sous_element_absent"] == 0},
        {"id": "L2-5 vue des bordures = modèle ± 5 mm (dessus de l'élément − surface devant la face)",
         "valeur": f"écart max {mm(b['vue_ecart_max_m'])} ; {b['vue_hors_5mm']} sonde hors tolérance, "
                   f"{b['sondes_sans_impact']} sans impact ({b['sondes_ecartees_angles']} sondes d'angle écartées ; "
                   f"{b.get('sondes_hors_emprise_bout', 0)} sondes devant la coupe d'un bout de scène, face tournée hors de "
                   f"l'emprise, comptées à part)",
         "seuil": "≤ 5 mm ; 0", "atteint": (b["vue_ecart_max_m"] or 0) <= 0.005 and b["vue_hors_5mm"] == 0
         and b["sondes_sans_impact"] == 0},
        {"id": "L2-6 trottoirs : dévers ≤ 2 % et pente < 5 % hors rampants (A2007)",
         "valeur": f"dévers max {b['devers_trottoir_max_pct']:.3f} % ; pente max {b['pente_trottoir_max_hors_rampants_pct']:.4f} %",
         "seuil": "≤ 2 % ; < 5 %", "atteint": b["devers_trottoir_max_pct"] <= 2.0 and b["pente_trottoir_max_hors_rampants_pct"] < 5.0},
        {"id": "L2-7 rampants d'abaissé ≥ 1,50 m (8 %) ou ≥ 2,40 m (5 %), mesurés sur le sol fabriqué",
         "valeur": f"{b['rampants']} rampants, {b['rampants_non_conformes']} non conforme",
         "seuil": "0 non conforme (≥ 1 mesuré)", "atteint": b["rampants"] > 0 and b["rampants_non_conformes"] == 0},
        {"id": "L2-8 contrôles TQ-SOL-* applicables au sol fabriqué : 0 échec",
         "valeur": " ; ".join(f"{k} {'OK' if v else 'ÉCHEC'}" for k, v in tq_sol.items()) + f" ; hors périmètre L2 : {hors}",
         "seuil": "0 échec", "atteint": all(tq_sol.values())},
        {"id": "L2-9 contrôles TQ-BOR-* applicables : 0 échec",
         "valeur": " ; ".join(f"{k} {'OK' if v else 'ÉCHEC'}" for k, v in tq_bor.items())
                   + f" ({b['elements']} éléments, {b['joints']} joints, {b['joints_rayons']} rayons)",
         "seuil": "0 échec", "atteint": all(tq_bor.values())},
        {"id": "L2-10 relief et accessoires : ralentisseurs en relief, BEV, terre-plein planté, arbres (DEF-030)",
         "valeur": f"ralentisseurs {sum(ral.values())} ({', '.join(f'{k} {v}' for k, v in ral.items() if v)}) au Z du "
                   f"modèle ; BEV {b['bev']} / {b['bev_attendues']} (écart max {mm(b['bev_ecart_max_m'])}) ; retrait "
                   f"planté {mm(b['retrait_plantee_min_m'])} à {mm(b['retrait_plantee_max_m'])} ; arbres "
                   f"{b['arbres']} / {b['arbres_attendus']} (écart max {mm(b['arbres_ecart_max_m'])}, axe à "
                   f"{b['arbres_axe_bord_chaussee_min_m']} m au moins du bord de chaussée)",
         "seuil": "BEV et arbres = attendus ; écarts ≤ 1 mm ; axe ≥ 1,50 m",
         "atteint": b["bev"] == b["bev_attendues"] and (b["bev_ecart_max_m"] or 0) <= 0.001
         and b["arbres"] == b["arbres_attendus"] and (b["arbres_ecart_max_m"] or 0) <= 0.001
         and (b["arbres_axe_bord_chaussee_min_m"] or 99) >= 1.5},
        {"id": "L2-11 HeightField de nivellement (README_HDA § 2, sortie 2 de rg::nivellement) : Z lu par pj_niv_z aux "
               "sommets visibles du sol (seuil interne : tolérance de vue, 5 mm)",
         "valeur": f"{b['heightfield_presents']} / {len(faites)} ; {b['heightfield_points_testes']} points, "
                   f"{b['heightfield_absents']} sans région ; écart max {mm(b['heightfield_ecart_max_m'])}, p99 "
                   f"{mm(b['heightfield_ecart_p99_max_m'])}",
         "seuil": "12 / 12 ; 0 sans région ; ≤ 5 mm",
         "atteint": b["heightfield_presents"] == len(faites) and b["heightfield_absents"] == 0
         and (b["heightfield_ecart_max_m"] or 0) <= 0.005},
        {"id": "L2-12 déterminisme (deux processus identiques à l'octet : l1/ et l2/)",
         "valeur": "; ".join(ecarts) if ecarts else "—", "seuil": "identique", "atteint": det is True},
        {"id": "L2-13 rendus Karma XPU de S01-S12 regardés en tuiles natives",
         "valeur": f"{len(rendus)} / {n12} rendues ; {len(regard)} / {n12} regardées ; "
                   f"{len(vues & set(tuiles))} tuiles regardées sur {len(tuiles)}",
         "seuil": "12 / 12", "atteint": len(rendus) == n12 and len(regard) == n12},
        {"id": "L2-14 témoins négatifs détectés par le contrôle indépendant",
         "valeur": f"{sum(t['detecte'] for t in tem)} / {len(tem)} : " + " ; ".join(f"{t['temoin']} → {t['mesure']}"
                                                                               for t in tem),
         "seuil": "100 %", "atteint": all(t["detecte"] for t in tem)},
    ]
    # critères ajoutés par la correction après contrôle (relecture adverse)
    cc = {n: CC.controler(OUT / n) for n in faites}
    avant = {}
    f_av = GEN / "tmp" / "correction" / "controles_avant.json"
    if f_av.exists():
        avant = {x["scene"]: x for x in json.loads(f_av.read_text(encoding="utf-8"))["scenes"]}
    bor = {n: v["bordures"] for n, v in cc.items()}
    fe = {n: v["fil_eau"] for n, v in cc.items()}
    rapport["etapes"]["correction"] = {"bordures": bor, "fil_eau": fe,
                                       "avant": {n: {"bordures_trous_m": x["bordures"]["longueur_trous_m"],
                                                     "fil_eau_interrompu_m": x["fil_eau"]["longueur_interrompue_m"]}
                                                 for n, x in avant.items()}}
    # étape 1 : pièces d'angle posées (pj::bordure::2.0) : plus aucun trou admis ; tout trou > 2 cm est un échec
    # (avant : 6,25 cm admis aux angles en about droit des avancées de S03)
    def trous_hors_angles(v):
        return [t for f in v["files"] for t in f["trous"] if (t[1] - t[0]) > 0.02 + 1e-6]
    crit.append({"id": "L2-15 elements.json complet (relecture adverse : pièces sur mesure des coudes et des angles "
                       "absentes, 2 × 1 m dans S09, 13,2 m dans S03) : chaque file de bordure couverte par ses éléments "
                       "et joints, aucun trou > 2 cm (angles des avancées et des îlots : pièces d'angle en onglet, "
                       "pj::bordure::2.0 ; avant : 6,25 cm admis aux angles en about droit de S03)",
                 "valeur": "trous : " + ", ".join(f"{n} {v['longueur_trous_m']} m" for n, v in sorted(bor.items()) if v["longueur_trous_m"])
                           + f" ; pièces sur mesure listées : {sum(v['pieces_sur_mesure'] for v in bor.values())} "
                           f"({sum(v['longueur_sur_mesure_m'] for v in bor.values()):.2f} m) ; avant : "
                           + ", ".join(f"{n} {x['bordures']['longueur_trous_m']} m" for n, x in sorted(avant.items()) if x["bordures"]["longueur_trous_m"]),
                 "seuil": "0 trou > 2 cm", "atteint": all(not trous_hors_angles(v) for v in bor.values())})
    ral = {n for n in faites if any(o.get("type") in ("plateau", "dos_d_ane") for o in
                                    json.loads((OUT / n / "modele_voie.json").read_text(encoding="utf-8")).get("objets", []))}
    crit.append({"id": "L2-16 fil d'eau continu au droit des ralentisseurs (relecture adverse : caniveau coupé au "
                       "dos-d'âne de S08 et au plateau de S10) : caniveau, caniveau à grille et avaloirs ; longueur de "
                       "fil d'eau sans élément sur toute l'étendue déclarée du caniveau (un retour de bordure sans "
                       "caniveau qui suit une file terminée par un avaloir, avancées de S03, est compté à part ; une "
                       "file fermée sans avaloir reste une interruption)",
                 "valeur": ", ".join(f"{n} : {fe[n]['longueur_interrompue_m']} m sans élément, {fe[n]['grilles']} grille(s), "
                                     f"{fe[n]['avaloirs']} avaloir(s)"
                                     + (f", {fe[n]['longueur_retours_draines_m']} m de retours drainés"
                                        if fe[n].get("longueur_retours_draines_m") else "")
                                     for n in sorted(fe) if fe[n]["files"])
                           + " ; avant : " + ", ".join(f"{n} {x['fil_eau']['longueur_interrompue_m']} m" for n, x in sorted(avant.items())
                                                       if x["fil_eau"]["longueur_interrompue_m"]),
                 "seuil": "0 m (S08, S10 et partout)",
                 "atteint": all(v["longueur_interrompue_m"] == 0 for v in fe.values()) and all(fe[n]["grilles"] > 0 for n in ral)})
    rapport["criteres"] = crit
    rapport["tq"] = {"TQ-SOL": tq_sol, "TQ-BOR": tq_bor, "hors_perimetre": hors}
    rapport["informations"] = {
        "faces_sol": {n: m["controles_houdini"]["faces_sol"] for n, m in mans.items()},
        "murs": {n: m["controles_houdini"]["murs"] for n, m in mans.items()},
        "faces_bordures": {n: m["controles_houdini"]["faces_bordures"] for n, m in mans.items()},
        "faces_caniveaux": {n: m["controles_houdini"]["faces_caniveaux"] for n, m in mans.items()},
        "retrait_trottoir_ecart_max_m": b["retrait_trottoir_ecart_max_m"],
        "angle_min_ge_20_part_min": -b["part_angle_min_ge_20_min"] if b["part_angle_min_ge_20_min"] is not None else None,
        "materiaux": {n: m["usd"]["materiaux"] for n, m in mans.items()},
    }
    rapport["statut"] = "ok" if all(c_["atteint"] for c_ in crit) else "partiel"
    (ICI / "rapport_L2.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for c_ in crit:
        print("ATTEINT" if c_["atteint"] else "NON ATTEINT", c_["id"], "|", c_["valeur"], "| seuil", c_["seuil"])
    print("statut :", rapport["statut"])


if __name__ == "__main__":
    main()
