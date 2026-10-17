# -*- coding: utf-8 -*-
"""Rapport du lot L2b (marquages de la section courante et rendus soignés) : rejoue tout et écrit rapport_L2b.json et
RAPPORT_L2b.md.

    python recon/generateur/validation/faire_rapport_L2b.py [--sans-rendus] [--sans-fabrication]

Étapes (aucune date ni durée écrite dans le rapport) :
1. HDA rg::marquages::1.0 construite deux fois (deux processus) : signature et dossier développé identiques ;
   pj::marquage_solide::1.0 et pj::gabarits_iisr::1.0 du dépôt réutilisées sans modification (empreintes relevées) ;
2. fabrication de S01-S12 avec --l2b --verifier-determinisme (second processus : fichiers l1/, l2/ et l2b/ comparés à
   l'octet) et --rendus (sauf --sans-rendus : les rendus déjà produits sont relus) ;
3. contrôles indépendants (controler_L2b.py, analytique_L2b.py : Python hors Houdini, gabarits du dossier 08 lus
   directement) ;
4. témoins négatifs : chaque témoin fausse une copie des sorties fabriquées ; le contrôle doit la refuser ;
5. rendus : critère M1 (maillages texturés), critère L1 (dynamique p99 − p1 de chaque rendu), planches par scène et
   planches d'ensemble (≤ 1092 px), revue en tuiles natives (constats_visuels_L2b.json) ;
6. critères du lot.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
TMP = GEN / "tmp" / "l2b"
HYTHON = os.environ.get("HYTHON", "C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
PILOTE = GEN / "fabriquer_generateur.py"
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN / "rendu"))
import controler_L2b as C  # noqa: E402
import controler_correction as CC  # noqa: E402

SCENES = sorted((GEN / "scenes_simples").glob("S*.yaml"))
HDA_L2B = GEN / "hda" / "rg_marquages" / "rg_marquages.hdalc"
PJ_COMMUN = DEPOT / "recon" / "pcg" / "houdini" / "hda" / "pj_marquage_commun"
SEUIL_DYN = 0.75
COTE_MAX = 1092


def rel(p):
    return str(Path(p).resolve().relative_to(DEPOT)).replace("\\", "/")


def lancer(cmd):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8", HOUDINI_VEX_DISABLE_JIT="1")
    for k in ("TEMP", "TMP", "HOUDINI_TEMP_DIR"):
        env[k] = str(GEN / "tmp" / "hython")
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(DEPOT), env=env)
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
def _pe(scene):
    return C.Peinture(OUT / scene / "l2b")


def _bouger(pe, nom, f):
    """Applique f (x, y) -> (x, y) aux points de l'entité nom (copie de la peinture)."""
    pe = copy.deepcopy(pe)
    idx = pe.ent[nom]["points"]
    xy = pe.P[idx, :2]
    pe.P[idx, :2] = np.array([f(x, y) for x, y in xy])
    return pe


def _ent(pe, prefixe, rang=0):
    return sorted(n for n in pe.ent if n.startswith(prefixe))[rang]


def _glisser(scene, pe, nom, ds=0.0, dt=0.0):
    """Translation de l'entité nom de ds le long de la référence et de dt en travers (repère local en son centre)."""
    S = C.AB.Scene(OUT / scene)
    R = S.routes[S.m["routes"][0]["id"]]
    cx, cy = pe.P[pe.ent[nom]["pied"], :2].mean(0)
    s, _t = S.st_de_xy(R, float(cx), float(cy))
    th = R.ref.eval(min(max(s, 0.0), R.ref.L))[2]
    dx = ds * math.cos(th) - dt * math.sin(th)
    dy = ds * math.sin(th) + dt * math.cos(th)
    return _bouger(pe, nom, lambda x, y: (x + dx, y + dy))


def temoins():
    out = []

    def ajoute(t, m, d):
        out.append({"temoin": t, "mesure": m, "detecte": bool(d)})
        print(("  détecté   " if d else "  MANQUÉ    ") + t + " : " + m)

    # 1. un tiret de S02 décalé de 2 cm le long de la route (+x)
    pe = _pe("S02")
    n = _ent(pe, "ML_", 3)
    r = C.controler_scene(OUT / "S02", _glisser("S02", pe, n, ds=0.02))
    v = r["lignes"]["debut_fin_max_m"]
    ajoute("un tiret T'1 de S02 décalé de 2 cm en long", f"début/fin max {v * 1000:.1f} mm", v > C.TOL["tiret_m"])
    # 2. un tiret T3 5u de S04 élargi de 3 mm (dilatation en travers autour de son axe)
    pe = _pe("S04")
    n = next(x for x in sorted(pe.ent) if x.startswith("ML_") and "T3" in x)
    yc = float(pe.P[pe.ent[n]["points"], 1].mean())
    r = C.controler_scene(OUT / "S04", _bouger(pe, n, lambda x, y: (x, yc + (y - yc) * (0.253 / 0.25))))
    v = r["lignes"]["largeur_max_m"]
    ajoute("un tiret T3 5u de S04 élargi de 3 mm", f"écart de largeur max {v * 1000:.2f} mm", v > C.TOL["largeur_m"])
    # 3. une flèche TD de S07 tournée de 0,6° autour de son pied
    pe = _pe("S07")
    n = "MQ_M_1_2"
    q = pe.P[pe.ent[n]["pied"], :2]
    o = q[np.argmin(q[:, 0])]
    a = math.radians(0.6)
    r = C.controler_scene(OUT / "S07", _bouger(pe, n, lambda x, y: (o[0] + (x - o[0]) * math.cos(a) - (y - o[1]) * math.sin(a),
                                                                      o[1] + (x - o[0]) * math.sin(a) + (y - o[1]) * math.cos(a))))
    m = next(s for s in r["symboles"] if s["id"] == "M-1.2")
    ajoute("une flèche TD de S07 tournée de 0,6°", f"rotation {m['rotation_deg']:.3f}° ; écart au gabarit "
           f"{1000 * max(m['ecart_sommets_fabriques_m'], m['ecart_sommets_gabarit_m']):.1f} mm",
           abs(m["rotation_deg"]) > C.TOL["angle_deg"] and max(m["ecart_sommets_fabriques_m"], m["ecart_sommets_gabarit_m"]) > C.TOL["gabarit_m"])
    # 4. une flèche TD de S07 décalée de 3 cm en travers
    pe = _pe("S07")
    r = C.controler_scene(OUT / "S07", _glisser("S07", pe, "MQ_M_1_4", dt=0.03))
    m = next(s for s in r["symboles"] if s["id"] == "M-1.4")
    ajoute("une flèche TD de S07 décalée de 3 cm en travers", f"centrage {m['centrage_m'] * 100:.1f} cm",
           m["centrage_m"] > C.TOL["centrage_m"])
    # 5. une flèche de rabattement de S01 agrandie de 0,3 % (homothétie depuis son pied)
    pe = _pe("S01")
    n = "MQ_M_1_2"
    q = pe.P[pe.ent[n]["pied"], :2]
    o = q.mean(0)
    r = C.controler_scene(OUT / "S01", _bouger(pe, n, lambda x, y: (o[0] + 1.003 * (x - o[0]), o[1] + 1.003 * (y - o[1]))))
    m = next(s for s in r["symboles"] if s["id"] == "M-1.2")
    v = max(m["ecart_sommets_fabriques_m"], m["ecart_sommets_gabarit_m"])
    ajoute("une flèche RAB_D de S01 agrandie de 0,3 %", f"écart au gabarit {v * 1000:.2f} mm", v > C.TOL["gabarit_m"])
    # 6. une flèche RAB_D de S01 avancée de 10 cm
    pe = _pe("S01")
    r = C.controler_scene(OUT / "S01", _glisser("S01", pe, "MQ_M_1_3", ds=0.10))
    v = max(q.get("ecart_max_m", 9) for q in r["interdistances"])
    ajoute("une flèche RAB_D de S01 avancée de 10 cm", f"écart de position max {v:.3f} m", v > C.TOL["interdistance_m"])
    # 7. une bande du passage de S08 retirée
    pe = copy.deepcopy(_pe("S08"))
    pe.ent.pop("MQ_M_1_1_b02")
    r = C.controler_scene(OUT / "S08", pe)
    p = r["passages"][0]
    ajoute("une bande du passage piéton de S08 retirée", f"{p['n_mesure']} bandes pour {p['n_attendu']}",
           p["n_mesure"] != p["n_attendu"])
    # 8. peinture d'un tiret de S08 enfoncée de 0,5 mm (dessus − sol)
    pe = copy.deepcopy(_pe("S08"))
    n = _ent(pe, "ML_", 2)
    pe.au[pe.ent[n]["points"]] -= 0.0005
    r = C.controler_scene(OUT / "S08", pe)
    v = r["epaisseur"]["lignes"]["sommets_ecart_max_m"]
    ajoute("un tiret de S08 enfoncé de 0,5 mm", f"écart d'épaisseur max {v * 1000:.2f} mm", v > C.TOL["epaisseur_m"])
    # 9. une hachure du zébra de S09 tournée de 0,3°
    pe = _pe("S09")
    n = next(x for x in sorted(pe.ent) if "_hachure" in x)
    q = pe.P[pe.ent[n]["points"], :2].mean(0)
    a = math.radians(0.3)
    r = C.controler_scene(OUT / "S09", _bouger(pe, n, lambda x, y: (q[0] + (x - q[0]) * math.cos(a) - (y - q[1]) * math.sin(a),
                                                                      q[1] + (x - q[0]) * math.sin(a) + (y - q[1]) * math.cos(a))))
    v = r["zebras"][0]["angle_ecart_max_deg"]
    ajoute("une hachure du zébra de S09 tournée de 0,3°", f"écart d'angle max {v:.3f}°", v > C.TOL["hachure_angle_deg"])
    # 10. un tiret T'2 de S03 retiré
    pe = copy.deepcopy(_pe("S03"))
    n = next(x for x in sorted(pe.ent) if x.startswith("ML_") and "T2" in x)
    pe.ent.pop(n)
    r = C.controler_scene(OUT / "S03", pe)
    t = r["attendus"]["traits"]
    ajoute("un tiret T'2 de S03 retiré", f"traits mesurés {t['mesure']} (attendus {t['attendu']}) ; "
           f"{len(r['lignes']['manquants'])} manquant", not t["ok"] and len(r["lignes"]["manquants"]) == 1)
    # 11. la lettre U de BUS (S12) déplacée de 2 mm
    pe = _pe("S12")
    pe2 = copy.deepcopy(pe)
    e = pe2.ent["MQ_M_1_1"]
    xy = pe2.P[e["points"], :2]
    cx = np.median(xy[:, 0])
    sel = e["points"][np.abs(pe2.P[e["points"], 1] - np.median(xy[:, 1])) < 0.25]
    pe2.P[sel, 0] += 0.002
    r = C.controler_scene(OUT / "S12", pe2)
    m = next(s for s in r["symboles"] if s["id"] == "M-1.1")
    v = max(m["ecart_sommets_fabriques_m"], m["ecart_sommets_gabarit_m"])
    ajoute("une lettre de BUS (S12) déplacée de 2 mm", f"écart au gabarit {v * 1000:.2f} mm", v > C.TOL["gabarit_m"])
    del cx
    # 12. la bande du passage de S10 la plus proche d'une bordure poussée de e + 10 cm vers elle (10 cm sur la bordure)
    pe = _pe("S10")
    S = C.AB.Scene(OUT / "S10")
    R = S.routes[S.m["routes"][0]["id"]]
    p0 = C.controler_scene(OUT / "S10", pe)["passages"][0]
    zones = S.zones_interdites(R, p0["s"])
    choix = []
    for nb in sorted(x for x in pe.ent if x.startswith("MQ_M_1_1_b")):
        st = C._st(S, R, pe.P[pe.ent[nb]["pied"], :2])
        for lo, hi in zones:
            if lo >= st[:, 1].max():
                choix.append((lo - st[:, 1].max(), nb, +1.0))
            elif hi <= st[:, 1].min():
                choix.append((st[:, 1].min() - hi, nb, -1.0))
    g, nb, sens = min(choix)
    r = C.controler_scene(OUT / "S10", _glisser("S10", pe, nb, dt=sens * (g + 0.10)))
    v = r["bordures"]["aire_m2"]
    ajoute(f"une bande du passage de S10 poussée de {(g + 0.10) * 100:.1f} cm vers la bordure (10 cm dessus)",
           f"{v:.4f} m² sur bordure ou caniveau", v > 0)
    return out


# ------------------------------------------------------------------------------------------------ rapport
def journal_determinisme(f, noms):
    """Verdicts de déterminisme d'un journal de fabrication (tmp/correction/fabriquer_tout.sh : un bloc « === <yaml> »
    par scène, ligne « déterminisme : … » du pilote) : (tous identiques, [« Sxx : … »])."""
    out, sc = {}, None
    for ligne in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if ligne.startswith("=== ") and ligne.endswith(".yaml"):
            sc = Path(ligne[4:].strip()).stem.split("_")[0]
        elif ligne.startswith("déterminisme") and sc:
            out[sc] = ligne.split(":", 1)[1].strip()
    lignes = [f"{n} : {out.get(n, 'absent du journal')}" for n in noms]
    return all(out.get(n, "").startswith("identique") for n in noms), lignes


def mm(v):
    return f"{v * 1000:.3f} mm".replace(".", ",")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-rendus", action="store_true", help="fabrication et déterminisme sans rendus (rendus relus)")
    ap.add_argument("--sans-fabrication", action="store_true")
    ap.add_argument("--journal", help="avec --sans-fabrication : journal d'une fabrication complète (un processus par "
                                      "scène, --verifier-determinisme) dont on relit les verdicts de déterminisme")
    a = ap.parse_args()
    TMP.mkdir(parents=True, exist_ok=True)
    rapport = {"lot": "L2b", "titre": "marquages de la section courante et rendus soignés",
               "plan": "recon/generateur/PLAN_GENERATEUR.md § 3 (L4, partie section courante)", "etapes": {}}

    # 1. HDA
    c1, o1, s1 = lancer([HYTHON, PILOTE, "--construire-hda", "--l2b"])
    e1 = empreinte([HDA_L2B])
    c2, o2, s2 = lancer([HYTHON, PILOTE, "--construire-hda", "--l2b"])
    e2 = empreinte([HDA_L2B])
    sig = [f.read_text(encoding="utf-8").strip() for f in HDA_L2B.glob("*/RgSignature")]
    pj = {n: empreinte([PJ_COMMUN / f"{n}.hdalc"]) for n in ("pj_marquage_solide", "pj_gabarits_iisr")}
    sys.path.insert(0, str(GEN / "hda" / "rg_marquages"))
    import gabarits_iisr7 as G
    spec_ok = G.convertir(G.SOURCE.read_bytes()) == json.loads((G.SORTIE).read_text(encoding="utf-8"))
    hda = {"construction": [c1, c2], "signatures": signatures(o2), "signatures_stables": signatures(o1) == signatures(o2),
           "rg_marquages": sig[0] if sig else "", "dossier_identique": e1 == e2, "empreinte_dossier": e2,
           "pj_reutilisees": pj, "gabarits_iisr7_pj_a_jour": spec_ok,
           "gabarits_source_sha256": json.loads(G.SORTIE.read_text(encoding="utf-8"))["source"]["sha256"]}
    rapport["etapes"]["hda"] = hda
    print("HDA :", hda["rg_marquages"][:12], "stable" if hda["dossier_identique"] else "INSTABLE")

    # 2. fabrication et déterminisme
    noms = [p.stem.split("_")[0] for p in SCENES]
    if not a.sans_fabrication:
        cmd = [HYTHON, PILOTE] + SCENES + ["--l2b", "--verifier-determinisme"] + ([] if a.sans_rendus else ["--rendus"])
        code, so, se = lancer(cmd)
        (TMP / "rapport_fabrication.log").write_text(so + "\n" + se, encoding="utf-8")
        det = "déterminisme : identique" in so
        ecarts = [x for x in so.splitlines() if x.startswith("déterminisme")]
        faites = [n for n in noms if f"{n} : L2b" in so]
    else:
        code, det, ecarts = 0, None, ["non rejoué (--sans-fabrication)"]
        faites = [n for n in noms if (OUT / n / "l2b" / "manifest_l2b.json").exists()]
        if a.journal:
            det, ecarts = journal_determinisme(Path(a.journal), noms)
    rapport["etapes"]["fabrication"] = {"descriptions": [rel(p) for p in SCENES], "code": code, "scenes": faites,
                                        "deterministe": det, "determinisme": ecarts}
    print("fabrication :", len(faites), "scènes ;", det)

    # 3. contrôles indépendants
    scenes = [C.controler_scene(OUT / n) for n in faites]
    bil = C.bilan(scenes)
    (ICI / "controles_L2b.json").write_text(json.dumps({"bilan": bil, "scenes": scenes}, ensure_ascii=False, indent=1,
                                                       default=float) + "\n", encoding="utf-8")
    rapport["etapes"]["controles"] = {"fichier": "recon/generateur/validation/controles_L2b.json", "bilan": bil}

    # 4. témoins négatifs
    tem = temoins()
    rapport["etapes"]["temoins"] = tem

    # 5. rendus, planches, revue
    import planches as PL
    rendus = {n: json.loads((OUT / n / "rendus" / "manifest_rendus.json").read_text(encoding="utf-8"))
              for n in noms if (OUT / n / "rendus" / "manifest_rendus.json").exists()}
    rendus = {n: m for n, m in rendus.items() if m.get("schema") in ("rg_rendus_l2b/0.1", "rg_rendus_l2b/0.2", "rg_rendus_l2b/0.3")}
    std = ("dessus", "oblique", "conducteur", "pieton")
    cams_ok = sorted(n for n, m in rendus.items() if all(v in m["images"] for v in std))
    m1 = {n: m["M1"] for n, m in rendus.items()}
    dyn = {f"{n}/{v}": d for n, m in rendus.items() for v, d in m["L1"].items()}
    dyn_ko = {k: d["dynamique"] for k, d in dyn.items() if d["dynamique"] < SEUIL_DYN}
    from PIL import Image
    planches = {}
    for n, m in rendus.items():
        f = OUT / n / "rendus" / m["planche"]
        if f.exists():
            w, h = Image.open(f).size
            planches[n] = {"fichier": rel(f), "taille": [w, h], "ok": max(w, h) <= COTE_MAX}
    for f_ancien in (OUT / "catalogue_rendus").glob("*.png"):     # planches d'un passage précédent remplacées
        f_ancien.unlink()
    ens = PL.planches_ensemble_paires([(n, PL.titre_scene(n), OUT / n / "rendus") for n in sorted(rendus)],
                                      OUT / "catalogue_rendus")
    ens_info = [{"fichier": rel(f), "taille": list(Image.open(f).size)} for f in ens]
    tuiles = sorted(rel(p) for n in rendus for p in (OUT / n / "rendus" / "tuiles").glob("*/*.png"))
    f_c = ICI / "constats_visuels_etape1.json"            # rendus refaits à l'étape 1 (route seule)
    if not f_c.exists():
        f_c = ICI / "constats_visuels_L2b.json"
    constats = json.loads(f_c.read_text(encoding="utf-8")) if f_c.exists() else {"constats": []}
    vues = {t for c_ in constats["constats"] for t in c_.get("tuiles", [])}
    regard_scenes = sorted({t.split("/")[3] for t in vues & set(tuiles)})
    regard_planches = sorted({c_["planche"] for c_ in constats["constats"] if c_.get("planche")})
    rapport["etapes"]["rendus"] = {"scenes": sorted(rendus), "cameras_standard": cams_ok, "M1": m1, "L1": dyn,
                                   "L1_sous_seuil": dyn_ko, "planches": planches, "planches_ensemble": ens_info,
                                   "tuiles_produites": len(tuiles), "tuiles_regardees": len(vues & set(tuiles)),
                                   "scenes_regardees": regard_scenes, "planches_regardees": regard_planches,
                                   "constats": f"recon/generateur/validation/{f_c.name}",
                                   "eclairage": next(iter(rendus.values()))["eclairage"] if rendus else {}}

    # 6. critères
    b = bil
    T, S, P, Z, E = b["tirets"], b["symboles"], b["passages"], b["zebras"], b["epaisseur"]
    n12 = len(noms)
    it = [q for r in scenes for q in r["interdistances"]]
    crit = [
        {"id": "L2b-1 HDA rg::marquages (dossier développé, signature stable, reconstruction identique) ; "
               "pj::marquage_solide::1.0 et pj::gabarits_iisr::1.0 réutilisées telles quelles",
         "valeur": f"signature {hda['rg_marquages'][:12]} {'stable' if hda['signatures_stables'] else 'instable'}, dossier "
                   f"{'identique' if hda['dossier_identique'] else 'différent'} ; gabarits dérivés du dossier 08 "
                   f"{'à jour' if spec_ok else 'PÉRIMÉS'}",
         "seuil": "stable, identique", "atteint": hda["signatures_stables"] and hda["dossier_identique"] and spec_ok
         and not any(hda["construction"])},
        {"id": "L2b-2 fabrication des marquages de S01-S12 sans erreur", "valeur": f"{len(faites)} / {n12}",
         "seuil": "12 / 12", "atteint": code == 0 and len(faites) == n12 == 12},
        {"id": "L2b-3 lignes : tirets conformes aux modulations IISR (RF-MQ-MOD-*) ; période et trait ± 1 cm, dérive "
               "cumulée sur un tronçon ≤ 1 cm sur 100 m ; début et fin de chaque tiret ± 1 cm",
         "valeur": f"{T['fabriques']} tirets pour {T['attendus']} attendus, {T['manquants']} manquant, {T['en_trop']} en trop ; "
                   f"période max {mm(T['periode_max_m'])}, trait max {mm(T['trait_max_m'])}, dérive max "
                   f"{mm(T['derive_max_m'])} ({T['periodes']} périodes) ; début/fin max {mm(T['debut_fin_max_m'])}",
         "seuil": "0 écart de tirets ; ≤ 10 mm", "atteint": T["manquants"] == 0 and T["en_trop"] == 0
         and max(T["periode_max_m"], T["trait_max_m"], T["derive_max_m"], T["debut_fin_max_m"]) <= 0.01},
        {"id": "L2b-4 largeur des lignes (largeur_u × u) ± 2 mm, centrées sur leur limite",
         "valeur": f"écart de largeur max {mm(T['largeur_max_m'])} ; décentrage max {mm(T['decentrage_max_m'])}",
         "seuil": "≤ 2 mm", "atteint": T["largeur_max_m"] <= 0.002 and T["decentrage_max_m"] <= 0.002},
        {"id": "L2b-5 flèches, triangles, figurines, lettres : sommets = gabarit du dossier 08 ± 1 mm, orientation "
               "± 0,5°, centrage ± 2 cm",
         "valeur": f"{S['total'] - S['absents']} / {S['total']} posés ({S['par_type']}) ; écart au gabarit max "
                   f"{mm(S['ecart_gabarit_max_m'])} ; rotation max {S['rotation_max_deg']:.4f}° ; centrage max "
                   f"{S['centrage_max_m'] * 100:.2f} cm",
         "seuil": "≤ 1 mm ; ≤ 0,5° ; ≤ 2 cm", "atteint": S["absents"] == 0 and S["ecart_gabarit_max_m"] <= 0.001
         and S["rotation_max_deg"] <= 0.5 and S["centrage_max_m"] <= 0.02},
        {"id": "L2b-6 positions et interdistances des flèches (RF-MQ-RAB-05 depuis le point de référence ; DEF-017 : "
               "20 m) ± 0,05 m ; pointe de la dernière flèche à 1,50 m d'une ligne transversale",
         "valeur": f"{len(it)} séries, écart max {max((q.get('ecart_max_m', 9) for q in it), default=0):.4f} m, "
                   f"{sum(1 for q in it if q.get('conforme') is False)} non conforme ; pointe à 1,50 m : sans objet "
                   "(aucune ligne transversale dans les scènes de section courante, lot L3)",
         "seuil": "≤ 0,05 m", "atteint": all(q.get("conforme", True) for q in it)
         and max((q.get("ecart_max_m", 9) for q in it), default=0) <= 0.05},
        {"id": "L2b-7 passages piétons : n = floor(W − 0,50) dans la plage IISR, e = (W − 0,5 n)/(n + 1) ± 1 cm, bandes "
               "0,50 ± 2 mm, longueur = zone du modèle ± 1 cm (DEF-011, RF-MQ-PP-02 à -05)",
         "valeur": f"{P['n_conformes']} / {P['passages']} conformes ; e max {mm(P['e_ecart_max_m'])} ; largeur max "
                   f"{mm(P['largeur_ecart_max_m'])} ; longueur max {mm(P['longueur_ecart_max_m'])}",
         "seuil": "100 % ; ≤ 10 mm ; ≤ 2 mm", "atteint": P["n_conformes"] == P["passages"] and P["e_ecart_max_m"] <= 0.01
         and P["largeur_ecart_max_m"] <= 0.002 and P["longueur_ecart_max_m"] <= 0.01},
        {"id": "L2b-8 zébra : hachures à 26,565 ± 0,1° de la rive, pas perpendiculaire 1,85 ± 0,01 m, aplats sous 0,30 m "
               "(DEF-020, RF-MQ-HACH-01, -03)",
         "valeur": f"{Z['zebras']} zébra : {Z['hachures']} hachures ({Z['hachures_sans_angle']} sans angle mesurable), "
                   f"{Z['aplats']} aplats ; écart d'angle max {Z['angle_ecart_max_deg']:.4f}° ; écart de pas max "
                   f"{mm(Z['pas_ecart_max_m'])}",
         "seuil": "≤ 0,1° ; ≤ 10 mm", "atteint": Z["zebras"] >= 1 and Z["angle_ecart_max_deg"] <= 0.1
         and Z["hachures_sans_angle"] == 0 and Z["pas_ecart_max_m"] <= 0.01},
        {"id": "L2b-9 peinture posée sur le sol fabriqué : dessus − sol = 2 mm (lignes) ou 3 mm (autres marques) ± 0,3 mm "
               "aux sommets et aux centres des faces du dessus (TQ-MQG-002, TQ-MQG-004, TQ-MQG-005) ; 0 m² sur une "
               "bordure ou un caniveau (TQ-MQG-014)",
         "valeur": f"lignes : {E['lignes']['sommets']} sommets, écart max {mm(E['lignes']['sommets_ecart_max_m'])}, "
                   f"{E['lignes']['centres']} centres, écart max {mm(E['lignes']['centres_ecart_max_m'])} ; autres : "
                   f"{E['autres']['sommets']} sommets, {mm(E['autres']['sommets_ecart_max_m'])}, {E['autres']['centres']} "
                   f"centres, {mm(E['autres']['centres_ecart_max_m'])} ; sans sol {E['lignes']['sans_sol'] + E['autres']['sans_sol']} ; "
                   f"sur bordure ou caniveau {b['bordures']['aire_m2']:.4f} m²",
         "seuil": "≤ 0,3 mm ; 0 m²", "atteint": max(E[k][q] for k in ("lignes", "autres") for q in
                                                     ("sommets_ecart_max_m", "centres_ecart_max_m")) <= 0.0003
         and E["lignes"]["sans_sol"] + E["autres"]["sans_sol"] == 0 and b["bordures"]["aire_m2"] == 0},
        {"id": "L2b-10 M1 : 100 % des maillages visibles texturés (couleur diffuse lue dans une texture, coordonnées de "
               "texture présentes)",
         "valeur": f"{sum(v['textures'] for v in m1.values())} / {sum(v['maillages'] for v in m1.values())} maillages, "
                   f"{len(m1)} scènes", "seuil": "100 %",
         "atteint": len(m1) == n12 and all(v["textures"] == v["maillages"] for v in m1.values())},
        {"id": "L2b-11 L1 : dynamique p99 − p1 de la luminance de chaque rendu ≥ 0,75 (exposition fixe)",
         "valeur": f"{len(dyn) - len(dyn_ko)} / {len(dyn)} rendus ; min {min((d['dynamique'] for d in dyn.values()), default=0):.3f}"
                   + (f" ; sous le seuil : {', '.join(f'{k} {v:.3f}' for k, v in sorted(dyn_ko.items()))}" if dyn_ko else ""),
         "seuil": "≥ 0,75 partout", "atteint": len(dyn) > 0 and not dyn_ko},
        {"id": "L2b-12 jeu de caméras standard (dessus, oblique 3/4 ~25 m, conducteur 1,20 m, piéton 1,60 m) rendu pour "
               "chaque scène ; planche catalogue par scène et planches d'ensemble ≤ 1092 px, regardées ; tuiles natives "
               "regardées",
         "valeur": f"caméras {len(cams_ok)} / {n12} ; planches {sum(1 for v in planches.values() if v['ok'])} / {n12} "
                   f"(≤ {COTE_MAX} px), regardées {len(regard_planches)} ; ensemble {len(ens_info)} fichier(s) "
                   f"{[x['taille'] for x in ens_info]} ; tuiles regardées {len(vues & set(tuiles))} / {len(tuiles)}, "
                   f"{len(regard_scenes)} scènes",
         "seuil": "12 / 12", "atteint": len(cams_ok) == n12 and sum(1 for v in planches.values() if v["ok"]) == n12
         and len(regard_planches) >= n12 and len(regard_scenes) == n12
         and all(max(x["taille"]) <= COTE_MAX for x in ens_info)},
        {"id": "L2b-13 « attendus » du catalogue vérifiés sur les sorties fabriquées (L1, L2, L2b)",
         "valeur": f"{b['attendus']['scenes_ok']} / {len(scenes)} scènes, {b['attendus']['ok']} / {b['attendus']['cles']} "
                   "clés" + (f" ; échecs : {b['attendus']['echecs']}" if b["attendus"]["echecs"] else ""),
         "seuil": "12 / 12", "atteint": b["attendus"]["scenes_ok"] == n12},
        {"id": "L2b-14 déterminisme (deux processus, octet : l1/, l2/, l2b/)",
         "valeur": "; ".join(ecarts), "seuil": "identique", "atteint": det is True},
        {"id": "L2b-15 témoins négatifs détectés par le contrôle indépendant",
         "valeur": f"{sum(t['detecte'] for t in tem)} / {len(tem)} : " + " ; ".join(f"{t['temoin']} → {t['mesure']}"
                                                                         for t in tem),
         "seuil": "100 %", "atteint": all(t["detecte"] for t in tem)},
    ]
    # critères ajoutés par la correction après contrôle (relecture adverse)
    cc = {n: CC.controler(OUT / n) for n in faites}
    rapport["etapes"]["correction"] = {"controles": "recon/generateur/validation/controles_correction.json",
                                       "lisibilite": {n: v["lisibilite"] for n, v in cc.items()},
                                       "arbres": {n: v["arbres"] for n, v in cc.items()}}
    lis = {n: v["lisibilite"] or {} for n, v in cc.items()}
    tr_ok = {n: x["ecart_trottoir_enrobe_atteint"] for n, x in lis.items() if "ecart_trottoir_enrobe_atteint" in x}
    # correction après le second contrôle : chaque classe de peinture à part (le passage seul, comme dans la référence)
    mq_ok = {f"{n}/{c}": ok for n, x in lis.items() for c, ok in (x.get("ecart_classe_enrobe_atteint") or {}).items()}
    mq_v = {f"{n}/{c}": v for n, x in lis.items() for c, v in (x.get("ecart_classe_enrobe") or {}).items()}
    crit.append({"id": "L2b-16 lisibilité de la vue de dessus (ajouté à côté de L2b-11, relecture adverse) : écarts de "
                       "luminance médiane trottoir − enrobé et peinture − enrobé, chaque classe de peinture à part "
                       "(second contrôle : le passage seul), ≥ ceux de la référence de l'utilisateur "
                       "(ref_carrefour_dessus : 0,318 et 0,406)",
                 "valeur": "trottoir − enrobé : " + ", ".join(f"{n} {lis[n].get('ecart_trottoir_enrobe')}" for n in sorted(tr_ok))
                           + f" ({sum(tr_ok.values())} / {len(tr_ok)}) ; peinture − enrobé par classe : "
                           + ", ".join(f"{k} {mq_v[k]}" for k in sorted(mq_ok))
                           + f" ({sum(mq_ok.values())} / {len(mq_ok)}) ; enrobé : "
                           + ", ".join(f"{n} {(lis[n].get('enrobe') or {}).get('Y_median')}" for n in sorted(lis)),
                 "seuil": "≥ 0,318 et ≥ 0,406 sur chaque scène et chaque classe", "atteint": bool(tr_ok) and all(tr_ok.values())
                 and bool(mq_ok) and all(mq_ok.values())})
    arb = [p for v in cc.values() for p in ((v["arbres"] or {}).get("prototypes") or [])]
    arb_ok = [p for p in arb if p["cartes_ok"] and p["fut_ok"] and p["rayon_ok"] and p["hauteur_ok"]]
    crit.append({"id": "L2b-17 arbres rendus aux dimensions du modèle (relecture adverse) : cartes de feuilles 0,08-0,15 m, "
                       "rien sous le fût (gabarit RF-OSM-VEG-001 : 3,80 m au-dessus de la chaussée, 2,50 m au-dessus d'un "
                       "trottoir), rayon du feuillage dans [0,85 ; 1,05] × houppier, hauteur ≤ 1,02 H",
                 "valeur": f"{len(arb_ok)} / {len(arb)} prototypes ; " + " ; ".join(
                     f"{p['groupe']}/{p['prototype']} H {p['gabarit']['hauteur']} fût {p['gabarit']['fut']} R "
                     f"{p['gabarit']['houppier']} : cartes {p['mesures']['carte_min_m']}-{p['mesures']['carte_max_m']}, "
                     f"bas {p['mesures']['feuilles_bas_m']}/{p['mesures']['branches_bas_m']}, R×{p['rayon_rel']}, "
                     f"h {p['mesures']['hauteur_m']}" for p in arb if p["groupe"].startswith("Arbres_modele"))[:1500],
                 "seuil": "100 %", "atteint": bool(arb) and len(arb_ok) == len(arb)})
    etapes = {m.get("etape", 2) for m in rendus.values()}
    if etapes == {1} and not arb:
        # étape 1 (décision de l'utilisateur : la route seule, la végétation à l'étape 2) : aucun arbre rendu ; le
        # critère est gardé, reporté, et exclu du statut (ni atteint ni abaissé)
        crit[-1]["valeur"] = ("aucun arbre rendu : étape 1, la route seule (décision de l'utilisateur du 17/10/2026) ; "
                              "dimensions portées dans le modèle (L0-16), code de rendu gardé et désactivé")
        crit[-1]["atteint"] = None
        crit[-1]["reporte"] = "étape 2 (végétation)"
    rapport["criteres"] = crit
    rapport["statut"] = "ok" if all(c["atteint"] for c in crit if c["atteint"] is not None) else "partiel"
    (ICI / "rapport_L2b.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1, default=float) + "\n",
                                          encoding="utf-8")
    for c in crit:
        print(("REP " if c["atteint"] is None else ("OK  " if c["atteint"] else "NON ")) + c["id"][:90] + " : "
              + c["valeur"][:220])
    print("statut :", rapport["statut"])
    ecrire_md(rapport)
    return 0


# ------------------------------------------------------------------------------------------------ RAPPORT_L2b.md
ECARTS = """## 6. Écarts au plan, interprétations et règles manquantes

- **HDA pj de marquage** : pj::marquage_solide::1.0 (extrusion, chanfrein, drapé sur le sol fabriqué, UV, normales) et
  pj::gabarits_iisr::1.0 (lecture des gabarits, avec une spécification dérivée du dossier 08) sont réutilisées telles
  quelles. pj::marquage_ligne, pj::passage_pieton et pj::symbole_iisr ne le sont pas : elles ne découpent pas les
  empreintes aux lignes de rupture du sol (une ligne de 2 mm sur une couronne à 2 × 2,5 % n'est plus qu'à 0,75 mm du
  sol en son milieu ; une bande de passage de 3 mm qui enjambe l'arête haute d'une rampe à 7 % passe 1,4 mm sous le
  sol) et pj::symbole_iisr lit marquages_geometrie.json, dont RAB_D et RAB_G sont antérieurs aux corrections du
  dossier 08 (TRIANGLE_DOS_ANE et glyphes absents). Les empreintes sont faites par rg::marquages ; aucune nouvelle
  version pj:: n'a été nécessaire. Les instances pour Unreal (points + prototypes de pj::symbole_iisr) restent au lot L4.
- **Compilateur L0 modifié** (description/description_vers_modele.py, `_decorer` ; ancienne version dans
  tmp/l2b/description_vers_modele.py.avant_L2b) : une interruption d'obstacle (passage piéton, RF-MQ-PP-03) coupe aussi
  une marque de remplacement qui la chevauche (S08 : l'axe T3 du dos-d'âne traversait le passage). faire_rapport_L0
  relancé : voir rapport_L0.json.
- **Choix sans règle, déclarés [G]** (comme au lot catalogue) : phase des tirets (chaque tronçon commence par un trait,
  trait tronqué gardé s'il fait au moins la moitié d'un trait) ; dégagement de 2u bord à bord entre deux lignes qui
  convergent, la discontinue s'arrête (S09 : l'axe T'1 s'arrête à 81,075 m) ; classe d'usure de la peinture =
  ceil(3 × usure) (légère 0,2 → u1, moyenne 0,4 → u2).
- **Écarts au plan coté du catalogue** (scenes_simples/description.py), sans effet sur les « attendus » :
  T3 dessinée par le catalogue à 13/3 m de période, RF-MQ-MOD-T3 donne 4,33 m (3,00 + 1,33 ; écart cumulé 7,7 cm sur
  100 m : règle « multiples ou sous-multiples de 13 m » à préciser) ; oblique de S09 centrée sur sa limite (modèle) et
  non tangente au nez de bordure (catalogue), sa peinture s'arrête au bord du caniveau (TQ-MQG-014 : jamais sur un
  caniveau) ; 2e flèche de rabattement de S09 au milieu de la voie qui se resserre (t = 1,25, modèle) et non dans l'axe
  de la voie en section courante (t = 1,50, catalogue) : « dans l'axe de la voie supprimée » est ambigu.
- **Modèle** : sur les avancées de S03, la limite bordée porte encore la ligne T'2 du stationnement ; rg::marquages ne
  peint jamais une limite bordée (MQ-DET-010) — 14 lignes écartées, à retirer à la source dans le compilateur.
- **Contrôle renforcé par les témoins** : à leur premier passage, trois témoins n'étaient pas détectés. Deux montraient
  une faiblesse du contrôle, corrigée : la position d'une flèche venait d'un seul Kabsch sur les plus proches sommets
  (un recul de 10 cm le long du fût n'en donnait que 1,5 cm ; position désormais par le centre de surface des faces du
  dessus, rotation par ICP) ; une hachure découpée par le maillage en segments de moins de 0,30 m n'avait aucun côté
  mesurable et échappait au contrôle d'angle (enveloppe débarrassée des sommets alignés, hachure sans angle signalée).
  Le troisième était mal construit (bande de S10 déplacée de 40 cm alors que e = 58 cm : elle n'atteignait pas la
  bordure ; elle est désormais poussée de e + 10 cm).
- **« Attendus » du catalogue** : la largeur de chaussée est mesurée sur la largeur courante (celle qui couvre la plus
  grande longueur ; S03 : 8,00 sur les places, 6,00 sur les avancées) et un abaissé est un tronçon de bordure de vue
  ≤ 3 cm (DEF-031 : 2 cm ; le sommet du dos-d'âne de S08, 10 cm sous une bordure de 14 cm, laisse 4 cm et n'est pas un
  abaissé). Reste un écart sur S03 : le catalogue compte 256 m de bordures, la géométrie L2 en a 252 m. Les deux
  avancées d'extrémité (0-2,50 m et 97,50-100 m) touchent les bouts de la scène ; le catalogue compte leur côté
  transversal extérieur (2 × 2,00 m), rg::vers_entites ne le construit pas (aucune section voisine au-delà du bout).
  Convention à trancher (catalogue ou lot L2), hors du périmètre de ce lot : le critère est laissé non atteint.
- **Pointe de la dernière flèche à 1,50 m d'une ligne transversale** (DEF-017) : sans objet dans les scènes de section
  courante (aucune ligne transversale) ; contrôlé au lot L3/L4 avec les carrefours.
- **Règles manquantes ou à préciser** (à porter dans regles_route_fr.json par son propriétaire) : phase des tirets et
  traitement d'un trait tronqué ; espace minimal entre deux marques distinctes (lignes qui convergent, flèche et
  oblique) ; raccord de l'oblique d'une réduction de voies à la bordure (nez, caniveau) ; position latérale d'une flèche
  de rabattement dans une voie qui se resserre ; période de T3 (1,33 ou 13/3) ; correspondance entre l'usure dite
  (légère, moyenne) et les classes IISR.
- **Rendus** : le ciel est un modèle analytique (Preetham) avec des nuages fractals et un voile d'horizon, et non une
  HDRI CC0 (aucune sur le disque ; un téléchargement demandait l'accord de l'utilisateur) ; le ciel vu en image est
  rendu 2,2 fois plus lumineux que le ciel qui éclaire (dôme de fond sans contribution, choix de rendu déclaré) ; les
  arbres sont procéduraux (3 prototypes par gabarit, PointInstancer), décor hors de l'emprise du modèle sauf les arbres
  du modèle ; l'enrobé ancien est rendu avec l'enrobé usé de route_fr (albédo 0,17 ; celui du site, étalonné sur
  l'ortho, vaut 0,28) ; les BEV de rg::sol n'ont pas de coordonnées de texture (projection de dessus ajoutée dans la
  scène de rendu seulement, à corriger à la source dans rg::sol) ; carte de rugosité du gazon inversée au rendu
  (rapport L2). *Après la correction (§ 8) : enrobé ancien recoloré à 0,11 ; BEV avec coordonnées de texture dans
  rg::sol ; sols en MaterialX.*
"""


def ecrire_md(rapport):
    b = rapport["etapes"]["controles"]["bilan"]
    r = rapport["etapes"]["rendus"]
    L = []
    L.append("# Rapport du lot L2b : marquages de la section courante et rendus soignés (S01-S12)\n")
    L.append("*`recon/generateur/validation/RAPPORT_L2b.md` — produit par `python recon/generateur/validation/faire_rapport_L2b.py` "
             "(données : `rapport_L2b.json`, `controles_L2b.json`, `constats_visuels_L2b.json`). Houdini 22.0.459 Indie "
             "(hython), VEX interprété, Karma XPU (husk). Base de règles lue, non modifiée : `regles_route_fr/1.0` ; "
             "dossier 08 lu, non modifié.*\n")
    dans = [c for c in rapport["criteres"] if c["atteint"] is not None]
    L.append(f"**Statut : {rapport['statut']} — {sum(bool(c['atteint']) for c in dans)} critères sur "
             f"{len(dans)} atteints**" + (f", {len(rapport['criteres']) - len(dans)} reporté(s) à l'étape 2 (décision de "
                                          "l'utilisateur : la route seule)" if len(dans) < len(rapport["criteres"]) else "")
             + chr(10))
    L.append(INTRO)
    L.append("## 2. Critères\n")
    L.append("| Critère | Valeur | Seuil | Atteint |\n|---|---|---|---|")
    for c in rapport["criteres"]:
        L.append(f"| {c['id']} | {c['valeur']} | {c['seuil']} | "
                 f"{'reporté (' + c.get('reporte', 'étape 2') + ')' if c['atteint'] is None else ('oui' if c['atteint'] else 'non')} |")
    L.append("")
    L.append("## 3. Mesures (contrôle indépendant)\n")
    T, S = b["tirets"], b["symboles"]
    L.append("Méthode : `controler_L2b.py` relit la peinture fabriquée (sommets du pied de la jupe, au ras de l'empreinte ; "
             "sommets et centres des faces du dessus avec leur hauteur au-dessus du sol fabriqué, rayon vertical posé dans "
             "Houdini) et la compare aux marques recalculées par `analytique_L2b.py` à partir du modèle, des règles et des "
             "gabarits du dossier 08 lus directement (aucun code commun avec le VEX). Symboles : écarts des sommets au "
             "gabarit posé (dans les deux sens), rotation par ICP, position par le centre de surface des faces du dessus "
             "(biais du chanfrein ≤ 2 mm).\n")
    L.append("| Contrôle | Résultat |\n|---|---|")
    L.append(f"| Tirets | {T['fabriques']} fabriqués / {T['attendus']} attendus ; début et fin max {T['debut_fin_max_m'] * 1000:.4f} mm ; "
             f"largeur max {T['largeur_max_m'] * 1000:.4f} mm ; décentrage max {T['decentrage_max_m'] * 1000:.4f} mm |")
    L.append(f"| Modulations | {T['periodes']} périodes ; écart de période max {T['periode_max_m'] * 1000:.4f} mm ; trait "
             f"{T['trait_max_m'] * 1000:.4f} mm ; dérive cumulée {T['derive_max_m'] * 1000:.4f} mm |")
    L.append(f"| Symboles | {S['par_type']} ; écart au gabarit max {S['ecart_gabarit_max_m'] * 1000:.4f} mm ; rotation "
             f"{S['rotation_max_deg']:.4f}° ; centrage {S['centrage_max_m'] * 100:.3f} cm |")
    L.append(f"| Interdistances | {b['interdistances']['series']} séries ; écart max {b['interdistances']['ecart_max_m']:.4f} m |")
    P = b["passages"]
    L.append(f"| Passages | {P['n_conformes']} / {P['passages']} ; e {P['e_ecart_max_m'] * 1000:.4f} mm ; bandes "
             f"{P['largeur_ecart_max_m'] * 1000:.4f} mm ; longueur {P['longueur_ecart_max_m'] * 1000:.4f} mm |")
    Z = b["zebras"]
    L.append(f"| Zébras | {Z['hachures']} hachures ({Z.get('hachures_sans_angle', 0)} sans angle mesurable), "
             f"{Z['aplats']} aplats ; angle {Z['angle_ecart_max_deg']:.4f}° ; pas "
             f"{Z['pas_ecart_max_m'] * 1000:.4f} mm |")
    E = b["epaisseur"]
    L.append(f"| Épaisseur (dessus − sol) | lignes : {E['lignes']['sommets']} sommets ({E['lignes']['sommets_ecart_max_m'] * 1000:.4f} mm), "
             f"{E['lignes']['centres']} centres ({E['lignes']['centres_ecart_max_m'] * 1000:.4f} mm) ; autres : "
             f"{E['autres']['sommets']} sommets ({E['autres']['sommets_ecart_max_m'] * 1000:.4f} mm), {E['autres']['centres']} "
             f"centres ({E['autres']['centres_ecart_max_m'] * 1000:.4f} mm) |")
    L.append(f"| Peinture sur bordure ou caniveau | {b['bordures']['aire_m2']:.6f} m² ({b['bordures']['faces']} faces) |")
    L.append(f"| Attendus du catalogue | {b['attendus']['ok']} / {b['attendus']['cles']} clés, {b['attendus']['scenes_ok']} scènes |")
    L.append("")
    L.append("## 4. Témoins négatifs\n")
    for t in rapport["etapes"]["temoins"]:
        L.append(f"- {t['temoin']} → {t['mesure']} : {'détecté' if t['detecte'] else 'NON DÉTECTÉ'}")
    L.append("")
    L.append("## 5. Rendus et revue visuelle\n")
    ecl = r.get("eclairage", {})
    L.append(f"Karma XPU, {r.get('scenes') and len(r['scenes'])} scènes, caméras dessus, oblique 3/4, conducteur 1,20 m, piéton "
             f"1,60 m et une vue de détail ; soleil {ecl.get('soleil_elevation_deg')}° (DistantLight normalisée), ciel "
             f"de Preetham (turbidité {ecl.get('ciel', {}).get('turbidite')}) ; exposition fixe, courbe "
             f"« {ecl.get('courbe')} ». Planches : `recon/out/generateur/<scène>/rendus/planche_<scène>.png` ; ensemble : "
             f"{', '.join(x['fichier'] for x in r['planches_ensemble'])}. Tuiles regardées : {r['tuiles_regardees']} sur "
             f"{r['tuiles_produites']}.\n")
    L.append("| Rendu | p1 | p99 | p99 − p1 |\n|---|---|---|---|")
    for k, d in sorted(r["L1"].items()):
        L.append(f"| {k} | {d['p1']:.3f} | {d['p99']:.3f} | {d['dynamique']:.3f}{' (< 0,75)' if d['dynamique'] < SEUIL_DYN else ''} |")
    L.append("")
    f_c = ICI / "constats_visuels_L2b.json"
    if f_c.exists():
        c = json.loads(f_c.read_text(encoding="utf-8"))
        for x in c["constats"]:
            L.append(f"- **{x['scene']}** : {x['constat']}" + (f" Défauts : {x['defauts']}" if x.get("defauts") else ""))
        L.append("")
    L.append(ECARTS)
    L.append(CORRECTIONS)
    L.append(FICHIERS)
    (ICI / "RAPPORT_L2b.md").write_text("\n".join(L) + "\n", encoding="utf-8")


INTRO = """## 1. Ce que le lot apporte

Une description simple (« voie ← | T'1 | voie → », un passage piéton ici, un dos-d'âne là, une réduction de voies avec
ses flèches de rabattement) est compilée en modèle (L0), échantillonnée (L1), nivelée et fabriquée en sol, bordures et
caniveaux (L2), puis **peinte** :

```
hython recon/generateur/fabriquer_generateur.py recon/generateur/scenes_simples/S08_rue_dos_d_ane_passage.yaml --l2b --rendus
  -> recon/out/generateur/S08/l2b/      empreintes, peinture (maillages), mesures, route_l2b.usda
  -> recon/out/generateur/S08/rendus/   dessus, oblique, conducteur, piéton, détail ; planche_S08.png ; tuiles
```

- **rg::marquages::1.0** (nouvelle HDA, VEX) : empreintes exactes de toutes les marques de la section courante —
  lignes à modulation IISR (RF-MQ-MOD-*), rives, continues, obliques, flèches directionnelles et de rabattement,
  triangles de dos-d'âne, passages piétons (n et e par DEF-011 / RF-MQ-PP-05), zébra (DEF-020), figurines vélo, BUS au
  sol (glyphes de 1,50 m) — gabarits et glyphes du dossier 08 au sommet près ; chaque empreinte est découpée aux lignes
  de rupture du sol (couronne, bandes, rampes, dos-d'âne) et jamais posée sur une bordure ou un caniveau ;
- **pj::marquage_solide::1.0** réutilisée deux fois (peinture des lignes 2 mm, enduit des autres marques 3 mm,
  TQ-MQG-002), drapée sur le sol fabriqué (TQ-MQG-005) ;
- **rendus soignés** (`rendu/rendu_l2b.py`) : matériaux PBR de la bibliothèque (enrobé usé, béton des bordures,
  trottoir, BEV, herbe sans répétition visible, peinture avec masques d'usure), ciel physique et nuages, soleil bas,
  arbres procéduraux, sol de décor raccordé au bord du sol fabriqué, caméras standard et planches catalogue
  (rendus refaits par la correction après contrôle : § 8).
"""

CORRECTIONS = """## 8. Corrections après contrôle (relecture adverse de l'étape 1, 17/10/2026)

Détail et mesures avant / après : `RAPPORT_correction.md`. Pour ce lot :

- **Zébras** (rg::marquages) : une zone hachurée interrompue par une autre section (îlot bordé de même largeur, rues de
  Meylan) était jointe par-dessus l'interruption avec un indice de bande absent (polygone peint hors de la chaussée) ;
  elle est découpée en suites continues. Une zone pleine dès s = 0 était remplie d'un aplat (test `sa > 0`) : hachurée.
  S01-S12 inchangés (aucun zébra de ce genre).
- **Rendus** (rendu/rendu_l2b.py, textures_sol.py, decor_l2b.py) : soleil à 42° (faces des bordures prises pour des
  rives à 25°) ; exposition au gain 1 et courbe en S 0,50 ; sols en MaterialX (détail de la bibliothèque recoloré ×
  carte macro × bruit fractal en coordonnées du monde, aucune répétition, aucune couture entre abord et décor) :
  enrobé ancien d'albédo 0,11 gris chaud, béton balayé 0,35 à joints, enrobé de trottoir clair 0,35 (à 0,24, l'écart
  trottoir − enrobé ne valait que 0,21 contre 0,318 dans la référence), dalles 0,32 grises (et non sable), herbe à
  teinte 75-80° de saturation modérée, cartes macro (4-20 m) et méso (touffes 7-30 cm, plaques 0,2-1,2 m, bruit
  spectral isotrope, deux périodes incommensurables : aucune répétition) ; bordures au 0,80 de leur albédo ; BEV en dalles
  podotactiles jointées (UV le long de la bordure, rg::sol) ; peinture salie (blanc 0,66 / 0,58 / 0,52 selon la classe)
  et masques d'usure à granulats affleurants (plus de cellules polygonales) ; caniveau à grille au droit des
  ralentisseurs, grilles d'avaloir au pied des rampes de plateau et au bout des files de caniveau fermées par une
  avancée (S03) ; arbres aux dimensions du modèle ; prolongement de la route sur 400 m hors de
  l'emprise ; sol de décor sans triangles géants (Karma XPU ne rendait pas les triangles de plusieurs kilomètres :
  stries) ; fond de relief voilé de bleu-gris (perspective aérienne) ; saison lue dans `date` du modèle ; empreintes
  sha256 de route_l2.usda et route_l2b.usda dans manifest_rendus.json.
- **Critère ajouté** L2b-16 (lisibilité mesurée sur la vue de dessus, contrôle indépendant controler_correction.py) et
  L2b-17 (arbres) ; le seuil de L2b-11 (dynamique ≥ 0,75) est gardé tel quel (il ne mesure pas la lisibilité : la
  référence de l'utilisateur n'atteint que 0,47).
- **Revue visuelle** : toutes les tuiles natives des rendus refaits (constats_visuels_L2b.json), vues ciblées aux points
  singuliers (coude de bordure, caniveau au dos-d'âne et au plateau, fin de route, angle d'avancée).
"""

FICHIERS = """## 7. Fichiers

- HDA : `recon/generateur/hda/rg_marquages/` (construire.py, marquages.vfl, rg_marquages.hdalc, gabarits_iisr7.py,
  gabarits_iisr7_pj.json), `recon/generateur/hda/commun/vex/rg_marquage.h`, `README_RG.md` § 6.
- Pilote : `recon/generateur/fabriquer_generateur.py` (`--l2b`), `recon/generateur/fabriquer_l2b.py`,
  `recon/generateur/rendu/{rendu_l2b,ciel,decor_l2b,textures,planches}.py`, `recon/generateur/commun/determinisme.py`.
- Contrôle : `recon/generateur/validation/{analytique_L2b,controler_L2b,faire_rapport_L2b}.py`, `rapport_L2b.json`,
  `controles_L2b.json`, `constats_visuels_L2b.json`.
- Sorties (non versionnées) : `recon/out/generateur/S01…S12/l2b/` et `rendus/`, `recon/out/generateur/catalogue_rendus/`.
"""


if __name__ == "__main__":
    sys.exit(main())
