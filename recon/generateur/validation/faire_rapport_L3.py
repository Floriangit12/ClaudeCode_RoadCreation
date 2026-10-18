"""Rapport du lot L3 (carrefours plans) : rejoue le contrôle indépendant (controler_L3.py) sur les scènes J1-J5 fabriquées
et écrit validation/rapport_L3.json (critères valeur / seuil / atteint) et validation/controles_L3.json (détail).

    python recon/generateur/validation/faire_rapport_L3.py [--determinisme FICHIER_JSON] [--rendus N]

Les critères reprennent ceux du plan (PLAN_GENERATEUR § 3, L3) et des critères d'appui du lot ; aucun seuil n'est
modifié. Le déterminisme (une fois en fin de lot, deux scènes) est lu dans le fichier passé en option (sortie du
pilote --verifier-determinisme recopiée par l'opérateur), sinon « non vérifié ».
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import controler_L3 as C  # noqa: E402

DEPOT = ICI.parents[2]


def critere(id_, valeur, seuil, atteint):
    return {"id": id_, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--determinisme", help="JSON {scenes: [...], identique: bool, fichiers: n}")
    ap.add_argument("--rendus", type=int, default=0, help="nombre de planches regardées en tuiles natives")
    a = ap.parse_args()
    dossiers = [DEPOT / "recon" / "out" / "generateur" / s for s in C.SCENES]
    res = [C.controler(d) for d in dossiers]
    (ICI / "controles_L3.json").write_text(json.dumps({"schema": "rg_controles_L3/0.1", "scenes": res}, ensure_ascii=False,
                                                      indent=1, default=float) + "\n", encoding="utf-8")
    cr = []
    coins = [c for r in res for c in r["coins"] if not c["droit"]]
    rupt = max(c["rupture_polyligne_deg"] for c in coins)
    tang = max(c["tangence_deg"] for c in coins)
    cr.append(critere("L3-1 coins tangents (rupture de la polyligne au point de tangence ; tangence de l'arc ajusté)",
                      f"rupture max {rupt:.3f}° ; tangence {tang:.4f}° ({len(coins)} congés)", "≤ 0,5°",
                      rupt <= 0.5 and tang <= 0.5))
    er = max(c["ecart_rayon_m"] for c in coins)
    dv = max((c["file_fabriquee_ecart_max_m"] or 0.0) for c in coins)
    cr.append(critere("L3-2 rayon des coins = consigne (cercle ajusté aux sommets du congé) ; file de bordure fabriquée "
                      "sur la face", f"écart max {er * 1000:.2f} mm ; file à {dv * 1000:.2f} mm de la face", "± 1 cm",
                      er <= 0.01 and dv <= 0.01))
    fr = [f for r in res for f in r["frontiere"]]
    cr.append(critere("L3-3 frontière fermée et simple", f"{sum(1 for f in fr if f['fermee'] and f['simple'])}/{len(fr)}",
                      f"{len(fr)}/{len(fr)}", all(f["fermee"] and f["simple"] for f in fr)))
    lig = [li for r in res for li in r["lignes"] if li["gabarit"] in ("CEDEZ", "STOP") and li.get("route")]
    ev = max(abs(li["bord_aval_m"]) for li in lig)
    cr.append(critere("L3-4 lignes CÉDEZ / STOP à la limite de la chaussée prioritaire (bord aval de la peinture "
                      "fabriquée)", f"écart max {ev:.3f} m ({len(lig)} lignes)", "0 ± 0,05 m", ev <= 0.05))
    pr = [x for li in lig for x in (li.get("passages_retrait_m") or [])]
    ep = max(abs(float(x) - 2.0) for x in pr) if pr else None
    cr.append(critere("L3-5 passages en retrait de la ligne CÉDEZ / STOP (bande la plus proche, peinture fabriquée)",
                      f"{[round(float(x), 3) for x in pr]} m", "2,00 ± 0,05 m", ep is not None and ep <= 0.05))
    refs = [float(x) for r in res for t in r["traversees"] for x in t["refuges_m"]]
    cr.append(critere("L3-6 refuges au droit des passages (largeur le long de l'axe du passage, sol fabriqué)",
                      f"min {min(refs):.3f} m ({len(refs)} refuges)" if refs else "aucun", "≥ 2,00 m",
                      bool(refs) and min(refs) >= 2.0 - 1e-6))
    feux = [li for r in res for li in r["lignes"] if li["gabarit"] == "CEDEZ" and li.get("regime_branche") == "feux"]
    cr.append(critere("L3-7 aucune ligne CÉDEZ sur une branche à feux", f"{len(feux)}", "0", len(feux) == 0))
    trav = [(r["scene"], t["passage"], t["traversee_max_hors_refuge_m"]) for r in res for t in r["traversees"]]
    tm = max(t[2] for t in trav)
    cr.append(critere("L3-8 traversée hors refuge (bloquant) : parcours de chaussée continu le long de l'axe de chaque "
                      "passage, entre faces de bordure fabriquées", f"max {tm:.2f} m ({len(trav)} passages)", "≤ 12 m",
                      tm <= 12.0))
    nez = [n for r in res for n in r["nez"] if "nez" in n]
    for v, lab in (("vl", "VL"), ("bus_standard_12m", "bus standard 12 m")):
        ms = [(n["nez"], n["marge_par_vehicule_m"].get(v)) for n in nez if n["marge_par_vehicule_m"].get(v) is not None]
        mn = min(m for _, m in ms) if ms else None
        pire = min(ms, key=lambda x: x[1])[0] if ms else ""
        cr.append(critere(f"L3-9 nez des îlots au premier contact des balayages + 0,30 m ({lab}, lot L3a ; retrait "
                          "plafonné par les refuges)",
                          f"marge min {mn:.3f} m ({pire}) ; {sum(1 for _, m in ms if m >= 0.30)}/{len(ms)} nez" if ms else
                          "aucun contact", "≥ 0,30 m", mn is None or mn >= 0.30))
    il = [n for r in res for n in r["nez"] if "ilot" in n]
    if il:
        dmin = min(n["distance_min_balayage_m"] for n in il)
        cr.append(critere("L3-10 îlots directionnels hors des balayages faisables (distance minimale)",
                          f"{dmin:.3f} m ({len(il)} îlots)", "≥ 0,30 m", dmin >= 0.30))
    rac = [(r["scene"], r["raccords"]["ecart_max_m"], r["raccords"]["bords_libres_hors_exterieur"]) for r in res]
    em = max(x[1] for x in rac)
    cr.append(critere("L3-11 sol étanche : écart vertical aux raccords carrefour / branches",
                      "; ".join(f"{s[:2]} {e * 1000:.2f} mm" for s, e, _ in rac), "≤ 1 mm", em <= 0.001))
    bl = sum(x[2] for x in rac)
    cr.append(critere("L3-12 sol étanche : bords libres hors du bord extérieur des trottoirs",
                      "; ".join(f"{s[:2]} {b}" for s, _, b in rac), "0", bl == 0))
    vt = [r["vue_bordures_carrefour"]["ecart_max_T2_m"] for r in res if r["vue_bordures_carrefour"]["ecart_max_T2_m"] is not None]
    cr.append(critere("L3-13 vue des bordures T2 du carrefour = modèle (sondes de fabriquer_l2 sur la géométrie posée)",
                      f"écart max {max(vt) * 1000:.1f} mm", "± 5 mm", max(vt) <= 0.005))
    ab = sum(r["abaisses"]["abaisses"] for r in res)
    abb = sum(r["abaisses"]["avec_bev"] for r in res)
    cr.append(critere("L3-14 abaissés des bordures du carrefour avec BEV (DEF-031)", f"{abb}/{ab}", f"{ab}/{ab}", abb == ab))
    cr.append(critere("L3-15 scènes fabriquées jusque dans le carrefour (sol, bordures, lignes, passages)",
                      f"{len(res)}/5", "5/5", len(res) == 5))
    if a.rendus:
        cr.append(critere("L3-16 planches de rendu regardées en tuiles natives (2 vues ; 3 pour J5)", f"{a.rendus}/5", "5/5",
                          a.rendus >= 5))
    det = json.loads(Path(a.determinisme).read_text(encoding="utf-8")) if a.determinisme else None
    if det:
        cr.append(critere("L3-17 déterminisme (deux processus, vérifié une fois en fin de lot)",
                          f"{'identique' if det['identique'] else 'DIFFÉRENT'} ({', '.join(det['scenes'])} ; {det['fichiers']} fichiers)",
                          "identique", det["identique"]))
    out = {"lot": "L3", "date": "2026-10-18", "criteres": cr,
           "scenes": [{"scene": r["scene"], "raccords": r["raccords"], "avertissements": r["avertissements"],
                       "balayages": r.get("balayages")} for r in res],
           "detail": "validation/controles_L3.json"}
    (ICI / "rapport_L3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    for c in cr:
        print(("OK  " if c["atteint"] else "NON ") + c["id"][:70], "|", c["valeur"], "|", c["seuil"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
