"""Gabarits IISR du dossier 08 au format lu par pj::gabarits_iisr::1.0 (lot L2b) ; Python du système ou hython.

    python recon/generateur/hda/rg_marquages/gabarits_iisr7.py [--verifier]

Source (lecture seule) : D:/DocRoute/08_Marquages_Geometrie_IISR7/marquages_iisr7.json (gabarits normatifs des annexes
B et D de l'IISR 7e partie, 42 polygones ; glyphes des annexes D.3 à D.6, 72 caractères). Les gabarits de
assets/specs/marquages_geometrie.json lus par pj::symbole_iisr::1.0 sont antérieurs aux corrections du dossier 08
(RAB_D et RAB_G diffèrent, TRIANGLE_DOS_ANE et les glyphes manquent) : rg::marquages lit donc ce fichier dérivé, par
l'HDA pj::gabarits_iisr::1.0 réutilisée telle quelle (paramètre « Spécification des marquages »).

Conversion (aucune géométrie nouvelle) : chaque gabarit garde son polygone, ses trous et ses parties (liste -> dict
"p01", "p02"... attendu par le lecteur pj) ; chaque glyphe devient le gabarit GLYPHE_<série>_<caractère> (série V70 :
hauteur 1,50 m, annexes D.3-D.4 ; V70P : 4,00 m, D.5-D.6), repère du glyphe (x = 0 au bord gauche, y = 0 sur la
ligne de base, y vers le haut du caractère = sens de circulation) ; première partie -> polygone et trous, suivantes ->
parties. Écrit gabarits_iisr7_pj.json à côté de ce script (versionné), avec le sha256 de la source ; deux exécutions
donnent les mêmes octets.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
SOURCE = Path(r"D:\DocRoute\08_Marquages_Geometrie_IISR7\marquages_iisr7.json")
SORTIE = ICI / "gabarits_iisr7_pj.json"
SERIES = {"V<=70": "V70", "V>70": "V70P"}


def _anneau(r):
    return [[round(float(x), 4), round(float(y), 4)] for x, y in r]


def convertir(src):
    d = json.loads(src.decode("utf-8"))
    out = {}
    for nom in sorted(d["gabarits"]):
        g = d["gabarits"][nom]
        e = {"polygone": _anneau(g["polygone"]), "famille": g.get("famille", ""), "couleur": g.get("couleur", ""),
             "longueur_m": g.get("longueur_m"), "largeur_m": g.get("largeur_m"), "aire_m2": g.get("aire_m2"),
             "origine": g.get("origine", ""), "boite": g.get("boite"),
             "source": {"texte": " ".join(str(g.get("source", {}).get(k, "")) for k in ("doc", "article")).strip(),
                        "page": g.get("source", {}).get("page")},
             "confiance": g.get("confiance", "")}
        if g.get("trous"):
            e["trous"] = [_anneau(t) for t in g["trous"]]
        parts = g.get("parties")
        if isinstance(parts, list) and parts:
            e["parties"] = {f"p{k + 1:02d}": {"polygone": _anneau(p)} for k, p in enumerate(parts)}
        elif isinstance(parts, dict) and parts:
            e["parties"] = {k: {"polygone": _anneau(v["polygone"]), **({"trous": [_anneau(t) for t in v["trous"]]}
                                                                      if v.get("trous") else {})}
                            for k, v in sorted(parts.items()) if isinstance(v, dict) and "polygone" in v}
        out[nom] = e
    gl = d["glyphes"]
    for serie, code in SERIES.items():
        for car in sorted(gl["series"][serie]):
            c = gl["series"][serie][car]
            parts = c["parties"]
            e = {"polygone": _anneau(parts[0]["exterieur"]), "famille": "glyphe", "couleur": "blanc",
                 "longueur_m": c.get("hauteur_nominale_m"), "largeur_m": c.get("largeur_m"), "aire_m2": c.get("aire_m2"),
                 "origine": "bord gauche du caractère (x = 0), ligne de base (y = 0) ; y vers le haut = sens de circulation",
                 "boite": {"x": [c["boite_m"][0], c["boite_m"][2]], "y": [c["boite_m"][1], c["boite_m"][3]]},
                 "source": {"texte": f"IISR7 118-7 annexe {c.get('annexe', '')}", "page": c.get("page")},
                 "confiance": "moyenne (planche vectorisée, tolérance " + str(gl["tolerance_m"].get(serie)) + " m)"}
            if parts[0].get("trous"):
                e["trous"] = [_anneau(t) for t in parts[0]["trous"]]
            if len(parts) > 1:
                e["parties"] = {f"p{k + 1:02d}": {"polygone": _anneau(p["exterieur"]),
                                                  **({"trous": [_anneau(t) for t in p["trous"]]} if p.get("trous") else {})}
                                for k, p in enumerate(parts[1:])}
            out[f"GLYPHE_{code}_{car}"] = e
    return {"schema": "rg_gabarits_iisr7_pj/0.1",
            "role": "gabarits du dossier 08 (IISR 7e partie) au format de pj::gabarits_iisr (lot L2b, rg::marquages)",
            "source": {"fichier": str(SOURCE).replace("\\", "/"), "sha256": hashlib.sha256(src).hexdigest(),
                       "schema": d.get("schema"), "date": d.get("date")},
            "repere": d["repere"],
            "glyphes": {"repere": gl["repere"], "espacement_caracteres_m": 0.15,
                        "espacement_source": "IISR7 annexe D.2 p. 69 (dossier 08, glyphes.repere)",
                        "series": {v: k for k, v in SERIES.items()}},
            "gabarits": out}


def ecrire():
    src = SOURCE.read_bytes()
    d = convertir(src)
    texte = json.dumps(d, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    if not SORTIE.exists() or SORTIE.read_text(encoding="utf-8") != texte:
        SORTIE.write_text(texte, encoding="utf-8")
    return SORTIE, d


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--verifier", action="store_true", help="vérifie seulement que le fichier versionné est à jour")
    a = ap.parse_args()
    if a.verifier:
        d = convertir(SOURCE.read_bytes())
        ok = SORTIE.exists() and SORTIE.read_text(encoding="utf-8") == json.dumps(d, ensure_ascii=False, indent=1) + "\n"
        print("à jour" if ok else "PÉRIMÉ")
        return 0 if ok else 1
    f, d = ecrire()
    print(f"{f} : {len(d['gabarits'])} gabarits (source sha256 {d['source']['sha256'][:12]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
