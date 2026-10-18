# -*- coding: utf-8 -*-
"""Résolveur de la couche réseau (lot N1 de CHAINE_CONSTRUCTION.md ; format FORMAT_DESCRIPTION_RESEAU.md).

    python -B recon/generateur/reseau/resoudre_reseau.py DESCRIPTION.yaml [--sortie DOSSIER] [--sans-compiler]
    python -B recon/generateur/reseau/resoudre_reseau.py --composer NOM|SITE1,SITE2,… [--reseau RESEAU.yaml] [--sortie D]

Entrée : une description réseau (`format: description_reseau/0.1`) — nœuds nommés et ancrés (Lambert-93, local, OSM,
site du dossier 13, photo, point d'un tronçon, position relative, intersection), nœuds partagés entre sites
(`reseau_commun`), valeurs approchées (« ≈ 3,5 », « 3 à 5 », « environ 20 m »), positions en mots (« au milieu »,
« à ≈ 20 de N_X », « sur environ 20 m au milieu : terre-plein planté »), accrochage à OSM (`osm: auto`, liste de ways,
chaussées `aller` / `retour`), état décrit, sources, preuves, itinéraires, ouvrages, échangeurs.
Sortie : une description EXACTE au format de l'étape 2 (`description_simple/0.2`, compilée par
`description/description_vers_modele.py` et `description/carrefours.py`, importés sans modification) et un rapport
`compilation_reseau.json` (approximations : texte, plage, valeur retenue, choix mesure / règle / centre ; ancrages
résolus ; ways ; clés non portées par l'étape 2 ; portes P00 et P01 ; contrats de raccord CC-04 aux nœuds partagés).
Une description déjà au format de l'étape 2 traverse le résolveur sans changer d'un octet.

Composition (`--composer`) : plusieurs sites de `recon/generateur/meylan/` réunis en une scène, dans un repère commun ;
les identifiants sont préfixés par l'alias du site ; deux tronçons de sites différents qui se touchent à un nœud
partagé de valence 2 (sans carrefour) sont fusionnés en un seul tronçon (la continuité est alors celle d'une route
unique : pas de couture de bordure, de marquage ni de sol au raccord) ; les autres nœuds partagés sont rapportés.

Règle tenue : rien n'est inventé. Une valeur approchée est une contrainte (plage), choisie par une mesure, sinon une
règle de `regles_route_fr.json` dans la plage, sinon le centre — et le choix est écrit. Ce qui ne se résout pas
arrête la résolution avec un message.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "schema"))
sys.path.insert(0, str(ICI))
import regles  # noqa: E402
from commun import profil as PF  # noqa: E402
from description import description_vers_modele as D  # noqa: E402
from description import format_profil as FP  # noqa: E402
from description import vocabulaire as V  # noqa: E402
from description import yaml_simple  # noqa: E402
import approx as AX  # noqa: E402
import osm_reseau as OSM  # noqa: E402
import yaml_ecrire as YE  # noqa: E402
import fusion as FU  # noqa: E402
from fusion import inverser_profil_texte, a_evenement as _a_evenement  # noqa: E402,F401

VERSION = "resoudre_reseau/1.0"
FORMAT_RESEAU = "description_reseau/0.1"
FORMAT_ETAPE2 = "description_simple/0.2"
MEYLAN = GEN / "meylan"
SITES_DOSSIER13 = Path(r"D:\DocRoute\13_Observations_Panoramax_Isere\sites.json")
SORTIE_DEFAUT = DEPOT / "recon" / "out" / "generateur"

# clés de la couche réseau (racine) en plus de celles de l'étape 2 (description_vers_modele.CLES_RACINE)
CLES_RACINE_RESEAU = {"reseau", "etat", "date_etat", "sources", "reseau_commun", "noeuds", "itineraires", "ouvrages",
                      "echangeurs", "extensions_auto", "extensions", "preuves", "notes", "retenue", "equipements",
                      "talus", "composition"}
# clés de tronçon de la couche réseau (en plus de description_vers_modele.CLES_TRONCON)
CLES_TRONCON_RESEAU = {"osm", "bdtopo", "tolerance_trace", "z", "jumele_avec", "itineraire", "ref", "categorie",
                       "vitesse", "vitesse_kmh", "agglomeration", "preuves", "ecarts_admis", "materiaux", "marquages",
                       "retenue", "equipements", "talus", "note", "notes", "confiance", "sens_unique", "u", "u_m"}
CLES_CONTEXTE_TRONCON = {"categorie", "vitesse", "vitesse_kmh", "agglomeration", "sens_unique", "u", "u_m"}
CLES_NOEUD = {"position", "repere", "osm", "osm_pres_de", "site", "photo", "sur", "a", "depuis", "distance", "cap",
              "intersection", "type", "z", "preuves", "note", "profil", "cap_profil", "sites", "troncons",
              "tolerance", "raccord", "proprietaire", "ecarts_admis"}
TYPES_NOEUD = {"limite_carte", "impasse", "fourche", "raccord", "connexion"}
# grandeurs approchées admises hors des profils : clé → (genre de plage, règle de la grandeur)
NUMERIQUES = {
    "coin": ("rayon", ("DEF-010", "bus_PL_occasionnels")), "rayon": ("rayon", None), "rayon_entree": ("rayon", None),
    "rayon_sortie": ("rayon", None), "diametre": ("diametre", None), "anneau": ("diametre", ("DEF-024", "anneau")),
    "couronne": ("largeur_ortho", None), "trottoir": ("largeur_photo", ("DEF-004", None)),
    "largeur": ("largeur_photo", None), "largeur_voie": ("largeur_photo", None), "retrait": ("largeur_photo", None),
    "biseau": ("longueur", None), "longueur": ("longueur", None), "obliquite": ("angle", None),
    "quai": ("longueur", None), "hauteur": ("hauteur", None), "vert": ("longueur", None), "transition": ("longueur", None),
    "pas": ("longueur", None), "interdistance": ("longueur", None),
}
INTERDITS_APPROX = {"regime", "mouvements", "code", "vitesse", "vitesse_kmh", "sens", "nombre"}


class ErreurReseau(D.ErreurDescription):
    pass


def _r(x, nd=3):
    return round(float(x), nd) + 0.0


def _bas(x):
    """Arrondi par défaut au micromètre (abscisse d'un évènement posé au bout d'un tronçon : jamais au-delà de L)."""
    return math.floor(float(x) * 1e6) / 1e6


def sha256(o: bytes) -> str:
    return hashlib.sha256(o).hexdigest()


# ===================================================================================================== détection
def est_reseau(d) -> bool:
    """Vrai si la description utilise la couche réseau (format déclaré, clé réseau, nœud nommé ou valeur approchée)."""
    if not isinstance(d, dict):
        return False
    if str(d.get("format", "")).startswith("description_reseau"):
        return True
    cles = {V.norm_cle(k) for k in d}
    if cles & CLES_RACINE_RESEAU:
        return True
    trs = d.get("troncons") or []
    for t in trs if isinstance(trs, list) else []:
        if isinstance(t, dict) and (isinstance(t.get("de"), str) or isinstance(t.get("vers"), str)
                                    or any(V.norm_cle(k) in CLES_TRONCON_RESEAU - D.CLES_TRONCON for k in t)):
            return True
    for k in ("carrefours", "giratoires"):
        for c in d.get(k) or []:
            if isinstance(c, dict) and ("noeud" in c or "nœud" in c):
                return True
    return False


# ===================================================================================================== utilitaires
def _norm_nom(s) -> str:
    return str(s).strip()


def _num(v, chemin):
    try:
        return V.nombre(v, chemin)
    except ValueError as e:
        raise ErreurReseau(str(e))


def charger_yaml(chemin: Path):
    try:
        return yaml_simple.charger(chemin.read_text(encoding="utf-8"))
    except yaml_simple.ErreurYaml as e:
        raise ErreurReseau(f"{chemin} : {e}")


def sites_dossier13() -> dict:
    if not SITES_DOSSIER13.exists():
        return {}
    d = json.loads(SITES_DOSSIER13.read_text(encoding="utf-8"))
    return {s["id"].split("_")[0]: s for s in d}


# ===================================================================================================== résolution
class Resolveur:
    """Une description réseau → (description exacte de l'étape 2, rapport).

    Tronçons : liste de (chemin, g, t, id) où g porte la géométrie et les clés de tronçon de la couche réseau, et t le
    profil, les évènements, la végétation et la signalisation (g = t pour un tronçon de la liste « troncons » ; pour un
    tronçon unique, g = la clé « troncon » ou la racine, t = la racine)."""

    def __init__(self, d: dict, source: str, dossier: Path | None = None, commun: dict | None = None):
        self.source = source
        self.dossier = dossier
        d = copy.deepcopy(d)
        # les noms de nœuds sont des données, pas des clés : ils ne sont pas normalisés
        brut = {V.norm_cle(k): k for k in d}
        noeuds = d.pop(brut["noeuds"]) if "noeuds" in brut else None
        try:
            self.d = D.normaliser_cles(d)
            if noeuds is not None:
                if not isinstance(noeuds, dict):
                    raise ErreurReseau("noeuds : dictionnaire « NOM: {ancrage} » attendu")
                self.d["noeuds"] = {n: (D.normaliser_cles(v) if isinstance(v, dict) else v) for n, v in noeuds.items()}
            if isinstance(self.d.get("ecarts_admis"), dict):
                self.d["ecarts_admis"] = {str(k).upper().replace("_", "-"): v for k, v in self.d["ecarts_admis"].items()}
        except D.ErreurDescription as e:
            raise ErreurReseau(str(e))
        self.av = []
        self.approx = []
        self.rap = {"version": VERSION, "source": source, "format_entree": FORMAT_RESEAU, "noeuds": {}, "troncons": {},
                    "approximations": self.approx, "non_portes_etape2": {}, "avertissements": self.av}
        self.commun = commun
        self.commun_noeuds = {}
        self.noeuds_desc = {}
        self.pos = {}                 # nœud → (x, y) L93
        self.tol = {}
        self._en_cours = set()
        self.troncons = []
        self.geo = {}                 # id tronçon → polyligne L93 résolue
        self.lg = {}                  # id tronçon → longueur exacte du tracé (m)
        self.ids = {}

    # ------------------------------------------------------------------------------------------------ entrée
    def resoudre(self) -> dict:
        d = self.d
        inconnues = sorted(set(d) - D.CLES_RACINE - CLES_RACINE_RESEAU)
        if inconnues:
            raise ErreurReseau(f"description : clé(s) inconnue(s) {', '.join(inconnues)} (P00-1)")
        self._etat()
        self._origine()
        self._commun()
        self._noeuds_locaux()
        self._lister_troncons()
        for nom in list(self.noeuds_desc):
            self.position(nom)
        self._geometries()
        self._centres()
        self._approximations_globales()
        self._profils()
        self._evenements()
        self._raccords_contrats()
        self._cles_troncons()
        self._fusions_internes()
        self._cles_racine()
        self._porte_p00()
        return self._sortie()

    # ------------------------------------------------------------------------------------------------ état
    def _etat(self):
        d = self.d
        etat = d.get("etat")
        if etat is not None and not isinstance(etat, dict):
            etat = {"nom": str(etat)}
        etat = dict(etat or {})
        dates = {k: str(v) for k, v in (("etat.date", etat.get("date")), ("date_etat", d.get("date_etat")),
                                         ("date", d.get("date"))) if v is not None}
        if len(set(dates.values())) > 1:
            raise ErreurReseau(f"dates d'état contradictoires : {dates} (P00-5 : une date d'état unique)")
        date = next(iter(dates.values()), None)
        if date is not None:
            etat["date"] = date
        self.etat = etat
        self.rap["etat"] = etat

    def _origine(self):
        d = self.d
        o = [_num(x, "origine") for x in d.get("origine", D.ORIGINE_DEPOT)]
        if len(o) == 2:
            o.append(D.ORIGINE_DEPOT[2])
        self.origine = o
        rep = V.norm(d.get("repere", "local"))
        if rep not in ("local", "l93", "relatif"):
            raise ErreurReseau("repere : local, l93 ou relatif")
        self.repere = rep
        self.rap["origine"] = o

    def _commun(self):
        rc = self.d.get("reseau_commun")
        if rc is None and self.commun is None:
            return
        if self.commun is None:
            base = self.dossier or Path.cwd()
            f = (base / str(rc)).resolve()
            if not f.exists():
                raise ErreurReseau(f"reseau_commun : fichier introuvable {f}")
            self.commun = charger_yaml(f)
            try:
                self.rap["reseau_commun"] = str(f.relative_to(DEPOT)).replace("\\", "/")
            except ValueError:
                self.rap["reseau_commun"] = str(f)
        brut = {V.norm_cle(k): k for k in self.commun}
        noeuds = self.commun.get(brut.get("noeuds", "noeuds")) or {}
        for nom, spec in noeuds.items():
            try:
                spec = D.normaliser_cles(dict(spec or {}))
            except D.ErreurDescription as e:
                raise ErreurReseau(f"reseau_commun.noeuds.{nom} : {e}")
            spec.setdefault("repere", "l93")
            self.commun_noeuds[_norm_nom(nom)] = spec

    def _noeuds_locaux(self):
        nd = self.d.get("noeuds") or {}
        if not isinstance(nd, dict):
            raise ErreurReseau("noeuds : dictionnaire « NOM: {ancrage} » attendu")
        for nom, spec in nd.items():
            nom = _norm_nom(nom)
            if not isinstance(spec, dict):
                raise ErreurReseau(f"noeuds.{nom} : ancrage {{position | osm | site | photo | sur | depuis | "
                                   "intersection}} attendu")
            if nom in self.commun_noeuds:
                raise ErreurReseau(f"noeuds.{nom} : nœud déjà déclaré par le réseau commun (le citer sans le redéclarer)")
            inc = sorted(set(spec) - CLES_NOEUD)
            if inc:
                raise ErreurReseau(f"noeuds.{nom} : clé(s) inconnue(s) {', '.join(inc)}")
            self.noeuds_desc[nom] = spec

    def spec_noeud(self, nom):
        nom = _norm_nom(nom)
        if nom in self.noeuds_desc:
            return self.noeuds_desc[nom], False
        if nom in self.commun_noeuds:
            return self.commun_noeuds[nom], True
        raise ErreurReseau(f"nœud « {nom} » non déclaré (ni dans noeuds, ni dans le réseau commun) (P00-2)")

    def est_noeud(self, v) -> bool:
        return isinstance(v, str) and (_norm_nom(v) in self.noeuds_desc or _norm_nom(v) in self.commun_noeuds)

    # ------------------------------------------------------------------------------------------------ nœuds
    def _xy(self, v, repere, chemin):
        if not (isinstance(v, list) and len(v) >= 2):
            raise ErreurReseau(f"{chemin} : point [x, y] attendu")
        x, y = (self._valeur(v[0], f"{chemin}[0]", "longueur"), self._valeur(v[1], f"{chemin}[1]", "longueur"))
        if V.norm(repere) == "l93":
            return (x, y)
        return (self.origine[0] + x, self.origine[1] + y)

    def _tolerance_depuis(self, n0):
        """Tolérance (m) d'une position déduite de valeurs approchées : demi-plage des valeurs lues depuis n0."""
        t = 0.0
        for a in self.approx[n0:]:
            if a.get("plage"):
                h = (a["plage"][1] - a["plage"][0]) / 2.0
                t = max(t, h if a.get("genre") != "angle" else 0.0)
        return t

    def position(self, nom) -> tuple:
        nom = _norm_nom(nom)
        if nom in self.pos:
            return self.pos[nom]
        if nom in self._en_cours:
            raise ErreurReseau(f"nœud « {nom} » : ancrage circulaire")
        self._en_cours.add(nom)
        spec, partage = self.spec_noeud(nom)
        c = f"noeuds.{nom}"
        rep = spec.get("repere", self.repere)
        cand = []                    # (x, y, tolérance, forme)
        info = {"partage": partage}
        if "position" in spec:
            n0 = len(self.approx)
            xy = self._xy(spec["position"], rep, c + ".position")
            cand.append((xy[0], xy[1], float(spec.get("tolerance", 0.0) or 0.0) + self._tolerance_depuis(n0),
                         "position"))
        if "osm" in spec:
            m = re.match(r"^\s*(?:node/)?(\d+)\s*$", str(spec["osm"]))
            if not m:
                raise ErreurReseau(f"{c}.osm : « node/<id> » attendu")
            try:
                n = OSM.noeud(int(m.group(1)))
            except OSM.ErreurOSM as e:
                raise ErreurReseau(f"{c} : {e}")
            cand.append((n["xy"][0], n["xy"][1], 0.0, f"osm:node/{n['id']}"))
        if "site" in spec:
            s = sites_dossier13().get(str(spec["site"]).split("_")[0])
            if s is None:
                raise ErreurReseau(f"{c}.site : site « {spec['site']} » absent de {SITES_DOSSIER13}")
            xy = OSM.l93(s["lon"], s["lat"])
            cand.append((xy[0], xy[1], 15.0, f"site:{s['id']}"))
        if "photo" in spec:
            xy = self._photo(str(spec["photo"]), c)
            cand.append((xy[0], xy[1], 5.0, f"photo:{spec['photo']}"))
        if "depuis" in spec:
            x0, y0 = self.position(spec["depuis"])
            n0 = len(self.approx)
            dist = self._valeur(spec.get("distance"), c + ".distance", "distance")
            cap = self._valeur(spec.get("cap"), c + ".cap", "angle")
            tol = self._tolerance_depuis(n0) + self.tol.get(_norm_nom(spec["depuis"]), 0.0)
            for a in self.approx[n0:]:
                if a.get("genre") == "angle" and a.get("plage"):
                    tol += dist * math.sin(math.radians((a["plage"][1] - a["plage"][0]) / 2.0))
            cand.append((x0 + dist * math.cos(math.radians(cap)), y0 + dist * math.sin(math.radians(cap)), tol,
                         f"depuis:{spec['depuis']}"))
        if "sur" in spec:
            tid = str(spec["sur"])
            pts = self.polyligne_troncon(tid, c)
            L = OSM.longueur(pts)
            n0 = len(self.approx)
            a = self._abscisse(spec.get("a"), L, c + ".a", tid, self._bouts(tid))
            xy = OSM.point_a(pts, a)
            cand.append((xy[0], xy[1], self._tolerance_depuis(n0), f"sur:{tid}@{a:.2f}"))
            info["sur"] = {"troncon": tid, "a": _r(a)}
        if "intersection" in spec:
            t1, t2 = [str(x) for x in spec["intersection"]]
            from shapely.geometry import LineString
            g = LineString(self.polyligne_troncon(t1, c)).intersection(LineString(self.polyligne_troncon(t2, c)))
            if g.is_empty:
                raise ErreurReseau(f"{c}.intersection : les axes de {t1} et {t2} ne se croisent pas")
            p = g if g.geom_type == "Point" else list(getattr(g, "geoms", [g]))[0]
            cand.append((p.x, p.y, 0.0, f"intersection:{t1}×{t2}"))
        if not cand:
            raise ErreurReseau(f"{c} : nœud sans ancrage (P00-2)")
        x, y, tol, forme = cand[0]
        for (x2, y2, t2, f2) in cand[1:]:
            e = math.hypot(x2 - x, y2 - y)
            if e > tol + t2 + 1e-6:
                raise ErreurReseau(f"{c} : ancrages contradictoires {forme} et {f2} (écart {e:.2f} m > {tol + t2:.2f} m)")
            info.setdefault("ecarts", []).append({"ancrages": [forme, f2], "ecart_m": _r(e, 2)})
        if spec.get("osm_pres_de") is not None:
            R = _num(spec["osm_pres_de"], c + ".osm_pres_de")
            sp = OSM.sommet_proche(x, y, R)
            if sp is None:
                raise ErreurReseau(f"{c}.osm_pres_de : aucun sommet de way routier à moins de {R} m")
            info["recalage_osm"] = {"deplacement_m": _r(sp[3], 2), "valence": sp[2]}
            x, y, tol = sp[0], sp[1], R
        self.pos[nom] = (x, y)
        self.tol[nom] = tol
        info.update(ancrage=forme, l93=[_r(x), _r(y)], local=[_r(x - self.origine[0]), _r(y - self.origine[1])],
                    tolerance_m=_r(tol, 2))
        if spec.get("type"):
            t = V.norm_cle(spec["type"])
            if t not in TYPES_NOEUD:
                raise ErreurReseau(f"{c}.type : {', '.join(sorted(TYPES_NOEUD))}")
            info["type"] = t
        for k in ("preuves", "note", "profil", "cap_profil", "z", "sites", "raccord", "proprietaire", "ecarts_admis"):
            if spec.get(k) is not None:
                info[k] = spec[k]
        self.rap["noeuds"].setdefault(nom, {}).update(info)
        self._en_cours.discard(nom)
        return (x, y)

    def _photo(self, pid, chemin):
        base = self.dossier
        for f in ([base / "photos.json"] if base else []) + sorted(MEYLAN.glob("*/photos.json")):
            if not f.exists():
                continue
            d = json.loads(f.read_text(encoding="utf-8"))
            for p in d.get("photos") or []:
                if str(p.get("id", "")).startswith(pid):
                    if p.get("x_l93") is not None:
                        return (float(p["x_l93"]), float(p["y_l93"]))
                    if p.get("lon") is not None:
                        return OSM.l93(float(p["lon"]), float(p["lat"]))
        raise ErreurReseau(f"{chemin}.photo : photo « {pid} » absente des photos.json de meylan/")

    # ------------------------------------------------------------------------------------------------ valeurs
    def _valeur(self, v, chemin, genre, regle=None):
        """Nombre (exact ou approché) → float ; l'approximation est rapportée."""
        if v is None:
            raise ErreurReseau(f"{chemin} : valeur à dire")
        if isinstance(v, bool):
            raise ErreurReseau(f"{chemin} : nombre attendu")
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v)
        if AX.contient_approx(s) or re.search(r"\d\s*(?:m\s+)?(?:à|a)\s+\d", s):
            try:
                ap = AX.lire(s, genre)
            except AX.ErreurApprox as e:
                raise ErreurReseau(f"{chemin} : {e}")
            if ap is None:
                raise ErreurReseau(f"{chemin} : valeur approchée illisible « {s} »")
            try:
                val, ent = AX.choisir(ap, regle, chemin, self.av)
            except AX.ErreurApprox as e:
                raise ErreurReseau(str(e))
            ent["genre"] = genre
            self.approx.append(ent)
            return float(val)
        return _num(s, chemin)

    def _bouts(self, tid):
        info = self.rap["troncons"].get(tid, {})
        return (info.get("de"), info.get("vers"))

    def _abscisse(self, v, L, chemin, tid=None, bouts=None):
        """Abscisse sur un tronçon de longueur L : nombre, plage, ou position en mots (FORMAT § 4.4)."""
        if v is None:
            raise ErreurReseau(f"{chemin} : abscisse à dire")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        s = re.sub(r"\s+", " ", V.sans_accents(str(v)).lower().strip())
        mots = {"au debut": (0.0, 0.15), "au depart": (0.0, 0.15), "au milieu": (0.4, 0.6),
                "a peu pres au milieu": (0.4, 0.6), "a la fin": (0.85, 1.0), "au bout": (0.85, 1.0),
                "a mi-longueur": (0.4, 0.6)}
        if s in mots:
            lo, hi = mots[s][0] * L, mots[s][1] * L
            c = (lo + hi) / 2.0
            self.approx.append({"chemin": chemin, "texte": str(v), "forme": "mots", "plage": [_r(lo), _r(hi)],
                                "valeur": _r(c), "choix": "centre", "genre": "abscisse"})
            self.av.append(f"{chemin} : « {v} » : position approchée, centre {c:.1f} m retenu")
            return c
        if s.startswith(("juste avant", "juste apres", "a la ligne d'arret", "au passage")):
            raise ErreurReseau(f"{chemin} : « {v} » dépend de la frontière du carrefour (FORMAT § 6.4, ancrage symbolique "
                               "non encore porté par l'étape 2) : donner une abscisse depuis un nœud")
        m = re.match(r"^au droit de ([A-Za-z0-9_.\-]+)$", s)
        if m:
            nom = next((n for n in list(self.noeuds_desc) + list(self.commun_noeuds) if n.lower() == m.group(1)), None)
            if nom is None:
                raise ErreurReseau(f"{chemin} : nœud « {m.group(1)} » inconnu")
            x, y = self.position(nom)
            return OSM.projeter(self.geo[tid], x, y)[0]
        m = re.match(r"^(?:a\s+)?(.+?)\s+(de|apres|avant)\s+([A-Za-z0-9_.\-]+)$", s)
        if m and bouts is not None:
            nom = next((n for n in bouts if n and n.lower() == m.group(3)), None)
            if nom is None:
                raise ErreurReseau(f"{chemin} : « {m.group(3)} » n'est pas une extrémité du tronçon "
                                   f"({', '.join(n for n in bouts if n) or 'aucun nœud nommé'})")
            dist = self._valeur(m.group(1), chemin, "abscisse")
            if nom == bouts[1] and nom != bouts[0]:
                return L - dist
            if m.group(2) == "avant":
                raise ErreurReseau(f"{chemin} : « avant {nom} » sort du tronçon ({nom} en est le début)")
            return dist
        s2 = re.sub(r"^a\s+", "", s)
        return self._valeur(s2, chemin, "abscisse")

    # ------------------------------------------------------------------------------------------------ tronçons
    def _lister_troncons(self):
        d = self.d
        if d.get("troncons"):
            if not isinstance(d["troncons"], list):
                raise ErreurReseau("troncons : liste attendue")
            for k, t in enumerate(d["troncons"]):
                if not isinstance(t, dict):
                    raise ErreurReseau(f"troncons[{k}] : dictionnaire attendu")
                inc = sorted(set(t) - D.CLES_TRONCON - CLES_TRONCON_RESEAU)
                if inc:
                    raise ErreurReseau(f"troncons[{k}] : clé(s) inconnue(s) {', '.join(inc)} (P00-1)")
                tid = str(t.get("id") or f"T{k + 1}")
                if tid in self.ids:
                    raise ErreurReseau(f"troncons[{k}].id : « {tid} » en double")
                self.ids[tid] = len(self.troncons)
                self.troncons.append((f"troncons[{k}]", t, t, tid))
            return
        if isinstance(d.get("troncon"), dict):
            g, ch = d["troncon"], "troncon"
            inc = sorted(set(g) - D.CLES_TRONCON - CLES_TRONCON_RESEAU)
            if inc:
                raise ErreurReseau(f"troncon : clé(s) inconnue(s) {', '.join(inc)} (P00-1)")
        elif any(k in d for k in ("trace", "polyligne", "longueur", "de", "vers")):
            g, ch = d, "racine"
        else:
            raise ErreurReseau("aucun tronçon : « troncons: » ou « troncon: » attendu")
        tid = str(g.get("id") or "T1")
        self.ids[tid] = 0
        self.troncons.append((ch, g, d, tid))

    def polyligne_troncon(self, tid, chemin):
        """Polyligne L93 de l'axe d'un tronçon (résolue à la demande, pour les ancrages « sur » et « intersection »)."""
        if tid not in self.ids:
            raise ErreurReseau(f"{chemin} : tronçon « {tid} » inconnu ({', '.join(self.ids)})")
        if tid not in self.geo:
            ch, g, t, _ = self.troncons[self.ids[tid]]
            self._geometrie(ch, g, t, tid)
        return self.geo[tid]

    def _pt_local(self, v, chemin, rep):
        if self.est_noeud(v):
            x, y = self.position(v)
        else:
            x, y = self._xy(v, rep, chemin)
        return [_r(x - self.origine[0]), _r(y - self.origine[1])]

    def _pt_l93(self, v, chemin, rep):
        if self.est_noeud(v):
            return self.position(v)
        return self._xy(v, rep, chemin)

    def _geometrie(self, ch, g, t, tid):
        rep = V.norm(g.get("repere", self.repere))
        info = self.rap["troncons"].setdefault(tid, {})
        info["chemin"] = ch
        de, vers = g.get("de"), g.get("vers")
        for k, v in (("de", de), ("vers", vers)):
            if isinstance(v, str):
                if not self.est_noeud(v):
                    raise ErreurReseau(f"{ch}.{k} : nœud « {v} » non déclaré (P00-2)")
                info[k] = _norm_nom(v)
        for i, p in enumerate(g.get("polyligne") or []):
            if isinstance(p, str):
                if not self.est_noeud(p):
                    raise ErreurReseau(f"{ch}.polyligne[{i}] : nœud « {p} » non déclaré (P00-2)")
                if i == 0:
                    info.setdefault("de", _norm_nom(p))
                elif i == len(g["polyligne"]) - 1:
                    info.setdefault("vers", _norm_nom(p))
        controle_lg = None
        osm = g.get("osm")
        if osm is not None and "polyligne" not in g and "trace" not in g:
            if de is None or vers is None:
                raise ErreurReseau(f"{ch}.osm : « de » et « vers » sont nécessaires pour accrocher le tracé à OSM")
            a = self._pt_l93(de, f"{ch}.de", rep)
            b = self._pt_l93(vers, f"{ch}.vers", rep)
            tol = _num(g.get("tolerance_trace", 15.0), f"{ch}.tolerance_trace")
            try:
                if isinstance(osm, str) and V.norm(osm) == "auto":
                    pts, ways, nature = OSM.auto(g.get("nom") or t.get("nom"), g.get("ref"), a, b, ch, tol)
                    info["osm"] = {"mode": "auto", "ways": [f"way/{w}" for w in ways], "nature": nature}
                elif isinstance(osm, dict):
                    al = OSM.decouper(OSM.chaine(osm["aller"], ch + ".osm.aller"), a, b, ch, tol)
                    rt = OSM.decouper(OSM.chaine(osm["retour"], ch + ".osm.retour"), a, b, ch, tol)
                    pts = OSM.mediane(al, rt)
                    info["osm"] = {"mode": "aller_retour", "aller": osm["aller"], "retour": osm["retour"]}
                else:
                    lst = osm if isinstance(osm, list) else [osm]
                    pts = OSM.decouper(OSM.chaine(lst, ch + ".osm"), a, b, ch, tol)
                    info["osm"] = {"mode": "ways", "ways": [str(w) for w in lst]}
            except OSM.ErreurOSM as e:
                raise ErreurReseau(str(e))
            pts = OSM.simplifier(pts, 0.25)
            pts[0], pts[-1] = a, b
            g["polyligne"] = [[_r(x - self.origine[0]), _r(y - self.origine[1])] for x, y in pts]
            g.pop("de", None)
            g.pop("vers", None)
            info["geometrie"] = "osm"
            controle_lg = g.pop("longueur", None)
        elif "polyligne" in g:
            g["polyligne"] = [self._pt_local(p, f"{ch}.polyligne[{i}]", rep) for i, p in enumerate(g["polyligne"])]
            for k, i in (("de", 0), ("vers", -1)):
                v = g.get(k)
                if v is None:
                    continue
                p = self._pt_local(v, f"{ch}.{k}", rep)
                e = math.dist(p, g["polyligne"][i])
                if e > 0.002:
                    if e > 2.0:
                        raise ErreurReseau(f"{ch}.{k} : le nœud est à {e:.2f} m du bout de la polyligne (> 2 m)")
                    self.av.append(f"{ch}.{k} : bout de polyligne recalé de {e:.2f} m sur le nœud")
                g["polyligne"][i] = p
                g.pop(k)
            info["geometrie"] = "polyligne"
            controle_lg = g.pop("longueur", None)
        elif de is not None and vers is not None and "trace" not in g:
            g["de"] = self._pt_local(de, f"{ch}.de", rep)
            g["vers"] = self._pt_local(vers, f"{ch}.vers", rep)
            info["geometrie"] = "droite"
            controle_lg = g.pop("longueur", None)
        elif "trace" in g:
            if isinstance(g["trace"], str):
                raise ErreurReseau(f"{ch}.trace : tracé qualitatif « {g['trace']} » non porté au lot N1 (régularisation : "
                                   "lot N2) ; écrire le tracé exact (droites, arcs, clothoïdes) ou l'accrocher à OSM")
            if isinstance(g.get("depart"), (str, list)):
                g["depart"] = self._pt_local(g["depart"], f"{ch}.depart", rep)
            info["geometrie"] = "trace"
        else:
            if g.get("depart") is not None:
                g["depart"] = self._pt_local(g["depart"], f"{ch}.depart", rep)
            info["geometrie"] = "longueur"
        g.pop("repere", None)
        try:
            tr = D.lire_trace(g, self.origine, ch)
        except D.ErreurDescription as e:
            raise ErreurReseau(str(e))
        pts = [(tr.point(s)[0], tr.point(s)[1]) for s in tr.abscisses()]
        self.geo[tid] = pts
        self.lg[tid] = tr.longueur
        info["longueur_m"] = _r(tr.longueur, 2)
        if info["geometrie"] == "trace" and info.get("vers"):
            xv, yv = self.position(info["vers"])
            e = math.hypot(pts[-1][0] - xv, pts[-1][1] - yv)
            if e > 0.05:
                raise ErreurReseau(f"{ch} : le tracé finit à {e:.2f} m du nœud « {info['vers']} »")
        if controle_lg is not None:
            n0 = len(self.approx)
            lc = self._valeur(controle_lg, f"{ch}.longueur", "longueur")
            ent = self.approx[n0] if len(self.approx) > n0 else None
            lo, hi = (ent["plage"] if ent else (lc, lc))
            if ent:
                ent["choix"] = "controle"
                ent["valeur"] = info["longueur_m"]
            if not (lo - 0.5 <= tr.longueur <= hi + 0.5):
                self.av.append(f"{ch}.longueur : contrôle « {controle_lg} » non tenu (tracé de {tr.longueur:.1f} m)")

    def _geometries(self):
        for ch, g, t, tid in self.troncons:
            if tid not in self.geo:
                self._geometrie(ch, g, t, tid)
        for tid, info in self.rap["troncons"].items():
            for k in ("de", "vers"):
                if k in info:
                    lst = self.rap["noeuds"].setdefault(info[k], {}).setdefault("troncons", [])
                    if f"{tid}.{k}" not in lst:
                        lst.append(f"{tid}.{k}")

    def _centres(self):
        for cle in ("carrefours", "giratoires"):
            for i, c in enumerate(self.d.get(cle) or []):
                if not isinstance(c, dict):
                    continue
                n = c.pop("noeud", None)
                if n is None:
                    continue
                if "centre" in c:
                    raise ErreurReseau(f"{cle}[{i}] : « noeud » et « centre » à la fois")
                x, y = self.position(n)
                c["centre"] = [_r(x - self.origine[0]), _r(y - self.origine[1])]
                self.rap["noeuds"].setdefault(_norm_nom(n), {})["carrefour"] = c.get("id") or f"{cle}[{i}]"
        for i, b in enumerate(self.d.get("bretelles") or []):
            if isinstance(b, dict) and self.est_noeud(b.get("point")):
                x, y = self.position(b["point"])
                b["point"] = [_r(x - self.origine[0]), _r(y - self.origine[1])]

    # ------------------------------------------------------------------------------------------------ approximations
    def _approximations_globales(self):
        ctx = self.d.get("contexte") or {}
        for k in ("vitesse", "vitesse_kmh"):
            if AX.contient_approx(ctx.get(k)):
                raise ErreurReseau(f"contexte.{k} : la vitesse réglementaire ne s'approche pas (FORMAT § 4.1)")
        for cle in ("carrefours", "giratoires", "bretelles"):
            for i, c in enumerate(self.d.get(cle) or []):
                self._parcourir_numeriques(c, f"{cle}[{i}]")

    def _parcourir_numeriques(self, o, chemin):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                c = f"{chemin}.{k}"
                if k in INTERDITS_APPROX and (AX.contient_approx(v) or (isinstance(v, list) and any(
                        AX.contient_approx(x) for x in v))):
                    raise ErreurReseau(f"{c} : « {v} » : {k} ne s'approche pas (FORMAT_DESCRIPTION_RESEAU § 4.1)")
                if isinstance(v, str) and k in NUMERIQUES and (AX.contient_approx(v) or re.search(r"\d\s*(?:à|a)\s+\d", v)):
                    genre, rg = NUMERIQUES[k]
                    o[k] = _r(self._valeur(v, c, genre, self._regle_numerique(rg)), 4)
                elif isinstance(v, (dict, list)):
                    self._parcourir_numeriques(v, c)
        elif isinstance(o, list):
            for i, x in enumerate(o):
                self._parcourir_numeriques(x, f"{chemin}[{i}]")

    def _regle_numerique(self, rg):
        """(valeur, règle, note) de la règle qui fixe une grandeur non dite, ou None."""
        if not rg:
            return None
        rid, cle = rg
        try:
            if rid == "DEF-010":
                agglo = V.booleen((self.d.get("contexte") or {}).get("agglomeration", "oui"), "contexte.agglomeration")
                if not agglo:
                    return None
            v = regles.valeur(rid, cle) if cle is not None else regles.valeur(rid)
            return (float(v), rid, cle) if isinstance(v, (int, float)) else None
        except Exception:
            return None

    # ------------------------------------------------------------------------------------------------ profils
    def _preuve_ortho(self, g) -> bool:
        pv = " ".join(str(x) for x in (g.get("preuves") or self.d.get("preuves") or []))
        return "ortho" in pv or "mesure" in pv or "coupe" in pv

    def _profils(self):
        for ch, g, t, tid in self.troncons:
            if "profil" not in t:
                continue
            genre = "largeur_ortho" if self._preuve_ortho(g) else "largeur_photo"
            p = t["profil"]
            if isinstance(p, str) and V.norm(p) == "osm":
                t["profil"] = self._profil_osm(g, ch, tid)
            else:
                t["profil"] = self._profil_exact(p, f"{ch}.profil", genre, g)
            for k, e in enumerate(t.get("evenements") or []):
                if isinstance(e, dict) and len(e) == 1:
                    (typ, prm), = e.items()
                    if isinstance(prm, dict) and isinstance(prm.get("nouveau"), str):
                        prm["nouveau"] = self._profil_exact(prm["nouveau"], f"{ch}.evenements[{k}].nouveau", genre, g)

    @staticmethod
    def _a_approx(e) -> bool:
        if isinstance(e, dict):
            return any(AX.contient_approx(v) for v in e.values())
        return AX.contient_approx(e) or bool(re.search(r"\d\s*(?:m\s+)?(?:à|a)\s+\d", str(e)))

    def _profil_exact(self, p, chemin, genre, g):
        try:
            els = FP.elements(p, chemin)
        except FP.ErreurFormat as e:
            raise ErreurReseau(str(e))
        if not any(self._a_approx(e) for e in els):
            return p
        sans = []
        for e in els:
            if isinstance(e, dict):
                sans.append({k: v for k, v in e.items() if not AX.contient_approx(v)})
            elif self._a_approx(e):
                ap = AX.lire(e, genre)
                sans.append(AX.sans_valeur(ap) if ap else e)
            else:
                sans.append(e)
        defauts = self._defauts_largeurs(sans, g, chemin)
        out, ib = [], -1
        for k, e in enumerate(els):
            c = f"{chemin}[{k}]"
            if isinstance(e, dict):
                e = dict(e)
                if "bande" in e:
                    ib += 1
                for kk, v in list(e.items()):
                    if AX.contient_approx(v):
                        gk = "vue" if kk == "vue" else genre
                        rg = defauts.get(ib) if kk == "largeur" else None
                        e[kk] = _r(self._valeur(v, f"{c}.{kk}", gk, rg), 4)
                out.append(e)
                continue
            est_bande = not FP._est_limite(V.jetons(e))
            if est_bande:
                ib += 1
            if not self._a_approx(e):
                out.append(e)
                continue
            try:
                ap = AX.lire(e, genre)
            except AX.ErreurApprox as x:
                raise ErreurReseau(f"{c} : {x}")
            avant = V.sans_accents(e[:ap["debut"]]).lower().strip()
            gk = "vue" if avant.endswith("vue") else genre
            rg = defauts.get(ib) if est_bande and gk != "vue" else None
            try:
                val, ent = AX.choisir(ap, rg, c, self.av)
            except AX.ErreurApprox as x:
                raise ErreurReseau(str(x))
            ent["genre"] = gk
            self.approx.append(ent)
            nv = AX.remplacer(e, ap, val)
            if self._a_approx(nv):
                raise ErreurReseau(f"{c} : une seule valeur approchée par élément de profil (« {e} »)")
            out.append(nv)
        if isinstance(p, str):
            return " | ".join(out)
        return out

    def _ctx_troncon(self, g):
        ctxt = dict(self.d.get("contexte") or {})
        for k in CLES_CONTEXTE_TRONCON:
            if g.get(k) is not None:
                ctxt[{"vitesse_kmh": "vitesse"}.get(k, k)] = g[k]
        ctxt.update(g.get("contexte") or {})
        return ctxt

    def _defauts_largeurs(self, els, g, chemin):
        """Indice de bande → (largeur, règle, note) des largeurs par défaut (description_vers_modele + commun/profil)."""
        try:
            bandes, limites = FP.analyser(els, chemin)
            dd = dict(self.d, contexte=self._ctx_troncon(g))
            ctxd = D.lire_contexte(dd, bandes)
            bandes, limites = D.resoudre_bandes(bandes, limites, dd, chemin, ctxd)
            ctx = PF.contexte(ctxd["agglomeration"], ctxd["vitesse"], ctxd["categorie"])
        except Exception:
            return {}
        out = {}
        for i, b in enumerate(bandes):
            try:
                w, prov = PF.largeur_defaut(b, bandes, ctx)
            except Exception:
                continue
            prov = prov or {}
            src = str(prov.get("src", ""))
            rid = prov.get("regle") or (src.split(":", 1)[1] if ":" in src else src)
            out[i] = (float(w), rid, prov.get("note"))
        return out

    def _profil_osm(self, g, ch, tid):
        """`profil: osm` : profil inféré des tags du premier way retenu (inference/osm_vers_modele.py, RF-OSM-*)."""
        info = self.rap["troncons"].get(tid, {})
        ways = (info.get("osm") or {}).get("ways") or []
        if not ways:
            raise ErreurReseau(f"{ch}.profil : « osm » demande un tronçon accroché à OSM (clé osm)")
        from inference import osm_vers_modele as OI
        w = OSM.way(str(ways[0]).split("/")[-1])
        try:
            prof, _, avs, _ = OI.profil_depuis_tags(w["tags"])
        except Exception as e:
            raise ErreurReseau(f"{ch}.profil : inférence OSM impossible ({e})")
        mots = {"trottoir": "trottoir", "voie_circulation": "voie", "voie_bus": "voie bus",
                "voie_tourne_gauche": "tourne-à-gauche", "voie_tourne_droite": "tourne-à-droite",
                "chaussee_partagee": "chaussée partagée", "bande_cyclable": "bande cyclable",
                "piste_cyclable": "piste cyclable", "stationnement": "stationnement", "bande_plantee": "bande plantée",
                "accotement_revetu": "accotement", "berme": "accotement herbe", "terre_plein": "terre-plein",
                "zone_neutralisee": "zone hachurée", "voie_verte": "voie verte", "bande_derasee": "BDD"}
        els = []
        for b in prof["bandes"]:
            if b["type"] not in mots:
                raise ErreurReseau(f"{ch}.profil : bande OSM « {b['type']} » sans mot du format")
            s = f"{mots[b['type']]} {AX.fmt(float(b['largeur_m'] if 'largeur_m' in b else b['largeur']))}"
            if b["type"] in PF.VOIES_MOTORISEES | {"bande_cyclable"}:
                s += {"avant": " →", "arriere": " ←"}.get(b.get("sens"), "")
            els.append(s)
        self.av.append(f"{ch}.profil : profil non relevé, inféré des tags OSM de way/{w['id']} (RF-OSM-*)")
        info["profil_osm"] = {"way": w["id"], "profil": " | ".join(els)}
        return " | ".join(els)

    # ------------------------------------------------------------------------------------------------ évènements
    def _evenements(self):
        for ch, g, t, tid in self.troncons:
            evs = t.get("evenements")
            if not evs:
                continue
            L = self.lg[tid]
            bouts = self._bouts(tid)
            out = []
            for k, e in enumerate(evs):
                out += self._evenement(e, f"{ch}.evenements[{k}]", L, bouts, t, g, tid)
            t["evenements"] = out
        for ch, g, t, tid in self.troncons:
            sig = t.get("signalisation")
            if sig:
                L = self.lg[tid]
                for k, s in enumerate(sig):
                    if isinstance(s, dict) and s.get("a") is not None and not isinstance(s["a"], (int, float)):
                        s["a"] = _r(self._abscisse(s["a"], L, f"{ch}.signalisation[{k}].a", tid, self._bouts(tid)), 3)

    def _evenement(self, e, c, L, bouts, t, g, tid) -> list:
        if isinstance(e, dict):
            if len(e) == 1:
                (typ, prm), = e.items()
                if isinstance(prm, dict):
                    prm = dict(prm)
                    if "a" in prm and not isinstance(prm["a"], (int, float)):
                        prm["a"] = _r(self._abscisse(prm["a"], L, f"{c}.a", tid, bouts), 3)
                    self._parcourir_numeriques(prm, c)
                    return [{typ: prm}]
            return [e]
        s = str(e)
        m = re.match(r"^\s*(.+?)\s*:\s*(.+)$", s)
        if not m:
            raise ErreurReseau(f"{c} : forme « position : évènement » attendue, lu « {s} »")
        pos, contenu = m.group(1), m.group(2).strip()
        p = re.sub(r"\s+", " ", V.sans_accents(pos).lower().strip())
        if re.match(r"^(?:a\s+)?\d+(?:[.,]\d+)?\s*m?$", p) and not self._a_approx(contenu):
            return [s]                                             # « à 40 : passage piéton » : forme de l'étape 2
        iv = self._intervalle(p, L, c, tid, bouts)
        if iv is not None:
            return self._insertion(iv, contenu, c, L, t, g, tid)
        a = self._abscisse(pos, L, f"{c}.a", tid, bouts)
        if not (-1e-6 <= a <= L + 1e-6):
            raise ErreurReseau(f"{c} : position {a:.1f} m hors du tronçon [0 ; {L:.1f}] (FORMAT § 11)")
        contenu = self._texte_exact(contenu, c, "longueur")
        return [f"à {_r(a, 2):g} : {contenu}"]

    def _texte_exact(self, texte, c, genre):
        """Toutes les valeurs approchées d'un texte remplacées par leur valeur retenue (centre, faute de règle)."""
        n = 0
        while self._a_approx(texte) and n < 6:
            ap = AX.lire(texte, genre)
            if ap is None or ap.get("forme") == "exacte" and "mesure" not in ap:
                break
            val, ent = AX.choisir(ap, None, c, self.av)
            ent["genre"] = genre
            self.approx.append(ent)
            texte = AX.remplacer(texte, ap, val)
            n += 1
        return texte

    def _intervalle(self, p, L, c, tid, bouts):
        if p in ("sur toute la longueur", "tout le long"):
            return (0.0, L)
        m = re.match(r"^sur\s+(.+?)\s*(?:m|metres)?\s+(au milieu|a peu pres au milieu|au debut|au depart|a la fin|au bout)$", p)
        if m:
            lg = self._valeur(m.group(1), f"{c}.longueur", "longueur")
            if m.group(2) in ("au debut", "au depart"):
                return (0.0, lg)
            if m.group(2) in ("a la fin", "au bout"):
                return (L - lg, L)
            centre = self._abscisse("au milieu", L, f"{c}.centre")
            return (centre - lg / 2.0, centre + lg / 2.0)
        m = re.match(r"^de\s+(.+?)\s+a\s+(.+)$", p)
        if m:
            m2 = re.match(r"^(.+?)\s+(de|apres|avant)\s+([A-Za-z0-9_.\-]+)$", m.group(2))
            suff = f" {m2.group(2)} {m2.group(3)}" if m2 else ""
            s0 = self._abscisse(m.group(1) + suff, L, f"{c}.de", tid, bouts)
            s1 = self._abscisse(m.group(2), L, f"{c}.a", tid, bouts)
            return (min(s0, s1), max(s0, s1))
        return None

    def _insertion(self, iv, contenu, c, L, t, g, tid) -> list:
        """« de S0 à S1 : terre-plein planté », « … : îlot refuge bordure basse vue 0,11 enrobé », « … : zone hachurée
        2,5 » : bande centrale insérée sur la ligne de référence (FORMAT_DESCRIPTION_RESEAU § 6.3)."""
        s0, s1 = iv
        if not (-1e-6 <= s0 < s1 <= L + 1e-6):
            raise ErreurReseau(f"{c} : intervalle [{s0:.1f} ; {s1:.1f}] hors du tronçon [0 ; {L:.1f}]")
        txt = V.sans_accents(contenu).lower()
        m = re.search(r"\bprise?s?\s+sur\s+(?:les?\s+|la\s+)?(plate-forme|plateforme|trottoirs?|voies?)\b", txt)
        if m:
            pris = m.group(1)
            if not pris.startswith("plate"):
                raise ErreurReseau(f"{c} : « pris sur {pris} » non porté au lot N1 (seule l'emprise prise sur la "
                                   "plate-forme est traduite) ; décrire le profil réduit par un évènement « profil »")
            contenu = (contenu[:m.start()] + contenu[m.end():]).strip()
        bord = None
        mb = re.search(r"\bbordure\b.*?\bvue\s+\S+(?:\s+\S+)?", contenu, re.I)
        if mb:
            seg = mb.group(0)
            m_v = re.search(rf"vue\s+(?:≈|~|environ)?\s*{AX.NUM}", seg, re.I)
            seg = seg[:m_v.end()] if m_v else seg
            bord = self._texte_exact(seg, c, "vue")
            contenu = (contenu[:mb.start()] + contenu[mb.start() + len(seg):]).strip()
        cn = V.sans_accents(contenu).lower()
        refuge = bool(re.match(r"^(ilot refuge|ilot|refuge)\b", cn))
        if refuge:
            mot = "terre-plein"
            reste = re.sub(r"^(îlot refuge|ilot refuge|îlot|ilot|refuge)\s*", "", contenu, flags=re.I)
            bord = bord or "bordure basse"
        elif re.match(r"^(terre-plein|terre plein|tpc)\b", cn):
            mot = "terre-plein"
            reste = re.sub(r"^(terre-plein|terre plein|tpc)\s*", "", contenu, flags=re.I)
        elif re.match(r"^zone (hachuree|neutralisee)\b", cn):
            mot = "zone hachurée"
            reste = re.sub(r"^zone\s+\S+\s*", "", contenu, flags=re.I)
        else:
            raise ErreurReseau(f"{c} : « {contenu} » : seules les bandes centrales (terre-plein, îlot refuge, zone "
                               "hachurée) s'insèrent par un intervalle au lot N1 ; pour une voie, une bande cyclable ou un "
                               "stationnement, écrire un évènement de l'étape 2 (elargissement, profil)")
        reste = self._texte_exact(reste, c, "largeur_photo") if reste else ""
        base_txt = t.get("profil")
        if base_txt is None:
            raise ErreurReseau(f"{c} : profil du tronçon introuvable")
        autres = [e for e in (t.get("evenements") or []) if isinstance(e, dict) and set(e) & {
            "profil", "ouverture", "fermeture", "rabattement", "elargissement"}]
        if autres:
            self.av.append(f"{c} : d'autres évènements changent le profil du tronçon : l'insertion part du profil de "
                           "base, à vérifier")
        try:
            els = FP.elements(base_txt, c)
        except FP.ErreurFormat as e:
            raise ErreurReseau(str(e))
        if any(isinstance(e, dict) for e in els):
            raise ErreurReseau(f"{c} : insertion dans un profil en forme structurée non portée (écrire le profil en ligne)")
        bandes = []
        for e in els:
            bandes.append((e, None if FP._est_limite(V.jetons(e)) else FP.analyser_bande(e, c)))
        arr = [i for i, (_, b) in enumerate(bandes) if b and b["type"] in PF.VOIES_MOTORISEES and b.get("sens") == "arriere"]
        ava = [i for i, (_, b) in enumerate(bandes) if b and b["type"] in PF.VOIES_MOTORISEES and b.get("sens") == "avant"]
        if not arr or not ava or max(arr) > min(ava):
            raise ErreurReseau(f"{c} : bande centrale : le profil doit avoir des voies ← à gauche des voies → (sens écrits)")
        centre = [i for i in range(max(arr) + 1, min(ava)) if bandes[i][1] is not None]
        mw = re.search(rf"(?<![\w,.])({AX.NUM})(?:\s*m\b)?", reste)
        attrs = re.sub(rf"(?<![\w,.]){AX.NUM}(?:\s*m\b)?", "", reste).strip() if reste else ""
        if mot == "terre-plein" and not re.search(r"plant|gazon|herbe|enrob|b[eé]ton|pav|gravier|galet|brf|arbre", attrs, re.I):
            attrs = (attrs + " " + ("enrobé" if refuge else "planté")).strip()
        lim = [bord] if bord else []
        base = " | ".join(x for x, _ in bandes)
        ins = self.rap["troncons"][tid].setdefault("insertions", [])
        if centre:
            # une bande de séparation existe : le terre-plein ou l'îlot la remplace sur l'intervalle (§ 6.3)
            i = centre[0]
            ex = bandes[i][1]
            if mw:
                w = AX.f(mw.group(1))
            elif ex.get("largeur"):
                w = float(ex["largeur"])
            else:
                raise ErreurReseau(f"{c} : largeur de la bande centrale à remplacer non dite")
            neuf = f"{mot} {AX.fmt(w)}" + (f" {attrs}" if attrs else "")
            nv = [x for x, _ in bandes[:i]] + lim + [neuf] + lim + [x for x, _ in bandes[i + 1:]]
            ins.append({"chemin": c, "intervalle": [_r(s0, 2), _r(s1, 2)], "bande": neuf, "remplace": bandes[i][0],
                        "regle": "FORMAT_DESCRIPTION_RESEAU § 6.3 (remplacement à largeur égale)"})
            return [{"profil": {"a": _r(s0, 3), "nouveau": " | ".join(nv)}},
                    {"profil": {"a": _r(s1, 3), "nouveau": base}}]
        if mw:
            w, prov_w = AX.f(mw.group(1)), "description"
        else:
            if mot == "zone hachurée":
                raise ErreurReseau(f"{c} : largeur de la zone hachurée à dire (aucune règle ne la fixe)")
            i_b = sum(1 for x, b in bandes[:min(ava)] if b is not None)
            sans = [x for x, _ in bandes[:min(ava)]] + lim + [f"{mot} {attrs}".strip()] + lim +                 [x for x, _ in bandes[min(ava):]]
            dft = self._defauts_largeurs(sans, g, c).get(i_b)
            if dft is None:
                raise ErreurReseau(f"{c} : largeur de « {mot} » non dite et aucune règle ne la fixe")
            w, prov_w = dft[0], dft[1]
            self.approx.append({"chemin": c, "texte": contenu, "forme": "non_dit", "valeur": w, "choix": "regle",
                                "regle": dft[1], "note": dft[2], "genre": "largeur"})
        Lt = self._oblique_demi(g)
        self.av.append(f"{c} : emprise non dite : la plate-forme s'élargit de {w:g} m, les bandes extérieures se "
                       f"déportent de {w / 2:g} m de chaque côté (FORMAT_DESCRIPTION_RESEAU § 6.3)")
        i_ins = min(ava)
        zh = f"zone hachurée {AX.fmt(w)}"
        neuf = f"{mot} {AX.fmt(w)}" + (f" {attrs}" if attrs else "")
        avant = [x for x, _ in bandes[:i_ins]]
        apres = [x for x, _ in bandes[i_ins:]]
        p_zh = " | ".join(avant + [zh] + apres)
        p_tp = " | ".join(avant + lim + [neuf] + lim + apres) if mot != "zone hachurée" else p_zh
        Lt0, Lt1 = min(Lt, s0), min(Lt, L - s1)
        if Lt0 < Lt - 1e-6 or Lt1 < Lt - 1e-6:
            self.av.append(f"{c} : têtes d'îlot de {Lt:g} m (L/2) raccourcies à {Lt0:.1f} / {Lt1:.1f} m : tronçon trop "
                           "court de part et d'autre")
        evs = []
        if Lt0 > 0.5:
            evs.append({"ouverture": {"a": _r(s0, 3), "longueur": _r(Lt0, 3), "nouveau": p_zh}})
            if p_tp != p_zh:
                evs.append({"profil": {"a": _r(s0, 3), "nouveau": p_tp}})
        else:
            evs.append({"profil": {"a": _r(s0, 3), "nouveau": p_tp}})
        if Lt1 > 0.5:
            if p_tp != p_zh:
                evs.append({"profil": {"a": _r(s1, 3), "nouveau": p_zh}})
            evs.append({"fermeture": {"a": _r(s1 + Lt1, 3), "longueur": _r(Lt1, 3), "nouveau": base}})
        else:
            evs.append({"profil": {"a": _r(s1, 3), "nouveau": base}})
        ins.append({"chemin": c, "intervalle": [_r(s0, 2), _r(s1, 2)], "bande": neuf, "largeur_m": w,
                    "largeur_prov": prov_w, "tetes_ilot_m": [_r(Lt0, 2), _r(Lt1, 2)],
                    "regle_tetes": "RF-MQ-OBL-05 (oblique de tête d'îlot L/2), RF-MQ-PS-03 (V15 → L)",
                    "emprise": "plate-forme élargie (FORMAT § 6.3, défaut)"})
        return evs

    def _oblique_demi(self, g):
        ctx = self._ctx_troncon(g)
        v = ctx.get("v15") or ctx.get("vitesse") or ctx.get("vitesse_kmh")
        if v is None:
            agglo = V.booleen(ctx.get("agglomeration", "oui"), "contexte.agglomeration")
            v = 50 if agglo else 80
        v = float(_num(v, "contexte.vitesse"))
        v = min(v, float(regles.valeur("RF-MQ-PS-02", "double_sens")))
        tab = regles.valeur("RF-MQ-PS-03", "V15_vers_L_m")
        cles = sorted(int(k) for k in tab)
        k = next((x for x in cles if x >= v), cles[-1])
        return float(tab[str(k)]) / 2.0

    # ------------------------------------------------------------------------------------------------ raccords
    def _raccords_contrats(self):
        """Contrat de profil aux nœuds partagés (CHAINE P3, CC-04) : un nœud du réseau commun peut porter le profil du
        joint (`profil`, lu dans le sens `cap_profil`) et la longueur du raccord (`raccord`, défaut ≈ 30 m [G]). Un
        tronçon qui finit sur ce nœud avec un autre profil reçoit, sur cette longueur, une transition continue vers le
        profil du joint : fermeture (bandes qui disparaissent → largeur nulle), puis ouverture (bandes qui naissent),
        sur la sous-suite commune des bandes (même type et même sens) ; largeurs des bandes communes en loi linéaire.
        Le contrôle CC-04 est refait sur le modèle compilé (`controler_raccords`)."""
        for ch, g, t, tid in self.troncons:
            info = self.rap["troncons"][tid]
            for bout in ("de", "vers"):
                nom = info.get(bout)
                if not nom or not self.rap["noeuds"].get(nom, {}).get("profil"):
                    continue
                nd = self.rap["noeuds"][nom]
                contrat = str(nd["profil"])
                pts = self.geo[tid]
                L = self.lg[tid]
                a, b = (pts[0], pts[1]) if bout == "de" else (pts[-2], pts[-1])
                cap_t = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
                cap_c = float(nd.get("cap_profil", cap_t))
                if abs(((cap_t - cap_c + 180.0) % 360.0) - 180.0) > 90.0:
                    contrat = inverser_profil_texte(contrat)
                propre = self._profil_bout(t, bout, L, ch)
                if propre is None:
                    self.av.append(f"{ch} : profil à l'extrémité « {bout} » non déductible avant compilation (voie "
                                   f"ajoutée ou retirée près du bout) : raccord au nœud {nom} non généré, contrôle CC-04 "
                                   "après compilation")
                    continue
                try:
                    bc = bandes_contrat(contrat, self._ctx_troncon(g))
                    bp = bandes_contrat(propre, self._ctx_troncon(g))
                except Exception as e:
                    raise ErreurReseau(f"noeuds.{nom}.profil : contrat illisible ({e})")
                if not comparer_profils(bc, bp):
                    info.setdefault("raccords", []).append({"noeud": nom, "bout": bout, "statut": "profil du joint"})
                    continue
                Lr = self._valeur(nd.get("raccord", "≈ 30"), f"noeuds.{nom}.raccord", "longueur")
                if Lr > L / 2.0:
                    raise ErreurReseau(f"{ch} : raccord de {Lr:g} m au nœud {nom} plus long que la moitié du tronçon "
                                       f"({L:.1f} m)")
                evs = self._transition(contrat, propre, bout, L, Lr, ch)
                if bout == "de":
                    t["profil"] = contrat
                    deja = [e for e in (t.get("evenements") or []) if _a_evenement(e) is not None
                            and _a_evenement(e) < Lr + 1e-6]
                    if deja:
                        self.av.append(f"{ch} : {len(deja)} évènement(s) dans les {Lr:g} premiers mètres, recouverts par "
                                       f"le raccord au nœud {nom} : à vérifier")
                t["evenements"] = list(t.get("evenements") or []) + evs
                for r_, m_ in (nd.get("ecarts_admis") or {}).items():
                    r_ = str(r_).upper().replace("_", "-")
                    ea = self.d.setdefault("ecarts_admis", {})
                    if r_ not in ea:
                        ea[r_] = f"profil du joint {nom} (site {nd.get('proprietaire', '?')}) : {m_}"
                info.setdefault("raccords", []).append({"noeud": nom, "bout": bout, "longueur_m": _r(Lr, 2),
                                                        "de": propre if bout == "vers" else contrat,
                                                        "vers": contrat if bout == "vers" else propre})
                self.av.append(f"{ch} : raccord de profil généré au nœud partagé {nom} ({bout}, {Lr:g} m) : le profil "
                               "décrit diffère du profil du joint (CC-04)")

    def _profil_bout(self, t, bout, L, ch):
        """Texte du profil en vigueur à une extrémité, d'après le profil de base et les évènements (None si une voie est
        ajoutée ou retirée par un rabattement / élargissement après le dernier changement de profil)."""
        base = t.get("profil")
        if isinstance(base, list) and all(isinstance(x, str) for x in base):
            base = " | ".join(x.strip() for x in base)
        if not isinstance(base, str):
            return None
        if bout == "de":
            return base
        dernier, a_der = base, -1.0
        for e in t.get("evenements") or []:
            if not isinstance(e, dict) or len(e) != 1:
                continue
            (typ, prm), = e.items()
            if not isinstance(prm, dict):
                continue
            a = prm.get("a")
            if not isinstance(a, (int, float)):
                continue
            if typ in ("profil", "fermeture") or (typ == "ouverture" and V.norm(str(prm.get("sens", "→"))) in ("→", "avant")):
                if a >= a_der and isinstance(prm.get("nouveau"), str):
                    dernier, a_der = prm["nouveau"], a
        for e in t.get("evenements") or []:
            if isinstance(e, dict) and len(e) == 1:
                (typ, prm), = e.items()
                if typ in ("rabattement", "elargissement") and isinstance(prm, dict) and \
                        isinstance(prm.get("a"), (int, float)) and prm["a"] >= a_der:
                    return None
        return dernier

    def _transition(self, joint_txt, propre_txt, bout, L, Lr, ch):
        """Évènements qui font passer le profil, d'une manière continue et monotone, du profil P0 au profil P1 sur
        [s0 ; s0 + Lr] : au bout « de », du profil du joint (s = 0) au profil propre ; au bout « vers », du profil propre
        au profil du joint (s = L). Les deux profils sont alignés sur leur plus longue sous-suite commune (même type, même
        sous-type, même sens) ; le profil intermédiaire M (à mi-longueur) porte toutes les bandes, celles de P0 seul à la
        moitié de leur largeur, celles de P1 seul à la moitié de la leur, les bandes communes à la largeur moyenne :
        ouverture P0 → M, puis fermeture M → P1. La largeur totale varie ainsi linéairement de W0 à (W0 + W1) / 2 puis
        à W1, sans pincement ni renflement."""
        if bout == "de":
            p0, p1, s0 = joint_txt, propre_txt, 0.0
        else:
            p0, p1, s0 = propre_txt, joint_txt, L - Lr
        els0 = [e.strip() for e in p0.split("|")]
        els1 = [e.strip() for e in p1.split("|")]
        try:
            b0 = [(e, FP.analyser_bande(e, ch)) for e in els0 if not FP._est_limite(V.jetons(e))]
            b1 = [(e, FP.analyser_bande(e, ch)) for e in els1 if not FP._est_limite(V.jetons(e))]
        except FP.ErreurFormat as e:
            raise ErreurReseau(str(e))
        cle = lambda b: (b["type"], b.get("sous_type"), b.get("sens"))  # noqa: E731
        n, m = len(b0), len(b1)
        T = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(n - 1, -1, -1):
            for j in range(m - 1, -1, -1):
                T[i][j] = T[i + 1][j + 1] + 1 if cle(b0[i][1]) == cle(b1[j][1]) else max(T[i + 1][j], T[i][j + 1])
        # suite fusionnée : (texte P0 | None, texte P1 | None)
        i = j = 0
        fus = []
        while i < n or j < m:
            if i < n and j < m and cle(b0[i][1]) == cle(b1[j][1]):
                fus.append((b0[i], b1[j]))
                i += 1
                j += 1
            elif j >= m or (i < n and T[i + 1][j] >= T[i][j + 1]):
                fus.append((b0[i], None))
                i += 1
            else:
                fus.append((None, b1[j]))
                j += 1
        if not any(x and y for x, y in fus):
            raise ErreurReseau(f"{ch} : aucun type de bande commun entre le profil propre et celui du joint : raccord "
                               "impossible")

        def largeur(entree, liste):
            e, b = entree
            if b.get("largeur") is not None:
                return float(b["largeur"])
            w = self._defauts_largeurs([x for x, _ in liste], {}, ch)
            k = [x for x, _ in liste].index(e)
            if k in w:
                return w[k][0]
            raise ErreurReseau(f"{ch} : largeur de « {e} » non dite et sans règle : raccord impossible")

        def avec_largeur(texte, b, w):
            """Texte de bande avec la largeur w (remplace la largeur dite, ou l'ajoute après le mot de la bande)."""
            t = re.sub(r"(?<![\w.,])\d+(?:[.,]\d+)?(?=\s|$)", AX.fmt(w), texte, count=1) if b.get("largeur") is not None \
                else None
            if t is None:
                toks = texte.split()
                cle_b, nb = V.correspondance(V.jetons(texte), 0, V.BANDES)
                t = " ".join(toks[:nb] + [AX.fmt(w)] + toks[nb:]) if cle_b else f"{texte} {AX.fmt(w)}"
            return t

        mid = []
        for x, y in fus:
            if x and y:
                w = (largeur(x, b0) + largeur(y, b1)) / 2.0
                mid.append(avec_largeur(y[0], y[1], round(w, 3)))
            elif x:
                mid.append(avec_largeur(x[0], x[1], round(largeur(x, b0) / 2.0, 3)))
            else:
                mid.append(avec_largeur(y[0], y[1], round(largeur(y, b1) / 2.0, 3)))
        m_txt = " | ".join(mid)
        sm = s0 + Lr / 2.0
        evs = []
        if any(x is None for x, _ in fus) or any(x and y for x, y in fus):
            evs.append({"ouverture": {"a": _r(sm, 3), "longueur": _r(Lr / 2.0, 3), "nouveau": m_txt, "raccord": "oui"}})
        # la fermeture commence 5 cm après la fin de l'ouverture : à abscisse égale, le compilateur garde le premier
        # changement de profil posé (max sur s0)
        fin = _bas(s0 + Lr)
        evs.append({"fermeture": {"a": fin, "longueur": _r(fin - sm - 0.05, 3), "nouveau": p1, "raccord": "oui"}})
        return evs

    # ------------------------------------------------------------------------------------------------ clés réseau
    def _cles_troncons(self):
        np_ = self.rap["non_portes_etape2"]
        admis = {}
        for ch, g, t, tid in self.troncons:
            ctx = dict(g.get("contexte") or {})
            for k in sorted(CLES_CONTEXTE_TRONCON):
                if k in g and g is not self.d:
                    if AX.contient_approx(g[k]) and k.startswith("vitesse"):
                        raise ErreurReseau(f"{ch}.{k} : la vitesse ne s'approche pas")
                    ctx[{"vitesse_kmh": "vitesse"}.get(k, k)] = g.pop(k)
            if ctx and g is not self.d:
                g["contexte"] = ctx
            for k in ("osm", "bdtopo", "tolerance_trace", "z", "jumele_avec", "itineraire", "ref", "preuves",
                      "retenue", "equipements", "talus", "note", "notes"):
                if k in g and g is not self.d:
                    v = g.pop(k)
                    if k not in ("osm", "tolerance_trace"):
                        np_.setdefault("troncons", {}).setdefault(tid, {})[k] = v
            if "ecarts_admis" in g and g is not self.d:
                for r, m in (g.pop("ecarts_admis") or {}).items():
                    admis.setdefault(r, []).append(f"{tid} : {m}")
            if ch == "troncon":
                g.pop("id", None)
            for k in ("materiaux", "marquages", "confiance"):
                if k in g and g is not self.d and ch == "troncon":
                    # tronçon unique : ses matériaux et marquages sont ceux de la description
                    if k in self.d and self.d[k] != g[k]:
                        raise ErreurReseau(f"troncon.{k} et {k} de la racine diffèrent")
                    self.d[k] = g.pop(k)
        if admis:
            ea = dict(self.d.get("ecarts_admis") or {})
            for r, ms in admis.items():
                ea[r] = " ; ".join(([ea[r]] if r in ea else []) + ms)
            self.d["ecarts_admis"] = ea

    def _fusions_internes(self):
        """Raccords internes : deux tronçons de la description qui se suivent par un nœud nommé de valence 2, hors
        carrefour, deviennent un seul tronçon (fusion.py) ; un nœud de valence ≥ 3 fusionne sa paire la mieux alignée."""
        trs = self.d.get("troncons")
        if not isinstance(trs, list) or len(trs) < 2:
            return
        ids = list(self.ids)
        for k, t in enumerate(trs):
            t["id"] = str(t.get("id") or ids[k])
        fins = {}
        for tid, info in self.rap["troncons"].items():
            for bout in ("de", "vers"):
                if info.get(bout):
                    fins.setdefault(info[bout], []).append((tid, bout))
        fins = {n: v for n, v in fins.items() if len(v) >= 2}
        if not fins:
            return
        bloques = {n for n, inf in self.rap["noeuds"].items() if inf.get("carrefour")}
        objets = {k: self.d.get(k) or [] for k in ("carrefours", "giratoires", "bretelles")}
        avant = {t["id"] for t in trs}
        nouv = FU.fusionner_aux_noeuds([dict(t) for t in trs], fins, bloques, self.origine, objets, self.rap)
        if {t["id"] for t in nouv} == avant:
            return
        self.d["troncons"] = nouv
        for k, v in objets.items():
            if v:
                self.d[k] = v
        # extrémités des tronçons restants : nœuds dont la position coïncide avec le premier / dernier point
        connus = {n for n in self.pos}
        for tid in list(self.rap["troncons"]):
            if tid not in {t["id"] for t in nouv}:
                self.rap["troncons"][tid]["fusionne_dans"] = next(
                    (f["troncons"][0] for f in self.rap.get("fusions", []) if tid in f["troncons"]), None)
        for t in nouv:
            pts = t["polyligne"] if t.get("polyligne") else [t["de"], t["vers"]]
            info = self.rap["troncons"].setdefault(t["id"], {})
            for bout, p in (("de", pts[0]), ("vers", pts[-1])):
                info.pop(bout, None)
                for n in connus:
                    x, y = self.pos[n]
                    if math.hypot(x - self.origine[0] - p[0], y - self.origine[1] - p[1]) < 0.01:
                        info[bout] = n
                        break
            info["longueur_m"] = _r(FU.longueur(t, self.origine), 2)
        for n, inf in self.rap["noeuds"].items():
            inf["troncons"] = [f"{tid}.{b}" for tid, i in self.rap["troncons"].items() if "fusionne_dans" not in i
                               for b in ("de", "vers") if i.get(b) == n]
        self.ids = {t["id"]: k for k, t in enumerate(nouv)}

    def _cles_racine(self):
        np_ = self.rap["non_portes_etape2"]
        for k in ("sources", "itineraires", "ouvrages", "echangeurs", "extensions_auto", "extensions", "preuves",
                  "notes", "retenue", "equipements", "talus", "composition"):
            if k in self.d:
                np_[k] = self.d.pop(k)
        for k in ("reseau_commun", "noeuds", "etat", "date_etat", "repere"):
            self.d.pop(k, None)
        reseau = self.d.pop("reseau", None)
        if reseau and not self.d.get("scene"):
            self.d["scene"] = reseau
        if self.etat.get("date"):
            self.d["date"] = self.etat["date"]
        self.d["format"] = FORMAT_ETAPE2
        self.d["origine"] = [_r(x, 3) for x in self.origine]

    # ------------------------------------------------------------------------------------------------ porte P00
    def _porte_p00(self):
        hors = [a for a in self.approx if a.get("hors_plage")]
        p = [{"id": "P00-1", "controle": "clés et mots connus", "statut": "conforme"},
             {"id": "P00-2", "controle": "nœuds déclarés et ancrés", "statut": "conforme",
              "valeur": len(self.rap["noeuds"])},
             {"id": "P00-3", "controle": "valeurs approchées à plage finie et non vide", "statut": "conforme",
              "valeur": len(self.approx)},
             {"id": "P00-5", "controle": "date d'état unique",
              "statut": "conforme" if self.etat.get("date") else "avertissement", "valeur": self.etat.get("date")}]
        if hors:
            p[2]["note"] = f"{len(hors)} mesure(s) hors de la plage dite (avertissements : la mesure prime)"
        self.rap["porte_P00"] = p

    # ------------------------------------------------------------------------------------------------ sortie
    def _sortie(self) -> dict:
        ordre = ["format", "scene", "nom", "titre", "date", "confiance", "origine", "description", "contexte"]
        out = {k: self.d[k] for k in ordre if k in self.d}
        for k, v in self.d.items():
            if k not in out:
                out[k] = v
        return out


# ===================================================================================================== API fichier
def resoudre_dict(d: dict, source: str, dossier: Path | None = None, commun: dict | None = None):
    """(description exacte, rapport) ; une description sans couche réseau est rendue telle quelle (même objet)."""
    if not est_reseau(d):
        return d, {"version": VERSION, "source": source, "format_entree": "description_simple (inchangée)",
                   "inchangee": True}
    R = Resolveur(d, source, dossier, commun)
    out = R.resoudre()
    return out, R.rap


def resoudre_fichier(chemin: Path):
    """(texte YAML exact, dict exact, rapport, octets d'entrée)."""
    chemin = Path(chemin)
    octets = chemin.read_bytes()
    d = yaml_simple.charger(octets.decode("utf-8"))
    try:
        src = str(chemin.resolve().relative_to(DEPOT)).replace("\\", "/")
    except ValueError:
        src = str(chemin).replace("\\", "/")
    exact, rap = resoudre_dict(d, src, chemin.resolve().parent)
    rap["sha256_entree"] = sha256(octets)
    if rap.get("inchangee"):
        return octets.decode("utf-8"), d, rap, octets
    texte = YE.ecrire(exact, entete=f"Description exacte (format de l'étape 2) résolue par recon/generateur/reseau/"
                                    f"resoudre_reseau.py\ndepuis {src} (sha256 {rap['sha256_entree'][:16]}) ; ne pas "
                                    "modifier à la main.")
    YE.verifier_aller_retour(exact, texte)
    return texte, exact, rap, octets


# ===================================================================================================== contrats CC-04
def _largeur_en(b, s):
    w = b.get("largeur")
    if isinstance(w, dict) and w.get("points"):
        pts = w["points"]
        if s <= pts[0][0]:
            return float(pts[0][1])
        if s >= pts[-1][0]:
            return float(pts[-1][1])
        for a, c in zip(pts, pts[1:]):
            if a[0] <= s <= c[0]:
                return float(a[1] + (c[1] - a[1]) * (s - a[0]) / (c[0] - a[0])) if c[0] > a[0] else float(c[1])
    return float(w) if isinstance(w, (int, float)) else None


def profil_a(modele: dict, rid: str, s: float, cote: str = "apres") -> list:
    """Bandes (type, sens, largeur) du profil d'une route à l'abscisse s (section qui commence en s si cote = « apres »,
    qui finit en s si « avant »), lois de largeur comprises ; les demi-bandes centrales d'une ouverture (_axe_g, _axe_d)
    sont réunies."""
    prof = {p["id"]: p for p in modele["profils"]}
    r = next(x for x in modele["routes"] if x["id"] == rid)
    secs = r["sections"]
    if cote == "apres":
        sec = next((x for x in secs if x["s0"] <= s + 1e-6 < x["s1"]), secs[-1])
    else:
        sec = next((x for x in secs if x["s0"] < s - 1e-6 <= x["s1"]), secs[0])
    out = []
    for b in prof[sec["profil"]]["bandes"]:
        w = _largeur_en(b, s)
        if out and b["id"].endswith("_axe_d") and out[-1].get("_id", "").endswith("_axe_g") and \
                out[-1]["type"] == b["type"]:
            out[-1]["largeur"] = (out[-1]["largeur"] or 0.0) + (w or 0.0)
            out[-1]["_id"] = b["id"]
            continue
        out.append({"type": b["type"], "sens": b.get("sens"), "largeur": w, "_id": b["id"]})
    for x in out:
        x.pop("_id", None)
    return [x for x in out if x["largeur"] is None or x["largeur"] > 1e-6]


def profil_extremite(modele: dict, rid: str, extremite: str) -> list:
    r = next(x for x in modele["routes"] if x["id"] == rid)
    L = r["ligne_reference"]["longueur_m"]
    return profil_a(modele, rid, 0.0, "apres") if extremite == "debut" else profil_a(modele, rid, L, "avant")


def comparer_profils(pa: list, pb: list, tol: float = 0.011):
    """Écarts entre deux listes de bandes (mêmes types, sens, largeurs à tol près)."""
    if [(x["type"], x["sens"]) for x in pa] != [(x["type"], x["sens"]) for x in pb]:
        return ["suite des bandes différente : " + " | ".join(f"{x['type']}" for x in pa) + "  ≠  "
                + " | ".join(f"{x['type']}" for x in pb)]
    out = []
    for i, (x, y) in enumerate(zip(pa, pb)):
        if x["largeur"] is None or y["largeur"] is None:
            continue
        if abs(float(x["largeur"]) - float(y["largeur"])) > tol:
            out.append(f"bande {i} ({x['type']}) : {x['largeur']:.2f} ≠ {y['largeur']:.2f}")
    return out


def inverser_bandes(bandes: list) -> list:
    inv = {"avant": "arriere", "arriere": "avant"}
    return [dict(b, sens=inv.get(b["sens"], b["sens"])) for b in reversed(bandes)]


def bandes_contrat(texte: str, contexte: dict) -> list:
    bl, lims = FP.analyser(texte, "contrat")
    dd = {"contexte": dict(contexte or {})}
    ctxd = D.lire_contexte(dd, bl)
    bl, lims = D.resoudre_bandes(bl, lims, dd, "contrat", ctxd)
    ctx = PF.contexte(ctxd["agglomeration"], ctxd["vitesse"], ctxd["categorie"])
    out = []
    for b in bl:
        w = b["largeur"] if b["largeur"] is not None else PF.largeur_defaut(b, bl, ctx)[0]
        out.append({"type": b["type"], "sens": b["sens"], "largeur": float(w)})
    return out


def controler_raccords(rap: dict, exact: dict, modele: dict) -> list:
    """CC-04 aux nœuds partagés qui portent un contrat de profil (`profil`, lu dans le sens `cap_profil`) : le profil
    de chaque route à ce nœud, ramené dans le sens du contrat, doit être celui du contrat (types, sens, largeurs à
    1 cm). La k-ième route du modèle (R-k) est le k-ième tronçon de la description exacte."""
    ctrl = []
    noms = [str(t.get("id") or f"T{k + 1}") for k, t in enumerate(exact.get("troncons") or [])] or         list(rap.get("troncons", {}))[:1]
    ids_routes = {r["id"] for r in modele["routes"]}
    for nom, info in rap.get("noeuds", {}).items():
        if not info.get("profil") or not info.get("troncons"):
            continue
        cap = float(info.get("cap_profil", 0.0))
        for ref in info["troncons"]:
            tid, bout = ref.rsplit(".", 1)
            if tid not in noms or f"R-{noms.index(tid) + 1}" not in ids_routes:
                continue
            rid = f"R-{noms.index(tid) + 1}"
            r = next(x for x in modele["routes"] if x["id"] == rid)
            ctx = dict(exact.get("contexte") or {})
            trs = exact.get("troncons") or []
            if noms.index(tid) < len(trs):
                ctx.update(trs[noms.index(tid)].get("contexte") or {})
            try:
                contrat = bandes_contrat(info["profil"], ctx)
            except Exception as e:
                ctrl.append({"controle": "CC-04", "noeud": nom, "statut": "erreur", "detail": f"contrat illisible : {e}"})
                break
            ext = "debut" if bout == "de" else "fin"
            pb = profil_extremite(modele, rid, ext)
            g = r["ligne_reference"]["geometrie"]
            a, b = (g[0], g[1]) if ext == "debut" else (g[-2], g[-1])
            cap_r = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            if abs(((cap_r - cap + 180.0) % 360.0) - 180.0) > 90.0:
                pb = inverser_bandes(pb)
            ecarts = comparer_profils(contrat, pb)
            ctrl.append({"controle": "CC-04", "noeud": nom, "troncon": tid, "route": rid, "extremite": ext,
                         "statut": "conforme" if not ecarts else "non_conforme", "ecarts": ecarts,
                         "regle": "CHAINE_CONSTRUCTION CC-04 (même t de chaque limite des deux côtés du joint)"})
    return ctrl


def controler_fusions(rap: dict, exact: dict, modele: dict) -> list:
    """Composition : au raccord de deux tronçons fusionnés (abscisse s du raccord sur la route fusionnée), profil juste
    avant et juste après (CC-04) ; un écart veut dire que les deux sites ne tiennent pas le même contrat de profil."""
    ctrl = []
    noms = [t["id"] for t in exact.get("troncons") or []]
    for f in rap.get("fusions") or []:
        tid = f.get("troncon_final", f["troncons"][0])
        if tid not in noms:
            continue
        rid = f"R-{noms.index(tid) + 1}"
        s = float(f.get("s", f["longueur_premier_m"]))
        try:
            pa = profil_a(modele, rid, s, "avant")
            pb = profil_a(modele, rid, s, "apres")
        except StopIteration:
            continue
        ecarts = comparer_profils(pa, pb)
        c = {"controle": "CC-04", "noeud": f["noeud"], "route": rid, "s": round(s, 2),
             "statut": "conforme" if not ecarts else "non_conforme", "ecarts": ecarts,
             "regle": "CHAINE_CONSTRUCTION CC-04 (profil continu au raccord fusionné)", "bloquant": False}
        if ecarts:
            c["note"] = ("les deux tronçons fusionnés n'ont pas le même profil au nœud : changement instantané dans la "
                         "route ; poser un contrat de profil au nœud (reseau_meylan.yaml) pour un raccord continu")
        ctrl.append(c)
    return ctrl


# ===================================================================================================== compilation
def compiler(exact: dict, source: str, sha: str | None):
    m, r = D.compiler(copy.deepcopy(exact), source, sha)
    return m, r


def ecrire_json(o, chemin: Path):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes((json.dumps(o, ensure_ascii=False, indent=1, default=str) + "\n").encode("utf-8"))


def apres_compilation(rap: dict, exact: dict, modele: dict, rapport: dict):
    """Contrôles de réseau sur le modèle compilé : CC-04 aux nœuds partagés à contrat de profil et aux raccords
    fusionnés, porte P01. Un raccord non conforme arrête (un contrôle de continuité ne s'admet pas, CHAINE P6)."""
    rap["raccords"] = controler_raccords(rap, exact, modele) + controler_fusions(rap, exact, modele)
    rap["porte_P01"] = porte_p01(modele, rap)
    nc = [c for c in rap["raccords"] if c["statut"] != "conforme" and c.get("bloquant", True)]
    rap["resume"] = {"erreurs_validation": rapport["validation"]["nb_erreurs"],
                     "non_conformites": len(rapport["non_conformites"]), "raccords_controles": len(rap["raccords"]),
                     "raccords_non_conformes": len(nc),
                     "raccords_fusionnes_a_changement_de_profil": sum(1 for c in rap["raccords"]
                                                                      if c["statut"] != "conforme" and not c.get("bloquant", True)),
                     "fusions": len(rap.get("fusions") or []),
                     "approximations": len(rap.get("approximations") or [])}
    rapport["reseau_n1"] = {"rapport": "compilation_reseau.json", **rap["resume"]}
    if nc:
        raise ErreurReseau("continuité : profil différent au joint (CC-04) : " + " ; ".join(
            f"{c.get('noeud')} {c.get('troncon') or c.get('route')} : {', '.join(c.get('ecarts') or [])}" for c in nc[:4]))


def ecrire_sorties(rap: dict, exact: dict, sortie: Path, sha: str | None = None):
    sortie = Path(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    texte = YE.ecrire(exact, entete=f"Description exacte (format de l'étape 2) résolue par recon/generateur/reseau/"
                                    f"resoudre_reseau.py\ndepuis {rap.get('source')}"
                                    + (f" (sha256 {sha[:16]})" if sha else "") + " ; ne pas modifier à la main.")
    YE.verifier_aller_retour(exact, texte)
    (sortie / "description_resolue.yaml").write_bytes(texte.encode("utf-8"))
    ecrire_json(rap, sortie / "compilation_reseau.json")


def traiter(entree: Path | None, sortie: Path | None, compiler_aussi: bool = True, composer_nom: str | None = None,
            reseau: Path | None = None):
    """Résout (et compile) un fichier ou une composition ; écrit les sorties ; rend (rapport réseau, rapport de
    compilation | None, dossier)."""
    if composer_nom:
        import composer as CO
        texte, exact, rap, octets, src = CO.composer(composer_nom, reseau)
    else:
        texte, exact, rap, octets = resoudre_fichier(entree)
        src = rap["source"]
    scene = str(exact.get("scene") or (Path(entree).stem if entree else composer_nom))
    sortie = Path(sortie) if sortie else SORTIE_DEFAUT / scene
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "description_resolue.yaml").write_bytes(texte.encode("utf-8"))
    rc = None
    if compiler_aussi:
        m, rc = compiler(exact, src, sha256(octets))
        if not rap.get("inchangee"):
            try:
                apres_compilation(rap, exact, m, rc)
            finally:
                ecrire_json(rap, sortie / "compilation_reseau.json")
        D.ecrire_json(m, sortie / "modele_voie.json")
        D.ecrire_json(rc, sortie / "compilation.json")
    ecrire_json(rap, sortie / "compilation_reseau.json")
    return rap, rc, sortie


def porte_p01(modele: dict, rap: dict) -> list:
    """P01-1 (extrémités : limite de carte seulement aux nœuds déclarés en bord, ou nœuds partagés à valence 1 dans
    la scène) et P01-2 (nœuds de valence ≥ 3 rattachés à un carrefour)."""
    out = []
    lc = [n for n in modele["noeuds"] if n["type"] == "limite_carte"]
    out.append({"id": "P01-1", "controle": "extrémités de route", "valeur": {"limite_carte": len(lc),
                "carrefour": sum(1 for n in modele["noeuds"] if n["type"] != "limite_carte")}, "statut": "conforme",
                "note": "dans une scène de site, chaque nœud partagé avec un site voisin est une limite de carte ; la "
                        "composition des sites les raccorde"})
    v3 = [n["id"] for n in modele["noeuds"] if len(n.get("routes", [])) >= 3 and not n.get("carrefour")]
    out.append({"id": "P01-2", "controle": "nœud de valence ≥ 3 sans carrefour", "valeur": v3,
                "statut": "conforme" if not v3 else "non_conforme"})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("description", nargs="?")
    ap.add_argument("--sortie")
    ap.add_argument("--sans-compiler", action="store_true")
    ap.add_argument("--composer", help="nom d'une composition de reseau_meylan.yaml, ou liste de sites séparés par des virgules")
    ap.add_argument("--reseau", help="fichier du réseau commun (défaut recon/generateur/meylan/reseau_meylan.yaml)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not a.description and not a.composer:
        ap.error("une description ou --composer")
    try:
        rap, rc, sortie = traiter(Path(a.description) if a.description else None, a.sortie, not a.sans_compiler,
                                  a.composer, Path(a.reseau) if a.reseau else None)
    except (ErreurReseau, D.ErreurDescription, yaml_simple.ErreurYaml, AX.ErreurApprox, OSM.ErreurOSM) as e:
        print(f"ERREUR\t{e}")
        return 2
    for w in rap.get("avertissements", []):
        print(f"AVERTISSEMENT RÉSEAU\t{w}")
    for c in rap.get("raccords", []):
        if c["statut"] != "conforme":
            print(f"RACCORD\t{c['noeud']}\t{c.get('troncon')}\t{c['statut']}\t{'; '.join(c.get('ecarts', []))}")
    if rc is not None:
        print(f"{rc['scene']} : {sum(t['sections'] for t in rc['troncons'])} section(s), "
              f"{rc['validation']['nb_erreurs']} erreur(s) de validation, {len(rc['non_conformites'])} non-conformité(s) "
              f"non admise(s), {len(rap.get('approximations', []))} valeur(s) approchée(s) → {sortie}")
        return 1 if rc["validation"]["nb_erreurs"] else 0
    print(f"résolu → {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
