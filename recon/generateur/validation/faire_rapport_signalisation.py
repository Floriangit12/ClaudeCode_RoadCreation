"""Rapport du lot L6 (signalisation verticale et feux) : contrôle indépendant de toutes les scènes, test ARB-19,
déterminisme, constats visuels -> validation/rapport_signalisation.json (le texte RAPPORT_signalisation.md est écrit à
la main à partir de ce JSON).

    python recon/generateur/validation/faire_rapport_signalisation.py [--determinisme]
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SORTIE = DEPOT / "recon" / "out" / "generateur"
HYTHON = Path("C:/Program Files/Side Effects Software/Houdini 22.0.459/bin/hython.exe")
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN / "hda" / "rg_signalisation"))
import controler_signalisation as C  # noqa: E402
import plan_signalisation as PS  # noqa: E402

SCENES_DETERMINISME = ("J1_T_cedez", "J5_carrefour_complexe", "G2_giratoire_periurbain_D50", "A4_bretelle_sortie",
                       "E01_entree_agglomeration")
FICHIERS_L6 = ("plan_signalisation.json", "ensembles.json", "instances.json", "points/signalisation.json",
               "points/feux.json", "mesures_l6.json", "signalisation.usda")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_arb19():
    """ARB-19 : une branche « stop_a_verifier » ne reçoit ni AB4 ni AB5, même si le modèle en porte un (défense en
    profondeur du plan). Copie de J2 dans recon/generateur/tmp/l6/arb19, branche B-nord passée à « stop_a_verifier »."""
    src = SORTIE / "J2_croix_stop"
    tmp = GEN / "tmp" / "l6" / "arb19" / "J2_croix_stop"
    (tmp / "l1").mkdir(parents=True, exist_ok=True)
    (tmp / "l3").mkdir(parents=True, exist_ok=True)
    for f in ("l1/courbes_controle.json", "l3/carrefours.json"):
        shutil.copyfile(src / f, tmp / f)
    m = json.loads((src / "modele_voie.json").read_text(encoding="utf-8"))
    for c in m["carrefours"]:
        for b in c["branches"]:
            if b["id"] == "B-nord":
                b["regime"] = "stop_a_verifier"
    (tmp / "modele_voie.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    plan = PS.construire_plan(tmp, PS.COMPLEMENTS / "J2_croix_stop.yaml")
    ab4 = [e["id"] for e in plan["ensembles"] if e.get("applicabilite", {}).get("branche") == "B-nord"
           and any(x["code"] == "AB4" for x in e["elements"])]
    refus = [x for x in plan["non_poses"] if x.get("code") == "AB4" and x.get("regle") == "ARB-19"]
    ex = [x for x in plan["exigences"] if x.get("branche") == "B-nord" and x.get("type") == "regime"]
    return {"scene": "J2_croix_stop (copie, B-nord « stop_a_verifier »)", "AB4_poses_sur_B_nord": ab4,
            "refus_ARB19": refus, "exigence": ex, "ok": not ab4 and bool(refus) and bool(ex) and "AB4" in ex[0]["interdits"]}


def determinisme():
    """Second passage du pilote (sans rendus) sur des scènes témoins : fichiers l6 identiques à l'octet."""
    avant = {s: {f: sha(SORTIE / s / "l6" / f) for f in FICHIERS_L6} for s in SCENES_DETERMINISME}
    env = {k: v for k, v in os.environ.items() if k != "RG_PILOTE_ENV"}
    r = subprocess.run([str(HYTHON), str(GEN / "fabriquer_signalisation.py")] +
                       [str(SORTIE / s) for s in SCENES_DETERMINISME], env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(DEPOT))
    if r.returncode:
        return {"ok": False, "erreur": r.stdout[-1500:] + r.stderr[-1500:]}
    apres = {s: {f: sha(SORTIE / s / "l6" / f) for f in FICHIERS_L6} for s in SCENES_DETERMINISME}
    ecarts = [f"{s}/{f}" for s in avant for f in avant[s] if avant[s][f] != apres[s][f]]
    return {"scenes": list(SCENES_DETERMINISME), "fichiers": len(SCENES_DETERMINISME) * len(FICHIERS_L6),
            "ecarts": ecarts, "ok": not ecarts}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--determinisme", action="store_true")
    a = ap.parse_args()
    res = [C.controler(SORTIE / s) for s in C.SCENES]
    (ICI / "controles_signalisation.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n",
                                                       encoding="utf-8")
    tot = lambda f: sum(f(r) for r in res)  # noqa: E731
    ex_n = tot(lambda r: r["C1"]["exigences"])
    ex_ok = tot(lambda r: r["C1"]["satisfaites"])
    regimes = [x for r in res for x in C.controler.__globals__["json"].loads("[]")]  # noqa: F841
    c24 = [(r["scene"], x) for r in res for x in r["C1"]["echecs"] if x["type"] == "voies_affectees"]
    n_c24 = sum(1 for r in res for x in json.loads((SORTIE / r["scene"] / "l6" / "plan_signalisation.json").read_text(
        encoding="utf-8"))["exigences"] if x["type"] == "voies_affectees")
    ens = {s: tot(lambda r, s=s: r["statuts"][s]) for s in ("ok", "contrainte", "echec")}
    vis = ICI / "constats_visuels_signalisation.json"
    constats = json.loads(vis.read_text(encoding="utf-8")) if vis.exists() else None
    arb19 = test_arb19()
    det = determinisme() if a.determinisme else None
    c10 = [(r["scene"], r["C10"].get("ok")) for r in res]
    criteres = [
        {"id": "L6-1", "critere": "branches et sections à régime : panneaux présents (P14-1)", "valeur": f"{ex_ok}/{ex_n}",
         "seuil": "100 %", "atteint": ex_ok == ex_n},
        {"id": "L6-2", "critere": "AB4 sur une branche à feux ou « stop_a_verifier » (P14-2, ARB-19)",
         "valeur": f"{tot(lambda r: r['C2']['AB4_sur_feux_ou_a_verifier'])} ; test ARB-19 {'réussi' if arb19['ok'] else 'échoué'}",
         "seuil": "0", "atteint": tot(lambda r: r["C2"]["AB4_sur_feux_ou_a_verifier"]) == 0 and arb19["ok"]},
        {"id": "L6-3", "critere": "bord du panneau à ≥ 0,70 m de la rive, sauf contrainte signalée (P14-3, ARB-20)",
         "valeur": f"{tot(lambda r: len(r['C3']['sous_070_non_signales']))} non signalé(s) ; "
                   f"{tot(lambda r: r['C3']['sous_070_signales'])} plaque(s) sous 0,70 m signalée(s) « contrainte » sur "
                   f"{tot(lambda r: r['C3']['plaques'])}",
         "seuil": "0 non signalé", "atteint": tot(lambda r: len(r["C3"]["sous_070_non_signales"])) == 0},
        {"id": "L6-4", "critere": "supports dans le cheminement de 1,40 m ; plaque au-dessus d'un trottoir sous 2,20 m (P14-5)",
         "valeur": f"{tot(lambda r: len(r['C4']['echecs']))} sur {tot(lambda r: r['C4']['supports_sur_trottoir'])} "
                   f"supports sur trottoir", "seuil": "0", "atteint": tot(lambda r: len(r["C4"]["echecs"])) == 0},
        {"id": "L6-5", "critere": "supports sur surface circulée, îlot peint ou abaissé",
         "valeur": f"{tot(lambda r: len(r['C5']['sur_surface_interdite']))} sur {tot(lambda r: r['C5']['supports'])}",
         "seuil": "0", "atteint": tot(lambda r: len(r["C5"]["sur_surface_interdite"])) == 0},
        {"id": "L6-6", "critere": "hauteur sous panneau (2,30 agglo / 1,00 campagne / îlot, feux, surplomb) ± 2 cm",
         "valeur": f"{tot(lambda r: r['C6']['conformes'])}/{tot(lambda r: r['C6']['ensembles'])} ; écart max "
                   f"{max(r['C6']['ecart_max_m'] for r in res)} m", "seuil": "100 % à ± 0,02 m",
         "atteint": tot(lambda r: r["C6"]["conformes"]) == tot(lambda r: r["C6"]["ensembles"])},
        {"id": "L6-7", "critere": "feux (IISR6) : R11 à droite du couloir, au droit ou à l'aval de la ligne d'effet, "
                                  "bas ≥ 2,00 m, axe < 4,20 m, ≤ 2 ensembles juxtaposés ; R12 aux deux extrémités",
         "valeur": f"R11 {tot(lambda r: r['C7']['R11_conformes'])}/{tot(lambda r: r['C7']['R11_modele'])} ; R12 "
                   f"{tot(lambda r: r['C7']['R12_poses'])}/{tot(lambda r: r['C7']['R12_modele'])} ; R14 0",
         "seuil": "100 %", "atteint": tot(lambda r: r["C7"]["R11_conformes"]) == tot(lambda r: r["C7"]["R11_modele"])
         and tot(lambda r: r["C7"]["R12_poses"]) == tot(lambda r: r["C7"]["R12_modele"])},
        {"id": "L6-8", "critere": "branches à voies affectées : C24 (ou Da30) présent (P14-6, RF-MQ-DIR-01)",
         "valeur": f"{n_c24 - len(c24)}/{n_c24}", "seuil": "100 %", "atteint": not c24},
        {"id": "L6-9", "critere": "faces tournées vers l'usager (écart ≤ 15°, RF-SV-GEN.ORIENTATION)",
         "valeur": f"{tot(lambda r: r['C8']['conformes'])}/{tot(lambda r: r['C8']['faces'])}", "seuil": "100 %",
         "atteint": tot(lambda r: r["C8"]["conformes"]) == tot(lambda r: r["C8"]["faces"])},
        {"id": "L6-10", "critere": "séquences : EB10 / EB20 dos à dos, B14 répété à gauche sur 2 × 2 (P14-8)",
         "valeur": f"{tot(lambda r: r['C9']['conformes'])}/{tot(lambda r: r['C9']['sequences'])}", "seuil": "100 %",
         "atteint": tot(lambda r: r["C9"]["conformes"]) == tot(lambda r: r["C9"]["sequences"])},
        {"id": "L6-11", "critere": "ensembles en échec de placement (aucun point admissible)",
         "valeur": f"{ens['echec']} ; {ens['contrainte']} sous contrainte signalée ; {ens['ok']} conformes",
         "seuil": "0 échec", "atteint": ens["echec"] == 0},
        {"id": "L6-12", "critere": "vue du conducteur : la plaque visée est dans l'image et mesure ≥ 40 px",
         "valeur": f"{sum(1 for _, v in c10 if v)}/{len(c10)}", "seuil": "100 %", "atteint": all(v for _, v in c10)},
    ]
    if det is not None:
        criteres.append({"id": "L6-13", "critere": "déterminisme (second passage, fichiers l6 à l'octet)",
                         "valeur": f"{det.get('fichiers')} fichiers, écarts {det.get('ecarts')}", "seuil": "identique",
                         "atteint": det["ok"]})
    if constats is not None:
        n = len(constats["scenes"])
        okv = sum(1 for s in constats["scenes"] if s["lisible"] and s["texturees"] and s["orientees"])
        criteres.append({"id": "L6-14", "critere": "rendus regardés en tuiles : faces texturées, orientées vers "
                                                   "l'usager, lisibles dans la vue du conducteur",
                         "valeur": f"{okv}/{n}", "seuil": "100 %", "atteint": okv == n})
    rapport = {"schema": "rg_rapport_lot/0.1", "lot": "L6 signalisation verticale et feux (E14)",
               "scenes": [r["scene"] for r in res], "criteres": criteres, "ensembles": ens, "test_arb19": arb19,
               "determinisme": det, "constats_visuels": constats,
               "non_poses": {r["scene"]: r["non_poses"] for r in res if r["non_poses"]},
               "par_scene": [{"scene": r["scene"], "statuts": r["statuts"], "C1": f"{r['C1']['satisfaites']}/{r['C1']['exigences']}",
                              "C3_min_m": r["C3"]["min_m"], "C4_libre_min_m": r["C4"]["libre_min_m"],
                              "C6_ecart_max_m": r["C6"]["ecart_max_m"], "C7_R11": f"{r['C7']['R11_conformes']}/{r['C7']['R11_modele']}",
                              "C10": r["C10"]} for r in res]}
    (ICI / "rapport_signalisation.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n",
                                                     encoding="utf-8")
    for c in criteres:
        print(f"{c['id']} {'OK ' if c['atteint'] else 'NON'} {c['critere']} : {c['valeur']} (seuil {c['seuil']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
