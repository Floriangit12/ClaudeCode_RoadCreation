# -*- coding: utf-8 -*-
"""Contrôle de assets/specs/route/regles_route_fr.json (structure, références, sources, pages).

Usage : python -I recon/generateur/outils/verifier_regles_route_fr.py [CHEMIN_JSON]
Code de sortie 0 si aucune erreur (les avertissements n'empêchent pas la sortie 0).
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
DEFAUT = DEPOT / "assets" / "specs" / "route" / "regles_route_fr.json"
CHAMPS = ("id", "famille", "sujet", "condition", "valeurs", "unite", "tolerance", "source", "nature", "confiance")


def pages(valeur):
    """Extrait les numéros de page d'un champ « page » ('45-46', '45 ; 67', 12, 'p. 3-6')."""
    if valeur is None:
        return []
    if isinstance(valeur, int):
        return [valeur]
    s = str(valeur)
    if re.search(r"[A-Za-z_]{3,}", s.replace("p.", "")):  # référence composée (volet 12) : non contrôlée
        return []
    out = []
    for a, b in re.findall(r"(\d+)\s*(?:-\s*(\d+))?", s):
        out.append(int(a))
        if b:
            out.append(int(b))
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAUT
    d = json.loads(chemin.read_text(encoding="utf-8"))
    erreurs, avert, n_ctrl = [], [], 0

    def ctrl(ok, msg, grave=True):
        nonlocal n_ctrl
        n_ctrl += 1
        if not ok:
            (erreurs if grave else avert).append(msg)

    regles = d["regles"]
    ids = [r["id"] for r in regles]
    ctrl(len(ids) == len(set(ids)), "identifiants en double")
    idx = {r["id"]: r for r in regles}
    familles = set(d["familles"])
    natures = set(d["natures"])
    sources = d["sources"]

    for r in regles:
        for c in CHAMPS:
            ctrl(c in r, f"{r.get('id')} : champ {c} absent")
        ctrl(r["famille"] in familles, f"{r['id']} : famille inconnue {r['famille']}")
        ctrl(r["nature"] in natures, f"{r['id']} : nature inconnue {r['nature']}")
        ctrl(r["confiance"] in ("haute", "moyenne", "faible"), f"{r['id']} : confiance {r['confiance']}")
        ctrl(r["source"].get("doc") in sources, f"{r['id']} : source {r['source'].get('doc')} absente du catalogue")
        for e in r.get("sources_secondaires", []):
            ctrl(e.get("doc") in sources, f"{r['id']} : source secondaire {e.get('doc')} absente du catalogue")
        if r["nature"] == "reglementaire":
            ctrl(r["source"].get("page") not in (None, "") or r["source"].get("article") not in (None, ""),
                 f"{r['id']} : règle réglementaire sans page ni article")
        for v in r.get("voir_aussi", []):
            ctrl(v in idx, f"{r['id']} : voir_aussi {v} inconnu")
        for al in r.get("alias", []):
            ctrl(al["id_fusionne"] not in idx, f"{r['id']} : alias {al['id_fusionne']} encore présent comme règle")
            ctrl(d["index_alias"].get(al["id_fusionne"]) == r["id"], f"{r['id']} : alias {al['id_fusionne']} mal indexé")
        ctrl(Path("D:/DocRoute", r["renvoi"]).exists(), f"{r['id']} : renvoi {r['renvoi']} introuvable")

    for k, v in d["index_alias"].items():
        ctrl(v in idx, f"index_alias {k} -> {v} inconnu")
    st = d["statistiques"]
    ctrl(st["regles_lues"] == len(regles) + st["doublons_fusionnes"], "comptes : lues != règles + doublons")
    ids_arb = {a["id"] for a in d["arbitrages"]}
    for a in d["arbitrages"]:
        for rid in a["regles"]:
            ctrl(rid in idx, f"{a['id']} : règle {rid} inconnue")
            ctrl(a["id"] in idx.get(rid, {}).get("arbitrages", []), f"{a['id']} non reporté dans {rid}")
    for p in d["parametres_par_defaut"]:
        for rid in p["regles"]:
            ctrl(rid in idx, f"{p['id']} : règle {rid} inconnue")
        ctrl(p["arbitrage"] is None or p["arbitrage"] in ids_arb, f"{p['id']} : arbitrage inconnu")

    # empreintes des fichiers des volets : la base est-elle à jour ?
    for rel, e in d["volets"].items():
        p = Path("D:/DocRoute") / rel
        h = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        ctrl(h == e["sha256"], f"{rel} modifié depuis la fusion (relancer fusionner_regles.py)", grave=False)

    # pages dans les bornes des PDF locaux
    try:
        import pymupdf
        nb_pages = {}
        for cle, s in sources.items():
            f = s.get("fichier")
            if f and f.lower().endswith(".pdf") and Path(f).is_file():
                try:
                    nb_pages[cle] = pymupdf.open(f).page_count
                except Exception:  # noqa: BLE001
                    pass
        hors = 0
        for r in regles:
            for src in [r["source"]] + r.get("sources_secondaires", []):
                n = nb_pages.get(src.get("doc"))
                if not n:
                    continue
                for pg in pages(src.get("page")):
                    n_ctrl += 1
                    if not 1 <= pg <= n:
                        hors += 1
                        avert.append(f"{r['id']} : page {pg} hors de {src.get('doc')} ({n} p.)")
        print(f"pages contrôlées dans {len(nb_pages)} PDF locaux ; hors bornes : {hors}")
    except ImportError:
        avert.append("PyMuPDF absent : bornes de pages non contrôlées")

    print(f"{n_ctrl} contrôles, {len(erreurs)} erreur(s), {len(avert)} avertissement(s)")
    for e in erreurs[:50]:
        print("ERREUR", e)
    for a in avert[:50]:
        print("AVERT ", a)
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
