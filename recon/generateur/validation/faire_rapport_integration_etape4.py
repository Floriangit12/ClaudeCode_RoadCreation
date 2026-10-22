# -*- coding: utf-8 -*-
"""Rapport de l'intégration de l'étape 4 (critères mesurés) -> validation/rapport_integration_etape4.json.

    python recon/generateur/validation/faire_rapport_integration_etape4.py

Lit, sans les recalculer (chaque fichier est écrit par son script, cité) :
  tmp/integration_etape4/fabrication_*.log        journaux de fabriquer_generateur.py --complet (code de sortie, scènes)
  tmp/integration_etape4/non_regression.json      comparer_integration_etape4.py (avant / après, toutes les scènes)
  tmp/integration_etape4/tester_descriptions.log  description/tests/tester_descriptions.py
  validation/controles_signalisation_etape4.json  controler_signalisation.py rejoué sur les sorties intégrées
  validation/controles_signalisation.json         le même contrôle, écrit par le lot L6 sur ses sorties
  validation/controles_ouvrages_etape4.json       controler_ouvrages.py rejoué (D1-D4 et V01)
  validation/controles_ouvrages.json              le même contrôle, écrit par le lot « ouvrages »
  validation/controles_vitrine.json               controler_vitrine.py (V01)
  validation/controles_signalisation_vitrine.json controler_signalisation.py sur les couches de V01
  tmp/integration_etape4/determinisme.log         fabriquer_generateur.py --verifier-determinisme
  validation/constats_visuels_integration_etape4.json   constats des rendus regardés en tuiles natives
  recon/out/generateur/catalogue_rendus/etape4_*.png    planches d'ensemble (taille)
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
TMP = GEN / "tmp" / "integration_etape4"
OUT = DEPOT / "recon" / "out" / "generateur"

# changements voulus, liste fermée (RAPPORT_integration_etape4.md § 3) : fichier (motif) -> raison
VOULUS = [
    (r"^D[1-4]_[^/]+/(ouvrages/manifest_ouvrages\.json|couches/[^/]+/(l1|l2|l2b|autoroute)/manifest_[a-z0-9]+\.json)$",
     "signature de rg::ouvrages (HDA reconstruite : nœuds des routes à niveau, sans effet sur D1-D4)"),
]


def _lire(f, defaut=None):
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def journaux():
    res = {}
    for f in sorted(TMP.glob("fabrication_*.log")):
        t = f.read_text(encoding="utf-8", errors="replace")
        code = re.findall(r"^code (\d+)\s*$", t, re.M)
        scenes = sorted(set(re.findall(r"^(\S+) : \d+ route\(s\)", t, re.M)) |
                        set(re.findall(r"^(\S+) \[[a-z, ]+\] : ", t, re.M)) |
                        set(re.findall(r"^(\S+) : ouvrages \{", t, re.M)))
        res[f.name] = {"code": int(code[-1]) if code else None, "scenes": scenes,
                       "l6": sorted(set(re.findall(r"^(\S+) : rendus \['dessus', 'l6_oblique'", t, re.M)))}
    return res


def non_regression():
    nr = _lire(TMP / "non_regression.json", {})
    out = {"scenes": len(nr), "identiques": 0, "differents": 0, "voulus": [], "non_voulus": [], "absents": [],
           "nouveaux": []}
    for s, r in sorted(nr.items()):
        out["identiques"] += r["identiques"]
        for k, v in r["differents"].items():
            cle = f"{s}/{k}"
            out["differents"] += 1
            raison = next((rz for motif, rz in VOULUS if re.match(motif, cle)), None)
            if raison and set(v.get("hda_changees", ["rg::ouvrages::1.0"])) <= {"rg::ouvrages::1.0"} and \
                    all(c.startswith("/hda") or c.startswith("/fichiers") for c in v.get("chemins", ["/hda"])):
                out["voulus"].append({"fichier": cle, "raison": raison, "chemins": v.get("chemins")})
            else:
                out["non_voulus"].append({"fichier": cle, "detail": v})
        out["absents"] += [f"{s}/{k}" for k in r["absents"]]
        out["nouveaux"] += [f"{s}/{k}" for k in r["nouveaux"]]
    return out


def _sans(d, cles=("C10",)):
    return {k: v for k, v in d.items() if k not in cles}


def controles_lots():
    a = {x["scene"]: x for x in _lire(ICI / "controles_signalisation.json", [])}
    b = {x["scene"]: x for x in _lire(ICI / "controles_signalisation_etape4.json", [])}
    diff_l6 = sorted(s for s in a if s not in b or json.dumps(_sans(a[s]), sort_keys=True) !=
                     json.dumps(_sans(b[s]), sort_keys=True))
    oa = (_lire(ICI / "controles_ouvrages.json", {}) or {}).get("scenes", {})
    ob = (_lire(ICI / "controles_ouvrages_etape4.json", {}) or {}).get("scenes", {})
    if isinstance(oa, list):
        oa = {x["scene"]: x for x in oa}
    if isinstance(ob, list):
        ob = {x["scene"]: x for x in ob}
    diff_ou = sorted(s for s in oa if s not in ob or json.dumps(oa[s].get("criteres"), sort_keys=True) !=
                     json.dumps(ob[s].get("criteres"), sort_keys=True))
    return {"L6": {"scenes": len(a), "rejouees": len(b), "mesures_differentes": diff_l6},
            "ouvrages": {"scenes": len(oa), "rejouees": len([s for s in oa if s in ob]), "mesures_differentes": diff_ou,
                         "V01": ob.get("V01_demi_echangeur_voie_rapide")}}


def main():
    j = journaux()
    nr = non_regression()
    tl = (TMP / "tester_descriptions.log").read_text(encoding="utf-8", errors="replace") \
        if (TMP / "tester_descriptions.log").exists() else ""
    m = re.search(r"descriptions valides : (\d+) / (\d+)", tl)
    cl = controles_lots()
    vit = _lire(ICI / "controles_vitrine.json", [])
    vsig = _lire(ICI / "controles_signalisation_vitrine.json", [])
    det = (TMP / "determinisme.log").read_text(encoding="utf-8", errors="replace") if (TMP / "determinisme.log").exists() else ""
    dm = re.search(r"déterminisme : (.*)", det)
    cv = _lire(ICI / "constats_visuels_integration_etape4.json", {})
    pl = sorted((OUT / "catalogue_rendus").glob("etape4_*.png"))
    tailles = {p.name: list(Image.open(p).size) for p in pl}
    scenes_fab = sorted({s for v in j.values() for s in v["scenes"]})
    codes = {k: v["code"] for k, v in j.items()}
    crit = []

    def C(i, nom, valeur, seuil, ok):
        crit.append({"id": i, "critere": nom, "valeur": valeur, "seuil": seuil, "atteint": bool(ok)})
    C("INT4-1", "une seule commande (--complet) : description -> rendu, ouvrages et signalisation compris",
      f"{len(scenes_fab)} scènes ; codes {codes}", "toutes les scènes, code 0",
      bool(j) and all(c == 0 for c in codes.values()))
    C("INT4-2", "non-régression : fichiers identiques à l'octet sauf changements voulus et listés",
      f"{nr['identiques']} identiques ; {len(nr['voulus'])} voulus ; {len(nr['non_voulus'])} non voulus ; "
      f"{len(nr['absents'])} absents ; {len(nr['nouveaux'])} nouveaux", "0 non voulu, 0 absent",
      nr["scenes"] > 0 and not nr["non_voulus"] and not nr["absents"])
    C("INT4-3", "compilation : tester_descriptions.py (rétrocompatibilité des descriptions)",
      f"{m.group(1)}/{m.group(2)}" if m else "non lancé", "toutes valides", bool(m) and m.group(1) == m.group(2))
    C("INT4-4", "contrôles des lots rejoués sur les sorties intégrées (L6 : 18 scènes ; ouvrages : D1-D4)",
      f"L6 : {cl['L6']['rejouees']}/{cl['L6']['scenes']}, mesures différentes {cl['L6']['mesures_differentes']} ; "
      f"ouvrages : {cl['ouvrages']['rejouees']}/{cl['ouvrages']['scenes']}, différentes "
      f"{cl['ouvrages']['mesures_differentes']}", "mêmes mesures que les lots",
      cl["L6"]["scenes"] > 0 and cl["L6"]["rejouees"] == cl["L6"]["scenes"] and not cl["L6"]["mesures_differentes"]
      and cl["ouvrages"]["scenes"] > 0 and not cl["ouvrages"]["mesures_differentes"])
    v01 = cl["ouvrages"]["V01"] or {}
    C("INT4-5", "vitrine V01 : critères du lot « ouvrages » (controler_ouvrages.py)",
      {k: v.get("atteint") for k, v in (v01.get("criteres") or {}).items()}, "tous atteints",
      bool(v01) and v01.get("atteint"))
    vv = vit[0] if vit else {}
    C("INT4-6", "vitrine V01 : critères de l'intégration (controler_vitrine.py : terrain sous toutes les routes, "
      "jonction des couches, bifurcation en palier, supports au sol, 0 échec)",
      {k: v.get("valeur") if not isinstance(v.get("valeur"), list) else "voir détail" for k, v in
       (vv.get("criteres") or {}).items()}, "tous atteints", bool(vv) and vv.get("atteint"))
    sig_ok = bool(vsig) and all(x["C2"]["AB4_sur_feux_ou_a_verifier"] == 0 and not x["C3"]["sous_070_non_signales"]
                                and not x["C4"]["echecs"] and not x["C5"]["sur_surface_interdite"]
                                and x["C1"]["satisfaites"] == x["C1"]["exigences"]
                                and x["C6"]["conformes"] == x["C6"]["ensembles"]
                                and x["C7"]["R11_conformes"] == x["C7"]["R11_modele"]
                                and x["C8"]["conformes"] == x["C8"]["faces"] for x in vsig)
    C("INT4-7", "vitrine V01 : contrôle du lot L6 sur chaque couche (C1-C9)",
      [{"couche": x["scene"], "C1": f"{x['C1']['satisfaites']}/{x['C1']['exigences']}",
        "C6": f"{x['C6']['conformes']}/{x['C6']['ensembles']}", "C7": f"{x['C7']['R11_conformes']}/{x['C7']['R11_modele']}",
        "C8": f"{x['C8']['conformes']}/{x['C8']['faces']}"} for x in vsig], "C1-C9 atteints", sig_ok)
    C("INT4-8", "déterminisme, une fois (second processus)", dm.group(1).strip() if dm else "non lancé", "identique",
      bool(dm) and dm.group(1).startswith("identique"))
    C("INT4-9", "rendus regardés en tuiles natives (2 à 3 vues par scène nouvelle ou enrichie)",
      f"{len(cv.get('constats', []))} constats", "toutes les planches de l'étape 4 regardées",
      bool(cv.get("constats")) and all(c.get("regarde") for c in cv["constats"]))
    C("INT4-10", "planches d'ensemble etape4_*.png <= 1092 px", tailles, "<= 1092 px de côté",
      bool(tailles) and all(max(w, h) <= 1092 for w, h in tailles.values()))
    rap = {"schema": "rg_rapport_integration_etape4/0.1", "criteres": crit, "journaux": j, "non_regression": nr,
           "controles_lots": cl, "vitrine": vv, "vitrine_signalisation": vsig}
    (ICI / "rapport_integration_etape4.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1) + "\n",
                                                          encoding="utf-8")
    for c in crit:
        print(f"{c['id']} {'oui' if c['atteint'] else 'NON'} : {c['critere']} -> {json.dumps(c['valeur'], ensure_ascii=False)[:220]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
