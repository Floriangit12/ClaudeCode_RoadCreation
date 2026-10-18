"""Travailleur de la comparaison v2 (lancé en sous-processus par etapes_v2.py ; un lot de tâches par processus) :

    python recon/generateur/comparaison/pose_lot.py <tache.json>

- « verticales » : vues.verticale_360 de photos 360° (image HD réduite à 2 880 px) -> {id: [u, n, résidu]} ;
- « poses » : comparer_multivues.poser_vue pour des vues de la sélection -> liste d'enregistrements de poses.json ;
- « planches » : etapes_v2.planche_vue pour des vues -> liste de gabarits d'écarts et vignettes.
Le résultat est écrit dans le fichier `resultat` de la tâche. Le modèle est relu dans chaque processus (lecture seule).
"""
import json
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))


def main(f_tache):
    tache = json.loads(Path(f_tache).read_text(encoding="utf-8"))
    from PIL import Image
    import vues as V
    out = None
    if tache["mode"] == "verticales":
        out = {}
        for pid, jpg in tache["photos"].items():
            im = Image.open(jpg).convert("RGB")
            im = im.resize((2880, 1440), Image.LANCZOS) if im.size[0] > 2880 else im
            r = V.verticale_360(im)
            out[pid] = None if r is None else [[float(v) for v in r[0]], int(r[1]), float(r[2])]
            print("verticale", pid[:8], None if r is None else round(float(r[2]), 2), flush=True)
    else:
        import comparer_multivues as CM
        import geo
        import modele as MO
        m = MO.Modele(tache["modele"])
        A = geo.Ancrage(*tache["ancrage"]["origine_l93"], tache["ancrage"]["azimut_grille_axe_x_deg"])
        P, T, typ = m.aretes()
        if tache["mode"] == "poses":
            out = []
            for v in tache["vues"]:
                r = v["verticale"]
                r = None if r is None else (np.asarray(r[0], dtype=np.float64), int(r[1]), float(r[2]))
                out.append(CM.poser_vue(v["ph"], v["jpg"], r, v["coherence"], m, A, P, T, typ, tache["dossier_vues"],
                                        cle=v["ph"]["cle"]))
        elif tache["mode"] == "planches":
            import etapes_v2 as E2
            out = []
            for v in tache["vues"]:
                out.append(E2.planche_vue(tache["site"], v["ph"], v["po"], m, P, T, typ, tache["dossiers"],
                                          tache.get("ancien", {}).get(v["ph"]["cle"]), tache["genre"]))
    Path(tache["resultat"]).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
