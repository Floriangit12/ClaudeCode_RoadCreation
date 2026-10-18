"""Rapport du lot « autoroutes » : critères mesurés (valeur, seuil, atteint) à partir de controler_autoroutes.py.

    python recon/generateur/validation/faire_rapport_autoroutes.py [--determinisme TEXTE] [--rendus-regardes N]
        -> recon/generateur/validation/rapport_autoroutes.json et controles_autoroutes.json
"""
import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(GEN))
import controler_autoroutes as CA  # noqa: E402

TOL = 0.01                    # largeurs, modulations, biseaux : ± 1 cm (lot autoroutes)
SOURCES = {                   # largeurs sourcées des profils autoroutiers (type de bande -> (valeur, source))
    "voie_circulation": (3.5, "RF-OSM-LAR-014 autoroute_voie ; VSA 90/110 § 5.1.2 p. 21"),
    "voie_insertion": (3.5, "VSA 90/110 § 6.2.3, schéma 26 (voie de 3,50 m)"),
    "voie_deceleration": (3.5, "VSA 90/110 § 6.2.2, schéma 14 (voie de 3,50 m)"),
    "bande_arret_urgence": (3.0, "RF-OSM-LAR-014 autoroute_BAU ; VSA 90/110 § 5.3.2 p. 23 (3,00 m si PL > 2 000/j)"),
    "berme": (1.0, "RF-OSM-LAR-014 autoroute_berme ; VSA 90/110 § 6.4.5 p. 48-49"),
    "bande_derasee": (1.0, "RF-GV-TPC-002 BDG_A_normale (ICTAVRU p. 50) ; VSA 90/110 § 5.2.1 p. 22"),
}
# lignes attendues (IISR7 art. 114-2 C, 114-4 B p. 15, 117-3 p. 39-40 ; RF-MQ-SC-06, RF-MQ-INS-01, RF-MQ-DEC-01)
LIGNES_ATTENDUES = {"T1": 2, "T4": 3, "T'3": 3, "T2": 5, "continue": 3}


def critere(cid, libelle, valeur, seuil, atteint, detail=None):
    return {"id": cid, "libelle": libelle, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint), "detail": detail}


def criteres(res, determinisme=None, rendus=(0, 9)):
    out = DEPOT / "recon" / "out" / "generateur"
    cr = []
    par = {r["scene"]: r for r in res}
    # AU-01 largeurs fabriquées
    e = [x["ecart_max_m"] for r in res for x in r["largeurs"]]
    n = sum(x["coupes"] for r in res for x in r["largeurs"])
    nb = sum(len(r["largeurs"]) for r in res)
    cr.append(critere("AU-01", "Largeurs des bandes mesurées sur le sol fabriqué = modèle (A1-A4)",
                      f"écart max {max(e):.4f} m ({nb} bandes, {n} coupes)", "≤ 0,01 m", max(e) <= TOL))
    # AU-02 largeurs du modèle = sources
    ok, tot, ko = 0, 0, []
    for s in CA.SCENES:
        m = json.loads((out / s / "modele_voie.json").read_text(encoding="utf-8"))
        for p in m["profils"]:
            for b in p["bandes"]:
                if b["type"] in SOURCES and isinstance(b["largeur"], (int, float)):
                    tot += 1
                    if abs(float(b["largeur"]) - SOURCES[b["type"]][0]) <= 1e-9:
                        ok += 1
                    else:
                        ko.append(f"{s}:{p['id']}:{b['id']}={b['largeur']}")
    cr.append(critere("AU-02", "Largeurs du modèle = valeurs sourcées (voie 3,50, BAU 3,00, berme 1,00, BDG 1,00)",
                      f"{ok}/{tot} bandes", "100 %", ok == tot, ko[:10]))
    # AU-03 modulations
    et, nt, mods = [], 0, set()
    for r in res:
        for l_ in r["lignes"]:
            if l_["trait_regle"] is None:
                continue
            mods.add(l_["modulation"])
            if l_["trait_m"]:
                et += [abs(v - l_["trait_regle"]) for v in l_["trait_m"]]
                nt += l_["tirets"]
            if l_["intervalle_m"]:
                et += [abs(v - l_["intervalle_regle"]) for v in l_["intervalle_m"]]
    cr.append(critere("AU-03", "Modulations des lignes (trait, intervalle) mesurées sur la peinture = RF-MQ-MOD-*",
                      f"écart max {max(et):.4f} m ({nt} tirets ; {', '.join(sorted(mods))})", "≤ 0,01 m", max(et) <= TOL))
    # AU-04 largeurs des lignes = largeur_u × u (u = 0,075 RF-MQ-U-01)
    ew, nl, demi = [], 0, []
    for r in res:
        for l_ in r["lignes"]:
            ku = LIGNES_ATTENDUES.get(l_["modulation"])
            if ku is None or not l_["largeur_m"]:
                continue
            w = ku * 0.075
            if l_["largeur_m"][1] < 0.6 * w:                   # demi-ligne au bord extérieur d'un profil (rg::marquages)
                demi.append(f"{r['scene']}:{l_['route']}:{l_['cle']}={l_['largeur_m'][0]}")
                continue
            ew += [abs(v - w) for v in l_["largeur_m"]]
            nl += 1
    cr.append(critere("AU-04", "Largeur des lignes mesurée = largeur_u × u (u = 7,5 cm sur autoroute, RF-MQ-U-01)",
                      f"écart max {max(ew):.4f} m ({nl} lignes)", "≤ 0,01 m", max(ew) <= TOL,
                      {"demi_lignes_au_bord_exterieur_du_profil": demi}))
    # AU-05 lignes conformes IISR autoroute
    cl = []
    for r in res:
        for l_ in r["lignes"]:
            cl.append(f"{r['scene']}:{l_['route']}:{l_['cle'].rsplit('_', 2)[0]}:{l_['modulation']}")
    cr.append(critere("AU-05", "Modulations du modèle conformes IISR7 autoroutes (délimitation T1 2u, BAU T4 3u, TPC continue 3u, "
                      "bretelle T'3 3u et rive sans BAU continue 3u, insertion / décélération T2 5u)",
                      f"{len(cl)} lignes, modulations {sorted({x.split(':')[-1] for x in cl})}", "100 % conformes",
                      all(x.split(":")[-1] in LIGNES_ATTENDUES for x in cl), cl))
    # AU-06 séparateurs béton
    bet = [(r["scene"], r["equipements"]["beton"]) for r in res if r["equipements"] and r["equipements"].get("beton")]
    eb = []
    cont = []
    for sc, b in bet:
        for c in b["coupes"]:
            eb += [abs(c["base_m"] - 0.60), abs(c["haut_sur_sol_m"] - 0.81)]
        cont.append(b["s_min"] <= 1e-3 and abs(b["s_max"] - b["longueur_route_m"]) <= 1e-3 and b["pas_max_m"] <= 1.0 + 1e-3)
    ncoupes = sum(len(b["coupes"]) for _, b in bet)
    cr.append(critere("AU-06", "Séparateur béton DBA (catalogue retenue_DBA, Cerema DR p. 32) : base 0,60 et hauteur 0,81 "
                      "au-dessus du sol fabriqué, continu sur toute la principale",
                      f"écart max {max(eb):.4f} m sur {ncoupes} coupes ({len(bet)} scènes) ; continu {sum(cont)}/{len(cont)}",
                      "≤ 0,01 m ; continu", max(eb) <= TOL and all(cont)))
    # AU-07 glissières
    gl = par.get("A2_autoroute_2x3_glissieres", {}).get("equipements", {}).get("glissieres", [])
    eg = []
    for g in gl:
        eg += [abs(v - 0.70) for v in g["haut_lisse_sur_sol_m"]]
        if g["pas_supports_m"]:
            eg += [abs(v - 2.0) for v in g["pas_supports_m"]]
        if g["limite_t_m"] is not None:
            eg += [abs(v - g["limite_t_m"]) for v in g["face_t_m"]]
    cr.append(critere("AU-07", "Glissières GS2 (catalogue, fiche Aximum GS2, Setra BVL p. 30) : haut de lisse 0,70 au-dessus "
                      "du sol, supports tous les 2,00 m, face de la lisse sur la limite du modèle",
                      f"{len(gl)} glissières, {sum(g['supports'] for g in gl)} supports ; écart max {max(eg) if eg else None:.4f} m",
                      "2 glissières ; ≤ 0,01 m", len(gl) == 2 and eg and max(eg) <= TOL, gl))
    # AU-08 / AU-09 voies auxiliaires
    for cid, sc, lib, biseau_src in (
            ("AU-08", "A3_bretelle_entree", "Voie d'insertion (A3) : largeur fabriquée = loi du modèle (3,50 m sur la zone "
             "parallèle, biseau linéaire de 75 m jusqu'à 0) ; zone de manœuvre de 200 m depuis E.1,00 (VSA 90/110 p. 34, "
             "schéma 26)", 75.0),
            ("AU-09", "A4_bretelle_sortie", "Voie de décélération (A4) : biseau de 150 m de 0 à 3,50 m (VSA 90/110 p. 31, "
             "schéma 14), largeur fabriquée = loi du modèle", 150.0)):
        b = par[sc]["bretelle"]
        va = b["voie_auxiliaire"]
        bm = va.get("biseau_mesure") or {}
        val = f"écart de largeur max {va['ecart_largeur_max_m']:.4f} m ; biseau {bm.get('longueur_m')} m"
        ok = va["ecart_largeur_max_m"] <= TOL and abs((bm.get("longueur_m") or 0) - biseau_src) <= TOL
        if sc.startswith("A3"):
            zm = 475.0 - (b["s_jonction"] - b["point_1m_depuis_jonction_m"])
            val += f" ; zone de manœuvre depuis E.1,00 : {zm:.3f} m"
            ok = ok and abs(zm - 200.0) <= 0.1
        cr.append(critere(cid, lib, val, f"≤ 0,01 m ; biseau {biseau_src:.0f} m ± 0,01" + (" ; 200 ± 0,1 m" if sc.startswith("A3") else ""), ok))
    # AU-10 points à 1 m / 5 m et obliquité
    att = {"A3_bretelle_entree": (25.0, 125.0, 0.04), "A4_bretelle_sortie": (33.0, 165.0, 1 / 33)}
    vals, ok = [], True
    for sc, (p1, p5, ob) in att.items():
        b = par[sc]["bretelle"]
        vals.append(f"{sc[:2]} : E/S.1,00 à {b['point_1m_depuis_jonction_m']} m, E/S.5,00 à {b['point_5m_depuis_jonction_m']} m, "
                    f"obliquité {b['obliquite']}")
        ok = ok and abs(b["point_1m_depuis_jonction_m"] - p1) <= 0.1 and abs(b["point_5m_depuis_jonction_m"] - p5) <= 0.1 \
            and abs(b["obliquite"] - ob) <= 5e-4
    cr.append(critere("AU-10", "Points à 1,00 m et 5,00 m et obliquité des bretelles (VSA 90/110 p. 38 : entrée 1/25 ; sortie 1/33)",
                      " ; ".join(vals), "± 0,10 m ; obliquité ± 0,0005", ok))
    # AU-11 chevrons
    ch = [par[s]["bretelle"]["chevrons"] for s in att]
    ea = max(abs(v - 26.565) for c in ch for v in c["angle_bissectrice_deg"])
    ew_ = max(abs(v - 0.50) for c in ch for v in c["largeur_m"])
    ep = max(abs(v - 1.85) for c in ch for v in c["pas_perpendiculaire_m"])
    am = sum(c["pointe_vers_amont"][0] for c in ch), sum(c["pointe_vers_amont"][1] for c in ch)
    cr.append(critere("AU-11", "Chevrons des musoirs mesurés sur la peinture (RF-MQ-HACH-02, DEF-020) : 2 pour 1 sur la "
                      "bissectrice (26,565°), bandes de 0,50, pas perpendiculaire 1,85, pointe vers le conducteur",
                      f"{sum(c['bandes'] for c in ch)} bandes ; angle ± {ea:.3f}° ; largeur ± {ew_:.4f} m ; pas ± {ep:.4f} m ; "
                      f"pointe vers l'amont {am[0]}/{am[1]}", "± 0,1° ; ± 0,01 m ; 100 %",
                      ea <= 0.1 and ew_ <= TOL and ep <= TOL and am[0] == am[1]))
    # AU-12 raccord vertical et sol du musoir
    rz = max(par[s]["bretelle"]["raccord_vertical"]["ecart_z_jonction_max_m"] for s in att)
    mz = max(par[s]["bretelle"]["sol_musoir"]["marche_z_bords_max_m"] for s in att)
    dz = [par[s]["bretelle"]["raccord_vertical"]["dz_applique_m"][0] for s in att]
    cr.append(critere("AU-12", "Raccord vertical bretelle / principale à la jonction et sol du musoir raccordé aux deux sols",
                      f"écart de Z à la jonction {rz:.4f} m (dz appliqué {dz}) ; marche aux bords du musoir {mz:.4f} m",
                      "≤ 0,01 m", rz <= TOL and mz <= TOL))
    # AU-13 BAU interrompue au droit du musoir
    bi = [par[s]["bretelle"]["bau_interrompue"] for s in att]
    cr.append(critere("AU-13", "BAU de la principale interrompue au droit du musoir (A3 [175 ; 300], A4 [500 ; 665])",
                      f"{[x['intervalles_s'] for x in bi]} : {sum(x['sommets_de_bau_dedans'] for x in bi)} sommet de BAU dedans",
                      "0", sum(x["sommets_de_bau_dedans"] for x in bi) == 0))
    # AU-14 flèches
    cr.append(critere("AU-14", "Gabarits des flèches ± 1 mm (flèches ×4/3 demandées)",
                      "sans objet : aucune flèche dans A1-A4 (IISR7 annexe B.1 : pas d'homothétie de la flèche de "
                      "rabattement ; ×4/3 = flèches directionnelles, nota B.2/B.3 p. 62-63, liées à une affectation non décrite)",
                      "± 1 mm", False))
    if determinisme is not None:
        cr.append(critere("AU-15", "Déterminisme (vérifié une fois en fin de lot, 2 scènes)", determinisme,
                          "identique", determinisme.startswith("identique")))
    cr.append(critere("AU-16", "Rendus regardés en tuiles natives ≤ 1092 px (2 vues par scène, 3 pour A3)",
                      f"{rendus[0]}/{rendus[1]} vues", f"{rendus[1]}/{rendus[1]}", rendus[0] == rendus[1]))
    return cr


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--determinisme")
    ap.add_argument("--rendus-regardes", type=int, default=0)
    ap.add_argument("--rendus-total", type=int, default=9)
    a = ap.parse_args()
    out = DEPOT / "recon" / "out" / "generateur"
    res = [CA.controler(out / s) for s in CA.SCENES]
    (ICI / "controles_autoroutes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cr = criteres(res, a.determinisme, (a.rendus_regardes, a.rendus_total))
    rap = {"schema": "rg_rapport_lot/0.1", "lot": "autoroutes", "scenes": list(CA.SCENES), "criteres": cr,
           "atteints": sum(c["atteint"] for c in cr), "total": len(cr)}
    (ICI / "rapport_autoroutes.json").write_text(json.dumps(rap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for c in cr:
        print(f"{c['id']} {'OK ' if c['atteint'] else 'NON'} {c['valeur']} (seuil {c['seuil']})")


if __name__ == "__main__":
    main()
