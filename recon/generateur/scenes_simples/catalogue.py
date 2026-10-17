# -*- coding: utf-8 -*-
"""Pilote du catalogue de routes simples (lot « catalogue », étape 1 du générateur).

Pour chaque description `S??_*.yaml` de ce dossier :
  1. lecture et calcul (`description.py`) : géométrie de contrôle, mesures, contrôles de conformité ;
  2. plan coté SVG (`plan_svg.py`) → `plans/<scene>_<nom>.svg` (versionné, déterministe) ;
  3. rendu PNG du SVG (PyMuPDF) et vues de détail ×3 autour des points singuliers →
     `recon/out/generateur/catalogue/{plans_png,details}/` (non versionné) ;
  4. découpe en tuiles natives (`recon/pcg/vision/decoupe.py image`) → `recon/out/generateur/catalogue/tuiles/` ;
puis écrit `recon/generateur/validation/rapport_catalogue.json` et `RAPPORT_catalogue.md`.

    python -B recon/generateur/scenes_simples/catalogue.py                    # tout
    python -B recon/generateur/scenes_simples/catalogue.py --sans-png         # SVG et rapport seulement
    python -B recon/generateur/scenes_simples/catalogue.py --verifier-determinisme

Le rapport ne contient aucune photo. Les constats visuels (tuiles regardées) viennent de `constats_visuels.json`,
écrit à la main après lecture des tuiles, et sont recopiés tels quels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN))

import regles  # noqa: E402
from description import FORMAT, Scene, _r  # noqa: E402
from plan_svg import Plan, ecrire_svg  # noqa: E402

PLANS = ICI / "plans"
SORTIE = DEPOT / "recon" / "out" / "generateur" / "catalogue"
VALIDATION = GEN / "validation"
DECOUPE = DEPOT / "recon" / "pcg" / "vision" / "decoupe.py"
TMP = GEN / "tmp" / "catalogue"
ZOOM = 3.0                              # vues de détail : 60 px/m
FENETRE_DETAIL_M = 17.0                 # longueur d'une vue de détail (≤ 1092 px à 60 px/m)
SCENES_ATTENDUES = [f"S{i:02d}" for i in range(1, 13)]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def descriptions() -> list[Path]:
    return sorted(p for p in ICI.glob("S[0-9][0-9]_*.yaml"))


def fenetres_detail(sc: Scene) -> list[tuple[float, float]]:
    """Fenêtres [s0, s1] des vues de détail : autour des points singuliers, sinon début et fin du tronçon."""
    pts = sorted({c["s"] for c in sc.cotes_s} | {f["s"] for f in sc.figurines} |
                 ({sc.avancees[0]["s"]} if sc.avancees else set()) | ({sc.arbres[0]["s"]} if sc.arbres else set()))
    pts = [p for p in pts if 0.0 <= p <= sc.L]
    fen = []
    if not pts:
        return [(0.0, FENETRE_DETAIL_M)]
    debut = pts[0]
    for p in pts:
        if p - debut > FENETRE_DETAIL_M - 4.0:
            fen.append(debut)
            debut = p
    fen.append(debut)
    out = []
    for d in fen:
        s0 = max(0.0, min(d - 2.0, sc.L - FENETRE_DETAIL_M))
        out.append((_r(s0, 3), _r(min(sc.L, s0 + FENETRE_DETAIL_M), 3)))
    return sorted(set(out))[:6]


def rendre_png(svg: Path, png: Path, plan: Plan | None = None, fenetre=None, zoom=1.0) -> dict:
    import pymupdf
    doc = pymupdf.open(str(svg))
    page = doc[0]
    mat = pymupdf.Matrix(zoom, zoom)
    if fenetre is None:
        pix = page.get_pixmap(matrix=mat, alpha=False)
    else:
        s0, s1 = fenetre
        sc = plan.sc
        xs, ys = [], []
        for s in (s0, 0.5 * (s0 + s1), s1):
            for i in (0, len(sc.limites) - 1):
                x, y = plan.px(s, sc.t_limite(i, s) + (1.0 if i == 0 else -1.0))
                xs.append(x)
                ys.append(y)
        clip = pymupdf.Rect(min(xs), min(ys), max(xs), max(ys))
        pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(png))
    return {"png": str(png.relative_to(DEPOT)).replace("\\", "/"), "px": [pix.width, pix.height]}


def decouper(png: Path, dossier: Path) -> list[str]:
    if dossier.exists():
        shutil.rmtree(dossier)
    r = subprocess.run([sys.executable, "-B", str(DECOUPE), "image", str(png), str(dossier), "--recouvrement", "0.2"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(r.stderr)
    return sorted(str(p.relative_to(DEPOT)).replace("\\", "/") for p in dossier.glob("*.png"))


def traiter(chemin: Path, plans: Path, png: bool) -> dict:
    sc = Scene(chemin)
    svg = plans / f"{sc.id}_{sc.nom}.svg"
    infos = ecrire_svg(sc, svg)
    res = sc.resume()
    # chemin repo-relatif pour le catalogue ; relatif au dossier de sortie pour les exécutions de contrôle
    rel = svg.relative_to(DEPOT) if plans == PLANS else svg.relative_to(plans.parent)
    res["plan"] = {"svg": str(rel).replace("\\", "/"),
                   "largeur_px": infos["largeur_px"], "hauteur_px": infos["hauteur_px"],
                   "echelle_px_m": infos["echelle_px_m"], "sha256": sha256(svg)}
    if png:
        plan = Plan(sc)
        rendus, tuiles = [], []
        p = SORTIE / "plans_png" / f"{sc.id}.png"
        rendus.append(rendre_png(svg, p))
        tuiles += decouper(p, SORTIE / "tuiles" / sc.id / "plan")
        for k, fen in enumerate(fenetres_detail(sc)):
            pd = SORTIE / "details" / f"{sc.id}_detail_{k}.png"
            r = rendre_png(svg, pd, plan, fen, ZOOM)
            r["fenetre_s"] = list(fen)
            rendus.append(r)
            tuiles += decouper(pd, SORTIE / "tuiles" / sc.id / f"detail_{k}")
        res["rendus"] = rendus
        res["tuiles"] = tuiles
    return res


def critere(cid, valeur, seuil, atteint, note=None) -> dict:
    d = {"id": cid, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint)}
    if note:
        d["note"] = note
    return d


def rapport(scenes: list[dict], determinisme: dict | None) -> dict:
    constats_p = ICI / "constats_visuels.json"
    constats = json.loads(constats_p.read_bytes().decode("utf-8")) if constats_p.exists() else {}
    ids = [s["scene"] for s in scenes]
    bloquants = [(s["scene"], c) for s in scenes for c in s["controles"] if c["bloquant"] and not c["atteint"]]
    non_bloquants = [(s["scene"], c) for s in scenes for c in s["controles"] if not c["bloquant"] and not c["atteint"]]
    att_ok = sum(1 for s in scenes for c in s["controles"] if c["id"] == "attendus" and c["atteint"])
    reg_ok = sum(1 for s in scenes for c in s["controles"] if c["id"] == "regles_citees" and c["atteint"])
    n_courbes = sum(1 for s in scenes if s["mesures"].get("rayons"))
    longueurs_ok = sum(1 for s in scenes if 80 - 1e-9 <= s["longueur_m"] <= 120 + 1e-9)
    regardees = constats.get("tuiles_regardees", {})
    n_plans_vus = sum(1 for i in ids if regardees.get(i))
    crit = [
        critere("C1_scenes", f"{len(scenes)}/12 ({', '.join(ids)})", "12 descriptions S01-S12", ids == SCENES_ATTENDUES),
        critere("C2_lecture", f"{len(scenes)}/{len(scenes)} lues sans erreur ({FORMAT})", "100 %", True),
        critere("C3_longueurs", f"{longueurs_ok}/{len(scenes)} dans [80 ; 120] m", "100 %", longueurs_ok == len(scenes)),
        critere("C4_une_courbe", f"{n_courbes} scène(s) avec courbe", "exactement 1", n_courbes == 1),
        critere("C5_regles_citees", f"{reg_ok}/{len(scenes)} scènes dont toutes les règles citées existent",
                "100 %", reg_ok == len(scenes)),
        critere("C6_attendus", f"{att_ok}/{len(scenes)} lignes « attendus » = mesures calculées", "100 %",
                att_ok == len(scenes)),
        critere("C7_conformite", f"{sum(len(s['controles']) for s in scenes) - len(bloquants) - len(non_bloquants)}"
                f"/{sum(len(s['controles']) for s in scenes)} contrôles atteints ; {len(bloquants)} échec(s) bloquant(s) ;"
                f" {len(non_bloquants)} avertissement(s)", "0 échec bloquant", not bloquants,
                note="; ".join(f"{i} {c['id']} ({c['valeur']} / {c['seuil']})" for i, c in bloquants + non_bloquants)
                or None),
        critere("C8_plans_svg", f"{sum(1 for s in scenes if s.get('plan'))}/{len(scenes)} plans SVG", "100 %",
                all(s.get("plan") for s in scenes)),
        critere("C9_tuiles_regardees", f"{n_plans_vus}/{len(scenes)} scènes dont les tuiles ont été regardées",
                "100 %", n_plans_vus == len(scenes), note="constats_visuels.json (lecture humaine des tuiles)"),
    ]
    if determinisme is not None:
        crit.append(critere("C10_determinisme", f"{determinisme['identiques']}/{determinisme['fichiers']} fichiers "
                            "identiques à l'octet entre deux exécutions", "100 %",
                            determinisme["identiques"] == determinisme["fichiers"]))
    return {
        "schema": "rapport_lot/0.1", "lot": "catalogue", "date": "2026-10-17",
        "objet": "catalogue de routes simples en description simple (YAML) + plans cotés SVG + attendus",
        "format_description": FORMAT, "format_doc": "recon/generateur/scenes_simples/FORMAT_PROPOSE.md",
        "regles": regles.empreinte(),
        "criteres": crit,
        "statut": "ok" if all(c["atteint"] for c in crit) else "partiel",
        "scenes": [{k: v for k, v in s.items() if k not in ("controles",)} | {"controles": s["controles"]}
                   for s in scenes],
        "constats_visuels": constats,
        "determinisme": determinisme,
    }


def ecrire_json(p: Path, d: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes((json.dumps(d, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def generer(plans: Path, sortie_json: Path | None, png: bool) -> list[dict]:
    scenes = [traiter(p, plans, png) for p in descriptions()]
    if sortie_json is not None:
        ecrire_json(sortie_json, {"scenes": [{k: v for k, v in s.items() if k not in ("rendus", "tuiles")}
                                             for s in scenes]})
    return scenes


def verifier_determinisme() -> dict:
    """Deux exécutions dans deux processus distincts → SVG et JSON identiques à l'octet."""
    sorties = []
    for nom in ("det_a", "det_b"):
        d = TMP / nom
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        r = subprocess.run([sys.executable, "-B", str(Path(__file__)), "--interne", str(d)], capture_output=True,
                           text=True, encoding="utf-8")
        if r.returncode != 0:
            raise RuntimeError(r.stderr)
        sorties.append(d)
    a, b = sorties
    fichiers = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    ident = sum(1 for f in fichiers if (b / f).exists() and sha256(a / f) == sha256(b / f))
    return {"fichiers": len(fichiers), "identiques": ident,
            "empreintes": {str(f).replace("\\", "/"): sha256(a / f) for f in fichiers}}


def markdown(r: dict) -> str:
    L = []
    L.append("# Rapport du lot « catalogue » : routes simples en description simple\n")
    L.append(f"*`recon/generateur/validation/RAPPORT_catalogue.md` — généré par "
             f"`recon/generateur/scenes_simples/catalogue.py` ({r['date']}). Statut : **{r['statut']}**.*\n")
    L.append("Douze tronçons droits de 80 à 120 m (une courbe), chacun décrit en YAML au format "
             f"`{r['format_description']}` (`scenes_simples/FORMAT_PROPOSE.md`), avec un plan coté SVG généré "
             "(`scenes_simples/plans/`) et une ligne `attendus` comparée aux mesures recalculées par les règles de "
             f"`regles_route_fr.json` (SHA-256 `{r['regles']['sha256'][:16]}…`, {r['regles']['regles']} règles).\n")
    L.append("## Critères\n")
    L.append("| Critère | Valeur | Seuil | Atteint |")
    L.append("|---|---|---|---|")
    for c in r["criteres"]:
        L.append(f"| {c['id']} | {c['valeur']} | {c['seuil']} | {'oui' if c['atteint'] else '**non**'} |")
    L.append("")
    L.append("## Scènes\n")
    L.append("| Scène | Titre | L (m) | Emprise (m) | Contrôles | Attendus |")
    L.append("|---|---|---|---|---|---|")
    for s in r["scenes"]:
        ok = sum(1 for c in s["controles"] if c["atteint"])
        att = next(c for c in s["controles"] if c["id"] == "attendus")
        L.append(f"| {s['scene']} | {s['titre']} | {s['longueur_m']:g} | {s['mesures']['largeur_emprise']:g} | "
                 f"{ok}/{len(s['controles'])} | {att['valeur']} |")
    L.append("")
    for s in r["scenes"]:
        L.append(f"### {s['scene']} — {s['titre']}\n")
        L.append(f"- Fichier : `scenes_simples/{s['fichier']}` ; plan : `{s['plan']['svg']}` "
                 f"({s['plan']['largeur_px']} × {s['plan']['hauteur_px']} px, {s['plan']['echelle_px_m']:g} px/m).")
        prof = " | ".join(f"{b['id']} {b['type']} {b['largeur'] if not isinstance(b['largeur'], list) else 'loi'}"
                          for b in s["profil"])
        L.append(f"- Profil (gauche → droite) : {prof}.")
        L.append(f"- Mesures : `{json.dumps(s['mesures'], ensure_ascii=False)}`.")
        ko = [c for c in s["controles"] if not c["atteint"]]
        if ko:
            for c in ko:
                L.append(f"- {'Échec' if c['bloquant'] else 'Avertissement'} `{c['id']}` : {c['sujet']} = "
                         f"{c['valeur']} (seuil {c['seuil']}) — {c['regle'] or ''}")
        cv = (r.get("constats_visuels") or {}).get("scenes", {}).get(s["scene"])
        if cv:
            L.append(f"- Constat visuel (tuiles regardées) : {cv}")
        L.append("")
    lim = (r.get("constats_visuels") or {}).get("regles_a_signaler")
    if lim:
        L.append("## Règles manquantes, imprécises ou à corriger (signalées, non modifiées)\n")
        for x in lim:
            L.append(f"- {x}")
        L.append("")
    coord = (r.get("constats_visuels") or {}).get("coordination_L0")
    if coord:
        L.append("## Coordination avec le lot L0 (compilateur de description)\n")
        for x in coord:
            L.append(f"- {x}")
        L.append("")
    if r.get("determinisme"):
        d = r["determinisme"]
        L.append(f"## Déterminisme\n\n{d['identiques']}/{d['fichiers']} fichiers (SVG + JSON) identiques à l'octet "
                 "entre deux exécutions dans deux processus.\n")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sans-png", action="store_true")
    ap.add_argument("--verifier-determinisme", action="store_true")
    ap.add_argument("--interne", help=argparse.SUPPRESS)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if a.interne:
        d = Path(a.interne)
        generer(d / "plans", d / "scenes.json", png=False)
        return
    det = verifier_determinisme() if a.verifier_determinisme else None
    scenes = generer(PLANS, None, png=not a.sans_png)
    r = rapport(scenes, det)
    ecrire_json(VALIDATION / "rapport_catalogue.json", r)
    (VALIDATION / "RAPPORT_catalogue.md").write_bytes(markdown(r).encode("utf-8"))
    for c in r["criteres"]:
        print(f"{'OK ' if c['atteint'] else 'NON'} {c['id']} : {c['valeur']} (seuil {c['seuil']})")
    print(f"statut : {r['statut']}")


if __name__ == "__main__":
    main()
