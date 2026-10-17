# -*- coding: utf-8 -*-
"""Description simple d'un tronçon (`description_simple/0.1`) → géométrie de contrôle 2D, mesures et contrôles.

Lit un fichier YAML de `recon/generateur/scenes_simples/` (format : `FORMAT_PROPOSE.md`), le normalise et en déduit,
**par les règles de `assets/specs/route/regles_route_fr.json`** (via `recon/generateur/regles.py`) et les gabarits
exacts du dossier 08 (`D:\\DocRoute\\08_Marquages_Geometrie_IISR7\\marquages_iisr7.json`, lu seulement) :

- la position transversale de chaque limite le long de s (lois de largeur, ligne de référence) ;
- les marquages longitudinaux (modulations, phase, interruptions), les flèches, triangles, passages piétons,
  hachures, inscriptions, figurines ; les bordures, caniveaux, abaissés, BEV ; les arbres et avancées ;
- les **mesures** (attendus calculés) et les **contrôles** de conformité (valeur / seuil / atteint / règle).

Ce n'est pas le générateur : c'est le plan coté de contrôle (vue de dessus) que le générateur Houdini devra
reproduire, et la liste des attendus qui servira à le vérifier. Python pur (math), sans écriture, déterministe.

    from description import scene
    sc = scene("S02_rue_1x1_bordures_trottoirs.yaml")
    sc.mesures, sc.controles, sc.primitives
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent                    # recon/generateur/scenes_simples
GEN = ICI.parent                                          # recon/generateur
DEPOT = GEN.parents[1]
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(ICI))
import regles  # noqa: E402
from yaml_simple import charger  # noqa: E402

FORMAT = "description_simple/0.1"
MARQUAGES_08 = Path(r"D:\DocRoute\08_Marquages_Geometrie_IISR7\marquages_iisr7.json")
MATERIAUX_SOL = DEPOT / "assets" / "specs" / "materiaux_sol.json"
EPS = 1e-9
LONGUEUR_MIN, LONGUEUR_MAX = 80.0, 120.0                 # consigne du lot catalogue (tronçons de 80 à 120 m)

# --------------------------------------------------------------------------------------------- tables des règles
# modulations (trait, vide) : IISR7 art. 113-1 B, tableau p. 6 (RF-MQ-MOD-*) ; T3 = 13/3 (multiple de 13 m)
MODULATIONS = {"T1": (3.0, 10.0), "T'1": (1.5, 5.0), "T2": (3.0, 3.5), "T'2": (0.5, 0.5), "T3": (3.0, 13.0 / 3.0 - 3.0),
               "T'3": (20.0, 6.0), "T4": (39.0, 13.0), "continue": None}
# phase des tirets : non fixée par l'IISR (MARQUAGES_IISR7_COMPLET § 3) ; choix du catalogue : chaque segment de
# ligne commence par un trait ; un trait tronqué en fin de segment n'est gardé que s'il fait au moins la moitié d'un trait
FRACTION_TRAIT_TRONQUE = 0.5

ALIAS_BANDES = {
    "voie": "voie_circulation", "voie_circulation": "voie_circulation", "voie_bus": "voie_bus",
    "bande_cyclable": "bande_cyclable", "piste_cyclable": "piste_cyclable", "stationnement": "stationnement",
    "trottoir": "trottoir", "terre_plein": "terre_plein", "bdg": "bande_derasee", "bdd": "bande_derasee",
    "bande_derasee": "bande_derasee", "surlargeur": "accotement_revetu", "accotement_revetu": "accotement_revetu",
    "berme": "berme", "separateur": "separateur", "bande_plantee": "bande_plantee",
}
ABREV = {"voie_circulation": "v", "voie_bus": "bus", "bande_cyclable": "bc", "piste_cyclable": "pc",
         "stationnement": "st", "trottoir": "tr", "terre_plein": "tp", "bande_derasee": "bd",
         "accotement_revetu": "acc", "berme": "ber", "separateur": "sep", "bande_plantee": "bp"}
VOIES = {"voie_circulation", "voie_bus"}
CHAUSSEE = VOIES | {"bande_cyclable", "stationnement", "bande_derasee", "accotement_revetu"}
HERBES = {"gazon_tondu", "herbe_haute", "gazon_sec", "noue_plantee", "terre_nue"}


def est_chaussee(b: dict) -> bool:
    """Bande au niveau de la chaussée et revêtue (une bande dérasée enherbée n'est pas de la chaussée)."""
    return b["type"] in CHAUSSEE and not (b["type"] == "bande_derasee" and b.get("materiau") in HERBES)
SENS = {"avant", "arriere", "double", "aucun"}


class ErreurDescription(ValueError):
    pass


def oui(x, defaut: bool) -> bool:
    """Booléen d'une description : true / false, « oui » / « non » (vocabulaire du lot L0)."""
    if x is None:
        return defaut
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return x != 0
    s = str(x).strip().lower()
    if s in ("oui", "o", "vrai", "true"):
        return True
    if s in ("non", "n", "faux", "false"):
        return False
    raise ErreurDescription(f"oui / non attendu, lu {x!r}")


def abscisse(v: dict, champ: str) -> float:
    """Abscisse « a » d'un évènement (« s » accepté)."""
    x = v.get("a", v.get("s"))
    if x is None:
        raise ErreurDescription(f"{champ} : abscisse « a: S » manquante")
    return float(x)


# abords « type largeur » (même table que le lot L0, description_vers_modele.TYPES_ABORDS) → matériau de sol
ABORDS = {"pelouse": "gazon_tondu", "gazon": "gazon_tondu", "herbe": "gazon_tondu", "herbe haute": "herbe_haute",
          "prairie": "herbe_haute", "friche": "herbe_haute", "champ": "terre_nue", "massif": "brf_bois_concasse",
          "parking": "enrobe_bbsg_ancien"}


def lire_abord(v, champ: str):
    """« pelouse 6 » → ("gazon_tondu", 6.0) ; un materiau_id seul → (id, None) (largeur non dite)."""
    if v is None:
        return None
    if isinstance(v, dict):
        typ = str(v.get("type", "")).strip().lower()
        mat = v.get("materiau") or ABORDS.get(typ)
        if mat is None:
            raise ErreurDescription(f"{champ} : type d'abord inconnu {typ!r}")
        return mat, (float(v["largeur"]) if v.get("largeur") is not None else None)
    mots = str(v).strip().split()
    nombres = [m for m in mots if re.match(r"^\d+([.,]\d+)?$", m)]
    typ = " ".join(m for m in mots if m not in nombres).lower()
    mat = ABORDS.get(typ, typ if typ in materiaux_connus() else None)
    if mat is None:
        raise ErreurDescription(f"{champ} : abord inconnu {v!r} ({', '.join(sorted(ABORDS))} ou materiau_id)")
    return mat, (float(nombres[0].replace(",", ".")) if nombres else None)


SYNONYMES_EVENEMENTS = {"ralentisseur_trapezoidal": "plateau", "plateau_pieton": "plateau",
                        "reduction_voies": "rabattement", "passage_pietons": "passage_pieton"}


def _r(x, n=4):
    """Arrondi stable pour les sorties (évite -0.0)."""
    v = round(float(x), n)
    return 0.0 if v == 0 else v


# ----------------------------------------------------------------------------------------------- données lues
_CACHE: dict = {}


def marquages_08() -> dict:
    if "m08" not in _CACHE:
        _CACHE["m08"] = json.loads(MARQUAGES_08.read_bytes().decode("utf-8"))
    return _CACHE["m08"]


def gabarit(nom: str) -> dict:
    g = marquages_08()["gabarits"].get(nom)
    if g is None:
        raise ErreurDescription(f"gabarit inconnu du dossier 08 : {nom}")
    return g


def glyphe(car: str, serie: str = "V<=70") -> dict:
    g = marquages_08()["glyphes"]["series"][serie].get(car)
    if g is None:
        raise ErreurDescription(f"glyphe inconnu : {car!r} ({serie})")
    return g


def materiaux_connus() -> set:
    if "mat" not in _CACHE:
        d = json.loads(MATERIAUX_SOL.read_bytes().decode("utf-8"))
        _CACHE["mat"] = set(d["materiaux"])
    return _CACHE["mat"]


def profil_bordure(nom: str) -> dict:
    """Cotes d'un profil de bordure ou de caniveau (règles RF-AS-profil_*, catalogue du dossier 14)."""
    return regles.valeur(f"RF-AS-profil_{nom}")


def table_L(v15: float) -> float:
    """Distance de présignalisation L (RF-MQ-PS-03, IISR7 p. 21) pour V15 (arrondie à la dizaine supérieure)."""
    t = regles.valeur("RF-MQ-PS-03", "V15_vers_L_m")
    cles = sorted(int(k) for k in t)
    for k in cles:
        if v15 <= k + EPS:
            return float(t[str(k)])
    raise ErreurDescription(f"V15 = {v15} hors du tableau de RF-MQ-PS-03")


def table_rabattement(L: float) -> dict:
    """Interdistances des flèches de rabattement (RF-MQ-RAB-05, IISR7 p. 22)."""
    for ligne in regles.valeur("RF-MQ-RAB-05", "table"):
        if abs(ligne["L"] - L) < EPS:
            return ligne
    raise ErreurDescription(f"L = {L} absent du tableau de RF-MQ-RAB-05")


# --------------------------------------------------------------------------------------------- tracé en plan
class Trace:
    """Ligne de référence : suite de droites et d'arcs, départ (0, 0) cap 0 (vers +x). t positif à gauche."""

    def __init__(self, elements: list):
        self.prims = []
        x = y = cap = 0.0
        s = 0.0
        for e in elements:
            if not isinstance(e, dict) or len(e) != 1:
                raise ErreurDescription(f"élément de tracé invalide : {e!r}")
            (k, v), = e.items()
            if k == "droite":
                L, kappa = float(v), 0.0
            elif k == "arc":
                R, ang = float(v["rayon"]), math.radians(float(v.get("angle", v.get("angle_deg"))))
                sg = {"gauche": 1.0, "droite": -1.0}[v.get("sens", "gauche")]
                L, kappa = R * ang, sg / R
            else:
                raise ErreurDescription(f"primitive de tracé inconnue : {k}")
            self.prims.append((s, L, x, y, cap, kappa))
            x, y, cap = self._point(self.prims[-1], L)
            s += L
        self.longueur = s

    @staticmethod
    def _point(p, u):
        s0, L, x0, y0, cap, k = p
        if abs(k) < EPS:
            return x0 + u * math.cos(cap), y0 + u * math.sin(cap), cap
        return (x0 + (math.sin(cap + k * u) - math.sin(cap)) / k,
                y0 - (math.cos(cap + k * u) - math.cos(cap)) / k, cap + k * u)

    def point(self, s: float, t: float = 0.0):
        s = min(max(s, 0.0), self.longueur)
        p = self.prims[-1]
        for q in self.prims:
            if s <= q[0] + q[1] + EPS:
                p = q
                break
        x, y, cap = self._point(p, s - p[0])
        return x - t * math.sin(cap), y + t * math.cos(cap)

    def courbe(self) -> bool:
        return any(abs(p[5]) > EPS for p in self.prims)

    def rayons(self) -> list:
        return [_r(1.0 / abs(p[5]), 3) for p in self.prims if abs(p[5]) > EPS]


# --------------------------------------------------------------------------------------------- lois de largeur
def loi(v):
    """Largeur constante (nombre) ou loi linéaire par morceaux [[s, w], …] (s absolus) → liste de points."""
    if isinstance(v, (int, float)):
        return [(0.0, float(v))]
    if isinstance(v, list) and all(isinstance(p, list) and len(p) == 2 for p in v):
        return [(float(a), float(b)) for a, b in v]
    raise ErreurDescription(f"largeur invalide : {v!r}")


def eval_loi(points, s: float) -> float:
    if len(points) == 1:
        return points[0][1]
    if s <= points[0][0]:
        return points[0][1]
    for (s0, w0), (s1, w1) in zip(points, points[1:]):
        if s <= s1 + EPS:
            return w0 if s1 - s0 < EPS else w0 + (w1 - w0) * (s - s0) / (s1 - s0)
    return points[-1][1]


# ------------------------------------------------------------------------------------------- géométrie plane
def clip_convexe(poly, a, b, c):
    """Partie du polygone où a·s + b·t + c ≥ 0 (Sutherland-Hodgman, un demi-plan)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] + c, a * q[0] + b * q[1] + c
        if fp >= 0:
            out.append(p)
        if (fp >= 0) != (fq >= 0):
            r = fp / (fp - fq)
            out.append((p[0] + r * (q[0] - p[0]), p[1] + r * (q[1] - p[1])))
    return out


def clip_poly(sujet, clip):
    """Intersection d'un polygone avec un polygone convexe (sens trigonométrique)."""
    out = list(sujet)
    n = len(clip)
    for i in range(n):
        (x1, y1), (x2, y2) = clip[i], clip[(i + 1) % n]
        a, b = -(y2 - y1), (x2 - x1)          # normale intérieure (gauche de l'arête)
        c = -(a * x1 + b * y1)
        out = clip_convexe(out, a, b, c)
        if not out:
            return []
    return out


def aire(poly) -> float:
    return 0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(poly, poly[1:] + poly[:1]))


def trigo(poly):
    return poly if aire(poly) > 0 else list(reversed(poly))


def _dans(p, poly) -> bool:
    x, y = p
    dedans = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            dedans = not dedans
    return dedans


def _croisent(a, b, c, d) -> bool:
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return (o(a, b, c) > 0) != (o(a, b, d) > 0) and (o(c, d, a) > 0) != (o(c, d, b) > 0)


def distance_polygones(poly_a, poly_b) -> float:
    """Distance minimale entre deux polygones (0 s'ils se touchent ou se recouvrent)."""
    aretes_a = list(zip(poly_a, poly_a[1:] + poly_a[:1]))
    aretes_b = list(zip(poly_b, poly_b[1:] + poly_b[:1]))
    if any(_dans(p, poly_b) for p in poly_a) or any(_dans(p, poly_a) for p in poly_b):
        return 0.0
    if any(_croisent(a, b, c, d) for a, b in aretes_a for c, d in aretes_b):
        return 0.0

    def dist_pt_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        u = 0.0 if L2 < EPS else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
        return math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)
    return min(min(dist_pt_seg(p, a, b) for p in poly_a for a, b in aretes_b),
               min(dist_pt_seg(p, a, b) for p in poly_b for a, b in aretes_a))


def poser(gab_poly, s0, t0, sens: str, x_vers="droite"):
    """Gabarit (x latéral positif à droite du sens de circulation, y dans le sens) posé en (s0, t0).

    sens « avant » : y → +s, droite → −t ; « arriere » : y → −s, droite → +t."""
    if sens == "avant":
        return [(s0 + y, t0 - x) for x, y in gab_poly]
    return [(s0 - y, t0 + x) for x, y in gab_poly]


# ------------------------------------------------------------------------------------------------------ scène
class Scene:
    def __init__(self, chemin):
        self.chemin = Path(chemin)
        self.texte = self.chemin.read_bytes().decode("utf-8")
        self.d = charger(self.chemin)
        self.primitives: list[dict] = []     # géométrie (s, t) pour le plan
        self.cotes_s: list[dict] = []        # repères longitudinaux cotés
        self.mesures: dict = {}
        self.controles: list[dict] = []
        self.regles_appliquees: set = set()
        self.avertissements: list[str] = []
        self._lire()
        self._profil()
        self._lignes_init()
        self._elements()
        self._objets()
        self._habillage()
        self._mesures()
        self._controles()

    # ------------------------------------------------------------------ lecture
    def _lire(self):
        d = self.d
        if not isinstance(d, dict) or d.get("format") != FORMAT:
            raise ErreurDescription(f"{self.chemin.name} : clé « format: {FORMAT} » absente")
        for cle in ("scene", "nom", "titre", "contexte", "trace", "profil", "attendus"):
            if cle not in d:
                raise ErreurDescription(f"{self.chemin.name} : clé obligatoire absente : {cle}")
        inconnues = set(d) - {"format", "scene", "nom", "titre", "description", "contexte", "trace", "profil",
                               "reference", "evenements", "elements", "objets", "abords", "marquages", "plan",
                               "attendus"}
        if inconnues:
            raise ErreurDescription(f"{self.chemin.name} : clés inconnues {sorted(inconnues)}")
        self.id, self.nom, self.titre = d["scene"], d["nom"], d["titre"]
        c = d["contexte"]
        self.agglo = oui(c["agglomeration"], True)
        self.vitesse = float(c["vitesse_kmh"])
        # V15 : en agglomération, plafonnée à la vitesse réglementaire (RF-MQ-PS-02) ; sinon dite par la description
        self.v15 = float(c.get("V15_kmh", self.vitesse))
        self.u = float(c.get("u_m", regles.valeur("DEF-001", "autres_routes")))
        self.categorie = c.get("categorie", "rue")
        self.usure = (self.d.get("marquages") or {}).get("usure", c.get("usure_marquages"))
        self.trace = Trace(d["trace"])
        self.L = self.trace.longueur
        self.regles_appliquees.update(["DEF-001"] if "u_m" not in c else [])

    # ------------------------------------------------------------------ profil
    def _profil(self):
        bandes, limites = [], []
        attente_limite = None
        rangs: dict = {}
        mat_par_type: dict = {}
        for k, e in enumerate(self.d["profil"]):
            if not isinstance(e, dict):
                raise ErreurDescription(f"profil[{k}] : mapping attendu, lu {e!r}")
            cles_bande = {"bande", "id", "largeur", "sens", "materiau", "niveau", "dz", "terre_plein"}
            cles_limite = {"bordure", "vue", "caniveau", "ligne", "largeur_u", "couleur", "limite", "rien"}
            inconnues = set(e) - (cles_bande if "bande" in e else cles_limite)
            if inconnues:
                raise ErreurDescription(f"profil[{k}] : clés inconnues {sorted(inconnues)}")
            if "bande" in e:
                if bandes and attente_limite is None:
                    attente_limite = {"nature": "rien"}
                if bandes:
                    limites.append(attente_limite)
                elif attente_limite is not None:
                    raise ErreurDescription("le profil commence par une limite")
                attente_limite = None
                typ = ALIAS_BANDES.get(e["bande"])
                if typ is None:
                    raise ErreurDescription(f"profil[{k}] : type de bande inconnu « {e['bande']} »")
                sens = e.get("sens", "double" if typ == "trottoir" else "aucun")
                if sens not in SENS:
                    raise ErreurDescription(f"profil[{k}] : sens inconnu {sens}")
                if typ in VOIES and sens not in ("avant", "arriere"):
                    raise ErreurDescription(f"profil[{k}] : une voie doit avoir le sens avant ou arriere")
                ab = ABREV[typ]
                rangs[ab] = rangs.get(ab, 0) + 1
                mat = e.get("materiau") or mat_par_type.get(typ)
                if e.get("materiau"):
                    mat_par_type[typ] = e["materiau"]
                b = {"id": e.get("id") or f"{ab}{rangs[ab]}", "type": typ, "sens": sens,
                     "loi": loi(e["largeur"]), "materiau": mat, "niveau": e.get("dz", e.get("niveau")),
                     "terre_plein": e.get("terre_plein"), "index": len(bandes), "champ": f"profil[{k}]"}
                bandes.append(b)
            else:
                if not bandes:
                    raise ErreurDescription("le profil commence par une limite")
                if attente_limite is not None:
                    raise ErreurDescription(f"profil[{k}] : deux limites de suite")
                if "ligne" in e and str(e["ligne"]).strip().lower() in ("aucune", "rien"):
                    attente_limite = {"nature": "rien"}            # « ligne aucune » (vocabulaire du lot L0)
                elif "ligne" in e:
                    mod = e["ligne"]
                    if mod not in MODULATIONS:
                        raise ErreurDescription(f"profil[{k}] : modulation inconnue {mod}")
                    attente_limite = {"nature": "ligne", "modulation": mod, "k": float(e["largeur_u"]),
                                      "couleur": e.get("couleur", "blanc")}
                elif "bordure" in e:
                    attente_limite = {"nature": "bordure", "profil": e["bordure"], "vue": float(e["vue"]),
                                      "caniveau": e.get("caniveau")}
                elif "rien" in e or e.get("limite") == "rien":
                    attente_limite = {"nature": "rien"}
                else:
                    raise ErreurDescription(f"profil[{k}] : entrée inconnue {e!r}")
                attente_limite["champ"] = f"profil[{k}]"
        if attente_limite is not None:
            raise ErreurDescription("le profil se termine par une limite")
        limites = [{"nature": "bord"}] + limites + [{"nature": "bord"}]
        ids = [b["id"] for b in bandes]
        if len(set(ids)) != len(ids):
            raise ErreurDescription(f"identifiants de bandes en double : {ids}")
        self.bandes, self.limites = bandes, limites
        self.par_id = {b["id"]: b for b in bandes}
        self.coupures_bordure: dict = {}          # limite → [(s0, s1)] où la bordure (et son caniveau) n'existe pas
        self.bordure_objets_m: dict = {}          # longueurs de bordure posées par les objets (avancées)
        for i, lim in enumerate(limites):
            lim["index"] = i
            g = bandes[i - 1]["id"] if i > 0 else None
            dr = bandes[i]["id"] if i < len(bandes) else None
            lim["id"] = f"{g or '|'}|{dr or '|'}"
        # niveaux : chaussée 0 ; sinon vue de la bordure qui la sépare de la chaussée (RF-OSM-NIV-010, DEF-005)
        for b in bandes:
            niv = b["niveau"]
            if isinstance(niv, str):                  # « trottoir » / « chaussee » (vocabulaire du lot L0)
                niv = niv.strip().lower().replace("é", "e")
                if niv == "chaussee":
                    b["dz"] = 0.0
                elif niv == "trottoir":
                    b["dz"] = self._dz_par_bordure(b["index"])
                else:
                    raise ErreurDescription(f"{b['champ']}.niveau : trottoir, chaussee ou un nombre (m)")
            elif niv is not None:
                b["dz"] = float(niv)
            elif est_chaussee(b):
                b["dz"] = 0.0
            else:
                b["dz"] = self._dz_par_bordure(b["index"])
        self._reference()

    def _dz_par_bordure(self, j: int) -> float:
        for pas in (-1, 1):
            i = j
            while 0 <= i + pas < len(self.bandes):
                lim = self.limites[i + (1 if pas > 0 else 0)]
                voisin = self.bandes[i + pas]
                if lim["nature"] == "bordure" and est_chaussee(voisin):
                    return lim["vue"]
                if est_chaussee(voisin):
                    break
                i += pas
        return 0.0

    def _reference(self):
        """Ligne de référence (t = 0) : séparation des sens ; à défaut milieu du terre-plein entre les sens ;
        sens unique : limite du milieu des voies (RF-OSM-PRF-010)."""
        voies = [b for b in self.bandes if b["type"] in VOIES]
        ref = self.d.get("reference")
        self.ref = None
        if isinstance(ref, dict) and "limite" in ref:
            self.ref = ("limite", int(ref["limite"]))
        else:
            for a, b in zip(self.bandes, self.bandes[1:]):
                if a["type"] in VOIES and b["type"] in VOIES and a["sens"] == "arriere" and b["sens"] == "avant":
                    self.ref = ("limite", b["index"])
                    break
            if self.ref is None:
                arr = [b["index"] for b in voies if b["sens"] == "arriere"]
                av = [b["index"] for b in voies if b["sens"] == "avant"]
                if arr and av:
                    milieu = [b for b in self.bandes[max(arr) + 1:min(av)] if b["type"] == "terre_plein"]
                    if milieu:
                        self.ref = ("bande", milieu[0]["index"])
                if self.ref is None:
                    n = len(voies)
                    if n % 2 == 0:
                        self.ref = ("limite", voies[n // 2]["index"])
                    else:
                        self.ref = ("bande", voies[n // 2]["index"])
        self.regles_appliquees.add("RF-OSM-PRF-010")

    def largeur(self, j: int, s: float) -> float:
        return eval_loi(self.bandes[j]["loi"], s)

    def t_limite(self, i: int, s: float) -> float:
        """t de la limite i (0 = bord gauche du profil) à l'abscisse s."""
        kind, r = self.ref
        if kind == "limite":
            t_r = 0.0
        else:
            t_r = self.largeur(r, s) / 2.0       # t de la limite r (bord gauche de la bande r)
        if i <= r:
            return t_r + sum(self.largeur(j, s) for j in range(i, r))
        return t_r - sum(self.largeur(j, s) for j in range(r, i))

    def t_axe_bande(self, j: int, s: float) -> float:
        return 0.5 * (self.t_limite(j, s) + self.t_limite(j + 1, s))

    def s_points(self, extra=()) -> list:
        pts = {0.0, self.L}
        for b in self.bandes:
            for s, _ in b["loi"]:
                if 0 <= s <= self.L:
                    pts.add(float(s))
        for s in extra:
            if 0 <= s <= self.L:
                pts.add(float(s))
        return sorted(pts)

    # ------------------------------------------------------------------ primitives
    def ajouter(self, calque, forme, **k):
        p = {"calque": calque, "forme": forme}
        p.update(k)
        self.primitives.append(p)
        return p

    def ruban(self, i_g: int, i_d: int, s0: float, s1: float, dt_g=0.0, dt_d=0.0):
        """Polygone entre la limite i_g (décalée de dt_g vers la droite) et la limite i_d (décalée de dt_d)."""
        ss = [s for s in self.s_points() if s0 < s < s1]
        ss = [s0] + ss + [s1]
        haut = [(s, self.t_limite(i_g, s) - dt_g) for s in ss]
        bas = [(s, self.t_limite(i_d, s) - dt_d) for s in reversed(ss)]
        return haut + bas

    # ------------------------------------------------------------------ lignes longitudinales
    def _lignes_init(self):
        """Segments de marquage par limite : [s0, s1, modulation, k]."""
        self.segments = {}
        for lim in self.limites:
            if lim["nature"] == "ligne":
                self.segments[lim["index"]] = [[0.0, self.L, lim["modulation"], lim["k"]]]
                self.regles_appliquees.add(f"RF-MQ-MOD-{lim['modulation']}" if lim["modulation"] != "continue"
                                           else "RF-MQ-LAR-A1a")
        self.coupures = {}                      # limite → [(c0, c1, motif)]
        self.lignes_obliques = []               # polygones de lignes obliques continues

    def remplacer_modulation(self, i: int, s0: float, s1: float, mod: str, k: float):
        segs = self.segments.setdefault(i, [])
        nouv = []
        for a, b, m, kk in segs:
            if b <= s0 or a >= s1:
                nouv.append([a, b, m, kk])
                continue
            if a < s0:
                nouv.append([a, s0, m, kk])
            if b > s1:
                nouv.append([s1, b, m, kk])
        nouv.append([max(0.0, s0), min(self.L, s1), mod, k])
        self.segments[i] = sorted(nouv)

    def couper(self, i: int, c0: float, c1: float, motif: str):
        self.coupures.setdefault(i, []).append((c0, c1, motif))
        segs = self.segments.get(i, [])
        nouv = []
        for a, b, m, kk in segs:
            if b <= c0 or a >= c1:
                nouv.append([a, b, m, kk])
                continue
            if a < c0:
                nouv.append([a, c0, m, kk])
            if b > c1:
                nouv.append([c1, b, m, kk])
        self.segments[i] = sorted(nouv)

    def tirets(self, a: float, b: float, mod: str):
        if MODULATIONS[mod] is None:
            return [(a, b)]
        trait, vide = MODULATIONS[mod]
        out, x = [], a
        while x < b - EPS:
            fin = min(x + trait, b)
            if fin - x >= FRACTION_TRAIT_TRONQUE * trait - 1e-6:
                out.append((x, fin))
            x += trait + vide
        return out

    def _dessiner_lignes(self):
        self.traits = {}            # modulation → nombre de traits
        self.longueur_continue = {}
        for i, segs in sorted(self.segments.items()):
            lim = self.limites[i]
            couleur = lim.get("couleur", "blanc")
            for a, b, mod, k in segs:
                w = k * self.u
                cle = f"{mod} {int(k) if k == int(k) else k}u"
                for x0, x1 in self.tirets(a, b, mod):
                    ss = [x0] + [s for s in self.s_points() if x0 < s < x1] + [x1]
                    if self.trace.courbe():
                        n = max(1, int(math.ceil((x1 - x0) / 0.5)))
                        ss = sorted(set(ss) | {x0 + (x1 - x0) * j / n for j in range(n + 1)})
                    poly = [(s, self.t_limite(i, s) + w / 2) for s in ss] + \
                           [(s, self.t_limite(i, s) - w / 2) for s in reversed(ss)]
                    self.ajouter("marquage", "poly", st=poly, couleur=couleur, role=f"ligne {cle}",
                                 limite=lim["id"])
                    if MODULATIONS[mod] is None:
                        self.longueur_continue[cle] = self.longueur_continue.get(cle, 0.0) + (x1 - x0)
                    else:
                        self.traits[cle] = self.traits.get(cle, 0) + 1

    # ------------------------------------------------------------------ éléments ponctuels
    def chaussee_autour(self, j: int):
        """(i_gauche, i_droite) des limites qui bordent le groupe de bandes de chaussée contenant la bande j."""
        g = j
        while g - 1 >= 0 and est_chaussee(self.bandes[g - 1]):
            g -= 1
        d = j
        while d + 1 < len(self.bandes) and est_chaussee(self.bandes[d + 1]):
            d += 1
        return g, d + 1

    def premiere_voie(self):
        return next(b for b in self.bandes if b["type"] in VOIES)

    def _elements(self):
        self.pp = []
        self.fleches = []
        self.triangles = []
        self.abaisses = []
        self.bevs = []
        self.ralentisseurs = []
        self.inscriptions = []
        self.hachures = []
        self.oblique = None
        self.reductions = []
        self.zones_dep = []
        cle = "evenements" if self.d.get("evenements") is not None else "elements"
        elements = self.d.get(cle) or []
        # ordre : modifications de modulation, puis coupures (passages), puis le reste
        ordre = {"dos_d_ane": 0, "zone_depassement_interdit": 0, "rabattement": 0, "plateau": 1,
                 "passage_pieton": 1, "fleches": 2, "inscription": 2}
        items = []
        for k, e in enumerate(elements):
            if not isinstance(e, dict) or len(e) != 1:
                raise ErreurDescription(f"{cle}[{k}] : « - type: {{…}} » attendu")
            (typ, v), = e.items()
            typ = SYNONYMES_EVENEMENTS.get(typ, typ)
            if typ not in ordre:
                raise ErreurDescription(f"{cle}[{k}] : type inconnu {typ}")
            items.append((ordre[typ], k, typ, v))
        for _, k, typ, v in sorted(items, key=lambda x: (x[0], x[1])):
            getattr(self, f"_el_{typ}")(v, f"{cle}[{k}]")
        self._dessiner_lignes()

    def _limites_interieures(self, g: int, d: int):
        return [i for i in range(g + 1, d) if self.limites[i]["nature"] == "ligne"]

    def _el_passage_pieton(self, v, champ, s_c=None, longueur=None, sur_plateau=None):
        s_c = abscisse(v, champ) if s_c is None else s_c
        Lb = float(longueur if longueur is not None else
                   v.get("largeur", v.get("longueur_bandes", regles.valeur("DEF-011", "longueur_bandes_ville"))))
        j = self.premiere_voie()["index"]
        g, d = self.chaussee_autour(j)
        W = self.t_limite(g, s_c) - self.t_limite(d, s_c)
        n = int(math.floor(W - 0.5 + EPS))                                   # DEF-011 (n maximal)
        e = (W - 0.5 * n) / (n + 1)                                          # RF-MQ-PP-05
        t_g = self.t_limite(g, s_c)
        bandes = []
        for q in range(n):
            t_haut = t_g - e - q * (0.5 + e)
            poly = [(s_c - Lb / 2, t_haut), (s_c + Lb / 2, t_haut), (s_c + Lb / 2, t_haut - 0.5),
                    (s_c - Lb / 2, t_haut - 0.5)]
            bandes.append(poly)
            self.ajouter("marquage", "poly", st=poly, couleur="blanc", role="passage piéton")
        inter = regles.valeur("RF-MQ-PP-03", "distance")
        for i in self._limites_interieures(g, d):
            self.couper(i, s_c - Lb / 2 - inter, s_c + Lb / 2 + inter, "passage_pieton")
        pp = {"s": s_c, "longueur_bandes": Lb, "W": W, "n": n, "e": e, "g": g, "d": d, "champ": champ,
              "sur_plateau": sur_plateau}
        self.pp.append(pp)
        self.regles_appliquees.update(["DEF-011", "RF-MQ-PP-01", "RF-MQ-PP-02", "RF-MQ-PP-03", "RF-MQ-PP-05"])
        self.cotes_s += [{"s": s_c - Lb / 2, "texte": "passage"}, {"s": s_c + Lb / 2, "texte": ""}]
        # abaissés et BEV de chaque côté (bordures qui bordent la chaussée)
        ab = v.get("abaisses") if isinstance(v, dict) else None
        if isinstance(ab, dict):
            pente = float(ab.get("pente_pct", 5))
        else:
            ab = oui(ab, True)                    # abaissés par défaut à toute traversée (RF-MA-BEV-001, ARR2007)
            # rampants à 5 % par défaut (DEF-031 rampant_5pct ; pente < 5 % de l'arrêté de 2007, RF-MA-TRO-003)
            pente = float(v.get("pente_rampants_pct", 5)) if isinstance(v, dict) else 5.0
        if sur_plateau is None and ab:            # sur un plateau, les abaissés sont posés par le ralentisseur
            nouveaux = []
            for i_b, cote in ((g, "gauche"), (d, "droite")):
                lim = self.limites[i_b]
                if lim["nature"] != "bordure":
                    continue
                dh = lim["vue"] - regles.valeur("DEF-031", "vue")
                Lr = dh / (pente / 100.0)               # rampants latéraux parallèles à la bordure (RF-MA-ABA-004)
                a = {"limite": i_b, "cote": cote, "s0": s_c - Lb / 2, "s1": s_c + Lb / 2,
                     "rampant": Lr, "pente_pct": pente, "vue": regles.valeur("DEF-031", "vue"), "dh": dh}
                self.abaisses.append(a)
                nouveaux.append(a)
            self.regles_appliquees.update(["DEF-031", "RF-MA-ABA-001", "RF-MA-ABA-004", "RF-MA-ABA-005"])
            if oui(v.get("bev"), True):
                for a in nouveaux:
                    self._bev(a)

    def _bev(self, a):
        i_b = a["limite"]
        cote = a["cote"]
        j_tr = i_b - 1 if cote == "gauche" else i_b                 # bande haute (trottoir)
        largeur_tr = self.largeur(j_tr, a["s0"])
        prof = regles.valeur("DEF-031", "BEV_profondeur")
        if largeur_tr < 1.90:
            prof = regles.valeur("DEF-031", "BEV_reduite_si_trottoir_lt_1_90")
        recul = regles.valeur("DEF-031", "BEV_recul_nez")
        sg = 1.0 if cote == "gauche" else -1.0
        t0 = self.t_limite(i_b, a["s0"]) + sg * recul
        t1 = t0 + sg * prof
        poly = [(a["s0"], t0), (a["s1"], t0), (a["s1"], t1), (a["s0"], t1)]
        self.bevs.append({"s0": a["s0"], "s1": a["s1"], "profondeur": prof, "recul": recul, "cote": cote,
                          "poly": poly})
        self.ajouter("sol", "poly", st=poly, couleur="bev", role="BEV")
        self.regles_appliquees.update(["DEF-031", "RF-MA-BEV-001", "RF-MA-BEV-002"])

    def _el_plateau(self, v, champ):
        """Ralentisseur trapézoïdal (décret 94-447) : a = milieu du plateau, longueur = dessus du plateau."""
        s_c = abscisse(v, champ)
        plateau = float(v.get("longueur", v.get("plateau")))
        h = float(v["hauteur"])
        rampe = float(v["rampe_pct"])
        Lr = h / (rampe / 100.0)
        j = self.premiere_voie()["index"]
        g, d = self.chaussee_autour(j)
        r = {"type": "trapezoidal", "s": s_c, "plateau": plateau, "hauteur": h, "rampe_pct": rampe, "rampant": Lr,
             "s_debut": s_c - plateau / 2 - Lr, "s_fin": s_c + plateau / 2 + Lr, "g": g, "d": d}
        self.ralentisseurs.append(r)
        for s0, s1, role in ((s_c - plateau / 2 - Lr, s_c - plateau / 2, "rampe"),
                             (s_c - plateau / 2, s_c + plateau / 2, "plateau"),
                             (s_c + plateau / 2, s_c + plateau / 2 + Lr, "rampe")):
            self.ajouter("relief", "poly", st=self.ruban(g, d, s0, s1), couleur=role, role=role)
        self.cotes_s += [{"s": r["s_debut"], "texte": "rampe"}, {"s": s_c - plateau / 2, "texte": "plateau"},
                         {"s": s_c + plateau / 2, "texte": "rampe"}, {"s": r["s_fin"], "texte": ""}]
        self.regles_appliquees.update(["RF-MA-RAL-001", "RF-MA-RAL-004", "RF-MQ-PP-04"])
        pp = v.get("passage_pieton")
        if isinstance(pp, dict) or oui(pp, False):
            pp = pp if isinstance(pp, dict) else {"bev": v.get("bev")}
            prolong = regles.valeur("RF-MQ-PP-04", "prolongement")
            Lb = plateau + 2 * prolong
            self._el_passage_pieton(pp, champ, s_c=s_c, longueur=Lb, sur_plateau={"plateau": plateau, "h": h})
            # abaissés : la chaussée remonte de h ; la vue résiduelle sur le plateau est vue − h
            for i_b, cote in ((g, "gauche"), (d, "droite")):
                lim = self.limites[i_b]
                if lim["nature"] != "bordure":
                    continue
                a = {"limite": i_b, "cote": cote, "s0": s_c - plateau / 2, "s1": s_c + plateau / 2, "rampant": 0.0,
                     "pente_pct": None, "vue": _r(lim["vue"] - h, 4), "dh": 0.0, "par_plateau": True}
                self.abaisses.append(a)
                if oui(pp.get("bev"), True):
                    self._bev(a)
            self.regles_appliquees.update(["RF-GV-RAL-002", "RF-MA-ABA-001", "RF-MA-ABA-005"])

    def _el_dos_d_ane(self, v, champ):
        """Dos-d'âne circulaire : a = milieu du ralentisseur."""
        Ld = float(v.get("longueur", regles.valeur("RF-MA-RAL-001", "dos_d_ane.longueur")))
        s0 = abscisse(v, champ) - Ld / 2
        h = float(v.get("hauteur", regles.valeur("RF-MA-RAL-001", "dos_d_ane.hauteur")))
        j = self.premiere_voie()["index"]
        g, d = self.chaussee_autour(j)
        self.ralentisseurs.append({"type": "dos_d_ane", "s": s0, "longueur": Ld, "hauteur": h, "s_debut": s0,
                                   "s_fin": s0 + Ld, "g": g, "d": d})
        self.ajouter("relief", "poly", st=self.ruban(g, d, s0, s0 + Ld / 2), couleur="rampe", role="dos-d'âne")
        self.ajouter("relief", "poly", st=self.ruban(g, d, s0 + Ld / 2, s0 + Ld), couleur="rampe",
                     role="dos-d'âne")
        tri = gabarit("TRIANGLE_DOS_ANE")["polygone"]
        pas = gabarit("TRIANGLE_DOS_ANE")["largeur_m"]
        for b in self.bandes:
            if b["type"] not in VOIES:
                continue
            ta = self.t_axe_bande(b["index"], s0)
            base_s = s0 if b["sens"] == "avant" else s0 + Ld          # partie montante dans le sens de circulation
            for q in (-1, 0, 1):
                poly = poser(tri, base_s, ta, b["sens"])
                dx = q * pas
                poly = [(s, t - dx if b["sens"] == "avant" else t + dx) for s, t in poly]
                self.triangles.append({"voie": b["id"], "poly": poly})
                self.ajouter("marquage", "poly", st=poly, couleur="blanc", role="triangle dos-d'âne")
        # axe T3 2u sur le ralentisseur, prolongé d'environ 10 m (chaussée bidirectionnelle ≥ 5 m, RF-MQ-RAL-01)
        W = self.t_limite(g, s0) - self.t_limite(d, s0)
        sens = {b["sens"] for b in self.bandes if b["type"] in VOIES}
        if W >= 5.0 - EPS and sens == {"avant", "arriere"}:
            i_axe = self.ref[1]
            self.remplacer_modulation(i_axe, s0 - 10.0, s0 + Ld + 10.0, "T3", 2)
            self.axe_dos_d_ane = (s0 - 10.0, s0 + Ld + 10.0)
            self.regles_appliquees.add("RF-MQ-MOD-T3")
        self.cotes_s += [{"s": s0, "texte": "dos-d'âne"}, {"s": s0 + Ld, "texte": ""},
                         {"s": s0 - 10.0, "texte": "T3"}, {"s": s0 + Ld + 10.0, "texte": "T'1"}]
        self.regles_appliquees.update(["RF-MA-RAL-001", "RF-MQ-RAL-01", "RF-MA-RAL-003"])

    def _el_zone_depassement_interdit(self, v, champ):
        sens = v.get("sens", "avant")
        s_c = abscisse(v, champ)                                    # début de la ligne continue axiale
        L = table_L(self.v15)
        tab = table_rabattement(L)
        i_axe = self.ref[1]
        # continue axiale à partir de s_c, ligne d'annonce T3 2u de longueur L avant (RF-MQ-PS-04)
        if sens == "avant":
            self.remplacer_modulation(i_axe, s_c - L, s_c, "T3", 2)
            self.remplacer_modulation(i_axe, s_c, self.L, "continue", 2)
            positions = [s_c - L, s_c - L + tab["i1"], s_c - L + tab["i1"] + tab["i2"]]
        else:
            self.remplacer_modulation(i_axe, s_c, s_c + L, "T3", 2)
            self.remplacer_modulation(i_axe, 0.0, s_c, "continue", 2)
            positions = [s_c + L, s_c + L - tab["i1"], s_c + L - tab["i1"] - tab["i2"]]
        g = gabarit("RAB_D")["polygone"]
        t_axe = self.t_limite(i_axe, s_c)
        for s in positions:                  # à cheval sur la ligne d'annonce (RF-MQ-RAB-02)
            poly = poser(g, s, t_axe, sens)
            self.fleches.append({"gabarit": "RAB_D", "s": s, "t": t_axe, "sens": sens, "poly": poly,
                                 "voie": "axe"})
            self.ajouter("marquage", "poly", st=poly, couleur="blanc", role="flèche RAB_D")
        self.zones_dep.append({"sens": sens, "s_continue": s_c, "L": L, "annonce": (s_c - L, s_c),
                               "fleches": positions, "table": tab})
        self.cotes_s += [{"s": s_c - L, "texte": "annonce T3"}, {"s": s_c, "texte": "continue"}] + \
                        [{"s": s, "texte": f"RAB {q + 1}"} for q, s in enumerate(positions)]
        self.regles_appliquees.update(["RF-MQ-PS-02", "RF-MQ-PS-03", "RF-MQ-PS-04", "RF-MQ-RAB-01", "RF-MQ-RAB-02",
                                       "RF-MQ-RAB-03", "RF-MQ-RAB-05", "RF-MQ-LAR-A3a", "RF-MQ-SC-01"])

    def _el_rabattement(self, v, champ):
        """Réduction du nombre de voies : a = point de fin (PCF) du rétrécissement physique, biseau = sa longueur Lp,
        voie = identifiant ou « gauche » / « droite » (voie extrême du sens dit) ; l'oblique marquée a la longueur
        max(Lp, L) et finit au PCF (RF-MQ-OBL-02)."""
        sens = v.get("sens", "avant")
        vid = v["voie"]
        if vid in ("gauche", "droite"):
            vs = [b for b in self.bandes if b["type"] in VOIES and b["sens"] == sens]
            vid = (vs[0] if vid == "gauche" else vs[-1])["id"]
        b = self.par_id[vid]
        j = b["index"]
        pcf = abscisse(v, champ)
        L = table_L(self.v15)                                      # RF-MQ-PS-03
        Lp = float(v.get("biseau", v.get("Lp")))
        if Lp >= L - EPS:
            Lob = Lp                                               # RF-MQ-OBL-02 : Lp si Lp ≥ L
        else:
            Lob = L                                                # sinon L en amont du point de fin
        s0 = pcf - Lob
        pci = pcf - Lp
        w = eval_loi(b["loi"], s0)
        b["loi"] = [(0.0, w), (pci, w), (pcf, 0.0)]
        cote = "gauche" if j == 0 or self.limites[j]["nature"] == "bordure" else "droite"
        if cote != "gauche":
            raise ErreurDescription("reduction_voies : seule la suppression de la voie de gauche est prise en charge")
        # la bande élargie (trottoir) absorbe la largeur rendue
        el = v.get("elargit")
        if el is None and j > 0 and self.limites[j]["nature"] == "bordure":
            el = self.bandes[j - 1]["id"]                          # la bande au-delà de la bordure (trottoir)
        if el:
            be = self.par_id[el]
            we = eval_loi(be["loi"], s0)
            be["loi"] = [(0.0, we), (pci, we), (pcf, we + w)]
        i_bord, i_ligne = j, j + 1                                 # bordure à gauche, ligne de voie à droite
        # oblique continue 3u (RF-MQ-LAR-A1c) raccordée à la bordure à ses deux bouts : son bord extérieur part du
        # nez de bordure au début de l'oblique et rejoint le nez de la bordure rabattue au point de fin (PCF) ; elle
        # passe sur le caniveau CS (affleurant) à ses extrémités
        k_ob = 3.0
        w_ob = k_ob * self.u
        cani = self.limites[i_bord].get("caniveau")
        l_cani = profil_bordure(cani)["base_m"] if cani else 0.0
        A = (s0, self.t_limite(i_bord, s0) - w_ob / 2)
        B = (pcf, self.t_limite(i_bord, pcf) - w_ob / 2)
        dx, dy = B[0] - A[0], B[1] - A[1]
        n = math.hypot(dx, dy)
        nx, ny = -dy / n * w_ob / 2, dx / n * w_ob / 2
        poly = [(A[0] + nx, A[1] + ny), (B[0] + nx, B[1] + ny), (B[0] - nx, B[1] - ny), (A[0] - nx, A[1] - ny)]
        self.ajouter("marquage", "poly", st=poly, couleur="blanc", role="oblique continue 3u")
        # la ligne de voie s'arrête là où l'oblique s'en approche à moins de 2u bord à bord (choix générateur [G],
        # par analogie avec l'espace non peint de 2u de RF-MQ-MUS-01) : elle ne doit ni croiser ni toucher l'oblique
        lim_l = self.limites[i_ligne]
        w_l = lim_l.get("k", 0.0) * self.u
        ecart = w_ob / 2 + w_l / 2 + 2 * self.u
        t_l = self.t_limite(i_ligne, s0)
        s_arret = A[0] + (A[1] - (t_l + ecart)) * (B[0] - A[0]) / (A[1] - B[1]) if A[1] > B[1] else pcf
        s_arret = min(s_arret, pcf)
        self.couper(i_ligne, s_arret, self.L + 1.0, "reduction_voies")
        self.oblique = {"s0": s0, "s1": pcf, "L": L, "Lob": Lob, "Lp": Lp, "pci": pci, "pcf": pcf,
                        "milieu": s0 + Lob / 2, "A": A, "B": B, "largeur": w_ob, "poly": poly,
                        "arret_ligne_voie": s_arret}
        self.cotes_s.append({"s": s_arret, "texte": "fin T'1"})
        # flèches de rabattement dans l'axe de la voie supprimée (RF-MQ-RAB-02, -04, -05, -07)
        tab = table_rabattement(L)
        M = s0 + Lob / 2
        d_k = [L, L - tab["i1"], L - tab["i1"] - tab["i2"]]
        nf = v.get("nombre_fleches", v.get("fleches", True))
        if isinstance(nf, bool) or isinstance(nf, str):
            nb = int(regles.valeur("RF-MQ-RAB-03", "nombre")) if oui(nf, True) else 0
        else:
            nb = int(nf)
        g = gabarit("RAB_D")["polygone"]
        t_axe = self.t_limite(i_bord, 0.0) - w / 2                  # axe de la voie en section courante
        candidates = []
        for q, dk in enumerate(d_k):
            s = M - dk
            poly_f = poser(g, s, t_axe, "avant")
            candidates.append({"gabarit": "RAB_D", "s": s, "t": t_axe, "sens": "avant", "poly": poly_f,
                               "voie": vid, "rang": q + 1, "distance_milieu": dk})
        for f in candidates[:nb]:
            self.fleches.append(f)
            self.ajouter("marquage", "poly", st=f["poly"], couleur="blanc", role="flèche RAB_D")
        self.fleches_candidates = candidates
        # zébra : hachures entre l'oblique et la bordure (RF-MQ-HACH-01, DEF-020)
        if oui(v.get("zebra"), True):
            self._zebra(i_bord, A, B, w_ob, l_cani, s0, pci, pcf)
        self.reductions.append({"voie": vid, "s0": s0, "pci": pci, "pcf": pcf, "L": L, "Lp": Lp, "Lob": Lob,
                                "fleches": nb})
        self.cotes_s += [{"s": c["s"], "texte": f"RAB {c['rang']}"} for c in candidates[:nb]] + \
                        [{"s": s0, "texte": "oblique"}, {"s": M, "texte": "milieu"}, {"s": pci, "texte": "PCI"},
                         {"s": pcf, "texte": "PCF"}]
        self.regles_appliquees.update(["RF-MQ-PS-03", "RF-MQ-OBL-02", "RF-MQ-RET-01", "RF-MQ-RAB-01", "RF-MQ-RAB-02",
                                       "RF-MQ-RAB-03", "RF-MQ-RAB-04", "RF-MQ-RAB-05", "RF-MQ-RAB-07",
                                       "RF-MQ-LAR-A1c"])

    def _zebra(self, i_bord, A, B, w_ob, l_cani, s0, pci, pcf):
        h = regles.valeur("DEF-020")
        bande, esp, ang = h["bande"], h["espacement"], math.radians(h["angle_rive_deg"])
        marge = 2 * self.u                                        # espace non peint 2u (RF-MQ-MUS-01)
        aplat = h["aplat_si_largeur_inf"]

        def t_bord(s):                                            # bord du caniveau côté chaussée, moins 2u
            return self.t_limite(i_bord, s) - l_cani - marge

        def t_obl(s):
            return A[1] + (B[1] - A[1]) * (s - A[0]) / (B[0] - A[0])
        n_ob = math.hypot(B[0] - A[0], B[1] - A[1])
        dt_ob = (w_ob / 2 + marge) * n_ob / (B[0] - A[0])         # bord gauche de l'oblique + 2u

        def largeur_zone(s):                                      # largeur (en t) disponible pour les hachures
            return t_bord(s) - (t_obl(s) + dt_ob)

        def chercher(a, b, seuil):
            """s de [a, b] où largeur_zone franchit seuil (fonction monotone sur [a, b])."""
            fa = largeur_zone(a) - seuil
            for _ in range(80):
                m = 0.5 * (a + b)
                fm = largeur_zone(m) - seuil
                if (fm >= 0) == (fa >= 0):
                    a, fa = m, fm
                else:
                    b = m
            return 0.5 * (a + b)
        # la zone (triangle) va du point où l'oblique quitte la marge du bord au point où le bord la rejoint
        sz0 = chercher(s0, pci, 0.0)
        sz1 = chercher(pci, pcf, 0.0)
        zone = trigo([(sz0, t_bord(sz0)), (pci, t_bord(pci)), (sz1, t_bord(sz1)),
                      (sz1, t_obl(sz1) + dt_ob), (sz0, t_obl(sz0) + dt_ob)])
        sa = chercher(sz0, pci, aplat)                            # largeur 0,30 atteinte (DEF-020)
        sb = chercher(pci, sz1, aplat)
        for c0, c1 in ((sz0, sa), (sb, sz1)):                     # pointes effilées : aplat (RF-MQ-HACH-03)
            p = clip_convexe(zone, 1.0, 0.0, -c0)
            p = clip_convexe(p, -1.0, 0.0, c1)
            if len(p) >= 3 and abs(aire(p)) > 1e-5:
                self.ajouter("marquage", "poly", st=p, couleur="blanc", role="aplat zébra")
                self.hachures.append({"type": "aplat", "poly": p})
        # hachures : direction (2, -1) (2 parallèlement à la rive pour 1 perpendiculairement), pas ⊥ = bande + esp
        ux, uy = math.cos(ang), -math.sin(ang)
        nx, ny = -uy, ux                                          # normale
        pas = bande + esp
        # phase : une bande démarre là où la zone atteint 0,30 (choix générateur, DEF-020 / § 19)
        p0 = (sa, self.t_limite(i_bord, sa) - l_cani - marge)
        c_ref = nx * p0[0] + ny * p0[1]
        proj = [nx * p[0] + ny * p[1] for p in zone]
        kmin = int(math.floor((min(proj) - c_ref) / pas)) - 1
        kmax = int(math.ceil((max(proj) - c_ref) / pas)) + 1
        zone_utile = clip_convexe(clip_convexe(zone, 1.0, 0.0, -sa), -1.0, 0.0, sb)
        for k in range(kmin, kmax + 1):
            c1 = c_ref + k * pas                                  # bord amont de la bande k (k = 0 : part de p0)
            c0 = c1 + bande
            p = clip_convexe(zone_utile, nx, ny, -c1)
            p = clip_convexe(p, -nx, -ny, c0)
            if len(p) >= 3 and abs(aire(p)) > 1e-4:
                self.ajouter("marquage", "poly", st=p, couleur="blanc", role="hachure")
                self.hachures.append({"type": "hachure", "poly": p})
        self.zebra = {"zone": zone, "s_zone": (sz0, sz1), "s_aplat": (sa, sb), "angle_deg": h["angle_rive_deg"],
                      "bande": bande, "espacement": esp, "marge": marge}
        self.regles_appliquees.update(["DEF-020", "RF-MQ-HACH-01", "RF-MQ-HACH-03", "RF-MQ-MUS-01"])

    def _el_fleches(self, v, champ):
        nom = v["type"]
        g = gabarit(nom)["polygone"]
        voies = v.get("voies", "toutes")
        cibles = [b for b in self.bandes if b["type"] in VOIES] if voies == "toutes" else [self.par_id[x]
                                                                                          for x in voies]
        a = v.get("a", v.get("s"))
        if isinstance(a, list):
            positions = [float(x) for x in a]
        else:                                                      # 1re flèche + nombre + interdistance (DEF-017)
            n = int(v.get("nombre", regles.valeur("DEF-017", "nombre_par_voie")))
            pas = float(v.get("interdistance", regles.valeur("DEF-017", "interdistance")))
            positions = [float(a) + q * pas for q in range(n)]
        for b in cibles:
            for s in positions:
                ta = self.t_axe_bande(b["index"], float(s))
                poly = poser(g, float(s), ta, b["sens"])
                self.fleches.append({"gabarit": nom, "s": float(s), "t": ta, "sens": b["sens"], "poly": poly,
                                     "voie": b["id"]})
                self.ajouter("marquage", "poly", st=poly, couleur="blanc", role=f"flèche {nom}")
        self.cotes_s += [{"s": s, "texte": nom} for s in positions]
        self.regles_appliquees.update(["DEF-017", "RF-MQ-DIR-02", "RF-MQ-DIR-03", "RF-MQ-DIR-04", "RF-MQ-DIR-08",
                                       "RF-MQ-DIR-09"])

    def _el_inscription(self, v, champ):
        texte = v["texte"]
        b = self.par_id[v["voie"]]
        s0 = abscisse(v, champ)
        hauteur = float(v.get("hauteur", 1.5))
        serie = "V<=70" if hauteur <= 1.5 + EPS else "V>70"
        esp = 0.15                                                 # espacement entre caractères (D.2 p. 69)
        largeurs = [glyphe(c, serie)["largeur_m"] for c in texte]
        total = sum(largeurs) + esp * (len(texte) - 1)
        ta = self.t_axe_bande(b["index"], s0)
        x = -total / 2
        polys = []
        for c, lc in zip(texte, largeurs):
            gl = glyphe(c, serie)
            for part in gl["parties"]:
                anneaux = [part["exterieur"]] + part.get("trous", [])
                anneaux_st = [poser([(x + px, py) for px, py in ann], s0, ta, b["sens"]) for ann in anneaux]
                polys.append(anneaux_st)
                self.ajouter("marquage", "poly_trous", anneaux=anneaux_st, couleur="blanc", role=f"lettre {c}")
            x += lc + esp
        self.inscriptions.append({"texte": texte, "voie": b["id"], "s": s0, "hauteur": hauteur,
                                  "largeur_totale": total})
        self.cotes_s.append({"s": s0, "texte": texte})
        self.regles_appliquees.update(["RF-MQ-TC-03", "RF-MA-CTC-002"])

    # ------------------------------------------------------------------ objets le long
    def _objets(self):
        self.arbres = []
        self.avancees = []
        self.places = []
        self.figurines = []
        for k, e in enumerate(self.d.get("objets") or []):
            (typ, v), = e.items()
            if typ == "avancees_plantees":
                self._obj_avancees(v)
            elif typ == "arbres":
                self._obj_arbres(v)
            elif typ == "figurines":
                self._obj_figurines(v)
            else:
                raise ErreurDescription(f"objets[{k}] : type inconnu {typ}")

    def _centres(self, v):
        c0, c1, pas = float(v["de"]), float(v["a"]), float(v["pas"])
        n = int(round((c1 - c0) / pas))
        if abs(c0 + n * pas - c1) > 1e-6:
            raise ErreurDescription(f"de/a/pas incohérents : {c0} → {c1} au pas {pas}")
        return [c0 + q * pas for q in range(n + 1)], pas

    def _obj_avancees(self, v):
        b = self.par_id[v["bande"]]
        j = b["index"]
        centres, pas = self._centres(v)
        Lav = float(v["longueur"])
        t_depuis = float(v["arbre"]["t_depuis_voie"])
        # côté voie : la limite gauche de la bande (stationnement à droite de la chaussée)
        i_voie = j if self.bandes[j - 1]["type"] in VOIES else j + 1
        sg = -1.0 if i_voie == j else 1.0
        for c in centres:
            s0, s1 = c - Lav / 2, c + Lav / 2
            poly = self.ruban(j, j + 1, s0, s1)
            self.avancees.append({"s": c, "s0": s0, "s1": s1, "poly": poly})
            self.ajouter("sol", "poly", st=poly, couleur=v.get("sol", "paillage_mineral"), role="avancée plantée")
            # bordure T2 de l'avancée (3 côtés)
            base = profil_bordure(v.get("bordure", "T2"))["base_m"]
            tv = self.t_limite(i_voie, c)
            t_tr = self.t_limite(j + 1 if i_voie == j else j, c)
            for poly_b in ([(s0, tv), (s1, tv), (s1, tv + sg * base), (s0, tv + sg * base)],
                           [(s0, tv), (s0 + base, tv), (s0 + base, t_tr), (s0, t_tr)],
                           [(s1 - base, tv), (s1, tv), (s1, t_tr), (s1 - base, t_tr)]):
                self.ajouter("bordure", "poly", st=poly_b, couleur="bordure", role="bordure avancée")
            # l'avancée prolonge le trottoir : la bordure principale et son caniveau sont interrompus à son droit
            i_tr = j + 1 if i_voie == j else j
            self.coupures_bordure.setdefault(i_tr, []).append((s0, s1))
            prof = v.get("bordure", "T2")
            self.bordure_objets_m[prof] = self.bordure_objets_m.get(prof, 0.0) + Lav + 2 * abs(t_tr - tv)
            ta = tv + sg * t_depuis
            self.arbres.append({"s": c, "t": ta, "bande": b["id"], "dist_voie": t_depuis})
            self.ajouter("vegetation", "arbre", s=c, t=ta, rayon=float(v["arbre"].get("houppier_rayon", 2.5)))
            # la ligne de délimitation du stationnement est interrompue au droit des avancées
            if self.limites[i_voie]["nature"] == "ligne":
                self.couper(i_voie, s0, s1, "avancee")
        for a, bq in zip(self.avancees, self.avancees[1:]):
            self.places.append({"s0": a["s1"], "s1": bq["s0"], "longueur": bq["s0"] - a["s1"]})
        self.regles_appliquees.update(["DEF-030", "DEF-009", "RF-MA-STA-001", "RF-OSM-VEG-001"])
        # la ligne a été coupée après le dessin des lignes : on redessine
        self.primitives = [p for p in self.primitives if not p.get("role", "").startswith("ligne ")]
        self._dessiner_lignes()

    def _obj_arbres(self, v):
        b = self.par_id[v["bande"]]
        centres, pas = self._centres(v)
        for c in centres:
            ta = self.t_axe_bande(b["index"], c)
            self.arbres.append({"s": c, "t": ta, "bande": b["id"]})
            self.ajouter("vegetation", "arbre", s=c, t=ta, rayon=float(v.get("houppier_rayon", 3.0)))
        self.regles_appliquees.update(["DEF-030", "RF-GV-TPC-010"])

    def _obj_figurines(self, v):
        g = gabarit(v.get("gabarit", "VELO"))
        for bid in v["bandes"]:
            b = self.par_id[bid]
            sens = b["sens"]
            for s in (v.get("a", v.get("s"))):
                ta = self.t_axe_bande(b["index"], float(s))
                y0 = -g["boite"]["y"][1] / 2
                anneaux = [poser([(x, y + y0) for x, y in g["polygone"]], float(s), ta, sens)]
                anneaux += [poser([(x, y + y0) for x, y in part], float(s), ta, sens) for part in g.get("parties", [])]
                self.figurines.append({"bande": bid, "s": float(s), "t": ta})
                self.ajouter("marquage", "poly_trous", anneaux=anneaux, couleur="blanc", role="figurine vélo")
        self.regles_appliquees.update(["DEF-018", "RF-MA-CYC-012", "RF-MQ-CYC-03"])

    # ------------------------------------------------------------------ sols, bordures
    def intervalles_bordure(self, i: int) -> list:
        """Intervalles [s0, s1] où la bordure de la limite i existe (tronçon moins les coupures)."""
        out, x = [], 0.0
        for c0, c1 in sorted(self.coupures_bordure.get(i, [])):
            if c0 > x + EPS:
                out.append((x, min(c0, self.L)))
            x = max(x, c1)
        if x < self.L - EPS:
            out.append((x, self.L))
        return out

    def _habillage(self):
        """Surfaces des bandes, bordures et caniveaux, abaissés (sous les marquages : calques séparés)."""
        for b in self.bandes:
            j = b["index"]
            poly = self.ruban(j, j + 1, 0.0, self.L)
            self.ajouter("sol", "poly", st=poly, couleur=b["materiau"] or b["type"], role=f"bande {b['id']}",
                         bande=b["id"], fond=True)
        for lim in self.limites:
            if lim["nature"] != "bordure":
                continue
            i = lim["index"]
            a, c = self.bandes[i - 1], self.bandes[i]
            haut_gauche = a["dz"] > c["dz"]
            base = profil_bordure(lim["profil"])["base_m"]
            # corps de la bordure côté haut, caniveau côté bas ; interrompus au droit des avancées
            sg = 1.0 if haut_gauche else -1.0
            for a0, a1 in self.intervalles_bordure(i):
                self.ajouter("bordure", "poly", st=self.ruban(i, i, a0, a1, dt_g=0.0, dt_d=-sg * base),
                             couleur="bordure", role=f"bordure {lim['profil']}")
                if lim.get("caniveau"):
                    lc = profil_bordure(lim["caniveau"])["base_m"]
                    self.ajouter("bordure", "poly", st=self.ruban(i, i, a0, a1, dt_g=0.0, dt_d=sg * lc),
                                 couleur="caniveau", role=f"caniveau {lim['caniveau']}")
            lim["haut"] = "gauche" if haut_gauche else "droite"
        for a in self.abaisses:
            i = a["limite"]
            lim = self.limites[i]
            base = profil_bordure(lim["profil"])["base_m"]
            sg = 1.0 if lim.get("haut") == "gauche" else -1.0
            t = self.t_limite(i, a["s0"])
            self.ajouter("bordure", "poly", st=[(a["s0"], t), (a["s1"], t), (a["s1"], t + sg * base),
                                                 (a["s0"], t + sg * base)], couleur="abaisse", role="abaissé")
            if a["rampant"] > 0:
                j_tr = i - 1 if sg > 0 else i
                larg = self.largeur(j_tr, a["s0"])
                for r0, r1 in ((a["s0"] - a["rampant"], a["s0"]), (a["s1"], a["s1"] + a["rampant"])):
                    self.ajouter("sol", "poly", st=[(r0, t), (r1, t), (r1, t + sg * larg), (r0, t + sg * larg)],
                                 couleur="rampant", role="rampant")
                    self.ajouter("bordure", "poly", st=[(r0, t), (r1, t), (r1, t + sg * base), (r0, t + sg * base)],
                                 couleur="abaisse_rampant", role="bordure en rampant")
                self.ajouter("sol", "poly", st=[(a["s0"], t), (a["s1"], t), (a["s1"], t + sg * larg),
                                                (a["s0"], t + sg * larg)], couleur="abaisse_sol", role="abaissé")
                self.cotes_s += [{"s": a["s0"] - a["rampant"], "texte": "rampant"}, {"s": a["s1"] + a["rampant"],
                                                                                     "texte": ""}]

    # ------------------------------------------------------------------ mesures
    def _mesures(self):
        m = {}
        m["longueur"] = _r(self.L, 3)
        m["largeur_emprise"] = _r(sum(self.largeur(j, 0.0) for j in range(len(self.bandes))), 3)
        j = self.premiere_voie()["index"]
        g, d = self.chaussee_autour(j)
        m["largeur_chaussee"] = _r(self.t_limite(g, 0.0) - self.t_limite(d, 0.0), 3)
        nv = {}
        for b in self.bandes:
            if b["type"] in VOIES and self.largeur(b["index"], 0.0) > 0:
                nv[b["sens"]] = nv.get(b["sens"], 0) + 1
        m["voies"] = dict(sorted(nv.items()))
        if self.trace.courbe():
            m["rayons"] = self.trace.rayons()
        m["traits"] = dict(sorted(self.traits.items()))
        if self.longueur_continue:
            m["continues_m"] = {k: _r(v, 3) for k, v in sorted(self.longueur_continue.items())}
        bords = {}
        for lim in self.limites:
            if lim["nature"] == "bordure":
                cle = lim["profil"]
                bords[cle] = bords.get(cle, 0.0) + sum(self._longueur_limite(lim["index"], a0, a1)
                                                       for a0, a1 in self.intervalles_bordure(lim["index"]))
        if bords:
            m["bordures_m"] = {k: _r(v, 2) for k, v in sorted(bords.items())}
        if self.bordure_objets_m:
            m["bordures_avancees_m"] = {k: _r(v, 2) for k, v in sorted(self.bordure_objets_m.items())}
        if self.fleches:
            f = {}
            for x in self.fleches:
                f[x["gabarit"]] = f.get(x["gabarit"], 0) + 1
            m["fleches"] = dict(sorted(f.items()))
        if self.pp:
            m["passages"] = [{"s": _r(p["s"], 3), "W": _r(p["W"], 3), "bandes": p["n"], "e": _r(p["e"], 3),
                              "longueur_bandes": _r(p["longueur_bandes"], 3)} for p in self.pp]
        if self.triangles:
            m["triangles"] = len(self.triangles)
        if self.abaisses:
            m["abaisses"] = len(self.abaisses)
        if self.bevs:
            m["bev"] = len(self.bevs)
        if self.ralentisseurs:
            m["ralentisseurs"] = [{k: (_r(v, 4) if isinstance(v, float) else v) for k, v in r.items()
                                   if k not in ("g", "d")} for r in self.ralentisseurs]
        if self.arbres:
            m["arbres"] = len(self.arbres)
        if self.avancees:
            m["avancees"] = len(self.avancees)
        if self.places:
            m["places"] = len(self.places)
        if self.figurines:
            m["figurines"] = len(self.figurines)
        if self.inscriptions:
            m["inscriptions"] = {i["texte"]: sum(1 for x in self.inscriptions if x["texte"] == i["texte"])
                                 for i in self.inscriptions}
        if self.hachures:
            m["hachures"] = sum(1 for h in self.hachures if h["type"] == "hachure")
            m["aplats"] = sum(1 for h in self.hachures if h["type"] == "aplat")
        if self.oblique:
            o = self.oblique
            m["oblique"] = {"L": _r(o["L"], 3), "s0": _r(o["s0"], 3), "s1": _r(o["s1"], 3), "PCI": _r(o["pci"], 3),
                            "Lp": _r(o["Lp"], 3)}
        if self.zones_dep:
            z = self.zones_dep[0]
            m["annonce"] = {"L": _r(z["L"], 3), "s0": _r(z["annonce"][0], 3), "s1": _r(z["annonce"][1], 3)}
        if self.fleches:
            m["fleches_s"] = [_r(f["s"], 3) for f in sorted(self.fleches, key=lambda f: (f["voie"], f["s"]))]
        self.mesures = m

    def _longueur_limite(self, i: int, s0: float = 0.0, s1: float | None = None) -> float:
        s1 = self.L if s1 is None else s1
        n = max(1, int(round((s1 - s0) / 0.5)))
        tot = 0.0
        prev = None
        for q in range(n + 1):
            s = s0 + (s1 - s0) * q / n
            p = self.trace.point(s, self.t_limite(i, s))
            if prev is not None:
                tot += math.hypot(p[0] - prev[0], p[1] - prev[1])
            prev = p
        return tot

    # ------------------------------------------------------------------ contrôles
    def ctl(self, cid, sujet, valeur, seuil, atteint, regle=None, bloquant=True):
        self.controles.append({"id": cid, "sujet": sujet, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint),
                               "regle": regle, "bloquant": bloquant})

    def _controles(self):
        # longueur du tronçon
        self.ctl("longueur", "longueur du tronçon (m)", _r(self.L, 3), f"[{LONGUEUR_MIN} ; {LONGUEUR_MAX}]",
                 LONGUEUR_MIN - EPS <= self.L <= LONGUEUR_MAX + EPS)
        # règles citées (commentaires et clés) toutes présentes dans la base fusionnée
        cites = sorted(set(re.findall(r"(RF-[A-Z]{2,4}[-.][A-Za-z0-9_.'\-]*[A-Za-z0-9_']|DEF-\d{3}|ARB-\d{2})",
                                      self.texte)))
        absentes = [c for c in cites if not regles.existe(c)]
        self.regles_citees = cites
        self.ctl("regles_citees", "règles citées dans la description présentes dans regles_route_fr.json",
                 f"{len(cites) - len(absentes)}/{len(cites)}", "100 %", not absentes,
                 regle=None if not absentes else "absentes : " + ", ".join(absentes))
        app_abs = sorted(r for r in self.regles_appliquees if not regles.existe(r))
        self.ctl("regles_appliquees", "règles appliquées par le calcul présentes dans la base",
                 f"{len(self.regles_appliquees) - len(app_abs)}/{len(self.regles_appliquees)}", "100 %", not app_abs,
                 regle=", ".join(app_abs) or None)
        # matériaux connus
        mats = sorted({b["materiau"] for b in self.bandes if b["materiau"]} |
                      {lire_abord(v, f"abords.{k}")[0] for k, v in (self.d.get("abords") or {}).items()} |
                      {o[k].get("sol") for o in (self.d.get("objets") or []) for k in o if isinstance(o[k], dict)
                       and o[k].get("sol")})
        inconnus = [x for x in mats if x not in materiaux_connus()]
        self.ctl("materiaux", "matériaux présents dans assets/specs/materiaux_sol.json",
                 f"{len(mats) - len(inconnus)}/{len(mats)}", "100 %", not inconnus,
                 regle=", ".join(inconnus) or None)
        sans_mat = [b["id"] for b in self.bandes if not b["materiau"]]
        self.ctl("materiaux_bandes", "bandes avec un matériau", f"{len(self.bandes) - len(sans_mat)}/{len(self.bandes)}",
                 "100 %", not sans_mat, regle=", ".join(sans_mat) or None)
        # largeurs par type
        for b in self.bandes:
            w = self.largeur(b["index"], 0.0)
            if w <= 0:
                continue
            j = b["index"]
            lg, ld = self.limites[j], self.limites[j + 1]
            hm = w - sum(l.get("k", 0) * self.u / 2 for l in (lg, ld) if l["nature"] == "ligne")
            cani = sum(profil_bordure(l["caniveau"])["base_m"] for l in (lg, ld)
                       if l["nature"] == "bordure" and l.get("caniveau") and
                       ((l is lg and l.get("haut") == "gauche") or (l is ld and l.get("haut") == "droite")))
            t = b["type"]
            if t == "voie_circulation":
                if self.agglo:
                    v = regles.valeur("RF-GV-PT-001")
                    self.ctl(f"largeur_{b['id']}", f"voie {b['id']} : largeur (m)", _r(w, 3),
                             f"[{v['minimum_normal']} ; {v['large_PL_TC'][1]}]",
                             v["minimum_normal"] - EPS <= w <= v["large_PL_TC"][1] + EPS, "RF-GV-PT-001")
                else:
                    v = regles.valeur("RF-GV-PT-009")
                    self.ctl(f"largeur_{b['id']}", f"voie {b['id']} : largeur (m)", _r(w, 3),
                             f"[{v['moderees']} ; {v['elevees']}]", v["moderees"] - EPS <= w <= v["elevees"] + EPS,
                             "RF-GV-PT-009")
            elif t == "voie_bus":
                mn = regles.valeur("RF-MA-CTC-002", "Grenoble_min")
                self.ctl(f"largeur_{b['id']}", f"voie bus {b['id']} : largeur hors marquage (m)", _r(hm, 3),
                         f">= {mn} (Grenoble)", hm >= mn - EPS, "RF-MA-CTC-002")
            elif t == "bande_cyclable":
                mn = regles.valeur("RF-MA-BAN-001", "min_hors_marquage")
                mx = regles.valeur("RF-MA-BAN-002", "max")
                self.ctl(f"largeur_{b['id']}_min", f"bande cyclable {b['id']} : largeur hors marquage et caniveau (m)",
                         _r(hm - cani, 3), f">= {mn}", hm - cani >= mn - EPS, "RF-MA-BAN-001")
                self.ctl(f"largeur_{b['id']}_max", f"bande cyclable {b['id']} : largeur hors marquage (m)",
                         _r(hm, 3), f"<= {mx}", hm <= mx + EPS, "RF-MA-BAN-002")
            elif t == "piste_cyclable":
                mn = regles.valeur("RF-MA-PIS-001", "0-1500_velos_j_sens")
                self.ctl(f"largeur_{b['id']}", f"piste unidirectionnelle {b['id']} : largeur (m)", _r(w, 3),
                         f">= {mn}", w >= mn - EPS, "RF-MA-PIS-001")
            elif t == "trottoir":
                mn = regles.valeur("RF-MA-TRO-001", "min")
                corps = sum(profil_bordure(l["profil"])["base_m"] for l in (lg, ld) if l["nature"] == "bordure")
                libre = w - corps
                self.ctl(f"cheminement_{b['id']}", f"trottoir {b['id']} : largeur libre hors bordure (m)",
                         _r(libre, 3), f">= {mn}", libre >= mn - EPS, "RF-MA-TRO-001")
                reco = regles.valeur("RF-MA-TRO-010", "Cerema_min")
                self.ctl(f"largeur_{b['id']}", f"trottoir {b['id']} : largeur (m)", _r(w, 3), f">= {reco}",
                         w >= reco - EPS, "RF-MA-TRO-010", bloquant=False)
            elif t == "stationnement":
                v = regles.valeur("RF-MA-STA-001")
                self.ctl(f"largeur_{b['id']}", f"stationnement {b['id']} : largeur (m)", _r(w, 3),
                         f"[{v['min_marquage_compris']} ; {v['max']}]",
                         v["min_marquage_compris"] - EPS <= w <= v["max"] + EPS, "RF-MA-STA-001")
            elif t == "terre_plein":
                c = regles.valeur("RF-GV-TPC-010", "fosse_ideale_cote")
                if self.arbres and any(a["bande"] == b["id"] for a in self.arbres):
                    self.ctl(f"largeur_{b['id']}", f"terre-plein planté {b['id']} : largeur (fosse {c} × {c})",
                             _r(w, 3), f">= {c}", w >= c - EPS, "RF-GV-TPC-010")
            elif t == "bande_derasee" and self.agglo:
                mn = regles.valeur("RF-GV-TPC-005", "BDG_min")
                self.ctl(f"largeur_{b['id']}", f"BDG {b['id']} : largeur (m)", _r(w, 3), f">= {mn}",
                         w >= mn - EPS, "RF-GV-TPC-005")
        # vues de bordure dans la plage nominale du profil
        for lim in self.limites:
            if lim["nature"] == "bordure":
                plage = profil_bordure(lim["profil"]).get("vue_nominale_m")
                if plage:
                    self.ctl(f"vue_{lim['id']}", f"bordure {lim['profil']} ({lim['id']}) : vue (m)", lim["vue"],
                             f"[{plage[0]} ; {plage[1]}]", plage[0] - EPS <= lim["vue"] <= plage[1] + EPS,
                             f"RF-AS-profil_{lim['profil']}")
        # passages piétons
        for q, p in enumerate(self.pp):
            tab = regles.valeur("RF-MQ-PP-02", "table")
            plages = [(x["bandes"][0], x["bandes"][1]) for x in tab if x["largeur_m"][0] - EPS <= p["W"] <=
                      x["largeur_m"][1] + EPS]
            ok_n = any(a <= p["n"] <= b for a, b in plages)
            self.ctl(f"pp{q}_bandes", f"passage {q + 1} : nombre de bandes pour W = {p['W']:.2f} m", p["n"],
                     " ou ".join(f"[{a} ; {b}]" for a, b in plages), ok_n, "RF-MQ-PP-02")
            inter = regles.valeur("RF-MQ-PP-01", "interdistance")
            self.ctl(f"pp{q}_e", f"passage {q + 1} : interdistance et marges e (m)", _r(p["e"], 4),
                     f"[{inter[0]} ; {inter[1]}]", inter[0] - EPS <= p["e"] <= inter[1] + EPS, "RF-MQ-PP-05")
            mn = regles.valeur("RF-MQ-PP-01", "longueur_ville_min")
            self.ctl(f"pp{q}_longueur", f"passage {q + 1} : longueur des bandes (m)", p["longueur_bandes"],
                     f">= {mn}", p["longueur_bandes"] >= mn - EPS, "RF-MQ-PP-01")
            # lignes interrompues à 0,50 m
            for i, cps in self.coupures.items():
                for c0, c1, motif in cps:
                    if motif == "passage_pieton" and abs((c0 + c1) / 2 - p["s"]) < 1e-6:
                        ecart = p["s"] - p["longueur_bandes"] / 2 - c0
                        self.ctl(f"pp{q}_interruption_{i}", f"passage {q + 1} : interruption de la ligne "
                                 f"{self.limites[i]['id']} (m)", _r(ecart, 3), "0.50", abs(ecart - 0.5) < 1e-6,
                                 "RF-MQ-PP-03")
        for q, a in enumerate(self.abaisses):
            self.ctl(f"abaisse{q}_vue", f"abaissé {q + 1} ({a['cote']}) : vue (m)", a["vue"],
                     f"<= {regles.valeur('DEF-031', 'vue')}", a["vue"] <= regles.valeur("DEF-031", "vue") + EPS,
                     "RF-MA-ABA-001")
            lg = a["s1"] - a["s0"]
            mn = regles.valeur("DEF-031", "largeur_min")
            self.ctl(f"abaisse{q}_largeur", f"abaissé {q + 1} : largeur (m)", _r(lg, 3), f">= {mn}", lg >= mn - EPS,
                     "RF-MA-ABA-001")
            if a["rampant"] > 0:
                ok = (a["pente_pct"] <= 5 + EPS) or (a["pente_pct"] <= 8 + EPS and a["rampant"] <= 2.0 + EPS)
                self.ctl(f"abaisse{q}_rampant", f"abaissé {q + 1} : rampant {a['rampant']:.2f} m à "
                         f"{a['pente_pct']:g} %", a["pente_pct"], "<= 5 % (8 % sur <= 2 m)", ok, "RF-MA-TRO-003")
        for q, bv in enumerate(self.bevs):
            pp = min(self.pp, key=lambda p: abs(p["s"] - 0.5 * (bv["s0"] + bv["s1"])))
            lg = bv["s1"] - bv["s0"]
            self.ctl(f"bev{q}_etendue", f"BEV {q + 1} : étendue <= marquage (m)", _r(lg, 3),
                     f"<= {pp['longueur_bandes']}", lg <= pp["longueur_bandes"] + EPS, "RF-MA-ABA-005")
        # ralentisseurs
        for r in self.ralentisseurs:
            if r["type"] == "dos_d_ane":
                v = regles.valeur("RF-MA-RAL-001", "dos_d_ane")
                self.ctl("dos_d_ane_dims", "dos-d'âne : longueur / hauteur (m)", f"{r['longueur']} / {r['hauteur']}",
                         f"{v['longueur']} / {v['hauteur']}", abs(r["longueur"] - v["longueur"]) < EPS and
                         abs(r["hauteur"] - v["hauteur"]) < EPS, "RF-MA-RAL-001")
                self.ctl("dos_d_ane_vitesse", "dos-d'âne : vitesse de la section (km/h)", self.vitesse, "<= 30",
                         self.vitesse <= 30 + EPS, "RF-MA-RAL-001")
                n_v = sum(1 for b in self.bandes if b["type"] in VOIES)
                self.ctl("dos_d_ane_triangles", "dos-d'âne : 3 triangles par voie", len(self.triangles), 3 * n_v,
                         len(self.triangles) == 3 * n_v, "RF-MQ-RAL-01")
                pp_sur = [p for p in self.pp if r["s_debut"] - EPS < p["s"] < r["s_fin"] + EPS]
                self.ctl("dos_d_ane_sans_passage", "dos-d'âne : aucun passage piéton dessus", len(pp_sur), 0,
                         not pp_sur, "RF-MA-RAL-001")
            else:
                v = regles.valeur("RF-MA-RAL-001", "trapezoidal")
                ok = (v["plateau"][0] - EPS <= r["plateau"] <= v["plateau"][1] + EPS and
                      abs(r["hauteur"] - v["hauteur"]) < EPS and
                      v["rampants_pct"][0] - EPS <= r["rampe_pct"] <= v["rampants_pct"][1] + EPS)
                self.ctl("trapezoidal_dims", "ralentisseur trapézoïdal : plateau / hauteur / rampe",
                         f"{r['plateau']} m / {r['hauteur']} m / {r['rampe_pct']} %",
                         f"[{v['plateau'][0]} ; {v['plateau'][1]}] / {v['hauteur']} / [{v['rampants_pct'][0]} ; "
                         f"{v['rampants_pct'][1]}] %", ok, "RF-MA-RAL-001")
                self.ctl("trapezoidal_vitesse", "ralentisseur : vitesse de la section (km/h)", self.vitesse, "<= 30",
                         self.vitesse <= 30 + EPS, "RF-MA-RAL-001")
                self.ctl("trapezoidal_triangles", "passage surélevé : aucun triangle", len(self.triangles), 0,
                         not self.triangles, "RF-MQ-PP-04")
                pp = [p for p in self.pp if abs(p["s"] - r["s"]) < EPS]
                if pp:
                    att = r["plateau"] + 2 * regles.valeur("RF-MQ-PP-04", "prolongement")
                    self.ctl("trapezoidal_bandes", "passage sur plateau : longueur des bandes = plateau + 2 × 0,50",
                             pp[0]["longueur_bandes"], att, abs(pp[0]["longueur_bandes"] - att) < EPS, "RF-MQ-PP-04")
        # zone de dépassement interdit : annonce et flèches
        for z in self.zones_dep:
            a0, a1 = z["annonce"]
            self.ctl("annonce_longueur", "ligne d'annonce T3 2u : longueur = L (m)", _r(a1 - a0, 3), z["L"],
                     abs(a1 - a0 - z["L"]) < EPS, "RF-MQ-PS-04")
            n = sum(1 for f in self.fleches if f["voie"] == "axe")
            self.ctl("annonce_fleches", "flèches de rabattement sur la ligne d'annonce", n,
                     regles.valeur("RF-MQ-RAB-03", "nombre"), n == regles.valeur("RF-MQ-RAB-03", "nombre"),
                     "RF-MQ-RAB-03")
            ds = [_r(z["s_continue"] - s, 3) for s in z["fleches"]]
            att = [z["table"]["L"], z["table"]["L"] - z["table"]["i1"], z["table"]["d_continue"]]
            self.ctl("annonce_positions", "distances des flèches au début de la continue (m)", ds, att,
                     all(abs(a - b) < EPS for a, b in zip(ds, att)), "RF-MQ-RAB-05")
        # réduction de voies
        for red in self.reductions:
            o = self.oblique
            self.ctl("oblique_longueur", "oblique : longueur (Lp < L → L) (m)", _r(o["Lob"], 3), o["L"],
                     abs(o["Lob"] - max(o["L"], o["Lp"])) < EPS, "RF-MQ-OBL-02")
            premiere = min(f["s"] for f in self.fleches if f["voie"] == red["voie"])
            self.ctl("rabattement_premiere", "1re flèche : L/2 en amont du début de l'oblique (m)",
                     _r(o["s0"] - premiere, 3), o["L"] / 2, abs(o["s0"] - premiere - o["L"] / 2) < EPS, "RF-MQ-RAB-04")
            # chaque flèche candidate doit rester du côté de la voie ouverte, à 2u au moins du bord de l'oblique
            # (seuil [G] : espace non peint de 2u, par analogie avec RF-MQ-MUS-01) ; une marge négative veut dire
            # que la flèche empiète sur l'oblique ou sur le zébra
            seuil = 2 * self.u
            for c in self.fleches_candidates:
                m = self.marge_oblique(c["poly"])
                retenue = any(f is c for f in self.fleches)
                self.ctl(f"rabattement_fleche{c['rang']}_marge",
                         f"flèche {c['rang']} (à {c['distance_milieu']:g} m du milieu de l'oblique) : marge au bord "
                         f"de l'oblique côté voie ouverte (m){'' if retenue else ' — non posée'}", _r(m, 3),
                         f">= {seuil:.2f} [G]", m >= seuil - EPS if retenue else True, "RF-MQ-RAB-02",
                         bloquant=retenue)
                if not retenue:
                    c["marge"] = m
            n_ret = sum(1 for f in self.fleches if f["voie"] == red["voie"])
            n_reg = regles.valeur("RF-MQ-RAB-03")
            self.ctl("rabattement_nombre", "nombre de flèches de rabattement (3 ; 2 en agglomération faute de place)",
                     n_ret, f"{n_reg['nombre']} ou {n_reg['exception_agglomeration']} (agglomération)",
                     n_ret == n_reg["nombre"] or (self.agglo and n_ret == n_reg["exception_agglomeration"]),
                     "RF-MQ-RAB-03")
            if getattr(self, "zebra", None):
                self.ctl("zebra_angle", "hachures : angle à la rive (°)", self.zebra["angle_deg"], 26.565,
                         abs(self.zebra["angle_deg"] - 26.565) < 1e-3, "RF-MQ-HACH-01")
        # flèches directionnelles : 3 par voie, interdistance constante
        dirs = [f for f in self.fleches if f["gabarit"] in ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG")]
        if dirs:
            par_voie = {}
            for f in dirs:
                par_voie.setdefault(f["voie"], []).append(f["s"])
            for vid, ss in sorted(par_voie.items()):
                n_ok = len(ss) == regles.valeur("DEF-017", "nombre_par_voie")
                self.ctl(f"fleches_{vid}_nombre", f"flèches directionnelles voie {vid}", len(ss),
                         regles.valeur("DEF-017", "nombre_par_voie"), n_ok, "RF-MQ-DIR-04")
                ss = sorted(ss)
                inter = sorted({_r(b - a, 3) for a, b in zip(ss, ss[1:])})
                self.ctl(f"fleches_{vid}_interdistance", f"flèches voie {vid} : interdistance (m)", inter,
                         regles.valeur("DEF-017", "interdistance"),
                         inter == [regles.valeur("DEF-017", "interdistance")], "DEF-017")
            ts = {}
            for f in dirs:
                ts.setdefault(_r(f["s"], 3), set()).add(f["voie"])
            n_voies = sum(1 for b in self.bandes if b["type"] in VOIES)
            self.ctl("fleches_meme_profil", "flèches de toutes les voies dans un même profil en travers",
                     sorted(len(v) for v in ts.values()), f"{n_voies} par profil",
                     all(len(v) == n_voies for v in ts.values()), "RF-MQ-DIR-03")
        # arbres : axe à >= 1,50 m du bord de la chaussée, entraxe
        if self.arbres:
            mn = regles.valeur("DEF-030", "axe_depuis_bord_chaussee_min")
            dmin = min(self._dist_chaussee(a) for a in self.arbres)
            self.ctl("arbres_recul", "arbres : distance de l'axe au bord de la voie circulée (m)", _r(dmin, 3),
                     f">= {mn}", dmin >= mn - EPS, "DEF-030")
            ss = sorted({a["s"] for a in self.arbres})
            inter = sorted({_r(b - a, 3) for a, b in zip(ss, ss[1:])})
            self.ctl("arbres_entraxe", "arbres : entraxe (m)", inter, regles.valeur("DEF-030", "entraxe"),
                     inter == [regles.valeur("DEF-030", "entraxe")], "DEF-030")
            dans_trottoir = [a for a in self.arbres if self.par_id[a["bande"]]["type"] == "trottoir"]
            self.ctl("arbres_hors_cheminement", "arbres dans un trottoir (cheminement)", len(dans_trottoir), 0,
                     not dans_trottoir, "DEF-030")
        if self.places:
            lp = sorted({_r(p["longueur"], 3) for p in self.places})
            self.ctl("places_longueur", "places longitudinales : longueur (m)", lp,
                     regles.valeur("DEF-009", "longueur_place"), lp == [regles.valeur("DEF-009", "longueur_place")],
                     "DEF-009")
        if self.figurines:
            ss = sorted({f["s"] for f in self.figurines})
            inter = sorted({_r(b - a, 3) for a, b in zip(ss, ss[1:])})
            self.ctl("figurines_pas", "figurines vélo : pas (m)", inter, regles.valeur("DEF-018"),
                     inter == [regles.valeur("DEF-018")], "DEF-018")
        for ins in self.inscriptions:
            b = self.par_id[ins["voie"]]
            w = self.largeur(b["index"], ins["s"])
            self.ctl("inscription_hauteur", f"inscription {ins['texte']} : hauteur des caractères (m)", ins["hauteur"],
                     ">= 1.50 (V <= 50)", ins["hauteur"] >= 1.5 - EPS and self.vitesse <= 50 + EPS, "RF-MA-CTC-002")
            self.ctl("inscription_largeur", f"inscription {ins['texte']} : tient dans la voie (m)",
                     _r(ins["largeur_totale"], 3), f"< {w:.2f}", ins["largeur_totale"] < w, "RF-MQ-TC-03")
        if self.trace.courbe():
            R = min(self.trace.rayons())
            self.ctl("courbe_epure", "courbe : rayon < 125 m → épure de giration bus à faire (lot L3a)", R, ">= 125",
                     R >= 125, "RF-GV-RAY-012", bloquant=False)
        # attendus de la description = mesures calculées
        self._comparer_attendus()

    def marge_oblique(self, poly) -> float:
        """Marge (m) entre un polygone et le bord droit (côté voie ouverte) de l'oblique de réduction :
        min sur les sommets dont s est dans [s0, PCF] de (t_bord_oblique(s) − t) ; distance au polygone sinon."""
        o = self.oblique
        A, B, w = o["A"], o["B"], o["largeur"]
        n = math.hypot(B[0] - A[0], B[1] - A[1])
        dt = (w / 2) * n / (B[0] - A[0])
        dedans = [(s, t) for s, t in poly if A[0] <= s <= B[0]]
        if not dedans:
            return distance_polygones(poly, o["poly"])
        return min(A[1] + (B[1] - A[1]) * (s - A[0]) / (B[0] - A[0]) - dt - t for s, t in dedans)

    def _dist_chaussee(self, a) -> float:
        """Distance de l'axe d'un arbre au bord le plus proche d'une voie de circulation."""
        d = math.inf
        for b in self.bandes:
            if b["type"] not in VOIES:
                continue
            tg, td = self.t_limite(b["index"], a["s"]), self.t_limite(b["index"] + 1, a["s"])
            if td <= a["t"] <= tg:
                return 0.0
            d = min(d, abs(a["t"] - tg), abs(a["t"] - td))
        return d

    def _comparer_attendus(self):
        att = self.d["attendus"]
        if not isinstance(att, dict):
            raise ErreurDescription("attendus : mapping attendu (une ligne { … })")
        self.ecarts = []
        for k, v in att.items():
            if k not in self.mesures:
                self.ecarts.append((k, v, None))
                continue
            if not _egal(v, self.mesures[k]):
                self.ecarts.append((k, v, self.mesures[k]))
        n = len(att)
        self.ctl("attendus", "attendus de la description = mesures calculées", f"{n - len(self.ecarts)}/{n}",
                 "100 %", not self.ecarts,
                 regle=None if not self.ecarts else "; ".join(f"{k} : décrit {a!r}, calculé {b!r}"
                                                              for k, a, b in self.ecarts))

    # ------------------------------------------------------------------ résumé
    def resume(self) -> dict:
        return {"scene": self.id, "nom": self.nom, "titre": self.titre, "fichier": self.chemin.name,
                "longueur_m": _r(self.L, 3), "agglomeration": self.agglo, "vitesse_kmh": self.vitesse,
                "V15_kmh": self.v15, "u_m": self.u,
                "profil": [{"id": b["id"], "type": b["type"], "sens": b["sens"],
                            "largeur": [[_r(s, 3), _r(w, 3)] for s, w in b["loi"]] if len(b["loi"]) > 1
                            else _r(b["loi"][0][1], 3), "materiau": b["materiau"], "dz": _r(b["dz"], 3)}
                           for b in self.bandes],
                "limites": [{k: v for k, v in l.items() if k in ("id", "nature", "modulation", "k", "profil", "vue",
                                                                  "caniveau", "haut")} for l in self.limites],
                "regles_citees": self.regles_citees, "regles_appliquees": sorted(self.regles_appliquees),
                "mesures": self.mesures, "controles": self.controles, "avertissements": self.avertissements}


def _egal(a, b) -> bool:
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_egal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_egal(x, y) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-3
    return a == b


def scene(chemin) -> Scene:
    return Scene(chemin)
