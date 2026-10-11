"""Évaluation des règles d'implantation et résolution des positions (solveur de cohérence).

Pour chaque objet (groupe rigide) : contexte au point (zone selon precedence_zones, bordure de
référence et (s, t), voies et sens, largeur libre), évaluation des règles de
assets/specs/regles_implantation.json (surfaces, reculs, relations, orientation, z, collisions),
politique de dureté (critique toujours ; majeur si σ ≥ 0,5 m ; « verifier » contraignant pour un objet
a priori), puis recherche déterministe du candidat le plus proche (normale à la bordure en s0, puis
grille), coût J = (Δt/σ)² + 4 (Δs/σ)² + termes mous, arbitrage (anomalie de surface, photo, a priori,
non-instanciation) et orientation recalculée quand l'azimut est grossier ou non mesuré.

Les classes de surface au voisinage immédiat d'une bordure (|t| < 1 m) sont arbitrées par la bordure
(levé GAM, σ 0,05 m) : côté haut = classe du côté haut, côté chaussée = classe du côté bas — seulement si
l'orientation de la bordure est forte (MNT, OpenDRIVE, GQ-ORI-001 ; P6).

v2 (revue adverse v1) : dureté selon la nature de la règle et le statut de l'objet (P7,
coherence_politique) ; exception GEN-02 des supports de feux piétons et palier majeur (P8) ; candidats
exclus à moins de r1 + r2 + 0,10 m d'un objet de preuve au moins aussi bonne (P5) ; budget de
déplacement compté depuis la position source brute (P9) ; les reculs d'un objet existant sont des coûts
mous qui orientent le candidat d'un déplacement imposé par une règle physique, jamais un motif de
déplacement.
"""
import math

import numpy as np

import coherence_politique as POL
from coherence_carte import PIETONNES, azimut, ecart_angle
from coherence_objets import anterieure_travaux, azimut_grossier
from commun import normale_gauche

DERIVEES = {"passage_pietons", "traversee_cyclable", "bev", "abaisse_traversee", "palier_abaisse", "ilot_peint",
            "voie_bus", "bande_cyclable", "stationnement_chaussee", "cheminement_pmr", "bande_fonctionnelle",
            "triangle_visibilite"}
EVALUEES = {"GEN-01", "GEN-02", "GEN-03", "GEN-04", "GEN-06", "GEN-08", "GEN-09", "PMR-01", "SIG-01", "SIG-02",
            "SIG-04", "SIG-05", "SIG-06", "SIG-07", "SIG-09", "SIG-10", "SIG-11", "SIG-12", "FEU-01", "FEU-02",
            "FEU-03", "FEU-04", "FEU-05", "FEU-06", "FEU-07", "FEU-09", "ECL-01", "ECL-02", "ECL-03", "ECL-05",
            "POT-01", "POT-03", "TC-01", "TC-02", "MOB-01", "MOB-03", "BAR-03", "VEG-01", "VEG-02", "VEG-03",
            "VEG-06", "RES-01", "RES-02", "RES-03"}
# usagers visés par code de panneau (SIG-04) : types de voies
USAGERS = {"C113": ("biking",), "C114": ("biking",), "M4d1": ("biking",)}
BRANCHES = {  # branche (mobilier) -> (route, signe de voie entrante, ligne d'effet v2)
    "Verdun NE": (3, -1, "verdun_ne"), "Verdun SW": (1, -1, "verdun_sw"),
    "Revirée": (5, 1, "reviree"), "Vercors": (6, 1, "vercors")}
CIRC_BASE = {"chaussee", "piste_cyclable", "parking", "acces_riverain"}
# règles dont la liste d'admission ne vaut que pour le cas visé (POT-03 : potelet sur piste)
AUTORISEES_CONDITIONNELLES = {"POT-03"}
# surfaces de circulation au sens strict (un objet côté bas d'une bordure sur l'une d'elles doit passer derrière)
VOIES_CIRCULEES = {"chaussee", "voie_bus", "bande_cyclable", "piste_cyclable", "passage_pietons", "traversee_cyclable"}
ZONES_LONGITUDINALES = {"abaisse_traversee", "palier_abaisse", "bev", "passage_pietons", "traversee_cyclable"}


def _dans(v, lst):
    return v in lst


class Solveur:
    def __init__(self, carte, regles, objets, clotures, tetes, hyps):
        self.c = carte
        self.R = regles
        self.res = regles["resolution"]
        self.par = self.res["parametres"]
        self.voc = regles["vocabulaire"]
        self.regles = {g["id"]: g for g in regles["regles"]}
        self.objets = objets
        self.par_id = {o["id"]: o for o in objets}
        self.clotures = clotures
        self.tetes = tetes
        self.tetes_de = {}
        for t in tetes:
            self.tetes_de.setdefault(t["parent"], []).append(t)
        self.hyps = hyps
        self.actifs = [o for o in objets if not o["statut"].startswith("absent")]
        self.P = np.array([o["p0"] for o in self.actifs])
        self.Rr = np.array([o["rayon"] for o in self.actifs])
        self.Grp = np.array([o["groupe"] for o in self.actifs], dtype=object)
        self.Ids = np.array([o["id"] for o in self.actifs], dtype=object)
        self.Sig = np.array([o["sigma"] for o in self.actifs], float)
        self.nez = self._nez_ilots()
        self.lignes_effet = {l["branche"]: l for l in carte.lignes_effet}
        self._ctx_cache = {}

    # ------------------------------------------------------------------ outils géométriques
    def _nez_ilots(self):
        """Nez d'îlots : extrémités des îlots bordés (îlots v2, surfaces ilot / terre-plein végétal)."""
        from commun import lire_geojson, DONNEES, repere
        out = []
        for il in self.c.ilots_v2:
            if il["nez"] is not None:
                out.append(dict(id=il["id"], p=il["nez"], src="ilots_v2"))
            out += [dict(id=il["id"], p=q, src="extremite") for q in _extremites(il["poly"][0])]
        self.ilots_v1 = []
        for f in lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"):
            p = f["properties"]
            if p["classe"] not in ("ilot", "terre_plein_vegetal") or p["surface_m2"] > 600:
                continue
            g = f["geometry"]
            r = repere(np.asarray(g["coordinates"][0])[:, :2])
            self.ilots_v1.append(r)
            out += [dict(id=p["id"], p=q, src="extremite_v1") for q in _extremites(r)]
        return out

    def zones(self, P):
        """Zone retenue (precedence + arbitrage par la bordure), classe de base, faiblesse, source."""
        P = np.atleast_2d(P)
        z = self.c.zone(P)
        base = self.c.classe(P)
        faible, defaut, src = self.c.faiblesse(P)
        arb = np.zeros(len(P), bool)
        cand = np.array([zz not in DERIVEES for zz in z])
        if cand.any():
            idx = np.nonzero(cand)[0]
            rr = self.c.ref_bordure(P[idx], rayon=1.0, circulee=False)
            for i, r in zip(idx, rr):
                if r is None or not self.c.bordures[r["k"]].get("orientation_forte"):
                    continue
                if r["t"] > 0 and z[i] in CIRC_BASE and r["classe_haut"] not in CIRC_BASE and r["classe_haut"]:
                    z[i], arb[i] = r["classe_haut"], True
                elif r["t"] < 0 and z[i] not in CIRC_BASE and r["classe_bas"] in CIRC_BASE:
                    z[i], arb[i] = r["classe_bas"], True
        return z, base, faible, defaut, src, arb

    def emprise(self, o, p, az=None):
        """Points de l'emprise au sol (centre + contour) à la position p."""
        p = np.asarray(p, float)
        dims = o.get("dims")
        if dims and o["type"] != "cloture":
            L, W = dims
            a = math.radians(az if az is not None else (o.get("azimut0") or 0.0))
            f = np.array([math.sin(a), math.cos(a)])          # direction de la face
            u = np.array([f[1], -f[0]])                        # axe long (perpendiculaire à la face)
            pts = [p]
            for i in (-1, 0, 1):
                for j in (-1, 0, 1):
                    if i or j:
                        pts.append(p + u * i * L / 2 + f * j * W / 2)
            return np.array(pts)
        r = max(o["rayon"], 0.03)
        ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        return np.vstack([p, p + r * np.c_[np.cos(ang), np.sin(ang)]])

    # ------------------------------------------------------------------ applicabilité
    def applicables(self, o, zone):
        out = []
        for g in self.R["regles"]:
            if "*" not in g["objet_types"] and o["type"] not in g["objet_types"]:
                continue
            if not self._filtre(g.get("filtre"), o, zone):
                continue
            if g["id"] in ("FEU-01", "FEU-02"):
                cote = self.cote_support(o)
                if cote is None or (g["id"] == "FEU-01") != (cote == "droit"):
                    continue
            out.append(g)
        return out

    def cote_support(self, o):
        """'droit' | 'gauche' pour un support portant un R11v (champ role du mobilier), sinon None."""
        if o["type"] != "support_feux" or not any(t["type_tete"] == "R11v" for t in self.tetes_de.get(o["id"], [])):
            return None
        role = str((o.get("props") or {}).get("role") or "")
        return "gauche" if ("gauche" in role or "TPC" in role or ("îlot" in role and "droit" not in role)) else "droit"

    def _filtre(self, f, o, zone):
        props = dict(o.get("props") or {})
        props.setdefault("code", o.get("code"))
        props.setdefault("source", o.get("source"))
        for cle, vals in (f or {}).items():
            if cle == "zone":
                if zone not in vals:
                    return False
            elif cle == "type_tete":
                tt = [t["type_tete"] for t in self.tetes_de.get(o["id"], [])] + ([o["type_tete"]] if o.get("type_tete") else [])
                if not any(t in vals for t in tt):
                    return False
            elif cle.endswith("_exclus"):
                if props.get(cle[:-7]) in vals:
                    return False
            elif cle.endswith("_contient"):
                if not any(v in str(props.get(cle[:-9]) or "") for v in vals):
                    return False
            elif props.get(cle) not in vals:
                return False
        return True

    def _excuses(self, g, o):
        ex = set()
        for e in g.get("exceptions", []):
            if "*" in e.get("objet_types", []) or o["type"] in e.get("objet_types", []):
                if self._filtre(e.get("filtre"), o, None if "zone" in (e.get("filtre") or {}) else ""):
                    ex |= set(e.get("zones_autorisees", []))
        return ex

    def dure(self, o, g, v=None):
        """Politique de résolution (P7) : la violation v de la règle g est-elle une contrainte dure pour o ?"""
        v = v or dict(nature="surface", valeur=list(g.get("surfaces_interdites") or []))
        d, _ = POL.durete(o, g, v, self.par["seuil_sigma_normatif_m"])
        return d

    # ------------------------------------------------------------------ contexte
    def contexte(self, o, p=None):
        p = np.asarray(o["p0"] if p is None else p, float)
        z, base, faible, defaut, src, arb = self.zones(p[None])
        ref = self.c.ref_bordure(p[None], rayon=self.par["rayon_bordure_reference_m"], circulee=True)[0]
        tout = self.c.ref_bordure(p[None], rayon=30.0, circulee=False)[0]
        ctx = dict(zone=str(z[0]), base=str(base[0]), faible=bool(faible[0]), zone_defaut=bool(defaut[0]),
                   source_classe=str(src[0]), arbitree_bordure=bool(arb[0]), ref=ref,
                   d_bordure=None if tout is None else round(tout["d"], 3),
                   z_sol=float(self.c.z_sol(p[None])[0]))
        return ctx

    # ------------------------------------------------------------------ évaluation
    def evaluer(self, o, p=None, az=None, dures_seulement=False):
        """Violations de l'objet à la position p (défaut p0) et à l'azimut az (défaut azimut0)."""
        p = np.asarray(o["p0"] if p is None else p, float)
        az = o.get("azimut0") if az is None else az
        ctx = self.contexte(o, p)
        ctx["_p"] = p
        V = []
        regs = self.applicables(o, ctx["zone"])
        emp = self.emprise(o, p, az)
        ze, _, _, zdef, _, _ = self.zones(emp)
        der = np.isin(ze, sorted(DERIVEES))
        ctx["_defaut_emprise"] = bool(np.all(zdef[der])) if der.any() else False
        if o["type"] == "balise_J11" and ctx["zone"] in CIRC_BASE:
            f = self.fuseau(p)
            if f:
                ctx["zone"], ctx["fuseau"] = "ilot_peint", f
                ze = np.where(np.isin(ze, list(CIRC_BASE)), "ilot_peint", ze)
                regs = self.applicables(o, ctx["zone"])
        for g in regs:
            gid = g["id"]
            if gid not in EVALUEES:
                continue
            V += self._regle(g, o, p, az, ctx, emp, ze)
        fort = o["sigma"] <= self.par["seuil_sigma_preuve_forte_m"]
        st = POL.statut_objet(o)
        for v in V:
            g = self.regles[v["regle"]]
            v.setdefault("gravite", g["gravite"])
            v.setdefault("action", g["action"])
            v["nature_regle"] = POL.nature_regle(g)
            v["physique"] = POL.violation_physique(v)
            d, motif = POL.durete(o, g, v, self.par["seuil_sigma_normatif_m"], st)
            v["dure"], v["motif_durete"] = bool(d), motif
            if v["dure"] and v.get("parametre_a_priori") and o["sigma"] < self.par["seuil_sigma_normatif_m"]:
                v["dure"], v["note"] = False, "borne a priori de la règle : non opposable à une position bien prouvée"
            if v["nature"] == "surface" and v.get("zones_a_priori") and fort and not v["physique"]:
                v["dure"], v["note"] = False, "zone dérivée à géométrie a priori : l'objet prouvé prime (anomalie de surface)"
        if dures_seulement:
            V = [v for v in V if v["dure"]]
        ctx["statut_objet"] = st
        return V, ctx, [g["id"] for g in regs]

    def _regle(self, g, o, p, az, ctx, emp, ze):
        gid = g["id"]
        V = []
        # ---- surfaces
        if g["surfaces_interdites"] or g["surfaces_autorisees"]:
            V += self._surface(g, o, ctx, ze)
        ref = ctx["ref"]
        # ---- reculs (derriere_bordure sur la bordure de chaussée)
        for rel in g.get("relations", []):
            if rel["rel"] == "derriere_bordure" and rel["cible"] in ("bordure_chaussee", "bordure_quai") and ref is not None:
                rmin = rel.get("recul_min_m")
                if gid == "VEG-02":
                    rmin = g["parametres"]["recul_tronc_min_m"][o.get("developpement", "moyen")]
                t_bord = ref["t"] - self._demi_profondeur(o, ref, az)
                cote_bas_admis = ref["t"] < 0 and ctx["zone"] not in VOIES_CIRCULEES
                if rmin is not None and t_bord < rmin - 1e-6 and -1.0 <= ref["t"] < 6.0 and not cote_bas_admis:
                    V.append(dict(regle=gid, nature="recul", valeur=round(t_bord, 3), attendu=f">= {rmin}",
                                  residu=round(rmin - t_bord, 3), bordure=ref["id"],
                                  message=f"nu à {t_bord:.2f} m de l'arête avant {ref['id']} (minimum {rmin} m)"))
        # ---- règles particulières
        fn = getattr(self, "_r_" + gid.replace("-", "_"), None)
        if fn is not None:
            V += fn(g, o, p, az, ctx) or []
        return V

    def _demi_profondeur(self, o, ref, az):
        if o.get("dims") and az is not None:
            L, W = o["dims"]
            a = math.radians(az)
            f = np.array([math.sin(a), math.cos(a)])
            n = normale_gauche(ref["tg"][None])[0]
            u = np.array([f[1], -f[0]])
            return abs(f @ n) * W / 2 + abs(u @ n) * L / 2
        return o["rayon"]

    def _surface(self, g, o, ctx, ze):
        ex = self._excuses(g, o)
        interd = set(g["surfaces_interdites"])
        autor = set(g["surfaces_autorisees"]) if g["id"] not in AUTORISEES_CONDITIONNELLES else set()
        zc = ze[0]
        out = []
        touche = sorted({z for z in ze if z in interd and z not in ex})
        if zc in ex:
            touche = []
        if g["id"] in ("GEN-02", "FEU-07") and touche and POL.porte_tete_pietonne(o, self.tetes_de):
            # P8 (CEREMA fiche BEV 03) : support de feux piétons / bouton d'appel à la limite arrière de la BEV,
            # dans le prolongement du passage : centre seul testé, palier non opposé dans le prolongement
            touche = [z for z in touche if z == zc]
            if "palier_abaisse" in touche and self.dans_prolongement_passage(ctx.get("_p")):
                touche = [z for z in touche if z != "palier_abaisse"]
            ctx["exception_P8"] = True
        if touche:
            a_priori = all(z in DERIVEES for z in touche) and bool(ctx.get("_defaut_emprise"))
            v = dict(regle=g["id"], nature="surface", valeur=list(touche), attendu="hors " + ", ".join(sorted(interd)),
                     zones_a_priori=a_priori, message=f"emprise sur {', '.join(touche)}")
            if g["id"] == "GEN-02" and set(touche) <= {"palier_abaisse"}:
                v["gravite"] = v["gravite_effective"] = "majeur"     # P8 : palier « si la largeur le permet »
                v["message"] += " (palier : majeur, ARR2007 « si la largeur du trottoir le permet »)"
            out.append(v)
        elif autor:
            dans = self.voc["classes_surface"].get(zc, {}).get("dans", [])
            ok = zc in autor or zc in ex or (zc in DERIVEES and ctx["base"] in autor and ctx["base"] in dans) \
                or (zc in DERIVEES and any(d in autor for d in dans) and zc not in interd)
            if not ok and zc:
                out.append(dict(regle=g["id"], nature="surface", valeur=[zc], attendu="dans " + ", ".join(sorted(autor)),
                                message=f"sur {zc} (admis : {', '.join(sorted(autor))})"))
        return out

    # ---- règles générales
    def _r_GEN_04(self, g, o, p, az, ctx):
        if o.get("z0") is None or "dalle" in str(o.get("z_source") or ""):
            return []
        dz = float(o["z0"]) - ctx["z_sol"]
        tol = g["parametres"]["tolerance_z_m"]
        if abs(dz) > tol and np.allclose(p, o["p0"]):
            return [dict(regle="GEN-04", nature="z", valeur=round(dz, 3), attendu=f"|dz| <= {tol}",
                         residu=round(abs(dz), 3), message=f"base à {dz:+.2f} m du sol 2026 (MNT)")]
        return []

    def _r_GEN_08(self, g, o, p, az, ctx):
        ref = ctx["ref"]
        if ref is None or ref["t"] < 0 or ref["t"] > g["parametres"]["profondeur_bande_m"] + o["rayon"]:
            return []
        out = []
        for pp in self.c.passages:
            m = (pp["a"] + pp["b"]) / 2
            if np.hypot(*(p - m)) > 14.0:
                continue
            # amont le long de la bordure : distance au bord du passage projetée sur la tangente
            d_long = abs((p - m) @ ref["tg"]) - pp["demi_largeur"]
            lo, hi = g["parametres"]["longueur_amont_m"]
            if 0.0 <= d_long <= hi:
                out.append(dict(regle="GEN-08", nature="relation", valeur=round(d_long, 2), attendu=f"hors {lo}-{hi} m du passage {pp['id']}",
                                message=f"objet opaque dans le triangle de visibilité du passage {pp['id']} ({d_long:.1f} m)"))
                break
        return out

    def _r_PMR_01(self, g, o, p, az, ctx):
        r = self._pmr(o, p, ctx)
        if r is None:
            return []
        o.setdefault("_pmr", r)
        if r["avec"] < r["seuil"] and r["sans"] >= r["seuil"]:
            return [dict(regle="PMR-01", nature="largeur", valeur=r["avec"], attendu=f">= {r['seuil']}",
                         residu=round(r["seuil"] - r["avec"], 2),
                         message=f"cheminement réduit à {r['avec']:.2f} m (sans l'objet {r['sans']:.2f} m, limite {r['fin']})")]
        if r["sans"] < r["seuil"]:
            return [dict(regle="PMR-01", nature="info", valeur=r["sans"], attendu=f">= {r['seuil']}",
                         message=f"trottoir étroit : {r['sans']:.2f} m libres sans l'objet (objet non en cause)")]
        return []

    def _pmr(self, o, p, ctx, exclure=()):
        ref = ctx["ref"]
        if ref is None or ctx["zone"] not in PIETONNES:
            return None
        t, m, fin = self.c.coupe_pietonne(ref["k"], ref["s"])
        if not m.any():
            return None
        q0 = self.c.point_bordure(ref["k"], [ref["s"]], [0.0])[0]
        n = normale_gauche(ref["tg"][None])[0]
        obs = []
        d = self.P - q0
        lat = np.abs(d @ ref["tg"])
        tt = d @ n
        proche = (lat <= self.Rr + 0.25) & (tt > -0.5) & (tt < t[-1] + 0.5)
        for i in np.nonzero(proche)[0]:
            if self.Ids[i] == o["id"] or self.Grp[i] == o["groupe"] or self.Ids[i] in exclure:
                continue
            obs.append((float(tt[i]), float(self.Rr[i])))
        t_o = float((p - q0) @ n)
        tm = t[m]
        r_o = self._demi_profondeur(o, ref, o.get("azimut0"))
        if t_o + r_o < tm.min() or t_o - r_o > tm.max():
            return None                 # l'objet n'est pas dans le cheminement mesuré derrière cette bordure
        sans = self.c.largeur_libre(t, m, obs)
        avec = self.c.largeur_libre(t, m, obs + [(t_o, self._demi_profondeur(o, ref, o.get("azimut0")))])
        dur = fin in ("batiment", "cloture")
        seuil = 1.40 if dur else 1.20
        return dict(sans=sans, avec=avec, seuil=seuil, fin=fin, largeur_trottoir=round(float(m.sum()) * 0.05, 2),
                    t_objet=round(t_o, 2))

    # ---- signalisation
    def _r_SIG_04(self, g, o, p, az, ctx):
        if o["type"] == "balise_J11":
            return []
        cible = self.orientation_cible(o, p, ctx)
        if cible is None:
            return []
        o["_orientation"] = cible
        if az is None:
            return [dict(regle=g["id"], nature="orientation", valeur=None, attendu=round(cible["az"], 1),
                         message="azimut absent : orienté par la règle")]
        tol = cible.get("tolerance", g["parametres"].get("tolerance_azimut_deg", 15.0))
        e = ecart_angle(az, cible["az"])
        if e > tol:
            return [dict(regle=g["id"], nature="orientation", valeur=round(float(az), 1), attendu=round(cible["az"], 1),
                         residu=round(e, 1), message=f"face à {az:.0f}°, attendu {cible['az']:.0f}° ({cible['motif']})")]
        return []

    _r_SIG_12 = _r_SIG_04

    def _r_SIG_05(self, g, o, p, az, ctx):
        cible = o.get("_orientation") or self.orientation_cible(o, p, ctx)
        if not cible or cible.get("cote") is None or cible["cote"] == "droit":
            return []
        return [dict(regle="SIG-05", nature="relation", valeur=cible["cote"], attendu="droit",
                     message=f"panneau à {cible['cote']} des usagers visés ({cible['motif']})")]

    def _r_SIG_06(self, g, o, p, az, ctx):
        return self._r_SIG_07(g, o, p, az, ctx, cible="ligne")

    def _r_SIG_07(self, g, o, p, az, ctx, cible="feux"):
        sup = [x for x in self.actifs if x["type"] == "support_feux" and np.hypot(*(x["p0"] - p)) < 25]
        if cible == "feux" and not sup:
            return []
        if cible == "feux":
            d = min(float(np.hypot(*(x["p0"] - p))) for x in sup)
            tol = g["parametres"]["tolerance_plan_m"]
            if d > tol + 6.0:
                return [dict(regle=g["id"], nature="relation", valeur=round(d, 1), attendu=f"plan des feux (±{tol} m)",
                             message=f"AB à {d:.1f} m du support de feux le plus proche")]
        return []

    def _r_SIG_10(self, g, o, p, az, ctx):
        dmax = g["parametres"]["distance_nez_max_m"]
        if not self.nez:
            return []
        d = min(float(np.hypot(*(n["p"] - p))) for n in self.nez)
        if d > dmax:
            return [dict(regle=g["id"], nature="relation", valeur=round(d, 2), attendu=f"<= {dmax} m d'un nez d'îlot",
                         residu=round(d - dmax, 2), parametre_a_priori=True,
                         message=f"à {d:.1f} m du nez d'îlot le plus proche")]
        return []

    _r_SIG_11 = _r_SIG_10

    def _r_SIG_09(self, g, o, p, az, ctx):
        """J11 : dans un fuseau peint (entre deux lignes continues à moins de 2,5 m de part et d'autre)."""
        if ctx["zone"] == "ilot_peint":
            return []
        f = self.fuseau(p)
        if f:
            ctx["zone"] = "ilot_peint"
            return []
        return []

    def fuseau(self, p):
        """Le point est-il entre deux lignes continues proches et parallèles (fuseau peint) ?"""
        from commun import distance_segments
        cotes = []
        for lid, P in self.c.lignes_continues:
            if np.min(np.hypot(*(P - p).T)) > 6.0 and len(P) < 3:
                continue
            d, j, pr = distance_segments(p[None], P[:-1], P[1:])
            if d[0] <= 2.5:
                seg = P[j[0] + 1] - P[j[0]]
                v = p - pr[0]
                cotes.append((lid, np.sign(seg[0] * v[1] - seg[1] * v[0]), seg / max(np.hypot(*seg), 1e-9), d[0]))
        for i in range(len(cotes)):
            for j in range(i + 1, len(cotes)):
                a, b = cotes[i], cotes[j]
                if a[0] != b[0] and abs(a[2] @ b[2]) > 0.9:
                    # côtés opposés (tenir compte du sens de parcours de chaque ligne)
                    sa = a[1]
                    sb = b[1] * np.sign(a[2] @ b[2])
                    if sa != sb:
                        return dict(lignes=[a[0], b[0]], d=[round(float(a[3]), 2), round(float(b[3]), 2)])
        return None

    # ---- orientation : cible par règle
    def _ilot_sous(self, p, rayon=1.5):
        """Anneau de l'îlot (v2 ou v1) qui porte le point p (à 1,5 m près), ou None."""
        from commun import dans_polygone, distance_segments, aretes
        best = None
        for il in self.c.ilots_v2:
            r = il["poly"][0]
            d = 0.0 if dans_polygone(p[None], [r])[0] else float(distance_segments(p[None], *aretes([r]))[0][0])
            if d <= rayon and (best is None or d < best[0]):
                best = (d, r)
        for r in self.ilots_v1:
            d = 0.0 if dans_polygone(p[None], [r])[0] else float(distance_segments(p[None], *aretes([r]))[0][0])
            if d <= rayon and (best is None or d < best[0]):
                best = (d, r)
        return None if best is None else best[1]

    def orientation_cible(self, o, p, ctx, az0="defaut"):
        """Azimut de face attendu (deg) par la règle de la famille de l'objet, ou None."""
        t = o["type"]
        code = (o.get("code") or "")
        az0 = o.get("azimut0") if az0 == "defaut" else az0
        if t in ("lampadaire", "abri_bus", "poteau_incendie"):
            # vers la chaussée principale : point le plus proche des voies motorisées (ECL-02, TC-01, RES-03)
            from commun import aretes, distance_segments
            vs = [v for v in self.c.voies(p, types=("driving", "bus"), rayon=25.0) if not v["dedans"]]
            if not vs or vs[0]["d"] > 10.0:
                return None             # voie éclairée non modélisée (parking, allée) : pas de cible
            l = self.c.lanes[vs[0]["i"]]
            A, B = aretes(l["poly"])
            _, _, pr = distance_segments(p[None], A, B)
            az = azimut(pr[0] - p)
            props = o.get("props") or {}
            double = t == "lampadaire" and (props.get("nb_crosses") or 0) >= 2
            tol = {"lampadaire": 10.0 if "crosse" in str(props.get("sous_type") or "") else 30.0,
                   "abri_bus": 10.0, "poteau_incendie": 30.0}[t]
            return dict(az=az, motif=f"vers la chaussée (voie {vs[0]['route']}/{vs[0]['voie']} à {vs[0]['d']:.1f} m)",
                        tolerance=tol, modulo_180=double, cote=None)
        if t != "panneau":
            return None
        ilot = code.startswith("B21") or code == "J5"
        types = USAGERS.get(code, ("driving", "bus"))
        cands = []
        for v in self.c.voies(p, types=types, rayon=20.0):
            if v["dedans"]:
                continue
            l = self.c.lanes[v["i"]]
            h = math.radians(v["cap_deg"])
            hv = np.array([math.sin(h), math.cos(h)])
            # la voie approche-t-elle du panneau ? (points de la voie 3 à 40 m en amont, à moins de 12 m)
            ring = _densifier_anneau(l["poly"][0], 1.0)
            w = p - ring
            u = w @ hv
            lat = np.abs(w[:, 0] * hv[1] - w[:, 1] * hv[0])
            if not np.any((u >= 3.0) & (u <= 40.0) & (lat <= 12.0)):
                continue
            if v["d"] > 10.0:
                continue
            if ilot:
                il = self._ilot_sous(p)
                if il is not None and float(np.mean((il - p) @ hv)) <= 0.0:
                    continue            # l'îlot doit s'étendre en aval du panneau pour ces usagers
            from commun import aretes, distance_segments
            A, B = aretes(l["poly"])
            _, _, pr = distance_segments(p[None], A, B)
            ww = p - pr[0]
            cote = "droit" if (hv[0] * ww[1] - hv[1] * ww[0]) < 0 else "gauche"
            rot = 4.0 if cote == "droit" else -4.0
            cible = (v["cap_deg"] + 180.0 - rot) % 360.0
            cands.append(dict(az=cible, cote=cote, d=v["d"], voie=f"{v['route']}/{v['voie']}", cap=v["cap_deg"],
                              motif=f"usagers de la voie {v['route']}/{v['voie']} ({v['type']}, cap {v['cap_deg']:.0f}°, "
                                    f"panneau à {cote})"))
        if not cands:
            return None
        pref = "gauche" if ilot else "droit"
        tol = 30.0 if code.startswith("D21") else (20.0 if ilot else 15.0)
        regle = sorted(cands, key=lambda c: (c["cote"] != pref, round(c["d"], 1), c["voie"]))[0]
        if az0 is not None:
            proche = sorted(cands, key=lambda c: (ecart_angle(az0, c["az"]), c["d"]))[0]
            lim = 45.0 if azimut_grossier(az0) else tol
            if code.startswith("D21") or ecart_angle(az0, proche["az"]) <= lim:
                regle = proche
        out = dict(regle)
        out["tolerance"] = tol
        return out

    # ---- feux
    def _approche(self, o):
        br = (o.get("props") or {}).get("branche")
        if br not in BRANCHES:
            return None
        route, signe, nom = BRANCHES[br]
        le = self.lignes_effet.get(nom)
        if le is None:
            return None
        m = le["P"].mean(axis=0)
        tg = self.c._cap_route(route, m)
        if tg is None:
            return None
        h = tg if signe < 0 else -tg
        return dict(ligne=le["id"], milieu=m, h=h, cap=azimut(h), route=route)

    def _r_FEU_01(self, g, o, p, az, ctx, cote_attendu="droit"):
        if self.cote_support(o) != cote_attendu:
            return []
        ap = self._approche(o)
        if ap is None:
            return []
        v = p - ap["milieu"]
        ds = float(v @ ap["h"])
        cote = "droit" if (ap["h"][0] * v[1] - ap["h"][1] * v[0]) < 0 else "gauche"
        lo, hi = g["parametres"]["ds_ligne_effet_m"]
        tol = g["parametres"].get("tolerance_amont_m", 0.5)
        out = []
        o.setdefault("_feu", {}).update(ds_ligne_effet=round(ds, 2), ligne=ap["ligne"], cote=cote)
        if ds < lo - tol or ds > hi:
            out.append(dict(regle=g["id"], nature="relation", valeur=round(ds, 2), attendu=f"ds dans [{lo - tol}, {hi}] m",
                            residu=round(max(lo - tol - ds, ds - hi), 2), parametre_a_priori=bool(ds > hi),
                            message=f"support à ds = {ds:+.2f} m de la ligne d'effet {ap['ligne']}"))
        if cote != cote_attendu:
            out.append(dict(regle=g["id"], nature="relation", valeur=cote, attendu=cote_attendu,
                            message=f"support à {cote} du couloir géré (attendu : {cote_attendu})"))
        return out

    def _r_FEU_02(self, g, o, p, az, ctx):
        return self._r_FEU_01(g, o, p, az, ctx, cote_attendu="gauche")

    def _r_FEU_03(self, g, o, p, az, ctx):
        if o["type"] != "support_feux":
            return []
        out = []
        piet = ctx["zone"] in PIETONNES or ctx["zone"] in ("espace_vert", "terre_plein_vegetal")
        for t in self.tetes_de.get(o["id"], []):
            if t["type_tete"] not in ("R11v",):
                continue
            h = float(t["z"]) - ctx["z_sol"]
            bas = h - 0.475
            if piet and bas < g["parametres"]["gabarit_sous_tete_min_m"] - 0.05:
                out.append(dict(regle="FEU-03", nature="hauteur", valeur=round(bas, 2), attendu=">= 2.0",
                                message=f"{t['id']} : bas de la tête à {bas:.2f} m au-dessus du sol"))
        return out

    def _r_FEU_05(self, g, o, p, az, ctx):
        """Têtes R11v / répétiteurs du support : visée de la voie gérée (contrainte d'orientation)."""
        return []

    def _orient(self, gid, o, p, az, ctx):
        cible = self.orientation_cible(o, p, ctx)
        if cible is None:
            return []
        o["_orientation"] = cible
        if az is None:
            return [dict(regle=gid, nature="orientation", valeur=None, attendu=round(cible["az"], 1),
                         message="azimut absent : orienté par la règle")]
        e = ecart_angle(az, cible["az"])
        if cible.get("modulo_180"):
            e = min(e, 180.0 - e)
        if e > cible["tolerance"]:
            return [dict(regle=gid, nature="orientation", valeur=round(float(az), 1), attendu=round(cible["az"], 1),
                         residu=round(e, 1), message=f"face à {az:.0f}°, attendu {cible['az']:.0f}° ({cible['motif']})")]
        return []

    def _r_ECL_02(self, g, o, p, az, ctx):
        return self._orient("ECL-02", o, p, az, ctx)

    def _r_TC_01(self, g, o, p, az, ctx):
        return self._orient("TC-01", o, p, az, ctx)

    def _r_RES_03(self, g, o, p, az, ctx):
        return self._orient("RES-03", o, p, az, ctx)

    def _r_ECL_05(self, g, o, p, az, ctx):
        arbres = [x for x in self.actifs if x["type"] == "arbre"]
        if not arbres:
            return []
        d = np.hypot(*(np.array([a["p0"] for a in arbres]) - p).T)
        i = int(np.argmin(d))
        dmin = g["parametres"]["distance_arbre_sous_couronne_min_m"]
        if d[i] < dmin:
            return [dict(regle="ECL-05", nature="relation", valeur=round(float(d[i]), 2), attendu=f">= {dmin}",
                         message=f"à {d[i]:.2f} m de {arbres[i]['id']}")]
        return []

    def _r_VEG_03(self, g, o, p, az, ctx):
        if o["preuve_propre"] not in ("plan2025", "a_priori") and not o["statut"].startswith("planté"):
            return []
        dev = o.get("developpement", "moyen")
        dmin = g["parametres"]["distance_arbre_min_m"][dev]
        autres = [x for x in self.actifs if x["type"] == "arbre" and x["id"] != o["id"]]
        d = np.hypot(*(np.array([a["p0"] for a in autres]) - p).T)
        i = int(np.argmin(d))
        if d[i] < dmin:
            return [dict(regle="VEG-03", nature="relation", valeur=round(float(d[i]), 2), attendu=f">= {dmin}",
                         message=f"à {d[i]:.1f} m de {autres[i]['id']} (développement {dev})")]
        return []

    def _r_MOB_01(self, g, o, p, az, ctx):
        ref = ctx["ref"]
        if ref is None or ctx["zone"] not in ("trottoir", "quai_bus"):
            return []
        t_bord = ref["t"] - self._demi_profondeur(o, ref, az)
        r = self._pmr(o, p, ctx)
        adosse = False
        if r is not None:
            fin_t = r["largeur_trottoir"]
            adosse = (fin_t - (ref["t"] + self._demi_profondeur(o, ref, az))) <= g["parametres"]["adossement_max_m"]
        if t_bord < g["parametres"]["recul_bord_min_m"] and not adosse:
            return [dict(regle="MOB-01", nature="recul", valeur=round(t_bord, 2), attendu=">= 0.5 ou adossé",
                         residu=round(g["parametres"]["recul_bord_min_m"] - t_bord, 2),
                         message=f"hors bande fonctionnelle (nu à {t_bord:.2f} m de la bordure)")]
        return []

    def _r_VEG_06(self, g, o, p, az, ctx):
        return []

    # ------------------------------------------------------------------ collisions / doublons (GEN-06)
    def collisions(self):
        out = []
        n = len(self.actifs)
        D = np.hypot(*(self.P[:, None, :] - self.P[None, :, :]).transpose(2, 0, 1))
        g6 = self.regles["GEN-06"]["parametres"]
        for i in range(n):
            for j in range(i + 1, n):
                if D[i, j] > 3.0:
                    continue
                a, b = self.actifs[i], self.actifs[j]
                if a["groupe"] == b["groupe"]:
                    continue
                if a["type"] == "arbre" and b["type"] == "arbre":
                    jeu = 0.0
                else:
                    jeu = g6["jeu_entre_emprises_m"]
                meme = a["type"] == b["type"] and (a.get("code") == b.get("code"))
                az_ok = a.get("azimut0") is None or b.get("azimut0") is None or \
                    ecart_angle(a["azimut0"], b["azimut0"]) <= g6["seuil_doublon_azimut_deg"]
                if meme and D[i, j] < g6["seuil_doublon_m"] and az_ok and a["type"] != "arbre":
                    out.append(dict(nature="doublon", a=a["id"], b=b["id"], d=round(float(D[i, j]), 3)))
                elif D[i, j] < a["rayon"] + b["rayon"] + jeu:
                    out.append(dict(nature="collision", a=a["id"], b=b["id"], d=round(float(D[i, j]), 3),
                                    min=round(a["rayon"] + b["rayon"] + jeu, 3)))
        return out

    # ------------------------------------------------------------------ résolution (v2)
    def dans_prolongement_passage(self, p, marge=0.3):
        """Le point est-il dans la bande d'un passage piéton prolongé au-delà de ses extrémités (≤ 3 m) ?"""
        if p is None:
            return False
        p = np.asarray(p, float)
        for pp in self.c.passages:
            d = p - pp["a"]
            L = float(np.hypot(*(pp["b"] - pp["a"])))
            u, v = float(d @ pp["u"]), float(d @ pp["v"])
            if abs(v) <= pp["demi_largeur"] + marge and (-3.0 <= u <= 0.0 or L <= u <= L + 3.0):
                return True
        return False

    def contraintes(self, o, ctx, passe="toutes"):
        """Contraintes de la recherche de candidat (P7, P8) selon le statut de l'objet et la passe :
        « toutes » (règles dures de l'objet), « critiques » (gravité critique + physiques), « physiques »."""
        st = POL.statut_objet(o)
        pieton = POL.porte_tete_pietonne(o, self.tetes_de)
        C = dict(statut=st, zones_emprise=set(), zones_centre=set(), palier_conditionnel=False, admissions=[],
                 reculs=[], relations=set(), regles=set())
        for g in self.applicables(o, ctx["zone"]):
            gid = g["id"]
            if gid not in EVALUEES:
                continue
            ex = self._excuses(g, o)
            interd = set(g["surfaces_interdites"]) - ex
            phys = interd & POL.SURFACES_PHYSIQUES
            dure_g = st != "existant" and self.dure(o, g, dict(nature="surface", valeur=sorted(interd - POL.SURFACES_PHYSIQUES),
                                                                 gravite_effective=g["gravite"]))
            if passe == "physiques" or (passe == "critiques" and g["gravite"] != "critique"):
                dure_g = False
            if phys:
                C["zones_emprise"] |= phys
                C["regles"].add(gid)
            if dure_g and interd - phys:
                autres = interd - phys
                if gid in ("GEN-02", "FEU-07") and pieton:
                    C["zones_centre"] |= autres - {"palier_abaisse"}
                    C["palier_conditionnel"] = C["palier_conditionnel"] or "palier_abaisse" in autres
                else:
                    C["zones_emprise"] |= autres
                C["regles"].add(gid)
            autor = set(g["surfaces_autorisees"]) if gid not in AUTORISEES_CONDITIONNELLES else set()
            if dure_g and autor:
                admis = set(autor) | set(ex)
                for zn, d in self.voc["classes_surface"].items():
                    if zn in DERIVEES and zn not in interd and any(x in autor for x in d.get("dans", [])):
                        admis.add(zn)
                C["admissions"].append((gid, admis))
            for rel in g.get("relations", []):
                if rel["rel"] == "derriere_bordure" and rel["cible"] in ("bordure_chaussee", "bordure_quai"):
                    rmin = rel.get("recul_min_m")
                    if gid == "VEG-02":
                        rmin = g["parametres"]["recul_tronc_min_m"][o.get("developpement", "moyen")]
                    C["reculs"].append(dict(regle=gid, rmin=rmin, rmax=rel.get("recul_max_m"), dure=dure_g,
                                            poids=POL.poids_mou(g, None)))
            if dure_g and gid in ("FEU-01", "SIG-10", "SIG-11", "PMR-01"):
                C["relations"].add(gid)
        return C

    def faisable(self, o, P, az, C):
        """Masque des candidats P (N, 2) qui respectent les contraintes dures C + coût mou."""
        P = np.atleast_2d(P)
        ok = np.ones(len(P), bool)
        mou = np.zeros(len(P))
        E = np.vstack([self.emprise(o, q, az) for q in P])
        k = len(E) // len(P)
        ze, base, _, zdef, _, _ = self.zones(E)
        if o["sigma"] <= self.par["seuil_sigma_preuve_forte_m"]:
            ze = np.where(zdef & np.isin(ze, sorted(DERIVEES)), base, ze)
        ze = ze.reshape(len(P), k)
        zc = ze[:, 0]
        if C["zones_emprise"]:
            ok &= ~np.isin(ze, sorted(C["zones_emprise"])).any(axis=1)
        if C["zones_centre"]:
            ok &= ~np.isin(zc, sorted(C["zones_centre"]))
        if C["palier_conditionnel"]:
            pal = zc == "palier_abaisse"
            for i in np.nonzero(pal & ok)[0]:
                if not self.dans_prolongement_passage(P[i]):
                    ok[i] = False
        for gid, admis in C["admissions"]:
            ok &= np.isin(zc, sorted(admis))
        refs = self.c.ref_bordure(P, rayon=self.par["rayon_bordure_reference_m"], circulee=True)
        r_p0 = self.c.ref_bordure(np.asarray(o["p0"], float)[None], rayon=self.par["rayon_bordure_reference_m"], circulee=True)[0]
        if r_p0 is not None and r_p0["t"] >= -1.0:
            for rc in C["reculs"]:
                for i, r in enumerate(refs):
                    if r is None or r["t"] >= 6.0:
                        continue
                    tb = r["t"] - self._demi_profondeur(o, r, az)
                    if rc["rmin"] is not None and tb < rc["rmin"] - 1e-6:
                        if rc["dure"]:
                            ok[i] = False
                        else:
                            mou[i] += rc["poids"] * ((rc["rmin"] - tb) / 0.25) ** 2
                    elif rc["rmax"] is not None and tb > rc["rmax"]:
                        mou[i] += 0.5 * rc["poids"] * ((tb - rc["rmax"]) / 0.5) ** 2
        if "FEU-01" in C["relations"]:
            g = self.regles["FEU-01"]
            ap = self._approche(o)
            if ap is not None:
                lo, hi = g["parametres"]["ds_ligne_effet_m"]
                tol = g["parametres"].get("tolerance_amont_m", 0.5)
                v = P - ap["milieu"]
                ds = v @ ap["h"]
                cote = (ap["h"][0] * v[:, 1] - ap["h"][1] * v[:, 0]) < 0
                ok &= (ds >= lo - tol) & (ds <= hi) & cote
        for gid in ("SIG-10", "SIG-11"):
            if gid in C["relations"] and self.nez:
                N_ = np.array([n["p"] for n in self.nez])
                d = np.min(np.hypot(*(P[:, None, :] - N_[None]).transpose(2, 0, 1)), axis=1)
                ok &= d <= self.regles[gid]["parametres"]["distance_nez_max_m"]
        if "PMR-01" in C["relations"]:
            z0 = self.zones(np.asarray(o["p0"], float)[None])[0][0]
            ok &= zc == z0
            for i in np.nonzero(ok)[0]:
                r = self._pmr(o, P[i], dict(ref=refs[i], zone=zc[i]))
                if r and r["avec"] < r["seuil"] <= r["sans"]:
                    ok[i] = False
        ok &= self._sans_traversee(o, P)
        # P5 : jamais à moins de r1 + r2 + 0,10 m d'un objet de preuve au moins aussi bonne ; coût sinon
        d = np.hypot(*(P[:, None, :] - self.P[None]).transpose(2, 0, 1))
        autre = (self.Grp != o["groupe"])
        lim = o["rayon"] + self.Rr + 0.10
        proche = (d < lim[None]) & autre[None]
        aussi_bon = self.Sig <= o["sigma"] + 1e-9
        ok &= ~np.any(proche & aussi_bon[None], axis=1)
        mou += 2.0 * np.sum(proche & ~aussi_bon[None], axis=1)
        ok &= ~np.any(ze == "batiment", axis=1) | ("dalle" in str(o.get("z_source") or ""))
        # P9 : budget compté depuis la position source brute
        if o.get("p_brut") is not None:
            ok &= np.hypot(*(P - np.asarray(o["p_brut"], float)).T) <= float(o["dmax_brut"]) + 1e-9
        return ok, mou

    def _chercher(self, o, ref, C, az, sigma, dmax, pas_n, pas_l):
        """Normale à la bordure en s0, puis grille (Δs, Δt) ; sans bordure : grille plane."""
        if ref is not None:
            n = normale_gauche(ref["tg"][None])[0]
            dt = np.arange(-dmax, dmax + 1e-9, pas_n)
            dt = dt[np.argsort(np.abs(dt) - 1e-6 * (dt > 0))]
            P = o["p0"] + dt[:, None] * n
            ok, mou = self.faisable(o, P, az, C)
            if ok.any():
                J = (dt / sigma) ** 2 + mou
                J[~ok] = np.inf
                i = int(np.argmin(J))
                return dict(p=P[i], dt=float(dt[i]), ds=0.0, J=float(J[i]), mode="normale")
            ds_ = np.arange(-dmax, dmax + 1e-9, pas_l)
            dt_ = np.arange(-dmax, dmax + 1e-9, pas_n)
            DS, DT = np.meshgrid(ds_, dt_)
            DS, DT = DS.ravel(), DT.ravel()
            m = np.hypot(DS, DT) <= dmax + 1e-9
            DS, DT = DS[m], DT[m]
            P = o["p0"] + DS[:, None] * ref["tg"] + DT[:, None] * n
            ok, mou = self.faisable(o, P, az, C)
            if ok.any():
                J = (DT / sigma) ** 2 + self.par["poids_longitudinal_ratio"] * (DS / sigma) ** 2 + mou
                J[~ok] = np.inf
                i = int(np.argmin(J))
                return dict(p=P[i], dt=float(DT[i]), ds=float(DS[i]), J=float(J[i]), mode="grille")
            return None
        g = np.arange(-dmax, dmax + 1e-9, 0.1)
        X, Y = np.meshgrid(g, g)
        D = np.c_[X.ravel(), Y.ravel()]
        D = D[np.hypot(*D.T) <= dmax]
        P = o["p0"] + D
        ok, mou = self.faisable(o, P, az, C)
        if ok.any():
            J = (np.hypot(*D.T) / sigma) ** 2 + mou
            J[~ok] = np.inf
            i = int(np.argmin(J))
            return dict(p=P[i], dt=float(np.hypot(*D[i])), ds=0.0, J=float(J[i]), mode="plan")
        return None

    def _sans_traversee(self, o, P):
        """Vrai pour les candidats atteints depuis p0 sans franchir d'arête avant de bordure (autre
        que la bordure de référence quand l'objet est côté chaussée, à moins de 1 m)."""
        p0 = np.asarray(o["p0"], float)
        P = np.atleast_2d(P)
        lo = np.minimum(P.min(axis=0), p0) - 0.1
        hi = np.maximum(P.max(axis=0), p0) + 0.1
        c = self.c
        sel = ((np.minimum(c.kA, c.kB) <= hi) & (np.maximum(c.kA, c.kB) >= lo)).all(axis=1)
        if not sel.any():
            return np.ones(len(P), bool)
        r0 = c.ref_bordure(p0[None], rayon=1.0, circulee=False)[0]
        if r0 is not None and r0["t"] < 0:
            sel &= c.kK != r0["k"]
        A, B = c.kA[sel], c.kB[sel]
        d = P - p0
        e = B - A
        den = d[:, None, 0] * e[None, :, 1] - d[:, None, 1] * e[None, :, 0]
        w = A[None, :, :] - p0
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (w[..., 0] * e[None, :, 1] - w[..., 1] * e[None, :, 0]) / den
            u = (w[..., 0] * d[:, None, 1] - w[..., 1] * d[:, None, 0]) / den
        coupe = (np.abs(den) > 1e-12) & (t > 1e-6) & (t <= 1.0) & (u >= 0.0) & (u <= 1.0)
        return ~coupe.any(axis=1)

    def resoudre(self, o, V, ctx):
        """Recherche du candidat admissible le plus proche ; renvoie un dict de résolution. Un objet sans
        violation dure ne bouge pas (P7 : un recul non respecté par un objet existant est signalé)."""
        dures = sorted({v["regle"] for v in V if v["dure"]})
        sigma, dmax = o["sigma"], o["dmax"]
        degrade = False
        if ctx["ref"] is not None and ctx["ref"]["modifiee"] and anterieure_travaux(o):
            sigma, degrade = sigma * 2.0, True
        out = dict(regles_dures=dures, sigma_recherche=round(sigma, 3), dmax=dmax, degradation_temporelle=degrade,
                   statut_objet=POL.statut_objet(o), p_brut=None if o.get("p_brut") is None else [round(float(v), 3) for v in o["p_brut"]],
                   dmax_brut=o.get("dmax_brut"))
        if not dures:
            return out
        if o["preuve"] == "gam":
            dmax = min(dmax, 0.5)
        az = o.get("azimut0")
        pas_n, pas_l = self.par["pas_normal_m"], self.par["pas_longitudinal_m"]
        ref = ctx["ref"] or self.c.ref_bordure(o["p0"][None], rayon=30.0, circulee=False)[0]
        Ct = self.contraintes(o, ctx, "toutes")
        out["contraintes"] = sorted(Ct["regles"])
        zones_v = {z for v in V if v["dure"] and v["nature"] == "surface" for z in (v.get("valeur") or [])}
        if ref is not None and zones_v and zones_v <= ZONES_LONGITUDINALES and not POL.porte_tete_pietonne(o, self.tetes_de):
            # (P8 : un support de feux piétons se place à la limite arrière de la BEV, dans le prolongement du
            # passage : il recule le long de la normale, il ne glisse pas sur le côté)
            dsv = np.arange(-dmax, dmax + 1e-9, pas_l)
            dsv = dsv[np.argsort(np.abs(dsv) - 1e-6 * (dsv > 0))]
            P = o["p0"] + dsv[:, None] * ref["tg"]
            ok, mou = self.faisable(o, P, az, Ct)
            if ok.any():
                J = self.par["poids_longitudinal_ratio"] * (dsv / sigma) ** 2 + mou
                J[~ok] = np.inf
                i = int(np.argmin(J))
                out.update(candidat=P[i], dt=0.0, ds=round(float(dsv[i]), 3), J=round(float(J[i]), 3),
                           mode="longitudinal", d=round(float(abs(dsv[i])), 3), dans_dmax=True)
                return out
        for passe in ("toutes", "critiques", "physiques"):
            C = Ct if passe == "toutes" else self.contraintes(o, ctx, passe)
            if passe != "toutes" and sorted(C["regles"]) == sorted(Ct["regles"]):
                continue
            c = self._chercher(o, ref, C, az, sigma, dmax, pas_n, pas_l)
            if c is not None:
                out.update(candidat=c["p"], dt=round(c["dt"], 3), ds=round(c["ds"], 3), J=round(c["J"], 3),
                           mode=c["mode"], d=round(float(np.hypot(*(c["p"] - o["p0"]))), 3), dans_dmax=True,
                           relaxation=None if passe == "toutes" else sorted(set(Ct["regles"]) - set(C["regles"])),
                           passe=passe)
                return out
        # au-delà de d_max : candidat indicatif (jamais appliqué : P9), pour l'arbitrage et la planche
        dabs = self.par["deplacement_max_absolu_m"]
        C = self.contraintes(o, ctx, "physiques")
        if dmax < dabs and ref is not None:
            dt = np.arange(-dabs, dabs + 1e-9, pas_n)
            dt = dt[np.argsort(np.abs(dt) - 1e-6 * (dt > 0))]
            n = normale_gauche(ref["tg"][None])[0]
            P = o["p0"] + dt[:, None] * n
            pb = o.get("p_brut")
            o["p_brut"] = None
            ok, mou = self.faisable(o, P, az, C)
            o["p_brut"] = pb
            if ok.any():
                i = int(np.argmax(ok))
                out.update(candidat_hors_dmax=P[i], d_hors=round(float(abs(dt[i])), 3), dt=round(float(dt[i]), 3), ds=0.0)
        out["dans_dmax"] = False
        return out


def _densifier_anneau(r, pas):
    r = np.asarray(r, float)
    rr = np.vstack([r, r[:1]])
    out = []
    for a, b in zip(rr[:-1], rr[1:]):
        k = max(1, int(math.ceil(np.hypot(*(b - a)) / pas)))
        out.append(a + (b - a) * (np.arange(k)[:, None] / k))
    return np.vstack(out)


def _extremites(r):
    r = np.asarray(r, float)
    c = r.mean(axis=0)
    w, V = np.linalg.eigh(np.cov((r - c).T))
    u = V[:, 1]
    pr = (r - c) @ u
    return [r[int(np.argmin(pr))], r[int(np.argmax(pr))]]
