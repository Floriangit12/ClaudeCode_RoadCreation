# -*- coding: utf-8 -*-
"""Rapport du lot « correction » (corrections après le contrôle adverse de l'étape 1, puis décision de l'utilisateur du
17/10/2026 : à l'étape 1, la route seule) : rassemble les mesures avant / après et écrit rapport_correction.json et
RAPPORT_correction.md.

    python recon/generateur/validation/faire_rapport_correction.py [--journal recon/generateur/tmp/etape1_route/fabrication.log]

Entrées (déjà produites, aucune refabrication ici, sauf la recompilation des cas piégés, rapide) : sorties
recon/out/generateur/<scène>/ (fabrication complète par tmp/etape1_route/fabriquer_tout.sh : un processus par scène,
--l2b --rendus --verifier-determinisme), controles_correction (controler_correction.py, après) et
tmp/correction/controles_avant.json (mêmes mesures sur les sorties d'avant la correction), rapports des lots L0, L2, L2b
régénérés, tests (validation/tests_*_L0.json), cas piégés de la relecture adverse (tmp/verif/adv, recompilés dans
tmp/etape1_route/adv), refus du pilote (tmp/etape1_route/refus_A9.log), planches rendu | photo,
constats_visuels_etape1.json (revue de toutes les tuiles natives des rendus refaits), regles_demandees_correction.json.

Critères « reportés à l'étape 2 » : la décision de l'utilisateur sort le décor et la végétation de l'étape 1 (arbres,
herbe de décor) ; leurs critères sont gardés, mesurés quand c'est possible, et exclus du statut (ni atteints ni
abaissés).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
OUT = DEPOT / "recon" / "out" / "generateur"
TMPC = GEN / "tmp" / "correction"
TMPE = GEN / "tmp" / "etape1_route"
TMP2 = GEN / "tmp" / "second_controle"            # correction après le second contrôle (passe unique du code final)
sys.path.insert(0, str(ICI))
import controler_correction as CC  # noqa: E402

CATALOGUE = [f"S{k:02d}" for k in range(1, 13)]
MEYLAN = ["S_M24", "S_M27", "S_M20"]
DECISION = ("« il ne doit pas générer la montagne : il doit générer les routes, la chaussée, etc. dans un premier temps ; "
            "la végétation, c'est dans un deuxième temps » (utilisateur, 17/10/2026)")


def _j(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _r(x, n=3):
    return None if x is None else round(float(x), n)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def journal(f):
    out, sc = {}, None
    if not f or not Path(f).exists():
        return out
    for ligne in Path(f).read_text(encoding="utf-8", errors="replace").splitlines():
        if ligne.startswith("=== ") and ligne.endswith(".yaml"):
            sc = Path(ligne[4:].strip()).stem
        elif ligne.startswith("déterminisme") and sc:
            out[sc] = ligne.split(":", 1)[1].strip()
        elif ligne.startswith("=== code") and sc:
            out.setdefault(sc + "#code", ligne.split()[2])
    return out


def recompiler_cas_pieges():
    """Cas piégés de la relecture adverse (tmp/verif/adv/A*.yaml, lus sans modification) recompilés par le Python du
    système dans tmp/etape1_route/adv/<cas>/ (compilation.json si la description est acceptée)."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(("PYTHON", "HOUDINI", "HFS", "H_"))}
    env["PYTHONIOENCODING"] = "utf-8"
    res = []
    for y in sorted((GEN / "tmp" / "verif" / "adv").glob("A*.yaml")):
        d = TMP2 / "adv" / y.stem
        if d.exists():
            for f in d.iterdir():
                f.unlink()
        d.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, str(GEN / "description" / "description_vers_modele.py"), str(y), "--sortie",
                            str(d)], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                           cwd=str(DEPOT))
        (TMP2 / "adv" / f"{y.stem}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
        f = d / "compilation.json"
        if r.returncode == 0 and f.exists():
            c = _j(f)
            res.append({"cas": y.stem, "compile": True, "non_conformites_bloquantes": len(c.get("non_conformites", []))})
        else:
            res.append({"cas": y.stem, "compile": False})
    return res


def constats():
    for nom in ("constats_visuels_etape1.json", "constats_visuels_L2b.json"):
        f = ICI / nom
        if f.exists():
            return nom, _j(f)
    return None, {"constats": []}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--journal", default=str(TMP2 / "fabrication.log"))
    a = ap.parse_args()
    scenes = CATALOGUE + MEYLAN
    apres = {n: CC.controler(OUT / n) for n in scenes if (OUT / n / "l2" / "manifest_l2.json").exists()}
    (ICI / "controles_correction.json").write_text(json.dumps({"schema": "rg_controles_correction/0.2",
                                                               "scenes": list(apres.values())}, ensure_ascii=False,
                                                              indent=1) + "\n", encoding="utf-8")
    avant = {x["scene"]: x for x in _j(TMPC / "controles_avant.json")["scenes"]} if (TMPC / "controles_avant.json").exists() else {}
    jr = journal(a.journal)
    r0 = _j(ICI / "rapport_L0.json")
    r2 = _j(ICI / "rapport_L2.json")
    r2b = _j(ICI / "rapport_L2b.json")
    crit_lot = {c["id"].split(" ")[0]: c for r in (r0, r2, r2b) for c in r["criteres"]}

    # ---- 1. compilateur (L0)
    m01 = _j(OUT / "S01" / "modele_voie.json")
    bdd = [(b["id"], b["niveau"].get("devers_pct"), (b["prov"].get("niveau.devers_pct") or {}).get("regle"))
           for p in m01["profils"] for b in p["bandes"] if b["type"] == "bande_derasee"]
    adv = recompiler_cas_pieges()
    attendu_adv = {"A1": "refus", "A2": "refus", "A3": "refus", "A4": "refus", "A5": "bloque", "A6": "refus", "A7": "refus",
                   "A8": "accepte", "A9": "bloque", "A10": "refus", "A11": "refus", "A12": "refus"}
    for x in adv:
        k = x["cas"].split("_")[0]
        obt = "refus" if not x["compile"] else ("bloque" if x["non_conformites_bloquantes"] else "accepte")
        x["attendu"], x["obtenu"] = attendu_adv.get(k), obt
        x["ok"] = attendu_adv.get(k) == obt
    f_refus = TMP2 / "refus_A9.log"
    refus = f_refus.read_text(encoding="utf-8", errors="replace") if f_refus.exists() else ""

    # ---- 2. déterminisme (journal : un processus par scène + second processus)
    det = {n: jr.get(n) for n in jr if "#" not in n}
    det_ok = {n: v.startswith("identique") for n, v in det.items()}

    # ---- 3. rendus : empreintes de la géométrie rendue
    geo = {}
    for n in scenes:
        f = OUT / n / "rendus" / "manifest_rendus.json"
        if f.exists():
            m = _j(f)
            g = m.get("geometrie_rendue_sha256", {})
            geo[n] = all(sha(OUT / n / k) == v for k, v in g.items()) and len(g) == 2

    # ---- 4. planches et Meylan
    planches = sorted(str(p.relative_to(OUT)).replace("\\", "/") for n in scenes
                      for p in (OUT / n / "photos_non_versionnees" / "planches").glob("planche_*.png"))
    mey = {}
    for n, yml in zip(MEYLAN, ("M24_avenue_du_granier", "M27_avenue_de_verdun", "M20_avenue_de_chamechaude")):
        c = _j(OUT / n / "compilation.json") if (OUT / n / "compilation.json").exists() else {}
        mey[n] = {"description": f"recon/generateur/scenes_meylan/{yml}.yaml", "erreurs": (c.get("validation") or {}).get("nb_erreurs"),
                  "non_conformites": len(c.get("non_conformites", [])), "ecarts_admis": c.get("ecarts_admis"),
                  "fabrique": (OUT / n / "l2b" / "manifest_l2b.json").exists(),
                  "rendus": sorted(_j(OUT / n / "rendus" / "manifest_rendus.json")["images"]) if (OUT / n / "rendus" / "manifest_rendus.json").exists() else [],
                  "planches": [p for p in planches if p.startswith(n + "/")],
                  "deterministe": det.get(yml)}
    # ---- 5. revue visuelle
    f_cv, cv = constats()
    tuiles = sorted(str(p.relative_to(OUT)).replace("\\", "/") for n in scenes for p in (OUT / n / "rendus" / "tuiles").glob("*/*.png"))
    vues = {t.replace("recon/out/generateur/", "") for c in cv["constats"] for t in c.get("tuiles", [])}
    regardees = sorted(set(tuiles) & vues)
    pl_cat = sorted(str(p.relative_to(OUT)).replace("\\", "/") for p in (OUT / "catalogue_rendus").glob("*.png"))
    # ---- 6. tests : sorties par défaut dans tmp/
    t_def = {f: str((GEN / f).read_text(encoding="utf-8")).count('default=str(GEN / "tmp" / "tests"') for f in
             ("description/tests/tester_descriptions.py", "inference/tests/tester_inference.py")}

    def L(n, cle, k2=None):
        x = (apres.get(n) or {}).get("lisibilite") or {}
        v = x.get(cle)
        return v.get(k2) if (k2 and isinstance(v, dict)) else v

    rs = {n: v.get("route_seule") for n, v in apres.items()}
    bor_trous = {n: v["bordures"]["longueur_trous_m"] for n, v in apres.items()}
    pistes = {n: (L(n, "ecart_piste_enrobe"), L(n, "delta_e_piste_enrobe")) for n in scenes if L(n, "piste")}
    import rendu_valeurs as RV  # noqa: E402  (tables du rendu lues hors Houdini)
    val = RV.valeurs()
    classes_mesurees = [n for n in scenes if L(n, "ecart_classe_enrobe")]

    # ---- 7. correction après le second contrôle (mesures de controler_correction.py, tests du compilateur)
    def A(n, *cles):
        x = apres.get(n) or {}
        for c in cles:
            x = (x or {}).get(c) if isinstance(x, dict) else None
        return x
    t_enr = {n: (L(n, "enrobe", "teinte_hsv_median_deg"), A(n, "conducteur", "enrobe", "teinte_deg")) for n in scenes}
    t_bor = {n: (L(n, "bordure_dessus", "teinte_hsv_median_deg"), A(n, "conducteur", "bordure_face_soleil", "teinte_deg"))
             for n in scenes}
    t_can = {n: L(n, "caniveau_dessus", "teinte_hsv_median_deg") for n in scenes}
    sup = {n: A(n, "supports") or {} for n in scenes}
    elf = {n: A(n, "elements") or {} for n in scenes}
    ret = {n: A(n, "retours") or {} for n in scenes}
    veg = {n: A(n, "vegetation") or {} for n in scenes}
    cbev = {f"{n}/{k}": v for n in scenes for k, v in (A(n, "contraste_bev") or {}).items()}
    ombre = {n: L(n, "bord_sol") for n in scenes}
    corr = CC.correlation_usure([OUT / n for n in scenes])
    f_tests = ICI / "tests_description_L0.json"
    tests = {x["id"]: x for x in (_j(f_tests).get("erreurs", []) if f_tests.exists() else [])}
    crit = [
        {"id": "C-1 dévers des bandes dérasées de S01 (RF-GV-DEV-001, cité par la description)",
         "valeur": f"{bdd} (avant : ±2,5 %, RF-OSM-NIV-010)", "seuil": "±4 %, RF-GV-DEV-001",
         "atteint": bool(bdd) and all(abs(abs(v) - 4.0) < 1e-9 and r == "RF-GV-DEV-001" for _, v, r in bdd)},
        {"id": "C-2 cas piégés de la relecture adverse (tmp/verif/adv, relus sans modification, recompilés) : refus, "
               "blocage de la fabrication ou acceptation attendus",
         "valeur": f"{sum(x['ok'] for x in adv)} / {len(adv)} : " + ", ".join(f"{x['cas'].split('_')[0]} {x['obtenu']}" for x in adv),
         "seuil": "12 / 12 (avant : 9 / 12)", "atteint": len(adv) == 12 and all(x["ok"] for x in adv)},
        {"id": "C-3 le pilote refuse de fabriquer une description non conforme non admise (A9 : trottoir de 1 m)",
         "valeur": "refusée (code 1)" if "fabrication refusée" in refus else "non refusée", "seuil": "refus",
         "atteint": "fabrication refusée" in refus},
        {"id": "C-4 déterminisme des données et des USD de L1-L2b : un processus par scène, second processus comparé à "
               "l'octet (l1/, l2/, l2b/ et leurs manifestes ; avertissements de Houdini sans la liste d'attributs propre "
               "au processus ; .usda aux chemins relatifs des matériaux près). Les images Karma ne sont pas couvertes : "
               "elles ne sont pas identiques au pixel d'un processus à l'autre (contrôle indépendant : écart de 11 à "
               "17/255 au plus, dynamique à ± 0,001)",
         "valeur": f"{sum(det_ok.values())} / {len(det_ok)} identiques" + "".join(f" ; {n} : {v}" for n, v in det.items() if not det_ok[n]),
         "seuil": f"{len(scenes)} / {len(scenes)}", "atteint": len(det_ok) == len(scenes) and all(det_ok.values())},
        {"id": "C-5 manifest_rendus.json porte l'empreinte sha256 de route_l2.usda et route_l2b.usda rendus (égale au "
               "fichier actuel)", "valeur": f"{sum(geo.values())} / {len(geo)}", "seuil": f"{len(scenes)} / {len(scenes)}",
         "atteint": len(geo) == len(scenes) and all(geo.values())},
        {"id": "C-6 elements.json complet (pièces sur mesure des coudes et des angles)", "valeur": crit_lot.get("L2-15", {}).get("valeur"),
         "seuil": crit_lot.get("L2-15", {}).get("seuil"), "atteint": crit_lot.get("L2-15", {}).get("atteint")},
        {"id": "C-7 fil d'eau continu au droit des ralentisseurs (caniveau à grille, avaloirs)", "valeur": crit_lot.get("L2-16", {}).get("valeur"),
         "seuil": crit_lot.get("L2-16", {}).get("seuil"), "atteint": crit_lot.get("L2-16", {}).get("atteint")},
        {"id": "C-8 lisibilité de la vue de dessus (critère L2b-16), sur les 15 scènes (catalogue et Meylan) et pour chaque "
               "classe de peinture à part (second contrôle : le passage seul, comme dans la référence de l'utilisateur)",
         "valeur": "trottoir − enrobé : " + ", ".join(f"{n} {L(n, 'ecart_trottoir_enrobe')}" for n in scenes
                                                      if L(n, "ecart_trottoir_enrobe") is not None)
                   + " ; peinture − enrobé par classe : " + ", ".join(
                       f"{n} {c} {v}" for n in scenes for c, v in sorted((L(n, "ecart_classe_enrobe") or {}).items())),
         "seuil": "≥ 0,318 (trottoir) et ≥ 0,406 (chaque classe de peinture) sur chaque scène",
         "atteint": all(L(n, "ecart_trottoir_enrobe") is None or L(n, "ecart_trottoir_enrobe") >= 0.318 - 1e-9 for n in scenes)
         and all(v >= 0.406 - 1e-9 for n in scenes for v in (L(n, "ecart_classe_enrobe") or {}).values())
         and len(classes_mesurees) == len(scenes)},
        {"id": "C-9 arbres aux dimensions du modèle (L2b-17)", "valeur": "aucun arbre rendu à l'étape 1 (décision de "
                                                                         "l'utilisateur) ; dimensions portées dans le modèle (L0-16) et code de rendu gardé, désactivé",
         "seuil": crit_lot.get("L2b-17", {}).get("seuil", "100 %"), "atteint": None, "reporte": "étape 2 (végétation)"},
        {"id": "C-10 enrobé de chaussée en vue de dessus : luminance médiane ≤ 0,40 (référence 0,334 ; avant 0,48-0,55) et "
               "gris chaud (teinte 15-45°, photos de Meylan 26,7-37,5° au second contrôle)",
         "valeur": ", ".join(f"{n} {L(n, 'enrobe', 'Y_median')} ({L(n, 'enrobe', 'teinte_deg')}°)" for n in scenes if L(n, "enrobe")),
         "seuil": "≤ 0,40 ; 15-45°",
         "atteint": all(L(n, "enrobe", "Y_median") <= 0.40 and 15 <= L(n, "enrobe", "teinte_deg") <= 45 for n in scenes if L(n, "enrobe"))},
        {"id": "C-11 herbe en vue de dessus : teinte 75-80° et écart-type de luminance ≥ 0,10 (réalisme de la végétation, "
               "relecture)",
         "valeur": "étape 1 : accotements de S01 et terre-plein de S06 rendus comme des surfaces de la route, aspect sobre "
                   "(sans cartes de touffes ni de plaques) : " + ", ".join(f"{n} {L(n, 'herbe', 'teinte_deg')}° σ {L(n, 'herbe', 'Y_sigma')}"
                                                                        for n in scenes if L(n, "herbe")),
         "seuil": "75-80° ; σ ≥ 0,10", "atteint": None, "reporte": "étape 2 (végétation : la sobriété est demandée à l'étape 1)"},
        {"id": "C-12 boucle photo → description → fabrication sur 3 rues réelles de Meylan sans carrefour (M24, M27, M20) : "
               "description d'après les tuiles, compilation sans erreur ni non-conformité non admise, fabrication L1-L2b, "
               "rendus dont vues au champ et au tangage de la photo, planches rendu | photo",
         "valeur": "; ".join(f"{n} : {v['erreurs']} erreur, {v['non_conformites']} non-conformité, écarts admis "
                             f"{sorted((v['ecarts_admis'] or {}))}, rendus {len(v['rendus'])}, planches {len(v['planches'])}"
                             for n, v in mey.items()),
         "seuil": "3 rues, 0 erreur, ≥ 2 planches chacune",
         "atteint": all(v["erreurs"] == 0 and v["non_conformites"] == 0 and v["fabrique"] and len(v["planches"]) >= 2 for v in mey.values())},
        {"id": "C-13 revue visuelle : toutes les tuiles natives des rendus refaits regardées (relecture : 12 sur 108)",
         "valeur": f"{len(regardees)} / {len(tuiles)} ({f_cv})", "seuil": "100 %", "atteint": len(tuiles) > 0 and len(regardees) == len(tuiles)},
        {"id": "C-14 tests : sortie --json par défaut dans tmp/ (validation/ écrit seulement par faire_rapport_L0.py)",
         "valeur": str(t_def), "seuil": "défaut dans tmp/ pour les deux", "atteint": all(v == 1 for v in t_def.values())},
        # ---- étape 1 : la route seule (décision de l'utilisateur)
        {"id": "C-15 route seule (décision de l'utilisateur) : aucune géométrie hors de l'emprise de la route dans les scènes "
               "rendues (ni arbres, ni relief, ni prairie de décor, ni prolongements), ciel sans nuage, abords du modèle "
               "non rendus, socle et sol plat neutres",
         "valeur": f"{sum(1 for v in rs.values() if v and v['conforme'])} / {len(rs)} scènes"
                   + "".join(f" ; {n} : {v}" for n, v in rs.items() if not (v and v["conforme"])),
         "seuil": f"{len(scenes)} / {len(scenes)}", "atteint": len(rs) == len(scenes) and all(v and v["conforme"] for v in rs.values())},
        {"id": "C-16 angles et avancées avec pièces d'angle (pj::bordure::2.0 : deux éléments sur mesure en onglet) : aucun "
               "trou > 2 cm dans les files de bordure (S03 : 1,58 m avant, 26 angles en about droit)",
         "valeur": ", ".join(f"{n} {v} m" for n, v in sorted(bor_trous.items())) + " ; pièces sur mesure "
                   + ", ".join(f"{n} {apres[n]['bordures']['pieces_sur_mesure']}" for n in sorted(apres) if apres[n]["bordures"]["pieces_sur_mesure"]),
         "seuil": "0 m partout", "atteint": all((v or 0) == 0 for v in bor_trous.values())},
        {"id": "C-17 piste cyclable distincte de la chaussée (RF-MA-PIS-009 : enrobé de couleur différente) : ΔE76 CIELAB "
               "des médianes en vue de dessus ≥ 10 (seuil gardé : 2,3 seuil de perception, 10 différence évidente, choix "
               "déclaré) et distinction de même signe que les photos de Meylan (second contrôle : la condition « piste plus "
               "claire », mesurée sur l'ortho, est remplacée : photos M24 f877235a et M29 737f941f, piste plus sombre de "
               "0,04 à 0,09 et chaude, 22-44°)",
         "valeur": ", ".join(f"{n} : ΔY {dy}, ΔE {de}, teinte {L(n, 'piste', 'teinte_hsv_median_deg')}°" for n, (dy, de) in sorted(pistes.items()))
                   + " ; photos : ΔE 6,1 (M29) à 9,6 (M24)" if pistes else "aucune piste mesurée",
         "seuil": "ΔE ≥ 10 ; ΔY < 0 ; teinte 22-44° sur chaque scène à piste",
         "atteint": bool(pistes) and all(de is not None and de >= 10 and dy < 0 and 22 <= L(n, "piste", "teinte_hsv_median_deg") <= 44
                                         for n, (dy, de) in pistes.items())},
        {"id": "C-18 bordures en béton gris de la valeur du trottoir (pas de face blanche) : albédo moyen de la bordure / "
               "albédo du trottoir (tables du rendu, matériaux de la bibliothèque)",
         "valeur": f"bordure {val['bordure']:.3f} ; trottoirs {', '.join(f'{k} {v:.3f}' for k, v in val['trottoirs'].items())} ; "
                   f"rapport {min(val['rapports']):.2f} à {max(val['rapports']):.2f} ; caniveau {val['caniveau']:.3f} ; "
                   f"soleil à {val['soleil_deg']}°",
         "seuil": "rapport 0,90-1,10 (et soleil ≥ 40°, relecture)",
         "atteint": all(0.90 <= x <= 1.10 for x in val["rapports"]) and val["soleil_deg"] >= 40},
        # ---- correction après le second contrôle de l'étape 1
        {"id": "C-19 teintes rendues sur la plage mesurée sur les photos Panoramax de Meylan (second contrôle : enrobé rendu à "
               "17-19°, bordures et caniveaux neutres ou bleutés) : enrobé 25-37° en vue de dessus et en vue conducteur ; "
               "bordures 25-40° (dessus, et faces au soleil en vue conducteur) ; caniveaux 25-40° (dessus) ; teinte HSV de "
               "la médiane sRGB",
         "valeur": "enrobé (dessus/conducteur) : " + ", ".join(f"{n} {a}/{b}" for n, (a, b) in t_enr.items())
                   + " ; bordures (dessus/conducteur) : " + ", ".join(f"{n} {a}/{b}" for n, (a, b) in t_bor.items()
                                                                     if a is not None or b is not None)
                   + " ; caniveaux : " + ", ".join(f"{n} {v}" for n, v in t_can.items() if v is not None),
         "seuil": "enrobé 25-37° ; bordures et caniveaux 25-40° (photos : enrobé 26,7-37,5°, bordures 28-33°, caniveau 40°)",
         "atteint": all(v is not None and 25 <= v <= 37 for a in t_enr.values() for v in a)
         and all(v is None or 25 <= v <= 40 for a in t_bor.values() for v in a)
         and all(v is None or 25 <= v <= 40 for v in t_can.values())},
        {"id": "C-20 traversées cohérentes (second contrôle : BEV dans les bandes plantées de S_M20 et S_M27, bande de passage "
               "sur le trottoir de S_M27) : sol L2 sous chaque dalle de BEV dans {trottoir, chemin piéton, terre-plein, "
               "refuge} et sous chaque face de bande de passage dans la chaussée ou une piste ; compilateur : passage "
               "aboutissant dans une bande plantée ou une berme refusé (E17, E18), traversée revêtue acceptée (F7)",
         "valeur": "BEV : " + ", ".join(f"{n} {s['dalles']} dalles, {s['exceptions_bev']} hors support"
                                        for n, s in sup.items() if s.get("dalles"))
                   + " ; passages : " + ", ".join(f"{n} {s['faces_passage']} faces, {s['exceptions_passage']} hors support"
                                                  for n, s in sup.items() if s.get("faces_passage"))
                   + " ; tests : " + ", ".join(f"{k} {'ok' if tests.get(k, {}).get('ok') else 'ÉCHEC'}"
                                               for k in ("E17", "E18", "F7")),
         "seuil": "0 exception ; E17, E18, F7 ok",
         "atteint": all(s.get("exceptions_bev", 1) == 0 and s.get("exceptions_passage", 1) == 0 for s in sup.values())
         and all(tests.get(k, {}).get("ok") for k in ("E17", "E18", "F7"))},
        {"id": "C-21 elements.json : l'avaloir remplace le caniveau qu'il occupe (second contrôle : S03 26 recouvrements, "
               "8,45 m ; S10 8, 2,6 m) : 0 recouvrement > 2 cm entre deux éléments d'une même file, 0 trou > 2 cm contre "
               "un avaloir",
         "valeur": ", ".join(f"{n} {e.get('recouvrements')} recouvrement(s), {e.get('n_trous_contre_avaloir')} trou(s), "
                             f"{e.get('avaloirs')} avaloir(s)" for n, e in elf.items() if e.get("avaloirs") or e.get("recouvrements"))
                   + f" ; autres scènes : 0 recouvrement",
         "seuil": "0 ; 0",
         "atteint": all(e.get("recouvrements", 1) == 0 and e.get("n_trous_contre_avaloir", 1) == 0 for e in elf.values())},
        {"id": "C-22 retours transversaux à vue variable typés « raccord_vue » (rôle « retour »), aucun typé « chartiere » "
               "(second contrôle : 52 retours d'avancée de S03 pris pour des chartières d'abaissé)",
         "valeur": ", ".join(f"{n} {r.get('pieces_de_retour')} pièces {r.get('types')}" for n, r in ret.items()
                             if r.get("pieces_de_retour")),
         "seuil": "0 chartière dans un retour", "atteint": all(r.get("chartieres_dans_un_retour", 1) == 0 for r in ret.values())},
        {"id": "C-23 végétation de l'étape 2 : l2/vegetation.json marqué « etape : 2 » (rg_vegetation/0.2, arbres sous "
               "« arbres ») sur chaque scène, aucun arbre rendu (second contrôle : 53 arbres exportés sans marque)",
         "valeur": ", ".join(f"{n} {v.get('etape')} ({v.get('arbres')})" for n, v in veg.items()),
         "seuil": f"{len(scenes)} / {len(scenes)} marqués", "atteint": all(v.get("etape") == 2 for v in veg.values())},
        {"id": "C-24 BEV en contraste avec le revêtement voisin (RF-MA-OBS-003, arrêté du 15/01/2007 annexe 1 : 0,70 "
               "recherché, 0,40 acceptable ; second contrôle : 0,13 à 0,16 sur trottoir) : luminance relative en vue de dessus",
         "valeur": ", ".join(f"{k} {v['contraste']} ({v['teinte']})" for k, v in sorted(cbev.items())),
         "seuil": "≥ 0,40 pour chaque BEV", "atteint": bool(cbev) and all(v["contraste"] >= 0.40 for v in cbev.values())},
        {"id": "C-25 usure de l'enrobé propre à chaque scène (second contrôle : reprises et fissures au même endroit d'une "
               "scène à l'autre, corrélation 0,67 à 0,80) : corrélation de la luminance de l'enrobé entre deux scènes au même "
               "(x, y), x = 44 à 50,5 m, voies communes, sans peinture",
         "valeur": f"max {corr['max']} sur {len(corr['paires'])} paires : " + ", ".join(
             f"{k} {v['correlation']}" for k, v in sorted(corr["paires"].items(), key=lambda kv: -kv[1]["correlation"])[:8]),
         "seuil": "< 0,2 pour chaque paire", "atteint": corr["max"] is not None and corr["max"] < 0.2},
        {"id": "C-26 pas d'ombre de la route sur le sol neutre (second contrôle : trait sombre de 4 à 8 px au nord, "
               "luminance 0,12-0,16) : sol neutre de 0 à 0,30 m hors de l'emprise, 5e centile contre la médiane du sol à "
               "plus de 1 m",
         "valeur": ", ".join(f"{n} {v['ombre']}" for n, v in ombre.items() if v),
         "seuil": "écart ≤ 0,05 sur chaque scène", "atteint": len([v for v in ombre.values() if v]) == len(scenes)
         and all(v["ombre"] <= 0.05 for v in ombre.values() if v)},
    ]
    dans = [c for c in crit if c["atteint"] is not None]
    rapport = {"lot": "correction", "titre": "corrections après le contrôle adverse de l'étape 1 (L0, catalogue, L1, L2, L2b) ; "
                                              "étape 1 : la route seule (décision de l'utilisateur)",
               "decision_utilisateur": DECISION,
               "criteres": crit, "statut": "ok" if all(c["atteint"] for c in dans) else "partiel",
               "criteres_reportes": [c["id"].split(" ")[0] for c in crit if c["atteint"] is None],
               "mesures": {"avant": {n: {"lisibilite": avant[n]["lisibilite"], "fil_eau_interrompu_m": avant[n]["fil_eau"]["longueur_interrompue_m"],
                                         "bordures_trous_m": avant[n]["bordures"]["longueur_trous_m"]} for n in avant},
                           "apres": {n: {"lisibilite": v["lisibilite"], "fil_eau_interrompu_m": v["fil_eau"]["longueur_interrompue_m"],
                                         "bordures_trous_m": v["bordures"]["longueur_trous_m"],
                                         "route_seule": v.get("route_seule")} for n, v in apres.items()}},
               "cas_pieges": adv, "determinisme": det, "meylan": mey, "planches": planches,
               "second_controle": {"correlation_usure": corr, "contraste_bev": cbev, "supports": sup,
                                   "teintes": {"enrobe": t_enr, "bordures": t_bor, "caniveaux": t_can}},
               "planches_catalogue": pl_cat, "valeurs_rendu": val,
               "tuiles": {"produites": len(tuiles), "regardees": len(regardees), "constats": f_cv},
               "lots": {"L0": {"statut": r0["statut"], "criteres": [(c["id"].split(" ")[0], c["atteint"]) for c in r0["criteres"]]},
                        "L2": {"statut": r2["statut"], "criteres": [(c["id"].split(" ")[0], c["atteint"]) for c in r2["criteres"]]},
                        "L2b": {"statut": r2b["statut"], "criteres": [(c["id"].split(" ")[0], c["atteint"]) for c in r2b["criteres"]]}},
               "regles_demandees": "recon/generateur/validation/regles_demandees_correction.json"}
    (ICI / "rapport_correction.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ecrire_md(rapport, apres, avant, cv)
    for c in crit:
        etat = "REP " if c["atteint"] is None else ("OK  " if c["atteint"] else "NON ")
        print(etat + c["id"][:100] + " : " + str(c["valeur"])[:300])
    print("statut :", rapport["statut"])
    return 0


def _f(x, n=3):
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",")


def _etat(c):
    if c["atteint"] is None:
        return f"reporté ({c.get('reporte', 'étape 2')})"
    return "oui" if c["atteint"] else "**non**"


def ecrire_md(rapport, apres, avant, cv):
    crit = rapport["criteres"]
    dans = [c for c in crit if c["atteint"] is not None]
    L = ["# Rapport du lot « correction » : corrections après le contrôle adverse de l'étape 1, la route seule\n",
         "*`recon/generateur/validation/RAPPORT_correction.md` — produit par `python recon/generateur/validation/"
         "faire_rapport_correction.py` (données : `rapport_correction.json`, `controles_correction.json`, "
         f"`{rapport['tuiles']['constats']}`, `regles_demandees_correction.json`). Houdini 22.0.459 Indie (hython, VEX "
         "interprété), Karma XPU (husk). Base de règles lue, non modifiée ; specs de l'autre équipe non modifiées.*\n",
         f"**Statut : {rapport['statut']} — {sum(bool(c['atteint']) for c in dans)} critères sur {len(dans)} atteints**, "
         f"{len(crit) - len(dans)} reportés à l'étape 2 par décision de l'utilisateur ({', '.join(rapport['criteres_reportes'])}) "
         f"(lots régénérés : L0 {rapport['lots']['L0']['statut']}, L2 {rapport['lots']['L2']['statut']}, "
         f"L2b {rapport['lots']['L2b']['statut']}).\n",
         INTRO, "## 2. Critères du lot\n", "| Critère | Valeur | Seuil | Atteint |", "|---|---|---|---|"]
    for c in crit:
        L.append(f"| {c['id']} | {str(c['valeur']).replace('|', '/')} | {c['seuil']} | {_etat(c)} |")
    L.append("")
    L.append("Critères des lots régénérés (détail dans `RAPPORT_L2.md`, `RAPPORT_L2b.md`, `rapport_L0.json`) : "
             + " ; ".join(f"{k} : " + ", ".join(f"{i} {'oui' if ok else ('reporté' if ok is None else 'non')}" for i, ok in v["criteres"])
                          for k, v in rapport["lots"].items()) + ".\n")
    L.append(ETAPE1)
    L.append(CORRECTIONS)
    L.append(CORRECTIONS2)
    # mesures avant / après
    L.append("## 5. Mesures avant / après (vue de dessus et listes d'éléments)\n")
    L.append("Contrôle indépendant `controler_correction.py` (lecture des sorties seulement) ; « avant » : mêmes mesures sur "
             "les sorties d'avant la correction (`tmp/correction/controles_avant.json`). Luminance Rec. 709 des valeurs "
             "sRGB ; référence de l'utilisateur (`ref_carrefour_dessus`) : enrobé 0,334, trottoir − enrobé 0,318, "
             "peinture − enrobé 0,406 ; photos de Meylan : enrobé 26,7-37,5° (mesure du second contrôle ; 25-29° au premier). Les mesures de l'herbe (accotements de S01, "
             "terre-plein de S06) sont données pour mémoire : la végétation est reportée à l'étape 2.\n")
    L.append("| Scène | Enrobé Y (teinte) | Trottoir − enrobé | Peinture − enrobé | Piste − enrobé (ΔE) | Herbe teinte, σY | Fil d'eau interrompu (m) | Trous de bordure (m) | Route seule |")
    L.append("|---|---|---|---|---|---|---|---|---|")

    def lis(d, k, k2=None):
        x = (d or {}).get("lisibilite") or {}
        v = x.get(k)
        if k2:
            return v.get(k2) if isinstance(v, dict) else None
        return None if isinstance(v, dict) else v

    for n in sorted(apres):
        a, b = apres[n], avant.get(n)

        def av_ap(k, k2=None, nd=3):
            x2 = lis(a, k, k2)
            if b is None:
                return _f(x2, nd)
            return f"{_f(lis(b, k, k2), nd)} → {_f(x2, nd)}"
        her = ""
        if b is not None and lis(b, "herbe", "teinte_deg") is not None:
            her = f"{_f(lis(b, 'herbe', 'teinte_deg'), 1)}°, {_f(lis(b, 'herbe', 'Y_sigma'))} → "
        her += (f"{_f(lis(a, 'herbe', 'teinte_deg'), 1)}°, {_f(lis(a, 'herbe', 'Y_sigma'))}"
                if lis(a, "herbe", "teinte_deg") is not None else "—")
        pis = (f"{_f(lis(a, 'ecart_piste_enrobe'))} ({_f(lis(a, 'delta_e_piste_enrobe'), 1)})"
               if lis(a, "ecart_piste_enrobe") is not None else "—")
        fa = a["fil_eau"]
        fe = (f"{_f(b['fil_eau']['longueur_interrompue_m'], 2)} → " if b else "") + _f(fa["longueur_interrompue_m"], 2)
        if fa.get("longueur_retours_draines_m"):
            fe += f" ({_f(fa['longueur_retours_draines_m'], 2)} m de retours drainés, {fa['avaloirs']} avaloirs)"
        elif fa.get("grilles") or fa.get("avaloirs"):
            fe += f" ({fa['grilles']} grille(s), {fa['avaloirs']} avaloir(s))"
        bo = (f"{_f(b['bordures']['longueur_trous_m'], 2)} → " if b else "") + _f(a["bordures"]["longueur_trous_m"], 2)
        r_s = a.get("route_seule") or {}
        L.append(f"| {n} | {av_ap('enrobe', 'Y_median')} ({_f(lis(a, 'enrobe', 'teinte_deg'), 1)}°) | "
                 f"{av_ap('ecart_trottoir_enrobe')} | {av_ap('ecart_marquage_enrobe')} | {pis} | {her} | {fe} | {bo} | "
                 f"{'oui' if r_s.get('conforme') else 'non'} |")
    L.append("")
    v = rapport["valeurs_rendu"]
    L.append(f"Valeurs du rendu (tables de `rendu/rendu_l2b.py`, albédos linéaires de la bibliothèque) : bordure "
             f"{_f(v['bordure'])}, caniveau {_f(v['caniveau'])}, trottoirs "
             + ", ".join(f"{k} {_f(x)}" for k, x in v["trottoirs"].items())
             + f", enrobé de chaussée {_f(v['enrobe'])}, piste {_f(v['piste'])}, sol neutre {_f(v['sol_neutre'])} ; "
               f"soleil à {v['soleil_deg']}° ; passages piétons × {v['gris_passage']}.\n")
    # Meylan
    L.append("## 6. Rues de Meylan : photo → description → fabrication\n")
    L.append("Descriptions écrites en regardant les tuiles natives des photos Panoramax (dossier 13, photos jamais versionnées "
             "ni diffusées) : `recon/generateur/scenes_meylan/` (README). Rendus refaits à l'étape 1 (route seule, sans les "
             "arbres ni le fond des photos). Planches rendu | photo dans "
             "`recon/out/generateur/<scène>/photos_non_versionnees/planches/` (non versionné, non diffusé).\n")
    L.append("| Scène | Description | Erreurs | Non-conformités non admises | Écarts admis | Rendus | Planches | Déterminisme |")
    L.append("|---|---|---|---|---|---|---|---|")
    for n, x in rapport["meylan"].items():
        L.append(f"| {n} | `{x['description']}` | {x['erreurs']} | {x['non_conformites']} | "
                 f"{', '.join(sorted((x['ecarts_admis'] or {}).keys())) or '—'} | {len(x['rendus'])} | {len(x['planches'])} | "
                 f"{x.get('deterministe') or '—'} |")
    L.append("")
    for x in cv.get("constats", []):
        if x["scene"] in rapport["meylan"]:
            L.append(f"- **{x['scene']}** : {x['constat']}" + (f" Défauts : {x['defauts']}" if x.get("defauts") else ""))
    L.append("")
    # revue visuelle
    L.append("## 7. Revue visuelle des rendus refaits\n")
    L.append(f"{rapport['tuiles']['regardees']} tuiles natives regardées sur {rapport['tuiles']['produites']} produites "
             "(`recon/pcg/vision/decoupe.py`, ≤ 1092 px, 20 % de recouvrement), planches par scène (1092 × 792) et planches "
             "d'ensemble du catalogue regardées en entier (`recon/out/generateur/catalogue_rendus/`, "
             + ", ".join(f"`{p.split('/')[-1]}`" for p in rapport["planches_catalogue"]) + f") ; constats dans "
             f"`{rapport['tuiles']['constats']}`.\n")
    for x in cv.get("constats", []):
        if x["scene"] not in rapport["meylan"]:
            L.append(f"- **{x['scene']}** : {x['constat']}" + (f" Défauts : {x['defauts']}" if x.get("defauts") else ""))
    L.append("")
    L.append(RESTE)
    nonat = [c for c in dans if not c["atteint"]]
    if nonat:
        L.append("Critères du lot non atteints : " + " ; ".join(c["id"].split(" ")[0] + " (" + str(c["valeur"])[:240] + ")"
                                                              for c in nonat) + ".\n")
    L.append("## 9. Règles demandées au propriétaire de la base (non modifiée)\n")
    rg = _j(ICI / "regles_demandees_correction.json")
    for d in rg["demandes"]:
        L.append(f"- **{d['id']} — {d['sujet']}** : {d['demande']}. Lu : {d['source_lue']}. Choix du générateur : "
                 f"{d['choix_du_generateur']}.")
    L.append("")
    L.append(FICHIERS)
    (ICI / "RAPPORT_correction.md").write_text("\n".join(L) + "\n", encoding="utf-8")


INTRO = """## 1. Ce que la relecture demandait, ce que l'utilisateur a décidé, ce que le lot a fait

La relecture adverse de l'étape 1 (verdict « corrections nécessaires ») relevait trois défauts majeurs (P1) : la boucle
voulue par l'utilisateur — photo de Meylan → description simple → fabrication — n'était faite sur aucune rue réelle ;
les arbres étaient rendus sans les dimensions du modèle ; la vue de dessus était moins lisible que la référence de
l'utilisateur. Venaient ensuite cinq défauts P2 (dévers des accotements hors agglomération, chevauchements et interdits
non bloquants, fil d'eau coupé aux ralentisseurs, pièces de bordure absentes de elements.json, déterminisme des
manifestes), cinq P3 (sorties des tests, BEV, fin de route, usure et trottoirs calés sur les photos, revue de toutes
les tuiles) et un P4 (lecteur YAML).

Pendant la correction, l'utilisateur a tranché : « il ne doit pas générer la montagne : il doit générer les routes, la
chaussée, etc. dans un premier temps ; la végétation, c'est dans un deuxième temps ». L'étape 1 est donc **la route
seule** : rien en dehors de l'emprise de la route (ni montagnes, ni arbres, même ceux du modèle, ni prairie, ni nuages
spectaculaires), un sol plat neutre et uni, un ciel physique clair et le soleil pour l'éclairage ; le code du décor et
de la végétation est gardé, désactivé (option `--decor-etape2`). Les points de la relecture qui portaient sur le décor
et la végétation (arbres, herbe, horizon) sont reportés à l'étape 2 et exclus du statut, sans seuil abaissé (§ 2,
« reporté ») ; toute l'attention va à la qualité de la route (§ 3).

Chaque point est corrigé à sa cause (§ 3 et 4) ; les seuils de la relecture sont gardés ; ce qui n'est pas atteint est
dit (§ 8). Un second contrôle indépendant de l'étape 1 a confirmé la route seule et relevé des défauts de la route
(traversées incohérentes à Meylan, contraste des passages, teintes, piste, usure répétée, avaloirs, retours, BEV, ombre
du socle, erreurs du rapport) : ils sont corrigés à leur cause au § 4 bis. Les 15 scènes ont ensuite été refabriquées
en **une seule passe du code final** (L1, L2, L2b, rendus ; un processus par scène, second processus pour le
déterminisme ; `tmp/second_controle/fabriquer_tout.sh`, journal `tmp/second_controle/fabrication.log`). Une première
passe complète a fait apparaître au rapport L2 deux régressions dues à ces corrections (L2-5 : 86 sondes de vue
hors ± 5 mm et 12 sans impact ; L2-9 : 13 coupes de caniveau de 4,7 cm, TQ-BOR-002) : corrigées à leur cause (§ 4 bis),
puis la passe unique a été refaite en entier (journal de la première : `tmp/second_controle/fabrication_passe1.log`).
"""

ETAPE1 = """## 3. Étape 1 : la route seule (décision de l'utilisateur)

| Point | Avant | Étape 1 | Contrôle |
|---|---|---|---|
| Décor | arbres du modèle et de décor, relief de 4,5 à 12 km, prairie texturée, prolongements de 400 m, nuages | **rien hors de l'emprise de la route** : abords du modèle (« pelouse 6 ») non rendus (sous-ensemble de faces lié à un matériau invisible ; la couche `l2/route_l2.usda` reste référencée telle quelle) ; arbres, relief, prairie, prolongements et nuages désactivés (code gardé : `rendre_scene(..., decor_etape2=True)`, pilote `--decor-etape2`) | C-15 |
| Fin de tronçon | route prolongée de 400 m sans marquage (ou arrêtée net sur la prairie avant la correction) | **socle** : jupe verticale sous la limite extérieure du profil et coupe nette en s = 0 et s = L, jusqu'à un sol plat 5 cm sous la surface visible la plus basse (`decor_l2b.socle_jupe`, `sol_plat`) : le tronçon fabriqué se lit tel quel, rien n'est inventé au-delà | vues `cible_fin_de_route`, oblique |
| Sol autour | prairie à touffes et plaques | sol plat **neutre et uni** (gris-beige clair, albédo 0,50, mat, ± 1 %), mailles de 2 à 512 m jusqu'à 16 km ; le fond vu au ras de l'horizon a la radiance du sol (aucune bande) | C-15 |
| Ciel | Preetham + nuages fractals | Preetham clair **sans nuage**, voile d'horizon blanc bleuté ; soleil à 42° pour l'éclairage | C-15 |
| Accotements (S01), terre-plein (S06), fosses (S03) | herbe à cartes macro et méso | surfaces de la route au matériau du modèle, **aspect sobre** (texture recolorée, sans touffes ni plaques) ; aucune plantation (les fosses restent en paillage minéral, le terre-plein en gazon plat) | C-11 (reporté) |
| Chaussée | enrobé 0,11 gris chaud, reprises et fissures marquées | même enrobé, **usure légère** : nuances ± 3 %, 10 reprises à peine plus sombres (0,90-0,95) dont des tranchées transversales étroites, fissures pontées rares et fines ; second contrôle : teinte calée sur le **rendu** (32-33° en vue de dessus, 30° en vue conducteur), cartes d'usure lues en **coordonnées de la route (s, t)** avec un **décalage propre à chaque scène** | C-10, C-8, C-19, C-25 |
| Bordures | béton du site (texture granuleuse verdâtre, lue comme du granit), 0,29 | **béton préfabriqué vibré à peau lisse** (bibliothèque route_fr:beton_prefa_lisse), albédo 0,35 = **valeur du trottoir** ; caniveaux 0,265 (un ton sous la bordure) ; second contrôle : **gris chaud** (échelle par canal, bordure ~30°, caniveau ~35°, saturation 0,06-0,08), luminance inchangée | C-18, C-19 |
| Angles et avancées | angles des avancées de S03 en about droit : fente de 0,12 m sur le nez, 26 angles, 1,58 m de « trous » | **pièces d'angle** : nouvelle version **pj::bordure::2.0** (la 1.0 reste intacte) : sommet vif > 30° (bordures_elements.json) posé en angle même quand il coïncide avec un changement d'intervalle ; les deux éléments sur mesure aboutés en onglet | C-16, C-6 |
| Piste cyclable (S05, Meylan) | gris chaud 0,20 | contrôle précédent : gris-vert de l'ortho (0,19), plus clair que la chaussée ; second contrôle : **recalée sur les photos Panoramax** (M24, M29) : plus sombre que la chaussée (rendu − 0,05) et chaude (~30°) | C-17 |
| Passages piétons | blanc de la classe d'usure | **un peu grisés** : albédo × GRIS_PASSAGE sur les faces de classe « passage » (sous-ensemble de faces) ; × 0,78 au contrôle précédent (le texte disait à tort × 0,86), × 0,93 depuis le second contrôle pour garder le passage seul au-dessus de la référence (≥ 0,406) ; usure plus diffuse | C-8 |
| Vues | dessus, oblique, conducteur, piéton, détail | idem + un détail par scène sur l'élément propre (rabattement, dos-d'âne et caniveau à grille, abaissé et BEV, piste, terre-plein, couloir bus…), vues ciblées (angle d'avancée, coude de bordure, plateau, fin de tronçon) ; planche d'ensemble dessus + oblique | § 7 |
| Ombre du socle | trait sombre de 4 à 8 px au nord du profil en vue de dessus (ombre de la route surélevée sur le sol plat) | second contrôle : soleil et ciel du sol neutre **liés à lui seul, sans ombre portée** (liens de lumière et d'ombre UsdLux) ; mêmes lumières, éclairage inchangé | C-26 |
| Fosses (S03) | paillage minéral verdâtre (80°), lu comme de la mousse | second contrôle : **paillage minéral gris-beige** (rendu 41°) | revue |
"""

CORRECTIONS = """## 4. Corrections après contrôle, point par point

| Point de la relecture | Cause | Correction | Contrôle |
|---|---|---|---|
| P1 Boucle Meylan absente | aucune description de rue réelle | 3 rues sans carrefour décrites d'après les tuiles natives des photos (avenue du Granier M24, avenue de Verdun M27, avenue de Chamechaude M20), `scenes_meylan/*.yaml` ; écarts réels admis avec leur preuve (`ecarts_admis`) ; fabrication L1-L2b et rendus, dont des vues au champ et au tangage de la photo (`VUES_PHOTO`) ; planches rendu / photo (`rendu/planches_photo.py`) | C-12, § 6 |
| P1 Arbres sans dimensions | le compilateur ne portait ni hauteur, ni houppier, ni fût ; le rendu tirait des arbres génériques | essence, hauteur, houppier et fût portés dans le modèle (`asset_id`, `hauteur_m`, `houppier_rayon_m`, `fut_m`) ; fût relevé au gabarit RF-OSM-VEG-001 ; rg::vers_entites les exporte ; le rendu sait construire chaque prototype à ces dimensions — **non rendu à l'étape 1** (décision de l'utilisateur) | L0-16 ; C-9 reporté |
| P1 Lisibilité, matériaux | exposition × 1,30 (enrobé à 0,55), enrobé bleuté, trottoir d'albédo voisin de la chaussée, soleil rasant | exposition au gain 1, courbe en S 0,50, soleil à 42° ; sols en MaterialX (coordonnées du monde : ni répétition ni couture) ; enrobé ancien 0,11 gris chaud (photos : 25-29° au premier contrôle, 26,7-37,5° au second) ; trottoir clair 0,35 ; critère de lisibilité ajouté (L2b-16) à côté de L2b-11, dont le seuil (dynamique ≥ 0,75) est gardé | L2b-16, C-8, C-10 |
| P2 Dévers des accotements | RF-GV-DEV-001 citée par la description de S01 mais non appliquée (2,5 %) | bande dérasée 4 %, berme 8 % vers l'extérieur hors agglomération, provenance de chaque dévers ; en agglomération inchangé (règle demandée) | L0-13, C-1 |
| P2 Refus | chevauchements acceptés, interdits réglementaires seulement signalés, fabrication lancée malgré une non-conformité | chevauchements refusés ; dos-d'âne ou plateau trapézoïdal hors agglomération ou à plus de 30 km/h refusés (décret 94-447) ; `ecarts_admis` (motif obligatoire) ; `preparer_entree` refuse de fabriquer sur un contrôle non conforme ou hors plage non admis | L0-14, L0-15, C-2, C-3 |
| P2 Fil d'eau aux ralentisseurs | le caniveau déclaré était coupé sous le dos-d'âne (S08) et le plateau (S10) | caniveau à grille dans l'emprise du caniveau relevé, radier au fil d'eau courant (continu) ; grilles d'avaloir au pied des rampes de plateau (Certu 2010) et au bout de chaque file de caniveau fermée par une avancée (S03) ; moyens [G], règles demandées (D-CORR-1, 2, 9) | L2-16, C-7 |
| P2 elements.json incomplet | les pièces sur mesure des coudes et des angles n'étaient pas listées (points lus avant le nœud de pose) | liste lue au nœud `poser` de pj::bordure ; angles des avancées désormais en pièces d'angle (pj::bordure::2.0) ; TQ-BOR rejoué | L2-15, C-6, C-16 |
| P2 Déterminisme des manifestes | avertissements de Houdini avec une liste d'attributs dans un ordre propre au processus ; géométrie rendue non tracée | avertissements normalisés (`commun/determinisme.py`) ; sha256 de `route_l2.usda` et `route_l2b.usda` dans `manifest_rendus.json` ; un processus par scène, second processus comparé à l'octet | C-4, C-5 |
| P3 Sorties des tests | `--json` écrivait par défaut dans validation/ | défaut `tmp/tests/` ; seul `faire_rapport_L0.py` écrit dans validation/ | C-14 |
| P3 BEV | BEV sans coordonnées de texture, étendue au-delà de la vue < 0,05 m | dalles podotactiles jointées (UV le long de la bordure dans rg::sol) ; étendue limitée à la vue visible < 0,05 m (RF-MA-TRO-015) | rapport L2 (BEV), vues `cible_abaisse_bev` |
| P3 Fin de route, couture | route arrêtée net sur la prairie, herbe du décor d'une autre teinte | étape 1 : socle à coupe nette et sol neutre uni (aucune couture possible : un seul matériau hors de la route) | C-15, vues `cible_fin_de_route` |
| P3 Usure, trottoirs calés sur Meylan | aucune mesure sur photo | teinte et saturation de l'enrobé, blanc de la peinture selon l'usure (0,66 / 0,58 / 0,52), masques d'usure à granulats affleurants ; béton balayé à joints sciés tous les 2 m (Meylan) ; passages un peu grisés | C-10 |
| P3 Revue visuelle | 12 tuiles regardées sur 108 | toutes les tuiles natives regardées, vues ciblées aux points singuliers (angle d'avancée, coude de bordure, caniveau au dos-d'âne et au plateau, abaissé et BEV, fin de tronçon) | C-13, § 7 |
| P4 Lecteur YAML | écart à PyYAML non documenté | test Y1 (PyYAML 6.0.3 du Python du système) ; écarts documentés | L0-17 |

Également corrigé en route : zones hachurées interrompues par une autre section (îlot bordé des rues de Meylan) jointes
par-dessus l'interruption et zone pleine dès s = 0 remplie d'un aplat (rg::marquages) ; îlot de bordure fermé abandonné
par pj::bordure (boucle ouverte par rg::vers_entites) et sans zone sous la bordure dans rg::sol ; marche de 2 cm aux
changements de section (crête à plat sur une bande de séparation, demande D-CORR-4).
"""

CORRECTIONS2 = """## 4 bis. Corrections après second contrôle

Second contrôle indépendant de l'étape 1 (la route seule), relu dans `tmp/controle_etape1.json` et
`tmp/controle_route/` (scripts m1 à m5, sans import du générateur). Ce qui tenait est gardé (route seule, sol neutre,
lisibilité du catalogue, bordures de la valeur du trottoir, caniveaux continus, BEV de 0,5875 m à 0,50 m, refuge de M24,
fin de tronçon, empreintes, déterminisme des données). Chaque défaut est corrigé à sa cause :

| Point du contrôle | Cause | Correction | Contrôle |
|---|---|---|---|
| P1 S_M27 : BEV dans les bandes plantées, abaissés sur les bordures extérieures (côté herbe), une bande du passage peinte sur le trottoir | le compilateur posait l'abaissé et la BEV sur **toutes** les bordures du profil, et peignait le passage sur tous les groupes de bandes au niveau de la chaussée (trottoir « niveau chaussée » compris) ; le diagnostic du rapport précédent (« bandes sur les bermes ») était faux | `description_vers_modele.py` : **traversée** du passage calculée dans chaque profil (`traversee_passage`) : des voies vers l'extérieur, bandes traversées (chaussée, zone neutralisée, accotement revêtu, piste) jusqu'à la **première surface piétonne** (trottoir, chemin, quai, voie verte) ; abaissé sur la bordure d'aboutissement (BEV côté piéton à 0,50 m), sur le refuge et sur une bordure franchie (sans BEV) ; bandes peintes sur les seules bandes traversées ; profil voisin qui touche le passage : rampants sans BEV ; **refus** d'un passage qui aboutit dans une berme, une bande plantée, un terre-plein extérieur ou le bord du profil ; aboutissement de plain-pied : BEV impossible au schéma 0.1, interdit RF-MA-BEV-001 (admissible). Description M27 : bermes coupées au droit du passage par une liaison revêtue au niveau de la chaussée (photos 176f9ab0, 7ab5b751 regardées en zooms natifs : liaisons revêtues, bandes du passage prolongées dessus), chemin au-delà de la piste ; débouchés de plain-pied sans BEV (écart admis, motif : aucune BEV visible sur les photos) ; dévers dit (« dévers 0 ») pour raccorder la liaison sans marche | C-20, tests E17, E18, F7 |
| P1 S_M20 : BEV dans les bandes plantées, passage sans surface piétonne | même cause | description M20 : traversées revêtues au droit du passage (chemin à travers la bande plantée gauche, liaison à travers l'accotement droit jusqu'au chemin piéton), abaissés et BEV sur les bordures basses côté chaussée | C-20 |
| P1 contraste des passages à Meylan (M24 0,361, M27 0,390 < 0,406) non mesuré par C-8 | C-8 ne mesurait que les 12 scènes du catalogue et toute la peinture ensemble ; grisage × 0,78 combiné à l'usure u2/u3 | C-8 et L2b-16 mesurés sur les **15 scènes et par classe de peinture** ; grisage des passages × 0,93 | C-8, L2b-16 |
| P2 teinte de l'enrobé rendue 17-19° (photos 27-37°) | albédo calé sur la teinte voulue sans tenir compte de l'éclairage (le ciel bleu rend un albédo neutre à 1,00 / 1,00 / 1,035) | albédos **recalés sur le rendu** (essais `tmp/second_controle/iter_enrobe.py`) ; critère resserré C-19 sur la plage des photos, en vue de dessus et en vue conducteur | C-19, C-10 |
| P2 bordures et caniveaux bleutés | béton lisse de la bibliothèque parfaitement neutre | échelle d'albédo **par canal** (gris chaud) à luminance inchangée (C-18 inchangé) | C-19, C-18 |
| P2 piste verte et plus claire que la chaussée (photos : plus sombre et chaude) | calage sur l'ortho, condition « ΔY > 0 » de C-17 | piste recalée sur les photos M24 (f877235a) et M29 (737f941f) ; C-17 : la condition « piste plus claire » est remplacée par une distinction de même signe que les photos (ΔY < 0, teinte 22-44°), le seuil ΔE ≥ 10 est gardé — il n'est **pas atteint** (photos : ΔE 6,1 à 9,6) : à trancher par l'utilisateur (§ 8) | C-17 |
| P2 usure de l'enrobé identique d'une scène à l'autre (corrélation 0,67-0,80) | carte macro lue en coordonnées du monde sans décalage | cartes (détail, macro, bruit) lues en **(s, t)** de la route (primvar `st_route` écrite par le rendu sur les maillages du sol, la couche fabriquée n'est pas modifiée) + **décalage propre à la scène** (hachage sha256 de son identifiant) ; masque d'usure de la peinture décalé de même | C-25 |
| P3 avaloirs posés par-dessus le caniveau (S03 26 recouvrements, S10 8) | rg::vers_entites ajoutait l'avaloir sans couper l'intervalle du caniveau | rg::vers_entites : intervalles du caniveau **moins** ceux des avaloirs ; **pj::caniveau::2.1** (nouvelle version, 1.0 et 2.0 intactes) : pièce gardée dès 5 mm à une borne d'intervalle (sinon trou de 5 cm devant l'avaloir) ; contrôle de continuité : 0 recouvrement > 2 cm, avaloir compté dans la file d'eau. Régressions vues au rapport L2 de la première passe, corrigées à leur cause : (1) la grille (quadrilatère sans épaisseur, 2 mm au-dessus du caniveau qu'elle recouvrait) flottait au-dessus de l'assise du caniveau retiré, la sonde de vue tombait 0,20 m plus bas (L2-5 : 86 sondes hors ± 5 mm, S03 et S10) : rg::vers_entites pose la grille au niveau du dessus du caniveau et le **corps fermé de l'avaloir** dessous (0,25 m), et la sonde « devant la face » voit les grilles ; (2) coupes de caniveau de 4,7 cm devant chaque avaloir de S03 (L2-9, TQ-BOR-002 : coupe ≥ 0,20 m) : pj::caniveau::2.1 **partage** une coupe de moins de 0,20 m avec l'élément voisin (2 × 0,52 m) | C-21, C-7, L2-5, L2-9 |
| P3 retours d'avancée typés « chartiere » (52 dans S03) | même pièce de raccord de vue que la chartière, même rôle | rg::vers_entites : intervalle du retour marqué `usage : retour` ; elements.json : type **raccord_vue**, rôle **retour** (la géométrie de pj::bordure est inchangée) | C-22 |
| P3 vegetation.json exporté sans marque à l'étape 1 (53 arbres) | export du lot L2 indépendant de l'étape | `rg_vegetation/0.2` : `{"etape": 2, "usage": …, "arbres": […]}` ; contrôles L2 relus sur « arbres » | C-23 |
| P3 fosses de S03 verdâtres (80°) | texture paillage_mineral de la bibliothèque | paillage minéral gris-beige recoloré (rendu 41°, saturation 0,14) | revue |
| P3 BEV peu contrastée (0,13-0,16) | dalles gris clair sur trottoir clair | teinte de la BEV **selon le revêtement voisin** (`materiau_voisin` porté par rg::sol, `teinte` dans bev.json) : anthracite sur revêtement clair, gris clair sur enrobé ; la photo M24 montre une BEV claire sur béton clair : la règle (RF-MA-OBS-003, réglementaire) est préférée, à trancher par l'utilisateur | C-24 |
| P3 ombre de la jupe du socle (trait sombre au nord) | la route surélevée sur son socle porte une ombre sur le sol plat (la jupe seule exclue des ombres ne suffit pas : essai `tmp/second_controle/essais`) | soleil et ciel du sol neutre liés à lui seul, sans ombre portée (liens UsdLux) ; murs du sol hors de l'emprise (entre deux abords) retirés de la jupe et non rendus | C-26 |
| P3 rapport inexact | — | § 3 : × 0,78 (et non × 0,86) au contrôle précédent, × 0,93 désormais ; BEV du refuge de M24 : 0,80 m (t = − 0,40 à 0,40), conforme RF-MA-BEV-004 (le rapport précédent écrivait à tort 1,80 m) ; diagnostic de M27 corrigé (ci-dessus) ; C-4 : données et USD de L1-L2b seulement, images Karma non déterministes au pixel | C-4 |
| P3 traçabilité : deux passes partielles | rendus de S05, S06, S07 (et S09) antérieurs à la dernière modification de rendu_l2b.py | les 15 scènes refaites en une seule passe du code final (`tmp/second_controle/fabriquer_tout.sh`) | C-4, journal |
| L2b-13 S03 : 252 m de bordures au lieu de 256 | le côté transversal des avancées coupées en s = 0 et s = L n'était pas construit | rg::nivellement : à un bout de la route, un élément répété (profil de la première ou de la dernière section repris plus loin entre deux sections d'un autre profil) a son retour construit contre le profil de la section voisine, supposé continuer au-delà du bout ; ces deux côtés sont posés sur la coupe du bout de scène, face tournée hors de l'emprise : rien n'est modélisé devant eux, leurs 12 sondes de vue sont comptées à part par `controler_L2.py` (L2-5, « sondes devant la coupe d'un bout de scène »), pas mêlées aux sondes sans impact | L2b-13, L2-5 |

Rues de Meylan après correction : M27, bermes coupées par des liaisons revêtues, bandes du passage sur la chaussée, les
liaisons et la piste, BEV claires sur le refuge ; M20, chemins revêtus des deux côtés, abaissés et BEV anthracite sur
les bordures basses ; M24 inchangée (BEV sur les trottoirs et le refuge).
"""

RESTE = """## 8. Ce qui reste (défauts connus)

- Reporté à l'étape 2 (décision de l'utilisateur) : arbres aux dimensions du modèle (C-9 ; le code est prêt, désactivé),
  herbe réaliste (C-11), fond (relief, bâti), mobilier et signalisation verticale.
- **À trancher par l'utilisateur (seuils gardés, non atteints)** :
  - C-17 : la piste est recalée sur les photos de Meylan (plus sombre et chaude, comme le demande le second contrôle) ;
    l'écart de couleur avec la chaussée est alors de l'ordre de celui des photos (ΔE 6,1 à 9,6), sous le seuil ΔE ≥ 10
    (« différence évidente », choix déclaré du contrôle précédent). Garder la fidélité aux photos, ou une piste plus
    sombre que les photos (≈ − 0,10 en luminance) pour atteindre ΔE ≥ 10 ?
  - L2b-11 (dynamique p99 − p1 ≥ 0,75) : non atteinte sur la plupart des rendus (0,50 à 0,72) ; à l'étape 1 les grandes
    plages uniformes (sol neutre, ciel clair) la réduisent, et le trait d'ombre retiré du socle l'abaisse encore ; elle ne
    mesure pas la lisibilité (la référence de l'utilisateur n'atteint que 0,47) : le critère L2b-16 est à côté, atteint.
  - BEV : teinte choisie en contraste avec le revêtement voisin (RF-MA-OBS-003, réglementaire : anthracite sur trottoir
    clair, gris clair sur enrobé) ; la photo M24 montre une BEV claire sur béton clair, peu contrastée : garder la règle
    (choix actuel) ou la fidélité à la photo ?
- L2b-13 (S03, côté transversal des avancées coupées par les bouts) : construit depuis le second contrôle (256 m).
- **Vu à la revue des tuiles, hors liste du second contrôle, non corrigé** : au droit d'un abaissé, `rg::nivellement`
  abaisse tout le côté au-delà de la bordure, jusqu'au bord du modèle, de la différence de vue (0,12 m pour une vue
  abaissée à 0,02 ; 0,04 m à S_M20) : trottoir, mais aussi piste au niveau du trottoir, bande plantée et abords (mesuré
  sur le sol L2 : S08, S_M20, S_M24 ; S10, sur plateau, n'est pas concerné). Il se voit à S_M24 : la limite trottoir |
  piste se plie au droit du passage (vue piéton, vue photo f877235a), quand la photo montre une limite droite. Correction
  proposée, à trancher : abaissement limité à la première surface piétonne par un plan incliné transversal ≤ 5 % quand
  le trottoir est assez large (2,40 m pour 0,12 m), sinon abaissement de toute la largeur du trottoir avec un raccord de
  la bande voisine (sans toucher la piste ni les abords).
- Rues de Meylan : la BEV ne peut pas être posée sur un débouché de plain-pied (schéma 0.1 : BEV portée par l'abaissé
  d'une bordure) ; S_M27 n'en a donc qu'au refuge, comme sur les photos (écart RF-MA-BEV-001 admis par la description).
- Mesure corrigée sans changer de seuil : L2-13 comptait les rues de Meylan avec le catalogue (motif « S* » : 15 scènes
  regardées pour 12 attendues, critère faux négatif) ; le comptage est restreint aux 12 scènes du catalogue.
- Moyens [G] sans règle de la base : caniveau à grille, avaloirs (plateaux, files fermées), crête à plat, dévers des
  accotements en agglomération (§ 9). La pièce d'angle suit la spécification de pose des bordures (angle vif = point
  dur, déviation > 30°, `assets/specs/bordures_elements.json`, lue sans modification) et l'onglet de pj::bordure.
- Rues de Meylan simplifiées (section droite sans carrefour, bâti et arbres absents à l'étape 1) : les planches sont des
  cas semblables, pas des vues recalées.
- Joints du béton balayé et usure de l'enrobé lus en coordonnées de la route (s, t) à l'étape 1 depuis le second
  contrôle ; le décor de l'étape 2 (prolongements, sol de décor) reste en coordonnées du monde (aucune couture).
"""

FICHIERS = """## 10. Fichiers

- Code et HDA (versionnés, `recon/generateur/`) : `commun/profil.py`, `commun/conformite.py`, `commun/determinisme.py`,
  `description/description_vers_modele.py`, `description/FORMAT_DESCRIPTION.md`, `description/tests/`,
  `schema/modele_voie.schema.json`, `schema/valider_modele.py`, `fabriquer_generateur.py` (`--decor-etape2`),
  `fabriquer_l2.py`, `fabriquer_l2b.py`, `hda/rg_nivellement`, `hda/rg_sol`, `hda/rg_vers_entites`, `hda/rg_marquages`,
  `hda/pj_caniveau_v2`, **`hda/pj_bordure_v2`** (pj::bordure::2.0), `hda/README_RG.md`, `rendu/rendu_l2b.py` (route
  seule par défaut), `rendu/decor_l2b.py` (socle ; décor de l'étape 2 gardé), `rendu/ciel.py`, `rendu/textures_sol.py`,
  `rendu/planches.py`, `rendu/planches_photo.py`, `scenes_meylan/`.
- Second contrôle : `description/description_vers_modele.py` (traversée d'un passage), `description/format_profil.py`,
  `hda/rg_vers_entites` (corps de l'avaloir), `hda/pj_caniveau_v2_1` (coupe < 0,20 m partagée),
  `commun/profil.py` (dévers dit), `description/tests/tester_descriptions.py` (E17, E18, F7), `description/exemples/05_*`,
  `scenes_meylan/M20_*.yaml`, `scenes_meylan/M27_*.yaml`, `hda/rg_nivellement`, `hda/rg_sol`, `hda/rg_vers_entites`,
  **`hda/pj_caniveau_v2_1`** (pj::caniveau::2.1), `fabriquer_l2.py`, `rendu/rendu_l2b.py`, `rendu/decor_l2b.py`,
  `rendu/textures_sol.py`, `validation/controler_correction.py`, `controler_L2.py`, `controler_L2b.py`,
  `faire_rapport_L2.py`, `faire_rapport_L2b.py` ; essais dans `tmp/second_controle/` (journal de la passe unique :
  `tmp/second_controle/fabrication.log`).
- Validation : `validation/controler_correction.py`, `faire_rapport_correction.py`, `rendu_valeurs.py`,
  `rapport_correction.json`, `controles_correction.json`, `constats_visuels_etape1.json`,
  `regles_demandees_correction.json`, rapports L0, L2, L2b régénérés.
- Sorties (non versionnées) : `recon/out/generateur/<scène>/` (l1, l2, l2b, rendus, tuiles) ; planches d'ensemble :
  `recon/out/generateur/catalogue_rendus/` ; planches avec photos : `recon/out/generateur/<scène>/photos_non_versionnees/planches/` ;
  journal de fabrication : `recon/generateur/tmp/second_controle/fabrication.log`.
"""

if __name__ == "__main__":
    sys.exit(main())
