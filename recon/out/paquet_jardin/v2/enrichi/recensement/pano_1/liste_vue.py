"""Liste des entités ponctuelles (mobilier, arbres, corrections) projetées dans une vue, avec statut 2026.
Usage : python liste_vue.py <prefixe_vue> (ex. 119d9094_v0) [--tout]"""
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
OBJ = Path("D:/ClaudeCode_RoadCreation/recon/out/paquet_jardin/package/donnees/objets")


def _idx():
    d = {}
    for f in ("mobilier.geojson", "arbres.geojson"):
        for ft in json.load(open(OBJ / f, encoding="utf-8"))["features"]:
            d[ft["properties"]["id"]] = ft["properties"]
    return d


def main():
    nom = sys.argv[1]
    tout = "--tout" in sys.argv
    m = json.load(open(ICI / "preuves" / f"{nom}.json", encoding="utf-8"))
    I = _idx()
    W, H = m["vue"]["taille"]
    print(nom, m["date"][:16], "pose", m["pose_source"], "C", m["pose"][:3])
    for e in sorted(m["entites"], key=lambda e: e["dist_m"]):
        if e["fam"] not in ("mobilier", "arbre", "correction") and not tout:
            continue
        uv = e.get("uv_pied") or e.get("uv")
        if not (0 <= uv[0] < W) and not tout:
            continue
        p = I.get(e["id"].rstrip("*"), {})
        extra = ""
        if e["fam"] == "mobilier":
            extra = f"{p.get('code') or ''} {p.get('lamp_type') or ''} {p.get('sous_type') or ''} conf={p.get('confiance')}"
            if p.get("tetes"):
                extra += " tetes=" + ",".join(f"{t['type']}@{t.get('hauteur_centre_m')}/{t.get('azimut_deg')}" for t in p["tetes"])
        elif e["fam"] == "arbre":
            extra = f"{p.get('essence') or p.get('type')} couronne={p.get('diametre_couronne_m')} src={str(p.get('source'))[:40]}"
        print(f"{e['id']:<28} {e['fam']:<10} d={e['dist_m']:>5} pied={uv} sommet={e.get('uv_sommet')} "
              f"h={e.get('h_m')} | {p.get('statut_2026', '')} | {extra}")


if __name__ == "__main__":
    main()
