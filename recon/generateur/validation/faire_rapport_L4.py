"""Rapport du lot L4 (marquages, trajectoires, conflits et zone de conflit des carrefours J1-J5) : critères mesurés
(valeur, seuil, atteint) à partir du contrôle indépendant (controler_L4.py) ; écrit validation/rapport_L4.json et
validation/controles_L4.json (détail).

    python recon/generateur/validation/faire_rapport_L4.py [--determinisme "identique (N fichiers)"]

Les constats visuels (planches regardées en entier, vues en tuiles natives) sont lus dans
validation/constats_visuels_L4.json.
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
import controler_L4 as C  # noqa: E402

SCENES = C.SCENES


def fmt(x, n=3):
    return "—" if x is None else f"{x:.{n}f}".replace(".", ",")


def critere(cid, libelle, valeur, seuil, atteint, regles=""):
    return {"id": cid, "critere": libelle, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint), "regles": regles}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--determinisme", default="non vérifié")
    a = ap.parse_args()
    R = {r["scene"]: r for r in (C.controler(s) for s in SCENES)}
    (ICI / "controles_L4.json").write_text(json.dumps(list(R.values()), ensure_ascii=False, indent=1, default=float) + "\n",
                                           encoding="utf-8")
    cr = []
    fl = [R[s]["fleches"] for s in SCENES if R[s]["fleches"]["fleches"]]
    n_fl = sum(f["fleches"] for f in fl)
    eg = max((f["ecart_gabarit_max_mm"] for f in fl), default=0.0)
    cen = max((f["centrage_max_m"] for f in fl), default=0.0)
    ori = max((f["orientation_max_deg"] for f in fl), default=0.0)
    pl = [p["distance_m"] for f in fl for p in f["pointe_ligne"]]
    idist = [i["m"] for f in fl for i in f["interdistances"]]
    cpt = [c for f in fl for c in f["comptes"]]
    cr.append(critere("L4-1", "flèches d'affectation : sommets = gabarit du dossier 08", f"écart max {fmt(eg, 3)} mm ({n_fl} flèches)",
                      "± 1 mm", eg <= 1.0, "RF-MQ-DIR-02, RF-MQ-DIR-09 ; IISR7 annexes B.2, B.3"))
    cr.append(critere("L4-2", "flèches centrées dans la voie (axe L1 des voies)", f"{fmt(100 * cen, 2)} cm", "± 2 cm",
                      cen <= 0.02, "RF-MQ-DIR-03"))
    cr.append(critere("L4-3", "flèches orientées le long de la voie", f"{fmt(ori, 3)}°", "± 0,5°", ori <= 0.5, "RF-MQ-DIR-03"))
    okp = bool(pl) and all(p is not None and abs(p - 1.5) <= 0.02 for p in pl)
    cr.append(critere("L4-4", "pointe de la dernière flèche à la ligne (bord amont de la peinture)",
                      f"{fmt(min(x for x in pl if x is not None), 3)} à {fmt(max(x for x in pl if x is not None), 3)} m ({len(pl)} voies)" if pl else "—",
                      "1,50 ± 0,02 m", okp, "DEF-017, ARB-11"))
    oki = bool(idist) and all(abs(x - 20.0) <= 0.05 for x in idist)
    cr.append(critere("L4-5", "interdistance des flèches (pointe à pointe)",
                      f"{fmt(min(idist), 3)} à {fmt(max(idist), 3)} m ({len(idist)})" if idist else "—", "20 ± 0,05 m", oki,
                      "DEF-017, ARB-11"))
    okn = bool(cpt) and all(c["posees"] == min(c["demandees"], c["tenant_dans_la_voie"]) and c["posees"] >= 2 for c in cpt)
    cr.append(critere("L4-6", "nombre de flèches : 3 par voie, 2 si la voie (formée et droite) est courte",
                      ", ".join(f"{c['voie']} {c['posees']}/{c['demandees']}" for c in cpt) or "—",
                      "posées = min(demandées, tenant dans la voie) ≥ 2", okn, "RF-MQ-DIR-04, ARB-11"))
    sas = [x for s in SCENES for x in R[s]["sas"]]
    oks = bool(sas) and all(x["axe_m"] <= 0.02 and (x["centrage_m"] or 0) <= 0.02 and 3.0 <= (x["profondeur_sas_m"] or 0) <= 5.0
                            for x in sas)
    cr.append(critere("L4-7", "sas vélos : figurine dans l'axe de chaque voie, centrée entre les lignes ; profondeur",
                      f"{len(sas)} figurines ; axe ≤ {fmt(max(x['axe_m'] for x in sas), 3)} m ; centrage ≤ "
                      f"{fmt(max(x['centrage_m'] for x in sas), 3)} m ; profondeur {fmt(min(x['profondeur_sas_m'] for x in sas), 3)} m"
                      if sas else "—", "± 2 cm ; 3 à 5 m (bord à bord)", oks, "RF-MQ-SAS-01, DEF-016"))
    tr = [R[s]["trajectoires"] for s in SCENES]
    nveh = sum(len(t["vehicule"]) for t in tr)
    nf = sum(len(t["non_faisables"]) for t in tr)
    rmin = min(t["rayon_min_m"] for t in tr if t["rayon_min_m"] is not None)
    cr.append(critere("L4-8", "trajectoires de rayon ≥ rayon d'axe minimal du véhicule de projet (VL, lot L3a)",
                      f"rayon mesuré min {fmt(rmin, 3)} m ; {nveh - nf}/{nveh} trajectoires", f"≥ {fmt(C.R_VL, 3)} m (100 %)",
                      nf == 0, "RF-GV-TRJ-006"))
    tang = max(t["tangence_bouts_max_deg"] for t in tr)
    dec = max(t["decalage_bouts_max_m"] for t in tr)
    rup = max(t["rupture_max_deg"] for t in tr)
    cr.append(critere("L4-9", "trajectoires droite – arc – droite tangentes aux voies (bouts sur l'axe L1, tangence) ; "
                      "rupture des polylignes", f"bouts {fmt(1000 * dec, 1)} mm, {fmt(tang, 3)}° ; rupture max {fmt(rup, 3)}°",
                      "≤ 1 cm, ≤ 0,5° ; ≤ 0,8° (pas angulaire des arcs)", dec <= 0.01 and tang <= 0.5 and rup <= 0.8 + 1e-3,
                      "RF-GV-TRJ-006"))
    gu = {s: R[s]["guidage"] for s in SCENES}
    okg = all((g["lignes"] == 0) == (len(g["trajectoires_guidees_decrites"]) == 0) for g in gu.values()) and \
        gu["J5_carrefour_complexe"]["lignes"] == 1
    cr.append(critere("L4-10", "guidage seulement là où il est décrit (ARB-08)",
                      ", ".join(f"{s[:2]} {g['lignes']} ligne(s) / {len(g['trajectoires_guidees_decrites'])} trajectoire(s) décrite(s)"
                                for s, g in gu.items()), "J5 : 1 ligne pour 2 TAG décrits ; J1-J4 : 0", okg,
                      "ARB-08, RF-OSM-MRQ-041, RF-MQ-GUI-01"))
    g5 = gu["J5_carrefour_complexe"]
    tt, iv, ll = g5["traits"], g5["intervalles"], g5["largeurs"]
    okm = bool(tt) and all(abs(x - 0.5) <= 0.01 for x in tt) and all(abs(x - 0.5) <= 0.01 for x in iv) and \
        all(abs(x - 0.10) <= 0.002 for x in ll)
    cr.append(critere("L4-11", "ligne de guidage T'2 0,10 : traits, intervalles (le long de la courbe), largeur",
                      f"{len(tt)} traits {fmt(min(tt), 4)}-{fmt(max(tt), 4)} m ; intervalles {fmt(min(iv), 4)}-{fmt(max(iv), 4)} m ; "
                      f"largeur {fmt(min(ll), 4)}-{fmt(max(ll), 4)} m" if tt else "—",
                      "0,50 ± 0,01 ; 0,50 ± 0,01 ; 0,10 ± 0,002 m", okm, "RF-MQ-MOD-T'2, RF-MQ-GUI-01, ARB-08"))
    okt = g5["tag_croisements"] == 0 and (g5["garde_caisse_min_m"] or -1) >= 0
    cr.append(critere("L4-12", "TAG à l'indonésienne (phase spéciale P2) : axes sans croisement ; caisse du VL (1,80 m) de "
                      "son côté de la ligne", f"croisements {g5['tag_croisements']} ; garde {fmt(g5['garde_caisse_min_m'], 3)} m",
                      "0 ; ≥ 0 m", okt, "RF-MQ-CAR-03, DEF-021"))
    ba = g5["balayages"] or {}
    okb = (ba.get("recouvrement_m2") or 0) == 0 and all((x or 0) == 0 for x in ba.get("contre_bordures_m", []))
    cr.append(critere("L4-13", "balayages du VL (lot L3a, rétroviseurs 2,10 m) des deux TAG guidés : disjoints et hors bordures",
                      f"recouvrement {fmt(ba.get('recouvrement_m2'), 2)} m² ; contre le nez du TPC "
                      f"{', '.join(fmt(x, 2) for x in ba.get('contre_bordures_m', []))} m", "0 m² ; 0 m", okb,
                      "RF-GV-TRJ-006 (garde 1,25 m), plan § 2.4 étape 9"))
    zl = sum(R[s]["zone"]["lignes_dans_la_zone"] for s in SCENES)
    cr.append(critere("L4-14", "zone de conflit : aucune ligne longitudinale dedans hors guidage (et hors discontinue de la "
                      "route prioritaire, RF-MQ-CAR-01)",
                      f"{zl} ligne(s) ; {sum(R[s]['zone']['retires'] for s in SCENES)} morceaux retirés, "
                      f"{sum(R[s]['zone']['coupes'] for s in SCENES)} coupés à la ligne d'arrêt",
                      "0", zl == 0, "RF-MQ-CAR-02, RF-MQ-CAR-04"))
    cf = {s: R[s]["conflits"] for s in SCENES}
    crois = ", ".join(f"{s[:2]} {c['points_CU']['croisement']}/{c['points_CU']['total']}" for s, c in cf.items())
    okc = all(cf[s]["points_CU"]["croisement"] == 16 and cf[s]["points_CU"]["total"] == 32 for s in ("J2_croix_stop", "J3_croix_feux"))
    cr.append(critere("L4-15", "points de conflit comptés et rapportés avec la liste des mouvements ; croix complète J2, J3 = "
                      "CU (16 croisements, 32 conflits)", f"croisements/total : {crois}", "J2, J3 : 16 / 32", okc,
                      "RF-GV-TRJ-001 ; CU p. 120-122"))
    ecarts = [e for s in SCENES for e in cf[s]["ecarts"]]
    cr.append(critere("L4-16", "conflits : géométrie (intersections des axes) = topologie (ordre des bouts autour du centre)",
                      f"{len(ecarts)} écart(s)" + (f" : {'; '.join(ecarts)}" if ecarts else ""), "0 écart",
                      not ecarts, "contrôle d'appui"))
    gr = {s: R[s]["graphe"] for s in SCENES}
    okgr = all(not g["entrantes_sans_successeur"] and not g["connecteurs_sans_voie"] and g["etiquettes"] <= 32 and
               g["raccord_max_m"] <= 0.001 and g["raccord_angle_max_deg"] <= 0.5 for g in gr.values())
    cr.append(critere("L4-17", "graphe de voies : chaque voie entrante a ≥ 1 successeur ; ≤ 32 étiquettes ; raccords",
                      f"{sum(g['voies_entrantes'] for g in gr.values())} voies entrantes, "
                      f"{sum(len(g['entrantes_sans_successeur']) for g in gr.values())} sans successeur ; étiquettes ≤ "
                      f"{max(g['etiquettes'] for g in gr.values())} ; raccords ≤ {fmt(1000 * max(g['raccord_max_m'] for g in gr.values()), 2)} mm, "
                      f"{fmt(max(g['raccord_angle_max_deg'] for g in gr.values()), 3)}°", "0 ; ≤ 32 ; ≤ 1 mm, ≤ 0,5°", okgr,
                      "12M § 7"))
    pe = [(s, f, v) for s in SCENES for f, v in R[s]["peinture"].items()]
    okpe = bool(pe) and all(v["sans_sol"] == 0 and abs(v["au_dessus_min_m"] - (0.002 if f == "lignes_l4" else 0.003)) <= 0.0003
                            and abs(v["au_dessus_max_m"] - (0.002 if f == "lignes_l4" else 0.003)) <= 0.0003
                            and abs(v["centres_min_m"] - (0.002 if f == "lignes_l4" else 0.003)) <= 0.0003
                            and abs(v["centres_max_m"] - (0.002 if f == "lignes_l4" else 0.003)) <= 0.0003 for s, f, v in pe)
    ec = max(max(abs(v[k] - (0.002 if f == "lignes_l4" else 0.003)) for k in ("au_dessus_min_m", "au_dessus_max_m",
                                                                             "centres_min_m", "centres_max_m"))
             for s, f, v in pe) if pe else None
    cr.append(critere("L4-18", "peinture du lot posée sur le sol fabriqué : dessus − sol = 2 mm (lignes) / 3 mm (marques)",
                      f"écart max {fmt(1000 * ec, 3)} mm (sommets et centres des faces du dessus)" if ec is not None else "—",
                      "± 0,3 mm", okpe, "TQ-MQG-002, TQ-MQG-005"))
    ax = {s: R[s]["axe_rives"] for s in SCENES}
    okax = all(ax[s]["tirets_axe_ajoutes"] >= 1 for s in ("J1_T_cedez", "J2_croix_stop", "J4_ilots_directionnel_separateurs")) \
        and all(a_["rives_restantes_au_droit_des_affluentes"] == 0 for a_ in ax.values())
    cr.append(critere("L4-19", "discontinue axiale de la route prioritaire non interrompue au droit de l'intersection ; rives "
                      "interrompues au droit des affluentes",
                      "; ".join(f"{s[:2]} : {ax[s]['tirets_axe_ajoutes']} tiret(s)" for s in ("J1_T_cedez", "J2_croix_stop",
                                                                                              "J4_ilots_directionnel_separateurs"))
                      + f" ; rives restantes {sum(a_['rives_restantes_au_droit_des_affluentes'] for a_ in ax.values())}",
                      "≥ 1 tiret par carrefour à route prioritaire ; 0 rive", okax, "RF-MQ-CAR-01, RF-MQ-SC-11"))
    cv = ICI / "constats_visuels_L4.json"
    vis = json.loads(cv.read_text(encoding="utf-8")) if cv.exists() else {}
    nv = sum(1 for s in SCENES if (vis.get(s) or {}).get("regardee"))
    cr.append(critere("L4-20", "planches de rendu regardées en entier (≤ 1092 px), vues en tuiles natives (J5 : 4 vues ; J1-J4 : 2)",
                      f"{nv}/5", "5/5", nv == 5, "consignes du dépôt"))
    cr.append(critere("L4-21", "déterminisme (deux processus, une fois en fin de lot, 2 scènes)", a.determinisme, "identique",
                      a.determinisme.startswith("identique"), "README_HDA § 9.2"))
    rap = {"schema": "rg_rapport_lot/0.1", "lot": "L4", "titre": "marquages, trajectoires, conflits et zone de conflit des carrefours plans",
           "scenes": list(SCENES), "criteres": cr,
           "atteints": sum(1 for c in cr if c["atteint"]), "total": len(cr),
           "resume_scenes": {s: {"trajectoires": len(R[s]["trajectoires"]["vehicule"]) + R[s]["trajectoires"]["velo"],
                                 "conflits_points_CU": R[s]["conflits"]["points_CU"],
                                 "conflits_paires": R[s]["conflits"]["geometrie"],
                                 "zone_m2": R[s]["zone"]["aire_m2"], "fleches": R[s]["fleches"]["fleches"],
                                 "figurines_sas": len(R[s]["sas"]), "guidage": R[s]["guidage"]["lignes"]} for s in SCENES}}
    (ICI / "rapport_L4.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    for c in cr:
        print(f"| {c['id']} {c['critere']} | {c['valeur']} | {c['seuil']} | {'oui' if c['atteint'] else '**non**'} |")
    print(f"{rap['atteints']}/{rap['total']} critères atteints")


if __name__ == "__main__":
    main()
