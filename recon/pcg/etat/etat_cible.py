"""État cible du pipeline : un état = une configuration (date T, sources admissibles, événements datés, dossiers).

Sélection (PLAN_AVANT_TRAVAUX.md § 3.1) : variable d'environnement PJ_ETAT, posée AVANT les imports par
recon/pcg/etat/lancer.py (les modules calculent leurs chemins à l'import, ex. commun.SORTIE). Date facultative
PJ_DATE_CIBLE : variante déclarée dans la configuration (ex. 2025-05-18), aucune date n'est écrite dans le code.
Sans PJ_ETAT : aucun état ; les modules gardent leurs chemins historiques, ceux de l'archive v2/ de l'état 2026
(gelée, étiquette git etat_2026_gel).

    import etat_cible as EC
    E = EC.courant()                          # None sans PJ_ETAT
    E.dossier("description")                  # recon/out/paquet_jardin/v2_avant_travaux/description
    E.reference("mnt"), E.source("gam")       # chemins déclarés par l'état
    E.valide("2025-05-18", (x, y), "marquage")   # Verdict(statut, classe, motifs)

Règle de validité (§ 2.1) : une observation datée d, au point p (L93), pour une famille f, est valable pour T si
aucun événement E ne touche f, ne contient p (marge comprise) et n'a pu se produire entre d et T. Sémantique des
dates d'un événement : date_min = dernier jour où l'état ancien est certain, date_max = premier jour où l'état
nouveau est certain ; le changement a lieu dans ]date_min ; date_max[. Il a pu se produire entre d et T si
max(date_min, min(d, T)) < min(date_max, max(d, T)).
    - non_valable : p dans l'emprise (au-delà de la marge) d'un événement observé qui sépare d de T, ou d pendant
      cet événement ;
    - incertain : p à moins de marge_m (+ précision du point) du bord, T pendant un événement observé, ou
      événement non observé ;
    - observation négative (type observation_negative) : zone A vue inchangée le jour d1 ; dans A, la date_min
      des événements visés (par défaut : les non observés) devient max(date_min, d1). Pour T ≤ d1, A est donc
      retirée de l'événement (§ 2.1) ; pour T > d1, l'événement reste possible entre d1 et T ;
    - observe_post (propriété d'un événement) : première observation de l'état d'après ; resserre date_max,
      partout (date) ou zone par zone ([{date, zone}]).
Dépendances : numpy seulement (aucun import du pipeline : commun.py importe ce module).
"""
import datetime as dt
import functools
import hashlib
import json
import math
import os
import re
from collections import namedtuple
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[3]
ICI = Path(__file__).resolve().parent
ETATS = ICI / "etats"
ENV_ETAT, ENV_DATE = "PJ_ETAT", "PJ_DATE_CIBLE"
SCHEMA_CONFIG = "pj_etat_cible/0.2"
SCHEMA_FIGE = "pj_etat_cible_fige/0.1"
FICHIER_FIGE = "etat_cible.json"

# Archive de l'état 2026 (gelée) : sorties historiques quand aucun état n'est sélectionné. Seul endroit du code
# où figure le dossier v2/ ; un état sélectionné n'y écrit jamais (verifier_ecriture).
ARCHIVE_2026 = RACINE / "recon/out/paquet_jardin/v2"
ARCHIVES = {
    "recon/out/paquet_jardin/v2": "état 2026 gelé (étiquette git etat_2026_gel) : lecture seule",
    "recon/out/paquet_jardin/package": "paquet v1 (état 2026) : lecture seule",
}
# sous-dossiers d'un état écrits par le pipeline (une écriture sans PJ_ETAT y est une erreur, § 3.5)
DOSSIERS_PIPELINE = ("description", "enrichi", "fabrique_hda", "controle", "validation", "ue_pilote")

FAMILLES = ("geometrie", "marquage", "texture", "objet", "vegetation", "apparence")
ORDRE_STATUT = {"valable": 0, "incertain": 1, "non_valable": 2}
JOUR_MIN, JOUR_MAX = dt.date(1900, 1, 1), dt.date(2999, 12, 31)

class Verdict(namedtuple("Verdict", "statut classe motifs")):
    __slots__ = ()

    @property
    def valable(self):
        return self.statut == "valable"


class ErreurEtat(Exception):
    """Configuration d'état absente, invalide ou incohérente."""


class EcritureCroisee(ErreurEtat):
    """Écriture d'un état dans le dossier d'un autre état (ou dans une archive en lecture seule)."""


# =========================================================================== dates
_RE_DATE = re.compile(r"(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")


def jour(x):
    """date ISO (AAAA-MM-JJ) -> datetime.date."""
    if isinstance(x, dt.datetime):
        return x.date()
    if isinstance(x, dt.date):
        return x
    return dt.date.fromisoformat(str(x)[:10])


def intervalle_date(x):
    """Date d'observation -> (jour_debut, jour_fin) ; None si aucune date lisible.
    Accepte un datetime / date, « AAAA-MM-JJ[Thh:mm[:ss]] », « AAAA-MM » (le mois), « AAAA » (l'année) ;
    dans un texte (« 2025-04-03 (panneau) ; 2026-05-14 (édition OSM) »), la première date citée."""
    if x is None:
        return None
    if isinstance(x, (dt.date, dt.datetime)):
        j = jour(x)
        return j, j
    m = _RE_DATE.search(str(x))
    if not m:
        return None
    a = int(m.group(1))
    if m.group(3):
        j = dt.date(a, int(m.group(2)), int(m.group(3)))
        return j, j
    if m.group(2):
        mo = int(m.group(2))
        fin = dt.date(a + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)
        return dt.date(a, mo, 1), fin
    return dt.date(a, 1, 1), dt.date(a, 12, 31)


def iso(j):
    return j.isoformat() if j not in (None, JOUR_MIN, JOUR_MAX) else None


# =========================================================================== géométrie (numpy, L93)
def _anneaux_geojson(g):
    """Géométrie GeoJSON -> (polygones [[anneaux (N,2)]], lignes [(N,2)], points (M,2))."""
    polys, lignes, pts = [], [], []
    t = g["type"]
    if t == "Polygon":
        polys.append([np.asarray(r, float)[:, :2] for r in g["coordinates"]])
    elif t == "MultiPolygon":
        polys += [[np.asarray(r, float)[:, :2] for r in p] for p in g["coordinates"]]
    elif t == "LineString":
        lignes.append(np.asarray(g["coordinates"], float)[:, :2])
    elif t == "MultiLineString":
        lignes += [np.asarray(c, float)[:, :2] for c in g["coordinates"]]
    elif t == "Point":
        pts.append(np.asarray(g["coordinates"], float)[:2])
    elif t == "MultiPoint":
        pts += [np.asarray(c, float)[:2] for c in g["coordinates"]]
    elif t == "GeometryCollection":
        for s in g["geometries"]:
            a, b, c = _anneaux_geojson(s)
            polys += a
            lignes += b
            pts += list(c)
    else:
        raise ErreurEtat(f"géométrie non gérée : {t}")
    return polys, lignes, np.asarray(pts, float).reshape(-1, 2)


class Emprise:
    """Emprise d'un événement ou d'une observation : polygones (avec trous), lignes ou points, dilatés de rayon_m.
    distance_signee(P) < 0 à l'intérieur ; les lignes et points n'ont d'intérieur que par leur rayon."""

    def __init__(self, geom, rayon_m=0.0):
        self.rayon = float(rayon_m or 0.0)
        self.polys, lignes, self.pts = _anneaux_geojson(geom)
        A, B = [], []
        for p in self.polys:
            for r in p:
                r = r[:-1] if len(r) > 1 and np.allclose(r[0], r[-1]) else r
                A.append(r)
                B.append(np.roll(r, -1, axis=0))
        for L in lignes:
            A.append(L[:-1])
            B.append(L[1:])
        self.A = np.vstack(A) if A else np.zeros((0, 2))
        self.B = np.vstack(B) if B else np.zeros((0, 2))
        tous = [self.A, self.B, self.pts]
        tous = np.vstack([t for t in tous if len(t)]) if any(len(t) for t in tous) else np.zeros((1, 2))
        self.bbox = (*tous.min(axis=0), *tous.max(axis=0))
        self._anneaux = [[(r[:-1] if len(r) > 1 and np.allclose(r[0], r[-1]) else r) for r in p] for p in self.polys]

    def _dedans(self, P):
        dedans = np.zeros(len(P), bool)
        x, y = P[:, 0][:, None], P[:, 1][:, None]
        for p in self._anneaux:
            par = np.zeros(len(P), bool)
            for r in p:
                xa, ya = r[:, 0][None], r[:, 1][None]
                xb, yb = np.roll(r[:, 0], -1)[None], np.roll(r[:, 1], -1)[None]
                cond = (ya > y) != (yb > y)
                with np.errstate(divide="ignore", invalid="ignore"):
                    xi = xa + (y - ya) * (xb - xa) / (yb - ya)
                par ^= (np.count_nonzero(cond & (x < xi), axis=1) % 2).astype(bool)
            dedans |= par
        return dedans

    def distance_signee(self, P, marge=0.0):
        """Distance signée (m) des points P (N, 2) L93 à l'emprise dilatée de rayon_m ; les points dont la boîte
        élargie de `marge` ne touche pas l'emprise reçoivent +inf (rejet rapide)."""
        P = np.atleast_2d(np.asarray(P, float))
        out = np.full(len(P), np.inf)
        x0, y0, x1, y1 = self.bbox
        m = self.rayon + marge
        proches = (P[:, 0] >= x0 - m) & (P[:, 0] <= x1 + m) & (P[:, 1] >= y0 - m) & (P[:, 1] <= y1 + m)
        idx = np.nonzero(proches)[0]
        for k0 in range(0, len(idx), 256):
            k = idx[k0:k0 + 256]
            Q = P[k]
            d = np.full(len(Q), np.inf)
            if len(self.A):
                AB = self.B - self.A
                L2 = np.maximum((AB ** 2).sum(axis=1), 1e-18)
                AQ = Q[:, None, :] - self.A[None]
                t = np.clip((AQ * AB[None]).sum(axis=2) / L2[None], 0.0, 1.0)
                pr = self.A[None] + t[..., None] * AB[None]
                d = np.minimum(d, np.sqrt(((Q[:, None, :] - pr) ** 2).sum(axis=2)).min(axis=1))
            if len(self.pts):
                d = np.minimum(d, np.sqrt(((Q[:, None, :] - self.pts[None]) ** 2).sum(axis=2)).min(axis=1))
            if self._anneaux:
                d = np.where(self._dedans(Q), -d, d)
            out[k] = d - self.rayon
        return out

    def position(self, p, marge=0.0, precision=0.0):
        """'dedans' (au-delà de marge + précision du bord), 'bord' ou 'dehors'."""
        r = float(marge) + float(precision or 0.0)
        sd = float(self.distance_signee(np.asarray(p, float)[None, :2], r)[0])
        if sd < -r:
            return "dedans"
        return "bord" if sd <= r else "dehors"


# =========================================================================== événements
class Evenement:
    def __init__(self, f, marge_defaut):
        p = f["properties"]
        self.props = p
        self.id = p["id"]
        self.type = p.get("type", "evenement")
        self.observe = bool(p.get("observe", True))
        fam = p.get("familles") or ["toutes"]
        self.familles = frozenset(fam)
        inconnues = self.familles - set(FAMILLES) - {"toutes"}
        if inconnues:
            raise ErreurEtat(f"{self.id} : familles inconnues {sorted(inconnues)}")
        self.marge = float(p.get("marge_m") if p.get("marge_m") is not None else marge_defaut)
        self.emprise = Emprise(f["geometry"], p.get("rayon_m", 0.0))
        if self.type == "observation_negative":
            d = intervalle_date(p.get("date") or p.get("date_min"))
            if d is None:
                raise ErreurEtat(f"{self.id} : observation négative sans date")
            self.date = d[1]
            vis = p.get("evenements")
            self.vise = frozenset(vis) if vis else None
            return
        a, b = p.get("date_min"), p.get("date_max")
        self.date_min = jour(a) if a else JOUR_MIN
        self.date_max = jour(b) if b else JOUR_MAX
        if p.get("date_min_borne") == "au_plus":     # date réelle antérieure ou égale : borne ouverte à gauche
            self.date_min = JOUR_MIN
        if self.date_max <= self.date_min:
            raise ErreurEtat(f"{self.id} : date_max {b} ≤ date_min {a}")
        self.observe_post = []
        op = p.get("observe_post")
        if isinstance(op, str):
            self.observe_post.append((jour(op), None))
        elif isinstance(op, list):
            for o in op:
                z = Emprise(o["zone"]) if o.get("zone") else None
                self.observe_post.append((jour(o["date"]), z))

    def touche(self, familles):
        return "toutes" in self.familles or "toutes" in familles or bool(self.familles & familles)


# =========================================================================== état
class Etat:
    """Configuration d'état chargée (voir charger())."""

    def __init__(self, config, fichier):
        self.config = config
        self.fichier = fichier
        self.id = config["id"]
        self.date_cible = config["date_cible"]
        self.T = jour(self.date_cible)
        self.date_etat = config["date_etat"]
        self.saison = config["saison"]
        self.dossier_sortie = RACINE / config["dossier_sortie"]
        self.sha256 = hashlib.sha256(canonique(config).encode("utf-8")).hexdigest()
        self._ev = None

    def __repr__(self):
        return f"Etat({self.id}, T={self.date_cible}, sha256={self.sha256[:12]})"

    # ------------------------------------------------------------------ chemins
    def dossier(self, nom):
        """Sous-dossier de sortie de l'état (description, enrichi, fabrique_hda, controle, validation, ...)."""
        return self.dossier_sortie / self.config.get("dossiers", {}).get(nom, nom)

    def _chemin(self, table, nom):
        v = self.config.get(table, {}).get(nom)
        if v is None:
            raise KeyError(f"état {self.id} : {table}.{nom} non déclaré dans {rel(self.fichier)}")
        v = v.get("chemin") if isinstance(v, dict) else v
        if v is None:
            raise KeyError(f"état {self.id} : {table}.{nom} sans chemin")
        return RACINE / v

    def reference(self, nom, exiger=False):
        """Chemin d'une référence de l'état (mnt, relief_zones, xodr, lanes, manoeuvres, surfaces_v1...).
        exiger=True : erreur explicite si le fichier n'est pas encore produit (lot de la phase 1 indiqué)."""
        p = self._chemin("references", nom)
        if exiger and not p.exists():
            info = self.config["references"][nom]
            lot = info.get("lot") if isinstance(info, dict) else None
            raise FileNotFoundError(f"référence {nom} de l'état {self.id} absente : {rel(p)}"
                                    + (f" (à produire par le lot {lot})" if lot else ""))
        return p

    def source(self, nom):
        """Chemin (fichier ou dossier) d'une source de l'état (gam, pcrs2019, ortho2022, osm...)."""
        return self._chemin("sources", nom)

    def source_info(self, nom):
        return dict(self.config["sources"][nom])

    def entree_partagee(self, nom):
        """Entrée lue en lecture seule dans l'archive (ex. poses 2026, points de départ du solveur 1i)."""
        return self._chemin("entrees_partagees", nom)

    def param(self, cle, defaut=None):
        return self.config.get(cle, defaut)

    # ------------------------------------------------------------------ tables
    @property
    def v_temporelle(self):
        """v_temporelle des marquages {source: {état de zone: poids}} (marquages_sources, FUS-SRC-001)."""
        return {s: {k: float(v) for k, v in t.items() if not k.startswith("_")}
                for s, t in self.config["v_temporelle_marquages"].items() if not s.startswith("_")}

    @property
    def sources_marquages(self):
        """Table SOURCES de marquages_sources (rang, r, libellé) pour l'état."""
        return {s: dict(v) for s, v in self.config["sources_marquages"].items() if not s.startswith("_")}

    @functools.cached_property
    def regles(self):
        """Surcharge des paramètres d'état des règles (assets/specs/regles_*.json restent intacts)."""
        f = self.config.get("regles_surcharge")
        return json.loads((RACINE / f).read_text(encoding="utf-8")) if f else {}

    def famille_de(self, classe):
        """Familles d'événements qui concernent une classe d'observation (recensement : marquage, arbre...)."""
        t = self.config["familles_observations"]
        return list(t.get(classe, t.get("_defaut", ["toutes"])))

    def statut_objet(self, statut_2026):
        """Statut à T d'un objet du paquet v1 d'après son statut_2026 (present, absent, a_verifier...)."""
        t = self.config["statut_objets_v1"]
        return t.get(statut_2026, t.get("_defaut", "a_verifier"))

    def age(self, date_realisation=None, contexte=None):
        """Âge relatif à T (neuf | recent | ancien | inconnu) d'un ouvrage réalisé à date_realisation."""
        a = self.config["age"]
        if contexte and contexte in a.get("par_contexte", {}):
            return a["par_contexte"][contexte]["age"]
        d = intervalle_date(date_realisation)
        if d is None:
            return "inconnu"
        ans = (self.T - d[1]).days / 365.25
        if ans < 0:
            return "inconnu"                         # ouvrage postérieur à T : absent de l'état
        for nom, seuil in a["seuils_ans"]:
            if ans <= seuil:
                return nom
        return a.get("au_dela", "ancien")

    def source_interdite(self, texte):
        """Identifiant de la source interdite citée dans `texte` (URL, nom), ou None (§ 2.8)."""
        s = str(texte).lower()
        for si in self.config["sources_interdites"]:
            for motif in si["motifs"]:
                if motif.lower() in s:
                    return si["id"]
        return None

    def manifeste(self):
        """Bloc etat_cible {id, sha256, date_cible} écrit par chaque manifeste (§ 3.5)."""
        return {"id": self.id, "sha256": self.sha256, "date_cible": self.date_cible,
                "fichier": rel(self.dossier_sortie / FICHIER_FIGE)}

    def filtre_leve(self):
        """Filtre du levé GAM par classe de datation (fonction fournie par le lot 1c), ou None s'il n'existe pas
        encore : filtre(couche, features, etat) -> features admissibles."""
        f = (self.config["sources"].get("gam") or {}).get("filtre")
        if not f:
            return None
        chemin = RACINE / f["module"]
        if not chemin.exists():
            return None
        import importlib.util
        spec = importlib.util.spec_from_file_location("_filtre_leve_" + chemin.stem, chemin)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, f["fonction"], None)
        return (lambda couche, feats: fn(couche, feats, self)) if fn else None

    # ------------------------------------------------------------------ événements et validité
    @property
    def evenements(self):
        if self._ev is None:
            f = RACINE / self.config["evenements"]["fichier"]
            d = json.loads(f.read_text(encoding="utf-8"))
            marge = float(self.config["evenements"].get("marge_defaut_m", 0.0))
            ev = [Evenement(x, marge) for x in d["features"]]
            ids = [e.id for e in ev]
            if len(ids) != len(set(ids)):
                raise ErreurEtat(f"{rel(f)} : identifiants en double")
            self._ev = ev
        return [e for e in self._ev if e.type != "observation_negative"]

    @property
    def observations_negatives(self):
        self.evenements
        return [e for e in self._ev if e.type == "observation_negative"]

    def evenement(self, eid):
        for e in self.evenements + self.observations_negatives:
            if e.id == eid:
                return e
        raise KeyError(eid)

    def _intervalle_au_point(self, ev, p, precision, familles):
        """[date_min ; date_max] de l'événement au point p, après observations négatives et observe_post."""
        dmin, dmax = ev.date_min, ev.date_max
        if p is None:
            return dmin, dmax
        for o in self.observations_negatives:
            vise = (ev.id in o.vise) if o.vise is not None else not ev.observe
            if not vise or o.date <= dmin:
                continue
            if not ("toutes" in o.familles or familles <= o.familles):
                continue                             # la vue ne prouve rien pour ces familles
            if o.emprise.position(p, 0.0, precision) == "dedans":
                dmin = o.date
        for d2, zone in ev.observe_post:
            if d2 > dmin and (zone is None or zone.position(p, 0.0, precision) == "dedans"):
                dmax = min(dmax, d2)
        return dmin, dmax

    def valide(self, date_obs, point_l93, famille, precision_m=0.0):
        """Validité à T d'une observation datée date_obs, au point point_l93 (x, y L93, ou None si inconnu),
        pour une famille (str ou liste ; « toutes »). -> Verdict(statut, classe, motifs)
        statut : valable | incertain | non_valable ; classe : voir classe_date() ; motifs : [{evenement, effet,
        raison}] triés par identifiant."""
        fams = frozenset([famille] if isinstance(famille, str) else famille)
        inconnues = fams - set(FAMILLES) - {"toutes"}
        if inconnues:
            raise ValueError(f"familles inconnues : {sorted(inconnues)}")
        di = intervalle_date(date_obs)
        if di is None:
            return Verdict("incertain", "incertaine", [{"evenement": None, "effet": "incertain",
                                                        "raison": f"date d'observation illisible : {date_obs!r}"}])
        d0, d1 = di
        T = self.T
        lo, hi = min(d0, T), max(d1, T)
        p = None if point_l93 is None else np.asarray(point_l93, float)[:2]
        if p is not None and not np.all(np.isfinite(p)):
            p = None
        motifs = []
        for ev in self.evenements:
            if not ev.touche(fams):
                continue
            dmin, dmax = self._intervalle_au_point(ev, p, precision_m, fams)
            if not max(dmin, lo) < min(dmax, hi):
                continue                             # aucun changement possible entre d et T
            pos = "inconnue" if p is None else ev.emprise.position(p, ev.marge, precision_m)
            if pos == "dehors":
                continue
            per = f"]{iso(dmin) or '…'} ; {iso(dmax) or '…'}["
            if pos == "inconnue":
                effet, raison = "incertain", f"position inconnue ; {ev.id} {per} touche le site entre d et T"
            elif not ev.observe:
                effet, raison = "incertain", f"{ev.id} non observé {per}, {pos}"
            elif pos == "bord":
                effet, raison = "incertain", f"à moins de {ev.marge:g} m (+ {float(precision_m or 0):g} m) du bord de {ev.id} {per}"
            elif dmin < d0 and d1 < dmax:
                effet, raison = "non_valable", f"observation pendant {ev.id} {per}"
            elif dmin < T < dmax:
                effet, raison = "incertain", f"T pendant {ev.id} {per}"
            else:
                effet, raison = "non_valable", f"{ev.id} {per} sépare l'observation de T"
            motifs.append({"evenement": ev.id, "effet": effet, "raison": raison})
        motifs.sort(key=lambda m: m["evenement"] or "")
        statut = max((m["effet"] for m in motifs), key=ORDRE_STATUT.get, default="valable")
        return Verdict(statut, self._classe(statut, motifs, d0, d1), motifs)

    def _classe(self, statut, motifs, d0, d1):
        if statut == "non_valable":
            return "pendant_evenement" if any(m["raison"].startswith("observation pendant") for m in motifs
                                              if m["effet"] == "non_valable") else "separee_par_evenement"
        if statut == "incertain":
            return "incertaine"
        if d0 <= self.T <= d1:
            return "jour_cible" if d0 == d1 else "contemporaine"
        return "anterieure_valable" if d1 < self.T else "posterieure_valable"

    def classe_date(self, date_obs, point_l93, famille, precision_m=0.0):
        """Classe relative à T : jour_cible | contemporaine (intervalle contenant T) | anterieure_valable |
        posterieure_valable | incertaine | separee_par_evenement | pendant_evenement."""
        return self.valide(date_obs, point_l93, famille, precision_m).classe

    def valide_observation(self, obs):
        """valide() appliqué à une observation du recensement (date_image, position.l93, classe, precision_m)."""
        pos = obs.get("position") or {}
        return self.valide(obs.get("date_image"), pos.get("l93"), self.famille_de(obs.get("classe")),
                           pos.get("precision_m") or 0.0)


# =========================================================================== chargement
def canonique(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def rel(p):
    p = Path(p).resolve()
    try:
        return p.relative_to(RACINE).as_posix()
    except ValueError:
        return p.as_posix()


def sha256_fichier(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _fusion(a, b):
    """Fusion profonde (b surcharge a) ; les listes sont remplacées."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = _fusion(a.get(k), v) if k in a else v
        return out
    return b


def _developper(obj, var):
    if isinstance(obj, dict):
        return {k: _developper(v, var) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_developper(v, var) for v in obj]
    if isinstance(obj, str) and "{" in obj:
        try:
            return obj.format(**var)
        except (KeyError, IndexError, ValueError):
            return obj
    return obj


SAISONS = {12: "hiver", 1: "hiver", 2: "hiver", 3: "printemps", 4: "printemps", 5: "printemps",
           6: "ete", 7: "ete", 8: "ete", 9: "automne", 10: "automne", 11: "automne"}
REQUIS = ("id", "libelle", "date_cible", "date_etat", "saison", "evenements", "sources", "sources_interdites",
          "v_temporelle_marquages", "sources_marquages", "regles_chronologie", "references", "dossier_sortie",
          "entrees_partagees", "ue", "schema_description", "familles_observations", "statut_objets_v1", "age")


def etats_disponibles():
    return sorted(f.stem for f in ETATS.glob("*.json") if "." not in f.stem)


def charger(id=None, date_cible=None):
    """Charge l'état `id` (défaut : variable PJ_ETAT ; None si elle est absente ou vide).
    date_cible (défaut : PJ_DATE_CIBLE) choisit une variante déclarée dans `variantes` ; une date non déclarée
    est acceptée (date_etat et saison déduites du mois) et signalée dans config['variante']."""
    id = id if id is not None else os.environ.get(ENV_ETAT, "").strip()
    if not id:
        return None
    f = ETATS / f"{id}.json"
    if not f.exists():
        raise ErreurEtat(f"état inconnu « {id} » (PJ_ETAT) ; états disponibles : {', '.join(etats_disponibles())}")
    brut = json.loads(f.read_text(encoding="utf-8"))
    manquants = [k for k in REQUIS if k not in brut]
    if manquants or brut.get("id") != id:
        raise ErreurEtat(f"{rel(f)} : clés manquantes {manquants} ou id ≠ {id}")
    date_cible = date_cible if date_cible is not None else (os.environ.get(ENV_DATE, "").strip() or None)
    cfg = dict(brut)
    if date_cible and date_cible != brut["date_cible"]:
        jour(date_cible)                                     # date ISO obligatoire
        var = (brut.get("variantes") or {}).get(date_cible)
        if var:
            cfg = _fusion(cfg, var.get("surcharges", {}))
            cfg["variante"] = {"date_cible": date_cible, "declaree": True, "libelle": var.get("libelle")}
        else:
            m = int(date_cible[5:7])
            cfg["date_etat"] = date_cible[:7]
            cfg["saison"] = {"nom": SAISONS[m], "mois": m, "note": "date non déclarée : saison déduite du mois"}
            cfg["variante"] = {"date_cible": date_cible, "declaree": False,
                               "avertissement": "date non déclarée dans variantes : sources datées à revoir"}
        cfg["date_cible"] = date_cible
    var = {"dossier_sortie": cfg["dossier_sortie"], "date_cible": cfg["date_cible"], "date_etat": cfg["date_etat"]}
    var.update({f"date_{k}": v for k, v in (cfg.get("dates_derivees") or {}).items()})
    cfg = _developper(cfg, var)
    fichiers = {"configuration": {"fichier": rel(f), "sha256": sha256_fichier(f)}}
    for cle, chemin in (("evenements", cfg["evenements"]["fichier"]), ("regles", cfg.get("regles_surcharge"))):
        if chemin and (RACINE / chemin).exists():
            fichiers[cle] = {"fichier": chemin, "sha256": sha256_fichier(RACINE / chemin)}
    cfg["fichiers"] = fichiers
    return Etat(cfg, f)


@functools.lru_cache(maxsize=None)
def _courant(id, date):
    return charger(id or "", date)


def courant():
    """État de l'exécution (PJ_ETAT, PJ_DATE_CIBLE), mémorisé ; None sans PJ_ETAT."""
    return _courant(os.environ.get(ENV_ETAT, "").strip(), os.environ.get(ENV_DATE, "").strip() or None)


def dossier(nom):
    """Sous-dossier de sortie : celui de l'état courant, sinon celui de l'archive 2026 (comportement historique)."""
    E = courant()
    return E.dossier(nom) if E else ARCHIVE_2026 / nom


def racine_sortie():
    E = courant()
    return E.dossier_sortie if E else ARCHIVE_2026


def reference(nom, defaut):
    """Référence de l'état courant, sinon le chemin historique `defaut` (archive 2026)."""
    E = courant()
    return E.reference(nom) if E else Path(defaut)


def source(nom, defaut):
    E = courant()
    return E.source(nom) if E else Path(defaut)


# =========================================================================== garde-fous d'écriture (§ 3.5)
@functools.lru_cache(maxsize=None)
def _dossiers_declares():
    out = {}
    for i in etats_disponibles():
        try:
            d = json.loads((ETATS / f"{i}.json").read_text(encoding="utf-8")).get("dossier_sortie")
        except (OSError, ValueError):
            continue
        if d:
            out[(RACINE / d).resolve()] = i
    return out


def _id_fige(dossier_etat):
    f = Path(dossier_etat) / FICHIER_FIGE
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("id")
    except (OSError, ValueError):
        return None


def etat_du_chemin(chemin):
    """À quel état appartient un chemin ? -> ("etat", id, racine) | ("archive", libellé, racine) | None.
    Racine d'état : ancêtre contenant etat_cible.json, ou dossier_sortie déclaré par une configuration."""
    p = Path(chemin).resolve()
    archives = {(RACINE / k).resolve(): v for k, v in ARCHIVES.items()}
    declares = _dossiers_declares()
    for a in [p] + list(p.parents):
        i = _id_fige(a) if (a / FICHIER_FIGE).is_file() else None
        if i:
            return ("etat", i, a)
        if a in declares:
            return ("etat", declares[a], a)
        if a in archives:
            return ("archive", archives[a], a)
    return None


def verifier_ecriture(chemin, etat=False):
    """Refuse une écriture croisée (§ 3.5) : un état n'écrit ni dans une archive ni dans le dossier d'un autre
    état ; sans PJ_ETAT, aucune écriture dans les sous-dossiers du pipeline d'un état (description, enrichi,
    fabrique_hda, controle, validation, ue_pilote). Lève EcritureCroisee."""
    E = courant() if etat is False else etat
    ou = etat_du_chemin(chemin)
    if ou is None:
        return
    p = Path(chemin).resolve()
    if E is None:
        if ou[0] == "etat":
            relatif = p.relative_to(ou[2]).parts
            if relatif and (relatif[0] in DOSSIERS_PIPELINE or relatif[0] == FICHIER_FIGE):
                raise EcritureCroisee(f"écriture dans {rel(p)} sans PJ_ETAT : dossier de l'état « {ou[1]} » "
                                      f"(lancer : python recon/pcg/etat/lancer.py --etat {ou[1]} -- …)")
        return
    if ou[0] == "archive":
        raise EcritureCroisee(f"écriture refusée dans {rel(p)} : {ou[1]} (état courant {E.id})")
    if ou[1] != E.id:
        raise EcritureCroisee(f"écriture refusée dans {rel(p)} : dossier de l'état « {ou[1]} », état courant « {E.id} »")


def contenu_fige(E):
    """Copie figée de la configuration effective (écrite dans <dossier_sortie>/etat_cible.json)."""
    return {"schema": SCHEMA_FIGE, "id": E.id, "date_cible": E.date_cible, "sha256": E.sha256,
            "note": "copie figée de la configuration effective de l'état ; sha256 = SHA-256 du JSON canonique "
                    "(clés triées, séparateurs compacts, UTF-8) du champ etat_cible ; chaque manifeste cite {id, sha256}",
            "etat_cible": E.config}


def figer(E, nouvelle_date=False, ecrire=True):
    """Vérifie puis écrit <dossier_sortie>/etat_cible.json. -> (action, message)
    action : cree | inchange | mis_a_jour | refus_id | refus_date | a_creer / a_mettre_a_jour (ecrire=False)."""
    f = E.dossier_sortie / FICHIER_FIGE
    if f.exists():
        try:
            ancien = json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            return "refus_id", f"{rel(f)} illisible ({e})"
        if ancien.get("id") != E.id:
            return "refus_id", f"{rel(f)} appartient à l'état « {ancien.get('id')} », pas à « {E.id} »"
        if ancien.get("date_cible") != E.date_cible and not nouvelle_date:
            return "refus_date", (f"{rel(f)} est figé pour T = {ancien.get('date_cible')} ; T demandée {E.date_cible} "
                                  "(--nouvelle-date pour changer de date : les sorties existantes sont à refaire)")
        if ancien.get("sha256") == E.sha256:
            return "inchange", f"{rel(f)} inchangé (sha256 {E.sha256[:12]})"
        action = "mis_a_jour" if ecrire else "a_mettre_a_jour"
        msg = f"{rel(f)} : sha256 {str(ancien.get('sha256'))[:12]} -> {E.sha256[:12]}"
    else:
        action, msg = ("cree" if ecrire else "a_creer"), f"{rel(f)} créé (sha256 {E.sha256[:12]})"
    if ecrire:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(contenu_fige(E), ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return action, msg
