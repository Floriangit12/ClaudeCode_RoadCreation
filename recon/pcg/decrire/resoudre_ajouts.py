"""Ajouts d'objets prouvés (fusion 0.3, ajouts.geojson) : arbres, mobilier, panneaux, candélabres, clôtures,
haies et massifs, tampons et avaloirs.

RES-ADD-001 : instancier vrai dans la fusion, preuve stricte probante, confiance ≥ moyenne, σ sous le seuil de la classe,
type non ambigu. RES-ADD-002 : tampons et avaloirs dans objets/ponctuels_sol_ajouts.geojson (pas de matériau fonte
dans la table du schéma 0.3). Les surfaces ajoutées ne sont jamais intégrées (partition de surfaces.py).
"""
import numpy as np

from commun import O, arrondi, repere
import resoudre_regles as RR

CLES_ARBRE = ["type", "essence", "essence_code", "genre", "hauteur_m", "diametre_couronne_m", "hauteur_lidar_2021_m",
              "hauteur_mnh_ign_m", "diametre_couronne_lidar_m", "circonference_cm", "annee_plantation",
              "hauteur_classe_inventaire", "zone_plantation", "bosquet", "etat_2026", "instancier", "source", "confiance",
              "remarque", "gam_bloc", "gam_echelle_bloc", "controle_ortho2024_vegetation", "controle_ortho2024_texture",
              "x_local", "y_local", "z_local", "z_sol_ngf", "z_source", "id", "statut_2026"]
# sous-type -> (type d'arbre, hauteur a priori m, couronne a priori m) ; a priori documentés (défaut du paquet : 5 m)
ARBRES = {"jeunes_arbres_alignement": ("feuillu", 5.0, 2.5), "arbustes_conifères": ("arbuste", 3.0, 1.5),
          "petit_arbre": ("feuillu", 5.0, 2.5), "grand_feuillu": ("feuillu", 13.5, 12.0),
          "petit_arbre_fleuri": ("feuillu", 5.0, 2.5), "feuillu": ("feuillu", 5.0, 3.5),
          "feuillage_pourpre": ("feuillu", 5.0, 3.0), "arbustes_boules": ("arbuste", 1.5, 1.2)}
MOBILIER = {"cage_metallique": ("abri_technique", "divers", 1.2), "conteneurs": ("conteneur_tri", "divers", 1.5),
            "conteneurs_dechets": ("conteneur_dechets", "divers", 1.2), "bancs": ("banc", "divers", 0.8),
            "bloc_rocheux_alignement": ("bloc_rocheux", "barriere", 0.6), "blocs_rocheux": ("bloc_rocheux", "barriere", 0.6),
            "borne_lumineuse_globe": ("lampadaire", "lampadaire", 3.0), "lampadaire_pieton": ("lampadaire", "lampadaire", 3.0),
            "panneau_parking_prive": ("panneau", "panneau", 2.0), "panneau_information_2_poteaux": ("panneau_information", "panneau", 2.0),
            "C13a_dos": ("panneau", "panneau", 2.3), "portail_coulissant": ("portail", "barriere", 1.8)}


def _points(g):
    if g["type"] == "Point":
        return [g["coordinates"]]
    if g["type"] == "MultiPoint":
        return g["coordinates"]
    return []


def _attr(q, a):
    v = (q["attributs"].get(a) or {}).get("valeur")
    return v


class ResolveurAjouts:
    def __init__(self, S, J, ctx, mnt):
        self.S, self.J, self.ctx, self.mnt = S, J, ctx, mnt
        self.arbres, self.mobilier, self.vegetation, self.ponctuels = [], [], [], []

    def _z(self, xy):
        z = float(self.mnt(np.array([xy[0] + O[0]]), np.array([xy[1] + O[1]]))[0])
        return z - O[2]

    def _preuve(self, q):
        if q["tranche_stricte"] not in RR.TRANCHES_PROBANTES:
            return f"preuve non stricte ({q['tranche_stricte']})"
        if q["confiance"] not in RR.CONFIANCES_PROBANTES:
            return f"confiance {q['confiance']}"
        if q.get("valide_2026") is not True:
            return f"validité 2026 {q.get('valide_2026')}"
        if any("_ou_" in s for s in q["sous_types"]):
            return f"type ambigu ({', '.join(q['sous_types'])})"
        return None

    def _provenance(self, q):
        obs = sorted({x["obs"] for x in q["provenance"]})
        ref = "; ".join(f"{x['obs']} ({x['source']}, {x['date']}, {x['confiance']})" for x in q["provenance"])
        return obs, ref

    def _refus(self, q, motif, origine="proposition_rejetee"):
        obs, _ = self._provenance(q)
        xy = [float(v) for v in q["local"]] if q.get("local") else None
        self.J.non_resolu(q["id"], "ajouts", f"ajout:{q['classe']}", origine=origine, xy=xy, classe=",".join(q["sous_types"]),
                          regles=["RES-ADD-001"] + (["RES-ADD-002"] if q["classe"] in ("tampon", "avaloir") else []),
                          observations=obs, motif=motif)

    # ------------------------------------------------------------------ arbres
    def _arbre(self, q, obs, ref):
        st = q["sous_types"][0]
        typ, h0, c0 = ARBRES.get(st, ("feuillu", 5.0, 3.0))
        h = _attr(q, "hauteur_m") or h0
        cour = _attr(q, "couronne_m") or c0
        pts = _points(self._geom(q))
        n = len(pts)
        for k, c in enumerate(pts, 1):
            xy = [float(c[0] - O[0]), float(c[1] - O[1])]
            z = self._z(xy)
            ident = q["id"] if n == 1 else f"{q['id']}-{k}"
            p = {cle: None for cle in CLES_ARBRE}
            p.update({"type": typ, "hauteur_m": float(h), "diametre_couronne_m": float(cour), "etat_2026": "existant",
                      "instancier": True, "source": f"fusion 0.3 ajout {q['id']} : {ref}"[:300], "confiance": q["confiance"],
                      "remarque": "; ".join(d["texte"] for d in q["descriptions"])[:300] or None,
                      "x_local": round(xy[0], 3), "y_local": round(xy[1], 3), "z_local": round(z, 3),
                      "z_sol_ngf": round(z + O[2], 2), "z_source": "MNT 2026 (heightmap_3025_10cm)", "id": ident,
                      "statut_2026": "existant (ajout prouvé, fusion 0.3)",
                      "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                            "regles": ["RES-ADD-001", "FUS-ADD-03"], "sigma_m": q["sigma_m"],
                                                            "conf": q["confiance"], "a_priori": {"hauteur_m": _attr(q, "hauteur_m") is None,
                                                                                                 "diametre_couronne_m": _attr(q, "couronne_m") is None}})]}})
            self.arbres.append({"type": "Feature", "properties": p,
                                "geometry": {"type": "Point", "coordinates": [round(c[0], 3), round(c[1], 3)]}})
            self.J.appliquer(ident, "arbres", "ajout", avant=None, apres={"type": typ, "hauteur_m": h}, regles=["RES-ADD-001", "FUS-ADD-03"],
                             observations=obs, conf=q["confiance"], xy_avant=None, xy_apres=xy, portee=0.6,
                             classe=typ, motif=f"{st} observé ({q['tranche_stricte']}), σ {q['sigma_m']} m")

    def _geom(self, q):
        return self._g[q["id"]]

    # ------------------------------------------------------------------ mobilier (points et lignes)
    def _mobilier(self, q, obs, ref, g):
        st = q["sous_types"][0]
        typ, cat, h = MOBILIER[st]
        code = _attr(q, "code")
        az = _attr(q, "azimut_deg")
        texte = _attr(q, "texte_lu")
        if g["type"] == "LineString":
            P = repere(np.asarray(g["coordinates"], float)[:, :2])
            xy = [float(P[:, 0].mean()), float(P[:, 1].mean())]
            ident = q["id"]
            p = {"id": ident, "type": typ, "categorie": cat, "hauteur_m": h, "longueur_m": round(float(np.hypot(*np.diff(P, axis=0).T).sum()), 2),
                 "etat_2026": "existant (ajout prouvé, fusion 0.3)", "confiance": q["confiance"],
                 "source": f"fusion 0.3 ajout {q['id']} : {ref}"[:300],
                 "remarque": "; ".join(d["texte"] for d in q["descriptions"])[:300] or None,
                 "statut_2026": "existant (ajout prouvé, fusion 0.3)",
                 "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                       "regles": ["RES-ADD-001", "FUS-ADD-03"], "sigma_m": q["sigma_m"], "conf": q["confiance"]})]}}
            self.mobilier.append({"type": "Feature", "properties": p,
                                  "geometry": {"type": "LineString", "coordinates": [[round(c[0], 3), round(c[1], 3)] for c in g["coordinates"]]}})
            self.J.appliquer(ident, "mobilier", "ajout", avant=None, apres={"type": typ}, regles=["RES-ADD-001", "FUS-ADD-03"],
                             observations=obs, conf=q["confiance"], xy_avant=None, xy_apres=xy, portee=0.6, classe=typ,
                             motif=f"{st} observé ({q['tranche_stricte']}), σ {q['sigma_m']} m")
            return
        pts = _points(g)
        n = len(pts)
        for k, c in enumerate(pts, 1):
            xy = [float(c[0] - O[0]), float(c[1] - O[1])]
            z = self._z(xy)
            ident = q["id"] if n == 1 else f"{q['id']}-{k}"
            sid, cl = self.ctx.surface(xy)
            kid, dk = self.ctx.bordure_gam(xy)
            p = {"id": ident, "type": typ, "categorie": cat, "hauteur_m": h, "azimut_deg": az, "yaw_deg": az,
                 "code": code, "texte": texte, "etat_2026": "existant (ajout prouvé, fusion 0.3)", "confiance": q["confiance"],
                 "source": f"fusion 0.3 ajout {q['id']} : {ref}"[:300],
                 "remarque": "; ".join(d["texte"] for d in q["descriptions"])[:300] or None,
                 "z_source": "MNT 2026 (heightmap_3025_10cm)", "x_local": round(xy[0], 3), "y_local": round(xy[1], 3),
                 "z_local": round(z, 3), "z_sol_ngf": round(z + O[2], 2), "classe_surface_2026": cl,
                 "distance_bordure_gam_m": round(dk, 2) if dk is not None else None,
                 "statut_2026": "existant (ajout prouvé, fusion 0.3)",
                 "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                       "regles": ["RES-ADD-001", "FUS-ADD-03"], "sigma_m": q["sigma_m"],
                                                       "conf": q["confiance"], "surface": sid,
                                                       "a_priori": {"hauteur_m": True}})]}}
            self.mobilier.append({"type": "Feature", "properties": p,
                                  "geometry": {"type": "Point", "coordinates": [round(c[0], 3), round(c[1], 3)]}})
            self.J.appliquer(ident, "mobilier", "ajout", avant=None, apres={"type": typ, "code": code}, regles=["RES-ADD-001", "FUS-ADD-03"],
                             observations=obs, conf=q["confiance"], xy_avant=None, xy_apres=xy, portee=0.8 if cat == "panneau" else 0.6,
                             classe=typ, motif=f"{st} observé ({q['tranche_stricte']}, {cl or 'hors surfaces'}), σ {q['sigma_m']} m")

    # ------------------------------------------------------------------ haies et massifs
    def _vegetation(self, q, obs, ref, g):
        typ = "haie" if q["classe"] == "haie" else "massif"
        ident = q["id"]
        cs = g["coordinates"]
        P = repere(np.asarray([cs] if g["type"] == "Point" else cs, float)[:, :2])
        xy = [float(P[:, 0].mean()), float(P[:, 1].mean())]
        p = {"id": ident, "type": typ, "sous_type": q["sous_types"][0], "hauteur_m": _attr(q, "hauteur_m"),
             "epaisseur_m": _attr(q, "epaisseur_m"), "essence": _attr(q, "essence"), "instancier": True,
             "source": f"fusion 0.3 ajout {q['id']} : {ref}"[:300], "confiance": q["confiance"],
             "remarque": "; ".join(d["texte"] for d in q["descriptions"])[:300] or None, "hotes": q["hotes"],
             "statut_2026": "existant (ajout prouvé, fusion 0.3)",
             "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                   "regles": ["RES-ADD-001", "FUS-ADD-03"], "sigma_m": q["sigma_m"], "conf": q["confiance"]})]}}
        geom = {"type": g["type"], "coordinates": [round(cs[0], 3), round(cs[1], 3)] if g["type"] == "Point" else
                [[round(c[0], 3), round(c[1], 3)] for c in cs]}
        self.vegetation.append({"type": "Feature", "properties": p, "geometry": geom})
        self.J.appliquer(ident, "vegetation", "ajout", avant=None, apres={"type": typ, "sous_type": q["sous_types"][0]},
                         regles=["RES-ADD-001", "FUS-ADD-03"], observations=obs, conf=q["confiance"], xy_avant=None, xy_apres=xy,
                         portee=0.7, classe=typ, motif=f"{q['sous_types'][0]} observé ({q['tranche_stricte']}), σ {q['sigma_m']} m")

    # ------------------------------------------------------------------ tampons et avaloirs
    def _ponctuel(self, q, obs, ref, g, compteur):
        typ = q["classe"]
        pre = "TAM" if typ == "tampon" else "AVA"
        forme = _attr(q, "forme") or ("carre" if any("carre" in s or "grille" in s for s in q["sous_types"]) else
                                      "rectangulaire" if any("rect" in s for s in q["sous_types"]) else "rond")
        dim = _attr(q, "dimension_m")
        for k, c in enumerate(_points(g), 1):
            compteur[pre] += 1
            ident = f"{pre}-{compteur[pre]:04d}"
            xy = [float(c[0] - O[0]), float(c[1] - O[1])]
            sid, cl = self.ctx.surface(xy)
            kid, dk = self.ctx.bordure_gam(xy)
            if cl in ("chaussee", "parking", "acces_riverain"):
                en124 = "D400" if (dk is None or dk > 0.5) else "C250"
            elif cl in ("trottoir", "quai_bus", "piste_cyclable"):
                en124 = "C250" if (dk is not None and dk <= 0.2) else "B125"
            else:
                en124 = "B125"
            z = self._z(xy)
            p = {"id": ident, "famille": "ponctuels_sol", "type": typ, "forme": forme, "dimension_m": dim,
                 "classe_en124": en124, "materiau": "fonte (absent de materiaux_description.json : RES-ADD-002)",
                 "surface": sid, "classe_surface": cl, "ancrage": {"bordure": kid, "distance_m": round(dk, 2) if dk is not None else None},
                 "z_local": round(z, 3), "ajout_fusion": q["id"], "point": k,
                 "prov": {"geometrie": {"src": "ortho2022" if all(x["source"] == "ortho2022" for x in q["provenance"]) else
                                        "regle:resolution.RES-ADD-002", "ref": f"fusion 0.3 ajout {q['id']} : {ref}"[:300],
                                        "conf": q["confiance"]},
                          "classe_en124": {"src": "regle:regles_conception.GA-ASS-003",
                                           "ref": f"surface {cl} à {dk if dk is None else round(dk, 2)} m de la bordure levée",
                                           "conf": "moyenne"}},
                 "remarque": "; ".join(d["texte"] for d in q["descriptions"])[:300] or None,
                 "resolution": {"decisions": [arrondi({"nature": "ajout", "ajout_fusion": q["id"], "observations": obs,
                                                       "regles": ["RES-ADD-001", "RES-ADD-002", "FUS-ADD-03", "GA-ASS-003"],
                                                       "sigma_m": q["sigma_m"], "conf": q["confiance"]})]}}
            self.ponctuels.append({"type": "Feature", "properties": p,
                                   "geometry": {"type": "Point", "coordinates": [round(c[0], 3), round(c[1], 3)]}})
            self.J.appliquer(ident, "ponctuels_sol", "ajout", avant=None, apres={"type": typ, "forme": forme, "classe_en124": en124},
                             regles=["RES-ADD-001", "RES-ADD-002", "FUS-ADD-03"], observations=obs, conf=q["confiance"],
                             xy_avant=None, xy_apres=xy, portee=0.4, classe=typ,
                             motif=f"{typ} {forme} sur {cl or 'hors surfaces'} ({q['id']}, σ {q['sigma_m']} m)")

    def executer(self):
        import collections
        compteur = collections.Counter()
        self._g = {f["properties"]["id"]: f["geometry"] for f in self.S.ajouts}
        for ft in sorted(self.S.ajouts, key=lambda f: f["properties"]["id"]):
            q = ft["properties"]
            g = ft["geometry"]
            if q["classe"] == "marquage":
                continue                       # resoudre_marquages.ajouts
            if not q["instancier"]:
                continue
            if q["classe"] == "surface":
                self._refus(q, "surface observée : la partition des surfaces appartient à surfaces.py (hôte "
                               f"{', '.join(q['hotes']) or '?'})", origine="schema")
                continue
            motif = self._preuve(q)
            if motif:
                self._refus(q, motif)
                continue
            lineaire = g["type"] in ("LineString", "MultiLineString")
            cle = "ponctuel" if q["classe"] in ("tampon", "avaloir") else "arbre" if q["classe"] == "arbre" else \
                  "lineaire" if lineaire or q["classe"] in ("haie", "massif") else "point"
            smax = RR.SIGMA_MAX_AJOUT[cle]
            if float(q["sigma_m"]) > smax:
                self._refus(q, f"σ {q['sigma_m']} m > {smax} m (classe {cle})")
                continue
            obs, ref = self._provenance(q)
            if q["classe"] == "arbre":
                if q["sous_types"][0] not in ARBRES:
                    self._refus(q, f"sous-type {q['sous_types'][0]} sans correspondance de type d'arbre", origine="schema")
                    continue
                self._arbre(q, obs, ref)
            elif q["classe"] in ("haie", "massif"):
                self._vegetation(q, obs, ref, g)
            elif q["classe"] in ("tampon", "avaloir"):
                self._ponctuel(q, obs, ref, g, compteur)
            elif q["sous_types"][0] in MOBILIER and (g["type"] in ("Point", "MultiPoint", "LineString")):
                if q["classe"] == "cloture" and g["type"] == "Point":
                    self._refus(q, "clôture décrite par un point : tracé inconnu")
                    continue
                self._mobilier(q, obs, ref, g)
            else:
                self._refus(q, f"classe {q['classe']} / sous-type {q['sous_types'][0]} sans famille d'objets", origine="schema")
        return self.arbres, self.mobilier, self.vegetation, self.ponctuels
