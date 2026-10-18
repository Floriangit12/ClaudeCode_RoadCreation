"""Rapport JSON du lot L5, partie giratoires : rejoue validation/controler_giratoires.py sur G1-G3 et regroupe les
critères par identifiant (atteint si toutes les scènes l'atteignent), avec les constats visuels des planches et le
contrôle de déterminisme passés en arguments (fichier JSON écrit par l'agent après lecture des tuiles).

    python recon/generateur/validation/faire_rapport_giratoires.py [--constats validation/constats_visuels_giratoires.json]
                                                                   [--determinisme "identique (N fichiers)"]
Écrit validation/rapport_giratoires.json et validation/controles_giratoires.json.
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import controler_giratoires as CG  # noqa: E402

NOMS = {
    "GI-01": "anneau de largeur uniforme (± 1 cm) et égale à la chaussée annulaire du modèle",
    "GI-02": "déflexion < 100 m sur chaque traversée (RF-GV-GIR-008)",
    "GI-03": "îlots séparateurs = ACI tableau 2 (H, B, d, r ± 1 cm ; retrait 1 m) ; mini : 0,85-2,00 m (RF-GV-GIR-016)",
    "GI-04": "refuge ≥ 2,00 m au droit du passage (RF-GV-GIR-014)",
    "GI-05": "couronne franchissable : vue ≤ 0,03 m, pente 4-6 %, matériau contrasté (RF-GV-GIR-006)",
    "GI-06": "îlot central hors agglomération sans arbre ni obstacle agressif (ACI p. 84)",
    "GI-07": "passages à 2-5 m de la ligne CÉDEZ (RF-GV-GIR-015, ARB-02)",
    "GI-08": "entrées et sorties tangentes : rupture ≤ 0,5°, rayons Re / Rs / anneau ± 1 cm (RF-GV-GIR-003)",
    "GI-09": "ligne CÉDEZ sur chaque entrée (RF-GV-GIR-024)",
    "GI-10": "mini-giratoire : dôme 10-15 cm (bus ≤ 12), relief 1-3 cm, contour T'2 3u (RF-GV-GIR-016, RF-MQ-GIR-02)",
    "GI-11": "sol étanche : raccords ≤ 1 mm, 0 bord libre hors extérieur, îlots posés sans bord libre visible",
    "GI-12": "abaissés des refuges avec BEV (DEF-031)",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--constats")
    ap.add_argument("--determinisme", default="")
    a = ap.parse_args()
    scenes = [CG.controler_scene(CG.SORTIE / s) for s in CG.SCENES]
    (ICI / "controles_giratoires.json").write_text(json.dumps({"schema": "rg_controles_giratoires/0.1", "scenes": scenes},
                                                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    par = {}
    for s in scenes:
        for c in s["criteres"]:
            par.setdefault(c["id"], []).append((s["scene"], c))
    criteres = []
    for cid in sorted(par):
        lst = par[cid]
        criteres.append({"id": f"{cid} {NOMS.get(cid, '')}",
                         "valeur": " | ".join(f"{sc.split('_')[0]} : {c['valeur']}" for sc, c in lst),
                         "seuil": lst[0][1]["seuil"], "atteint": all(c["atteint"] for _, c in lst),
                         "scenes": [sc for sc, _ in lst]})
    if a.constats:
        cv = json.loads(Path(a.constats).read_text(encoding="utf-8"))
        criteres.append({"id": "GI-13 planches de rendu regardées en tuiles natives (G1 : 3 vues ; G2, G3 : 2 vues)",
                         "valeur": f"{cv.get('regardees', 0)} / 3 planches ; {cv.get('vues', 0)} vues",
                         "seuil": "3 / 3 planches ; 7 vues", "atteint": cv.get("regardees", 0) == 3 and cv.get("vues", 0) == 7})
    if a.determinisme:
        criteres.append({"id": "GI-14 déterminisme (2 scènes, deux processus, une fois en fin de lot)",
                         "valeur": a.determinisme, "seuil": "identique", "atteint": a.determinisme.startswith("identique")})
    out = {"lot": "L5 giratoires", "date": "2026-10-18", "criteres": criteres,
           "scenes": [{"scene": s["scene"], "mesures": s["mesures"]} for s in scenes],
           "detail": "validation/controles_giratoires.json ; recon/out/generateur/<scene>/l5/giratoires.json"}
    (ICI / "rapport_giratoires.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for c in criteres:
        print(("OK  " if c["atteint"] else "NON ") + c["id"] + " : " + c["valeur"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
