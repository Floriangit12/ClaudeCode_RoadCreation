"""Rapport du lot « ouvrages » (L8 / E07) : rejoue le contrôle indépendant (controler_ouvrages.py), vérifie la
rétrocompatibilité du compilateur (descriptions existantes recompilées, comparées aux modèles déjà produits) et
assemble validation/rapport_ouvrages.json avec les constats visuels (constats_visuels_ouvrages.json, écrits en
regardant les tuiles natives des rendus).

    python recon/generateur/validation/faire_rapport_ouvrages.py [--sans-retro]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SORTIE = DEPOT / "recon" / "out" / "generateur"
TMP = GEN / "tmp" / "ouvrages" / "retro"
sys.path.insert(0, str(ICI))
import controler_ouvrages as CO  # noqa: E402


def retro():
    """Descriptions existantes (S, A, J, G, M) recompilées dans tmp/ : modèle identique à l'octet à celui de
    recon/out/generateur/<scène>/ ? (les modèles plus anciens que les dernières évolutions d'autres lots sont signalés)."""
    res = []
    for motif in ("scenes_simples/S*.yaml", "scenes_autoroutes/A*.yaml", "scenes_carrefours/J*.yaml",
                  "scenes_giratoires/G*.yaml", "scenes_meylan/M*.yaml"):
        for f in sorted(GEN.glob(motif)):
            out = TMP / f.stem
            subprocess.run([sys.executable, "-B", str(GEN / "description" / "description_vers_modele.py"), str(f),
                            "--sortie", str(out)], capture_output=True, text=True)
            m = json.loads((out / "modele_voie.json").read_text(encoding="utf-8"))
            zone = m["meta"]["zone"]
            ref = SORTIE / zone / "modele_voie.json"
            ident = ref.exists() and ref.read_bytes() == (out / "modele_voie.json").read_bytes()
            res.append({"description": f"{f.parent.name}/{f.name}", "identique": ident,
                        "reference": str(ref.relative_to(DEPOT)).replace("\\", "/") if ref.exists() else None,
                        "a_ouvrages": "ouvrages" in m})
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-retro", action="store_true")
    a = ap.parse_args()
    scenes = []
    for s in CO.SCENES:
        dsc = SORTIE / s
        if (dsc / "ouvrages" / "maillage_ouvrages.npz").exists():
            CO._CACHE.clear()
            scenes.append(CO.controler_scene(dsc))
    f_const = ICI / "constats_visuels_ouvrages.json"
    constats = json.loads(f_const.read_text(encoding="utf-8")) if f_const.exists() else {}
    rendus = {}
    for s in CO.SCENES:
        m = SORTIE / s / "rendus" / "manifest_rendus.json"
        if m.exists():
            d = json.loads(m.read_text(encoding="utf-8"))
            rendus[s] = {"images": d["images"], "planche": d["planche"], "tuiles": d["tuiles"], "L1": d["L1"]}
    rap = {"schema": "rg_rapport_lot/0.1", "lot": "ouvrages (L8 du plan, E07 de la chaîne)", "date": "2026-10-22",
           "scenes": scenes, "rendus": rendus, "constats_visuels": constats,
           "retrocompatibilite": None if a.sans_retro else retro()}
    crit = {}
    for s in scenes:
        for k, v in s["criteres"].items():
            crit.setdefault(k, []).append(bool(v["atteint"]))
    rap["synthese"] = {k: all(v) for k, v in crit.items()}
    rap["tous_atteints"] = all(rap["synthese"].values()) and bool(scenes)
    (ICI / "rapport_ouvrages.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1, default=CO._jsn) + "\n",
                                               encoding="utf-8")
    print(json.dumps(rap["synthese"], ensure_ascii=False))
    if rap["retrocompatibilite"]:
        n = len(rap["retrocompatibilite"])
        k = sum(x["identique"] for x in rap["retrocompatibilite"])
        print(f"rétrocompatibilité : {k}/{n} modèles identiques à l'octet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
