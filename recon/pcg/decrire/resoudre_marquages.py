"""Résolution de la famille marquages (schéma 0.3) : retraits prouvés, flèches recentrées, marques arrêtées à
l'arête des bordures, attributs prouvés, ajouts de traits isolés.

Toute modification est faite sur une copie de base/marquages.geojson et tracée dans la propriété `resolution` de
l'entité (le schéma des marquages admet des propriétés libres) et dans le journal.
"""
import copy
import math

import numpy as np

import marquages_commun as M
from commun import O, abscisses, anneaux, arrondi, echantillons_interieurs, point_a, repere
import resoudre_regles as RR
import resoudre_revue as RV

ROULABLE = {"chaussee", "parking", "acces_riverain", "piste_cyclable"}
ENUM_ETAT = {"conserve", "neuf_2025", "refait_2025_identique", "fantome"}
ENUM_USURE = {"0", "1", "2", "3", "F"}
MARGE_BOITE_M = 0.10


def _loc(c):
    return repere(np.asarray(c, float)[..., :2])


def _centre(f):
    g = f["geometry"]
    if g["type"] == "LineString":
        P = _loc(g["coordinates"])
        q, _ = point_a(P, abscisses(P)[-1] / 2)
        return [float(q[0, 0]), float(q[0, 1])]
    if g["type"] == "MultiLineString":
        P = _loc(g["coordinates"][0])
        return [float(P[:, 0].mean()), float(P[:, 1].mean())]
    polys = anneaux(g)
    R = repere(polys[0][0])
    return [float(R[:, 0].mean()), float(R[:, 1].mean())]


def _resolution(p, d):
    r = p.setdefault("resolution", {"decisions": []})
    r["decisions"].append(arrondi(d))


def _segments_dans_boite(A, B, o, ex, ey, xa, xb, ya, yb, pas=0.05):
    """Segments [A, B] (locaux) dont une partie tombe dans la boîte du repère de la flèche (x à droite, y en avant)."""
    touches = []
    for k in range(len(A)):
        L = float(np.hypot(*(B[k] - A[k])))
        n = max(2, int(math.ceil(L / pas)) + 1)
        Q = A[k] + np.linspace(0.0, 1.0, n)[:, None] * (B[k] - A[k])
        x = (Q - o) @ ex
        y = (Q - o) @ ey
        if np.any((x >= xa) & (x <= xb) & (y >= ya) & (y <= yb)):
            touches.append(k)
    return touches


class ResolveurMarquages:
    def __init__(self, S, J, ctx):
        self.S, self.J, self.ctx = S, J, ctx
        self.F = S.index_base("marquages")
        self.E = S.entites
        self.R2 = RV.index_revue_v2()
        self.retires = set()
        self.K = S.index_base("bordures")
        A, B, kid = [], [], []
        for i, f in sorted(self.K.items()):
            P = _loc(f["geometry"]["coordinates"])
            A.append(P[:-1])
            B.append(P[1:])
            kid += [i] * (len(P) - 1)
        self.KA, self.KB, self.kid = np.vstack(A), np.vstack(B), np.array(kid)
        LA, LB, lid = [], [], []
        for i, f in sorted(self.F.items()):
            p = f["properties"]
            if p["classe"] != "ligne" or (p.get("fabrication") or {}).get("statut") == "non_fabrique":
                continue
            g = f["geometry"]
            parts = [g["coordinates"]] if g["type"] == "LineString" else g["coordinates"]
            for c in parts:
                P = _loc(c)
                LA.append(P[:-1])
                LB.append(P[1:])
                lid += [i] * (len(P) - 1)
        self.LA, self.LB, self.lid = np.vstack(LA), np.vstack(LB), np.array(lid)

    # ------------------------------------------------------------------ 1. retraits (RES-EXI-001/02)
    def existence(self):
        for ident in sorted(self.E):
            if ident not in self.F:
                continue
            e = self.E[ident]
            f = self.F[ident]
            p = f["properties"]
            xy = _centre(f)
            ex, st = e["existence"], e["statut_verification"]
            if ex in ("absent_2026", "retirer") and st in ("absent_2026", "a_retirer") and e["preuve_stricte"]["obs"]:
                obs = e["preuve_stricte"]["obs"]
                if RR.projection_lointaine(obs, self.S.observations):
                    d = min(float(self.S.observations[o]["distance_camera_m"]) for o in obs)
                    nat = "retrait" if ex == "retirer" else "absence"
                    self.J.non_resolu(ident, "marquages", "absence_projection_lointaine", origine="incertain", xy=xy,
                                      classe=p["classe"], regles=["RES-EXI-005"] + e["regles"], observations=obs,
                                      motif=f"{nat} vue seulement en projection à {d:.1f} m de la caméra : trait fin "
                                            f"possiblement invisible")
                    continue
                avant_trav = e["tranche_stricte"] != "apres_travaux"
                neuf = p.get("etat") in ("neuf_2025", "refait_2025_identique") or p.get("zone_etat") in ("neuf_2025", "refait_2025_identique")
                gam = p.get("src") == "gam"
                if avant_trav and (neuf or gam):
                    self.J.non_resolu(ident, "marquages", "absence_anterieure_contre_2026", origine="conflit", xy=xy,
                                      classe=p["classe"], regles=["RES-EXI-002"] + e["regles"], observations=obs,
                                      motif=f"{'retrait' if ex == 'retirer' else 'absence'} vu(e) avant la fin des travaux "
                                            f"({e['tranche_stricte']}) contre un marquage {'levé GAM 2026' if gam else 'posé ou refait en 2025'}")
                    continue
                if (p.get("fabrication") or {}).get("statut") == "non_fabrique":
                    continue
                rv = self.R2.get(ident)
                raison = (f"{'retiré' if ex == 'retirer' else 'absent en 2026'} : preuve stricte {', '.join(obs)} "
                          f"({e['categorie_preuve']}, {e['tranche_stricte']}) ; fusion_recensement/0.3, RES-EXI-001")
                p["fabrication"] = {"statut": "non_fabrique", "raison": raison}
                _resolution(p, {"nature": "retrait", "regles": ["RES-EXI-001"] + e["regles"], "observations": obs,
                                "revue": f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']}" if rv else None,
                                "conf": "moyenne"})
                self.retires.add(ident)
                self.J.appliquer(ident, "marquages", "retrait", avant={"fabrication": None},
                                 apres={"fabrication": "non_fabrique"}, regles=["RES-EXI-001"] + e["regles"],
                                 observations=obs, revue=(f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']} — {rv['motif']}" if rv else None),
                                 conf="moyenne", motif=raison, xy_avant=xy, xy_apres=xy,
                                 portee=1.0 + min(float(p.get("longueur_m") or 2.0), 20.0) / 20.0, classe=p["classe"],
                                 extra={"geometrie_l93": f["geometry"]})
            elif ex == "absent_2026_a_verifier":
                self.J.non_resolu(ident, "marquages", "absence_a_verifier", origine="incertain", xy=xy, classe=p["classe"],
                                  regles=["RES-EXI-004"] + e["regles"], observations=e["obs"],
                                  motif="absence 2026 sans preuve stricte (FUS-EXI-04) : marquage gardé")

    # ------------------------------------------------------------------ 2. flèches (RES-MQ-001)
    def _verifier_fleche(self, f, ctrl, dxy):
        p = f["properties"]
        o = _loc(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        ex, ey = M.axes_cap(float(p["pose"]["cap_deg"]))
        poly = [repere(r) for r in anneaux(f["geometry"])[0]]
        R = poly[0]
        x, y = (R - o) @ ex, (R - o) @ ey
        bo = (float(x.min()) - MARGE_BOITE_M, float(x.max()) + MARGE_BOITE_M, float(y.min()) - MARGE_BOITE_M,
              float(y.max()) + MARGE_BOITE_M)
        res = {"motifs": []}
        if p.get("src") == "gam":
            res["motifs"].append("flèche levée GAM : jamais déplacée")
        if "OpenDRIVE" in str(ctrl.get("bords")):
            res["motifs"].append(f"voie bornée seulement par OpenDRIVE ({ctrl.get('bords')})")
        for etat, d in (("avant", np.zeros(2)), ("apres", dxy)):
            o2 = o + d
            kb = _segments_dans_boite(self.KA, self.KB, o2, ex, ey, *bo)
            kl = [k for k in _segments_dans_boite(self.LA, self.LB, o2, ex, ey, *bo) if self.lid[k] != p["id"]]
            res[f"bordures_coupant_{etat}"] = sorted({str(self.kid[k]) for k in kb})
            res[f"lignes_coupant_{etat}"] = sorted({str(self.lid[k]) for k in kl})
            Q = np.vstack([echantillons_interieurs([r + d for r in poly], 0.05)])
            cl = self.ctx.classes(Q)
            res[f"part_roulable_{etat}"] = round(float(np.mean([c in ROULABLE for c in cl])) if len(cl) else 0.0, 3)
        if res["bordures_coupant_apres"] or res["bordures_coupant_avant"]:
            res["motifs"].append(f"voie coupée : bordure {', '.join(res['bordures_coupant_avant'] or res['bordures_coupant_apres'])} "
                                 f"dans la boîte de la flèche (marge {MARGE_BOITE_M} m)")
        if res["lignes_coupant_apres"]:
            res["motifs"].append(f"ligne {', '.join(res['lignes_coupant_apres'])} dans la boîte de la flèche recalée")
        if res["part_roulable_apres"] < 0.995:
            res["motifs"].append(f"empreinte recalée roulable à {res['part_roulable_apres']:.0%} seulement")
        return res, o, ex, ey

    def fleches(self):
        ctrl = {c["id"]: c for c in self.S.mq_controle.get("fleches", [])}
        for prop in sorted(self.S.corr_mq, key=lambda f: f["properties"]["id"]):
            q = prop["properties"]
            if q.get("nature") != "recalage_lateral_fleche":
                continue
            ident = q["id"]
            f = self.F.get(ident)
            if f is None:
                continue
            p = f["properties"]
            xy = _centre(f)
            if ident in self.retires:
                self.J.non_resolu(ident, "marquages", "recalage_fleche", origine="proposition_rejetee", xy=xy, classe="fleche",
                                  regles=["RES-MQ-001", "RES-EXI-001"], motif="flèche retirée (preuve stricte) : recalage sans objet")
                continue
            dxy = np.asarray(q["translation_m"], float)
            c = ctrl.get(ident, {})
            rv = self.R2.get(ident)
            res, o, ex, ey = self._verifier_fleche(f, c, dxy)
            if rv and rv["verdict"] == "faux":
                res["motifs"].append(f"revue « faux » : {rv['motif']}")
            prop_info = {"translation_m": list(dxy), "ecart_m": q.get("ecart_m"), "bords": q.get("bords"),
                         "controle_resolution": res}
            if res["motifs"]:
                self.J.non_resolu(ident, "marquages", "recalage_fleche", origine="proposition_rejetee", xy=xy, classe="fleche",
                                  regles=["RES-MQ-001", q.get("regle", "MQ-FLE-006")], proposition=prop_info,
                                  revue=(f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']} — {rv['motif']}" if rv else None),
                                  motif="recalage non appliqué : " + " ; ".join(res["motifs"]))
                continue
            # application : géométrie, pose, ancrage (t)
            d93 = dxy
            g = f["geometry"]
            g_avant = copy.deepcopy(g)
            g["coordinates"] = [[[round(c0[0] + d93[0], 3), round(c0[1] + d93[1], 3)] + list(c0[2:]) for c0 in r]
                                for r in g["coordinates"]]
            pt = p["pose"]["point_l93"]
            p["pose"]["point_l93"] = [round(pt[0] + d93[0], 3), round(pt[1] + d93[1], 3)]
            dt = None
            anc = p.get("ancrage") or {}
            if anc.get("type") == "xodr" and anc.get("t") is not None and anc.get("voie") is not None:
                gauche = float(dxy @ (-ex))
                dt = gauche if int(anc["voie"]) < 0 else -gauche
                t0 = anc["t"]
                anc["t"] = round(float(t0) + dt, 3)
            d = float(np.hypot(*dxy))
            revue = f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']} — {rv['motif']}" if rv else None
            _resolution(p, {"nature": "recalage_fleche", "regles": ["RES-MQ-001", "MQ-FLE-006"], "translation_m": list(dxy),
                            "dt_ancrage_m": dt, "bords": q.get("bords"), "controle": res, "revue": revue, "conf": "faible"})
            self.J.appliquer(ident, "marquages", "recalage_fleche", avant={"pose_point_l93": pt},
                             apres={"pose_point_l93": p["pose"]["point_l93"], "d_m": d}, regles=["RES-MQ-001", "MQ-FLE-006"],
                             revue=revue, conf="faible", xy_avant=xy, xy_apres=[xy[0] + dxy[0], xy[1] + dxy[1]],
                             portee=1.0 + 3.0 * d, classe="fleche",
                             motif=f"flèche centrée dans sa voie ({q.get('bords')}) : écart {q.get('ecart_m')} m corrigé ; "
                                   f"aucune limite dans la boîte, empreinte 100 % roulable",
                             extra={"geometrie_avant_l93": g_avant, "geometrie_apres_l93": copy.deepcopy(f["geometry"])})

    # ------------------------------------------------------------------ 3. marques au-delà de l'arête (RES-MQ-002)
    def raccourcissements(self):
        for prop in sorted(self.S.corr_mq, key=lambda f: f["properties"]["id"]):
            q = prop["properties"]
            ident = q["id"]
            f = self.F.get(ident)
            if f is None:
                continue
            p = f["properties"]
            xy = _centre(f)
            if q.get("nature") == "translation_dans_chaussee":
                self.J.non_resolu(ident, "marquages", "translation", origine="proposition_rejetee", xy=xy, classe=p["classe"],
                                  regles=["RES-MQ-002"], proposition={"translation_m": q.get("translation_m")},
                                  motif=f"translation de {np.hypot(*q['translation_m']):.3f} m sous la résolution des sources : sans effet")
                continue
            if q.get("nature") != "raccourcissement_dans_chaussee":
                continue
            if ident in self.retires:
                continue
            g = f["geometry"]
            if g["type"] != "LineString":
                self.J.non_resolu(ident, "marquages", "raccourcissement", origine="schema", xy=xy, classe=p["classe"],
                                  regles=["RES-MQ-002"], motif="géométrie non linéaire")
                continue
            P = _loc(g["coordinates"])
            S = abscisses(P)
            L = float(S[-1])
            cuts, motifs = [], []
            for cote, r in (("debut", float(q.get("raccourcir_debut_m") or 0.0)), ("fin", float(q.get("raccourcir_fin_m") or 0.0))):
                if r <= 0:
                    continue
                s_x, kb = self._croisement_bordure(P, S, cote, r + 0.5)
                if s_x is None:
                    motifs.append(f"{cote} : aucune bordure croisée dans les {r + 0.5:.2f} m d'extrémité")
                    continue
                a, b = (0.0, s_x) if cote == "debut" else (s_x, L)
                Q, _ = point_a(P, np.linspace(a, b, max(3, int((b - a) / 0.05) + 1)))
                cl = self.ctx.classes(Q[:, :2])
                part = float(np.mean([c in ROULABLE for c in cl]))
                if part > 0.5:
                    motifs.append(f"{cote} : la partie au-delà de {kb} est roulable à {part:.0%}")
                    continue
                cuts.append((round(a, 3), round(b, 3), kb, cote))
            if not cuts:
                self.J.non_resolu(ident, "marquages", "raccourcissement", origine="proposition_rejetee", xy=xy,
                                  classe=p["classe"], regles=["RES-MQ-002", "MQ-DET-010"], proposition=q,
                                  motif="raccourcissement non vérifié : " + " ; ".join(motifs))
                continue
            iv0 = [list(x) for x in p.get("interruptions", [])]
            iv = sorted(iv0 + [[a, b] for a, b, _, _ in cuts])
            fus = []
            for a, b in iv:
                if fus and a <= fus[-1][1] + 1e-6:
                    fus[-1][1] = max(fus[-1][1], b)
                else:
                    fus.append([a, b])
            p["interruptions"] = [[round(a, 3), round(b, 3)] for a, b in fus]
            lg = sum(b - a for a, b, _, _ in cuts)
            _resolution(p, {"nature": "arret_a_l_arete", "regles": ["RES-MQ-002", "MQ-DET-010", "TQ-MQG-014"],
                            "interruptions_ajoutees": [[a, b] for a, b, _, _ in cuts],
                            "bordures": sorted({k for _, _, k, _ in cuts}), "conf": "moyenne"})
            self.J.appliquer(ident, "marquages", "arret_a_l_arete", avant={"interruptions": iv0},
                             apres={"interruptions": p["interruptions"]}, regles=["RES-MQ-002", "MQ-DET-010", "TQ-MQG-014"],
                             conf="moyenne", xy_avant=xy, xy_apres=xy, portee=0.5 + lg, classe=p["classe"],
                             motif=f"{lg:.2f} m de marque au-delà de l'arête avant de {', '.join(sorted({k for _, _, k, _ in cuts}))} "
                                   f"rendus non peints (géométrie inchangée)")

    def _croisement_bordure(self, P, S, cote, portee):
        """Abscisse du croisement de la polyligne P avec une arête de bordure, dans les `portee` m d'extrémité."""
        best = None
        for j in range(len(P) - 1):
            a, b = P[j], P[j + 1]
            d = b - a
            lo, hi = np.minimum(a, b) - 1e-9, np.maximum(a, b) + 1e-9
            sel = (np.maximum(self.KA[:, 0], self.KB[:, 0]) >= lo[0]) & (np.minimum(self.KA[:, 0], self.KB[:, 0]) <= hi[0]) & \
                  (np.maximum(self.KA[:, 1], self.KB[:, 1]) >= lo[1]) & (np.minimum(self.KA[:, 1], self.KB[:, 1]) <= hi[1])
            for k in np.where(sel)[0]:
                c, e = self.KA[k], self.KB[k] - self.KA[k]
                den = d[0] * e[1] - d[1] * e[0]
                if abs(den) < 1e-12:
                    continue
                w = c - a
                t = (w[0] * e[1] - w[1] * e[0]) / den
                u = (w[0] * d[1] - w[1] * d[0]) / den
                if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                    s = float(S[j] + t * (S[j + 1] - S[j]))
                    dist = s if cote == "debut" else float(S[-1]) - s
                    if dist <= portee and (best is None or dist < best[0]):
                        best = (dist, s, str(self.kid[k]))
        return (best[1], best[2]) if best else (None, None)

    # ------------------------------------------------------------------ 4. attributs (RES-ATT-001)
    def attributs(self):
        for ft in sorted(self.S.attributs, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            ident = q["id"]
            if q["famille"] != "marquages" or ident not in self.F:
                continue
            f = self.F[ident]
            p = f["properties"]
            xy = _centre(f)
            for a in sorted(q["maj"]):
                m = q["maj"][a]
                regles = ["RES-ATT-001"] + [r.strip() for r in m.get("regle", "").split(";") if r.strip()]
                if m.get("decision") != "appliquer":
                    self.J.non_resolu(ident, "marquages", f"attribut:{a}", origine="incertain", xy=xy, classe=p["classe"],
                                      regles=regles, observations=m.get("obs", []),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"mise à jour {a} en revue (FUS-ATT-06)")
                    continue
                if m.get("conf") not in RR.CONFIANCES_PROBANTES:
                    self.J.non_resolu(ident, "marquages", f"attribut:{a}", origine="incertain", xy=xy, classe=p["classe"],
                                      regles=regles, observations=m.get("obs", []),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"valeur {m.get('apres')!r} de confiance {m.get('conf')} (< moyenne)")
                    continue
                v, ok, motif = m["apres"], False, ""
                if a == "usure" and isinstance(v, (int, float)) and str(int(round(v))) in ENUM_USURE:
                    v, ok = str(int(round(v))), True
                elif a == "etat" and v in ENUM_ETAT:
                    ok = True
                elif a == "largeur_m" and isinstance(v, (int, float)) and 0.05 <= v <= 0.6 and p["classe"] in ("ligne", "transversale"):
                    ok = True
                elif a == "modulation" and p["classe"] == "ligne" and v == p.get("modulation"):
                    ok = True
                elif a == "modulation":
                    motif = f"modulation {p.get('modulation')} -> {v} demande trait, vide et phase (absents de l'observation)"
                if not ok:
                    self.J.non_resolu(ident, "marquages", f"attribut:{a}", origine="schema", xy=xy, classe=p["classe"],
                                      regles=regles, observations=m.get("obs", []),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=motif or f"valeur {m['apres']!r} hors du domaine de {a} (schéma 0.3)")
                    continue
                avant = p.get(a)
                if avant == v:
                    continue
                p[a] = v
                if a == "usure":
                    p.setdefault("prov", {})["usure"] = {"src": "regle:resolution.RES-ATT-001",
                                                         "ref": f"fusion 0.3 : {', '.join(m.get('obs_strictes') or m.get('obs', []))}",
                                                         "conf": m.get("conf") or "moyenne"}
                _resolution(p, {"nature": "attribut", "attribut": a, "avant": avant, "apres": v, "regles": regles,
                                "observations": m.get("obs_strictes") or m.get("obs", []), "conf": m.get("conf")})
                self.J.appliquer(ident, "marquages", "attribut", avant={a: avant}, apres={a: v}, regles=regles,
                                 observations=m.get("obs_strictes") or m.get("obs", []), conf=m.get("conf") or "moyenne",
                                 xy_avant=xy, xy_apres=xy, portee=0.05, classe=p["classe"], motif=f"{a} : {avant} -> {v}")

    # ------------------------------------------------------------------ 5. signalements restants
    def signalements(self):
        for m in sorted(self.S.mq_controle.get("marques", []), key=lambda m: m["id"]):
            if m.get("statut") != "signalement" or m["id"] in self.retires or m["id"] not in self.F:
                continue
            f = self.F[m["id"]]
            rv = self.R2.get(m["id"])
            self.J.non_resolu(m["id"], "marquages", "marque_hors_chaussee", origine="conflit", xy=_centre(f),
                              classe=m.get("classe"), regles=["RES-NRE-001", "MQ-DET-010"],
                              revue=(f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']} — {rv['motif']}" if rv else None),
                              motif=f"{m['part_hors_chaussee']:.0%} hors chaussée (débord {m['debord_max_m']} m), source "
                                    f"{m['source']} : bordure, limite de chaussée ou marque à revoir")
        for c in sorted(self.S.mq_controle.get("fleches", []), key=lambda c: c["id"]):
            if c["id"] not in self.F or c["id"] in self.retires:
                continue
            if c["statut"] in ("leve_ecart_garde", "voie_non_bornee", "garde_par_ortho"):
                rv = self.R2.get(c["id"])
                self.J.non_resolu(c["id"], "marquages", f"fleche_{c['statut']}", origine="incertain",
                                  xy=_centre(self.F[c["id"]]), classe="fleche", regles=["RES-MQ-001", "MQ-FLE-006"],
                                  revue=(f"{RV.REVUE_V2_ID} n° {rv['n']} : {rv['verdict']} — {rv['motif']}" if rv else None),
                                  motif=f"flèche gardée ({c['statut']}, écart {c.get('ecart_m')} m ; {c.get('bords')}) : "
                                        f"bords de voie à vérifier")

    # ------------------------------------------------------------------ 6. ajouts de traits (RES-MQ-003)
    def ajouts(self, ajouts):
        n = 7000
        pris = {i for i in self.F}
        nouveaux = []
        for ft in sorted(ajouts, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            if q["classe"] != "marquage" or not q["instancier"]:
                continue
            g = ft["geometry"]
            xy = [float(v) for v in q["local"]] if q.get("local") else None
            st = q["sous_types"]
            motif = None
            if q["tranche_stricte"] not in RR.TRANCHES_PROBANTES or q["confiance"] not in RR.CONFIANCES_PROBANTES:
                motif = f"preuve non stricte ({q['tranche_stricte']}, {q['confiance']})"
            elif g["type"] != "LineString":
                motif = f"géométrie {g['type']} : forme du marquage inconnue (polygone ou trait à relever)"
            elif not any(s.startswith("ligne_place") for s in st):
                motif = f"type {', '.join(st)} : paramètres de modulation ou d'aplat non observés"
            elif float(q["sigma_m"]) > RR.SIGMA_MAX_MARQUAGE_AJOUT:
                motif = f"σ {q['sigma_m']} m > {RR.SIGMA_MAX_MARQUAGE_AJOUT} m"
            obs = sorted({x["obs"] for x in q["provenance"]})
            src_obs = sorted({x["source"] for x in q["provenance"]})
            if motif is None and not all(s == "ortho2022" for s in src_obs):
                motif = f"source {', '.join(src_obs)} non représentable dans src_marquage (schéma 0.3)"
            P = _loc(g["coordinates"]) if g["type"] == "LineString" else None
            if motif is None:
                Q, _ = point_a(P, np.linspace(0, abscisses(P)[-1], 9))
                from commun import distance_segments
                d, j, _ = distance_segments(Q[:, :2], self.LA, self.LB)
                if np.median(d) < 0.3:
                    motif = f"doublon probable de {self.lid[j[int(np.argmin(d))]]} (à {float(np.median(d)):.2f} m)"
            if motif:
                self.J.non_resolu(q["id"], "marquages", "ajout", origine="schema" if "schéma" in motif or "type" in motif or
                                  "géométrie" in motif else "proposition_rejetee", xy=xy, classe=",".join(st),
                                  regles=["RES-MQ-003", "RES-ADD-001"], observations=obs,
                                  motif=f"ajout instanciable par la fusion non intégré : {motif}")
                continue
            while f"ML-{n:04d}" in pris:
                n += 1
            ident = f"ML-{n:04d}"
            pris.add(ident)
            larg = (q["attributs"].get("largeur_m") or {}).get("valeur")
            larg_ok = isinstance(larg, (int, float)) and 0.08 <= larg <= 0.20
            L = float(abscisses(P)[-1])
            coul = (q["attributs"].get("couleur") or {}).get("valeur") or "blanc"
            ref = "; ".join(f"{x['obs']} ({x['source']}, {x['date']}, {x['confiance']})" for x in q["provenance"])
            props = {
                "id": ident, "famille": "marquages", "classe": "ligne", "type": "segment", "couleur": coul if coul in ("blanc", "jaune", "ocre") else "blanc",
                "usure": "1", "couverture": 0.85, "etat": "conserve", "groupe": "resolution_ajouts", "branche": "parkings_acces",
                "lien_v1": [],
                "prov": {"geometrie": {"src": "ortho2022", "ref": f"ajout fusion {q['id']} : {ref}", "conf": q["confiance"]},
                         "largeur_m": {"src": "ortho2022" if larg_ok else "regle:resolution.RES-MQ-003",
                                       "ref": f"largeur observée {larg} m" if larg_ok else
                                              f"largeur observée {larg} hors 0,08-0,20 m : 0,12 m par défaut (ligne de place)",
                                       "conf": "moyenne" if larg_ok else "faible"},
                         "existence": {"src": "ortho2022", "ref": f"{', '.join(obs)} : absent de la description, valide 2026 "
                                                                  f"({q['tranche_stricte']})", "conf": q["confiance"]}},
                "ancrage": {"type": "axe", "source": "detection"},
                "longueur_m": round(L, 3), "modulation": "continue", "interruptions": [],
                "largeur_m": round(float(larg), 3) if larg_ok else 0.12, "role": "stationnement",
                "src": "ortho2022",
                "sources": [{"src": "ortho2022", "ref": f"{q['id']} ({', '.join(obs)})", "c": None,
                             "S": 0.75 if q["confiance"] == "haute" else 0.6}],
                "regles": ["RES-MQ-003", "RES-ADD-001"], "score": 0.75 if q["confiance"] == "haute" else 0.6,
                "confiance": q["confiance"], "zone_etat": "conserve",
                "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                      "regles": ["RES-MQ-003", "RES-ADD-001", "FUS-ADD-03"],
                                                      "sigma_m": q["sigma_m"], "conf": q["confiance"]})]},
            }
            feat = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[round(c[0], 3), round(c[1], 3)]
                                                                                         for c in g["coordinates"]]},
                    "properties": props}
            nouveaux.append(feat)
            self.J.appliquer(ident, "marquages", "ajout", avant=None, apres={"ajout_fusion": q["id"], "longueur_m": L},
                             regles=props["regles"], observations=obs, conf=q["confiance"], xy_avant=None,
                             xy_apres=_centre(feat), portee=0.3 + L / 10.0, classe="ligne",
                             motif=f"trait de place ({', '.join(st)}) observé sur l'ortho 2022 hors emprise des travaux, σ {q['sigma_m']} m")
        self.S.base["marquages"]["features"].extend(nouveaux)
        return nouveaux

    def executer(self, ajouts):
        self.existence()
        self.fleches()
        self.raccourcissements()
        self.attributs()
        self.signalements()
        return self.ajouts(ajouts)
