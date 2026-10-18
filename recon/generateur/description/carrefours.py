# -*- coding: utf-8 -*-
"""Compilateur de réseau de la description simple (lot « scenes », 17/10/2026) : carrefours plans, giratoires et
bretelles d'autoroute reliant des tronçons décrits (`troncons[]`, chacun avec son `id`).

Appelé par `description_vers_modele.compiler` dès que la description porte « carrefours », « giratoires » ou
« bretelles ». Deux passes :
  1. les tronçons seuls sont compilés (profils d'extrémité, tracés) ; la géométrie du réseau en est tirée : branches
     (azimut, bords de chaussée, voies entrantes et sortantes), limite de la chaussée abordée (frontière), positions des
     lignes transversales, des passages, des sas, des flèches ;
  2. les tronçons sont recompilés avec les évènements posés aux branches (passages piétons, continue d'approche…), puis
     les objets du réseau sont construits sur le modèle (nœuds de carrefour, carrefours, branches, îlots, trajectoires,
     conflits, zone de conflit, signaux, contrôleur de feux, anneau de giratoire, musoirs de bretelle) avant la
     validation.

Règle tenue : « Houdini n'invente rien ». Une valeur dite garde la provenance `description:<chemin>` ; une valeur non
dite vient d'une règle de `regles_route_fr.json` citée (`defaut:` / `inference:`) ; un résultat de construction
géométrique porte `solveur:<étape>` avec la règle qui le fonde. Sans règle ni valeur dite : erreur.
Géométrie : shapely (déterministe), coordonnées Lambert-93 comme le reste du modèle.
"""
from __future__ import annotations

import copy
import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

import regles
from commun import profil as PF
from commun import prov as P
from description import description_vers_modele as D
from description import format_profil as FP
from description import vocabulaire as V
from commun import geometrie as G

TOL_EXTREMITE = 0.05            # m : extrémité de branche au centre du carrefour / sur l'anneau
VERSION_RESEAU = "carrefours/1.0"

CLES_CARREFOUR = {"id", "nom", "centre", "type", "regime", "branches", "ilots", "feux", "guidage", "note",
                  "commentaire", "vehicule"}
CLES_BRANCHE = {"troncon", "regime", "passage", "sas", "ligne_effet", "coin", "fleches", "mouvements", "note",
                "commentaire", "ilot", "triangle"}
CLES_ILOT_CARREFOUR = {"type", "de", "vers", "rayon", "largeur_voie", "regime", "passage", "note", "commentaire",
                       "remplissage", "balise"}
CLES_FEUX = {"phases", "jaune", "cycle", "note", "commentaire"}
CLES_PHASE = {"nom", "mouvements", "vert", "pietons", "note"}
CLES_GUIDAGE = {"mouvements", "modulation", "largeur", "note"}
CLES_GIRATOIRE = {"id", "nom", "centre", "diametre", "rayon", "anneau", "couronne", "ilot_central", "branches", "type",
                  "trottoir", "note", "commentaire", "passages", "bordure_exterieure"}
CLES_BRANCHE_GIR = {"troncon", "ilot", "passage", "note", "commentaire", "entree", "sortie", "rayon_entree",
                    "rayon_sortie"}
CLES_BRETELLE = {"id", "nom", "type", "principale", "bretelle", "voie", "point", "biseau", "longueur", "musoir",
                 "note", "commentaire", "obliquite"}


class ErreurReseau(D.ErreurDescription):
    pass


def _r(x, nd=4):
    return round(float(x), nd) + 0.0


def _v(x, chemin):
    try:
        return V.nombre(x, chemin)
    except ValueError as e:
        raise ErreurReseau(str(e))


def _b(x, chemin):
    try:
        return V.booleen(x, chemin)
    except ValueError as e:
        raise ErreurReseau(str(e))


def _cles(dct, admises, chemin):
    if not isinstance(dct, dict):
        raise ErreurReseau(f"{chemin} : dictionnaire attendu")
    D.verifier_cles(dct, admises, chemin)


def unit(dx, dy):
    n = math.hypot(dx, dy)
    return (dx / n, dy / n)


def rot(v, a_deg):
    a = math.radians(a_deg)
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def ang(v):
    return math.degrees(math.atan2(v[1], v[0])) % 360.0


def norm180(a):
    a = (a + 180.0) % 360.0 - 180.0
    return 180.0 if abs(a + 180.0) < 1e-9 else a


def inter_lignes(p, u, q, v):
    """Intersection des droites (p + a u) et (q + b v) ; None si parallèles."""
    det = u[0] * (-v[1]) - u[1] * (-v[0])
    if abs(det) < 1e-9:
        return None
    rx, ry = q[0] - p[0], q[1] - p[1]
    a = (rx * (-v[1]) - ry * (-v[0])) / det
    return (p[0] + a * u[0], p[1] + a * u[1])


def arc_pts(c, r, a0, a1, pas_deg=3.0):
    """Points d'un arc de centre c, rayon r, de l'angle a0 à a1 (degrés, sens de a0 vers a1)."""
    n = max(2, int(math.ceil(abs(a1 - a0) / pas_deg)) + 1)
    return [(c[0] + r * math.cos(math.radians(a0 + (a1 - a0) * k / (n - 1))),
             c[1] + r * math.sin(math.radians(a0 + (a1 - a0) * k / (n - 1)))) for k in range(n)]


def xy_r(p):
    return [_r(p[0]), _r(p[1])]


def anneau(pts):
    pts = [xy_r(p) for p in pts]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def poly_schema(geom):
    """shapely Polygon → $defs/polygone (extérieur dans le sens trigonométrique)."""
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    from shapely.geometry.polygon import orient
    g = orient(geom, 1.0)
    out = {"exterieur": anneau(list(g.exterior.coords))}
    if g.interiors:
        out["trous"] = [anneau(list(i.coords)) for i in g.interiors]
    return out


def arrondir_sommets(poly, r):
    """Nez arrondis : ouverture morphologique (érosion puis dilatation de r) — sommets convexes de rayon r."""
    if r <= 0:
        return poly
    g = poly.buffer(-r, join_style="mitre").buffer(r, join_style="round", quad_segs=8)
    if g.is_empty:
        return poly
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda x: x.area)
    return g


# ================================================================================================ branches
class Branche:
    """Une extrémité de tronçon au centre d'un carrefour (ou au bord d'un anneau) : géométrie au droit de l'extrémité.
    Repère de branche : u = direction sortante (du centre vers l'extérieur), n = normale à gauche de u ; w = décalage
    latéral (positif du côté n). Les voies entrantes (vers le centre) sont du côté w > 0 (circulation à droite)."""

    def __init__(self, nom, trinfo, centre, chemin, rayon_contact=0.0):
        self.nom, self.chemin = nom, chemin
        self.rid, self.tr, self.desc = trinfo["rid"], trinfo["tr"], trinfo["desc"]
        tr = self.tr
        L = tr.L
        x0, y0, c0 = tr.trace.point(0.0)
        x1, y1, c1 = tr.trace.point(L)

        def ecarts(x, y, cap):
            """(écart longitudinal, écart latéral) de l'extrémité au centre, dans le repère de la ligne de référence."""
            dx, dy = x - centre[0], y - centre[1]
            if rayon_contact:
                return math.hypot(dx, dy) - rayon_contact, 0.0
            return dx * math.cos(cap) + dy * math.sin(cap), -dx * math.sin(cap) + dy * math.cos(cap)
        l0, t0 = ecarts(x0, y0, c0)
        l1, t1 = ecarts(x1, y1, c1)
        # l'extrémité est au droit du centre (écart longitudinal ≤ 5 cm) ; un décalage latéral de la ligne de référence
        # est admis (séparation des sens déportée à l'approche : voie de TAG, îlot), il est rapporté
        if abs(l1) <= TOL_EXTREMITE and (abs(l1) + abs(t1) <= abs(l0) + abs(t0)):
            self.extremite, self.s_ext, self.decalage = "fin", L, t1
        elif abs(l0) <= TOL_EXTREMITE:
            self.extremite, self.s_ext, self.decalage = "debut", 0.0, t0
        else:
            ou = "le centre" if rayon_contact == 0 else f"l'anneau (rayon {rayon_contact:.2f} m)"
            raise ErreurReseau(f"{chemin} : le tronçon « {nom} » ne rejoint pas {ou} : écarts longitudinaux {l0:.2f} m et "
                               f"{l1:.2f} m (tolérance {TOL_EXTREMITE} m) — les branches doivent se rejoindre")
        xe, ye, cap = tr.trace.point(self.s_ext)
        self.pe = (xe, ye)
        dr = (math.cos(cap), math.sin(cap))
        self.u = (-dr[0], -dr[1]) if self.extremite == "fin" else dr
        self.n = rot(self.u, 90.0)
        self.azimut = ang(self.u)
        self.sg = -1.0 if self.extremite == "fin" else 1.0      # t_route = sg · w
        eps = 1e-6
        self.s_prof = L - eps if self.extremite == "fin" else eps
        self.profil = tr.profil_a(self.s_prof)
        T = D.t_limites(self.profil, self.s_prof)
        self.bandes = []
        for i, b in enumerate(self.profil["bandes"]):
            wa, wb = sorted((self.sg * T[i], self.sg * T[i + 1]))
            self.bandes.append({"i": i, "id": b["id"], "type": b["type"], "sens": b["sens"], "w0": wa, "w1": wb,
                                "niveau": b["niveau"]["reference"], "b": b})
        ch = [x for x in self.bandes if x["niveau"] == "chaussee"]
        if not ch:
            raise ErreurReseau(f"{chemin} : la branche « {nom} » n'a pas de chaussée à son extrémité")
        self.w_g = max(x["w1"] for x in ch)                     # bord de chaussée côté n (voies entrantes)
        self.w_d = min(x["w0"] for x in ch)                     # bord de chaussée côté −n (voies sortantes)
        vers_centre = "avant" if self.extremite == "fin" else "arriere"
        mot = [x for x in self.bandes if x["type"] in PF.VOIES_MOTORISEES]
        # entrantes : de la gauche des usagers (côté axe, w petit) vers la droite (w grand)
        self.entrantes = sorted([x for x in mot if x["sens"] in (vers_centre, "double")], key=lambda x: x["w0"])
        self.sortantes = sorted([x for x in mot if x["sens"] not in (vers_centre,) or x["sens"] == "double"],
                                key=lambda x: -x["w1"])    # de la gauche des usagers sortants (côté axe) vers la droite
        self.cyclables_entrantes = [x for x in self.bandes if x["type"] == "bande_cyclable" and x["sens"] == vers_centre]
        # îlot (terre-plein) entre les sens à l'extrémité
        self.ilot_bande = None              # terre-plein entre les deux sens (TPC, îlot séparateur)
        self.ilots_bandes = []              # tous les terre-pleins entre voies motorisées (îlots de TAG compris)
        if self.entrantes and self.sortantes:
            wa, wb = min(x["w0"] for x in self.entrantes), max(x["w1"] for x in self.sortantes)
            for x in self.bandes:
                if x["type"] == "terre_plein" and x["w0"] >= wb - 1e-6 and x["w1"] <= wa + 1e-6:
                    self.ilot_bande = x
        if mot:
            w_min, w_max = min(x["w0"] for x in mot), max(x["w1"] for x in mot)
            self.ilots_bandes = [x for x in self.bandes if x["type"] == "terre_plein"
                                 and x["w0"] >= w_min - 1e-6 and x["w1"] <= w_max + 1e-6]
        if abs(self.decalage) > max(abs(self.w_g), abs(self.w_d)):
            raise ErreurReseau(f"{chemin} : la ligne de référence de « {nom} » passe à {self.decalage:.2f} m du centre, "
                               "hors de sa chaussée")
        self.regime = None
        self.d_front = 0.0

    # ---------------------------------------------------------------- outils
    def s_de_x(self, x):
        """Abscisse de route à la distance x du centre (le long de la branche)."""
        return self.tr.L - x if self.extremite == "fin" else x

    def pt(self, x, w):
        return (self.pe[0] + x * self.u[0] + w * self.n[0], self.pe[1] + x * self.u[1] + w * self.n[1])

    def pt_route(self, x, w):
        """Point exact sur le tracé de la route (courbes comprises)."""
        return self.tr.trace.point_st(self.s_de_x(x), self.sg * w)

    def t_route(self, w):
        return self.sg * w

    def largeur_chaussee(self):
        return self.w_g - self.w_d

    def bande(self, bid):
        return next((x for x in self.bandes if x["id"] == bid), None)


# ================================================================================================ compilation
def compiler_reseau(d, source, sha):
    for k in D.CLES_RESEAU:
        if d.get(k) is not None and not isinstance(d[k], list):
            raise ErreurReseau(f"{k} : liste attendue")
    if not d.get("troncons"):
        raise ErreurReseau("réseau : décrire les branches dans « troncons: » (chacune avec son « id »)")
    d1 = {k: v for k, v in d.items() if k not in D.CLES_RESEAU}
    cap = {}
    D.compiler(copy.deepcopy(d1), source, sha, _reseau=lambda m, r, c: cap.update(c))
    R = Reseau(d, cap)
    R.analyser()
    d2 = copy.deepcopy(d)
    R.injecter(d2)
    return D.compiler(d2, source, sha, _reseau=R.construire)


class Reseau:
    def __init__(self, d, cap):
        self.d = d
        self.noms = {}
        for k, t in enumerate(d["troncons"]):
            nom = str(t.get("id") or f"T{k + 1}")
            if nom in self.noms:
                raise ErreurReseau(f"troncons[{k}].id : « {nom} » en double")
            self.noms[nom] = k
        self.cap1 = cap
        self.origine = cap["origine"]
        self.carrefours = [CarrefourPlan(self, c, f"carrefours[{i}]", i) for i, c in enumerate(d.get("carrefours") or [])]
        self.giratoires = [Giratoire(self, g, f"giratoires[{i}]", i) for i, g in enumerate(d.get("giratoires") or [])]
        self.bretelles = [Bretelle(self, b, f"bretelles[{i}]", i) for i, b in enumerate(d.get("bretelles") or [])]
        self.tous = self.carrefours + self.giratoires + self.bretelles

    def trinfo(self, nom, chemin, cap=None):
        cap = cap or self.cap1
        if str(nom) not in self.noms:
            raise ErreurReseau(f"{chemin} : tronçon « {nom} » inconnu ({', '.join(self.noms)})")
        return cap["trs"][self.noms[str(nom)]]

    def local(self, p, chemin):
        if not (isinstance(p, list) and len(p) >= 2):
            raise ErreurReseau(f"{chemin} : point [x, y] attendu")
        return (self.origine[0] + _v(p[0], chemin), self.origine[1] + _v(p[1], chemin))

    def analyser(self):
        utilises = {}
        for obj in self.tous:
            obj.analyser(self.cap1)
            for cle in obj.extremites_utilisees():
                if cle in utilises:
                    raise ErreurReseau(f"{obj.chemin} : l'extrémité « {cle[1]} » du tronçon « {cle[0]} » est déjà une "
                                       f"branche de {utilises[cle]}")
                utilises[cle] = obj.chemin

    def injecter(self, d2):
        for obj in self.tous:
            for nom, ev in obj.evenements():
                t = d2["troncons"][self.noms[nom]]
                t.setdefault("evenements", [])
                t["evenements"] = list(t["evenements"] or []) + [ev]

    def construire(self, modele, rapport, ctxh):
        self.ctxh = ctxh
        self.modele = modele
        rapport["reseau"] = {"version": VERSION_RESEAU, "objets": [], "controles": [], "avertissements": []}
        self.rap = rapport["reseau"]
        modele.setdefault("carrefours", [])
        for obj in self.tous:
            obj.analyser(ctxh)          # géométrie recalculée sur les tronçons de la passe 2
            obj.construire(self, modele, ctxh)
            self.rap["objets"].append(obj.rapport)
            self.rap["controles"] += obj.ctrl
            self.rap["avertissements"] += obj.av
        if not modele["carrefours"]:
            modele.pop("carrefours")
        # nœuds d'extrémité devenus inutiles (remplacés par les nœuds de carrefour)
        utilises = {r["noeud_debut"] for r in modele["routes"]} | {r["noeud_fin"] for r in modele["routes"]}
        for c in modele.get("carrefours", []):
            utilises |= set(c.get("noeuds", []))
        modele["noeuds"] = [n for n in modele["noeuds"] if n["id"] in utilises]
        # lignes des voies d'insertion / de décélération : T2 5u (RF-MQ-INS-01, RF-MQ-DEC-01) au lieu du T1 2u des voies
        # de même sens (RF-OSM-MRQ-011) — règle spéciale, pas un écart : l'avertissement est remplacé par une note
        import re
        motif = re.compile(r"^ligne décrite (T2 5\.0|T'3 3\.0) entre \S+ et \S+ ; la règle RF-OSM-MRQ-0(11|21|22)")
        aux = re.compile(r"\b(ins|dec)(_e)?\d+\b")
        bretelles = {r["id"] for r in modele["routes"] if r.get("categorie") == "bretelle"}
        for t in rapport["troncons"]:
            garde = []
            for w in t["avertissements"]:
                if motif.match(w) and aux.search(w):
                    self.rap["avertissements"].append(f"{t['route']} : {w.split(' ; ')[0]} — ligne de voie auxiliaire "
                                                      "(RF-MQ-INS-01 / RF-MQ-DEC-01 / RF-MQ-LAR-B1b), règle spéciale")
                elif motif.match(w) and w.startswith("ligne décrite T'3") and t["route"] in bretelles:
                    # rive de BAU des bretelles T'3 3u (RF-MQ-SC-06 « bretelles_bau ») et non T4 3u de section courante
                    self.rap["avertissements"].append(f"{t['route']} : {w.split(' ; ')[0]} — rive de BAU de bretelle "
                                                      "T'3 3u (RF-MQ-SC-06), règle spéciale")
                else:
                    garde.append(w)
            t["avertissements"][:] = garde

    # ---------------------------------------------------------------- outils communs de construction
    def noeud_reseau(self, modele, nid, position, typ, cid, branches, note):
        routes = []
        for br in branches:
            routes.append(br.rid)
            r = next(x for x in modele["routes"] if x["id"] == br.rid)
            r["noeud_fin" if br.extremite == "fin" else "noeud_debut"] = nid
            if cid:
                r["carrefour_fin" if br.extremite == "fin" else "carrefour_debut"] = cid
        n = {"id": nid, "position": xy_r(position), "type": typ, "routes": sorted(set(routes))}
        if cid:
            n["carrefour"] = cid
        n["prov"] = {"type": P.solveur("reseau", regle="RF-OSM-CAR-001", note=note)}
        modele["noeuds"].append(n)
        return n


# ================================================================================================ objets communs
class ObjetReseau:
    def __init__(self, R, desc, chemin, k):
        self.R, self.desc, self.chemin, self.k = R, desc, chemin, k
        self.ctrl, self.av = [], []
        self.rapport = {"chemin": chemin}

    def extremites_utilisees(self):
        return [(x.nom, x.extremite) for x in getattr(self, "br", [])]

    def evenements(self):
        return []

    def controle(self, nom, valeur, plage, regle, statut=None, **k):
        if statut is None:
            lo, hi = plage
            ok = (lo is None or valeur >= lo - 1e-6) and (hi is None or valeur <= hi + 1e-6)
            statut = "conforme" if ok else "non_conforme"
        c = {"controle": nom, "objet": self.chemin, "valeur": _r(valeur, 3) if isinstance(valeur, float) else valeur,
             "plage": list(plage), "regle": regle, "statut": statut}
        c.update(k)
        self.ctrl.append(c)
        return c

    def conf(self):
        return self.R.d.get("confiance", "moyenne")

    def pd(self, champ, regle=None, note=None):
        return P.description(f"{self.chemin}.{champ}", self.conf(), regle=regle, note=note)


def _prov_reg(regle, note=None, conf=None):
    return P.defaut(regle, conf=conf, note=note)


# ---------------------------------------------------------------- signaux
GAMME_LARGEUR = {"triangle": {"petite": 0.7, "normale": 1.0, "grande": 1.25, "tres_grande": 1.5},
                 "octogone": {"petite": 0.6, "normale": 0.8, "grande": 1.0, "tres_grande": 1.2},
                 "disque": {"petite": 0.65, "normale": 0.85, "grande": 1.05, "tres_grande": 1.25}}
FORME = {"AB3a": "triangle", "AB4": "octogone", "AB25": "triangle", "AB2": "triangle", "B21-1": "disque",
         "B21a1": "disque", "J5": "disque", "J3": "disque", "J14a": "disque", "C24a": "disque"}


def gamme_panneau(ctx, sur_ilot=False):
    """Gamme retenue par le générateur (RF-SV-DIM.CHOIX_GAMME.GENERATEUR)."""
    v = ctx["vitesse_kmh"]
    if sur_ilot:
        return "petite"
    if ctx["categorie"] == "autoroute" or v >= 130:
        return "tres_grande"
    if v >= 110:
        return "grande"
    return "normale"


def signal(sid, famille, code, pos_xy, cap_vise_deg, route, s, cote, regles_l, prov, hauteur=None, gamme=None,
           panonceaux=None, applic=None, support=None, feux=None, t=None):
    sg = {"id": sid, "famille": famille, "code": code}
    if panonceaux:
        sg["panonceaux"] = [{"code": c} for c in panonceaux]
    if gamme:
        sg["gamme"] = gamme
    if support:
        sg["support"] = support
    pos = {"route": route, "s": _r(max(s, 0.0)), "xyz": xy_r(pos_xy), "cote": cote}
    if t is not None:
        pos["t"] = _r(t)
    sg["position"] = pos
    sg["orientation"] = {"azimut_deg": _r((cap_vise_deg + 180.0) % 360.0, 3)}
    if hauteur is not None:
        sg["hauteur_bas_m"] = hauteur
    if applic:
        sg["applicabilite"] = applic
    if feux:
        sg["feux"] = feux
    sg["regles"] = regles_l
    sg["prov"] = prov
    return sg


# ================================================================================================ carrefour plan
REGIMES_BRANCHE = {"prioritaire": "prioritaire", "priorite": "prioritaire", "cedez": "cedez",
                   "cedez le passage": "cedez", "stop": "stop", "feux": "feux", "feu": "feux",
                   "priorite a droite": "priorite_droite", "priorite_droite": "priorite_droite",
                   "sortie seule": "sortie_seule", "sortie_seule": "sortie_seule"}
MOUVEMENTS = ("TD", "TAG", "TAD")


class CarrefourPlan(ObjetReseau):
    def __init__(self, R, desc, chemin, k):
        super().__init__(R, desc, chemin, k)
        _cles(desc, CLES_CARREFOUR, chemin)
        self.id = f"C-{desc.get('id') or k + 1}"
        if not desc.get("centre"):
            raise ErreurReseau(f"{chemin}.centre : position [x, y] du centre à dire")
        self.centre = R.local(desc["centre"], chemin + ".centre")
        self.bdesc = desc.get("branches") or []
        if len(self.bdesc) < 3:
            raise ErreurReseau(f"{chemin}.branches : au moins 3 branches (T) pour un carrefour plan")
        for i, b in enumerate(self.bdesc):
            _cles(b, CLES_BRANCHE, f"{chemin}.branches[{i}]")
        self.idesc = desc.get("ilots") or []
        for i, x in enumerate(self.idesc):
            _cles(x, CLES_ILOT_CARREFOUR, f"{chemin}.ilots[{i}]")
        if desc.get("feux") is not None:
            _cles(desc["feux"], CLES_FEUX, chemin + ".feux")
        if desc.get("guidage") is not None:
            _cles(desc["guidage"], CLES_GUIDAGE, chemin + ".guidage")
        self.rapport.update({"id": self.id, "genre": "carrefour_plan"})

    # ---------------------------------------------------------------- analyse géométrique
    def analyser(self, cap):
        self.cap = cap
        self.br = []
        for i, b in enumerate(self.bdesc):
            c = f"{self.chemin}.branches[{i}]"
            if b.get("troncon") is None:
                raise ErreurReseau(f"{c}.troncon : id du tronçon de la branche à dire")
            x = Branche(str(b["troncon"]), self.R.trinfo(b["troncon"], c, cap), self.centre, c)
            x.desc_b, x.k = b, i
            self.br.append(x)
        self.br.sort(key=lambda x: x.azimut)
        self.agglo = self.br[0].tr.ctx["agglomeration"]
        self.ctx0 = self.br[0].tr.ctx
        # régimes
        reg_c = V.norm(self.desc.get("regime", "")) if self.desc.get("regime") else None
        for x in self.br:
            r = x.desc_b.get("regime")
            if r is None:
                if reg_c == "feux":
                    r = "feux"
                elif reg_c in ("priorite a droite", "priorite_droite"):
                    r = "priorite_droite"
                else:
                    raise ErreurReseau(f"{x.chemin}.regime : régime de la branche à dire (prioritaire, cédez, stop, "
                                       "feux, priorité à droite) ; aucune règle ne le déduit d'une description")
            rn = REGIMES_BRANCHE.get(V.norm(r))
            if rn is None:
                raise ErreurReseau(f"{x.chemin}.regime : « {r} » inconnu ({', '.join(sorted(set(REGIMES_BRANCHE.values())))})")
            if not x.entrantes and rn != "sortie_seule":
                rn = "sortie_seule"
            x.regime = rn
            x.prov_regime = self.pd(f"branches[{x.k}].regime") if x.desc_b.get("regime") else self.pd("regime")
        regs = {x.regime for x in self.br} - {"prioritaire", "sortie_seule"}
        if "feux" in regs:
            self.regime, self.type = "feux", "plan_feux"
        elif regs == {"priorite_droite"}:
            self.regime, self.type = "priorite_droite", "plan_simple"
        elif len(regs) == 1:
            self.regime, self.type = regs.pop(), "plan_simple"
        else:
            self.regime, self.type = "mixte", "plan_simple"
        if self.idesc or any(x.ilot_bande for x in self.br):
            self.type = "plan_ilots" if self.regime != "feux" else "plan_feux"
        if self.desc.get("type"):
            t = V.norm_cle(self.desc["type"])
            if t not in ("plan_simple", "plan_ilots", "plan_feux"):
                raise ErreurReseau(f"{self.chemin}.type : plan_simple, plan_ilots ou plan_feux")
            self.type = t
        self._frontieres()
        self._positions()
        self._coins()

    def _frontieres(self):
        """Limite de la chaussée abordée sur chaque branche : distance au centre, sur l'axe de la branche, du point où
        la chaussée de la branche sort de la chaussée des branches sécantes (bords de chaussée prolongés) ; c'est la
        « limite de la chaussée prioritaire » où se pose la ligne cédez / STOP (DEF-012, ARB-02, RF-MQ-STOP-04)."""
        for x in self.br:
            d = 0.0
            for y in self.br:
                if y is x:
                    continue
                a = abs(norm180(x.azimut - y.azimut))
                if a < 20.0 or a > 160.0:
                    continue
                for wx in (x.w_g, x.w_d):
                    for wy in (y.w_g, y.w_d):
                        p = inter_lignes(x.pt(0, wx), x.u, y.pt(0, wy), y.u)
                        if p is not None:
                            d = max(d, (p[0] - x.pe[0]) * x.u[0] + (p[1] - x.pe[1]) * x.u[1])
            x.d_front = d

    def _positions(self):
        """Lignes transversales, passages, sas, le long de chaque branche (distances au centre)."""
        retrait_pp = regles.valeur("DEF-012", "passage_en_retrait")
        larg_ligne = regles.valeur("RF-MQ-CED-01", "largeur")
        for x in self.br:
            b = x.desc_b
            x.ligne = None
            x.passage = None
            x.sas = None
            x.ligne_effet_peinte = False
            pp = b.get("passage")
            veut_pp = pp is not None and (isinstance(pp, dict) or _b(pp, f"{x.chemin}.passage"))
            ppd = pp if isinstance(pp, dict) else {}
            if isinstance(pp, dict):
                _cles(ppd, {"largeur", "retrait", "note"}, f"{x.chemin}.passage")
            w_pp = _v(ppd["largeur"], f"{x.chemin}.passage.largeur") if ppd.get("largeur") is not None else \
                regles.valeur("DEF-011", "longueur_bandes_ville")
            x.pp_largeur_dite = ppd.get("largeur") is not None
            ret = _v(ppd["retrait"], f"{x.chemin}.passage.retrait") if ppd.get("retrait") is not None else retrait_pp
            x.pp_retrait_dit = ppd.get("retrait") is not None
            d0 = x.d_front
            if x.regime in ("cedez", "stop"):
                x.ligne = {"type": "CEDEZ" if x.regime == "cedez" else "STOP", "x0": d0, "x1": d0 + larg_ligne}
                if veut_pp:
                    x.passage = {"x0": d0 + larg_ligne + ret, "largeur": w_pp, "retrait": ret}
            elif x.regime == "feux":
                if veut_pp:
                    x.passage = {"x0": d0 + ret, "largeur": w_pp, "retrait": ret}
                sas = b.get("sas") is not None and _b(b["sas"], f"{x.chemin}.sas")
                lep = sas or (b.get("ligne_effet") is not None and _b(b["ligne_effet"], f"{x.chemin}.ligne_effet"))
                x.ligne_effet_peinte = lep
                base = (x.passage["x0"] + w_pp) if x.passage else d0
                if lep:
                    recul = regles.valeur("DEF-015", "recul_passage") if x.passage else 0.0
                    xe = base + recul
                    if sas:
                        if not x.cyclables_entrantes:
                            self.av.append(f"{x.chemin} : sas vélo sans bande cyclable d'accès (RF-MQ-SAS-01 : possible "
                                           "seulement si impossibilité technique)")
                        prof = regles.valeur("DEF-016")
                        x.sas = {"x_avant": xe, "x_arriere": xe + prof, "profondeur": prof}
                        x.ligne = {"type": "EFFET_FEUX", "x0": xe + prof, "x1": xe + prof + 0.15}
                    else:
                        x.ligne = {"type": "EFFET_FEUX", "x0": xe, "x1": xe + 0.15}
                else:
                    x.ligne = {"type": "virtuelle", "x0": base, "x1": base}
            elif x.regime in ("prioritaire", "priorite_droite"):
                if veut_pp:
                    x.passage = {"x0": d0 + ret, "largeur": w_pp, "retrait": ret}
            elif veut_pp:
                x.passage = {"x0": d0 + ret, "largeur": w_pp, "retrait": ret}
            if x.passage:
                x.passage["x1"] = x.passage["x0"] + x.passage["largeur"]
                x.passage["xc"] = x.passage["x0"] + x.passage["largeur"] / 2
                x.passage["s"] = x.s_de_x(x.passage["xc"])

    def _coins(self):
        """Coins (raccords de bordure) entre chaque branche et la suivante dans le sens trigonométrique : arc de rayon
        R tangent aux deux bords de chaussée (schéma : coin_droit) ; îlot directionnel de tourne-à-droite éventuel."""
        n = len(self.br)
        dirs = {}
        for i, x in enumerate(self.idesc):
            c = f"{self.chemin}.ilots[{i}]"
            if V.norm(x.get("type", "")) not in ("directionnel", "ilot directionnel", "tourne a droite"):
                raise ErreurReseau(f"{c}.type : « directionnel » (îlot directionnel de tourne-à-droite) ; les îlots "
                                   "séparateurs et de TAG se décrivent dans le profil des branches (terre-plein)")
            de, vers = str(x.get("de")), str(x.get("vers"))
            dirs[(de, vers)] = (x, c)
        self.coins = []
        for k, x in enumerate(self.br):
            y = self.br[(k + 1) % n]
            a = (y.azimut - x.azimut) % 360.0
            co = {"de": x, "vers": y, "angle": a, "ilot": None}
            # rayon
            rd = x.desc_b.get("coin")
            dirdesc = dirs.pop((x.nom, y.nom), None)
            if dirdesc is not None:
                xd, c = dirdesc
                if xd.get("rayon") is None or xd.get("largeur_voie") is None:
                    raise ErreurReseau(f"{c} : rayon de la bordure du shunt et largeur de la voie directe à dire "
                                       "(RF-GV-VS-017 : R = 25 m, 4,00 m sur artère 70 km/h)")
                co["rayon"] = _v(xd["rayon"], c + ".rayon")
                co["prov_rayon"] = P.description(c + ".rayon", self.conf(), regle="RF-GV-VS-017")
                co["ilot"] = {"desc": xd, "chemin": c, "W": _v(xd["largeur_voie"], c + ".largeur_voie")}
            elif rd is not None:
                co["rayon"] = _v(rd, f"{x.chemin}.coin")
                co["prov_rayon"] = P.description(f"{x.chemin}.coin", self.conf(), regle="DEF-010")
            elif a > 179.0:
                co["rayon"] = None             # pas de coin (branche suivante dans le prolongement ou au-delà)
            elif self.agglo:
                co["rayon"] = float(regles.valeur("DEF-010", "bus_PL_occasionnels"))
                co["prov_rayon"] = P.defaut("DEF-010", note="rayon d'angle bus / PL occasionnels (8 m ; 6-8 m aux feux)")
            else:
                raise ErreurReseau(f"{x.chemin}.coin : rayon d'angle à dire hors agglomération (aucune règle de la base "
                                   "ne le fixe seul ; RF-GV-RAY-001 périurbain PL 8-12 m)")
            if co.get("rayon"):
                self._geo_coin(co)
            self.coins.append(co)
        for (de, vers), (xd, c) in dirs.items():
            raise ErreurReseau(f"{c} : pas de coin entre « {de} » et « {vers} » (branches consécutives dans le sens "
                               "trigonométrique, tourne-à-droite de « de » vers « vers »)")

    def _geo_coin(self, co):
        x, y, R = co["de"], co["vers"], co["rayon"]
        A, B = x.pt(0, x.w_g), y.pt(0, y.w_d)
        Pc = inter_lignes(A, x.u, B, y.u)
        if Pc is None:
            co["rayon"] = None
            return
        # centre : à distance R des deux bords, du côté extérieur (hors chaussées)
        ca = (Pc[0] + R * x.n[0], Pc[1] + R * x.n[1])
        cb_n = (-y.n[0], -y.n[1])
        C = inter_lignes((A[0] + R * x.n[0], A[1] + R * x.n[1]), x.u, (B[0] + R * cb_n[0], B[1] + R * cb_n[1]), y.u)
        Ti = (C[0] - R * x.n[0], C[1] - R * x.n[1])
        Tk = (C[0] - R * cb_n[0], C[1] - R * cb_n[1])
        co.update(P=Pc, C=C, Ti=Ti, Tk=Tk,
                  xi=(Ti[0] - x.pe[0]) * x.u[0] + (Ti[1] - x.pe[1]) * x.u[1],
                  xk=(Tk[0] - y.pe[0]) * y.u[0] + (Tk[1] - y.pe[1]) * y.u[1])
        a0, a1 = ang((Ti[0] - C[0], Ti[1] - C[1])), ang((Tk[0] - C[0], Tk[1] - C[1]))
        # arc du côté du carrefour (le plus court entre Ti et Tk)
        da = norm180(a1 - a0)
        co["arc"] = arc_pts(C, R, a0, a0 + da)
        co["a0"], co["da"] = a0, da

    # ---------------------------------------------------------------- évènements posés aux tronçons
    def evenements(self):
        out = []
        for x in self.br:
            if x.passage:
                ev = {"type": "passage_pieton", "a": _r(x.passage["s"], 3), "_chemin": f"{x.chemin}.passage"}
                if x.pp_largeur_dite:
                    ev["largeur"] = x.passage["largeur"]
                else:
                    ev["largeur"] = x.passage["largeur"]
                    ev["_prov_largeur"] = P.defaut("DEF-011", note="longueur des bandes du passage de carrefour")
                if x.regime == "feux":
                    ev["regime"] = "feux"
                out.append((x.nom, ev))
        return out

    # ---------------------------------------------------------------- construction des objets du modèle
    def construire(self, R, modele, ctxh):
        tous = ctxh["tous"]
        cid = self.id
        u_m = self.ctx0["u"]
        nid = f"N-{cid}"
        R.noeud_reseau(modele, nid, self.centre, "carrefour", cid, self.br,
                       note=f"carrefour décrit : {len(self.br)} branches rejoignant le centre")
        prov = {"type": self.pd("branches", regle="RF-OSM-CAR-001", note=f"{len(self.br)} branches décrites ; type {self.type}"),
                "regime": self.pd("regime") if self.desc.get("regime") else P.solveur("regime", regle="RF-OSM-CAR-011",
                                                                                     note="régime déduit des régimes de branche décrits")}
        branches, signaux, marquages, ilots, passages = [], [], [], [], []
        self.signaux, self.marquages, self.ilots_out = signaux, marquages, ilots
        rap_b = {}
        for x in self.br:
            bid = f"B-{x.nom}"
            x.bid = bid
            bo = {"id": bid, "route": x.rid, "extremite": x.extremite, "azimut_deg": _r(x.azimut, 3),
                  "bandes_entrantes": [b["id"] for b in x.entrantes], "bandes_sortantes": [b["id"] for b in x.sortantes],
                  "regime": x.regime, "s_frontiere_m": _r(x.s_de_x(x.d_front))}
            prov[f"branches[{bid}].regime"] = x.prov_regime
            if x.ligne and x.ligne["type"] != "virtuelle":
                la = {"type": x.ligne["type"], "distance_m": _r(x.ligne["x0"] - x.d_front),
                      "bandes": [b["id"] for b in x.entrantes]}
                if x.ligne["type"] in ("CEDEZ", "STOP"):
                    la.update(largeur_m=regles.valeur("RF-MQ-CED-01", "largeur"),
                              modulation="T'2" if x.ligne["type"] == "CEDEZ" else "continue",
                              regle="RF-MQ-CED-01" if x.ligne["type"] == "CEDEZ" else "RF-MQ-STOP-01")
                    prov[f"branches[{bid}].ligne_arret"] = P.defaut("DEF-012", note="ligne à la limite de la chaussée "
                                                                                    "prioritaire (0 m), ARB-02")
                else:
                    la.update(largeur_m=regles.valeur("RF-MQ-FEU-01", "largeur"), modulation="T'2", regle="RF-MQ-FEU-01")
                    prov[f"branches[{bid}].ligne_arret"] = P.defaut(
                        "DEF-015", note="ligne d'effet peinte (sas ou dite) à 3,0 m en amont du passage (ARB-01)"
                        + (" ; ligne des véhicules au fond du sas de 4 m (DEF-016)" if x.sas else ""))
                bo["ligne_arret"] = la
                marquages += self._marque_transversale(x, la, u_m)
            elif x.ligne and x.ligne["type"] == "virtuelle":
                bo["ligne_arret"] = {"type": "virtuelle", "distance_m": _r(x.ligne["x0"] - x.d_front),
                                     "bandes": [b["id"] for b in x.entrantes], "regle": "ARB-01"}
                prov[f"branches[{bid}].ligne_arret"] = P.defaut("ARB-01", note="ligne d'effet non peinte : le passage "
                                                                             "piéton tient lieu de ligne d'arrêt")
            # continue axiale d'approche (double sens sans îlot, cédez / STOP) : DEF-013
            if x.regime in ("cedez", "stop") and x.entrantes and x.sortantes and x.ilot_bande is None:
                lg = float(regles.valeur("DEF-013"))
                bo["ligne_axiale_approche"] = {"modulation": "continue", "largeur_u": 2, "longueur_m": lg,
                                               "regle": "RF-MQ-STOP-03"}
                prov[f"branches[{bid}].ligne_axiale_approche"] = P.defaut("DEF-013", note="continue 2u sur 15 m")
                self._axe_continue(x, lg)
            if x.passage:
                ppid = f"PP-{self.id[2:]}.{x.nom}"
                x.passage["id"] = ppid
                bo["passage_pieton"] = ppid
                passages.append(self._passage(x, ppid))
            if x.sas:
                bo["sas_velo"] = {"profondeur_m": x.sas["profondeur"], "regle": "RF-MQ-SAS-01"}
                if x.cyclables_entrantes:
                    bo["sas_velo"]["bande_acces"] = x.cyclables_entrantes[0]["id"]
                prov[f"branches[{bid}].sas_velo"] = P.defaut("DEF-016", note="sas de 4 m")
                marquages += self._marques_sas(x, u_m)
            co = next(c for c in self.coins if c["de"] is x)
            if co.get("rayon"):
                bo["coin_droit"] = {"rayon_m": _r(co["rayon"]), "forme": "arc", "regle": "DEF-010"}
                prov[f"branches[{bid}].coin_droit"] = co["prov_rayon"]
            fl = self._fleches(x, u_m)
            if fl:
                bo["fleches"] = [{"bande": b, "types": [t], "nombre": len(p), "intervalle_m": regles.valeur("DEF-017", "interdistance"),
                                  "recul_derniere_m": regles.valeur("DEF-017", "pointe_derniere"), "regle": "RF-MQ-DIR-03"}
                                 for b, t, p in fl]
                prov[f"branches[{bid}].fleches"] = P.defaut("DEF-017", note="3 flèches au pas de 20 m, pointe de la "
                                                                            "dernière à 1,50 m de la ligne")
            branches.append(bo)
            rap_b[x.nom] = {"frontiere_m": _r(x.d_front, 3), "regime": x.regime,
                            "ligne": None if not x.ligne else {"type": x.ligne["type"], "x0_m": _r(x.ligne["x0"], 3),
                                                               "s": _r(x.s_de_x(x.ligne["x0"]), 3)},
                            "passage": None if not x.passage else {"x0_m": _r(x.passage["x0"], 3), "largeur_m": x.passage["largeur"],
                                                                   "s": _r(x.passage["s"], 3)},
                            "sas": x.sas and {k: _r(v, 3) for k, v in x.sas.items()},
                            "largeur_chaussee_m": _r(x.largeur_chaussee(), 3),
                            "entrantes": [b["id"] for b in x.entrantes], "sortantes": [b["id"] for b in x.sortantes]}
        # îlots : terre-pleins à l'extrémité des branches (TPC, îlots séparateurs, îlots de TAG) et îlots directionnels
        for x in self.br:
            x.ilots_ent = {}
            for bd in x.ilots_bandes:
                il = self._ilot_profil(x, bd)
                if il:
                    ilots.append(il)
                    x.ilots_ent[bd["id"]] = il
                    if bd is x.ilot_bande:
                        bo = next(b for b in branches if b["id"] == x.bid)
                        bo["ilot_separateur"] = il["id"]
        for co in self.coins:
            if co.get("ilot"):
                ilots += self._ilot_directionnel(co, branches, prov)
        # trajectoires, conflits, guidage
        traj = self._trajectoires(branches)
        self._usagers(traj)
        guid = self._guidage(traj, marquages, u_m)
        conflits = self._conflits(traj)
        prov["trajectoires"] = P.solveur("trajectoires", regle="RF-GV-TRJ-006",
                                         note="droite – arc tangent – droite le long des axes de voie ; rayon = plus "
                                              "grand arc tangent aux deux axes entre les frontières")
        # zone de conflit et frontière
        zc = self._zone_conflit()
        frontiere = [{"type": "joint", "route": x.rid, "extremite": x.extremite, "s0": _r(x.s_de_x(x.d_front)),
                      "s1": _r(x.s_de_x(x.d_front))} for x in self.br]
        c = {"id": cid, "type": self.type, "regime": self.regime, "noeuds": [nid], "centre": xy_r(self.centre),
             "branches": branches, "zone_conflit": poly_schema(zc), "frontiere": frontiere}
        if ilots:
            c["ilots"] = [i["id"] for i in ilots]
        c["trajectoires"] = traj
        if conflits:
            c["conflits"] = conflits
        if passages:
            c["passages_pieton"] = passages
        # feux
        if self.regime == "feux":
            ctrl_id = self._feux(c, traj, signaux, tous, modele)
            if ctrl_id:
                c["controleur"] = ctrl_id
        else:
            self._panneaux(c, signaux)
        c["regles"] = ["RF-OSM-CAR-001", "DEF-012", "ARB-02", "RF-GV-TRJ-001", "RF-GV-TRJ-006", "RF-MQ-CAR-02",
                       "RF-MQ-CAR-04"] + (["RF-GV-FEU-001", "DEF-028"] if self.regime == "feux" else [])
        c["prov"] = {k: prov[k] for k in sorted(prov, key=lambda k: (not k.startswith(("type", "regime")), k))}
        modele["carrefours"].append(c)
        for b in c["branches"]:
            sids = [s["id"] for s in signaux if (s.get("applicabilite") or {}).get("branche") == b["id"]]
            if sids:
                b["signaux"] = sids
        tous["signaux"] += signaux
        tous["marquages"] += marquages
        tous["ilots"] += ilots
        # contrôles du carrefour
        self._controles(c, traj, conflits, zc)
        self.rapport.update({"branches": rap_b, "zone_conflit_m2": _r(zc.area, 2),
                             "trajectoires": len(traj), "mouvements": sorted(t["id"] for t in traj),
                             "conflits": self.compte_conflits, "ilots": [i["id"] for i in ilots],
                             "signaux": sorted({s["code"] for s in signaux}), "nb_signaux": len(signaux),
                             "passages": [p["id"] for p in passages], "guidage": guid})

    # ---------------------------------------------------------------- marques
    def _marque_transversale(self, x, la, u_m):
        """Une ligne par couloir (voies entrantes contiguës, sans îlot entre elles) : jamais sur un îlot."""
        xm = (x.ligne["x0"] + x.ligne["x1"]) / 2
        out = []
        gab = {"CEDEZ": "CEDEZ", "STOP": "STOP", "EFFET_FEUX": "EFFET_FEUX"}[la["type"]]
        for k, (voies, _, _) in enumerate(self._couloirs(x)):
            bs = [x.bande(v) for v in voies]
            wa, wb = min(b["w0"] for b in bs), max(b["w1"] for b in bs)
            if k == len(self._couloirs(x)) - 1 and x.sas:
                wb = max([wb] + [b["w1"] for b in x.cyclables_entrantes])
            out.append({"id": f"M-{self.id[2:]}.{x.nom}.ligne{'' if k == 0 else k + 1}", "type": "ligne_transversale",
                        "gabarit": gab,
                        "ancrage": {"route": x.rid, "s": _r(x.s_de_x(xm)), "carrefour": self.id, "branche": x.bid},
                        "geometrie": [xy_r(x.pt(xm, wa)), xy_r(x.pt(xm, wb))], "couleur": "blanc",
                        "regles": [la["regle"], "DEF-012" if la["type"] != "EFFET_FEUX" else "DEF-015"],
                        "prov": {"*": P.solveur("lignes_transversales", regle=la["regle"],
                                                note=f"largeur {la['largeur_m']} m, modulation {la['modulation']}, sur les "
                                                     f"voies {'+'.join(voies)}")}})
        return out

    def _marques_sas(self, x, u_m):
        """Sas sur le couloir de droite (celui qu'atteint la bande cyclable d'accès) : RF-MQ-SAS-01."""
        out = []
        voies = self._couloirs(x)[-1][0]
        bs = [x.bande(v) for v in voies]
        wa = min(b["w0"] for b in bs)
        wb = max([b["w1"] for b in bs] + [b["w1"] for b in x.cyclables_entrantes])
        x_lig = (x.ligne["x0"] + x.ligne["x1"]) / 2 if x.ligne else None
        for nom, xx in (("avant", x.sas["x_avant"] + 0.075), ("arriere", x.sas["x_arriere"] + 0.075)):
            if nom == "arriere" and x_lig is not None and abs(xx - x_lig) < 1e-6:
                # la ligne d'effet du couloir du sas (_marque_transversale, prolongée sur la bande cyclable) EST la ligne
                # arrière du sas : pas de seconde ligne au même endroit (correction après le contrôle de l'étape 2 :
                # ligne2 et sas_arriere de J5 superposées, 16 tirets, 1,18 m²)
                continue
            out.append({"id": f"M-{self.id[2:]}.{x.nom}.sas_{nom}", "type": "ligne_transversale", "gabarit": "EFFET_FEUX",
                        "ancrage": {"route": x.rid, "s": _r(x.s_de_x(xx)), "carrefour": self.id, "branche": x.bid},
                        "geometrie": [xy_r(x.pt(xx, wa)), xy_r(x.pt(xx, wb))], "couleur": "blanc",
                        "regles": ["RF-MQ-SAS-01", "RF-MQ-FEU-01", "DEF-016"],
                        "prov": {"*": P.defaut("DEF-016", note=f"ligne {nom} du sas : T'2 0,15 (RF-MQ-SAS-01)")}})
        xm = (x.sas["x_avant"] + x.sas["x_arriere"]) / 2
        for b in bs:
            wm = (b["w0"] + b["w1"]) / 2
            out.append({"id": f"M-{self.id[2:]}.{x.nom}.sas_velo_{b['id']}", "type": "figurine_velo", "gabarit": "VELO",
                        "ancrage": {"route": x.rid, "bande": b["id"], "s": _r(x.s_de_x(xm)), "t": _r(x.t_route(wm)),
                                    "cap_deg": _r(ang((-x.u[0], -x.u[1])), 3), "carrefour": self.id, "branche": x.bid},
                        "couleur": "blanc", "regles": ["RF-MQ-SAS-01"],
                        "prov": {"*": P.defaut("RF-MQ-SAS-01", note="figurine dans l'axe de chaque voie du sas")}})
        out.append({"id": f"M-{self.id[2:]}.{x.nom}.sas", "type": "sas_velo",
                    "ancrage": {"route": x.rid, "s": _r(x.s_de_x(xm)), "carrefour": self.id, "branche": x.bid},
                    "geometrie": {"exterieur": anneau([x.pt(x.sas["x_avant"], wa), x.pt(x.sas["x_avant"], wb),
                                                       x.pt(x.sas["x_arriere"], wb), x.pt(x.sas["x_arriere"], wa)])},
                    "couleur": "blanc", "regles": ["RF-MQ-SAS-01", "DEF-016"],
                    "prov": {"*": P.defaut("DEF-016", note="emprise du sas (profondeur 4 m) sur les voies gérées par le feu")}})
        return out

    def _fleches(self, x, u_m):
        """Flèches directionnelles des branches à voies affectées (voie de TAG ou de TAD, ou flèches dites) :
        3 par voie au pas de 20 m, pointe de la dernière à 1,50 m de la ligne (DEF-017, RF-MQ-DIR-03/-04)."""
        fl = x.desc_b.get("fleches")
        if fl is not None and not isinstance(fl, dict) and not _b(fl, f"{x.chemin}.fleches"):
            return []
        aff = any(b["type"] in ("voie_tourne_gauche", "voie_tourne_droite") for b in x.entrantes)
        if not aff and not isinstance(fl, dict) and fl is None:
            return []
        mv = self._mouvements_voies(x)
        L = regles.valeur("DEF-017", "longueur")
        pas = regles.valeur("DEF-017", "interdistance")
        rec = regles.valeur("DEF-017", "pointe_derniere")
        nb = regles.valeur("DEF-017", "nombre_par_voie")
        x_ligne = x.ligne["x1"] if x.ligne else x.d_front
        out = []
        for b in x.entrantes:
            ms = [m for m in mv.get(b["id"], []) if m in MOUVEMENTS]
            typ = "_".join(sorted(ms, key=lambda m: MOUVEMENTS.index(m))) if ms else None
            if typ not in regles.valeur("RF-MQ-DIR-02", "types"):
                continue
            pos = []
            for k in range(nb):
                xc = x_ligne + rec + L / 2 + k * pas
                s = x.s_de_x(xc)
                if not (0.0 <= s <= x.tr.L):
                    break
                p = x.tr.profil_a(s)
                if b["id"] not in [bb["id"] for bb in p["bandes"]]:
                    break
                T = D.t_limites(p, s)
                kk = [bb["id"] for bb in p["bandes"]].index(b["id"])
                pos.append(xc)
                self.marquages.append({
                    "id": f"M-{self.id[2:]}.{x.nom}.fl_{b['id']}_{k + 1}", "type": "fleche", "gabarit": typ,
                    "ancrage": {"route": x.rid, "bande": b["id"], "s": _r(s), "t": _r((T[kk] + T[kk + 1]) / 2),
                                "cap_deg": _r(ang((-x.u[0], -x.u[1])), 3), "carrefour": self.id, "branche": x.bid},
                    "couleur": "blanc", "regles": ["RF-MQ-DIR-02", "RF-MQ-DIR-03", "RF-MQ-DIR-04", "RF-MQ-DIR-09", "DEF-017"],
                    "prov": {"*": P.defaut("DEF-017", note=f"flèche {k + 1} de {nb} ; longueur {L} m (RF-MQ-DIR-09)")}})
            if pos:
                out.append((b["id"], typ, pos))
        if out:
            self.av.append(f"{x.chemin} : voies affectées (flèches) : panneau C24a/b ou Da30 obligatoire (RF-MQ-DIR-01), "
                           "posé au lot L6")
        return out

    def _axe_continue(self, x, lg):
        tr = x.tr
        xa = x.ligne["x1"]
        s0, s1 = sorted((x.s_de_x(xa), x.s_de_x(xa + lg)))
        tr.decos.append({"type": "interruption", "s0": s0, "s1": s1, "cible": "axe", "motif": "autre"})
        tr.decos.append({"type": "marque", "s0": s0, "s1": s1, "cible": "axe",
                         "marque": PF.marque("continue", 2, tr.ctx, "RF-MQ-STOP-03")})
        tr._decorer()

    # ---------------------------------------------------------------- passages
    def _passage(self, x, ppid):
        p = x.passage
        pp = {"id": ppid, "route": x.rid, "s": _r(p["s"]),
              "axe": [xy_r(x.pt(p["xc"], x.w_d - 1.0)), xy_r(x.pt(p["xc"], x.w_g + 1.0))],
              "largeur_m": p["largeur"], "regime": "feux" if x.regime == "feux" else "non_gere",
              "abaisses": True, "bev": True}
        if x.ilot_bande is not None:
            pp["refuge"] = f"I-{self.id[2:]}.{x.nom}"
        pp["prov"] = {"*": P.description(f"{x.chemin}.passage", self.conf(), regle="DEF-012",
                                         note=f"passage en retrait de {p['retrait']} m (DEF-012, ARB-02) de la ligne"
                                              f"{' / de la zone de conflit (RF-GV-PIE-006)' if x.regime != 'cedez' and x.regime != 'stop' else ''}"),
                      "largeur_m": P.description(f"{x.chemin}.passage.largeur") if x.pp_largeur_dite else
                      P.defaut("DEF-011", note="longueur des bandes")}
        # traversée hors refuge (RF-GV-PIE-010 : ≤ 12 m, bloquant)
        groupes, prof, T = x.tr.chaussees(p["s"])
        larg = [tg - td for tg, td, _ in groupes]
        self.controle("traversee_hors_refuge", max(larg), (None, regles.valeur("RF-GV-PIE-010", "traversee_max")),
                      "RF-GV-PIE-010", passage=ppid, troncons=[round(v, 2) for v in larg])
        return pp

    # ---------------------------------------------------------------- îlots
    def _ilot_profil(self, x, b):
        """Îlot porté par le profil de la branche (terre-plein entre voies à l'extrémité : TPC, îlot séparateur, îlot
        de TAG) : entité îlot (refuge, nez, balise, signaux portés) dont le polygone est l'empreinte de la bande sur les
        sections contiguës de même profil que l'extrémité ; la bande du profil fabrique la géométrie (champ
        porte_par_profil, à ne pas refabriquer)."""
        tr = x.tr
        # étendue : sections contiguës de même profil que l'extrémité (îlot de carrefour, pas le TPC courant)
        secs = list(reversed(tr.secs)) if x.extremite == "fin" else list(tr.secs)
        s_lim = None
        p_ext = secs[0]["profil"]
        for sec in secs:
            if sec["profil"] != p_ext:
                break
            s_lim = sec["s0"] if x.extremite == "fin" else sec["s1"]
        x0 = abs(x.s_ext - s_lim)                      # distance au centre du bout amont de l'îlot
        x1 = x.d_front                                 # l'îlot s'arrête à la frontière (le solveur le coupe)
        if x0 <= x1 + 0.5:
            self.av.append(f"{x.chemin} : le terre-plein {b['id']} ne dépasse pas la limite de la chaussée abordée")
            return None
        pts = []
        n = 12
        for k in range(n + 1):
            xx = x1 + (x0 - x1) * k / n
            s = x.s_de_x(xx)
            p = tr.profil_a(s)
            T = D.t_limites(p, s)
            ids = [bb["id"] for bb in p["bandes"]]
            if b["id"] not in ids:
                continue
            i = ids.index(b["id"])
            pts.append((xx, x.sg * T[i], x.sg * T[i + 1]))
        gauche = [x.pt_route(xx, max(wa, wb)) for xx, wa, wb in pts]
        droite = [x.pt_route(xx, min(wa, wb)) for xx, wa, wb in pts]
        poly = Polygon(gauche + droite[::-1])
        bd = b["b"]
        tp = copy.deepcopy(bd.get("terre_plein") or {"franchissable": "non"})
        tp.setdefault("surelevation_m", bd["niveau"]["dz_m"])
        larg = b["w1"] - b["w0"]
        entre_sens = b is x.ilot_bande
        sous = (b["b"].get("sous_type") or "")
        typ = "terre_plein_central" if sous == "terre_plein_central" else "separateur"
        iid = f"I-{self.id[2:]}.{x.nom}" + ("" if entre_sens else f".{b['id']}")
        il = {"id": iid, "type": typ, "polygone": poly_schema(poly),
              "carrefour": self.id, "terre_plein": tp,
              "porte_par_profil": {"route": x.rid, "bande": b["id"], "s0": _r(min(x.s_de_x(x0), x.s_de_x(x1))),
                                   "s1": _r(max(x.s_de_x(x0), x.s_de_x(x1)))}}
        if x.passage and x.passage["x1"] <= x0 + 1e-6:
            il["refuge"] = {"largeur_m": _r(larg), "traversee": f"PP-{self.id[2:]}.{x.nom}", "abaisses": True, "bev": True}
            self.controle("refuge_largeur", larg, (regles.valeur("DEF-022", "largeur"), None), "DEF-022",
                          ilot=il["id"])
        # nez côté carrefour : balise J5 (îlot en saillie, RF-SV-J5) si l'îlot est assez large (RF-GV-ILO-008)
        nez = x.pt((x1 + 0.0), (b["w0"] + b["w1"]) / 2)
        il["nez"] = [{"position": xy_r(nez), "rayon_m": _r(min(larg / 2, 0.5)), "balise": "J5" if larg >= regles.valeur("RF-GV-ILO-008", "largeur_min") - 1e-6 else "aucune"}]
        il["prov"] = {"*": P.solveur("ilots", regle="RF-GV-CAR-008",
                                     note="empreinte du terre-plein décrit dans le profil de la branche, jusqu'à la "
                                          "limite de la chaussée abordée ; porté par le profil")}
        self.controle("ilot_surface", poly.area, (regles.valeur("RF-GV-CAR-008", "surface_min_m2"), None),
                      "RF-GV-CAR-008", ilot=il["id"])
        return il

    def _ilot_directionnel(self, co, branches, prov):
        """Îlot directionnel de tourne-à-droite avec voie directe (shunt) : bord de la voie directe = arc de rayon R
        tangent aux bords de chaussée des deux branches (coin), voie de largeur W, îlot = zone d'angle au-delà de
        R + W, en saillie à 0,50 m de l'enveloppe peinte, nez arrondis de 0,50 m (RF-GV-ILO-013, -015 ; RF-GV-VS-017)."""
        x, y = co["de"], co["vers"]
        W, R_ = co["ilot"]["W"], co["rayon"]
        c = co["ilot"]["chemin"]
        C = co["C"]
        tri = Polygon([co["P"], co["Ti"], *co["arc"][1:-1], co["Tk"]]).buffer(0)
        disque = Point(C).buffer(R_ + W, quad_segs=64)
        env = tri.difference(disque)
        if env.is_empty:
            raise ErreurReseau(f"{c} : rayon {R_} + voie {W} : pas de place pour un îlot dans l'angle")
        if env.geom_type == "MultiPolygon":
            env = max(env.geoms, key=lambda g: g.area)
        ret = regles.valeur("RF-GV-ILO-015", "retrait_saillie")
        nez = regles.valeur("RF-GV-ILO-015", "nez")[0]
        raised = arrondir_sommets(env.buffer(-ret, join_style="mitre"), nez)
        iid = f"I-{self.id[2:]}.dir_{x.nom}_{y.nom}"
        rem = co["ilot"]["desc"].get("remplissage")
        rem_t = {"type": "beton", "materiau_id": "beton_balaye"} if rem is None else None
        if rem is not None:
            m = V.MATERIAUX.get(V.norm(rem))
            if m is None or isinstance(m, dict):
                raise ErreurReseau(f"{c}.remplissage : matériau inconnu « {rem} »")
            rem_t = {"type": {"gazon_tondu": "gazon", "paves_beton": "paves", "beton_balaye": "beton"}.get(m, "beton"),
                     "materiau_id": m}
        il = {"id": iid, "type": "directionnel", "polygone": poly_schema(raised), "carrefour": self.id,
              "terre_plein": {"franchissable": "non", "surelevation_m": regles.valeur("DEF-005", "ilot"),
                              "ceinture": {"profil": "I2", "vue_m": regles.valeur("DEF-005", "ilot")},
                              "remplissage": rem_t,
                              "marquage_contour": {"modulation": "continue", "largeur_u": 3, "retrait_u": 2}}}
        # nez côté branche de départ et côté branche d'arrivée
        cs = list(raised.exterior.coords)
        nez_i = min(cs, key=lambda p: Point(p).distance(Point(co["Ti"])))
        nez_k = min(cs, key=lambda p: Point(p).distance(Point(co["Tk"])))
        il["nez"] = [{"position": xy_r(nez_i), "rayon_m": nez, "balise": "J5"},
                     {"position": xy_r(nez_k), "rayon_m": nez, "balise": "aucune"}]
        il["prov"] = {"*": P.solveur("ilot_directionnel", regle="RF-GV-ILO-015",
                                     note=f"voie directe R = {R_} m, largeur {W} m ({c}) ; saillie {ret} m ; nez {nez} m")}
        larg_min = 2 * raised.area / max(raised.length / 2, 1e-6)
        self.controle("ilot_directionnel_surface", raised.area, (regles.valeur("RF-GV-ILO-015", "surface_min_m2"), None),
                      "RF-GV-ILO-015", ilot=iid)
        out = [il]
        # enveloppe peinte (contour continue 3u)
        co["ilot"].update(env=env, raised=raised, id=iid, C=C, R=R_, W=W)
        # voie directe : ligne cédez au débouché sur la branche d'arrivée, AB3a sur l'îlot (IISR3 art. 42-9)
        reg = V.norm(co["ilot"]["desc"].get("regime", "cedez"))
        if reg not in ("cedez", "cedez le passage"):
            raise ErreurReseau(f"{c}.regime : la voie directe de tourne-à-droite est en cédez le passage (RF-SV-AB3A, "
                               "IISR3 art. 42-9) dans le format")
        a_fin = co["a0"] + co["da"]
        # angle où l'îlot finit côté branche d'arrivée : projection du nez k sur le cercle
        ak = ang((nez_k[0] - C[0], nez_k[1] - C[1]))
        p1 = (C[0] + R_ * math.cos(math.radians(ak)), C[1] + R_ * math.sin(math.radians(ak)))
        p2 = (C[0] + (R_ + W) * math.cos(math.radians(ak)), C[1] + (R_ + W) * math.sin(math.radians(ak)))
        self.marquages.append({"id": f"M-{self.id[2:]}.dir_{x.nom}_{y.nom}.cedez", "type": "ligne_transversale",
                               "gabarit": "CEDEZ", "ancrage": {"carrefour": self.id, "branche": x.bid},
                               "geometrie": [xy_r(p1), xy_r(p2)], "couleur": "blanc",
                               "regles": ["RF-MQ-CED-01", "RF-SV-AB3A.POSITION"],
                               "prov": {"*": P.solveur("ilot_directionnel", regle="RF-MQ-CED-01",
                                                       note="ligne T'2 0,50 au débouché de la voie directe, au droit du nez de l'îlot")}})
        h = regles.valeur("DEF-025", "hauteur_trottoir_agglo" if self.agglo else "hauteur_rase_campagne")
        cen = raised.centroid.coords[0]
        dv = unit(cen[0] - nez_k[0], cen[1] - nez_k[1])
        pab = (nez_k[0] + 1.0 * dv[0], nez_k[1] + 1.0 * dv[1])
        if not raised.contains(Point(pab)):
            pab = raised.representative_point().coords[0]
        self.signaux.append(signal(f"SG-{self.id[2:]}.dir_{x.nom}.AB3a", "panneau", "AB3a", pab, ak + 90.0, x.rid,
                                   x.s_de_x(x.d_front), "ilot",
                                   ["RF-SV-AB3A.POSITION", "RF-SV-GEN.SUPPORT_EXCLUSIF_AB3A_AB4", "DEF-025"],
                                   {"*": P.solveur("ilot_directionnel", regle="RF-SV-AB3A.POSITION",
                                                   note="AB3a + M9c sur son support, sur l'îlot directionnel (IISR3 art. 42-9)")},
                                   hauteur=h, gamme="petite", panonceaux=["M9c"],
                                   applic={"carrefour": self.id, "branche": x.bid, "route": x.rid},
                                   support={"type": "ilot"}))
        il["terre_plein"]["objets_portes"] = [f"SG-{self.id[2:]}.dir_{x.nom}.AB3a"]
        # passage à travers la voie directe (refuge sur l'îlot) si dit
        if co["ilot"]["desc"].get("passage") is not None and _b(co["ilot"]["desc"]["passage"], c + ".passage"):
            ai = ang((nez_i[0] - C[0], nez_i[1] - C[1]))
            a_pp = ai + (4.0 + 1.0) / (R_ + W / 2) * 180 / math.pi * (1 if co["da"] > 0 else -1) * 0.0
            if x.passage:
                # dans le prolongement du passage de la branche de départ (même traversée, refuge sur l'îlot)
                q = x.pt(x.passage["xc"], x.w_g)
                ac = ang((q[0] - C[0], q[1] - C[1]))
            else:
                dl = (2.0 + 2.0) / (R_ + W / 2) * 180.0 / math.pi * (1 if co["da"] > 0 else -1)
                ac = ai + dl
            w = regles.valeur("DEF-011", "longueur_bandes_ville")
            dA = w / 2 / (R_ + W / 2) * 180.0 / math.pi
            pts = arc_pts(C, R_, ac - dA, ac + dA, 2.0) + arc_pts(C, R_ + W, ac + dA, ac - dA, 2.0)
            self.marquages.append({"id": f"M-{self.id[2:]}.dir_{x.nom}_{y.nom}.passage", "type": "passage_pieton",
                                   "ancrage": {"carrefour": self.id, "branche": x.bid},
                                   "geometrie": {"exterieur": anneau(pts)}, "couleur": "blanc",
                                   "regles": ["RF-MQ-PP-01", "RF-MQ-PP-05", "DEF-011"],
                                   "x-opendrive": {"object_type": "crosswalk"},
                                   "prov": {"*": P.description(c + ".passage", self.conf(), regle="DEF-011",
                                                               note="passage à travers la voie directe, refuge sur l'îlot")}})
            if x.passage:
                # largeur du refuge dans le sens de la marche (perpendiculaire à la branche, au droit du passage)
                q0, q1 = x.pt(x.passage["xc"], x.w_g - 1.0), x.pt(x.passage["xc"], x.w_g + 60.0)
                seg = LineString([q0, q1]).intersection(raised)
                lr = seg.length if not seg.is_empty else 0.0
            else:
                lr = self._largeur_locale(raised, C, ac)
            il["refuge"] = {"largeur_m": _r(lr), "abaisses": True, "bev": True}
            self.controle("refuge_largeur", il["refuge"]["largeur_m"], (regles.valeur("DEF-022", "largeur"), None),
                          "DEF-022", ilot=iid)
        return out

    @staticmethod
    def _largeur_locale(poly, C, a_deg):
        """Largeur de l'îlot le long du rayon issu de C à l'angle a (au droit du passage)."""
        far = (C[0] + 500 * math.cos(math.radians(a_deg)), C[1] + 500 * math.sin(math.radians(a_deg)))
        seg = LineString([C, far]).intersection(poly)
        return seg.length if not seg.is_empty else 0.0

    # ---------------------------------------------------------------- trajectoires
    def _mouvements_voies(self, x):
        """Mouvements autorisés par voie entrante : dits (« mouvements ») ou déduits du type de voie (voie de TAG →
        TAG, voie de TAD → TAD ; voie générale la plus à gauche : TAG s'il n'y a pas de voie de TAG ; la plus à droite :
        TAD s'il n'y a pas de voie de TAD ou de voie directe ; toutes : TD)."""
        dit = x.desc_b.get("mouvements")
        if dit is not None:
            out = {}
            for k, v in dit.items():
                if x.bande(str(k)) is None:
                    raise ErreurReseau(f"{x.chemin}.mouvements : voie « {k} » absente du profil d'extrémité")
                lst = [str(m).upper() for m in (v if isinstance(v, list) else [v])]
                for m in lst:
                    if m not in MOUVEMENTS:
                        raise ErreurReseau(f"{x.chemin}.mouvements.{k} : {m} (TD, TAG, TAD)")
                out[str(k)] = lst
            return out
        gen = [b for b in x.entrantes if b["type"] not in ("voie_tourne_gauche", "voie_tourne_droite")]
        a_tag = any(b["type"] == "voie_tourne_gauche" for b in x.entrantes)
        a_tad = any(b["type"] == "voie_tourne_droite" for b in x.entrantes)
        out = {}
        for b in x.entrantes:
            if b["type"] == "voie_tourne_gauche":
                out[b["id"]] = ["TAG"]
            elif b["type"] == "voie_tourne_droite":
                out[b["id"]] = ["TAD"]
            else:
                m = ["TD"]
                if gen and b is gen[0] and not a_tag:
                    m.append("TAG")
                if gen and b is gen[-1] and not a_tad:
                    m.append("TAD")
                out[b["id"]] = m
        return out

    def _cible(self, x, mv):
        best, bscore = None, None
        hin = ang((-x.u[0], -x.u[1]))
        for y in self.br:
            if y is x or not y.sortantes:
                continue
            dlt = norm180(y.azimut - hin)
            if mv == "TD" and abs(dlt) < 45:
                sc = abs(dlt)
            elif mv == "TAG" and 45 <= dlt <= 160:
                sc = abs(dlt - 90)
            elif mv == "TAD" and -160 <= dlt <= -45:
                sc = abs(dlt + 90)
            else:
                continue
            if bscore is None or sc < bscore:
                best, bscore = y, sc
        return best

    def _trajectoires(self, branches):
        traj = []
        self.traj_geo = {}
        for x in self.br:
            mv = self._mouvements_voies(x)
            gen_in = [b for b in x.entrantes]
            for b in x.entrantes:
                for m in mv.get(b["id"], []):
                    y = self._cible(x, m)
                    if y is None:
                        continue
                    # voie de sortie : TAG → la plus à gauche, TAD → la plus à droite, TD → même rang
                    so = y.sortantes
                    if m == "TAG":
                        bo = so[0]
                    elif m == "TAD":
                        bo = so[-1]
                    else:
                        gi = [g for g in gen_in if g["type"] not in ("voie_tourne_gauche", "voie_tourne_droite")]
                        r = gi.index(b) if b in gi else 0
                        bo = so[min(r, len(so) - 1)]
                    co = next((c for c in self.coins if c["de"] is x and c["vers"] is y and c.get("ilot")), None)
                    geo, rmin, lg = self._geo_traj(x, b, y, bo, m, co)
                    tid = f"T-{x.nom}.{b['id']}.{m}"
                    t = {"id": tid, "de": {"branche": x.bid, "bande": b["id"]}, "vers": {"branche": f"B-{y.nom}", "bande": bo["id"]},
                         "mouvement": m, "geometrie": [xy_r(p) for p in geo],
                         "largeur_m": _r(b["w1"] - b["w0"])}
                    if rmin is not None:
                        t["rayon_min_m"] = _r(rmin, 3)
                    t["tags_graphe"] = ["vehicule"]
                    t["priorite"] = 1 if x.regime in ("prioritaire", "feux") else (3 if x.regime == "priorite_droite" else 2)
                    if co is not None:
                        t["priorite"] = 2
                    traj.append(t)
                    self.traj_geo[tid] = {"ligne": LineString(geo), "x": x, "y": y, "m": m, "longueur": lg, "voie_directe": co is not None}
        return traj

    def _geo_traj(self, x, b, y, bo, m, co):
        wa = (b["w0"] + b["w1"]) / 2
        wb = (bo["w0"] + bo["w1"]) / 2
        if co is not None:
            # voie directe : arc concentrique au bord du shunt, au milieu de la voie
            C, R_, W = co["C"], co["rayon"], co["ilot"]["W"]
            rr = R_ + W / 2
            pts = arc_pts(C, rr, co["a0"], co["a0"] + co["da"], 2.0)
            A = x.pt(max(co["xi"], x.d_front) + 15.0, wa)
            Bp = y.pt(max(co["xk"], y.d_front) + 15.0, wb)
            geo = [A] + pts + [Bp]
            return geo, rr, LineString(geo).length
        A = x.pt(x.d_front, wa)
        B = y.pt(y.d_front, wb)
        hin = (-x.u[0], -x.u[1])
        hout = y.u
        I = inter_lignes(A, hin, B, hout)
        if m == "TD" or I is None:
            return [A, B], None, math.dist(A, B)
        ta = (I[0] - A[0]) * hin[0] + (I[1] - A[1]) * hin[1]
        tb = (B[0] - I[0]) * hout[0] + (B[1] - I[1]) * hout[1]
        if ta <= 0 or tb <= 0:
            return [A, B], None, math.dist(A, B)
        phi = math.radians(abs(norm180(ang(hout) - ang(hin))))
        T = min(ta, tb)
        coin = next((c for c in self.coins if c["de"] is x and c["vers"] is y and c.get("rayon")), None)
        if m == "TAD" and coin is not None:
            # tourne-à-droite : arc concentrique au coin (rayon du coin + écart de l'axe de voie à la bordure)
            Rr = coin["rayon"] + min(x.w_g - wa, wb - y.w_d)
            T = Rr * math.tan(phi / 2)
        Rr = T / math.tan(phi / 2)
        P1 = (I[0] - T * hin[0], I[1] - T * hin[1])
        P2 = (I[0] + T * hout[0], I[1] + T * hout[1])
        if T > ta:
            A = P1
        if T > tb:
            B = P2
        gauche = norm180(ang(hout) - ang(hin)) > 0
        nrm = rot(hin, 90.0 if gauche else -90.0)
        C = (P1[0] + Rr * nrm[0], P1[1] + Rr * nrm[1])
        a0 = ang((P1[0] - C[0], P1[1] - C[1]))
        a1 = a0 + math.degrees(phi) * (1 if gauche else -1)
        pts = arc_pts(C, Rr, a0, a1, 3.0)
        geo = [A] + pts + [B]
        return geo, Rr, LineString(geo).length

    def _conflits(self, traj):
        """Points de conflit (CU p. 120-122) : croisements = paires de trajectoires d'origines et de destinations
        différentes qui se coupent ; convergences = (n − 1) par voie de destination ; divergences = (n − 1) par voie
        d'origine (n mouvements). Voie directe de tourne-à-droite : convergence avec les mouvements de même destination."""
        out = []
        ids = [t["id"] for t in traj]
        tt = {t["id"]: t for t in traj}
        crois = conv = div = 0
        par_orig, par_dest = {}, {}
        for t in traj:
            par_orig.setdefault((t["de"]["branche"], t["de"]["bande"]), []).append(t["id"])
            par_dest.setdefault((t["vers"]["branche"], t["vers"]["bande"]), []).append(t["id"])
        k = 0
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                ta, tb = tt[a], tt[b]
                same_o = (ta["de"] == tb["de"])
                same_d = (ta["vers"] == tb["vers"])
                if same_o or same_d:
                    continue
                ga, gb = self.traj_geo[a]["ligne"], self.traj_geo[b]["ligne"]
                inter = ga.intersection(gb)
                if inter.is_empty:
                    continue
                pt = inter if inter.geom_type == "Point" else inter.centroid if inter.geom_type != "MultiPoint" else list(inter.geoms)[0]
                k += 1
                crois += 1
                pa, pb = ta["priorite"], tb["priorite"]
                c = {"id": f"K-{self.id[2:]}.{k}", "trajectoires": [a, b], "type": "croisement", "point": xy_r(pt.coords[0])}
                if pa != pb:
                    c["prioritaire"] = a if pa < pb else b
                out.append(c)
        for (br, bd), lst in sorted(par_dest.items()):
            for j in range(1, len(lst)):
                k += 1
                conv += 1
                out.append({"id": f"K-{self.id[2:]}.{k}", "trajectoires": [lst[0], lst[j]], "type": "convergence",
                            "point": tt[lst[j]]["geometrie"][-1]})
        for (br, bd), lst in sorted(par_orig.items()):
            for j in range(1, len(lst)):
                k += 1
                div += 1
                out.append({"id": f"K-{self.id[2:]}.{k}", "trajectoires": [lst[0], lst[j]], "type": "divergence",
                            "point": tt[lst[j]]["geometrie"][0]})
        # TAG opposés qui se coupent (giration « derrière » l'autre, rayon court) : le décompte de référence (CU p. 120-122,
        # croix complète : 16 croisements, 32 conflits) ne les compte pas ; les deux décomptes sont rapportés
        opp = 0
        for k_ in out:
            if k_["type"] != "croisement":
                continue
            ga, gb = self.traj_geo[k_["trajectoires"][0]], self.traj_geo[k_["trajectoires"][1]]
            if ga["m"] == gb["m"] == "TAG" and abs(abs(norm180(ga["x"].azimut - gb["x"].azimut)) - 180) < 20:
                opp += 1
                k_["note"] = "TAG opposés"
        self.compte_conflits = {"croisement": crois, "convergence": conv, "divergence": div, "total": crois + conv + div,
                                "croisements_TAG_opposes": opp, "croisement_reference_CU": crois - opp,
                                "total_reference_CU": crois - opp + conv + div}
        for k_ in out:
            k_.pop("note", None)
        for t in traj:
            t["conflits"] = sorted(c["id"] for c in out if t["id"] in c["trajectoires"])
            if not t["conflits"]:
                t.pop("conflits")
        return out

    VEHICULES_PROJET = {"vl": "vl", "bus": "bus_standard_12m", "bus_standard_12m": "bus_standard_12m"}

    def _usagers(self, traj):
        """Véhicules de projet de chaque mouvement (correction après le contrôle de l'étape 2) : la description peut dire
        quels mouvements le bus (standard 12 m, lot L3a) doit desservir, « vehicule: {bus: [ouest TD, est TD]} » ; le VL
        dessert tous les mouvements. Le modèle porte alors trajectoires[].usagers (["vl"] ou ["vl", "bus_standard_12m"]) :
        les balayages du lot L3 (nez des îlots, îlots du cœur) ne sont calculés que pour ces véhicules. Sans la clé, rien
        n'est écrit et les deux véhicules balaient tous les mouvements (comportement antérieur)."""
        vd = self.desc.get("vehicule")
        if vd is None:
            return
        c = self.chemin + ".vehicule"
        if not isinstance(vd, dict):
            raise ErreurReseau(f"{c} : « {{bus: [<branche> TD|TAG|TAD, ...]}} » attendu")
        servis = {}
        for nom_v, mvts in vd.items():
            v = self.VEHICULES_PROJET.get(V.norm(str(nom_v)).replace(" ", "_"))
            if v is None or v == "vl":
                raise ErreurReseau(f"{c}.{nom_v} : véhicule de projet inconnu (bus ; le VL dessert tous les mouvements)")
            for mv in (mvts or []):
                nom, m = str(mv).rsplit(" ", 1)
                x = next((b for b in self.br if b.nom == nom), None)
                if x is None or m.upper() not in ("TD", "TAG", "TAD"):
                    raise ErreurReseau(f"{c}.{nom_v} : « {mv} » : « <branche> TD|TAG|TAD » attendu")
                ts = [t for t in traj if t["de"]["branche"] == x.bid and t["mouvement"] == m.upper()]
                if not ts:
                    raise ErreurReseau(f"{c}.{nom_v} : aucune trajectoire « {mv} »")
                for t in ts:
                    servis.setdefault(t["id"], set()).add(v)
        for t in traj:
            t["usagers"] = ["vl"] + sorted(servis.get(t["id"], ()))

    def _guidage(self, traj, marquages, u_m):
        """Lignes de guidage seulement si décrites (ARB-08, RF-OSM-MRQ-041) et seulement dans les cas de l'art. 117-1 :
        TAG à l'indonésienne en phase spéciale (T'2 0,10, RF-MQ-GUI-01). Géométrie (RF-MQ-CAR-03, IISR7 p. 36) :
        prolongement, dans le carrefour, du bord droit de chaque voie de TAG opposée, reliés par un segment oblique à
        45° à travers la zone centrale ; les deux courants passent l'un devant l'autre de part et d'autre."""
        gd = self.desc.get("guidage")
        if not gd:
            return None
        c = self.chemin + ".guidage"
        mvts = gd.get("mouvements") or []
        if not mvts:
            raise ErreurReseau(f"{c}.mouvements : mouvements guidés à dire (« ouest TAG », « est TAG »)")
        modu = str(gd.get("modulation", "T'2"))
        larg = _v(gd["largeur"], c + ".largeur") if gd.get("largeur") is not None else regles.valeur("RF-MQ-GUI-01", "largeur")
        if self.regime != "feux":
            raise ErreurReseau(f"{c} : TAG à l'indonésienne guidé seulement en carrefour à feux avec phase spéciale "
                               "(RF-GV-FEU-002, DEF-028 ; IISR7 art. 117-1)")
        guides = []
        for mv in mvts:
            nom, m = str(mv).rsplit(" ", 1)
            x = next((b for b in self.br if b.nom == nom), None)
            if x is None or m.upper() != "TAG":
                raise ErreurReseau(f"{c}.mouvements : « {mv} » : « <branche> TAG » attendu")
            ts = [t for t in traj if t["de"]["branche"] == x.bid and t["mouvement"] == "TAG"]
            if not ts:
                raise ErreurReseau(f"{c} : aucune trajectoire TAG depuis « {nom} »")
            guides.append((x, ts))
        self.guides = guides
        out = {"mouvements": [str(m) for m in mvts], "modulation": modu, "largeur_m": larg, "lignes": []}
        # paires opposées
        faits = set()
        for x, ts in guides:
            for y, ts2 in guides:
                if y is x or (y.nom, x.nom) in faits:
                    continue
                if abs(abs(norm180(x.azimut - y.azimut)) - 180) > 20:
                    continue
                faits.add((x.nom, y.nom))
                bx = max((b for b in x.entrantes if b["type"] == "voie_tourne_gauche"), key=lambda b: b["w1"], default=None)
                byy = max((b for b in y.entrantes if b["type"] == "voie_tourne_gauche"), key=lambda b: b["w1"], default=None)
                if bx is None or byy is None:
                    raise ErreurReseau(f"{c} : TAG à l'indonésienne sans voie de TAG sur « {x.nom} » ou « {y.nom} »")
                # bords droits des voies de TAG (côté voies directes), prolongés
                pa0 = x.pt(x.d_front, bx["w1"])
                pb0 = y.pt(y.d_front, byy["w1"])
                hx = (-x.u[0], -x.u[1])
                # repère : origine centre, axe e = hx ; décalages latéraux des deux lignes
                e = hx
                nn = rot(e, 90.0)
                oa = (pa0[0] - self.centre[0]) * nn[0] + (pa0[1] - self.centre[1]) * nn[1]
                ob = (pb0[0] - self.centre[0]) * nn[0] + (pb0[1] - self.centre[1]) * nn[1]
                dl = abs(ob - oa)
                q1 = (self.centre[0] + nn[0] * oa - e[0] * dl / 2, self.centre[1] + nn[1] * oa - e[1] * dl / 2)
                q2 = (self.centre[0] + nn[0] * ob + e[0] * dl / 2, self.centre[1] + nn[1] * ob + e[1] * dl / 2)
                geo = [pa0, q1, q2, pb0]
                mid = f"M-{self.id[2:]}.guidage_{x.nom}_{y.nom}"
                marquages.append({"id": mid, "type": "ligne_guidage", "ancrage": {"carrefour": self.id},
                                  "geometrie": [xy_r(p) for p in geo], "couleur": "blanc",
                                  "regles": ["RF-MQ-GUI-01", "RF-MQ-CAR-03", "DEF-021", "ARB-08"],
                                  "x-opendrive": {"modulation": modu, "largeur_m": larg},
                                  "prov": {"*": P.description(c, self.conf(), regle="RF-MQ-GUI-01",
                                                              note=f"guidage décrit ({modu} {larg} m) ; tracé RF-MQ-CAR-03 : "
                                                                   "prolongements des bords droits des voies de TAG reliés à 45°")}})
                ligne = LineString(geo)
                out["lignes"].append(mid)
                # trajectoires des TAG guidés (RF-MQ-CAR-03 : les deux courants passent l'un devant l'autre) : axe de
                # la voie de TAG jusqu'à la frontière, oblique à 45° vers la gauche jusqu'à l'axe de la voie de sortie,
                # puis cet axe ; chaque courant garde la ligne de guidage à sa droite
                for t in ts + ts2:
                    g = self.traj_geo[t["id"]]
                    xx, yy = g["x"], g["y"]
                    A = tuple(t["geometrie"][0])
                    hin = (-xx.u[0], -xx.u[1])
                    d45 = rot(hin, 45.0)
                    B = tuple(t["geometrie"][-1])
                    Pk = inter_lignes(A, d45, B, yy.u)
                    if Pk is not None:
                        geo_t = [A, Pk, B]
                        t["geometrie"] = [xy_r(q) for q in geo_t]
                        t.pop("rayon_min_m", None)
                        g["ligne"] = LineString(geo_t)
                        g["longueur"] = g["ligne"].length
                        g["guide"] = True
                for t in ts + ts2:
                    t["guidage"] = {"materialise": True, "modulation": "T'2", "largeur_m": larg, "cotes": "droite",
                                    "regle": "RF-MQ-GUI-01"}
                    # contrôle : la trajectoire reste d'un seul côté de la ligne de guidage
                    g = self.traj_geo[t["id"]]["ligne"]
                    n_int = 0 if g.intersection(ligne).is_empty else 1
                    self.controle("guidage_separe_les_TAG", n_int, (0, 0), "RF-MQ-CAR-03", trajectoire=t["id"])
                g1 = self.traj_geo[ts[0]["id"]]["ligne"]
                g2 = self.traj_geo[ts2[0]["id"]]["ligne"]
                self.controle("TAG_opposes_sans_croisement", 0 if g1.intersection(g2).is_empty else 1, (0, 0),
                              "RF-MQ-CAR-03", trajectoires=[ts[0]["id"], ts2[0]["id"]])
        for t in traj:
            if t["mouvement"] != "TAG" or "guidage" in t:
                continue
            t["guidage"] = {"materialise": False, "modulation": "aucune", "regle": "RF-OSM-MRQ-041"}
        return out

    def _zone_conflit(self):
        pts = []
        for x in self.br:
            pts += [x.pt(x.d_front, x.w_g), x.pt(x.d_front, x.w_d)]
        return Polygon(pts).convex_hull

    # ---------------------------------------------------------------- signalisation de priorité
    def _panneaux(self, c, signaux):
        agglo = self.agglo
        h = regles.valeur("DEF-025", "hauteur_trottoir_agglo" if agglo else "hauteur_rase_campagne")
        for x in self.br:
            if x.regime not in ("cedez", "stop"):
                continue
            code = "AB3a" if x.regime == "cedez" else "AB4"
            gam = gamme_panneau(x.tr.ctx)
            l = GAMME_LARGEUR[FORME[code]][gam]
            dl = regles.valeur("DEF-025", "bord_panneau_a_la_rive") + l / 2
            if not agglo:
                dl = max(dl, regles.valeur("RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "support_min_m"))
            xs = x.ligne["x1"] + 0.5
            w = x.w_g + dl
            pos = x.pt(xs, w)
            regs = ["RF-SV-AB3A.POSITION" if code == "AB3a" else "RF-SV-AB4.POSITION", "RF-SV-GEN.DISTANCE_RIVE",
                    "RF-SV-GEN.SUPPORT_EXCLUSIF_AB3A_AB4", "DEF-025", "ARB-20"]
            signaux.append(signal(f"SG-{self.id[2:]}.{x.nom}.{code}", "panneau", code, pos, ang((-x.u[0], -x.u[1])),
                                  x.rid, x.s_de_x(xs), "droite", regs,
                                  {"*": P.defaut("RF-SV-AB3A.POSITION" if code == "AB3a" else "RF-SV-AB4.POSITION",
                                                 note=f"au droit de la ligne, côté amont ; bord à {regles.valeur('DEF-025', 'bord_panneau_a_la_rive')} m "
                                                      "de la rive (placement fin ARB-20 au lot L6)")},
                                  hauteur=h, gamme=gam, panonceaux=["M9c"] if code == "AB3a" else None,
                                  applic={"carrefour": self.id, "branche": x.bid, "route": x.rid, "sens": "avant"},
                                  support={"type": "poteau"}, t=x.t_route(w)))
        # hors agglomération, sans îlot sur la route prioritaire : J3 dans chaque angle (RF-SV-J3) ; AB2 sur les
        # branches prioritaires à 150 m (RF-SV-AB2.EMPLOI, RF-SV-A.DISTANCE)
        if not agglo:
            prio = [x for x in self.br if x.regime == "prioritaire"]
            if prio and not any(x.ilot_bande for x in prio):
                for co in self.coins:
                    if not co.get("rayon"):
                        continue
                    P0 = co["P"]
                    dirc = unit(co["C"][0] - P0[0], co["C"][1] - P0[1])
                    pos = (P0[0] + dirc[0] * (co["rayon"] * 0.6), P0[1] + dirc[1] * (co["rayon"] * 0.6))
                    x = co["de"]
                    signaux.append(signal(f"SG-{self.id[2:]}.J3_{co['de'].nom}_{co['vers'].nom}", "balise", "J3", pos,
                                          ang((P0[0] - pos[0], P0[1] - pos[1])), x.rid, x.s_de_x(x.d_front), "droite",
                                          ["RF-SV-J3"], {"*": P.defaut("RF-SV-J3", note="une balise J3 par angle, hors "
                                                                                     "agglomération sans îlot sur la route prioritaire")},
                                          applic={"carrefour": self.id}))
            # présignalisation des branches non prioritaires hors agglomération : AB3b (AB3a + M1) en cédez,
            # AB5 (AB3a + M5) en STOP, à 150 m (RF-SV-AB3B.EMPLOI, RF-SV-AB5.EMPLOI, RF-SV-A.DISTANCE)
            for x in self.br:
                if x.regime not in ("cedez", "stop"):
                    continue
                code, pan, reg = ("AB3b", "M1", "RF-SV-AB3B.EMPLOI") if x.regime == "cedez" else ("AB5", "M5", "RF-SV-AB5.EMPLOI")
                dist = regles.valeur("RF-SV-A.DISTANCE", "hors_agglo_cible_m")["route"]
                xs = x.d_front + dist
                s = x.s_de_x(xs)
                if not (0 <= s <= x.tr.L):
                    self.av.append(f"{x.chemin} : {code} à {dist} m hors du tronçon (le prolonger)")
                    continue
                gam = gamme_panneau(x.tr.ctx)
                dl = max(regles.valeur("DEF-025", "bord_panneau_a_la_rive") + GAMME_LARGEUR["triangle"][gam] / 2,
                         regles.valeur("RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "support_min_m"))
                pos = x.pt_route(xs, x.w_g + dl)
                signaux.append(signal(f"SG-{self.id[2:]}.{x.nom}.{code}", "panneau", code, pos, ang((-x.u[0], -x.u[1])),
                                      x.rid, s, "droite", [reg, "RF-SV-A.DISTANCE", "DEF-025"],
                                      {"*": P.defaut(reg, note=f"présignalisation à {dist} m (RF-SV-A.DISTANCE), AB3a + {pan}")},
                                      hauteur=h, gamme=gam, panonceaux=[pan],
                                      applic={"carrefour": self.id, "branche": x.bid, "route": x.rid},
                                      support={"type": "poteau"}, t=x.t_route(x.w_g + dl)))
            for x in prio:
                dist = regles.valeur("RF-SV-A.DISTANCE", "hors_agglo_cible_m")["route"]
                xs = x.d_front + dist
                s = x.s_de_x(xs)
                if not (0 <= s <= x.tr.L):
                    self.av.append(f"{x.chemin} : AB2 à {dist} m hors du tronçon (le prolonger)")
                    continue
                gam = gamme_panneau(x.tr.ctx)
                dl = max(regles.valeur("DEF-025", "bord_panneau_a_la_rive") + GAMME_LARGEUR["triangle"][gam] / 2,
                         regles.valeur("RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "support_min_m"))
                pos = x.pt_route(xs, x.w_g + dl)
                signaux.append(signal(f"SG-{self.id[2:]}.{x.nom}.AB2", "panneau", "AB2", pos, ang((-x.u[0], -x.u[1])),
                                      x.rid, s, "droite", ["RF-SV-AB2.EMPLOI", "RF-SV-A.DISTANCE", "DEF-025"],
                                      {"*": P.defaut("RF-SV-AB2.EMPLOI", note=f"branche prioritaire hors agglomération ; à {dist} m (RF-SV-A.DISTANCE)")},
                                      hauteur=h, gamme=gam, applic={"carrefour": self.id, "branche": x.bid, "route": x.rid},
                                      support={"type": "poteau"}, t=x.t_route(x.w_g + dl)))

    # ---------------------------------------------------------------- feux
    def _feux(self, c, traj, signaux, tous, modele):
        fd = self.desc.get("feux") or {}
        ch = self.chemin + ".feux"
        phases_d = fd.get("phases")
        if not phases_d:
            raise ErreurReseau(f"{ch}.phases : plan de feux à décrire (phases et mouvements ; RF-GV-FEU-001 : 2 phases "
                               "de préférence, phase spéciale de TAG si TAG à l'indonésienne)")
        h_bas = regles.valeur("DEF-027", "bas_boitier")
        groupes = {}         # couloir (branche, voies) → signaux
        # R11 : un par couloir, sur le trottoir ou l'îlot à droite (RF-FEU.R11.NOMBRE_ET_COTES) ; couloirs séparés par
        # un îlot (voie de TAG en phase spéciale) : l'îlot porte les R11 des deux couloirs (RF-FEU.PHASE_SPECIALE)
        for x in self.br:
            if x.regime != "feux" or not x.entrantes:
                continue
            couloirs = self._couloirs(x)
            xe = (x.ligne["x0"] if x.ligne else x.d_front) - regles.valeur("DEF-027", "mat_aval_ligne_effet")
            for k, (voies, w_droite, porte) in enumerate(couloirs):
                gid = f"G-{x.nom}.{k + 1}"
                dl = 0.70 if porte == "trottoir" else (w_droite[1] - w_droite[0]) / 2
                w = w_droite[0] + dl if porte == "trottoir" else (w_droite[0] + w_droite[1]) / 2
                pos = x.pt(xe, w)
                sid = f"SG-{self.id[2:]}.{x.nom}.R11.{k + 1}"
                signaux.append(signal(sid, "feu", "R11v", pos, ang((-x.u[0], -x.u[1])), x.rid, x.s_de_x(xe),
                                      "droite" if porte == "trottoir" else "ilot",
                                      ["RF-FEU.R11.NOMBRE_ET_COTES", "RF-FEU.POSITION.GENERATEUR", "RF-FEU.POSITION_LIGNE_EFFET",
                                       "DEF-027", "ARB-14"],
                                      {"*": P.defaut("DEF-027", note=f"R11 principal à droite du couloir {'+'.join(voies)}, "
                                                                     "0,30 m en aval de la ligne d'effet, axe à 0,70 m de la rive "
                                                                     "(sur îlot : au milieu) ; placement fin ARB-20 au lot L6")},
                                      hauteur=h_bas,
                                      applic={"carrefour": self.id, "branche": x.bid, "route": x.rid, "bandes": voies},
                                      support={"type": "support_feux", "hauteur_m": regles.valeur("DEF-027", "mat_hauteur"),
                                               "diametre_mm": regles.valeur("DEF-027", "mat_diametre") * 1000},
                                      feux={"type": "tricolore", "tetes": [{"type": "R11v", "diametre_mm": 200},
                                                                           {"type": "R11v", "diametre_mm": 90, "repetiteur": True}],
                                            "controleur": f"F-{self.id[2:]}", "groupe": gid}, t=x.t_route(w)))
                groupes.setdefault(gid, []).append(sid)
                x.__dict__.setdefault("groupes", []).append((gid, voies))
                self._porter(x, w, sid)
                # rappel gauche sur l'îlot qui sépare deux couloirs (phase spéciale) : obligatoire
                if porte == "ilot" and k + 1 < len(couloirs) + 1:
                    pass
            # îlot entre deux couloirs : rappel du couloir de droite (voies directes) sur le même îlot
            for k in range(len(couloirs) - 1):
                voies, w_d, porte = couloirs[k + 1]
                _, w_il, porte_il = couloirs[k]
                if porte_il != "ilot":
                    continue
                gid = f"G-{x.nom}.{k + 2}"
                w = (w_il[0] + w_il[1]) / 2
                pos = x.pt(xe + 0.6, w)
                sid = f"SG-{self.id[2:]}.{x.nom}.R11.{k + 2}g"
                signaux.append(signal(sid, "feu", "R11v", pos, ang((-x.u[0], -x.u[1])), x.rid, x.s_de_x(xe + 0.6), "ilot",
                                      ["RF-FEU.R11.NOMBRE_ET_COTES", "RF-FEU.PHASE_SPECIALE", "DEF-027"],
                                      {"*": P.defaut("RF-FEU.PHASE_SPECIALE", note="l'îlot entre deux couloirs en phases "
                                                                                   "dissociées porte les R11 des deux couloirs")},
                                      hauteur=h_bas,
                                      applic={"carrefour": self.id, "branche": x.bid, "route": x.rid, "bandes": voies},
                                      support={"type": "support_feux", "hauteur_m": regles.valeur("DEF-027", "mat_hauteur")},
                                      feux={"type": "tricolore", "tetes": [{"type": "R11v", "diametre_mm": 200}],
                                            "controleur": f"F-{self.id[2:]}", "groupe": gid}, t=x.t_route(w)))
                groupes.setdefault(gid, []).append(sid)
                self._porter(x, w, sid)
        # R12 : aux deux extrémités de chaque traversée gérée, sur le trottoir de destination (RF-FEU.R12.POSITION)
        for x in self.br:
            if not x.passage:
                continue
            gid = f"G-PP.{x.nom}"
            for cote, w in (("gauche", x.w_d - 0.7), ("droite", x.w_g + 0.7)):
                pos = x.pt(x.passage["x0"] - 0.3, w)
                sid = f"SG-{self.id[2:]}.{x.nom}.R12.{cote}"
                vise = rot(x.n, 0.0) if cote == "gauche" else (-x.n[0], -x.n[1])
                signaux.append(signal(sid, "feu", "R12", pos, ang(vise), x.rid, x.s_de_x(x.passage["x0"] - 0.3),
                                      cote, ["RF-FEU.R12.POSITION", "DEF-027"],
                                      {"*": P.defaut("RF-FEU.R12.POSITION", note="R12 face au piéton qui attend en face, "
                                                                               "à l'extrémité de la traversée")},
                                      hauteur=regles.valeur("DEF-027", "R12_centre"),
                                      applic={"carrefour": self.id, "branche": x.bid, "route": x.rid},
                                      feux={"type": "pietons", "tetes": [{"type": "R12", "diametre_mm": 200}],
                                            "controleur": f"F-{self.id[2:]}", "groupe": gid}, t=x.t_route(w)))
                groupes.setdefault(gid, []).append(sid)
        # phases
        mv_groupe = {}
        for x in self.br:
            for gid, voies in getattr(x, "groupes", []):
                for t in traj:
                    if t["de"]["branche"] == x.bid and t["de"]["bande"] in voies and not self.traj_geo[t["id"]]["voie_directe"]:
                        mv_groupe.setdefault(gid, set()).add(t["id"])
        jaune = _v(fd["jaune"], ch + ".jaune") if fd.get("jaune") is not None else \
            regles.valeur("DEF-028", "jaune_agglo_s" if self.agglo else "jaune_hors_agglo_s")
        vmin = regles.valeur("DEF-028", "vert_min_s")
        phases, phases_rap = [], []
        verts = {}
        tid_par_mv = {}
        for t in traj:
            nom = t["de"]["branche"][2:]
            tid_par_mv.setdefault(f"{nom} {t['mouvement']}", []).append(t["id"])
        tous_gid = sorted(groupes)
        self.phases_mv = []
        for i, ph in enumerate(phases_d):
            cp = f"{ch}.phases[{i}]"
            _cles(ph, CLES_PHASE, cp)
            nom = str(ph.get("nom") or f"P{i + 1}")
            mvts = []
            for m in ph.get("mouvements") or []:
                if str(m) not in tid_par_mv:
                    raise ErreurReseau(f"{cp}.mouvements : « {m} » inconnu (mouvements : {', '.join(sorted(tid_par_mv))})")
                mvts += tid_par_mv[str(m)]
            piet = [str(p) for p in (ph.get("pietons") or [])]
            if ph.get("vert") is None:
                raise ErreurReseau(f"{cp}.vert : durée de vert à dire (s ; ≥ {vmin} s, DEF-028)")
            vert = _v(ph["vert"], cp + ".vert")
            if vert < vmin:
                self.controle("vert_min", vert, (vmin, None), "DEF-028", phase=nom)
            # groupes verts : couloirs dont tous les mouvements sont dans la phase ; piétons dits
            verts_g = set()
            for gid, ms in mv_groupe.items():
                if ms and ms <= set(mvts):
                    verts_g.add(gid)
            for p in piet:
                if f"G-PP.{p}" not in groupes:
                    raise ErreurReseau(f"{cp}.pietons : pas de passage géré sur la branche « {p} »")
                verts_g.add(f"G-PP.{p}")
            # couloir partiellement servi : erreur (un couloir = un seul feu ; R11 et R14 jamais sur le même couloir)
            for gid, ms in mv_groupe.items():
                if ms & set(mvts) and not ms <= set(mvts):
                    raise ErreurReseau(f"{cp} : le couloir {gid} ({', '.join(sorted(ms))}) n'est servi qu'en partie : "
                                       "séparer les voies par un îlot portant les R11 (RF-FEU.PHASE_SPECIALE) ou décrire "
                                       "des R14 (hors format)")
            # dégagement : plus longue trajectoire de la phase / 10 m/s (RF-GV-FEU-004, DEF-028)
            lmax = max((self.traj_geo[t]["longueur"] for t in mvts), default=0.0)
            deg = math.ceil(lmax / regles.valeur("DEF-028", "degagement_vehicules_m_s"))
            etat = lambda col: {sid: (col if g in verts_g else "rouge") for g in tous_gid for sid in groupes[g]}  # noqa: E731
            phases.append({"nom": f"{nom} vert", "duree_s": vert, "etats": etat("vert")})
            phases.append({"nom": f"{nom} jaune", "duree_s": jaune, "etats": {sid: ("jaune" if g in verts_g and not g.startswith("G-PP") else "rouge")
                                                                               for g in tous_gid for sid in groupes[g]}})
            phases.append({"nom": f"{nom} dégagement", "duree_s": float(deg), "etats": {sid: "rouge" for g in tous_gid for sid in groupes[g]}})
            phases_rap.append({"nom": nom, "mouvements": sorted(mvts), "groupes_verts": sorted(verts_g), "vert_s": vert,
                               "jaune_s": jaune, "degagement_s": deg, "trajectoire_max_m": _r(lmax, 2)})
            self.phases_mv.append((nom, set(mvts)))
        # tout mouvement doit être servi par une phase
        servis = set().union(*[m for _, m in self.phases_mv]) if self.phases_mv else set()
        voie_dir = {t for t, g in self.traj_geo.items() if g["voie_directe"]}
        non_servis = sorted(set(self.traj_geo) - servis - voie_dir)
        self.controle("mouvements_servis", len(non_servis), (0, 0), "RF-FEU.GESTION_COURANTS", non_servis=non_servis)
        cycle = sum(p["duree_s"] for p in phases)
        ctrl = {"id": f"F-{self.id[2:]}", "carrefour": self.id, "signaux": sorted(s["id"] for s in signaux if s["famille"] == "feu"),
                "cycle_s": cycle, "decalage_s": 0.0, "phases": phases, "groupes": {g: groupes[g] for g in tous_gid}}
        modele.setdefault("controleurs", []).append(ctrl)
        self.rapport["feux"] = {"phases": phases_rap, "cycle_s": cycle, "groupes": {g: groupes[g] for g in tous_gid}}
        self.controle("rouge_max", max((cycle - p["duree_s"] for p in phases if p["nom"].endswith("vert")), default=0),
                      (None, regles.valeur("DEF-028", "rouge_max_s")), "DEF-028")
        self.controle("nombre_phases", len(phases_d), (2, None), "RF-GV-FEU-001")
        return ctrl["id"]

    def _porter(self, x, w, sid):
        """Signal posé sur un îlot de la branche (w dans l'emprise d'un terre-plein) : objets_portes de l'îlot."""
        for bid, il in getattr(x, "ilots_ent", {}).items():
            bd = x.bande(bid)
            if bd and bd["w0"] - 1e-6 <= w <= bd["w1"] + 1e-6:
                il["terre_plein"].setdefault("objets_portes", []).append(sid)

    def _couloirs(self, x):
        """Couloirs d'une entrée : voies entrantes contiguës (sans îlot entre elles) ; (voies, (w0, w1) de ce qui
        borde le couloir à droite, 'trottoir' | 'ilot')."""
        out = []
        cur = []
        ents = sorted(x.entrantes, key=lambda b: b["w0"])
        for b in ents:
            if cur and abs(b["w0"] - cur[-1]["w1"]) > 1e-6:
                out.append(cur)
                cur = []
            cur.append(b)
        if cur:
            out.append(cur)
        res = []
        for grp in out:
            wr = grp[-1]["w1"]
            nxt = next((bb for bb in sorted(x.bandes, key=lambda b: b["w0"]) if abs(bb["w0"] - wr) < 1e-6), None)
            if nxt is not None and nxt["type"] == "terre_plein":
                res.append(([g["id"] for g in grp], (nxt["w0"], nxt["w1"]), "ilot"))
            else:
                res.append(([g["id"] for g in grp], (x.w_g, x.w_g + 2.0), "trottoir"))
        return res

    # ---------------------------------------------------------------- contrôles
    def _controles(self, c, traj, conflits, zc):
        # aucune ligne cédez sur une branche à feux (RF-MQ-CED-03) — aussi C09 du validateur
        for b in c["branches"]:
            if b["regime"] == "feux":
                la = (b.get("ligne_arret") or {}).get("type")
                self.controle("pas_de_cedez_aux_feux", 1 if la in ("CEDEZ", "STOP") else 0, (0, 0), "RF-MQ-CED-03", branche=b["id"])
        # zone de conflit : plus longue trajectoire dans la zone (≤ 40 m, avertissement, RF-GV-PIE-010)
        lmax = max((zc.intersection(g["ligne"]).length for g in self.traj_geo.values() if not g["voie_directe"]), default=0.0)
        st = "conforme" if lmax <= regles.valeur("RF-GV-PIE-010", "zone_conflit_max") else "avertissement"
        self.controle("zone_conflit_longueur", lmax, (None, regles.valeur("RF-GV-PIE-010", "zone_conflit_max")),
                      "RF-GV-PIE-010", statut=st)
        # rayon des trajectoires tournantes ≥ rayon intérieur de giration du VL (berline Rint 3,6, RF-GV-RAY-006)
        rint = regles.valeur("RF-GV-RAY-006", "berline")["Rint"]
        for t in traj:
            if t.get("rayon_min_m") is not None and not self.traj_geo[t["id"]].get("guide"):
                self.controle("rayon_trajectoire", t["rayon_min_m"], (rint, None), "RF-GV-RAY-006", trajectoire=t["id"])
        # TAG à l'indonésienne : jamais dans une phase partagée avec le direct opposé (DEF-028, RF-GV-FEU-002)
        if self.regime == "feux" and getattr(self, "guides", None):
            for nom, mvts in self.phases_mv:
                tags = [t for t in mvts if self.traj_geo[t]["m"] == "TAG" and t in {tt["id"] for x, ts in self.guides for tt in ts}]
                for tg in sorted(tags):         # ordre fixe (rapport déterministe ; lot N1, 18/10/2026)
                    xg = self.traj_geo[tg]["x"]
                    opp_td = [t for t in mvts if self.traj_geo[t]["m"] == "TD"
                              and abs(abs(norm180(self.traj_geo[t]["x"].azimut - xg.azimut)) - 180) < 20]
                    self.controle("TAG_indonesienne_phase_speciale", len(opp_td), (0, 0), "DEF-028", phase=nom, trajectoire=tg)
        # conflits de croisement entre mouvements d'une même phase (rapportés)
        if self.regime == "feux":
            rap = {}
            for nom, mvts in self.phases_mv:
                n = sum(1 for k in conflits if k["type"] == "croisement" and set(k["trajectoires"]) <= mvts)
                rap[nom] = n
            self.rapport["croisements_par_phase"] = rap


# ================================================================================================ giratoire
class Giratoire(ObjetReseau):
    """Giratoire : anneau (route fermée « anneau_giratoire » à sens unique, sens trigonométrique), îlot central
    (infranchissable + couronne franchissable), branches arrivant sur le bord extérieur de l'anneau, îlots séparateurs
    (ACI tableau 2 : H = Rg, B = Rg/4, d, r ; retrait de 1 m sur l'anneau), lignes cédez, passages, AB25 / B21-1."""

    def __init__(self, R, desc, chemin, k):
        super().__init__(R, desc, chemin, k)
        _cles(desc, CLES_GIRATOIRE, chemin)
        self.id = f"C-{desc.get('id') or ('G' + str(k + 1))}"
        if not desc.get("centre"):
            raise ErreurReseau(f"{chemin}.centre : position du centre à dire")
        self.centre = R.local(desc["centre"], chemin + ".centre")
        if desc.get("diametre") is not None:
            self.Rg = _v(desc["diametre"], chemin + ".diametre") / 2
            self.p_Rg = self.pd("diametre", note="diamètre extérieur (bord extérieur de l'anneau)")
        elif desc.get("rayon") is not None:
            self.Rg = _v(desc["rayon"], chemin + ".rayon")
            self.p_Rg = self.pd("rayon")
        else:
            raise ErreurReseau(f"{chemin} : diamètre (ou rayon) extérieur à dire (DEF-024 : observé 29-66 m de diamètre, "
                               "aucune règle ne fixe le diamètre)")
        typ = V.norm_cle(desc.get("type", "giratoire"))
        if typ not in ("giratoire", "mini_giratoire"):
            raise ErreurReseau(f"{chemin}.type : giratoire ou mini_giratoire")
        self.type = typ
        self.bdesc = desc.get("branches") or []
        for i, b in enumerate(self.bdesc):
            _cles(b, CLES_BRANCHE_GIR, f"{chemin}.branches[{i}]")
        self.rapport.update({"id": self.id, "genre": typ})

    def analyser(self, cap):
        self.cap = cap
        d = self.desc
        c = self.chemin
        self.br = []
        for i, b in enumerate(self.bdesc):
            x = Branche(str(b["troncon"]), self.R.trinfo(b["troncon"], f"{c}.branches[{i}]", cap), self.centre,
                        f"{c}.branches[{i}]", rayon_contact=self.Rg)
            x.desc_b, x.k = b, i
            self.br.append(x)
        self.br.sort(key=lambda x: x.azimut)
        self.ctx0 = self.br[0].tr.ctx
        self.agglo = self.ctx0["agglomeration"]
        # anneau
        if d.get("anneau") is not None:
            self.la, self.p_la = _v(d["anneau"], c + ".anneau"), self.pd("anneau", regle="RF-GV-GIR-004")
        else:
            self.la = regles.valeur("DEF-024", "anneau")
            self.p_la = P.defaut("DEF-024", note="largeur d'anneau 7 m")
        if self.type == "mini_giratoire":
            self.bf, self.p_bf = 0.0, None
        elif d.get("couronne") is not None:
            self.bf, self.p_bf = _v(d["couronne"], c + ".couronne"), self.pd("couronne", regle="RF-GV-GIR-006")
        else:
            self.bf, self.p_bf = 0.0, P.defaut("RF-GV-GIR-006", note="pas de couronne franchissable dite")
        self.Ri = self.Rg - self.la                      # rayon de l'îlot central (couronne comprise)
        self.Ri_inf = self.Ri - self.bf                  # partie infranchissable
        if self.Ri <= 0:
            raise ErreurReseau(f"{c} : anneau de {self.la} m plus large que le rayon {self.Rg} m")
        # bord extérieur, trottoir de l'anneau
        tw = d.get("trottoir")
        self.trottoir = _v(tw, c + ".trottoir") if tw is not None else (regles.valeur("DEF-004") if self.agglo else None)
        self.d_front = 0.0
        for x in self.br:
            x.d_front = 0.0          # la branche s'arrête au bord de l'anneau
        self._positions()

    def _lignes_a_la_ligne_cedez(self):
        """Entrée à plusieurs voies (giratoire multivoie, correction de l'étape 2) : la ligne qui sépare deux voies
        d'entrée s'arrête au bord amont de la ligne cédez (elle la traversait : recouvrement ligne / ligne transversale
        de G4) ; interruption sur la seule limite entre voies entrantes, sur l'emprise de la ligne cédez."""
        for x in self.br:
            if not x.ligne or len(x.entrantes) < 2:
                continue
            s0, s1 = sorted((x.s_de_x(x.ligne["x0"]), x.s_de_x(x.ligne["x1"])))
            ordre = sorted(x.entrantes, key=lambda b: abs(b["w0"] + b["w1"]))
            for b in ordre[:-1]:
                x.tr.decos.append({"type": "interruption", "s0": s0, "s1": s1 + 1e-3, "cible": ("limite_bande_ext", b["id"]),
                                   "motif": "autre"})
            # bord intérieur de la voie d'entrée la plus intérieure (contour de la zone hachurée) : arrêté aussi
            x.tr.decos.append({"type": "interruption", "s0": s0, "s1": s1 + 1e-3, "cible": ("limite_bande", ordre[0]["id"]),
                               "motif": "autre"})
            x.tr._decorer()

    def _rives_anneau(self, tr):
        """Rives peintes de l'anneau (correction après le contrôle de l'étape 2 : G2 recevait la rive inférée des routes
        sans bordure, T2 3u, RF-OSM-MRQ-021, sur le contour de l'îlot central et sur la rive extérieure). IISR7 art.
        117-2 C.1 : contour du terre-plein central en continue 3u (RF-MQ-GIR-01) ; rive continue à l'intérieur de
        l'anneau (RF-MQ-GIR-04). Les rives d'approche des branches gardent leur T2 3u ; le contour du dôme d'un
        mini-giratoire reste en T'2 3u (RF-MQ-GIR-02, posé par rg::giratoires_sol)."""
        if self.type == "mini_giratoire":
            return
        for p in tr.profils:
            n = len(p["limites"])
            for k, lim in enumerate(p["limites"]):
                mq = lim.get("marquages")
                if not isinstance(mq, list) or "bordure" in lim.get("nature", []):
                    continue
                regle = "RF-MQ-GIR-01" if k == 0 else "RF-MQ-GIR-04"
                for q in mq:
                    if q.get("modulation") in ("T2", "T'2", "T'3", "T3") and q.get("regle") == "RF-OSM-MRQ-021":
                        q["modulation"] = "continue"
                        q["largeur_u"] = 3
                        q["regle"] = regle
                        lim.setdefault("x-opendrive", {})["roadmark_type"] = "solid"
                        lim.setdefault("prov", {})["marquages"] = P.defaut(
                            regle, note="contour du terre-plein central de l'anneau : continue 3u (IISR7 117-2 C.1)"
                            if k == 0 else "rive intérieure à l'anneau : continue 3u (IISR7 117-2 C.1 a)")

    def _positions(self):
        """Ligne cédez au bord de l'anneau (0 m, DEF-012 / RF-OSM-CAR-002) ; passage en retrait de 2 à 5 m (ARB-02 :
        2 m si Rg < 15 m, 5 m au-delà ; 4 m en interurbain)."""
        lg = regles.valeur("RF-MQ-CED-01", "largeur")
        for x in self.br:
            pp = x.desc_b.get("passage")
            x.ligne = {"type": "CEDEZ", "x0": 0.0, "x1": lg} if x.entrantes else None
            x.passage = None
            if isinstance(pp, dict) and pp.get("retrait") is not None:
                # retrait dit (correction après le contrôle de l'étape 2 : mini-giratoire, passage au-delà de l'îlot)
                _cles(pp, {"retrait", "note"}, f"{x.chemin}.passage")
                ret = _v(pp["retrait"], f"{x.chemin}.passage.retrait")
                pr = P.description(f"{x.chemin}.passage.retrait", self.conf(), regle="DEF-012")
                plage = regles.valeur("DEF-012", "giratoire")
                self.controle("passage_retrait", ret, tuple(plage), "DEF-012", branche=x.nom)
                w = regles.valeur("DEF-011", "longueur_bandes_ville")
                x0 = lg + ret
                x.passage = {"x0": x0, "largeur": w, "x1": x0 + w, "xc": x0 + w / 2, "s": x.s_de_x(x0 + w / 2),
                             "retrait": ret, "prov": pr}
            elif pp is not None and _b(pp, f"{x.chemin}.passage"):
                if not self.agglo:
                    ret, pr = regles.valeur("DEF-012", "interurbain"), P.defaut("DEF-012", note="interurbain : 4 m")
                elif self.Rg < 15:
                    ret, pr = regles.valeur("DEF-012", "giratoire")[0], P.defaut("DEF-012", note="giratoire Rg < 15 m : 2 m (ARB-02)")
                else:
                    ret, pr = regles.valeur("DEF-012", "giratoire")[1], P.defaut("DEF-012", note="giratoire Rg ≥ 15 m : 5 m (ARB-02)")
                w = regles.valeur("DEF-011", "longueur_bandes_ville")
                x0 = lg + ret
                x.passage = {"x0": x0, "largeur": w, "x1": x0 + w, "xc": x0 + w / 2, "s": x.s_de_x(x0 + w / 2),
                             "retrait": ret, "prov": pr}

    def evenements(self):
        out = []
        for x in self.br:
            if x.passage:
                out.append((x.nom, {"type": "passage_pieton", "a": _r(x.passage["s"], 3), "largeur": x.passage["largeur"],
                                    "_prov_largeur": P.defaut("DEF-011", note="longueur des bandes"),
                                    "_chemin": f"{x.chemin}.passage"}))
        return out

    def construire(self, R, modele, ctxh):
        tous = ctxh["tous"]
        cid = self.id
        u_m = self.ctx0["u"]
        nid = f"N-{cid}"
        self.signaux, self.marquages = [], []
        # anneau : route fermée
        rid = f"R-{cid[2:]}A"
        r_axe = self.Rg - self.la / 2
        x0, y0 = self.centre[0], self.centre[1] - r_axe
        trace = G.Trace(x0, y0, 0.0).arc(r_axe, 2 * math.pi * r_axe, True)
        morceaux = []
        if self.type != "mini_giratoire" and self.bf > 0:
            morceaux += [f"terre-plein {self.bf} pavés franchissable", "bordure A2 vue 0,03"]
        morceaux.append(f"voie {self.la} →")
        if self.trottoir:
            morceaux += ["bordure T2", f"trottoir {self.trottoir}"]
        else:
            morceaux += ["bande dérasée 1,0"]
        profil_txt = " | ".join(morceaux)
        tr, route, ctxd = construire_troncon_annexe(R, ctxh, rid, trace, profil_txt, f"{self.chemin}.anneau",
                                                    self.ctx0, "anneau_giratoire", nid, nid)
        route["prov"]["ligne_reference"] = P.solveur("giratoire", regle="RF-GV-GIR-004",
                                                     note=f"cercle d'axe de rayon Rg − la/2 = {r_axe:.2f} m, sens trigonométrique")
        self._rives_anneau(tr)
        self._lignes_a_la_ligne_cedez()
        route["prov"]["categorie"] = P.solveur("giratoire", regle="RF-OSM-CAR-002", note="anneau de giratoire")
        noeud = R.noeud_reseau(modele, nid, (x0, y0), "carrefour", cid, self.br, note="giratoire décrit")
        noeud["routes"] = sorted(set(noeud["routes"] + [rid]))
        route["carrefour_debut"] = route["carrefour_fin"] = cid
        # îlot central
        ilots = []
        nc = 96
        cercle = lambda r: Point(self.centre).buffer(r, quad_segs=nc // 4)  # noqa: E731
        idc = f"I-{cid[2:]}.central"
        plant = self.desc.get("ilot_central") or ("franchissable" if self.type == "mini_giratoire" else "gazon")
        if self.type == "mini_giratoire":
            dome = regles.valeur("RF-GV-GIR-016", "dome_cm")
            h = dome[0] / 100.0 if self.desc.get("dome") is None else _v(self.desc["dome"], self.chemin + ".dome")
            tp = {"franchissable": "vl_pl", "surelevation_m": h,
                  "remplissage": {"type": "beton", "materiau_id": "beton_balaye", "bombement_m": h},
                  "marquage_contour": {"modulation": "T'2", "largeur_u": 3, "retrait_u": 0}}
            pr = P.defaut("RF-GV-GIR-016", note=f"îlot central franchissable en dôme de {h * 100:.0f} cm (10-15 cm, bus ≤ 12) ; "
                                                 "contour T'2 3u (RF-MQ-GIR-02)")
            ilots.append({"id": idc, "type": "central_giratoire", "polygone": poly_schema(cercle(self.Ri)), "carrefour": cid,
                          "terre_plein": tp, "prov": {"*": pr}})
        else:
            vue_inf = regles.valeur("RF-GV-GIR-006", "bordure_infranchissable_vue_max_cm") / 100.0
            rem = V.MATERIAUX.get(V.norm(plant)) if isinstance(plant, str) else None
            if rem is None or isinstance(rem, dict):
                raise ErreurReseau(f"{self.chemin}.ilot_central : matériau / remplissage inconnu « {plant} »")
            tp = {"franchissable": "non", "surelevation_m": vue_inf,
                  "ceinture": {"profil": "A2", "vue_m": round(vue_inf - 0.03, 3) if self.bf > 0 else vue_inf},
                  "remplissage": {"type": "gazon" if rem == "gazon_tondu" else "plante", "materiau_id": rem},
                  "plantation": {"strates": [{"type": "gazon"}],
                                 "hauteur_max_visibilite_m": regles.valeur("RF-GV-TPC-011", "zone_hauteur")[0]},
                  "marquage_contour": {"modulation": "aucune"}}
            ilots.append({"id": idc, "type": "central_giratoire", "polygone": poly_schema(cercle(self.Ri_inf)),
                          "carrefour": cid, "terre_plein": tp,
                          "prov": {"*": P.solveur("giratoire", regle="RF-GV-GIR-006",
                                                  note=f"rayon {self.Ri_inf:.2f} m (Rg − anneau − couronne) ; bordure ≤ 6 cm "
                                                       "au-dessus de l'anneau ; couronne de 2 m sans masque"
                                                       + ("" if self.agglo else " ; hors agglomération : aucun "
                                                          "obstacle agressif (ACI p. 84)"))}})
        # branches : lignes cédez, passages, îlots séparateurs
        branches = []
        prov = {"type": self.pd("type") if self.desc.get("type") else P.defaut("RF-OSM-CAR-002", note="giratoire décrit"),
                "regime": P.inference("RF-OSM-CAR-002", note="entrée de giratoire : cédez le passage obligatoire"),
                "anneau": P.description(self.chemin, self.conf(), regle="RF-GV-GIR-004",
                                        note=f"Rg {self.Rg} m ; anneau {self.la} m ; couronne {self.bf} m")}
        passages = []
        h = regles.valeur("DEF-025", "hauteur_trottoir_agglo" if self.agglo else "hauteur_rase_campagne")
        rap_b = {}
        for x in self.br:
            bid = f"B-{x.nom}"
            x.bid = bid
            bo = {"id": bid, "route": x.rid, "extremite": x.extremite, "azimut_deg": _r(x.azimut, 3),
                  "bandes_entrantes": [b["id"] for b in x.entrantes], "bandes_sortantes": [b["id"] for b in x.sortantes],
                  "regime": "entree_giratoire" if x.entrantes else "sortie_seule"}
            prov[f"branches[{bid}].regime"] = P.inference("RF-OSM-CAR-002", note="entrée de giratoire")
            if x.ligne:
                la = {"type": "CEDEZ", "distance_m": 0.0, "bandes": [b["id"] for b in x.entrantes],
                      "largeur_m": regles.valeur("RF-MQ-CED-01", "largeur"), "modulation": "T'2", "regle": "RF-MQ-CED-01"}
                bo["ligne_arret"] = la
                prov[f"branches[{bid}].ligne_arret"] = P.defaut("DEF-012", note="ligne cédez au bord de l'anneau (0 m)")
                xm = 0.25
                wa = min(b["w0"] for b in x.entrantes)
                wb = max(b["w1"] for b in x.entrantes)
                self.marquages.append({"id": f"M-{cid[2:]}.{x.nom}.cedez", "type": "ligne_transversale", "gabarit": "CEDEZ",
                                       "ancrage": {"route": x.rid, "s": _r(x.s_de_x(xm)), "carrefour": cid, "branche": bid},
                                       "geometrie": [xy_r(x.pt(xm, wa)), xy_r(x.pt(xm, wb))], "couleur": "blanc",
                                       "regles": ["RF-MQ-CED-01", "RF-GV-GIR-024"],
                                       "prov": {"*": P.defaut("RF-GV-GIR-024", note="ligne cédez obligatoire à chaque entrée")}})
            if x.passage:
                ppid = f"PP-{cid[2:]}.{x.nom}"
                bo["passage_pieton"] = ppid
                passages.append({"id": ppid, "route": x.rid, "s": _r(x.passage["s"]),
                                 "axe": [xy_r(x.pt(x.passage["xc"], x.w_d - 1)), xy_r(x.pt(x.passage["xc"], x.w_g + 1))],
                                 "largeur_m": x.passage["largeur"], "regime": "non_gere", "abaisses": True, "bev": True,
                                 "prov": {"*": x.passage["prov"]}})
            il = self._ilot_separateur(x)
            if il:
                ilots.append(il)
                bo["ilot_separateur"] = il["id"]
                if x.passage:
                    passages[-1]["refuge"] = il["id"]
            branches.append(bo)
            # signaux : AB25 en amont (10-50 m agglo, 150 m hors), AB3a + M9c hors agglomération, B21-1 face à l'entrée
            if x.entrantes:
                dist = regles.valeur("RF-SV-AB25.DISTANCE.GENERATEUR", "agglo_m")[1] if self.agglo else \
                    regles.valeur("RF-SV-AB25.DISTANCE.GENERATEUR", "rase_campagne_m")
                s = x.s_de_x(dist)
                gam = gamme_panneau(x.tr.ctx)
                dl = regles.valeur("DEF-025", "bord_panneau_a_la_rive") + GAMME_LARGEUR["triangle"][gam] / 2
                if not self.agglo:
                    dl = max(dl, regles.valeur("RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "support_min_m"))
                if 0 <= s <= x.tr.L:
                    wv = self._w_bord(x, dist) + dl
                    self.signaux.append(signal(f"SG-{cid[2:]}.{x.nom}.AB25", "panneau", "AB25", x.pt_route(dist, wv),
                                               ang((-x.u[0], -x.u[1])), x.rid, s, "droite",
                                               ["RF-SV-AB25.EMPLOI", "RF-SV-AB25.DISTANCE.GENERATEUR", "RF-GV-GIR-024", "DEF-025"],
                                               {"*": P.defaut("RF-SV-AB25.DISTANCE.GENERATEUR", note=f"AB25 à {dist} m de l'anneau")},
                                               hauteur=h, gamme=gam, applic={"carrefour": cid, "branche": bid, "route": x.rid},
                                               support={"type": "poteau"}, t=x.t_route(wv)))
                else:
                    self.av.append(f"{x.chemin} : AB25 à {dist} m hors du tronçon (le prolonger)")
                if not self.agglo:
                    xs = 1.0
                    wv = x.w_g + dl
                    self.signaux.append(signal(f"SG-{cid[2:]}.{x.nom}.AB3a", "panneau", "AB3a", x.pt(xs, wv),
                                               ang((-x.u[0], -x.u[1])), x.rid, x.s_de_x(xs), "droite",
                                               ["RF-SV-AB3A.POSITION", "RF-GV-GIR-024", "DEF-025"],
                                               {"*": P.defaut("RF-GV-GIR-024", note="AB3a + M9c obligatoires hors agglomération")},
                                               hauteur=h, gamme=gam, panonceaux=["M9c"],
                                               applic={"carrefour": cid, "branche": bid, "route": x.rid},
                                               support={"type": "poteau"}, t=x.t_route(wv)))
                if self.type != "mini_giratoire":
                    # B21-1 sur l'îlot central, face à l'entrée (sur l'axe de la voie d'entrée prolongée)
                    wm = (min(b["w0"] for b in x.entrantes) + max(b["w1"] for b in x.entrantes)) / 2
                    p0 = x.pt(0.0, wm)
                    dirc = unit(self.centre[0] - p0[0], self.centre[1] - p0[1])
                    rpos = self.Ri_inf - 0.7 - 0.35
                    pb = (self.centre[0] - dirc[0] * rpos, self.centre[1] - dirc[1] * rpos)
                    self.signaux.append(signal(f"SG-{cid[2:]}.{x.nom}.B21-1", "panneau", "B21-1", pb, ang(dirc), x.rid,
                                               x.s_ext, "ilot", ["RF-SV-B21.EMPLOI", "RF-GV-GIR-024", "RF-OBS-SIG-01", "ARB-04"],
                                               {"*": P.defaut("RF-GV-GIR-024", note="B21-1 face à chaque entrée sur l'îlot "
                                                                                    "central (sauf mini-giratoire)")},
                                               hauteur=regles.valeur("DEF-026", "J5"), gamme="petite",
                                               applic={"carrefour": cid, "branche": bid}, support={"type": "ilot"}))
            rap_b[x.nom] = {"azimut_deg": _r(x.azimut, 2), "entrantes": [b["id"] for b in x.entrantes],
                            "sortantes": [b["id"] for b in x.sortantes],
                            "largeur_entree_m": _r(sum(b["w1"] - b["w0"] for b in x.entrantes), 3),
                            "largeur_sortie_m": _r(sum(b["w1"] - b["w0"] for b in x.sortantes), 3),
                            "passage": None if not x.passage else {"retrait_m": x.passage["retrait"], "x0_m": _r(x.passage["x0"], 3)}}
        # trajectoires (entrée → anneau → sortie), conflits topologiques, déflexion
        traj, conflits, defl = self._trajectoires(branches)
        prov["trajectoires"] = P.solveur("giratoire", regle="RF-GV-TRJ-006", note="entrée – arc d'anneau – sortie")
        raccords = self._raccords()
        anneau_d = {"rayon_exterieur_m": _r(self.Rg), "largeur_anneau_m": _r(self.la), "rayon_ilot_central_m": _r(self.Ri),
                    "bande_franchissable_m": _r(self.bf), "nb_voies": 1, "ilot_central": idc, "sens": "trigonometrique",
                    "construction": {"Rg": self.Rg, "Ri_infranchissable": _r(self.Ri_inf), "route_anneau": rid,
                                     "raccordements": raccords}}
        prov["anneau"]["note"] += " ; raccordements : " + "; ".join(
            f"{k} Re {v['entree_m']} Rs {v['sortie_m']} ({v['source']})" for k, v in raccords.items())
        cdict = {"id": cid, "type": self.type, "regime": "giratoire", "noeuds": [nid], "centre": xy_r(self.centre),
                 "branches": branches, "frontiere": [{"type": "joint", "route": x.rid, "extremite": x.extremite,
                                                      "s0": _r(x.s_ext), "s1": _r(x.s_ext)} for x in self.br],
                 "ilots": [i["id"] for i in ilots], "anneau": anneau_d, "trajectoires": traj, "conflits": conflits}
        if passages:
            cdict["passages_pieton"] = passages
        cdict["regles"] = ["RF-OSM-CAR-002", "RF-GV-GIR-003", "RF-GV-GIR-004", "RF-GV-GIR-006", "RF-GV-GIR-008",
                           "RF-GV-GIR-013", "RF-GV-GIR-024", "DEF-024"]
        if self.type == "mini_giratoire":
            cdict["regles"].append("RF-GV-GIR-016")
        cdict["prov"] = {k: prov[k] for k in sorted(prov, key=lambda k: (not k.startswith(("type", "regime")), k))}
        modele["carrefours"].append(cdict)
        for b in branches:
            sids = [s["id"] for s in self.signaux if (s.get("applicabilite") or {}).get("branche") == b["id"]]
            if sids:
                b["signaux"] = sids
        tous["signaux"] += self.signaux
        tous["marquages"] += self.marquages
        tous["ilots"] += ilots
        # contrôles
        self._controles(defl)
        self.rapport.update({"Rg_m": self.Rg, "diametre_m": 2 * self.Rg, "anneau_m": self.la, "couronne_m": self.bf,
                             "Ri_m": _r(self.Ri, 3), "Ri_infranchissable_m": _r(self.Ri_inf, 3), "route_anneau": rid,
                             "branches": rap_b, "ilots": [i["id"] for i in ilots], "deflexion_m": defl,
                             "conflits": self.compte, "signaux": sorted({s["code"] for s in self.signaux}),
                             "nb_signaux": len(self.signaux), "passages": [p["id"] for p in passages]})

    def _raccords(self):
        """Rayons de raccordement des bordures d'entrée (Re) et de sortie (Rs) sur l'anneau : dits par branche, sinon
        ACI tableau 1 (RF-GV-GIR-003) à la ligne de Rg la plus proche ; contrôlés aux plages RF-GV-GIR-011 / -012."""
        tab = regles.valeur("RF-GV-GIR-003")
        k = min(tab, key=lambda r: abs(float(r) - self.Rg))
        out = {}
        for x in self.br:
            d = x.desc_b
            if self.type == "mini_giratoire":
                # mini-giratoire : raccords comme des angles de rue (DEF-010, desserte) si non dits
                dflt, src0 = float(regles.valeur("DEF-010", "desserte")), "DEF-010 desserte"
            else:
                dflt, src0 = None, f"RF-GV-GIR-003 tableau 1, Rg {k}"
            re_ = _v(d["rayon_entree"], x.chemin + ".rayon_entree") if d.get("rayon_entree") is not None else (dflt or float(tab[k]["Re"]))
            rs_ = _v(d["rayon_sortie"], x.chemin + ".rayon_sortie") if d.get("rayon_sortie") is not None else (dflt or float(tab[k]["Rs"]))
            src = "dit" if d.get("rayon_entree") is not None else src0
            out[f"B-{x.nom}"] = {"entree_m": re_, "sortie_m": rs_, "source": src}
            x.Re, x.Rs = re_, rs_
            if self.type != "mini_giratoire":
                plage_e = regles.valeur("RF-GV-GIR-011", "urbain" if self.agglo else "interurbain")
                self.controle("rayon_entree", re_, (plage_e[0], min(plage_e[1], self.Rg)), "RF-GV-GIR-011", branche=x.nom)
                self.controle("rayon_sortie", rs_, tuple(regles.valeur("RF-GV-GIR-012", "rayon")), "RF-GV-GIR-012",
                              branche=x.nom)
        return out

    def _w_bord(self, x, dist):
        s = x.s_de_x(dist)
        p = x.tr.profil_a(s)
        T = D.t_limites(p, s)
        ws = [x.sg * T[i] for i, b in enumerate(p["bandes"]) if b["niveau"]["reference"] == "chaussee"] + \
             [x.sg * T[i + 1] for i, b in enumerate(p["bandes"]) if b["niveau"]["reference"] == "chaussee"]
        return max(ws)

    def _ilot_separateur(self, x):
        """Îlot séparateur de branche : ACI tableau 2 (RF-GV-GIR-013) — H = Rg, B = Rg/4, d = (0,5 + Rg/50)/2 (0 si
        Rg < 15), r = Rg/50 (0,25 si Rg < 15) ; retrait de 1 m sur l'anneau ; saillie à 0,50 m de l'enveloppe peinte.
        Mini-giratoire : îlot de 0,85 à 2,00 m (RF-GV-GIR-016), franchissable ou peint, dit dans la description.
        L'enveloppe (triangle de base B sur l'anneau et de sommet à H) doit tenir dans la bande « enveloppe d'îlot »
        (zone neutralisée) que le profil de la branche ouvre à son extrémité (contrôle)."""
        idesc = x.desc_b.get("ilot")
        if idesc is None or (not isinstance(idesc, dict) and not _b(idesc, f"{x.chemin}.ilot")):
            return None
        c = f"{x.chemin}.ilot"
        Rg = self.Rg
        if self.type == "mini_giratoire":
            if not isinstance(idesc, dict) or idesc.get("largeur") is None or idesc.get("longueur") is None:
                raise ErreurReseau(f"{c} : mini-giratoire : largeur (0,85-2,00 m, RF-GV-GIR-016) et longueur de l'îlot à dire")
            B, H = _v(idesc["largeur"], c + ".largeur"), _v(idesc["longueur"], c + ".longueur")
            d, r = 0.0, min(B / 2, 0.25)
            prov = P.description(c, self.conf(), regle="RF-GV-GIR-016")
            self.controle("ilot_mini_largeur", B, tuple(regles.valeur("RF-GV-GIR-016", "ilot_separateur")), "RF-GV-GIR-016",
                          branche=x.nom)
        else:
            tab = regles.valeur("RF-GV-GIR-013", "valeurs")
            if Rg < 15:
                H, B, d, r = Rg, Rg / 4, 0.0, 0.25
            else:
                H, B, d, r = Rg, Rg / 4, (0.5 + Rg / 50) / 2, Rg / 50
            if isinstance(idesc, dict):
                _cles(idesc, {"largeur", "longueur", "note"}, c)
                if idesc.get("largeur") is not None:
                    B = _v(idesc["largeur"], c + ".largeur")
                if idesc.get("longueur") is not None:
                    H = _v(idesc["longueur"], c + ".longueur")
            prov = P.defaut("RF-GV-GIR-013", note=f"ACI tableau 2 : H = Rg = {H:.2f}, B = Rg/4 = {B:.2f}, d = {d:.3f}, r = {r:.3f}")
        ret = regles.valeur("RF-GV-GIR-013", "retrait_anneau")
        sail = 0.5
        if self.type == "mini_giratoire":
            # îlot franchissable du mini-giratoire (RF-GV-GIR-016 : 0,85-2,00 m) : la saillie de 0,50 m des îlots
            # infranchissables ne laisse rien d'un triangle de cette largeur (îlots dégénérés de G3, contrôle de
            # l'étape 2) ; l'îlot franchissable est posé dans l'enveloppe peinte, en retrait du contour 3u de la zone
            # et de l'espace non peint de 2u (IISR7 art. 117-2 A-B : contour 3u, espace non peint 2u)
            sail = 5.0 * float(x.tr.ctx["u"])
        # enveloppe : triangle de base B au bord de l'anneau (x = 0), sommet à x = H, axe décalé de d vers la sortie
        wa = min(b["w0"] for b in x.entrantes) if x.entrantes else 0.0
        wb = max(b["w1"] for b in x.sortantes) if x.sortantes else 0.0
        wm = (wa + wb) / 2 - d
        env = Polygon([x.pt(0.0, wm - B / 2), x.pt(0.0, wm + B / 2), x.pt(H, wm)])
        raised = env.buffer(-sail, join_style="mitre")
        raised = raised.difference(Point(self.centre).buffer(self.Rg + ret, quad_segs=48))
        if raised.is_empty:
            raise ErreurReseau(f"{c} : îlot trop petit (B = {B} m) pour une saillie de {sail} m")
        if raised.geom_type == "MultiPolygon":
            raised = max(raised.geoms, key=lambda g: g.area)
        raised = arrondir_sommets(raised, r)
        iid = f"I-{self.id[2:]}.{x.nom}"
        tp = {"franchissable": "non", "surelevation_m": regles.valeur("DEF-005", "ilot"),
              "ceinture": {"profil": "I2", "vue_m": regles.valeur("DEF-005", "ilot")},
              "remplissage": {"type": "beton", "materiau_id": "beton_balaye"},
              "marquage_contour": {"modulation": "continue", "largeur_u": 3, "retrait_u": 2}}
        if self.type == "mini_giratoire":
            # contour : celui de la zone hachurée de la branche (continue 3u) ; pas de second contour peint autour de
            # l'îlot (il serait sur les lignes de la zone)
            tp = {"franchissable": "vl_pl", "surelevation_m": 0.03, "ceinture": {"profil": "A2", "vue_m": 0.03},
                  "remplissage": {"type": "paves", "materiau_id": "paves_beton"},
                  "marquage_contour": {"modulation": "aucune", "largeur_u": 3, "retrait_u": 2}}
        il = {"id": iid, "type": "goutte_eau" if self.type != "mini_giratoire" else "separateur",
              "polygone": poly_schema(raised), "carrefour": self.id, "terre_plein": tp,
              "nez": [{"position": xy_r(x.pt(H - sail * 2, wm)), "rayon_m": _r(r), "balise": "aucune"}],
              "prov": {"*": prov}}
        # enveloppe dans la bande du profil (zone neutralisée ouverte par la branche) : contrôle
        zone = self._bande_enveloppe(x)
        if zone is not None:
            dehors = raised.difference(zone.buffer(0.02)).area
            self.controle("ilot_dans_enveloppe", dehors, (0.0, 0.05), "RF-GV-GIR-013", ilot=iid,
                          note="surface (m²) de l'îlot en saillie hors de la zone neutralisée du profil")
        else:
            self.av.append(f"{c} : le profil de la branche n'ouvre pas de zone neutralisée pour l'îlot (évènement "
                           "« ouverture ») : îlot posé sur la chaussée")
            self.controle("ilot_dans_enveloppe", raised.area, (0.0, 0.05), "RF-GV-GIR-013", ilot=iid)
        # refuge au droit du passage (RF-GV-GIR-014 : ≥ 2,00 m) ; mini-giratoire : îlot de 0,85-2,00 m, pas un refuge
        if x.passage and self.type != "mini_giratoire":
            seg = LineString([x.pt(x.passage["xc"], wm - 10), x.pt(x.passage["xc"], wm + 10)]).intersection(raised)
            lr = seg.length if not seg.is_empty else 0.0
            il["refuge"] = {"largeur_m": _r(lr), "traversee": f"PP-{self.id[2:]}.{x.nom}", "abaisses": True, "bev": True}
            self.controle("refuge_largeur", lr, (regles.valeur("RF-GV-GIR-014", "largeur_au_passage_min"), None),
                          "RF-GV-GIR-014", ilot=iid)
        x.ilot_raised = raised
        return il

    def _bande_enveloppe(self, x):
        """Emprise (polygone) des bandes zone neutralisée entre les sens, sur le dernier tronçon de la branche."""
        polys = []
        for k in range(0, 60):
            pass
        pts_g, pts_d = [], []
        Lmax = min(x.tr.L, self.Rg * 1.6)
        n = 40
        for k in range(n + 1):
            xx = Lmax * k / n
            s = x.s_de_x(xx)
            p = x.tr.profil_a(s)
            T = D.t_limites(p, s)
            zs = [i for i, b in enumerate(p["bandes"]) if b["type"] == "zone_neutralisee"]
            if not zs:
                break
            i0, i1 = min(zs), max(zs)
            wa, wb = sorted((x.sg * T[i0], x.sg * T[i1 + 1]))
            pts_g.append(x.pt_route(xx, wb))
            pts_d.append(x.pt_route(xx, wa))
        if len(pts_g) < 2:
            return None
        return Polygon(pts_g + pts_d[::-1]).buffer(0)

    def _trajectoires(self, branches):
        """Trajectoires voie à voie : de la voie d'entrée (à la ligne cédez) à l'anneau (axe de l'anneau), arc dans le
        sens trigonométrique, puis à la voie de sortie. Conflits (VU p. 84, RF-GV-TRJ-001) : une convergence par
        entrée (avec la circulation de l'anneau), une divergence par sortie."""
        traj = []
        r_axe = self.Rg - self.la / 2
        C = self.centre
        n = len(self.br)
        for i, x in enumerate(self.br):
            for b in x.entrantes:
                wa = (b["w0"] + b["w1"]) / 2
                A = x.pt(0.0, wa)
                a_in = ang((A[0] - C[0], A[1] - C[1]))
                for j in range(1, n):
                    y = self.br[(i + j) % n]
                    if not y.sortantes:
                        continue
                    bo = y.sortantes[-1]
                    wb = (bo["w0"] + bo["w1"]) / 2
                    B = y.pt(0.0, wb)
                    a_out = ang((B[0] - C[0], B[1] - C[1]))
                    da = (a_out - a_in) % 360.0
                    pts = [A] + arc_pts(C, r_axe, a_in + 8.0, a_in + da - 8.0, 3.0) + [B]
                    mv = "TAD" if j == 1 else ("TAG" if j == n - 1 else "TD")
                    traj.append({"id": f"T-{x.nom}.{b['id']}.{y.nom}", "de": {"branche": f"B-{x.nom}", "bande": b["id"]},
                                 "vers": {"branche": f"B-{y.nom}", "bande": bo["id"]}, "mouvement": "anneau",
                                 "geometrie": [xy_r(p) for p in pts], "largeur_m": _r(b["w1"] - b["w0"]),
                                 "rayon_min_m": _r(r_axe), "tags_graphe": ["vehicule"], "priorite": 2})
        conflits = []
        k = 0
        for x in self.br:
            if x.entrantes:
                k += 1
                conflits.append({"id": f"K-{self.id[2:]}.{k}", "trajectoires": [t["id"] for t in traj if t["de"]["branche"] == f"B-{x.nom}"][:1]
                                 + [t["id"] for t in traj if t["de"]["branche"] != f"B-{x.nom}"][:1],
                                 "type": "convergence", "point": xy_r(x.pt(-self.la / 2, (x.entrantes[0]["w0"] + x.entrantes[-1]["w1"]) / 2))})
        for x in self.br:
            if x.sortantes:
                lst = [t["id"] for t in traj if t["vers"]["branche"] == f"B-{x.nom}"]
                if len(lst) >= 2:
                    k += 1
                    conflits.append({"id": f"K-{self.id[2:]}.{k}", "trajectoires": lst[:2], "type": "divergence",
                                     "point": xy_r(x.pt(-self.la / 2, (x.sortantes[0]["w0"] + x.sortantes[-1]["w1"]) / 2))})
        for c in conflits:
            if len(c["trajectoires"]) < 2 or c["trajectoires"][0] == c["trajectoires"][1]:
                c["trajectoires"] = c["trajectoires"][:1] * 2
        conflits = [c for c in conflits if c["trajectoires"][0] != c["trajectoires"][1]]
        self.compte = {"convergence": sum(1 for c in conflits if c["type"] == "convergence"),
                       "divergence": sum(1 for c in conflits if c["type"] == "divergence")}
        self.compte["VL_VL"] = self.compte["convergence"]
        # déflexion (RF-GV-GIR-008) : trajectoire la plus tendue pour chaque traversée (branches à ≥ 120°) : cercle passant
        # à 2,00 m des bordures d'entrée et de sortie (au bord de l'anneau) et à 1,50 m de l'îlot central
        defl = {}
        for i, x in enumerate(self.br):
            if not x.entrantes:
                continue
            for y in self.br:
                if y is x or not y.sortantes:
                    continue
                a = (y.azimut - x.azimut) % 360.0
                if not (120.0 <= a <= 240.0):
                    continue
                A = x.pt(0.0, x.w_g - 2.0)        # 2 m de la bordure droite d'entrée
                B = y.pt(0.0, y.w_d + 2.0)        # 2 m de la bordure droite de sortie
                rho = self.Ri + 1.5
                Rd = cercle_deflexion(A, B, C, rho)
                defl[f"{x.nom}→{y.nom}"] = None if Rd is None else _r(Rd, 2)
        return traj, conflits, defl

    def _controles(self, defl):
        Rg, la = self.Rg, self.la
        if self.type == "mini_giratoire":
            self.controle("Rext_mini", Rg, tuple(regles.valeur("RF-GV-GIR-016", "Rext")), "RF-GV-GIR-016")
            self.controle("Ri_mini_franchissable", self.Ri, tuple(regles.valeur("RF-GV-GIR-016", "Ri")), "RF-GV-GIR-016")
            self.controle("anneau_mini", la, tuple(regles.valeur("RF-GV-GIR-001", "mini")["anneau"]), "RF-GV-GIR-001")
            self.controle("branches_max", len(self.br), (None, regles.valeur("RF-GV-GIR-016", "branches_max")), "RF-GV-GIR-016")
        else:
            g4 = regles.valeur("RF-GV-GIR-004")
            self.controle("anneau_largeur", la, (g4["min"], g4["max"]), "RF-GV-GIR-004")
            self.controle("Ri_infranchissable", self.Ri_inf, (regles.valeur("RF-GV-GIR-006", "infranchissable_rayon_min"), None),
                          "RF-GV-GIR-006")
            if self.bf > 0:
                self.controle("couronne_franchissable", self.bf, tuple(regles.valeur("RF-GV-GIR-006", "bande_franchissable")),
                              "RF-GV-GIR-006")
            if not self.agglo:
                self.controle("Rg_interurbain", Rg, (regles.valeur("RF-GV-GIR-002", "deconseille_si_inf"), None), "RF-GV-GIR-002")
            for k, v in defl.items():
                self.controle("deflexion", v if v is not None else 1e9,
                              (None, regles.valeur("RF-GV-GIR-008", "max")), "RF-GV-GIR-008", couple=k)
        for x in self.br:
            le = sum(b["w1"] - b["w0"] for b in x.entrantes)
            ls = sum(b["w1"] - b["w0"] for b in x.sortantes)
            if self.type == "mini_giratoire":
                self.controle("entree_mini", le, tuple(regles.valeur("RF-GV-GIR-016", "entree")), "RF-GV-GIR-016", branche=x.nom)
                self.controle("sortie_mini", ls, tuple(regles.valeur("RF-GV-GIR-016", "sortie")), "RF-GV-GIR-016", branche=x.nom)
            elif self.agglo and len(x.entrantes) >= 2:
                # entrée à 2 voies (giratoire multivoie, lot correction de l'étape 2)
                self.controle("entree_urbaine_2_voies", le, tuple(regles.valeur("RF-GV-GIR-010", "urbain_2_voies")),
                              "RF-GV-GIR-010", branche=x.nom)
                self.controle("sortie_1_voie", ls, tuple(regles.valeur("RF-GV-GIR-012", "1_voie")), "RF-GV-GIR-012", branche=x.nom)
            elif self.agglo:
                self.controle("entree_urbaine_1_voie", le, tuple(regles.valeur("RF-GV-GIR-010", "urbain_1_voie")),
                              "RF-GV-GIR-010", branche=x.nom)
                self.controle("sortie_1_voie", ls, tuple(regles.valeur("RF-GV-GIR-012", "1_voie")), "RF-GV-GIR-012", branche=x.nom)
            else:
                self.controle("entree_interurbaine_1_voie", le, (regles.valeur("RF-GV-GIR-010", "interurbain_1_voie"),
                                                                 regles.valeur("RF-GV-GIR-010", "interurbain_1_voie")),
                              "RF-GV-GIR-010", branche=x.nom)
                self.controle("sortie_1_voie", ls, tuple(regles.valeur("RF-GV-GIR-012", "1_voie")), "RF-GV-GIR-012", branche=x.nom)
        # angles entre branches (mini : 80-140°)
        n = len(self.br)
        for i, x in enumerate(self.br):
            y = self.br[(i + 1) % n]
            a = (y.azimut - x.azimut) % 360.0
            if self.type == "mini_giratoire":
                self.controle("angle_branches", a, tuple(regles.valeur("RF-GV-GIR-016", "angles_branches_deg")), "RF-GV-GIR-016",
                              branches=[x.nom, y.nom])
        # branches dirigées vers le centre (excentration à droite exclue, RF-GV-GIR-021)
        for x in self.br:
            ex = abs((self.centre[0] - x.pe[0]) * x.n[0] + (self.centre[1] - x.pe[1]) * x.n[1])
            self.controle("branche_vers_centre", ex, (None, 0.5), "RF-GV-GIR-021", branche=x.nom)


def cercle_deflexion(A, B, O, rho):
    """Rayon du cercle passant par A et B et tangent extérieurement au cercle (O, rho) du côté qui sépare A et B
    de O (trajectoire la plus tendue de la déflexion ACI). None si la corde AB ne coupe pas le cercle (O, rho) : la
    trajectoire peut être rectiligne (déflexion infinie)."""
    if LineString([A, B]).distance(Point(O)) >= rho:
        return None
    M = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
    h = math.dist(A, B) / 2
    nb = unit(-(B[1] - A[1]), B[0] - A[0])
    # la trajectoire contourne l'îlot : son centre est du côté de O sur la médiatrice de AB et le cercle (O, rho) lui est
    # intérieurement tangent (dist(C, O) = R − rho) ; le plus grand R admissible est la déflexion
    so = (O[0] - M[0]) * nb[0] + (O[1] - M[1]) * nb[1]
    sg = 1.0 if so > 0 else -1.0

    def f(t):
        Cc = (M[0] + sg * t * nb[0], M[1] + sg * t * nb[1])
        R = math.hypot(h, t)
        return math.dist(Cc, O) - (R - rho)
    lo, hi = 0.0, 1e4
    if f(lo) >= 0:
        return h
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return math.hypot(h, (lo + hi) / 2)


def construire_troncon_annexe(R, ctxh, rid, trace, profil_txt, chemin, ctx_ref, categorie, n0, n1):
    """Route supplémentaire construite par le réseau (anneau de giratoire) avec la machinerie des tronçons."""
    d = ctxh["d"]
    conf = ctxh["conf"]
    try:
        bandes, limites = FP.analyser(profil_txt, chemin)
    except FP.ErreurFormat as e:
        raise ErreurReseau(str(e))
    cdesc = {"agglomeration": "oui" if ctx_ref["agglomeration"] else "non", "vitesse": ctx_ref["vitesse_kmh"],
             "sens_unique": "oui"}
    ctxd = D.lire_contexte(dict(d, contexte=cdesc), bandes)
    ctxd["prov_vitesse"] = P.solveur("giratoire", note="vitesse des branches")
    bandes, limites = D.resoudre_bandes(bandes, limites, {"contexte": cdesc}, chemin, ctxd)
    mats, mat_bord = D.materiaux_globaux(d, conf)
    ctx = PF.contexte(ctxd["agglomeration"], ctxd["vitesse"], ctx_ref["categorie"], u=ctx_ref["u"], prov_u=ctx_ref.get("prov_u"),
                      prov_agglomeration=ctxd["prov_agglomeration"], prov_vitesse=ctxd["prov_vitesse"], materiaux=mats)
    ctx["marquages"], ctx["usure_marquages"] = {}, ctx_ref.get("usure_marquages")
    tr = D.Troncon(rid, trace, bandes, limites, ctx, chemin, conf)
    tr.construire(ctxh["num_p"])
    for f in tr._apres:
        f()
    modele = R.modele
    route = {"id": rid, "noeud_debut": n0, "noeud_fin": n1, "categorie": categorie, "agglomeration": ctx["agglomeration"],
             "vitesse_kmh": ctx["vitesse_kmh"], "sens_unique": "oui",
             "ligne_reference": {"geometrie": [tr.xy(s, 0.0) for s in trace.abscisses()],
                                 "geometrie_reguliere": [p.vers_schema() for p in trace.primitives],
                                 "longueur_m": _r(trace.longueur)},
             "sections": [{"s0": _r(s["s0"]), "s1": _r(s["s1"]), "profil": s["profil"]} for s in tr.secs],
             "prov": {"categorie": P.solveur("reseau"), "agglomeration": ctxd["prov_agglomeration"],
                      "vitesse_kmh": ctxd["prov_vitesse"], "sens_unique": P.inference("RF-OSM-PRF-002", note="anneau à sens unique"),
                      "ligne_reference": P.solveur("reseau")}}
    modele["profils"] += tr.profils
    modele["routes"].append(route)
    ctxh["trs"].append({"rid": rid, "tr": tr, "desc": {}, "ctx": ctx, "ctxd": ctxd, "chemin": chemin, "route": route})
    return tr, route, ctxd


# ================================================================================================ bretelles
class Bretelle(ObjetReseau):
    """Bretelle d'autoroute (VSA 90/110, Cerema 2014 ; ICTAVRU) reliée à une chaussée principale :
    - entrée (« insertion ») : la bretelle (tronçon) finit au point E.1,00 m sur le bord droit de la chaussée
      principale ; la voie d'insertion (évènement « élargissement » de type insertion sur la principale : zone de
      manœuvre parallèle puis biseau) et le musoir de convergence (chevrons entre E.5,00 m et E.1,00 m) ;
    - sortie (« deboitement ») : la voie de décélération (élargissement de type décélération, biseau du S.1,50 m au
      S.1,00 m) puis la bretelle (tronçon) qui part du point S.1,00 m ; musoir de divergence (chevrons du S.1,00 m au
      S.5,00 m, contour continue 3u, espace 2u, balise J14a au S.5,00 m).
    Les cotes (longueurs, obliquité) sont dites dans la description avec leur source ; ce module construit le nœud de
    jonction, le musoir (îlot peint + nez en saillie), les chevrons et contrôle la continuité géométrique."""

    def __init__(self, R, desc, chemin, k):
        super().__init__(R, desc, chemin, k)
        _cles(desc, CLES_BRETELLE, chemin)
        self.id = f"C-{desc.get('id') or ('E' + str(k + 1))}"
        t = V.norm(desc.get("type", ""))
        if t not in ("entree", "sortie", "insertion", "deboitement"):
            raise ErreurReseau(f"{chemin}.type : entrée (insertion) ou sortie (déboîtement)")
        self.genre = "entree" if t in ("entree", "insertion") else "sortie"
        for k_ in ("principale", "bretelle"):
            if desc.get(k_) is None:
                raise ErreurReseau(f"{chemin}.{k_} : id du tronçon à dire")
        self.rapport.update({"id": self.id, "genre": f"bretelle_{self.genre}"})

    def extremites_utilisees(self):
        return [(str(self.desc["bretelle"]), getattr(self, "ext_b", "?"))]

    def analyser(self, cap):
        self.cap = cap
        d, c = self.desc, self.chemin
        self.tp = self.R.trinfo(d["principale"], c + ".principale", cap)
        self.tb = self.R.trinfo(d["bretelle"], c + ".bretelle", cap)
        trp, trb = self.tp["tr"], self.tb["tr"]
        # voie auxiliaire de la principale (insertion / décélération)
        typ = "voie_insertion" if self.genre == "entree" else "voie_deceleration"
        self.aux = None
        for sec in trp.secs:
            p = next(pp for pp in trp.profils if pp["id"] == sec["profil"])
            for b in p["bandes"]:
                if b["type"] == typ:
                    self.aux = b["id"]
        if self.aux is None:
            raise ErreurReseau(f"{c} : la principale « {d['principale']} » n'a pas de {typ.replace('_', ' ')} "
                               "(évènement « élargissement » de type insertion / décélération)")
        # étendue de la voie auxiliaire
        ss = []
        for sec in trp.secs:
            p = next(pp for pp in trp.profils if pp["id"] == sec["profil"])
            if any(b["id"] == self.aux for b in p["bandes"]):
                ss.append((sec["s0"], sec["s1"], p))
        self.s_aux0, self.s_aux1 = ss[0][0], ss[-1][1]
        # point de jonction : extrémité de la bretelle la plus proche du bord droit de la voie auxiliaire
        Lb = trb.L
        ends = [(0.0, "debut"), (Lb, "fin")]
        best = None
        for s_b, ex in ends:
            xb, yb, capb = trb.trace.point(s_b)
            # projection sur la principale (recherche)
            s_p, dmin = None, None
            for k in range(0, 2001):
                sp = trp.L * k / 2000
                xp, yp, _ = trp.trace.point(sp)
                dd = math.hypot(xp - xb, yp - yb)
                if dmin is None or dd < dmin:
                    s_p, dmin = sp, dd
            if best is None or dmin < best[3]:
                best = (s_b, ex, s_p, dmin, (xb, yb), capb)
        self.s_b, self.ext_b, self.s_p, _, self.pj, self.capb = best
        if self.genre == "entree" and self.ext_b != "fin":
            raise ErreurReseau(f"{c} : une bretelle d'entrée se termine sur la principale (tracer le tronçon vers elle)")
        if self.genre == "sortie" and self.ext_b != "debut":
            raise ErreurReseau(f"{c} : une bretelle de sortie part de la principale (tracer le tronçon depuis elle)")
        # bord gauche de la bretelle à la jonction / bord droit de la principale (voie auxiliaire)
        s_chk = min(max(self.s_p + (0.5 if self.genre == "entree" else -0.5), 0.0), trp.L)
        pp = trp.profil_a(s_chk)
        T = D.t_limites(pp, s_chk)
        ids = [b["id"] for b in pp["bandes"]]
        if self.aux not in ids:
            raise ErreurReseau(f"{c} : à la jonction (s = {self.s_p:.1f} m sur la principale), la voie auxiliaire n'existe pas")
        i = ids.index(self.aux)
        self.t_aux = (T[i], T[i + 1])       # (gauche, droite)
        pb = trb.profil_a(min(max(self.s_b, 1e-6), trb.L - 1e-6))
        Tb = D.t_limites(pb, self.s_b)
        mot = [k for k, b in enumerate(pb["bandes"]) if b["type"] in PF.VOIES_MOTORISEES]
        self.tb_voies = (Tb[min(mot)], Tb[max(mot) + 1])
        # écart entre le bord droit de la voie auxiliaire et la voie de la bretelle à la jonction
        xb, yb = self.pj
        xd, yd = trp.trace.point_st(self.s_p, self.t_aux[1])
        xg, yg = trp.trace.point_st(self.s_p, self.t_aux[0])
        _, _, capp = trp.trace.point(self.s_p)
        self.obliquite = abs(math.tan(norm180(math.degrees(self.capb - capp)) * math.pi / 180.0))
        # l'axe de la voie de la bretelle doit tomber dans la voie auxiliaire (continuité de la voie à la jonction)
        nP = (-math.sin(capp), math.cos(capp))
        xv, yv = trb.trace.point_st(self.s_b, (self.tb_voies[0] + self.tb_voies[1]) / 2)
        t_b = (xv - trp.trace.point(self.s_p)[0]) * nP[0] + (yv - trp.trace.point(self.s_p)[1]) * nP[1]
        self.t_b = t_b
        self.ecart_axe = t_b - (self.t_aux[0] + self.t_aux[1]) / 2

    def construire(self, R, modele, ctxh):
        d, c = self.desc, self.chemin
        tous = ctxh["tous"]
        trp, trb = self.tp["tr"], self.tb["tr"]
        cid = self.id
        nid = f"N-{cid}"
        # nœud de jonction : la bretelle s'y raccroche, la principale passe (nœud « fourche »)
        rb = next(r for r in modele["routes"] if r["id"] == self.tb["rid"])
        rb["noeud_fin" if self.ext_b == "fin" else "noeud_debut"] = nid
        rb["carrefour_fin" if self.ext_b == "fin" else "carrefour_debut"] = cid
        modele["noeuds"].append({"id": nid, "position": xy_r(self.pj), "type": "fourche", "carrefour": cid,
                                 "routes": sorted([self.tb["rid"], self.tp["rid"]]),
                                 "prov": {"type": P.solveur("bretelle", regle="RF-OSM-CAR-001",
                                                            note="divergence / convergence sans ligne d'arrêt")}})
        # musoir : zone entre le bord droit de la principale (bord gauche de la BAU / voie auxiliaire) et le bord
        # gauche de la bretelle, du point à 1,00 m au point à 5,00 m (chevrons), puis nez en saillie
        pb_voies = self.tb_voies
        sg_b = 1.0 if self.ext_b == "debut" else -1.0      # sens de parcours de la bretelle en s'éloignant de la jonction
        pts_chev_g, pts_chev_d = [], []
        lst = []
        Lb = trb.L
        x_1, x_5, x_n = None, None, None
        # bord gauche de la bretelle (côté principale) : t le plus grand de ses voies ; bord droit de la principale :
        # t le plus petit de sa dernière voie (principale à gauche de la bretelle)
        for k in range(0, 801):
            sb = (k * 0.25) if self.ext_b == "debut" else Lb - k * 0.25
            if not (0 <= sb <= Lb):
                break
            pbp = trb.profil_a(sb)
            Tb = D.t_limites(pbp, sb)
            mot = [j for j, b in enumerate(pbp["bandes"]) if b["type"] in PF.VOIES_MOTORISEES]
            tg_b = Tb[min(mot)]          # bord gauche des voies de la bretelle (côté principale)
            Pb = trb.trace.point_st(sb, tg_b)
            # point le plus proche sur le bord droit des voies de la principale (voie la plus à droite hors auxiliaire)
            sp = self._s_proche(trp, Pb)
            pp = trp.profil_a(sp)
            Tp = D.t_limites(pp, sp)
            motp = [j for j, b in enumerate(pp["bandes"]) if b["type"] in PF.VOIES_MOTORISEES and b["id"] != self.aux]
            tp_d = Tp[max(motp) + 1]
            Pp = trp.trace.point_st(sp, tp_d)
            gap = math.dist(Pb, Pp)
            lst.append((k * 0.25, gap, Pb, Pp))
            if x_1 is None and gap >= 1.0:
                x_1 = k * 0.25
            if x_5 is None and gap >= 5.0:
                x_5 = k * 0.25
                break
        if x_1 is None or x_5 is None:
            raise ErreurReseau(f"{c} : la bretelle ne s'écarte pas de 5 m de la principale sur 200 m (vérifier le tracé)")
        chev = [q for q in lst if q[0] >= x_1 - 1e-9]
        poly_chev = Polygon([q[2] for q in chev] + [q[3] for q in chev][::-1]).buffer(0)
        # nez physique (tpl) : 0,70 m de part et d'autre de la balise (VSA p. 39, note 23) — îlot en saillie au-delà
        nez_x = x_5 + 2.0
        nez_pts = [(xx, g, Pb, Pp) for (xx, g, Pb, Pp) in lst]
        Pn_b, Pn_p = lst[-1][2], lst[-1][3]
        mid5 = ((Pn_b[0] + Pn_p[0]) / 2, (Pn_b[1] + Pn_p[1]) / 2)
        ilot_peint = {"id": f"I-{cid[2:]}.musoir_peint", "type": "ilot_peint", "polygone": poly_schema(poly_chev),
                      "carrefour": cid,
                      "terre_plein": {"franchissable": "peint", "remplissage": {"type": "hachures_peintes"},
                                      "marquage_contour": {"modulation": "continue", "largeur_u": 3, "retrait_u": 2},
                                      "hachures": {"angle_deg": regles.valeur("DEF-020", "angle_rive_deg"),
                                                   "bande_m": regles.valeur("DEF-020", "bande"),
                                                   "espacement_m": regles.valeur("DEF-020", "espacement"),
                                                   "aplat_sous_m": regles.valeur("DEF-020", "aplat_si_largeur_inf")}},
                      "prov": {"*": P.solveur("bretelle", regle="RF-MQ-MUS-01",
                                              note=f"musoir entre le point à 1,00 m ({'E' if self.genre == 'entree' else 'S'}.1,00, "
                                                   f"à {x_1:.1f} m de la jonction) et le point à 5,00 m (à {x_5:.1f} m) ; "
                                                   "contour continue 3u, espace 2u (RF-MQ-MUS-01) ; chevrons (RF-MQ-HACH-02)")}}
        chevrons = {"id": f"M-{cid[2:]}.chevrons", "type": "chevrons", "geometrie": poly_schema(poly_chev),
                    "ancrage": {"carrefour": cid, "route": self.tp["rid"], "s": _r(self.s_p)}, "couleur": "blanc",
                    "regles": ["RF-MQ-HACH-02", "RF-OSM-CAR-051", "DEF-020"],
                    "prov": {"*": P.defaut("RF-MQ-HACH-02", note="chevrons aux divergences / convergences, pointe vers le "
                                                                "conducteur ; dimensions des hachures (DEF-020)")}}
        balise = signal(f"SG-{cid[2:]}.J14a", "balise", "J14a", mid5,
                        math.degrees(self.capb) + (0 if self.genre == "sortie" else 180), self.tp["rid"], self.s_p,
                        "ilot", ["RF-SV-J14"],
                        {"*": P.defaut("RF-SV-J14", note="balise de musoir au point à 5,00 m (S.5,00 / E.5,00, VSA 90/110 p. 29)")},
                        hauteur=None, applic={"carrefour": cid})
        ilots = [ilot_peint]
        # nez en saillie (terre-plein latéral) au-delà du point à 5 m : îlot musoir (VSA p. 29 : tpl)
        lg_nez = d.get("musoir", {}).get("longueur") if isinstance(d.get("musoir"), dict) else None
        if lg_nez is not None:
            lg_nez = _v(lg_nez, c + ".musoir.longueur")
            pts = []
            sb5 = x_5
            for k in range(0, int(lg_nez / 0.5) + 1):
                xx = sb5 + 0.5 * k
                sb = xx if self.ext_b == "debut" else Lb - xx
                if not (0 <= sb <= Lb):
                    break
                pbp = trb.profil_a(sb)
                Tb = D.t_limites(pbp, sb)
                mot = [j for j, b in enumerate(pbp["bandes"]) if b["type"] in PF.VOIES_MOTORISEES]
                tg_b = Tb[min(mot)]          # bord gauche des voies de la bretelle (côté principale)
                Pb = trb.trace.point_st(sb, tg_b)
                sp = self._s_proche(trp, Pb)
                pp = trp.profil_a(sp)
                Tp = D.t_limites(pp, sp)
                motp = [j for j, b in enumerate(pp["bandes"]) if b["type"] in PF.VOIES_MOTORISEES and b["id"] != self.aux]
                Pp = trp.trace.point_st(sp, Tp[max(motp) + 1])
                pts.append((Pb, Pp))
            env = Polygon([a for a, _ in pts] + [b for _, b in pts][::-1]).buffer(0)
            # dégagements : 0,70 m entre la balise et le bord de chaussée (VSA p. 39 note 23) ; saillie 0,50 m
            raised = arrondir_sommets(env.buffer(-0.7, join_style="mitre"), 0.5)
            if not raised.is_empty:
                ilots.append({"id": f"I-{cid[2:]}.musoir", "type": "musoir", "polygone": poly_schema(raised), "carrefour": cid,
                              "terre_plein": {"franchissable": "non", "surelevation_m": regles.valeur("DEF-005", "ilot"),
                                              "ceinture": {"profil": "I2", "vue_m": regles.valeur("DEF-005", "ilot")},
                                              "remplissage": {"type": "gazon", "materiau_id": "gazon_tondu"}},
                              "nez": [{"position": xy_r(mid5), "rayon_m": 0.5, "balise": "aucune"}],
                              "prov": {"*": P.description(c + ".musoir", self.conf(), regle="RF-MQ-MUS-01",
                                                          note="terre-plein latéral (tpl) en saillie au-delà du point à 5 m, "
                                                               "à 0,70 m des bords de chaussée (VSA 90/110 p. 39)")}})
        tous["ilots"] += ilots
        tous["marquages"].append(chevrons)
        tous["signaux"].append(balise)
        # flèches ×4/3 sur la voie de décélération (RF-MQ-DIR-09) : non posées (affectation non dite)
        traj = [{"id": f"T-{cid[2:]}.{'insertion' if self.genre == 'entree' else 'sortie'}",
                 "de": {"branche": "B-bretelle" if self.genre == "entree" else "B-principale", "bande": self.aux},
                 "vers": {"branche": "B-principale" if self.genre == "entree" else "B-bretelle", "bande": self.aux},
                 "mouvement": "insertion" if self.genre == "entree" else "sortie", "tags_graphe": ["vehicule"]}]
        pb_end = trb.profil_a(min(max(self.s_b, 1e-6), Lb - 1e-6))
        motb = [b["id"] for b in pb_end["bandes"] if b["type"] in PF.VOIES_MOTORISEES]
        pp_end = trp.profil_a(self.s_p)
        motp = [b["id"] for b in pp_end["bandes"] if b["type"] in PF.VOIES_MOTORISEES]
        branches = [{"id": "B-principale", "route": self.tp["rid"], "extremite": "fin" if self.s_p > trp.L / 2 else "debut",
                     "bandes_entrantes": [], "bandes_sortantes": [], "regime": "prioritaire"},
                    {"id": "B-bretelle", "route": self.tb["rid"], "extremite": self.ext_b,
                     "bandes_entrantes": motb if self.genre == "entree" else [],
                     "bandes_sortantes": motb if self.genre == "sortie" else [],
                     "regime": "cedez" if self.genre == "entree" else "sortie_seule"}]
        if self.genre == "entree":
            branches[1]["ligne_arret"] = {"type": "virtuelle", "bandes": motb, "regle": "RF-MQ-INS-01"}
        cdict = {"id": cid, "type": "bifurcation", "regime": "cedez" if self.genre == "entree" else "sans_conflit",
                 "noeuds": [nid], "centre": xy_r(self.pj), "branches": branches,
                 "ilots": [i["id"] for i in ilots], "trajectoires": traj,
                 "regles": ["RF-MQ-INS-01" if self.genre == "entree" else "RF-MQ-DEC-01", "RF-MQ-MUS-01", "RF-MQ-HACH-02",
                            "RF-SV-J14", "RF-MQ-SC-06"],
                 "prov": {"type": self.pd("type", note="bretelle décrite (VSA 90/110 p. 29-36)"),
                          "regime": P.defaut("RF-MQ-INS-01", note="la ligne T2 5u de la voie d'insertion vaut ligne cédez")
                          if self.genre == "entree" else P.defaut("RF-MQ-DEC-01", note="sortie : pas de conflit à la divergence"),
                          "branches[B-principale].regime": P.solveur("bretelle", note="chaussée principale"),
                          "branches[B-bretelle].regime": P.defaut("RF-MQ-INS-01") if self.genre == "entree" else P.solveur("bretelle"),
                          "trajectoires": P.solveur("bretelle", note="mouvement d'insertion / de sortie")}}
        if self.genre == "entree":
            cdict["prov"]["branches[B-bretelle].ligne_arret"] = P.defaut("RF-MQ-INS-01", note="pas de ligne transversale")
        modele["carrefours"].append(cdict)
        # contrôles
        aux_l = self.s_aux1 - self.s_aux0
        self.controle("obliquite", self.obliquite, (1 / 33 - 0.004, 1 / 20 + 0.004), "RF-MQ-INS-01",
                      note="obliquité de la bretelle au raccordement (VSA 90/110 p. 38 : entrée 1/33 à 1/20 ; sortie 1/33)")
        self.controle("bretelle_dans_voie_auxiliaire", abs(self.ecart_axe), (None, 0.5 * abs(self.t_aux[0] - self.t_aux[1])),
                      "RF-OSM-CAR-001", note="axe de la bretelle à la jonction dans la voie auxiliaire")
        self.rapport.update({"principale": self.tp["rid"], "bretelle": self.tb["rid"], "voie_auxiliaire": self.aux,
                             "voie_auxiliaire_s": [_r(self.s_aux0, 2), _r(self.s_aux1, 2)],
                             "voie_auxiliaire_longueur_m": _r(aux_l, 2), "jonction_s_principale": _r(self.s_p, 2),
                             "point_1m_depuis_jonction_m": _r(x_1, 2), "point_5m_depuis_jonction_m": _r(x_5, 2),
                             "obliquite": _r(self.obliquite, 4), "musoir_peint_m2": _r(poly_chev.area, 2),
                             "ilots": [i["id"] for i in ilots]})

    @staticmethod
    def _s_proche(tr, P0):
        best, bd = 0.0, None
        lo, hi = 0.0, tr.L
        for it in range(3):
            n = 200
            for k in range(n + 1):
                s = lo + (hi - lo) * k / n
                x, y, _ = tr.trace.point(s)
                dd = math.hypot(x - P0[0], y - P0[1])
                if bd is None or dd < bd:
                    best, bd = s, dd
            pas = (hi - lo) / n
            lo, hi = max(0.0, best - pas), min(tr.L, best + pas)
        return best
