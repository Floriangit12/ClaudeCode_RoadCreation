"""Inventaire des occurrences câblées sur l'état 2026 dans recon/pcg (instantané figé).

Usage : python scanner.py RACINE_INSTANTANE SORTIE_CSV SORTIE_JSON
Lecture seule. Catégories = motifs regex ; une ligne peut porter plusieurs catégories.
"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

CATS = collections.OrderedDict([
    ("SORTIE_V2", r"recon/out/paquet_jardin/v2(?![_\w])|out/paquet_jardin/v2[\"'/]|[\"']v2[\"']\s*/|/\s*[\"']v2[\"']|paquet_jardin/v2\b"),
    ("GAM_ETAT_2026", r"etat_2026|levé GAM 2026|leve_gam_2026|GAM 2026|gam_2026"),
    ("V1_2026", r"surfaces_2026|marquages_2026|lanes_2026|relief_zones_2026|manoeuvres_2026|validation_2026|paquet_jardin_2026|chaussee_2026|autorisee_2026"),
    ("MNT_2026", r"heightmap_3025|MNT 2026|mnt_2026|modele_2026|nivellement_2026|dtm_2026|sol 2026|MNT\(\)"),
    ("PLAN_2025", r"plan_projet_2025|plan2025|plan projet 2025|plan 2025|plan_cad|PLAN\s*="),
    ("ORTHO_2022", r"ortho5cm_2022|ortho2022|ortho 2022|ORTHO_2022|PCRS 5 cm"),
    ("PCRS_GAMTOPO", r"gam_topo_sol|_pcrs\b|_pcrs\.|pcrs2019|PCRS 2019"),
    ("CHRONO_TRAVAUX", r"zone_travaux|travaux|creee_apres_2021|modifiee_2025|modifie_2025|refait_2025|resurface_2025|neuf_2025|construit_2023_2024|2025-06-23|2025-12-05|2026-01-30|apres_travaux|avant_travaux|post[ée]rieur|ant[ée]rieur|valide_2026|valide_a|valide_de|DEBUT_TRAVAUX|FIN_TRAVAUX"),
    ("DATE_ETAT", r"date_etat|\"2026-10\"|'2026-10'|octobre 2026|PJ_2026|niveau_2026|annee_cible|date_cible|ETAT_CIBLE|etat_cible"),
    ("TERRAIN_2026", r"terrain2026|terrain_2026|photo_utilisateur"),
    ("COUVERTURE_COEUR", r"couverture_stricte|couverture stricte|strict|\bcoeur\b|\bcœur\b"),
])
RX = {k: re.compile(v, re.I) for k, v in CATS.items()}


def module_de(rel):
    p = rel.split("/")
    return p[0] if len(p) > 1 else "(racine)"


def main(racine, out_csv, out_json):
    racine = Path(racine)
    rows = []
    for f in sorted(racine.rglob("*")):
        if "__pycache__" in f.parts or not f.is_file():
            continue
        if f.suffix not in (".py", ".md", ".json", ".vex", ".txt"):
            continue
        if f.stat().st_size > 2_000_000:
            continue
        rel = f.relative_to(racine).as_posix()
        try:
            lignes = f.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            lignes = f.read_text(encoding="latin-1").splitlines()
        for i, l in enumerate(lignes, 1):
            cats = [k for k, r in RX.items() if r.search(l)]
            if cats:
                rows.append({"module": module_de(rel), "fichier": "recon/pcg/" + rel, "ligne": i,
                             "categories": "|".join(cats), "extrait": l.strip()[:200]})
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["module", "fichier", "ligne", "categories", "extrait"])
        w.writeheader()
        w.writerows(rows)
    par_mod = collections.defaultdict(collections.Counter)
    par_fic = collections.defaultdict(collections.Counter)
    for r in rows:
        for c in r["categories"].split("|"):
            par_mod[r["module"]][c] += 1
            par_fic[r["fichier"]][c] += 1
    res = {"categories": CATS, "n_lignes": len(rows),
           "n_fichiers": len(par_fic),
           "par_module": {m: dict(c) for m, c in sorted(par_mod.items())},
           "par_fichier": {f: dict(c) for f, c in sorted(par_fic.items(), key=lambda kv: -sum(kv[1].values()))}}
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    sys.stdout.reconfigure(encoding="utf-8")
    print(len(rows), "lignes ;", len(par_fic), "fichiers")
    for m, c in sorted(par_mod.items()):
        print(m, dict(c))


if __name__ == "__main__":
    main(*sys.argv[1:4])
