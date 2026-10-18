# -*- coding: utf-8 -*-
"""Contrôles du lot « bordures » (17/10/2026) : types de bordures et de caniveaux, pièces d'abaissé et d'angle,
meshes du catalogue route_fr, règles par défaut ; reliquats du contrôle de l'étape 1 (passages de Meylan, teintes,
piste, usure, avaloirs). Lecture des sorties seulement (npy, json, png) ; rien n'est fabriqué ici.

    python recon/generateur/validation/controler_bordures.py [--json validation/rapport_bordures.json]

Les mesures de rendu (teintes, piste, usure, supports des BEV et des passages, continuité des files) reprennent les
fonctions de validation/controler_correction.py (importées sans modification).
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SORTIE = DEPOT / "recon" / "out" / "generateur"
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN / "commun"))
import controler_correction as CC  # noqa: E402
import bordures_catalogue as BC  # noqa: E402

SCENE = "B01"
ETIQ = GEN / "scenes_simples" / "B01_nuancier_bordures.etiquettes.json"
TOL_VUE = 0.005                    # vue des bordures = modèle ± 5 mm (PLAN_GENERATEUR § 3, lot L2)


def _r(x, n=4):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def critere(cid, nom, valeur, seuil, atteint, detail=None):
    return {"id": cid, "nom": nom, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint),
            **({"detail": detail} if detail is not None else {})}


def types_catalogue():
    """Profils des bordures et caniveaux du catalogue route_fr (hors raccords « A->B »)."""
    cat = BC._catalogue()
    b = sorted({a["profil"] for a in cat.values() if a["famille"] == "bordures" and a.get("profil") and "->" not in a["profil"]})
    c = sorted({a["profil"] for a in cat.values() if a["famille"] == "caniveaux" and a.get("profil")})
    return b, c


def rangee(e):
    y = e["xyz"][1]
    return "G" if y > 3.0 else ("C" if abs(y) < 2.0 else "D")


def controles_b01():
    d = SORTIE / SCENE / "l2"
    el = json.loads((d / "elements.json").read_text(encoding="utf-8"))
    ent = json.loads((d / "entites.json").read_text(encoding="utf-8"))
    et = json.loads(ETIQ.read_text(encoding="utf-8"))
    out = []
    elem = [e for e in el if e.get("kind") == "element"]
    bord = [e for e in elem if e["famille"] == "bordure"]
    cani = [e for e in elem if e["famille"] == "caniveau" and e.get("type") == "caniveau"]
    # C-B1 : types du catalogue posés
    tb, tc = types_catalogue()
    poses_b = {e["profil"] for e in bord}
    poses_c = {e["profil"] for e in cani}
    manq = [p for p in tb if p not in poses_b] + [p for p in tc if p not in poses_c]
    n_cat = len(tb) + len(tc)
    out.append(critere("C-B1", "types du catalogue route_fr posés dans B01 (bordures et caniveaux)",
                       f"{n_cat - len(manq)}/{n_cat}", f"{n_cat}/{n_cat}", not manq,
                       {"bordures_catalogue": tb, "caniveaux_catalogue": tc, "manquants": manq,
                        "profils_poses": sorted(poses_b | poses_c),
                        "hors_catalogue_poses": sorted((poses_b | poses_c) - set(tb) - set(tc))}))
    # C-B2 : description : chaque type du catalogue a un mot de profil (compilateur étendu)
    V, _PF, _VM = BC.installer_description()
    mots = set(V.PROFILS_BORDURE.values()) | set(V.CANIVEAUX.values())
    sans = [p for p in tb + tc if p not in mots]
    out.append(critere("C-B2", "types du catalogue que la description peut nommer (vocabulaire étendu)",
                       f"{n_cat - len(sans)}/{n_cat}", f"{n_cat}/{n_cat}", not sans, {"sans_mot": sans}))
    # C-B3 / C-B4 : vue posée (éléments droits courants) = vue décrite ± 5 mm ; dans la vue nominale du profil
    attendu = {}
    for t in et["troncons"]:
        attendu.setdefault((t["rangee"], t["profil"]), t["vue_m"])
        if t.get("bordurette"):
            attendu.setdefault(("D", t["bordurette"]), t["bordurette_vue_m"])
    vn = BC.vues_nominales()
    ecarts, hors_nom, n = [], [], 0
    for e in bord:
        if e.get("type") != "droit" or e.get("role") != "courant":
            continue
        k = (rangee(e), e["profil"])
        if e["xyz"][1] < -5.0:                          # bordurettes (t = −6)
            k = ("D", e["profil"])
        if k not in attendu:
            continue
        n += 1
        v = 0.5 * (e["vue"] + e.get("vue_fin", e["vue"]))
        if abs(v - attendu[k]) > TOL_VUE:
            ecarts.append((e["id"], e["profil"], _r(v), attendu[k]))
        a, b = vn.get(e["profil"], (None, None))
        if a is not None and not (a - 1e-6 <= v <= b + 1e-6):
            hors_nom.append((e["id"], e["profil"], _r(v), [a, b]))
    out.append(critere("C-B3", "vue posée des éléments courants = vue décrite (± 5 mm)",
                       f"{n - len(ecarts)}/{n}", f"{n}/{n}", not ecarts, {"ecarts": ecarts[:10]}))
    prof_hors = sorted({x[1] for x in hors_nom})
    out.append(critere("C-B4", "vue posée dans la vue nominale du profil (RF-AS-profil_*, bordures.json)",
                       f"{n - len(hors_nom)}/{n}", f"{n}/{n}", not hors_nom,
                       {"profils_hors_plage": prof_hors, "exemples": hors_nom[:6]}))
    # C-B5 : pièces d'abaissé : profil de la table, vue ≤ 0,05 (0,02 ± 0,005 aux traversées)
    pieces = BC.table_pieces_abaisse()
    bateaux = [e for e in bord if e.get("role") == "bateau"]
    files = {x["id"]: x for x in ent}
    mauvais = []
    for e in bateaux:
        f = files.get(e["bordure"], {})
        cour = [iv["profil"] for iv in f.get("intervalles", []) if iv["role"] == "courant"]
        pc = cour[0] if cour else None
        att = pieces.get(pc, pc)
        v = min(e["vue"], e.get("vue_fin", e["vue"]))
        ok_v = v <= 0.05 + 1e-6
        if e["profil"] != att or not ok_v:
            mauvais.append((e["id"], pc, e["profil"], att, _r(v)))
    vues_trav = sorted({_r(min(e["vue"], e.get("vue_fin", e["vue"])), 3) for e in bateaux})
    out.append(critere("C-B5", "pièces d'abaissé : profil de la pièce du type courant (T2 → T2_bateau, T3 → "
                       "T3_surbaissee…), vue ≤ 0,05 m", f"{len(bateaux) - len(mauvais)}/{len(bateaux)}",
                       f"{len(bateaux)}/{len(bateaux)} (≥ 1 par type d'abaissé décrit)",
                       not mauvais and {e["profil"] for e in bateaux} >= {"T2_bateau", "T3_surbaissee"},
                       {"profils": sorted({e["profil"] for e in bateaux}), "vues": vues_trav, "ecarts": mauvais}))
    # C-B6 : pièces d'angle : chaque coin (déviation > 30°) d'une file est posé en pièce d'angle (2 éléments en onglet)
    coins, poses_a, manques = 0, 0, []
    for f in ent:
        xy = [tuple(p) for p in f["xy"]]
        S = f["niv_s"]
        q = [(xy[0], S[0])]
        for p, s in zip(xy[1:], S[1:]):
            if math.dist(p, q[-1][0]) > 1e-6:
                q.append((p, s))
        cf = []
        for i in range(1, len(q) - 1):
            a = (q[i][0][0] - q[i - 1][0][0], q[i][0][1] - q[i - 1][0][1])
            b = (q[i + 1][0][0] - q[i][0][0], q[i + 1][0][1] - q[i][0][1])
            dv = math.degrees(math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1]))
            if abs(dv) > 30:
                cf.append(q[i][1])
        sf = [e for e in bord if e["bordure"] == f["id"] and (e.get("angle_debut") or e.get("angle_fin"))]
        sa = {round(e["s1"] if e.get("angle_fin") else e["s0"], 1) for e in sf}
        for s in cf:
            coins += 1
            if any(abs(s - x) < 0.06 for x in sa):
                poses_a += 1
            else:
                manques.append((f["id"], _r(s, 2)))
    sens = collections.Counter(e.get("angle_sens") for e in bord if e.get("angle_sens"))
    out.append(critere("C-B6", "coins de file (déviation > 30°) posés en pièce d'angle (onglet, sens sortant / rentrant)",
                       f"{poses_a}/{coins}", f"{coins}/{coins}", poses_a == coins,
                       {"manquants": manques[:10], "sens": dict(sens)}))
    # C-B7 : continuité des files : 0 trou > 2 cm, 0 recouvrement > 2 cm
    cb, ef = CC.couverture_bordures(SORTIE / SCENE), CC.elements_files(SORTIE / SCENE)
    out.append(critere("C-B7", "continuité des files de bordures et de caniveaux (trous, recouvrements > 2 cm)",
                       f"trous {cb['longueur_trous_m']} m, recouvrements {ef['recouvrements']}", "0 m, 0",
                       cb["longueur_trous_m"] <= 0.0 and ef["recouvrements"] == 0))
    # C-B8 : meshes du catalogue : chaque élément a un asset ou un motif sur mesure ; part de longueur au catalogue
    sans_motif = [e["id"] for e in elem if not e.get("asset_id") and not e.get("asset_motif")]
    lc = sum(e["longueur"] for e in elem if e.get("asset_id"))
    lt = sum(e["longueur"] for e in elem)
    motifs = collections.Counter(e["asset_motif"].split(" (")[0].split(" :")[0] for e in elem if not e.get("asset_id"))
    out.append(critere("C-B8", "éléments posés avec un mesh du catalogue route_fr (asset_id) ou un motif de pièce sur "
                       "mesure", f"{len(elem) - len(sans_motif)}/{len(elem)} ; {100 * lc / lt:.1f} % de la longueur au "
                       "catalogue", f"{len(elem)}/{len(elem)}", not sans_motif,
                       {"longueur_catalogue_m": _r(lc, 2), "longueur_totale_m": _r(lt, 2),
                        "assets_distincts": len({e['asset_id'] for e in elem if e.get('asset_id')}),
                        "motifs_sur_mesure": dict(motifs.most_common(8))}))
    # C-B9 : contour posé (table de pj::bordure 2.1, avant le chanfrein arrière ajouté) / contour du mesh du catalogue
    t, _src = BC.construire_table_etendue()
    ec = BC.ecarts_contours_catalogue(t)
    aj, ch = {}, {}
    for k in sorted(BC.AJOUTS):
        cand = [x for x in (f"bordure_{k}_L100", f"bordure_{k}_L050") if x in BC._catalogue()]
        if not cand:
            continue
        brut = BC._nettoyer(BC.profil_rf(k)["contour_uv_m"])
        aj[k] = _r(BC._distance_contours(brut, BC.contour_catalogue(cand[0])), 5)
        ch[k] = _r(BC._distance_contours(t[k]["contour"], brut), 5)
    ex = {k: v["ecart_m"] for k, v in ec.items() if k not in BC.AJOUTS}
    out.append(critere("C-B9", "profils ajoutés : écart du contour posé (hors chanfrein arrière de 5 × 5 ou 3 × 3 mm, "
                       "bordures_elements.json aretes) au contour du mesh du catalogue route_fr",
                       f"max {max(aj.values()) * 1000:.2f} mm ({len(aj)} profils)", "≤ 1 mm",
                       max(aj.values()) <= 0.001,
                       {"ecart_hors_chanfrein_m": aj, "chanfrein_arriere_ajoute_m": ch,
                        "profils_bordures_json_m (autre équipe, non modifiés, contour posé / mesh)": ex}))
    return out, {"elements": len(elem), "bordures": len(bord), "caniveaux": len(cani)}


def controle_regles():
    """C-B10 : chaque contexte a un profil connu, une vue dans sa plage nominale (sauf écart déclaré) et des règles
    existantes."""
    import regles
    t, _ = BC.construire_table_etendue()
    vn = BC.vues_nominales()
    lignes, ko = [], []
    for c in BC.CONTEXTES:
        d = BC.bordure_par_contexte(c)
        p, v = d["profil"], d["vue_m"]
        r_ok = all(regles.existe(x) for x in d["regles"])
        if p is None:
            lignes.append((c, None, None, r_ok, True))
            if not r_ok:
                ko.append(c)
            continue
        a, b = vn.get(p, (None, None))
        dans = a is not None and a - 1e-6 <= v <= b + 1e-6
        lignes.append((c, p, v, r_ok, dans))
        if p not in t or not r_ok or not dans:
            ko.append(c)
    return critere("C-B10", "règles par défaut par contexte : profil connu, vue dans la plage nominale, règles citées "
                   "existantes", f"{len(lignes) - len(ko)}/{len(lignes)}", f"{len(lignes)}/{len(lignes)}", not ko,
                   {"contextes": [{"contexte": c, "profil": p, "vue_m": v, "regles_existantes": r, "vue_nominale": dn}
                                  for c, p, v, r, dn in lignes], "hors": ko})


def reliquats():
    out = []
    mey = ["S_M20", "S_M24", "S_M27"]
    # R1 : supports des BEV et des bandes de passage
    sup = {s: CC.supports(SORTIE / s) for s in mey}
    eb = sum(v["exceptions_bev"] for v in sup.values())
    ep = sum(v["exceptions_passage"] for v in sup.values())
    nd = sum(v["dalles"] for v in sup.values())
    nf = sum(v["faces_passage"] for v in sup.values())
    out.append(critere("R1", "Meylan : BEV sur surface piétonne ou refuge, bandes de passage sur chaussée ou piste "
                       "(passage jusqu'au trottoir)", f"BEV {nd - eb}/{nd} dalles, passage {nf - ep}/{nf} faces",
                       "0 exception", eb == 0 and ep == 0,
                       {s: {"bev": v["bev"], "passages": {k: c for k, c in v["passages"].items()}} for s, v in sup.items()}))
    # R2, R3, R4 : teintes (vue de dessus et vue conducteur)
    sc = ["S01", "S02", "S03", "S05", "S10", "S12", "S_M20", "S_M24", "S_M27", "B01"]
    lis = {s: CC.lisibilite(SORTIE / s) for s in sc}
    cond = {s: CC.teintes_conducteur(SORTIE / s) for s in sc}
    t_dessus = {s: (l or {}).get("enrobe", {}).get("teinte_hsv_median_deg") for s, l in lis.items()}
    t_cond = {s: ((c or {}).get("enrobe") or {}).get("teinte_deg") for s, c in cond.items()}
    vals = [v for v in list(t_dessus.values()) + list(t_cond.values()) if v is not None]
    out.append(critere("R2", "teinte rendue de l'enrobé (vue de dessus et vue conducteur), gris chaud des photos",
                       f"{min(vals):.1f}-{max(vals):.1f}°", "26-37°", 26 <= min(vals) and max(vals) <= 37,
                       {"dessus": t_dessus, "conducteur": t_cond}))
    bd = {s: (l or {}).get("bordure_dessus") or {} for s, l in lis.items()}
    cd = {s: (l or {}).get("caniveau_dessus") or {} for s, l in lis.items()}
    fs = {s: (c or {}).get("bordure_face_soleil") or {} for s, c in cond.items()}
    fo = {s: (c or {}).get("bordure_face_ombre") or {} for s, c in cond.items()}
    mes = []
    for nom, tab, cle_t, cle_s in (("tête (dessus)", bd, "teinte_hsv_median_deg", "saturation_hsv_median"),
                                   ("caniveau (dessus)", cd, "teinte_hsv_median_deg", "saturation_hsv_median"),
                                   ("face au soleil (conducteur)", fs, "teinte_deg", "saturation")):
        for s, v in tab.items():
            if v.get(cle_t) is not None:
                mes.append((nom, s, v[cle_t], v[cle_s]))
    ok = all(20 <= t <= 45 and sat >= 0.04 for _n, _s, t, sat in mes)
    out.append(critere("R3", "bordures et caniveaux non bleutés : teinte rendue (têtes, caniveaux, faces au soleil)",
                       f"{min(m[2] for m in mes):.1f}-{max(m[2] for m in mes):.1f}°, saturation ≥ "
                       f"{min(m[3] for m in mes):.3f}", "20-45°, saturation ≥ 0,04", ok,
                       {"mesures": mes, "faces_a_l_ombre (information : ciel bleu seul)":
                        {s: (v.get("teinte_deg"), v.get("saturation")) for s, v in fo.items() if v}}))
    pis = {s: lis[s] for s in ("S05", "S_M24", "S_M27") if lis.get(s) and lis[s].get("piste")}
    dy = {s: l.get("ecart_piste_enrobe") for s, l in pis.items()}
    tp = {s: l["piste"].get("teinte_hsv_median_deg") for s, l in pis.items()}
    out.append(critere("R4", "piste cyclable plus sombre que la chaussée et non verdâtre (vue de dessus)",
                       f"ΔY {min(dy.values()):+.3f} à {max(dy.values()):+.3f} ; teinte {min(tp.values()):.1f}-"
                       f"{max(tp.values()):.1f}°", "ΔY < 0 ; 20-45°",
                       max(dy.values()) < 0 and all(20 <= v <= 45 for v in tp.values()), {"dY": dy, "teinte": tp}))
    cu = CC.correlation_usure([SORTIE / s for s in ("S01", "S02", "S03", "S07", "S12")])
    out.append(critere("R5", "usure de l'enrobé variée par scène : corrélation de luminance au même (x, y) entre scènes",
                       f"max {cu['max']}", "< 0,2", cu["max"] is not None and cu["max"] < 0.2, cu["paires"]))
    av = {s: CC.elements_files(SORTIE / s) for s in ("S03", "S10")}
    out.append(critere("R6", "avaloirs qui remplacent l'élément de caniveau (recouvrements et trous > 2 cm)",
                       ", ".join(f"{s} : {v['avaloirs']} avaloirs, {v['recouvrements']} recouvrements, "
                                 f"{v['n_trous_contre_avaloir']} trous" for s, v in av.items()), "0 recouvrement, 0 trou",
                       all(v["recouvrements"] == 0 and v["n_trous_contre_avaloir"] == 0 for v in av.values())))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    b01, comptes = controles_b01()
    res = {"schema": "rg_controles_bordures/0.1", "scene": SCENE, "comptes_b01": comptes,
           "criteres": b01 + [controle_regles()] + reliquats()}
    for c in res["criteres"]:
        print(f"{c['id']:6} {'OK ' if c['atteint'] else 'NON'} {c['valeur']}  (seuil {c['seuil']}) — {c['nom']}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
