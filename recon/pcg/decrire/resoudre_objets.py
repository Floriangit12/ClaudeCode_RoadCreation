"""Résolution des objets (mobilier, panneaux, feux, candélabres, arbres) du paquet v1.

Sorties : objets/mobilier.geojson et objets/arbres.geojson, même schéma que le paquet, plus une propriété
`resolution` (décisions appliquées avec provenance) sur chaque objet modifié. Les positions décidées viennent de la
cohérence v2 (p_resolu) ; la fusion 0.3 et les revues décident de ce qui est appliqué (resoudre_regles.REGLES).
"""
import copy

import numpy as np

from commun import O, arrondi
import resoudre_regles as RR
import resoudre_revue as RV

ATTR_ARBRES = {"couronne_m": "diametre_couronne_m", "hauteur_m": "hauteur_m", "essence": "essence", "type": "type"}
ATTR_MOBILIER = {"couleur_mat": "couleur_mat", "hauteur_m": "hauteur_m", "nb_crosses": "nb_crosses",
                 "nb_lanternes": "nb_lanternes", "porte_a_faux_m": "porte_a_faux_m", "azimut_deg": "azimut_deg"}
METHODES_TRIANGULEES = ("triangulation", "triangulation_mixte", "ombre_ortho")


def _xy(f):
    p = f["properties"]
    if p.get("x_local") is not None:
        return [float(p["x_local"]), float(p["y_local"])]
    g = f["geometry"]
    c = np.asarray(g["coordinates"], float)
    c = c if c.ndim == 1 else c.mean(axis=0)
    return [float(c[0] - O[0]), float(c[1] - O[1])]


def _txt_revue(rv, src=RV.REVUE_V2_ID):
    if not rv:
        return None
    n = f" n° {rv['n']}" if "n" in rv else ""
    return f"{src}{n} : {rv['verdict']} — {rv['motif']}"


def _ajouter_decision(f, d):
    r = f["properties"].setdefault("resolution", {"decisions": []})
    r["decisions"].append(arrondi(d))


class ResolveurObjets:
    def __init__(self, S, J, ctx):
        self.S, self.J, self.ctx = S, J, ctx
        self.obj = {}
        for fam, fc in (("mobilier", S.mobilier), ("arbres", S.arbres)):
            for f in fc["features"]:
                self.obj[f["properties"]["id"]] = (fam, copy.deepcopy(f))
        self.O = S.objets_coherence()
        self.R2 = RV.index_revue_v2()
        self.R1 = RV.index_revue_v1()
        self.RL = RV.index_relecture()
        self.E = S.entites
        self.fcorr = {f["properties"]["id"]: f["properties"] for f in S.corr_pos}
        self.deplaces = {}          # id -> (xy_avant, xy_apres)
        self._tetes_prises = {}
        self.non_instancies = set()

    # ------------------------------------------------------------------ utilitaires
    def _deplacer(self, ident, xy, z, decision):
        fam, f = self.obj[ident]
        p = f["properties"]
        avant = _xy(f)
        x93, y93 = xy[0] + O[0], xy[1] + O[1]
        f["geometry"] = {"type": "Point", "coordinates": [round(x93, 3), round(y93, 3)]}
        p["x_local"], p["y_local"] = round(xy[0], 3), round(xy[1], 3)
        if z is not None:
            p["z_local"] = round(z, 3)
            p["z_sol_ngf"] = round(z + O[2], 2)
        sid, cl = self.ctx.surface(xy)
        if fam == "mobilier" and cl is not None and "classe_surface_2026" in p:
            decision["classe_surface_2026_avant"] = p["classe_surface_2026"]
            p["classe_surface_2026"] = cl
        if fam == "mobilier" and "distance_bordure_gam_m" in p:
            k, d = self.ctx.bordure_gam(xy)
            if d is not None:
                decision["distance_bordure_gam_m_avant"] = p["distance_bordure_gam_m"]
                p["distance_bordure_gam_m"] = round(d, 2)
        decision["surface_apres"] = sid
        self.deplaces[ident] = (avant, list(xy))
        _ajouter_decision(f, decision)
        return avant

    def _orienter(self, ident, az, decision):
        fam, f = self.obj[ident]
        p = f["properties"]
        a0 = p.get("azimut_deg")
        p["azimut_deg"] = round(float(az), 1)
        if a0 is not None and p.get("yaw_deg") is not None:
            p["yaw_deg"] = round((float(p["yaw_deg"]) + float(az) - float(a0)) % 360.0, 1)
        _ajouter_decision(f, decision)
        return a0

    def _retirer(self, ident, statut, decision):
        fam, f = self.obj[ident]
        p = f["properties"]
        avant = {"instancier": p.get("instancier", True), "statut_2026": p.get("statut_2026")}
        p["instancier"] = False
        p["statut_2026"] = statut
        self.non_instancies.add(ident)
        _ajouter_decision(f, decision)
        return avant

    # ------------------------------------------------------------------ 1. existence
    def existence(self):
        for ident in sorted(self.E):
            if ident not in self.obj:
                continue
            e = self.E[ident]
            fam, f = self.obj[ident]
            p = f["properties"]
            xy = _xy(f)
            ex, st = e["existence"], e["statut_verification"]
            if ex in ("absent_2026", "retirer") and st in ("absent_2026", "a_retirer") and e["preuve_stricte"]["obs"]:
                obs = e["preuve_stricte"]["obs"]
                if RR.projection_lointaine(obs, self.S.observations):
                    self.J.non_resolu(ident, fam, "absence_projection_lointaine", origine="incertain", xy=xy,
                                      regles=["RES-EXI-005"] + e["regles"], observations=obs, classe=p.get("type"),
                                      motif="absence vue seulement en projection à plus de 15 m de la caméra")
                    continue
                pose_2025 = "2025" in str(p.get("statut_2026")) or "projet" in str(p.get("statut_2026"))
                gam = "GAM" in str(p.get("source"))
                if e["tranche_stricte"] != "apres_travaux" and (pose_2025 or gam):
                    self.J.non_resolu(ident, fam, "absence_anterieure_contre_2026", origine="conflit", xy=xy,
                                      motif=f"absence vue avant la fin des travaux ({e['tranche_stricte']}) contre un objet "
                                            f"{'levé GAM 2026' if gam else 'posé en 2025'}",
                                      regles=["RES-EXI-002"] + e["regles"], observations=obs, classe=p.get("type"))
                    continue
                if not p.get("instancier", True) and fam == "arbres":
                    continue
                dec = {"nature": "non_instancie_absent_2026", "regles": ["RES-EXI-001"] + e["regles"],
                       "observations": obs, "conf": "moyenne", "source": "fusion_recensement/0.3"}
                avant = self._retirer(ident, "absent 2026 (fusion 0.3, preuve stricte)", dec)
                self.J.appliquer(ident, fam, "non_instancie_absent_2026", avant=avant,
                                 apres={"instancier": False, "statut_2026": p["statut_2026"]},
                                 regles=dec["regles"], observations=obs, conf="moyenne", xy_avant=xy, xy_apres=xy,
                                 motif=f"absence 2026 prouvée ({e['tranche_stricte']}, {e['categorie_preuve']})",
                                 portee=2.0, classe=p.get("type"))
            elif ex == "absent_2026_a_verifier":
                self.J.non_resolu(ident, fam, "absence_a_verifier", origine="incertain", xy=xy,
                                  motif="absence 2026 sans preuve stricte (FUS-EXI-04) : entité gardée",
                                  regles=["RES-EXI-004"] + e["regles"], observations=e["obs"], classe=p.get("type"))
        # RES-EXI-003 : absences relevées par la revue adverse v2 et confirmées par la seconde lecture
        for ident in sorted(self.RL):
            rl = self.RL[ident]
            rv = self.R2.get(ident)
            if rl["verdict"] != "absent_2026" or not rv or rv["portee"] != "existence" or ident not in self.obj:
                continue
            fam, f = self.obj[ident]
            if ident in self.non_instancies:
                continue
            xy = _xy(f)
            dec = {"nature": "non_instancie_absent_2026", "regles": ["RES-EXI-003", "RES-SRC-001"],
                   "observations": ["pnx:f8d91bb1", "pnx:ded07efa", "pnx:00c1ba9a"], "conf": "moyenne",
                   "revue": _txt_revue(rv), "seconde_lecture": f"{RV.RELECTURE_ID} : {rl['lecture']}"}
            avant = self._retirer(ident, "absent 2026 (photos calées 2026-07-28, revue + seconde lecture)", dec)
            self.J.appliquer(ident, fam, "non_instancie_absent_2026", avant=avant,
                             apres={"instancier": False, "statut_2026": f["properties"]["statut_2026"]},
                             regles=dec["regles"], observations=dec["observations"], revue=dec["revue"], conf="moyenne",
                             xy_avant=xy, xy_apres=xy, portee=2.0, classe=f["properties"].get("type"),
                             motif="arbre levé GAM absent sur les 3 photos 2026 calées ; à intégrer comme constat ARB "
                                   "dans arbitrages_fusion.json (propriétaire de la fusion)")

    # ------------------------------------------------------------------ 2. positions
    def positions(self):
        for ident in sorted(self.O):
            o = self.O[ident]
            if "correction" not in o or ident not in self.obj:
                continue
            c = o["correction"]
            fam, f = self.obj[ident]
            xy0 = _xy(f)
            d = float(c.get("d_m") or 0.0)
            if ident in self.non_instancies:
                continue
            if d < 0.005:
                continue
            rv, rv1 = self.R2.get(ident), self.R1.get(ident)
            m = o["preuve"].get("mesure")
            meth = [r["source"] for r in m["retenues"]] if m else []
            mobs = sorted({x for r in (m["retenues"] if m else []) for x in r.get("preuves", [])})
            photos = sorted({ph["photo"] for ph in (c.get("photos_planche") or []) if ph.get("decisive")})
            xy1 = [float(v) for v in c["p_resolu_local"]]
            z1 = c.get("z_resolu_local")
            classe = o.get("type")
            prop = {"p_resolu_local": xy1, "d_m": d, "statut_coherence": o["statut_resolution"]}
            appliquer, regles, conf, revue, motif = False, [], c.get("conf") or "faible", None, ""
            if rv and rv["portee"] == "position":
                revue = _txt_revue(rv)
                if rv["verdict"] == "juste":
                    appliquer, regles = True, ["RES-POS-001", "RES-SRC-001"]
                    conf = "moyenne"
                    motif = "mesure jugée juste par la revue adverse v2"
                else:
                    self.J.non_resolu(ident, fam, "position", origine="incertain" if rv["verdict"] == "incertain" else
                                      "proposition_rejetee", xy=xy0, regles=["RES-POS-003"], observations=mobs + photos,
                                      revue=revue, proposition=prop, classe=classe,
                                      motif=f"déplacement de {d:.2f} m non appliqué : revue « {rv['verdict']} »")
                    continue
            elif m:
                tri = all(s in METHODES_TRIANGULEES for s in meth)
                if tri and d <= RR.SEUIL_DOUBLE_LECTURE_M and not c.get("drapeaux"):
                    appliquer, regles, conf = True, ["RES-POS-001"], "moyenne"
                    motif = f"triangulation multi-vues ({', '.join(r['methode'] for r in m['retenues'])}) de {d:.2f} m, " \
                            f"sous le seuil de double lecture"
                else:
                    self.J.non_resolu(ident, fam, "position", origine="proposition_rejetee", xy=xy0,
                                      regles=["RES-POS-001", "RES-POS-002"], observations=mobs + photos, proposition=prop,
                                      classe=classe, motif=f"mesure non revue ({', '.join(meth)}) de {d:.2f} m : au-delà de "
                                                           f"0,30 m ou non triangulée, double lecture requise")
                    continue
            elif o["statut_resolution"] == "corrige":
                if o.get("statut_objet") in ("deduit", "projet") and c.get("budget_respecte"):
                    appliquer, regles, conf = True, ["RES-POS-004"], "faible"
                    motif = f"objet {o['statut_objet']} : position a priori mise en conformité ({', '.join(c.get('regles_dures') or [])})"
                elif rv1 and rv1["verdict"] == "juste":
                    appliquer, regles, conf = True, ["RES-POS-004", "RES-SRC-001"], "faible"
                    revue = _txt_revue(rv1, RV.REVUE_V1_ID)
                    motif = "objet existant hors de la chaussée : sens et position légale jugés justes par la revue v1, " \
                            "ampleur minimale"
                else:
                    self.J.non_resolu(ident, fam, "violation_physique", origine="proposition_rejetee", xy=xy0,
                                      regles=["RES-POS-004"], proposition=prop, classe=classe,
                                      revue=_txt_revue(rv) if rv else None,
                                      motif=f"déplacement par la règle de {d:.2f} m ({', '.join(c.get('regles_dures') or [])}) "
                                            f"sans mesure ni revue : objet ou surface ({o['contexte'].get('zone')}, classe "
                                            f"{'faible' if o['contexte'].get('classe_faible') else 'sûre'}) à vérifier")
                    continue
            else:
                self.J.non_resolu(ident, fam, "position", origine="proposition_rejetee", xy=xy0, proposition=prop,
                                  classe=classe, regles=["RES-NRE-001"],
                                  motif=f"déplacement de {d:.2f} m ({o['statut_resolution']}) sans mesure retenue")
                continue
            if not appliquer:
                continue
            dec = {"nature": "deplacement", "regles": regles, "observations": mobs + photos, "conf": conf,
                   "revue": revue, "d_m": d, "source": f"coherence v2 ({o['statut_resolution']})",
                   "methodes": [r["methode"] for r in m["retenues"]] if m else ["regle"]}
            if rv and rv.get("reserve_sigma"):
                dec["sigma_m"] = max(RR.SIGMA_PLANCHER_PHOTO_UNIQUE_M, float(m["sigma_m"]) if m else 0.0)
                dec["reserve"] = rv["reserve_sigma"]
            # RES-POS-006 : statut temporel d'un objet déplacé par les travaux (mesure postérieure)
            dates = [r.get("date") or "" for r in (m["retenues"] if m else [])]
            if d >= RR.DEPLACE_TRAVAUX_M and dates and max(dates) >= RR.FIN_TRAVAUX and o.get("statut_objet") == "existant":
                p = f["properties"]
                dec["statut_2026_avant"] = p.get("statut_2026")
                p["statut_2026"] = (rv or {}).get("reserve_statut") or "déplacé lors des travaux 2025 (mesuré 2026)"
                regles = regles + ["RES-POS-006"]
                dec["regles"] = regles
            avant = self._deplacer(ident, xy1, z1, dec)
            self.J.appliquer(ident, fam, "deplacement", avant={"xy_local": avant}, apres={"xy_local": xy1, "d_m": d},
                             regles=regles, observations=mobs + photos, revue=revue, conf=conf, motif=motif,
                             xy_avant=avant, xy_apres=xy1, portee=d, classe=classe)

    # ------------------------------------------------------------------ 3. orientations
    def orientations(self):
        for ident in sorted(self.O):
            o = self.O[ident]
            if "correction" not in o or ident not in self.obj or ident in self.non_instancies:
                continue
            c = o["correction"]
            a0, a1 = c.get("azimut_source_deg"), c.get("azimut_resolu_deg")
            if a1 is None or (a0 is not None and abs((a1 - a0 + 180) % 360 - 180) < 0.5):
                continue
            fam, f = self.obj[ident]
            xy = _xy(f)
            rv = self.R2.get(ident)
            classe = o.get("type")
            prop = {"azimut_source_deg": a0, "azimut_resolu_deg": a1, "motif": c.get("orientation_raison")}
            if rv and rv["portee"] == "azimut" and rv["verdict"] == "juste":
                regles, conf, revue, motif = ["RES-ORI-001", "RES-SRC-001"], "moyenne", _txt_revue(rv), "azimut jugé juste par la revue"
            elif rv and rv.get("azimut") == "plausible":
                regles, conf, revue = ["RES-ORI-001", "RES-POS-003"], "faible", _txt_revue(rv)
                motif = "azimut mesuré par le raccourci des plaques (4 vues) et jugé plausible ; position non appliquée"
            elif a0 is None:
                regles, conf, revue = ["RES-ORI-001"], "faible", None
                motif = f"azimut absent complété par la règle ({c.get('orientation_motif') or c.get('orientation_raison')})"
            else:
                self.J.non_resolu(ident, fam, "orientation", origine="incertain" if rv else "proposition_rejetee", xy=xy,
                                  regles=["RES-ORI-001"], revue=_txt_revue(rv) if rv else None, proposition=prop,
                                  classe=classe, motif=f"réorientation {a0}° -> {a1}° sans revue juste")
                continue
            dec = {"nature": "reorientation", "regles": regles, "conf": conf, "revue": revue,
                   "azimut_avant_deg": a0, "azimut_apres_deg": a1}
            self._orienter(ident, a1, dec)
            daz = 180.0 if a0 is None else abs((a1 - a0 + 180) % 360 - 180)
            self.J.appliquer(ident, fam, "reorientation", avant={"azimut_deg": a0}, apres={"azimut_deg": a1},
                             regles=regles, revue=revue, conf=conf, motif=motif, xy_avant=xy, xy_apres=xy,
                             portee=daz / 60.0 if a0 is not None else 0.2, classe=classe)

    # ------------------------------------------------------------------ 4. têtes de feux
    def tetes(self):
        for t in sorted(self.S.rapport.get("tetes", []), key=lambda t: t["id"]):
            sup = t["support"]
            if sup not in self.obj:
                continue
            fam, f = self.obj[sup]
            xy = _xy(f)
            if t["statut"] == "orientation_signalee":
                self.J.non_resolu(t["id"], "mobilier", "orientation_tete", origine="incertain", xy=xy,
                                  regles=["RES-ORI-002", t["regle"]], classe=t["type_tete"],
                                  proposition={"azimut_source": t["azimut_source"], "cible": t["cible"]},
                                  motif=f"tête à {t['ecart_deg']}° de la cible ({t['motif']}) : gardée par la cohérence")
                continue
            if t["statut"] != "reoriente":
                continue
            tetes = f["properties"].get("tetes") or []
            pris = self._tetes_prises.setdefault(sup, set())
            cand = [j for j, tt in enumerate(tetes) if tt.get("type") == t["type_tete"] and j not in pris
                    and tt.get("azimut_deg") is not None and abs(float(tt["azimut_deg"]) - float(t["azimut_source"])) < 0.5]
            k = cand[0] if cand else None
            if k is not None:
                pris.add(k)
            if k is None:
                self.J.non_resolu(t["id"], "mobilier", "orientation_tete", origine="conflit", xy=xy, regles=["RES-ORI-002"],
                                  classe=t["type_tete"], motif="tête introuvable ou de type différent dans le support")
                continue
            a0 = float(tetes[k]["azimut_deg"])
            a1 = float(t["azimut_resolu"])
            daz = abs((a1 - a0 + 180) % 360 - 180)
            if a0 % 45.0 != 0.0 or daz > 60.0:
                self.J.non_resolu(t["id"], "mobilier", "orientation_tete", origine="proposition_rejetee", xy=xy,
                                  regles=["RES-ORI-002", t["regle"]], classe=t["type_tete"],
                                  proposition={"azimut_source": a0, "azimut_resolu": a1},
                                  motif=f"azimut source {a0}° non saisi au pas de 45° ou écart {daz:.1f}° > 60°")
                continue
            tetes[k]["azimut_deg"] = round(a1, 1)
            dec = {"nature": "reorientation_tete", "tete": t["id"], "type": t["type_tete"], "regles": ["RES-ORI-002", t["regle"]],
                   "conf": "faible", "azimut_avant_deg": a0, "azimut_apres_deg": a1, "motif": t["motif"]}
            _ajouter_decision(f, dec)
            self.J.appliquer(t["id"], "mobilier", "reorientation_tete", avant={"azimut_deg": a0}, apres={"azimut_deg": a1},
                             regles=dec["regles"], conf="faible", xy_avant=xy, xy_apres=xy, portee=daz / 90.0,
                             classe=t["type_tete"], motif=f"azimut de saisie {a0}° remplacé par la cible fonctionnelle "
                                                          f"({t['motif']})")

    # ------------------------------------------------------------------ 5. fusion de supports (P5)
    def fusions(self):
        for p in sorted(self.S.rapport.get("propositions", []), key=lambda p: p["id"]):
            if p["type"] != "fusion_supports":
                continue
            a, b = p["id"].split("-", 1)[1].split("-", 1) if p["id"].count("-") >= 2 else (None, None)
            rv = self.R2.get(b) or self.R2.get(a)
            if not (a in self.obj and b in self.obj and rv and rv["verdict"] == "juste" and rv.get("fusion_avec") in (a, b)):
                xy = _xy(self.obj[a][1]) if a in self.obj else None
                self.J.non_resolu(p["id"], "mobilier", "fusion_supports", origine="incertain", xy=xy, regles=["RES-POS-005"],
                                  motif=p["justification"])
                continue
            porteur, porte = (a, b) if self.obj[a][1]["properties"].get("type") == "lampadaire" else (b, a)
            fam, f = self.obj[porte]
            xy = _xy(f)
            dec = {"nature": "support_commun", "regles": ["RES-POS-005"], "conf": "moyenne", "revue": _txt_revue(rv),
                   "porte_par": porteur, "instancier_fut": False}
            f["properties"]["porte_par"] = porteur
            f["properties"]["instancier_fut"] = False
            _ajouter_decision(f, dec)
            self.J.appliquer(porte, fam, "support_commun", avant={"porte_par": None}, apres={"porte_par": porteur},
                             regles=dec["regles"], revue=dec["revue"], conf="moyenne", xy_avant=xy, xy_apres=xy,
                             portee=0.5, classe=f["properties"].get("type"),
                             motif=f"{p['justification']} : un seul fût ({porteur}), {porte} porté")

    # ------------------------------------------------------------------ 6. attributs (fusion « appliquer »)
    def attributs(self):
        for ft in sorted(self.S.attributs, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            ident = q["id"]
            if ident not in self.obj or q["famille"] not in ("arbres", "mobilier"):
                continue
            fam, f = self.obj[ident]
            p = f["properties"]
            xy = _xy(f)
            table = ATTR_ARBRES if fam == "arbres" else ATTR_MOBILIER
            for a in sorted(q["maj"]):
                m = q["maj"][a]
                if m.get("decision") != "appliquer":
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="incertain", xy=xy, regles=["RES-ATT-001"] +
                                      m.get("regle", "").replace(" ", "").split(";"), observations=m.get("obs", []),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")}, classe=p.get("type"),
                                      motif=f"mise à jour {a} en revue (FUS-ATT-06)")
                    continue
                if m.get("conf") not in RR.CONFIANCES_PROBANTES:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="incertain", xy=xy, regles=["RES-ATT-001"],
                                      observations=m.get("obs", []), classe=p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"valeur {m.get('apres')!r} de confiance {m.get('conf')} (< moyenne)")
                    continue
                if fam == "arbres" and a == "type" and m["apres"] not in RR.TYPES_ARBRE:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="schema", xy=xy, regles=["RES-ATT-001"],
                                      observations=m.get("obs", []), classe=p.get("type"),
                                      proposition={"avant": m.get("avant"), "apres": m.get("apres")},
                                      motif=f"type {m['apres']!r} hors des types d'arbres du paquet (objet à requalifier : "
                                            f"haie ou massif)")
                    continue
                cle = table.get(a)
                if cle is None:
                    self.J.non_resolu(ident, fam, f"attribut:{a}", origine="schema", xy=xy, regles=["RES-ATT-001"],
                                      observations=m.get("obs", []), classe=p.get("type"),
                                      motif=f"attribut {a} sans équivalent dans le schéma des objets")
                    continue
                v = m["apres"]
                if a == "azimut_deg":
                    oc = (self.O.get(ident) or {}).get("correction") or {}
                    a_coh = oc.get("azimut_resolu_deg")
                    va = (self.S.revue_coh.get(ident) or {}).get("verdict_azimut")
                    if a_coh is not None and abs((float(v) - float(a_coh) + 180) % 360 - 180) > 20:
                        note = f" (revue de cohérence : azimut {va})" if va else ""
                        self.J.non_resolu(ident, fam, "attribut:azimut_deg", origine="conflit", xy=xy, regles=["RES-ATT-001"],
                                          observations=m.get("obs", []), classe=p.get("type"),
                                          proposition={"avant": m.get("avant"), "apres": v, "azimut_coherence": a_coh},
                                          motif=f"azimut fusion {v}° contre azimut {a_coh}° de la cohérence v2{note}")
                        continue
                    avant = p.get("azimut_deg")
                    self._orienter(ident, float(v), {"nature": "attribut", "attribut": a, "regles": ["RES-ATT-001"],
                                                     "observations": m.get("obs", []), "conf": m.get("conf")})
                else:
                    avant = p.get(cle)
                    p[cle] = v
                    _ajouter_decision(f, {"nature": "attribut", "attribut": cle, "avant": avant, "apres": v,
                                          "regles": ["RES-ATT-001"] + [r.strip() for r in m.get("regle", "").split(";") if r.strip()],
                                          "observations": m.get("obs", []), "conf": m.get("conf")})
                self.J.appliquer(ident, fam, "attribut", avant={cle: avant}, apres={cle: v},
                                 regles=["RES-ATT-001"] + [r.strip() for r in m.get("regle", "").split(";") if r.strip()],
                                 observations=m.get("obs_strictes") or m.get("obs", []), conf=m.get("conf") or "moyenne",
                                 xy_avant=xy, xy_apres=xy, portee=0.05, classe=p.get("type"),
                                 motif=f"{cle} : {avant} -> {v} (FUS-ATT-06, preuve stricte)")

    # ------------------------------------------------------------------ 7. propositions et listes restantes
    def restes(self):
        R2 = self.R2
        for ident in sorted(self.O):
            o = self.O[ident]
            if ident not in self.obj:
                continue
            fam, f = self.obj[ident]
            xy = _xy(f)
            st = o["statut_resolution"]
            if st == "anomalie_surface":
                c = o.get("correction") or {}
                self.J.non_resolu(ident, "surfaces", "anomalie_surface", origine="conflit", xy=xy, regles=["RES-NRE-001"],
                                  classe=o.get("type"),
                                  motif="objet prouvé sur une surface de classe " + str(o.get("contexte", {}).get("zone")) +
                                        " : surface à corriger par le propriétaire de surfaces.py ; " +
                                        "; ".join(c.get("justification", [])[:1])[:300])
            elif st in ("non_resolu", "a_arbitrer_photo"):
                rv = R2.get(ident)
                self.J.non_resolu(ident, fam, "existence", origine="incertain", xy=xy, regles=["RES-EXI-004", "RES-NRE-001"],
                                  revue=_txt_revue(rv) if rv else None, classe=o.get("type"),
                                  motif=f"non-instanciation proposée par la cohérence ({st}, "
                                        f"{', '.join((o.get('correction') or {}).get('drapeaux', []))}) : entité gardée "
                                        f"telle que la base")
            rv = R2.get(ident)
            if rv and rv["portee"] == "conforme" and rv["verdict"] == "incertain":
                self.J.non_resolu(ident, fam, "conforme_non_verifiable", origine="incertain", xy=xy, regles=["RES-NRE-001"],
                                  revue=_txt_revue(rv), classe=o.get("type"), motif="« conforme » non vérifiable sur image")
            if rv and rv.get("reserve_type"):
                self.J.non_resolu(ident, fam, "type", origine="incertain", xy=xy, regles=["RES-NRE-001"], revue=_txt_revue(rv),
                                  classe=o.get("type"), motif=f"type à vérifier : {rv['reserve_type']}")
        # RES-NRE-002 : présence 2026 non testée près des photos 2026 calées (Q4)
        for ident in sorted(self.obj):
            fam, f = self.obj[ident]
            p = f["properties"]
            if ident in self.non_instancies or p.get("instancier") is False or f["geometry"]["type"] != "Point":
                continue
            xy = _xy(f)
            vues = sorted((round(float(np.hypot(xy[0] - c[0], xy[1] - c[1])), 1), ph) for ph, c in self.S.poses_2026)
            vues = [(d, ph) for d, ph in vues if d <= RR.RAYON_PRESENCE_2026_M]
            if not vues:
                continue
            e = self.E.get(ident) or {}
            if e.get("tranche_stricte") == "apres_travaux" and e.get("existence") == "present":
                continue
            self.J.non_resolu(ident, fam, "presence_2026_non_testee", origine="incertain", xy=xy, regles=["RES-NRE-002"],
                              observations=[ph for _, ph in vues], classe=p.get("type"),
                              motif="visible depuis " + ", ".join(f"{ph} ({d} m)" for d, ph in vues) +
                                    " : aucune preuve stricte après travaux ; test de présence sur vignette à faire")
        for ident in sorted(self.fcorr):
            q = self.fcorr[ident]
            if ident not in self.obj:
                continue
            fam, f = self.obj[ident]
            if ident in self.deplaces:
                continue
            xy = _xy(f)
            motif = f"correction fusion {q['decision']} de {q['d_m']} m ({', '.join(q.get('methodes') or [])})"
            if q["decision"] == "appliquer":
                oc = self.O.get(ident, {})
                rej = [m.get("motif_rejet") for m in (oc.get("preuve") or {}).get("mesures_candidates", []) if m.get("motif_rejet")]
                rv = R2.get(ident)
                motif += " non appliquée : " + ("; ".join(rej) if rej else (f"revue « {rv['verdict']} »" if rv else "sans corroboration"))
            self.J.non_resolu(ident, fam, "position_fusion", origine="conflit" if q["decision"] == "appliquer" else "incertain",
                              xy=xy, regles=["RES-POS-002"] + q.get("regles", []), observations=q.get("obs", []),
                              proposition={"d_m": q["d_m"], "sigma_m": q["sigma_m"], "p_fusion_local": q.get("p_fusion_local")},
                              classe=q.get("type"), motif=motif + "; " + "; ".join(q.get("raisons", []))[:300])
        for p in sorted(self.S.rapport.get("propositions", []), key=lambda p: p["id"]):
            if p["type"] in ("fusion_supports", "supports_distincts"):
                continue
            xy = p.get("p_local")
            if xy is None:
                ids = [i for i in self.obj if i in p["id"]]
                xy = _xy(self.obj[ids[0]][1]) if ids else None
            self.J.non_resolu(p["id"], "objets" if p["type"] != "surface_a_corriger" else "surfaces", p["type"],
                              origine="incertain", xy=xy, regles=["RES-NRE-001", p.get("regle") or "coherence"],
                              observations=p.get("preuves", []), motif=p["justification"][:300])

    def executer(self):
        self.existence()
        self.positions()
        self.orientations()
        self.tetes()
        self.fusions()
        self.attributs()
        self.restes()
        mob = [f for i, (fam, f) in sorted(self.obj.items()) if fam == "mobilier"]
        arb = [f for i, (fam, f) in sorted(self.obj.items()) if fam == "arbres"]
        return mob, arb
