"""Contrôle indépendant du lot L6 (signalisation verticale et feux) — Python du système, sans Houdini.

    python recon/generateur/validation/controler_signalisation.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Mesures refaites sur la géométrie FABRIQUÉE (sol l2/sol_*.npy, classes du sol) et sur les instances posées par
rg::signalisation (l6/instances.json, l6/ensembles.json), sans relire les mesures de l'HDA :
  C1  P14-1  régimes signalés : chaque exigence du plan (branche à régime, voies affectées, sens unique, ralentisseur,
             passage surélevé, limite d'agglomération, répétition à gauche) a ses panneaux posés (statut ≠ échec) ;
  C2  P14-2  0 AB4 sur une branche à feux ou « stop_a_verifier » (ARB-19) ;
  C3  P14-3  bord de chaque plaque à ≥ 0,70 m de la chaussée visible, sauf contrainte signalée (motif de l'ensemble) ;
  C4  P14-5  cheminement de 1,40 m libre au droit de chaque support posé sur un trottoir ; plaque au-dessus d'un
             trottoir : bas ≥ 2,20 m ;
  C5  L6     aucun support sur une surface circulée (chaussée, BDD, BAU, piste, couronne franchissable), un îlot peint
             (zone neutralisée) ou un abaissé (bateau fabriqué et zone d'attente de 1,20 m, ou fond à vue < 0,03 m) ;
  C6  L6     hauteurs : bas de la plaque la plus basse = hauteur réglementaire du plan ± 2 cm (DEF-025, DEF-026, DEF-027,
             L6-SV-SURPLOMB.GABARIT ; îlot en agglomération : valeur [G] de confiance faible, ARB-04) ;
  C7  IISR6  feux : chaque R11 du modèle posé, à droite de son couloir (ou sur l'îlot qui le borde), au droit ou à l'aval
             de sa ligne d'effet, bas du boîtier ≥ 2,00 m, axe du feu supérieur < 4,20 m, ≤ 2 ensembles juxtaposés par
             support ; R12 aux deux extrémités de chaque traversée gérée ;
  C8  IISR1  orientation : face tournée vers l'usager visé (écart à la direction opposée au trafic ≤ 15°) ;
  C9  P14-8  séquences : EB10 et EB20 dos à dos à la limite d'agglomération ; B14 répété à gauche sur 2 × 2 voies ;
  C10        lisibilité dans la vue du conducteur : les plaques visées sont dans l'image et l'une mesure ≥ 40 px de large
             (tête de feu R11 de 0,27 m : ≥ 15 px) [G].
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SORTIE = DEPOT / "recon" / "out" / "generateur"
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "hda" / "rg_signalisation"))
import plan_signalisation as PS  # noqa: E402  (catalogue et étendues des assets seulement)

SCENES = ("E01_entree_agglomeration", "J1_T_cedez", "J2_croix_stop", "J3_croix_feux",
          "J4_ilots_directionnel_separateurs", "J5_carrefour_complexe", "J6_carrefour_complexe_2x2",
          "G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20",
          "G4_giratoire_multivoie_D50", "A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree",
          "A4_bretelle_sortie", "S07", "S08", "S10")
CHAUSSEE = set("voie_circulation voie_bus voie_tourne_gauche voie_tourne_droite voie_insertion voie_deceleration "
               "voie_acceleration voie_stockage bande_cyclable stationnement livraison chaussee_partagee "
               "carrefour_chaussee musoir sous_element caniveau_releve tampon".split())
PEINT = {"zone_neutralisee"}
CIRCULEES = set("bande_derasee bande_arret_urgence accotement_revetu surlargeur piste_cyclable voie_verte".split())
PIETONS = set("trottoir carrefour_trottoir quai_bus chemin_pieton".split())
ILOTS = set("terre_plein carrefour_ilot giratoire_ilot separateur ilot".split())
FRANCHISSABLES = {"paves_beton", "paves_granit"}
BORD, CHEM, SURPL, TOL_H, VUE = 0.70, 1.40, 2.20, 0.02, 0.03


def _r(x, n=3):
    return None if x is None else round(float(x), n)


class Sol:
    """Sol fabriqué : triangles (local Z haut) et classes ; requêtes « face du dessus » en un point."""

    def __init__(self, d):
        from shapely.geometry import Polygon
        from shapely.strtree import STRtree
        pts = np.load(d / "l2" / "sol_points.npy")[:, :3]
        faces = np.load(d / "l2" / "sol_faces.npy")
        comptes = np.load(d / "l2" / "sol_comptes.npy")
        att = np.load(d / "l2" / "sol_attributs.npy")
        voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
        self.polys, self.cls, self.mat, self.z = [], [], [], []
        k = 0
        for n, a in zip(comptes, att):
            idx = faces[k:k + n]
            k += n
            P = pts[idx]
            if n < 3:
                continue
            poly = Polygon(P[:, :2])
            if not poly.is_valid or poly.area < 1e-8:          # murs (verticaux) et faces dégénérées
                continue
            self.polys.append(poly)
            self.cls.append(voc["classe"][int(a[4])])
            self.mat.append(voc["materiau_id"][int(a[5])])
            self.z.append(P)
        self.tree = STRtree(self.polys)

    def dessus(self, x, y):
        """(classe, matériau, z) de la face la plus haute au point (x, y) ; None hors du sol."""
        from shapely.geometry import Point
        p = Point(x, y)
        best = None
        for i in self.tree.query(p):
            if not self.polys[i].covers(p):
                continue
            P = self.z[i]
            # plan de la face (3 premiers sommets non alignés)
            a, b, c = P[0], P[1], P[2]
            n = np.cross(b - a, c - a)
            if abs(n[2]) < 1e-9:
                continue
            z = a[2] - (n[0] * (x - a[0]) + n[1] * (y - a[1])) / n[2]
            if best is None or z > best[2]:
                best = (self.cls[i], self.mat[i], z)
        return best

    def z_classes(self, x, y, classes):
        """Altitude la plus haute des faces des classes données au point (x, y), ou None."""
        from shapely.geometry import Point
        p = Point(x, y)
        best = None
        for i in self.tree.query(p):
            if self.cls[i] not in classes or not self.polys[i].covers(p):
                continue
            P = self.z[i]
            a, b, c = P[0], P[1], P[2]
            n = np.cross(b - a, c - a)
            if abs(n[2]) < 1e-9:
                continue
            z = a[2] - (n[0] * (x - a[0]) + n[1] * (y - a[1])) / n[2]
            best = z if best is None else max(best, z)
        return best

    def chaussee_visible(self):
        """Union de la chaussée (et des îlots peints) moins les îlots posés dessus (sol de carrefour sous les îlots)."""
        from shapely.ops import unary_union
        ch = unary_union([p for p, c in zip(self.polys, self.cls) if c in CHAUSSEE or c in PEINT])
        il = unary_union([p for p, c in zip(self.polys, self.cls) if c in ILOTS])
        return ch.difference(il) if not il.is_empty else ch

    def union(self, classes):
        from shapely.ops import unary_union
        return unary_union([p for p, c in zip(self.polys, self.cls) if c in classes])


def plaques(ins):
    return [x for x in ins if x["kind"] in ("plaque", "plaque_composee")]


def bas_plaque(x):
    """Bas réel d'une plaque : z du pivot + zmin de l'asset à sa gamme × échelle (catalogue route_fr), ou 0 (plaque
    composée : pivot au bord inférieur)."""
    if x["kind"] == "plaque_composee":
        return x["p"][2]
    e = PS.etendues_gammes(x["asset"])
    g = x["gamme"] if x["gamme"] in e else sorted(e)[0]
    return x["p"][2] + e[g][1] * float(x["echelle"][2])


def controler(d):
    d = Path(d)
    scene = d.name
    plan = json.loads((d / "l6" / "plan_signalisation.json").read_text(encoding="utf-8"))
    ens = {e["id"]: e for e in json.loads((d / "l6" / "ensembles.json").read_text(encoding="utf-8"))["ensembles"]}
    ins = json.loads((d / "l6" / "instances.json").read_text(encoding="utf-8"))["instances"]
    m = json.loads((d / "modele_voie.json").read_text(encoding="utf-8"))
    sol = Sol(d)
    from shapely.geometry import LineString, Point
    chaussee = sol.chaussee_visible()
    pietons = sol.union(PIETONS)
    pe = {p["id"]: p for p in plan["ensembles"]}
    # abaissé : bateau des bordures fabriquées (vue 0,02 m, DEF-031) et zone d'attente de 1,20 m de part et d'autre
    # de la face (BEV 0,50 + 0,5875 m) ; fond de l'abaissé : vue < 0,03 m
    zones_bateau = [LineString(z["polyligne"]).buffer(float(z.get("profondeur", 1.2)), cap_style=2)
                    for z in plan.get("exclusions") or [] if len(z["polyligne"]) >= 2]
    par_ens = {}
    for x in ins:
        par_ens.setdefault(x["ensemble"], []).append(x)
    res = {"scene": scene}
    # ---- C1 exigences
    c1 = []
    for x in plan["exigences"]:
        poses = [e for e in x["ensembles"] if e in ens and ens[e]["statut"] != "echec"]
        codes = {i["code"] for e in poses for i in par_ens.get(e, [])}
        manq = [c for c in x["codes"] if not any(c == k or k.startswith(c) for k in codes)]
        if x["type"] == "voies_affectees":
            manq = [] if any(k.startswith(("C24", "Da30")) for k in codes) else x["codes"]
        if x["type"] == "regime" and x.get("regime") == "feux":
            manq = [] if "R11v" in codes else ["R11v"]
        c1.append({"id": x["id"], "type": x["type"], "regime": x.get("regime"), "codes": x["codes"],
                   "manquants": manq, "ok": not manq})
    res["C1"] = {"exigences": len(c1), "satisfaites": sum(1 for x in c1 if x["ok"]),
                 "taux": _r(sum(1 for x in c1 if x["ok"]) / len(c1), 4) if c1 else 1.0,
                 "echecs": [x for x in c1 if not x["ok"]]}
    # ---- C2 AB4 interdit
    interdits = []
    for c in m.get("carrefours") or []:
        for b in c.get("branches") or []:
            if b.get("regime") in ("feux", "stop_a_verifier"):
                for e in ens.values():
                    if pe[e["id"]].get("applicabilite", {}).get("branche") == b["id"] and \
                            any(i["code"] == "AB4" for i in par_ens.get(e["id"], [])):
                        interdits.append(e["id"])
    res["C2"] = {"AB4_sur_feux_ou_a_verifier": len(interdits), "ensembles": interdits,
                 "branches_stop_a_verifier": sum(1 for c in m.get("carrefours") or [] for b in c.get("branches") or []
                                                 if b.get("regime") == "stop_a_verifier")}
    # ---- C3 bord du panneau / rive ; C4 cheminement et surplomb ; C5 surfaces ; C6 hauteurs ; C8 orientation
    c3, c4, c5, c6, c8 = [], [], [], [], []
    for eid, e in sorted(ens.items()):
        els = par_ens.get(eid, [])
        sup = [x for x in els if x["kind"] == "support"]
        pl = plaques(els)
        contrainte = e["statut"] == "contrainte"
        # C3 (IISR1 art. 8 i, panneaux d'accotement) : hors plaques en surplomb des voies (potence, portique :
        # gabarit, C6) et
        # hors panonceau M12 du support d'un feu (accessoire du feu : axe du mât à 0,70 m, DEF-027 ; IISR1 9-1 B 12)
        for x in pl:
            if e["famille"] in ("potence", "portique") or (e["famille"] == "feu" and x["code"].startswith("M12")):
                continue
            F = np.array(x["face_dir"][:2])
            U = np.array([F[1], -F[0]])
            P = np.array(x["p"][:2])
            dmin = min(chaussee.distance(Point(*(P + s * U * 0.5 * x["largeur"] * float(x["echelle"][0]))))
                       for s in (-1, 1))
            ok = dmin >= BORD - 0.005
            c3.append({"ensemble": eid, "code": x["code"], "bord_m": _r(dmin), "ok": ok,
                       "contrainte_signalee": contrainte and "contrainte" in (e.get("motif") or "") or
                       ("8 i" in (e.get("motif") or "")) or ("si possible" in (e.get("motif") or ""))})
        # C5 et C4 : supports
        for s in sup:
            x, y = s["p"][0], s["p"][1]
            top = sol.dessus(x, y)
            cl = top[0] if top else "hors_sol"
            mat = top[1] if top else ""
            interdit = (cl in CHAUSSEE or cl in CIRCULEES or cl in PEINT or
                        (cl in ("giratoire_ilot", "carrefour_ilot") and mat in FRANCHISSABLES))
            abaisse = False
            if cl in PIETONS and top:
                dch = chaussee.distance(Point(x, y))
                # vue : altitude du trottoir au support − altitude de la chaussée la plus proche
                from shapely.ops import nearest_points
                q = nearest_points(chaussee, Point(x, y))[0]
                u = np.array([q.x - x, q.y - y])
                u = u / (np.linalg.norm(u) or 1.0)
                zq = sol.z_classes(q.x + u[0] * 0.03, q.y + u[1] * 0.03, CHAUSSEE | PEINT)
                if zq is not None and top[2] - zq < VUE:
                    abaisse = True
            if any(z.distance(Point(x, y)) < 1e-6 for z in zones_bateau):
                abaisse = True
            sur_separateur = "séparateur" in (e.get("motif") or "")
            c5.append({"ensemble": eid, "support": s["asset"], "classe": cl, "interdit": interdit, "abaisse": abaisse,
                       "fixe_sur_separateur": sur_separateur, "ok": not interdit and not abaisse})
            if cl in PIETONS:
                # cheminement : coupe perpendiculaire à la chaussée la plus proche, dans le trottoir
                from shapely.ops import nearest_points
                q = nearest_points(chaussee, Point(x, y))[0]
                n = np.array([x - q.x, y - q.y])
                n = n / (np.linalg.norm(n) or 1.0)
                r = 0.5 * float(e.get("support_r", 0.03) or 0.03) * 2
                ligne = LineString([(x - n[0] * 12, y - n[1] * 12), (x + n[0] * 12, y + n[1] * 12)])
                inter = ligne.intersection(pietons.buffer(0.01))
                segs = [g for g in getattr(inter, "geoms", [inter]) if not g.is_empty and g.length > 0]
                seg = next((g for g in segs if g.distance(Point(x, y)) < 0.02), None)
                if seg is None:
                    c4.append({"ensemble": eid, "ok": False, "motif": "coupe du trottoir introuvable"})
                    continue
                cs = list(seg.coords)
                da = [math.hypot(c[0] - x, c[1] - y) for c in (cs[0], cs[-1])]
                libre = max(da) - r
                larg = seg.length
                ok = libre >= CHEM - 0.01 or (larg < CHEM + 2 * r and contrainte)
                c4.append({"ensemble": eid, "largeur_trottoir_m": _r(larg), "libre_m": _r(libre), "ok": ok})
        # C4 surplomb : plaque qui avance au-dessus du cheminement (côté façade au cas 1 d'ARB-20, côté chaussée au
        # cas 2) : bas ≥ 2,20 m (A2007 art. 1, 6° c-d)
        if sup:
            S = sup[0]["p"]
            ds_ = chaussee.distance(Point(S[0], S[1]))
            r_ = float(e.get("support_r") or 0.03)
            for x in pl:
                top = sol.dessus(x["p"][0], x["p"][1])
                if not (top and top[0] in PIETONS):
                    continue
                dp = chaussee.distance(Point(x["p"][0], x["p"][1]))
                demi = 0.5 * x["largeur"] * float(x["echelle"][0])
                if e.get("cas_arb20") == 2:
                    empiete = dp - demi < ds_ - r_ - 0.005
                else:
                    empiete = dp + demi > ds_ + r_ + 0.005
                b = bas_plaque(x) - top[2]
                if empiete and b < SURPL - 0.005:
                    c4.append({"ensemble": eid, "code": x["code"], "surplomb_bas_m": _r(b), "ok": False})
        # C6 hauteurs : plaque la plus basse (hors feux ; potence et portique : au-dessus de la chaussée)
        if pl and e["famille"] in ("panneau", "balise", "potence", "portique"):
            zsol = e["z_sol"]
            bas = min(bas_plaque(x) for x in pl) - zsol
            surplomb = e["famille"] in ("potence", "portique")
            if surplomb:
                # au-dessus de la chaussée sous chaque plaque (gabarit, L6-SV-SURPLOMB.GABARIT)
                def _bas_sur_sol(x):
                    t = sol.dessus(x["p"][0], x["p"][1])
                    return bas_plaque(x) - (t[2] if t else zsol)
                bas = min(_bas_sur_sol(x) for x in pl)
                cible = pe[eid]["bas"]
                ok = bas >= cible - TOL_H
            else:
                cible = pe[eid]["bas"]
                ok = abs(bas - cible) <= TOL_H
            c6.append({"ensemble": eid, "bas_m": _r(bas), "cible_m": cible, "regle": pe[eid].get("regle_hauteur"),
                       "ecart_m": _r(bas - cible), "surplomb": surplomb, "ok": bool(ok)})
        # C8 orientation (plaques et feux principaux tournés vers l'usager)
        T = np.array(e["trafic_dir"][:2])
        if np.linalg.norm(T) > 0.5 and pe[eid]["ancrage"]["type"] != "xy" and not pe[eid]["ancrage"].get("face_az") \
                and not pe[eid]["ancrage"].get("vise"):
            for x in [i for i in els if i["kind"] in ("plaque", "plaque_composee") or i["code"] == "R11v"]:
                F = np.array(x["face_dir"][:2])
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(F, -T) / np.linalg.norm(T))))))
                c8.append({"ensemble": eid, "code": x["code"], "ecart_deg": _r(ang, 2), "ok": ang <= 15.0})
    res["C3"] = {"plaques": len(c3), "conformes": sum(1 for x in c3 if x["ok"]),
                 "sous_070_signales": sum(1 for x in c3 if not x["ok"] and x["contrainte_signalee"]),
                 "sous_070_non_signales": [x for x in c3 if not x["ok"] and not x["contrainte_signalee"]],
                 "min_m": _r(min([x["bord_m"] for x in c3] or [None]) if c3 else None)}
    res["C4"] = {"supports_sur_trottoir": sum(1 for x in c4 if "libre_m" in x),
                 "echecs": [x for x in c4 if not x["ok"]], "libre_min_m": _r(min([x["libre_m"] for x in c4 if "libre_m" in x] or [99]))}
    res["C5"] = {"supports": len(c5), "sur_surface_interdite": [x for x in c5 if not x["ok"]],
                 "fixes_sur_separateur": sum(1 for x in c5 if x["fixe_sur_separateur"]),
                 "classes": sorted({x["classe"] for x in c5})}
    res["C6"] = {"ensembles": len(c6), "conformes": sum(1 for x in c6 if x["ok"]),
                 "ecart_max_m": _r(max([abs(x["ecart_m"]) for x in c6 if not x["surplomb"]] or [0])),
                 "echecs": [x for x in c6 if not x["ok"]], "surplomb": [x for x in c6 if x["surplomb"]]}
    res["C8"] = {"faces": len(c8), "conformes": sum(1 for x in c8 if x["ok"]),
                 "ecart_max_deg": _r(max([x["ecart_deg"] for x in c8] or [0]), 2), "echecs": [x for x in c8 if not x["ok"]]}
    # ---- C7 feux
    c7 = []
    r11 = [s for s in m.get("signaux") or [] if s.get("code", "").startswith("R11")]
    for sg in r11:
        e = next((x for x in ens.values() if sg["id"] in pe[x["id"]]["source"]), None)
        if e is None:
            c7.append({"signal": sg["id"], "ok": False, "motif": "non posé"})
            continue
        heads = [i for i in par_ens.get(e["id"], []) if i["code"] == "R11v"]
        # bas du boîtier = pivot de l'asset feu_R11v_* (catalogue : « bas du boîtier inférieur ») au-dessus du sol
        bas = min(i["p"][2] - e["z_sol"] for i in heads) if heads else None
        axe = max(i["p"][2] - e["z_sol"] for i in heads) + 2.5 * 0.24 if heads else None
        cote = pe[e["id"]]["ancrage"].get("cote") or ("ilot" if pe[e["id"]]["ancrage"]["type"] == "xy" else "")
        a_droite = cote in ("droite", "ilot") and (cote == "ilot" or (e.get("dt") or 0) > 0)
        ligne_ok = True
        if pe[e["id"]]["ancrage"]["type"] == "route":
            # ancrage = ligne d'effet + 0,30 m (DEF-027) : ds ≥ −0,30 ⇔ au droit ou à l'aval de la ligne
            ligne_ok = (e.get("ds") or 0.0) >= -0.30 - 0.02
        juxt = max(sum(1 for i in heads if abs(i["lacet_usd"] - h["lacet_usd"]) < 1.0) for h in heads) if heads else 0
        ok = e["statut"] != "echec" and a_droite and ligne_ok and bas is not None and bas >= 2.0 - 1e-6 and axe < 4.2 \
            and juxt <= 2
        c7.append({"signal": sg["id"], "ensemble": e["id"], "statut": e["statut"], "cote": cote, "a_droite": a_droite,
                   "ligne_effet_ok": ligne_ok, "bas_m": _r(bas), "axe_sup_m": _r(axe), "juxtaposes": juxt, "ok": ok})
    r12 = [s for s in m.get("signaux") or [] if s.get("code") == "R12"]
    r12_poses = sum(1 for s in r12 if any(s["id"] in pe[x]["source"] and ens[x]["statut"] != "echec" for x in ens))
    pp_geres = [p for c in m.get("carrefours") or [] for p in c.get("passages_pieton") or [] if p.get("regime") == "feux"]
    res["C7"] = {"R11_modele": len(r11), "R11_conformes": sum(1 for x in c7 if x["ok"]), "echecs": [x for x in c7 if not x["ok"]],
                 "R12_modele": len(r12), "R12_poses": r12_poses, "traversees_gerees": len(pp_geres),
                 "R12_par_traversee": _r(r12_poses / len(pp_geres), 2) if pp_geres else None, "R14": 0}
    # ---- C9 séquences
    c9 = []
    eb10 = [e for e in ens.values() if any(i["code"] == "EB10" for i in par_ens.get(e["id"], []))]
    eb20 = [e for e in ens.values() if any(i["code"] == "EB20" for i in par_ens.get(e["id"], []))]
    for a in eb10:
        ok = any(abs((pe[a["id"]]["ancrage"]["s"] + a["ds"] * pe[a["id"]]["ancrage"]["sens"]) -
                     (pe[b["id"]]["ancrage"]["s"] + b["ds"] * pe[b["id"]]["ancrage"]["sens"])) <= 5.0 for b in eb20)
        c9.append({"sequence": "EB10/EB20 dos à dos", "ensemble": a["id"], "ok": ok})
    for x in plan["exigences"]:
        if x["type"] == "repetition_gauche":
            ok = all(i in ens and ens[i]["statut"] != "echec" for i in x["ensembles"])
            c9.append({"sequence": "B14 droite + gauche", "exigence": x["id"], "ok": ok})
    res["C9"] = {"sequences": len(c9), "conformes": sum(1 for x in c9 if x["ok"]), "detail": c9}
    # ---- C10 lisibilité (vue du conducteur) : projection de la plaque visée
    fr = d / "l6" / "rendus" / "manifest_rendus_l6.json"
    if fr.exists():
        mr = json.loads(fr.read_text(encoding="utf-8"))
        cam = mr["cameras"]["l6_conducteur"]
        o, c = np.array(cam["oeil"]), np.array(cam["cible"])
        fwd = (c - o) / np.linalg.norm(c - o)
        right = np.cross(fwd, [0, 0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        W, H = cam["res"]
        f_px = cam["focale_mm"] / 36.0 * W
        cibles = [x for x in plaques(par_ens.get(cam["ensemble"], []))] +             [x for x in par_ens.get(cam["ensemble"], []) if x["code"] == "R11v"]
        mes = []
        for x in cibles:
            P = np.array(x["p"]) + np.array([0, 0, x["hauteur"] * 0.5 * float(x["echelle"][2])])
            v = P - o
            z = float(v @ fwd)
            if z <= 0:
                mes.append({"code": x["code"], "visible": False})
                continue
            u = W / 2 + f_px * float(v @ right) / z
            w = H / 2 - f_px * float(v @ up) / z
            larg = f_px * x["largeur"] * float(x["echelle"][0]) / z
            seuil = 15.0 if x["code"] == "R11v" else 40.0
            mes.append({"code": x["code"], "u_px": _r(u, 1), "v_px": _r(w, 1), "largeur_px": _r(larg, 1),
                        "seuil_px": seuil, "visible": 0 <= u <= W and 0 <= w <= H, "ok": larg >= seuil})
        ok = bool(mes) and all(m_["visible"] for m_ in mes) and any(m_.get("ok") for m_ in mes)
        res["C10"] = {"ensemble": cam["ensemble"], "plaques": mes, "ok": ok}
    else:
        res["C10"] = {"ok": None, "motif": "rendus absents"}
    res["statuts"] = {s: sum(1 for e in ens.values() if e["statut"] == s) for s in ("ok", "contrainte", "echec")}
    res["non_poses"] = plan["non_poses"]
    return res


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = [Path(s) for s in a.scenes] or [SORTIE / s for s in SCENES]
    out = []
    for d in dossiers:
        r = controler(d)
        out.append(r)
        print(f"{r['scene']}: C1 {r['C1']['satisfaites']}/{r['C1']['exigences']} ; C2 AB4 interdits {r['C2']['AB4_sur_feux_ou_a_verifier']} ;"
              f" C3 {r['C3']['conformes']}/{r['C3']['plaques']} (non signalés {len(r['C3']['sous_070_non_signales'])}) ;"
              f" C4 échecs {len(r['C4']['echecs'])} ; C5 interdits {len(r['C5']['sur_surface_interdite'])} ;"
              f" C6 {r['C6']['conformes']}/{r['C6']['ensembles']} ; C7 R11 {r['C7']['R11_conformes']}/{r['C7']['R11_modele']} ;"
              f" C8 {r['C8']['conformes']}/{r['C8']['faces']} ; C9 {r['C9']['conformes']}/{r['C9']['sequences']} ;"
              f" C10 {r['C10'].get('ok')}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
