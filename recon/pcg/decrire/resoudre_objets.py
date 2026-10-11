"""Résolution des objets (mobilier, panneaux, feux, candélabres, arbres) du paquet v1.

Sorties : objets/mobilier.geojson et objets/arbres.geojson, même schéma que le paquet, plus une propriété
`resolution` (décisions appliquées avec provenance) sur chaque objet modifié. Les positions décidées viennent de la
cohérence v3 (p_resolu) ; la fusion 0.3 et les revues adverses (v3 de référence, v2 si la décision relue n'a pas
changé : RES-SRC-002) décident de ce qui est appliqué (resoudre_regles.REGLES). Une position que la cohérence a
abandonnée à tort (retour à la source jugé « faux » par la revue v3, preuve photo 2026 et seconde lecture) est
reprise depuis la position prouvée par la revue (RES-POS-007).
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
# drapeaux de la cohérence qui ne portent pas sur la mesure retenue (un candidat écarté devenu indice)
DRAPEAUX_NON_BLOQUANTS = {"mesure_indice_q1"}
SURFACES_INTERDITES_MAT = {"chaussee", "parking", "piste_cyclable", "acces_riverain"}
NATURES_CONFORME_V3 = {"pan_B1_1": "orientation_ambigue", "armoire_1313238971": "position_douteuse",
                       "banc_8360664518": "position_douteuse", "arbre_462": "existence"}


def _xy(f):
    p = f["properties"]
    if p.get("x_local") is not None:
        return [float(p["x_local"]), float(p["y_local"])]
    g = f["geometry"]
    c = np.asarray(g["coordinates"], float)
    c = c if c.ndim == 1 else c.mean(axis=0)
    return [float(c[0] - O[0]), float(c[1] - O[1])]


def _txt_revue(rv, src=RV.REVUE_V2_ID):
    return RV.txt(rv, src)


def _ajouter_decision(f, d):
    r = f["properties"].setdefault("resolution", {"decisions": []})
    r["decisions"].append(arrondi(d))


class ResolveurObjets:
    def __init__(self, S, J, ctx, mnt=None):
        self.S, self.J, self.ctx, self.mnt = S, J, ctx, mnt
        self.obj = {}
        for fam, fc in (("mobilier", S.mobilier), ("arbres", S.arbres)):
            for f in fc["features"]:
                self.obj[f["properties"]["id"]] = (fam, copy.deepcopy(f))
        self.O = S.objets_coherence()
        self.R3 = RV.index_revue_v3()
        self.R2 = RV.index_revue_v2()
        self.R1 = RV.index_revue_v1()
        self.RL = RV.index_relecture()
        self.E = S.entites
        self.fcorr = {f["properties"]["id"]: f["properties"] for f in S.corr_pos}
        self.desaccords = {}
        for e in S.conflits_fusion:
            self.desaccords.setdefault(e["entite"], []).append(e)
        self.deplaces = {}          # id -> (xy_avant, xy_apres)
        self._tetes_prises = {}
        self.non_instancies = set()
        self.traites_existence = set()

    # ------------------------------------------------------------------ utilitaires
    def _z(self, xy):
        if self.mnt is None:
            return None
        return float(self.mnt(np.array([xy[0] + O[0]]), np.array([xy[1] + O[1]]))[0]) - O[2]

    def _revue(self, ident):
        """Texte du verdict le plus récent qui nomme l'objet (v3 puis v2), pour la provenance des listes."""
        if ident in self.R3:
            return _txt_revue(self.R3[ident], RV.REVUE_V3_ID)
        if ident in self.R2:
            return _txt_revue(self.R2[ident], RV.REVUE_V2_ID)
        return None

    def _relecture(self, ident, rv):
        for i in [ident] + list((rv or {}).get("groupe", [])):
            if i in self.RL:
                return self.RL[i]
        return None

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
                rv3 = self.R3.get(ident)
                if rv3 and rv3["verdict"] == "juste":
                    dec["revue"] = _txt_revue(rv3, RV.REVUE_V3_ID)
                avant = self._retirer(ident, "absent 2026 (fusion 0.3, preuve stricte)", dec)
                self.traites_existence.add(ident)
                self.J.appliquer(ident, fam, "non_instancie_absent_2026", avant=avant,
                                 apres={"instancier": False, "statut_2026": p["statut_2026"]},
                                 regles=dec["regles"], observations=obs, conf="moyenne", xy_avant=xy, xy_apres=xy,
                                 revue=dec.get("revue"),
                                 motif=f"absence 2026 prouvée ({e['tranche_stricte']}, {e['categorie_preuve']})",
                                 portee=2.0, classe=p.get("type"))
            elif ex == "absent_2026_a_verifier":
                self.J.non_resolu(ident, fam, "absence_a_verifier", origine="incertain", xy=xy,
                                  motif="absence 2026 sans preuve stricte (FUS-EXI-04) : entité gardée",
                                  regles=["RES-EXI-004"] + e["regles"], observations=e["obs"], classe=p.get("type"))
        # RES-EXI-003 / RES-EXI-006 : non-instanciations de la cohérence v3 (revue de présence Q4) jugées par la revue v3
        for ident in sorted(self.O):
            o = self.O[ident]
            if o["statut_resolution"] != "non_instancie_absent_2026" or ident not in self.obj or ident in self.non_instancies:
                continue
            fam, f = self.obj[ident]
            p = f["properties"]
            if p.get("instancier") is False:
                continue                         # déjà non instancié dans le paquet : rien à décider
            xy = _xy(f)
            pres = o.get("presence_2026") or {}
            prev = pres.get("revue") or {}
            photos = sorted(prev.get("photos") or [])
            rv3 = self.R3.get(ident)
            rl = self._relecture(ident, rv3)
            self.traites_existence.add(ident)
            if rv3 and rv3["verdict"] == "juste" and rv3.get("existence") == "souche_presente":
                if p.get("type") == "souche":
                    self.J.confirmer(ident, fam, "souche_presente", xy=xy, classe=p.get("type"),
                                     regles=["RES-EXI-006", "RES-SRC-002"], observations=photos,
                                     revue=_txt_revue(rv3, RV.REVUE_V3_ID),
                                     seconde_lecture=f"{RV.RELECTURE_ID} : {rl['lecture']}" if rl else None,
                                     motif="arbre absent, souche présente : l'objet décrit est la souche (type souche, levé "
                                           "GAM, 0,4 m), vue sur ded07efa et f8d91bb1 ; non-instanciation de la cohérence "
                                           "non appliquée, souche gardée instanciée")
                else:
                    self.J.non_resolu(ident, fam, "souche", origine="schema", xy=xy, regles=["RES-EXI-006"],
                                      observations=photos, revue=_txt_revue(rv3, RV.REVUE_V3_ID), classe=p.get("type"),
                                      motif="arbre abattu, souche présente : requalifier l'objet en souche (type du paquet)")
                continue
            if rv3 and rv3["verdict"] == "juste" and rv3.get("existence") == "absent" and rl \
                    and rl["verdict"] == "absent_2026":
                dec = {"nature": "non_instancie_absent_2026", "regles": ["RES-EXI-003", "RES-SRC-001", "RES-SRC-002"],
                       "observations": photos, "conf": "moyenne", "revue": _txt_revue(rv3, RV.REVUE_V3_ID),
                       "seconde_lecture": f"{RV.RELECTURE_ID} : {rl['lecture']}",
                       "revue_presence_q4": prev.get("note")}
                avant = self._retirer(ident, f"absent 2026 (photos calées {prev.get('date') or '2026-07-28'}, revue de "
                                             f"présence, revue adverse v3 et seconde lecture)", dec)
                self.J.appliquer(ident, fam, "non_instancie_absent_2026", avant=avant,
                                 apres={"instancier": False, "statut_2026": p["statut_2026"]},
                                 regles=dec["regles"], observations=photos, revue=dec["revue"], conf="moyenne",
                                 xy_avant=xy, xy_apres=xy, portee=2.0, classe=p.get("type"),
                                 motif="absent sur les photos 2026 calées (revue de présence Q4 de la cohérence, jugée "
                                       "juste par la revue v3, seconde lecture) ; à intégrer comme constat ARB dans "
                                       "arbitrages_fusion.json (propriétaire de la fusion)",
                                 extra={"seconde_lecture": dec["seconde_lecture"]})
                continue
            prop = None
            if rv3 and rv3.get("p_probable_local"):
                prop = {"hypothese": rv3.get("existence"), "p_probable_local": rv3["p_probable_local"]}
            motif = "non-instanciation de la cohérence (revue de présence : " + str(prev.get("note") or "absent")[:160] + ")"
            if rv3:
                motif += f" jugée « {rv3['verdict']} » par la revue v3"
                if rv3.get("existence") == "deplacement_probable":
                    motif += f" : déplacement probable vers ({rv3['p_probable_local'][0]:.1f} ; {rv3['p_probable_local'][1]:.1f})"
            elif not rl:
                motif += " sans revue adverse ni seconde lecture"
            self.J.non_resolu(ident, fam, "existence", origine="incertain", xy=xy, regles=["RES-EXI-003", "RES-NRE-001"],
                              observations=photos, revue=_txt_revue(rv3, RV.REVUE_V3_ID) if rv3 else None,
                              proposition=prop, classe=p.get("type"),
                              motif=motif + " : entité gardée telle que la base, à vérifier sur le terrain")

    # ------------------------------------------------------------------ 2. positions
    def _position_prouvee(self, ident, o, rv):
        """RES-POS-007 : retour à la source jugé faux, position prouvée par la revue et la seconde lecture."""
        fam, f = self.obj[ident]
        xy0 = _xy(f)
        pp = rv["position_prouvee"]
        xy1 = [float(v) for v in pp["p_local"]]
        d = float(np.hypot(xy1[0] - xy0[0], xy1[1] - xy0[1]))
        rl = self._relecture(ident, rv)
        classe = o.get("type")
        fobs = sorted((self.fcorr.get(ident) or {}).get("obs") or [])
        obs = sorted(set(pp.get("photos", [])) | set(fobs))
        if not rl or not str(rl["verdict"]).startswith("position"):
            self.J.non_resolu(ident, fam, "position", origine="incertain", xy=xy0, regles=["RES-POS-007"],
                              observations=obs, revue=_txt_revue(rv, RV.REVUE_V3_ID), classe=classe,
                              proposition={"p_local": xy1, "d_m": round(d, 3)},
                              motif="retour à la source jugé faux, mais sans seconde lecture : position prouvée non reprise")
            return
        dec = {"nature": "deplacement", "regles": ["RES-POS-007", "RES-SRC-001", "RES-SRC-002"], "observations": obs,
               "conf": "moyenne", "revue": _txt_revue(rv, RV.REVUE_V3_ID), "d_m": d,
               "seconde_lecture": f"{RV.RELECTURE_ID} : {rl['lecture']}", "source": pp["source"],
               "methodes": ["revue_adverse_photo_2026"], "sigma_m": RR.SIGMA_PLANCHER_PHOTO_UNIQUE_M,
               "decision_coherence_v3": f"retour à la source ({o['statut_resolution']}, "
                                        f"{', '.join((o.get('correction') or {}).get('drapeaux') or []) or 'sans drapeau'})"}
        avant = self._deplacer(ident, xy1, self._z(xy1), dec)
        sid, cl = self.ctx.surface(xy1)
        if cl in SURFACES_INTERDITES_MAT:
            self.J.non_resolu(ident, "surfaces", "anomalie_surface", origine="conflit", xy=xy1, regles=["RES-POS-007", "RES-NRE-003"],
                              observations=obs, classe=classe, revue=dec["revue"],
                              motif=f"position prouvée sur photos (RES-POS-007) sur la classe {cl} ({sid}) : îlot, "
                                    f"trottoir ou espace vert manquant dans la partition ; surface à corriger par le "
                                    f"propriétaire de surfaces.py (le support est sur un sol non roulable sur les photos)")
        self.J.appliquer(ident, fam, "deplacement", avant={"xy_local": avant}, apres={"xy_local": xy1, "d_m": d},
                         regles=dec["regles"], observations=obs, revue=dec["revue"], conf="moyenne", xy_avant=avant,
                         xy_apres=xy1, portee=d, classe=classe,
                         motif=f"retour à la source de la cohérence v3 jugé faux par la revue v3 : position prouvée sur "
                               f"les photos calées {', '.join(pp.get('photos', []))} ({pp['source']}) reprise, seconde "
                               f"lecture concordante",
                         extra={"seconde_lecture": dec["seconde_lecture"]})

    def _indices_non_relus(self, ident, o, xy0):
        """Mesure candidate devenue indice (Q1) sans revue : position de la base gardée, listée (RES-POS-007)."""
        fam, _ = self.obj[ident]
        ind = [m for m in (o["preuve"].get("mesures_candidates") or []) if m.get("motif_indice")]
        if not ind or ident in self.R3:
            return
        m = ind[0]
        xy = [float(v) for v in m["xy"]]
        d = float(np.hypot(xy[0] - xy0[0], xy[1] - xy0[1]))
        if d < 0.05:
            return
        q1 = m.get("q1") or {}
        self.J.non_resolu(ident, fam, "position", origine="incertain", xy=xy0, regles=["RES-POS-001", "RES-POS-007"],
                          observations=sorted(set(m.get("preuves") or []) | set(q1.get("votes_X") or [])
                                              | set(q1.get("votes_A") or [])), classe=o.get("type"),
                          proposition={"p_mesure_local": xy, "d_m": round(d, 3), "methode": m.get("methode"),
                                       "q1": q1.get("verdict"), "somme_r2_X": q1.get("somme_r2_X"),
                                       "somme_r2_A": q1.get("somme_r2_A")},
                          motif=f"mesure de {d:.2f} m ({m.get('methode')}) devenue indice par la cohérence v3 "
                                f"({m['motif_indice']}) et non relue par une revue adverse : position de la base gardée "
                                f"(détecteur Q1 non robuste, R3)")

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
            rv3 = self.R3.get(ident)
            if rv3 and rv3.get("decision_relue") == "retour_source" and rv3["verdict"] == "faux" and rv3.get("position_prouvee"):
                self._position_prouvee(ident, o, rv3)
                continue
            if d < 0.005:
                self._indices_non_relus(ident, o, xy0)
                continue
            rv1 = self.R1.get(ident)
            m = o["preuve"].get("mesure")
            meth = [r["source"] for r in m["retenues"]] if m else []
            mobs = sorted({x for r in (m["retenues"] if m else []) for x in r.get("preuves", [])})
            photos = sorted({ph["photo"] for ph in (c.get("photos_planche") or []) if ph.get("decisive")})
            xy1 = [float(v) for v in c["p_resolu_local"]]
            z1 = c.get("z_resolu_local")
            classe = o.get("type")
            drap = list(c.get("drapeaux") or [])
            prop = {"p_resolu_local": xy1, "d_m": d, "statut_coherence": o["statut_resolution"], "drapeaux": drap}
            rv, src, lien = RV.verdict_position(ident, xy1, self.R3, self.R2)
            appliquer, regles, conf, revue, motif = False, [], c.get("conf") or "faible", None, ""
            if rv is not None:
                revue = _txt_revue(rv, src)
                if rv["verdict"] == "juste":
                    appliquer, regles = True, ["RES-POS-001", "RES-SRC-001", "RES-SRC-002"]
                    conf = "moyenne"
                    motif = f"décision de la cohérence v3 jugée juste par la {'revue v3' if src == RV.REVUE_V3_ID else 'revue v2'} " \
                            f"({lien})"
                else:
                    self.J.non_resolu(ident, fam, "position", origine="incertain" if rv["verdict"] == "incertain" else
                                      "proposition_rejetee", xy=xy0, regles=["RES-POS-003", "RES-SRC-002"],
                                      observations=mobs + photos, revue=revue, proposition=prop, classe=classe,
                                      motif=f"déplacement de {d:.2f} m non appliqué : revue « {rv['verdict']} »")
                    continue
            elif m:
                tri = all(r["source"] in METHODES_TRIANGULEES
                          or str(r.get("methode", "")).startswith(("axe triangulé", "triangulation")) for r in m["retenues"])
                q1 = [r.get("q1") for r in m["retenues"]]
                bloquants = sorted(set(drap) - DRAPEAUX_NON_BLOQUANTS)
                if tri and d <= RR.SEUIL_DOUBLE_LECTURE_M and all(q == "accord" for q in q1) and not bloquants:
                    appliquer, regles, conf = True, ["RES-POS-001"], "moyenne"
                    motif = f"triangulation multi-vues ({', '.join(r['methode'] for r in m['retenues'])}) de {d:.2f} m, " \
                            f"en accord avec les photos (Q1), sous le seuil de double lecture"
                else:
                    raisons = []
                    if not tri:
                        raisons.append("mesure non triangulée")
                    if d > RR.SEUIL_DOUBLE_LECTURE_M:
                        raisons.append("au-delà de 0,30 m")
                    if not all(q == "accord" for q in q1):
                        raisons.append(f"Q1 {', '.join(str(q) for q in q1)}")
                    if bloquants:
                        raisons.append(f"drapeaux {', '.join(bloquants)}")
                    self.J.non_resolu(ident, fam, "position", origine="proposition_rejetee", xy=xy0,
                                      regles=["RES-POS-001", "RES-POS-002", "RES-SRC-002"], observations=mobs + photos,
                                      proposition=prop, classe=classe, revue=self._revue(ident),
                                      motif=f"mesure non revue ({', '.join(meth)}) de {d:.2f} m : {' ; '.join(raisons)} ; "
                                            f"double lecture requise" + (f" ({lien})" if lien else ""))
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
                                      regles=["RES-POS-004"], proposition=prop, classe=classe, revue=self._revue(ident),
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
                   "revue": revue, "d_m": d, "source": f"coherence v3 ({o['statut_resolution']})",
                   "methodes": [r["methode"] for r in m["retenues"]] if m else ["regle"]}
            if drap:
                dec["drapeaux_coherence"] = drap
            if rv and rv.get("reserve_sigma"):
                dec["sigma_m"] = max(RR.SIGMA_PLANCHER_PHOTO_UNIQUE_M, float(m["sigma_m"]) if m else 0.0)
                dec["reserve"] = rv["reserve_sigma"]
            if rv and rv.get("reserve_surface"):
                dec["reserve"] = rv["reserve_surface"]
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
            rv3, rv2 = self.R3.get(ident), self.R2.get(ident)
            classe = o.get("type")
            prop = {"azimut_source_deg": a0, "azimut_resolu_deg": a1, "motif": c.get("orientation_raison")}
            if rv3 and rv3.get("azimut") == "juste" and abs((float(rv3.get("azimut_relu_deg", a1)) - a1 + 180) % 360 - 180) < 0.5:
                regles, conf, revue = ["RES-ORI-001", "RES-SRC-001", "RES-SRC-002"], "moyenne", _txt_revue(rv3, RV.REVUE_V3_ID)
                motif = "azimut jugé juste par la revue v3"
            elif rv3 and "plausible" in str(rv3.get("azimut")):
                regles, conf, revue = ["RES-ORI-001", "RES-POS-003"], "faible", _txt_revue(rv3, RV.REVUE_V3_ID)
                motif = "azimut mesuré par le raccourci des plaques (4 vues) et jugé plausible (revue v2, non contesté en v3) ; " \
                        "position non appliquée"
            elif not rv3 and rv2 and rv2["portee"] == "azimut" and rv2["verdict"] == "juste":
                regles, conf, revue = ["RES-ORI-001", "RES-SRC-001"], "moyenne", _txt_revue(rv2)
                motif = "azimut jugé juste par la revue v2"
            elif a0 is None:
                regles, conf, revue = ["RES-ORI-001"], "faible", None
                motif = f"azimut absent complété par la règle ({c.get('orientation_motif') or c.get('orientation_raison')})"
            else:
                rv = rv3 or rv2
                self.J.non_resolu(ident, fam, "orientation", origine="incertain" if rv else "proposition_rejetee", xy=xy,
                                  regles=["RES-ORI-001"], revue=self._revue(ident), proposition=prop,
                                  classe=classe, motif=f"réorientation {a0}° -> {a1}° sans revue juste")
                continue
            rl = self.RL.get(ident)
            obs = sorted(set((rv3 or {}).get("photos", [])) | set((rl or {}).get("photos", [])))
            dec = {"nature": "reorientation", "regles": regles, "conf": conf, "revue": revue,
                   "azimut_avant_deg": a0, "azimut_apres_deg": a1, "observations": obs}
            extra = None
            if rl and rl["verdict"] == "orientation_a_preciser":
                dec["seconde_lecture"] = f"{RV.RELECTURE_ID} : {rl['lecture']}"
                extra = {"seconde_lecture": dec["seconde_lecture"]}
                self.J.non_resolu(ident, fam, "orientation_a_preciser", origine="incertain", xy=xy,
                                  regles=["RES-ORI-001", "RES-NRE-003"], observations=obs, revue=revue, classe=classe,
                                  proposition={"azimut_applique_deg": a1, "intervalle_lu_deg": [77.0, 109.0]},
                                  motif=f"azimut {a1}° appliqué (revue juste) mais la seconde lecture lit la face entre 77° "
                                        f"et 109° : azimut fin à mesurer sur place")
            self._orienter(ident, a1, dec)
            daz = 180.0 if a0 is None else abs((a1 - a0 + 180) % 360 - 180)
            self.J.appliquer(ident, fam, "reorientation", avant={"azimut_deg": a0}, apres={"azimut_deg": a1},
                             regles=regles, revue=revue, conf=conf, motif=motif, xy_avant=xy, xy_apres=xy,
                             portee=daz / 60.0 if a0 is not None else 0.2, classe=classe, observations=obs, extra=extra)

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
            rv, src = None, None
            for R, s in ((self.R3, RV.REVUE_V3_ID), (self.R2, RV.REVUE_V2_ID)):
                rv = R.get(b) or R.get(a)
                if rv and rv.get("fusion_avec") in (a, b):
                    src = s
                    break
                rv = None
            if not (a in self.obj and b in self.obj and rv and rv["verdict"] == "juste"):
                xy = _xy(self.obj[a][1]) if a in self.obj else None
                self.J.non_resolu(p["id"], "mobilier", "fusion_supports", origine="incertain", xy=xy, regles=["RES-POS-005"],
                                  motif=p["justification"])
                continue
            porteur, porte = (a, b) if self.obj[a][1]["properties"].get("type") == "lampadaire" else (b, a)
            fam, f = self.obj[porte]
            xy = _xy(f)
            dec = {"nature": "support_commun", "regles": ["RES-POS-005"], "conf": "moyenne", "revue": _txt_revue(rv, src),
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
                                          motif=f"azimut fusion {v}° contre azimut {a_coh}° de la cohérence v3{note}")
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

    # ------------------------------------------------------------------ 7. propositions, réserves et listes restantes
    def restes(self):
        R2, R3 = self.R2, self.R3
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
                self.J.non_resolu(ident, fam, "existence", origine="incertain", xy=xy, regles=["RES-EXI-004", "RES-NRE-001"],
                                  revue=self._revue(ident), classe=o.get("type"),
                                  motif=f"non-instanciation proposée par la cohérence ({st}, "
                                        f"{', '.join((o.get('correction') or {}).get('drapeaux', []))}) : entité gardée "
                                        f"telle que la base")
            rv3 = R3.get(ident)
            rv2 = R2.get(ident)
            if rv3 and rv3["portee"] == "conforme" and rv3["verdict"] == "incertain":
                nat = NATURES_CONFORME_V3.get(ident, "conforme_non_verifiable")
                self.J.non_resolu(ident, fam, nat, origine="incertain", xy=xy, regles=["RES-NRE-003", "RES-NRE-001"],
                                  revue=_txt_revue(rv3, RV.REVUE_V3_ID), classe=o.get("type"),
                                  proposition=({k: rv3[k] for k in ("orientation_ambigue", "p_probable_local") if rv3.get(k)}
                                               or None),
                                  motif=f"« conforme » non vérifiable (revue v3 n° {rv3['n']}) : {rv3['motif'][:220]}")
            elif not rv3 and rv2 and rv2["portee"] == "conforme" and rv2["verdict"] == "incertain":
                self.J.non_resolu(ident, fam, "conforme_non_verifiable", origine="incertain", xy=xy, regles=["RES-NRE-001"],
                                  revue=_txt_revue(rv2), classe=o.get("type"), motif="« conforme » non vérifiable sur image")
            elif rv3 and rv3["portee"] == "conforme" and rv3["verdict"] == "juste":
                self.J.confirmer(ident, fam, "conforme_confirme", xy=xy, classe=o.get("type"), regles=["RES-SRC-002"],
                                 revue=_txt_revue(rv3, RV.REVUE_V3_ID), motif=rv3["motif"][:200])
            if rv3 and rv3.get("reserve_surface"):
                self.J.non_resolu(ident, "surfaces", "anomalie_surface", origine="conflit", xy=_xy(f), regles=["RES-NRE-003"],
                                  revue=_txt_revue(rv3, RV.REVUE_V3_ID), classe=o.get("type"),
                                  motif=f"réserve de la revue v3 n° {rv3['n']} (R8) : {rv3['reserve_surface']} ; signalement "
                                        f"de surface pour le propriétaire de surfaces.py")
            if rv2 and rv2.get("reserve_type"):
                self.J.non_resolu(ident, fam, "type", origine="incertain", xy=xy, regles=["RES-NRE-001"], revue=_txt_revue(rv2),
                                  classe=o.get("type"), motif=f"type à vérifier : {rv2['reserve_type']}")
            if rv3 and rv3.get("decision_relue") == "reste_en_A" and rv3["verdict"] == "juste":
                self.J.confirmer(ident, fam, "position_source_confirmee", xy=xy, classe=o.get("type"),
                                 regles=["RES-POS-003", "RES-SRC-002"], revue=_txt_revue(rv3, RV.REVUE_V3_ID),
                                 motif="la cohérence v3 garde la position de la base, confirmée sur photos par la revue v3")
        # observations de la revue v3 sans décision (R4)
        for ob in RV.OBSERVATIONS_V3:
            ident = ob["objet"]
            if ident not in self.obj:
                continue
            fam, f = self.obj[ident]
            self.J.non_resolu(ident, fam, ob["nature"], origine="incertain", xy=_xy(f), regles=["RES-NRE-003"],
                              classe=f["properties"].get("type"), proposition={"p_probable_local": ob["p_probable_local"]},
                              revue=f"{RV.REVUE_V3_ID} (problèmes systémiques) : {ob['motif']}", motif=ob["motif"])
        # RES-NRE-002 : présence 2026 non testée près des photos 2026 calées (Q4)
        for ident in sorted(self.obj):
            fam, f = self.obj[ident]
            p = f["properties"]
            if ident in self.non_instancies or p.get("instancier") is False or f["geometry"]["type"] != "Point":
                continue
            xy = _xy(f)
            pres = (self.O.get(ident) or {}).get("presence_2026") or {}
            dec_pres = pres.get("decision")
            if dec_pres == "non_visible":
                prev = pres.get("revue") or {}
                self.J.non_resolu(ident, fam, "presence_2026_non_visible", origine="incertain", xy=xy, regles=["RES-NRE-002"],
                                  observations=sorted(prev.get("photos") or []), classe=p.get("type"),
                                  motif=f"revue de présence Q4 : {str(prev.get('note') or 'non visible')[:200]}")
                continue
            if dec_pres in ("present", "absent") or ident in self.traites_existence:
                continue
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
                                    " : aucune preuve stricte après travaux ni revue de présence ; test sur vignette à faire")
        for ident in sorted(self.fcorr):
            q = self.fcorr[ident]
            if ident not in self.obj:
                continue
            fam, f = self.obj[ident]
            if ident in self.deplaces:
                continue                      # position décidée par une mesure revue (la fusion y est comparée dans le journal)
            xy = _xy(f)
            motif = f"correction fusion {q['decision']} de {q['d_m']} m ({', '.join(q.get('methodes') or [])})"
            if q["decision"] == "appliquer":
                oc = self.O.get(ident, {})
                rej = [m.get("motif_rejet") or m.get("motif_indice") for m in (oc.get("preuve") or {}).get("mesures_candidates", [])
                       if m.get("motif_rejet") or m.get("motif_indice")]
                rv = self._revue(ident)
                motif += " non appliquée : " + ("; ".join(rej) if rej else "sans corroboration")
                if rv:
                    motif += f" ; {rv.split(' — ')[0]}"
            for dsc in self.desaccords.get(ident, []):
                if dsc["nature"] == "hypothese_fusion_confirmee_q1":
                    motif += f" ; cohérence v3 : hypothèse confirmée par Q1 ({', '.join(dsc['coherence'].get('votes_X') or [])}), " \
                             f"non relue par une revue adverse (> 0,30 m)"
            self.J.non_resolu(ident, fam, "position_fusion", origine="conflit" if q["decision"] == "appliquer" else "incertain",
                              xy=xy, regles=["RES-POS-002"] + q.get("regles", []), observations=q.get("obs", []),
                              proposition={"d_m": q["d_m"], "sigma_m": q["sigma_m"], "p_fusion_local": q.get("p_fusion_local")},
                              classe=q.get("type"), revue=self._revue(ident),
                              motif=motif + "; " + "; ".join(q.get("raisons", []))[:300])
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
