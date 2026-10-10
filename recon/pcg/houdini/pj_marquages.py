"""pj_marquages : fabrication géométrique des marquages v2 (famille « marquages », schéma
description_scene_v2/0.2), site complet. Aucune géométrie n'est tirée d'un raster : chaque marque est
construite depuis ses paramètres (ou, pour les polygones gardés de la description, depuis leur contour
vectoriel simplifié), puis triangulée par le verbe SOP Triangulate 2D et drapée sur le sol.

    hython recon/pcg/houdini/pj_marquages.py [--sortie DOSSIER] [--verifier-determinisme]
    hython recon/pcg/houdini/fabriquer.py --marquages-seuls [--verifier-determinisme]

Construction (repère local, m) :
- lignes (ML-) : axe = bord de voie OpenDRIVE recalculé (decrire/xodr_echantillonne.py + chaîne de bords de
  marquages_lignes, décalé de t_off) ou axe propre (levé GAM / v1) ; σ = abscisse curviligne ; tirets
  [phase + k (trait + vide), + trait] ∩ [0, L] hors interruptions ; ruban de largeur exacte (décalage
  normal, onglets bornés à 3 x), abouts perpendiculaires à l'axe ; traits continus découpés en tronçons
  ≤ 4 m (coupes hors sommets, normales de coupe prises sur l'axe complet : pas de fente) ;
- transversales (MT-) : mêmes tirets le long de leur axe (T'2 0,15) ;
- zébras (MP-) : bandes rectangulaires largeur_bande x longueur_bande au cap cap_bandes_deg, centrées en
  A + k pas_axe (B − A)/|B − A|, hors coupures ; traversées cyclables : tuiles (gabarit IISR / site ou
  rectangle mesuré) en A + k pas dir, hors absents ;
- flèches et figurines (MF-, MS- velo) : polygones exacts des gabarits de assets/specs/marquages_geometrie.json
  (trous compris, roues de VELO réunies au corps), x echelle, posés (origine, cap) par
  marquages_commun.poser ;
- symboles paramétriques : dent de requin (triangle base x hauteur), chevron (V à trait constant), barre
  (rectangle), point (disque, corde ≤ 1 mm) ; PMR, « 30 » / « 50 » et T de stationnement : glyphes reconstruits par
  primitives depuis leurs paramètres (decrire/marquages_glyphes) ; figurine VELO : D1 reconstruite par primitives ;
- zones : hachures (bandes de largeur bande_m au pas pas_m, coupées par le contour convexe, contour peint
  3u et espace non peint 2u si contour_peint), zigzag (base, amplitude à l'axe du trait, n périodes = longueur
  / période, traits d'extrémité perpendiculaires), primitives des polygones v1 (rectangle, ruban, gabarit, contour
  redressé) et fantômes (une entité par groupe d'empreintes qui se recouvrent : réunion à la triangulation) ;
- triangulation : Triangulate 2D (contraintes : contours fermés, extérieur trigonométrique, trous
  horaires, réunion des recouvrements ; plus les arêtes des triangles du sol, des bandes de tête de bordure v2 et
  des marques prioritaires, en polylignes ouvertes) : chaque triangle de marque tombe dans UN triangle du sol ;
  fusion des arêtes < 3 mm sans jamais déplacer un sommet du contour ni rogner un coin de gabarit ;
- coupes (au lieu d'un empilement) : découpes décrites (decoupes : dégagement de 2u des bordures, marque voisine) ; une
  marque n'est pas peinte sous la tête d'une bordure v2 (de l'arête avant à la base du profil), ni à moins de 1 cm d'une
  face verticale v1 de plus de 2 cm (filet de sécurité), ni sous une marque d'une entité prioritaire (fantôme < zone <
  passage < ligne < flèche / symbole, puis id ; filet de sécurité signalé en avertissement) ; ni sur un sol de pente > 30 % ; une marque à cheval sur une marche du sol v1 (même arête plane, altitudes
  différentes) ne garde que les régions qui ne déchirent pas une région mieux classée (chaussée, puis aire) ; les
  composantes hors chaussée d'une pièce qui touche la chaussée et les éclats de coupe < min(0,10 m, 0,75 x largeur) sont
  retirés ;
- drapé : z de chaque coin = plan du triangle de sol sous le triangle de marque (sol v2 fabrique/sol.usda
  dans l'emprise pilote, sinon sol v1 composé paquet + contexte/masque_v1_pilote.usdc, voirie et terrain hors
  bâtiments) + dz : marques 3 mm, surface colorée 2,5 mm, fantômes 2 mm ; sommets de même (x, y) à moins de 2 mm
  soudés ;
- primvars : st1 (x, y en m, masques d'usure), couleur, usure, couverture, seuil_usure, type, id, support,
  manque_roues (par sommet : traces de roues de toutes les marques d'usure 1 à 3), axe_marque (par sommet : axe principal de
  la pièce, plaques de faïençage), dist_bordure (par sommet : distance à la bordure, salissure du caniveau),
  karma:object:rendervisibility ;
  un maillage par classe /World/PJ_Marquages/<couleur>_u<usure>, matériau peinture_<couleur>_u<usure>
  (pj_marquages_materiaux : MaterialX Karma + UsdPreviewSurface + MI Unreal).
Sorties (fabrique/) : marquages.usda (site), marquages_pilote.usda (triangles posés sur le sol v2 : remplace
les zébras provisoires de pj_decals dans rendu_pilote.usda), marquages_prototypes.usda (gabarits à plat pour
décalques / maillages UE), points/marquages_symboles.json (pj_points/0.1), marquages_manifest.json
(entrées, comptes, contrôles, hashes).
Contrôles bloquants (manifeste controles.bloquants, code de sortie 2 de l'exécution seule) : franchissement (arête de pente
> 30 % et de dénivelé > 2 cm), bord de marque qui coupe une face v1 > 2 cm ou une arête avant v2 hors abaissés franchissables,
flèche ou gabarit coupé de plus de 1 % de son aire, point enfoui, recouvrement au même dz, MQ « genere » / « garde_simplifie »
sans triangle ou « garde_non_fabrique » fabriqué. Les entités décrites fabrication.statut = non_fabrique ne sont pas fabriquées.
Déterminisme : entités triées par id, pièces numérotées, soudure des sommets au 1/100 mm, aucun aléa.
"""
import argparse
import collections
import hashlib
import json
import math
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.dont_write_bytecode = True

import hou                                                     # noqa: E402
import numpy as np                                             # noqa: E402
from pxr import Sdf, Usd, UsdGeom, Vt                          # noqa: E402

import pj_commun as K                                          # noqa: E402
import pj_marquages_materiaux as MM                            # noqa: E402
import pj_usd as U                                             # noqa: E402

C = K.C
import marquages_commun as MC                                  # noqa: E402  (decrire/, chemin posé par pj_commun)
import marquages_lignes as LG                                  # noqa: E402
import marquages_symboles as SY                                # noqa: E402
import xodr_echantillonne as X                                 # noqa: E402

T = Sdf.ValueTypeNames
CAT = hou.sopNodeTypeCategory()
VERSION = "pj_marquages/0.2"
DZ = {"marque": 0.003, "surface_coloree": 0.0025, "fantome": 0.002}
PRIORITE = {"fantome": 0, "zone": 1, "passage": 2, "ligne": 3, "transversale": 3, "fleche": 4, "symbole": 4}
TRONCON_MAX = 4.0           # longueur maximale d'une pièce de trait continu (m)
TOL_PLAN = 0.0005           # Douglas-Peucker des axes avant ruban (m)
ONGLET_MAX = 3.0            # facteur d'onglet maximal des rubans
EPS_AIRE = 1e-7             # triangles plus petits retirés (m²)
SOUDURE = 1e-5              # soudure des sommets (m)
FRAGMENT_MIN = 0.05        # morceau de bande de hachure plus petit écarté (m²) ; IISR : aplat sous 0,30 m de large
PENTE_MAX = 0.12           # pente maximale du plan de pose d'un symbole (points/marquages_symboles.json)
COURTE = 0.003              # arêtes plus courtes fusionnées (points de coupe par le sol ; contour de la marque fixe)
SEUIL_DECHIRURE = 0.002     # sommets de même (x, y) : soudés en dessous, déchirure au-dessus (m)
ECLAT_MAX = 0.10            # éclat de coupe plus étroit retiré (m)
PENTE_SOL_MAX = 0.30        # sol plus pentu (face ou chanfrein de bordure, marche, talus) : pas de marque ; rampes de plateau
                            # (≤ 15 %) gardées
FRANCHISSEMENT = (0.30, 0.02)   # arête de marque de pente > 30 % et de dénivelé > 2 cm : franchissement (contrôle bloquant)
SECURITE_FACE = 0.01        # bande de sécurité autour des faces verticales v1 (> 2 cm) : marque coupée (le dégagement de 2u est
                            # décrit par la description, decoupes / interruptions_bordures)
FACE_MIN = 0.02             # face verticale v1 plus haute : bordure (franchissement interdit)
COUPE_FLECHE_MAX = 0.01     # part d'aire coupée au-delà de laquelle une flèche / un gabarit est refusé (contrôle bloquant)
U_VERDUN, U_DEFAUT = LG.U_VERDUN, LG.U_DEFAUT
PEINTURE = K.SPECS / "peinture.json"
SPEC = MC.SPEC
SOL_V2 = "sol.usda"
MASQUE_V1 = "contexte/masque_v1_pilote.usdc"
V1_RACINE = K.PAQUET_V1 / "paquet_jardin_2026.usda"
V1_EXCLUS = ("batiment", "jupe_emprise")
CHAUSSEE_V1 = ("chaussee", "parking", "piste_cyclable", "acces_riverain", "quai_bus")
CHAUSSEE_V2 = ("enrobe_bbsg_ancien", "enrobe_bbsg_neuf_2025", "enrobe_reprise_tranchee", "enrobe_piste_cyclable",
               "enrobe_colore_ocre", "resine_verte", "resine_cyan", "enrobe_clair_granulats")


def journal(*a):
    print(*a, flush=True)


# =========================================================================== géométrie plane
def aire(r):
    r = np.asarray(r, float)
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def orienter(poly):
    """Polygone [extérieur, trous...] : extérieur trigonométrique, trous horaires, sans sommet doublé."""
    out = []
    for k, r in enumerate(poly):
        r = MC.dedoublonner(np.asarray(r, float)[:, :2])
        if len(r) > 1 and np.hypot(*(r[0] - r[-1])) < 1e-6:
            r = r[:-1]
        if len(r) < 3:
            continue
        a = aire(r)
        if (k == 0 and a < 0) or (k > 0 and a > 0):
            r = r[::-1]
        out.append(r)
    return out


def aires_tri(P, F):
    """Aires planes (xy) des triangles F de P."""
    a, b, c = P[F[:, 0], :2], P[F[:, 1], :2], P[F[:, 2], :2]
    return 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0]))


def tangente_a(P, s):
    _, tg = C.point_a(P, s)
    return tg[0]


def ruban(Q, w, t0=None, t1=None):
    """Contour (trigonométrique) d'un ruban de largeur w centré sur la polyligne Q ; t0 / t1 : tangentes
    imposées aux extrémités (abouts perpendiculaires à l'axe complet)."""
    Q = MC.dedoublonner(np.asarray(Q, float))
    if len(Q) > 2:
        Q = MC.douglas_peucker(Q, TOL_PLAN)
    d = np.diff(Q, axis=0)
    t = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    ns = np.c_[-t[:, 1], t[:, 0]]
    nv = np.zeros((len(Q), 2))
    fac = np.ones(len(Q))
    nv[0] = ns[0] if t0 is None else np.array([-t0[1], t0[0]])
    nv[-1] = ns[-1] if t1 is None else np.array([-t1[1], t1[0]])
    if len(Q) > 2:
        b = ns[:-1] + ns[1:]
        b /= np.maximum(np.hypot(b[:, 0], b[:, 1]), 1e-12)[:, None]
        c = np.einsum("ij,ij->i", b, ns[1:])
        nv[1:-1] = b
        fac[1:-1] = 1.0 / np.maximum(c, 1.0 / ONGLET_MAX)
    off = nv * (0.5 * w * fac)[:, None]
    return np.vstack([Q - off, (Q + off)[::-1]])


def trait(Q, w, t0=None, t1=None, coude_max=100.0):
    """Polygones d'un trait de largeur w le long de Q : un ruban par tronçon entre coudes vifs (virage
    > coude_max : aller-retour d'un levé, trait d'extrémité de zigzag), réunis par Triangulate 2D, avec un
    biseau de chaque côté du coude (pas de pointe d'onglet ni de contour auto-sécant)."""
    Q = MC.dedoublonner(np.asarray(Q, float))
    if len(Q) > 2:
        Q = MC.douglas_peucker(Q, TOL_PLAN)
    if len(Q) < 3:
        return [[ruban(Q, w, t0, t1)]]
    d = np.diff(Q, axis=0)
    t = d / np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)[:, None]
    cosv = np.einsum("ij,ij->i", t[:-1], t[1:])
    coupes = [i + 1 for i in np.where(cosv < math.cos(math.radians(coude_max)))[0]]
    if not coupes:
        return [[ruban(Q, w, t0, t1)]]
    bornes = [0] + coupes + [len(Q) - 1]
    out = []
    for k, (i, j) in enumerate(zip(bornes[:-1], bornes[1:])):
        out.append([ruban(Q[i:j + 1], w, t0 if k == 0 else None, t1 if j == len(Q) - 1 else None)])
    h = 0.5 * w
    for i in coupes:
        na = np.array([-t[i - 1, 1], t[i - 1, 0]])
        nb = np.array([-t[i, 1], t[i, 0]])
        for s in (1.0, -1.0):
            tri = np.array([Q[i], Q[i] + s * na * h, Q[i] + s * nb * h])
            if abs(aire(tri)) > 1e-8:
                out.append([tri])
    return out


def rectangle(c, u, L, W):
    """Rectangle centré en c, grand côté L selon u, largeur W (trigonométrique)."""
    u = np.asarray(u, float) / np.hypot(*u)
    v = np.array([-u[1], u[0]])
    return np.array([c - u * L / 2 - v * W / 2, c + u * L / 2 - v * W / 2, c + u * L / 2 + v * W / 2,
                     c - u * L / 2 + v * W / 2])


def dir_cap(cap_deg):
    h = math.radians(cap_deg)
    return np.array([math.cos(h), math.sin(h)])


def decaler_convexe(r, d):
    """Polygone convexe trigonométrique rétréci de d : intersection des demi-plans des côtés décalés vers
    l'intérieur (robuste aux petits côtés et aux pointes aiguës) ; None si vide."""
    r = np.asarray(r, float)
    out = r.copy()
    for i in range(len(r)):
        a, b = r[i], r[(i + 1) % len(r)]
        t = (b - a) / max(float(np.hypot(*(b - a))), 1e-12)
        n = np.array([-t[1], t[0]])
        out = couper_demi_plan(out, a + n * d, t)
        if out is None:
            return None
    return out


def couper_demi_plan(poly, a, t):
    """Partie de `poly` à gauche de la droite (a, t)."""
    if poly is None or len(poly) < 3:
        return None
    gauche = lambda p: t[0] * (p[1] - a[1]) - t[1] * (p[0] - a[0]) >= -1e-12
    out = []
    for j in range(len(poly)):
        p, q = poly[j - 1], poly[j]
        ip, iq = gauche(p), gauche(q)
        if iq:
            if not ip:
                out.append(_inter(p, q, a, a + t))
            out.append(q)
        elif ip:
            out.append(_inter(p, q, a, a + t))
    return np.array(out) if len(out) >= 3 else None


def couper_convexe(sujet, clip):
    """Sutherland-Hodgman : polygone `sujet` coupé par le polygone convexe trigonométrique `clip`."""
    out = [np.asarray(p, float) for p in sujet]
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        e = b - a
        entree, out = out, []
        if not entree:
            break
        dedans = lambda p: e[0] * (p[1] - a[1]) - e[1] * (p[0] - a[0]) >= -1e-12
        for j in range(len(entree)):
            p, q = entree[j - 1], entree[j]
            ip, iq = dedans(p), dedans(q)
            if iq:
                if not ip:
                    out.append(_inter(p, q, a, b))
                out.append(q)
            elif ip:
                out.append(_inter(p, q, a, b))
    return np.array(out) if len(out) >= 3 else None


def _inter(p, q, a, b):
    r, s = q - p, b - a
    den = r[0] * s[1] - r[1] * s[0]
    t = ((a - p)[0] * s[1] - (a - p)[1] * s[0]) / den if abs(den) > 1e-15 else 0.0
    return p + r * t


def disque(c, d, corde=0.001):
    r = d / 2
    n = max(16, int(math.ceil(math.pi / math.acos(max(-1.0, 1.0 - corde / r)))))
    a = 2 * math.pi * np.arange(n) / n
    return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


# =========================================================================== description -> pièces
def asset_glyphe(prm):
    """Nom de prototype d'un glyphe : PMR_h<mm>[_m], TEXTE_<texte>_<L mm>x<W mm>, T_STAT_<barre>x<jambe>_t<trait> (mm)."""
    mm = lambda v: int(round(float(v) * 1000))
    if prm["nom"] == "pmr":
        return f"PMR_h{mm(prm['hauteur_m']):04d}" + ("_m" if prm.get("miroir") else "")
    if prm["nom"] == "texte_ellipse":
        return f"TEXTE_{prm['texte']}_{mm(prm['longueur_m']):04d}x{mm(prm['largeur_m']):04d}"
    return f"T_STAT_{mm(prm['barre_m']):04d}x{mm(prm['jambe_m']):04d}_t{mm(prm['trait_m']):03d}"


def u_de(p):
    return U_VERDUN if p.get("branche") in LG.BRANCHES_VERDUN else U_DEFAUT


def intervalles(p, L):
    """Parties peintes (σ0, σ1) d'une ligne (marquages_controles._pieces) sur une longueur L."""
    if p.get("type") == "discontinue" or (p.get("classe") == "transversale" and p.get("trait_m")):
        T_, V, ph = p["trait_m"], p["vide_m"], p["phase_m"]
        per = T_ + V
        k0 = math.floor(-ph / per) - 1
        iv = [(ph + k * per, ph + k * per + T_) for k in range(k0, int((L - ph) / per) + 2)]
    else:
        iv = [(0.0, L)]
    iv = [(max(0.0, a), min(L, b)) for a, b in iv if b > 0 and a < L]
    for a0, b0 in p.get("interruptions", []):
        out = []
        for a, b in iv:
            if b <= a0 or a >= b0:
                out.append((a, b))
            else:
                if a < a0:
                    out.append((a, a0))
                if b > b0:
                    out.append((b0, b))
        iv = out
    return [(a, b) for a, b in iv if b - a > 1e-3]


def troncons(P, a, b):
    """Coupe [a, b] en tronçons ≤ TRONCON_MAX, coupes écartées des sommets de P (≥ 2 cm)."""
    n = max(1, int(math.ceil((b - a) / TRONCON_MAX - 1e-9)))
    if n == 1:
        return [(a, b)]
    S = C.abscisses(P)
    cuts = []
    for k in range(1, n):
        c = a + (b - a) * k / n
        j = int(np.argmin(np.abs(S - c)))
        if abs(S[j] - c) < 0.02:
            c = S[j] + (0.02 if S[j] >= c else -0.02)
        cuts.append(c)
    bornes = [a] + cuts + [b]
    return list(zip(bornes[:-1], bornes[1:]))


class Pieces:
    """Pièces planes (polygones) de chaque entité ; une pièce = une triangulation."""

    def __init__(self, dossier_description, log=journal):
        self.log = log
        self.dossier = Path(dossier_description)
        self.manifeste = K.lire_json(self.dossier / "description_scene_v2.json")
        self.fichier = self.dossier / "base/marquages.geojson"
        self.features = sorted(C.lire_geojson(self.fichier), key=lambda f: f["properties"]["id"])
        self.hash = self.manifeste.get("hash_marquages") or C.sha256(self.fichier)
        self.spec = MC.spec()
        self.reseau = X.lire_xodr()
        self.chaines = {}
        for ch in LG.chaines_reseau(self.reseau):
            for b in ch.bords:
                self.chaines[(ch.route, round(b.section_s, 3), b.voie)] = ch
        self.pieces = []
        self.glyphes = {}           # prototypes des glyphes (asset -> paramètres)
        self.symboles = []          # poses pour points/marquages_symboles.json
        self.non_fabriques = []
        self.axes = {}              # axe local des lignes (contrôles)
        self.attendu = {}           # aires et nombres attendus (contrôles)
        for f in self.features:
            self._entite(f)
        self.log(f"   {len(self.features)} entités -> {len(self.pieces)} pièces, {len(self.symboles)} poses de symboles")

    # ------------------------------------------------------------------ outils
    def _base(self, p):
        return {"entite": p["id"], "classe": p["classe"], "type": p["type"], "couleur": p["couleur"],
                "usure": str(p["usure"]), "couverture": float(p["couverture"]),
                "dz": DZ["fantome"] if p["classe"] == "fantome" else
                DZ["surface_coloree"] if p["type"] == "surface_coloree" else DZ["marque"]}

    def _ajouter(self, p, polys, sous_type=None):
        polys = [orienter(pp) for pp in polys]
        polys = [pp for pp in polys if pp]
        if not polys:
            return
        d = self._base(p)
        d["sous_type"] = sous_type or p["type"]
        d["polys"] = polys
        d["id"] = f"{p['id']}/{self._compteur(p['id']):03d}"
        d["decoupes"] = [orienter([self._local(np.asarray(c["polygone_l93"], float))]) for c in p.get("decoupes", [])]
        d["decoupes"] = [c for c in d["decoupes"] if c]
        self.pieces.append(d)

    def _compteur(self, eid):
        self._n = getattr(self, "_n", {})
        self._n[eid] = self._n.get(eid, -1) + 1
        return self._n[eid]

    @staticmethod
    def _local(coords):
        return C.repere(np.asarray(coords, float)[..., :2])

    def _pose(self, p):
        o = self._local(np.asarray(p["pose"]["point_l93"], float)[None])[0]
        return o, float(p["pose"]["cap_deg"])

    def _symbole(self, p, asset, o, cap, s, x=None):
        self.symboles.append({"entite": p["id"], "asset": asset, "o": o, "cap": cap, "s": s, "couleur": p["couleur"],
                              "usure": str(p["usure"]), "couverture": float(p["couverture"]), "classe": p["classe"],
                              "type": p["type"], "x": x or {}})

    # ------------------------------------------------------------------ entités
    def _entite(self, f):
        p = f["properties"]
        cl, ty = p["classe"], p["type"]
        g = f["geometry"]
        if (p.get("fabrication") or {}).get("statut") == "non_fabrique":
            self.non_fabriques.append({"id": p["id"], "raison": "description : " + p["fabrication"]["raison"], "decrit_non_fabrique": True})
            return
        if cl in ("ligne", "transversale"):
            self._ligne(p, g)
        elif cl == "passage" and ty == "zebra":
            self._zebra(p, g)
        elif cl == "passage" and ty == "traversee_cyclable":
            self._traversee(p)
        elif cl == "fleche" or (cl == "symbole" and ty == "velo"):
            self._gabarit(p)
        elif cl == "symbole":
            self._symbole_param(p, g)
        elif cl == "zone" and ty == "hachures":
            self._hachures(p, g)
        elif cl == "zone" and ty == "zigzag":
            self._zigzag(p, g)
        elif cl == "zone" and ty == "t_stationnement":
            self._glyphe(p)
        elif cl in ("zone", "fantome"):
            self._polygone(p, g)
        else:
            self.non_fabriques.append({"id": p["id"], "raison": f"classe {cl} / type {ty} inconnus"})

    def axe_ligne(self, p, g):
        anc = p.get("ancrage") or {}
        P_desc = self._local(g["coordinates"])
        if anc.get("type") == "xodr" and anc.get("bords"):
            b0 = anc["bords"][0]
            ch = self.chaines.get((anc["route"], round(float(b0["section_s"]), 3), int(b0["voie"])))
            if ch is None:
                raise KeyError(f"{p['id']} : chaîne de bords {anc['route']}/{b0['section_s']}/{b0['voie']} introuvable")
            P = ch.axe(float(anc["t_off_m"]), float(anc["s0"]), float(anc["s1"]), profil=anc.get("t_off_profil"))
            return P, P_desc, "xodr"
        return P_desc, P_desc, "geometrie"

    def _ligne(self, p, g):
        P, P_desc, src = self.axe_ligne(p, g)
        L_desc = float(C.abscisses(P_desc)[-1])
        L = float(C.abscisses(P)[-1])
        k = L / max(L_desc, 1e-9)
        self.axes[p["id"]] = (P, src)
        w = float(p["largeur_m"])
        iv = intervalles(p, L_desc)
        n_tirets = n_complets = 0
        for a, b in iv:
            a, b = a * k, b * k
            if p.get("type") == "discontinue" or p["classe"] == "transversale":
                parts = [(a, b)]
                n_tirets += 1
                n_complets += int(b - a >= float(p["trait_m"]) - 1e-3)
            else:
                parts = troncons(P, a, b)
            for a2, b2 in parts:
                Q = C.sous_polyligne(P, a2, b2)
                if len(Q) < 2:
                    continue
                self._ajouter(p, trait(Q, w, tangente_a(P, a2), tangente_a(P, b2)),
                              sous_type=f"{p['classe']}_{p['type']}")
        self.attendu[p["id"]] = {"aire": w * sum((b - a) * k for a, b in iv), "n_tirets": n_tirets,
                                 "n_complets": n_complets, "n_tirets_decrits": p.get("n_tirets"),
                                 "ecart_longueur_axe_m": abs(L - L_desc)}

    def _zebra(self, p, g):
        A, B = self._local(g["coordinates"])[:2]
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        u = dir_cap(p["cap_bandes_deg"])
        nb = int(p.get("nb_emplacements") or p["nb_bandes"])
        n = 0
        for k in range(nb):
            if k in p.get("coupures", []):
                continue
            c = A + ax * k * float(p["pas_axe_m"])
            self._ajouter(p, [[rectangle(c, u, float(p["longueur_bande_m"]), float(p["largeur_bande_m"]))]], "zebra_bande")
            n += 1
        self.attendu[p["id"]] = {"aire": n * float(p["longueur_bande_m"]) * float(p["largeur_bande_m"]), "n_bandes": n}

    def _traversee(self, p):
        aire_t, n = 0.0, 0
        for fi, fl in enumerate(p["files"]):
            ax = self._local(fl["axe_l93"])
            A = ax[0]
            d = dir_cap(fl["cap_deg"])
            pas = float(fl["pas_m"])
            nk = int(round(float(np.hypot(*(ax[-1] - A))) / pas)) + 1 if pas > 0 and len(ax) > 1 else 1
            if "gabarit" in fl:
                polys = MC.gabarit(fl["gabarit"])
                a_t = float(self.spec["gabarits"][fl["gabarit"]]["aire_m2"])
                asset, s = fl["gabarit"], [1.0, 1.0, 1.0]
            else:
                tx, ty = float(fl["tuile_m"]["perp_file"]), float(fl["tuile_m"]["le_long_file"])
                polys = [[np.array([[-tx / 2, -ty / 2], [tx / 2, -ty / 2], [tx / 2, ty / 2], [-tx / 2, ty / 2]])]]
                a_t = tx * ty
                asset, s = "RECT_UNITE", [tx, ty, 1.0]
            for k in range(nk):
                if k in fl.get("absents", []):
                    continue
                c = A + d * pas * k
                posees = [[MC.poser(r, c, fl["cap_deg"]) for r in poly] for poly in polys]
                self._ajouter(dict(p, couleur=fl.get("couleur", p["couleur"])), posees, "traversee_tuile")
                self._symbole(dict(p, couleur=fl.get("couleur", p["couleur"])), asset, c, float(fl["cap_deg"]), s,
                              {"file": fi, "rang": k})
                aire_t += a_t
                n += 1
        self.attendu[p["id"]] = {"aire": aire_t, "n_tuiles": n, "n_tuiles_decrites": p.get("nb_tuiles")}

    def _gabarit(self, p):
        o, cap = self._pose(p)
        e = float(p.get("echelle", 1.0))
        nom = p["gabarit"]
        polys = MC.gabarit(nom)
        posees = [[MC.poser(r, o, cap, e) for r in poly] for poly in polys]
        self._ajouter(p, posees, f"{p['classe']}_{nom}")
        self._symbole(p, nom, o, cap, [e, e, 1.0], {"gabarit": nom})
        aire_g = float(self.spec["gabarits"][nom]["aire_m2"]) if nom != "VELO" else \
            float(self.spec["gabarits"]["VELO"]["parties"]["aire_totale_m2"])
        self.attendu[p["id"]] = {"aire": aire_g * e * e, "gabarit": nom, "echelle": e, "origine": o, "cap": cap}

    def _glyphe(self, p):
        """PMR, « 30 » / « 50 », T de stationnement : polygones reconstruits depuis les paramètres du glyphe
        (decrire/marquages_glyphes via marquages_symboles.construire_glyphe), posés (origine, cap)."""
        o, cap = self._pose(p)
        prm = p["glyphe"]
        polys = [[MC.poser(r, o, cap) for r in poly] for poly in SY.construire_glyphe(prm)]
        self._ajouter(p, polys, f"{p['classe']}_{p['type']}")
        asset = asset_glyphe(prm)
        self.glyphes[asset] = prm
        self._symbole(p, asset, o, cap, [1.0, 1.0, 1.0], {"glyphe": prm})
        self.attendu[p["id"]] = {"aire": None}

    def _symbole_param(self, p, g):
        ty = p["type"]
        if ty in ("pmr", "texte"):
            self._glyphe(p)
            return
        if ty == "a_vectoriser":
            o, cap = self._pose(p)
            bx = p["boite"]
            self._symbole(p, f"A_VECTORISER_{p.get('nature', 'inconnu').upper()}", o, cap,
                          [float(bx["largeur_m"]), float(bx["longueur_m"]), 1.0], {"statut": "a_vectoriser"})
            self.non_fabriques.append({"id": p["id"], "raison": f"{p.get('nature')} : gabarit à vectoriser (boîte "
                                                               f"{bx['longueur_m']} x {bx['largeur_m']} m, points seulement)"})
            return
        o, cap = self._pose(p)
        d = dir_cap(cap)
        ex = np.array([d[1], -d[0]])                                   # x du gabarit (droite)
        if ty == "dent_requin":
            b, h = float(p["triangle"]["base_m"]), float(p["triangle"]["hauteur_m"])
            poly = np.array([o - ex * b / 2, o + ex * b / 2, o + d * h])
            self._symbole(p, "TRIANGLE_UNITE", o, cap, [b, h, 1.0])
            a_ = 0.5 * b * h
        elif ty == "chevron":
            c = p["chevron"]
            lb, ouv, tr = float(c["branche_m"]), math.radians(float(c["ouverture_deg"])), float(c["trait_m"])
            u1 = MC.poser(np.array([[math.sin(ouv / 2), -math.cos(ouv / 2)]]), np.zeros(2), cap)[0]
            u2 = MC.poser(np.array([[-math.sin(ouv / 2), -math.cos(ouv / 2)]]), np.zeros(2), cap)[0]
            n1 = MC.poser(np.array([[-math.cos(ouv / 2), -math.sin(ouv / 2)]]), np.zeros(2), cap)[0]
            n2 = MC.poser(np.array([[math.cos(ouv / 2), -math.sin(ouv / 2)]]), np.zeros(2), cap)[0]
            e1, e2 = o + u1 * lb, o + u2 * lb
            ic = o - d * (tr / math.sin(ouv / 2))
            poly = np.array([o, e2, e2 + n2 * tr, ic, e1 + n1 * tr, e1])
            asset = f"CHEVRON_b{round(lb * 1000):04d}_o{round(math.degrees(ouv) * 10):04d}_t{round(tr * 1000):03d}"
            self._symbole(p, asset, o, cap, [1.0, 1.0, 1.0], {"chevron": c})
            a_ = abs(aire(poly))
        elif ty == "barre":
            L, W = float(p["rectangle"]["longueur_m"]), float(p["rectangle"]["largeur_m"])
            poly = rectangle(o, d, L, W)
            self._symbole(p, "RECT_UNITE", o, cap, [W, L, 1.0])
            a_ = L * W
        elif ty == "point":
            dm = float(p["disque"]["diametre_m"])
            poly = disque(o, dm)
            self._symbole(p, "DISQUE_UNITE", o, cap, [dm, dm, 1.0])
            a_ = abs(aire(poly))
        else:
            self.non_fabriques.append({"id": p["id"], "raison": f"symbole {ty} inconnu"})
            return
        self._ajouter(p, [[poly]], f"symbole_{ty}")
        self.attendu[p["id"]] = {"aire": a_}

    def _hachures(self, p, g):
        zone = orienter([self._local(g["coordinates"][0])])[0]
        u = dir_cap(p["cap_bandes_deg"])
        n = np.array([-u[1], u[0]])
        o = self._local(np.asarray(p["origine_bandes_l93"], float)[None])[0]
        pas, bande = float(p["pas_m"]), float(p["bande_m"])
        polys = []
        interieur = zone
        if p.get("contour_peint"):
            wc = float(p.get("contour_largeur_m") or 3 * u_de(p))
            interieur = decaler_convexe(zone, wc)
            polys.append([zone, interieur[::-1]] if interieur is not None else [zone])
            interieur = decaler_convexe(zone, wc + 2 * u_de(p))
        if interieur is None:
            interieur = np.zeros((0, 2))
        t = (zone - o) @ n
        L = float(np.ptp(zone @ u)) + 2.0
        cu = float((zone @ u).mean())
        for k in range(int(math.floor((t.min() - bande) / pas)), int(math.ceil((t.max() + bande) / pas)) + 1):
            c = o + n * (k * pas)
            c = c + u * (cu - c @ u)
            r = couper_convexe(rectangle(c, u, L, bande), interieur) if len(interieur) >= 3 else None
            if r is not None and abs(aire(r)) > FRAGMENT_MIN:
                polys.append([r])
        for poly in polys:
            self._ajouter(p, [poly], "zone_hachures")
        self.attendu[p["id"]] = {"aire": sum(abs(aire(pp[0])) - sum(abs(aire(h)) for h in pp[1:]) for pp in polys)}

    def _zigzag(self, p, g):
        A, B = self._local(g["coordinates"])[:2]
        L = float(np.hypot(*(B - A)))
        u = (B - A) / L
        n = np.array([-u[1], u[0]]) * (1 if int(p["cote"]) > 0 else -1)
        npér = max(1, int(round(L / float(p["periode_m"]))))
        P_ = L / npér
        amp = float(p["amplitude_m"])
        pts = [A]
        for k in range(npér + 1):
            pts.append(A + u * (k * P_) + n * amp)
            if k < npér:
                pts.append(A + u * ((k + 0.5) * P_))
        pts.append(B)
        Q = np.array(pts)
        self._ajouter(p, trait(Q, float(p["trait_m"])), "zone_zigzag")
        self.attendu[p["id"]] = {"aire": float(p["trait_m"]) * float(C.abscisses(Q)[-1]), "periode_m": P_, "n_periodes": npér}

    def _polygone(self, p, g):
        polys = [[self._local(r) for r in poly] for poly in C.anneaux(g)]
        for poly in polys:
            self._ajouter(p, [poly], f"{p['classe']}_{p['type']}")
        self.attendu[p["id"]] = {"aire": sum(abs(aire(pp[0])) - sum(abs(aire(h)) for h in pp[1:]) for pp in polys)}


# =========================================================================== sol (support du drapé)
class Sol:
    """Triangles du sol : v2 (fabrique/sol.usda, emprise pilote) prioritaires, puis v1 composé (paquet v1 +
    masque_v1_pilote : faces de l'emprise dégénérées, raccords recréés)."""

    def __init__(self, fabrique, log=journal, cellule=1.0):
        self.log = log
        tris, src, cl = [], [], []
        self.classes = []
        v2 = Usd.Stage.Open(str(Path(fabrique) / SOL_V2))
        for prim in sorted(v2.Traverse(), key=lambda q: str(q.GetPath())):
            if prim.IsA(UsdGeom.Mesh):
                self._mesh(prim, 0, prim.GetName(), tris, src, cl)
        lay = Sdf.Layer.CreateAnonymous(".usda")
        lay.subLayerPaths.append(str((Path(fabrique) / MASQUE_V1).resolve().as_posix()))
        lay.subLayerPaths.append(str(V1_RACINE.resolve().as_posix()))
        v1 = Usd.Stage.Open(lay)
        for racine in ("/World/Voirie", "/World/Terrain"):
            r = v1.GetPrimAtPath(racine)
            for prim in sorted(r.GetChildren(), key=lambda q: str(q.GetPath())):
                nom = prim.GetName()
                if not prim.IsA(UsdGeom.Mesh) or any(nom.startswith(x) for x in V1_EXCLUS):
                    continue
                base = nom.replace("_raccord_pilote", "")
                self._mesh(prim, 1, base, tris, src, cl)
        self.T = np.vstack(tris)
        self.src = np.concatenate(src).astype(np.int8)
        self.cl = np.concatenate(cl).astype(np.int32)
        ab = self.T[:, 1, :2] - self.T[:, 0, :2]
        ac = self.T[:, 2, :2] - self.T[:, 0, :2]
        cr = ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]
        ok = np.abs(cr) > 1e-9
        self.T, self.src, self.cl = self.T[ok], self.src[ok], self.cl[ok]
        self.c = cellule
        lo = self.T[:, :, :2].min(axis=1)
        hi = self.T[:, :, :2].max(axis=1)
        self.o = np.floor(lo.min(axis=0)) - 1.0
        i0 = np.floor((lo - self.o) / cellule).astype(np.int64)
        i1 = np.floor((hi - self.o) / cellule).astype(np.int64)
        self.ny = int(i1[:, 1].max()) + 2
        nx, ny = i1[:, 0] - i0[:, 0] + 1, i1[:, 1] - i0[:, 1] + 1
        cnt = nx * ny
        tri = np.repeat(np.arange(len(self.T)), cnt)
        off = np.arange(int(cnt.sum())) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        ix = np.repeat(i0[:, 0], cnt) + off // np.repeat(ny, cnt)
        iy = np.repeat(i0[:, 1], cnt) + off % np.repeat(ny, cnt)
        cle = ix * self.ny + iy
        o = np.argsort(cle, kind="stable")
        self.cles, self.tri_cle = cle[o], tri[o]
        nrm = np.cross(self.T[:, 1] - self.T[:, 0], self.T[:, 2] - self.T[:, 0])
        self.pente = np.hypot(nrm[:, 0], nrm[:, 1]) / np.maximum(np.abs(nrm[:, 2]), 1e-12)
        self.chaussee = np.array([(nom.startswith(CHAUSSEE_V1) if src_ == "v1" else nom in CHAUSSEE_V2)
                                  for src_, nom in (c.split(":", 1) for c in self.classes)], bool)
        self.log(f"   sol : {int((self.src == 0).sum())} triangles v2, {int((self.src == 1).sum())} triangles v1 ; "
                 f"{len(self.classes)} classes")

    def _mesh(self, prim, s, nom, tris, src, cl):
        m = UsdGeom.Mesh(prim)
        P = np.asarray(m.GetPointsAttr().Get(), dtype=np.float64)
        cnt = np.asarray(m.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
        idx = np.asarray(m.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
        if len(cnt) == 0:
            return
        deb = np.r_[0, np.cumsum(cnt)[:-1]]
        out = []
        for k in range(1, int(cnt.max()) - 1):                    # éventail
            sel = cnt > k + 1
            out.append(np.c_[idx[deb[sel]], idx[deb[sel] + k], idx[deb[sel] + k + 1]])
        F = np.vstack(out)
        cle = f"{'v2' if s == 0 else 'v1'}:{nom}"
        if cle not in self.classes:
            self.classes.append(cle)
        tris.append(P[F])
        src.append(np.full(len(F), s))
        cl.append(np.full(len(F), self.classes.index(cle)))

    def candidats(self, lo, hi):
        i0 = np.maximum(np.floor((np.asarray(lo) - self.o) / self.c).astype(np.int64), 0)
        i1 = np.floor((np.asarray(hi) - self.o) / self.c).astype(np.int64)
        i1[1] = min(int(i1[1]), self.ny - 1)
        if i1[0] < i0[0] or i1[1] < i0[1]:
            return np.zeros(0, np.int64)
        ks = (np.arange(i0[0], i1[0] + 1)[:, None] * self.ny + np.arange(i0[1], i1[1] + 1)[None]).ravel()
        a = np.searchsorted(self.cles, ks, "left")
        b = np.searchsorted(self.cles, ks, "right")
        if not (b > a).any():
            return np.zeros(0, np.int64)
        return np.unique(np.concatenate([self.tri_cle[x:y] for x, y in zip(a, b) if y > x]))

    def aretes(self, cand, lo, hi):
        """Arêtes des triangles candidats coupées au rectangle [lo, hi] : (n, 2, 2)."""
        if len(cand) == 0:
            return np.zeros((0, 2, 2))
        Tc = self.T[cand][:, :, :2]
        E = np.concatenate([Tc[:, [0, 1]], Tc[:, [1, 2]], Tc[:, [2, 0]]])
        a = np.round(E[:, 0] / 1e-6).astype(np.int64)
        b = np.round(E[:, 1] / 1e-6).astype(np.int64)
        sw = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
        E[sw] = E[sw][:, ::-1]
        k = np.round(E.reshape(-1, 4) / 1e-6).astype(np.int64)
        _, ui = np.unique(k, axis=0, return_index=True)
        E = E[np.sort(ui)]
        # Liang-Barsky
        p0, d = E[:, 0], E[:, 1] - E[:, 0]
        t0, t1 = np.zeros(len(E)), np.ones(len(E))
        ok = np.ones(len(E), bool)
        for ax in range(2):
            for pp, qq in ((-d[:, ax], p0[:, ax] - lo[ax]), (d[:, ax], hi[ax] - p0[:, ax])):
                par = np.abs(pp) < 1e-15
                ok &= ~(par & (qq < 0))
                r = np.where(par, 0.0, qq / np.where(par, 1.0, pp))
                ent = (pp < 0) & ~par
                sor = (pp > 0) & ~par
                t0 = np.where(ent, np.maximum(t0, r), t0)
                t1 = np.where(sor, np.minimum(t1, r), t1)
        ok &= t1 - t0 > 1e-9
        E2 = np.stack([p0 + d * t0[:, None], p0 + d * t1[:, None]], axis=1)[ok]
        return E2

    def localiser(self, Q, cand):
        """Indice du triangle support de chaque point (v2 d'abord, puis z le plus haut) ou −1."""
        Q = np.atleast_2d(Q)
        res = np.full(len(Q), -1, np.int64)
        if len(cand) == 0 or len(Q) == 0:
            return res
        Tc = self.T[cand]
        a, b, c = Tc[:, 0, :2], Tc[:, 1, :2], Tc[:, 2, :2]
        v0, v1 = b - a, c - a
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        v2 = Q[:, None, :] - a[None]
        d20 = (v2 * v0[None]).sum(2)
        d21 = (v2 * v1[None]).sum(2)
        lv = (d11 * d20 - d01 * d21) / den
        lw = (d00 * d21 - d01 * d20) / den
        lu = 1 - lv - lw
        ins = (lu >= -1e-9) & (lv >= -1e-9) & (lw >= -1e-9)
        z = lu * Tc[None, :, 0, 2] + lv * Tc[None, :, 1, 2] + lw * Tc[None, :, 2, 2]
        cle = np.where(ins, (1 - self.src[cand][None]) * 1e6 + z, -np.inf)
        j = np.argmax(cle, axis=1)
        trouve = np.isfinite(cle[np.arange(len(Q)), j])
        res[trouve] = cand[j[trouve]]
        return res

    def z_plan(self, t, Q):
        """z du plan du triangle t (indices) aux points Q (barycentriques, extrapolation permise)."""
        Tt = self.T[t]
        a, b, c = Tt[:, 0], Tt[:, 1], Tt[:, 2]
        v0, v1 = (b - a)[:, :2], (c - a)[:, :2]
        v2 = Q - a[:, :2]
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        lv = (d11 * d20 - d01 * d21) / den
        lw = (d00 * d21 - d01 * d20) / den
        return (1 - lv - lw) * a[:, 2] + lv * b[:, 2] + lw * c[:, 2]

    def z_sous(self, Q):
        """(z, triangle) du sol sous des points quelconques (contrôles)."""
        Q = np.atleast_2d(Q)
        z = np.full(len(Q), np.nan)
        tri = np.full(len(Q), -1, np.int64)
        cel = np.floor((Q - self.o) / self.c).astype(np.int64)
        cles = cel[:, 0] * self.ny + cel[:, 1]
        for k in np.unique(cles):
            m = np.where(cles == k)[0]
            a = np.searchsorted(self.cles, k, "left")
            b = np.searchsorted(self.cles, k, "right")
            if b <= a:
                continue
            t = self.localiser(Q[m], self.tri_cle[a:b])
            ok = t >= 0
            tri[m[ok]] = t[ok]
            z[m[ok]] = self.z_plan(t[ok], Q[m[ok]])
        return z, tri


# =========================================================================== triangulation et drapé
def trianguler(polys, segments, centre, exact=False):
    """Triangulate 2D : contours fermés (contraintes, intérieur gardé) + segments ouverts (arêtes du sol)."""
    g = hou.Geometry()
    grp = g.createPrimGroup("c")
    pts, anneaux_, ouverts = [], [], []
    for poly in polys:
        for r in poly:
            i0 = len(pts)
            pts += [(float(x - centre[0]), float(y - centre[1]), 0.0) for x, y in r]
            anneaux_.append(list(range(i0, len(pts))))
    for s in segments:
        i0 = len(pts)
        pts += [(float(s[0, 0] - centre[0]), float(s[0, 1] - centre[1]), 0.0),
                (float(s[1, 0] - centre[0]), float(s[1, 1] - centre[1]), 0.0)]
        ouverts.append([i0, i0 + 1])
    g.createPoints([hou.Vector3(*q) for q in pts])
    if anneaux_:
        for pr in g.createPolygons(anneaux_, True):
            grp.add(pr)
    if ouverts:
        for pr in g.createPolygons(ouverts, False):
            grp.add(pr)
    v = CAT.nodeVerb("triangulate2d::3.0")
    v.setParms({"planepossrc": 1, "origin": hou.Vector3(0, 0, 0), "dir": hou.Vector3(0, 0, 1),
                "useconstrpolys": 1, "constrpolys": "c", "allowconstrsplit": 1, "removeduplicatepoints": 1,
                "removefromconvexhull": 1, "removefromconstrpolys": 1, "keepprims": 0, "removeunusedpoints": 1,
                "refine": 0, "useexactconstruction": int(exact)})
    out = hou.Geometry()
    v.execute(out, [g])
    P = np.array(out.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)[:, :2] + np.asarray(centre)
    F = np.array([[vv.point().number() for vv in pr.vertices()] for pr in out.iterPrims()], dtype=np.int64).reshape(-1, 3)
    if len(F) == 0:
        return P, F
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    F[cr < 0] = F[cr < 0][:, [0, 2, 1]]
    return P, F[np.abs(cr) > 2 * EPS_AIRE]


def nettoyer(P, F, fixes, eps=COURTE, segs=None):
    """Arêtes de moins de eps (m) fusionnées : le sommet libre (point de coupe par une arête du sol, ou
    sommet du sol) rejoint l'autre extrémité ; les sommets du contour de la marque (fixes) ne bougent pas ; un
    point posé sur une arête du contour (segs ≥ 0) ne rejoint qu'un point de la même arête ou un sommet fixe (le
    coin d'un gabarit n'est jamais rogné) ; une fusion qui retournerait un triangle est annulée. -> (P, F)."""
    for _ in range(3):
        E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
        E = np.unique(E, axis=0)
        L = np.hypot(*(P[E[:, 0]] - P[E[:, 1]]).T)
        courtes = E[L < eps]
        if len(courtes) == 0:
            break
        cible = np.arange(len(P))
        fait = np.zeros(len(P), bool)
        for a, b in courtes[np.argsort(L[L < eps], kind="stable")]:
            if fait[a] or fait[b]:
                continue
            if not fixes[b]:
                src, dst = b, a
            elif not fixes[a]:
                src, dst = a, b
            else:
                continue
            if segs is not None and segs[src] >= 0 and not fixes[dst] and segs[dst] != segs[src]:
                continue
            cible[src] = dst
            fait[src] = fait[dst] = True
        if not fait.any():
            break
        F2 = cible[F]
        garde = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
        a, b, c = P[F2[:, 0]], P[F2[:, 1]], P[F2[:, 2]]
        cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        inv = garde & (cr <= 2 * EPS_AIRE)
        if inv.any():                                           # annule les fusions qui retournent un triangle
            mauvais = np.unique(F[inv])
            cible[mauvais] = mauvais
            for s in np.where(cible != np.arange(len(P)))[0]:
                if cible[s] in mauvais:
                    cible[s] = s
            F2 = cible[F]
            garde = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
            a, b, c = P[F2[:, 0]], P[F2[:, 1]], P[F2[:, 2]]
            cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            garde &= cr > 2 * EPS_AIRE
        if np.array_equal(F2[garde], F):
            break
        F = F2[garde]
    return P, F


def couper_segments(E, lo, hi):
    """Segments (n, 2, 2) coupés au rectangle [lo, hi] (Liang-Barsky)."""
    if len(E) == 0:
        return np.zeros((0, 2, 2))
    p0, d = E[:, 0], E[:, 1] - E[:, 0]
    t0, t1 = np.zeros(len(E)), np.ones(len(E))
    ok = np.ones(len(E), bool)
    for ax in range(2):
        for pp, qq in ((-d[:, ax], p0[:, ax] - lo[ax]), (d[:, ax], hi[ax] - p0[:, ax])):
            par = np.abs(pp) < 1e-15
            ok &= ~(par & (qq < 0))
            r = np.where(par, 0.0, qq / np.where(par, 1.0, pp))
            t0 = np.where((pp < 0) & ~par, np.maximum(t0, r), t0)
            t1 = np.where((pp > 0) & ~par, np.minimum(t1, r), t1)
    ok &= t1 - t0 > 1e-9
    return np.stack([p0 + d * t0[:, None], p0 + d * t1[:, None]], axis=1)[ok]


def _aretes_polys(polys):
    out = []
    for poly in polys:
        for r in poly:
            r = np.asarray(r, float)
            out.append(np.stack([r, np.roll(r, -1, axis=0)], axis=1))
    return np.concatenate(out) if out else np.zeros((0, 2, 2))


def _dans(Q, polys):
    m = np.zeros(len(Q), bool)
    for poly in polys:
        m |= C.dans_polygone(Q, [np.asarray(r, float) for r in poly])
    return m


def fabriquer_piece(pc, sol, coupes=()):
    """Triangles drapés d'une pièce. `coupes` : [(motif, polygones)] à retirer de la marque (bande sous la tête des
    bordures v2, marque d'une entité prioritaire) : leurs contours sont des contraintes de la triangulation et les
    triangles dont le centroïde y tombe sont retirés. Après le drapé : sommets de même (x, y) à moins de 2 mm d'écart
    soudés ; déchirures (même arête plane, altitudes différentes : marche du sol v1) : la pièce est découpée en
    régions le long des déchirures et seules les régions qui ne déchirent pas une région mieux classée (sur chaussée,
    puis plus grande) sont gardées ; triangles posés sur un sol de pente > 60 % (face de bordure, marche) retirés ; composantes hors chaussée d'une
    pièce qui touche la chaussée retirées ; éclats de coupe plus étroits que min(0,10 m, 0,75 x largeur de la pièce) retirés.
    -> {P, F, sup, hors_sol_m2, coupe_m2 {motif: m²}, dechirure_m2, eclats_m2, mode} ou None."""
    R = np.vstack([r for poly in pc["polys"] for r in poly])
    lo, hi = R.min(axis=0) - 0.01, R.max(axis=0) + 0.01
    centre = np.round((lo + hi) / 2, 2)
    cand = sol.candidats(lo, hi)
    E = sol.aretes(cand, lo, hi)
    Ec = [couper_segments(_aretes_polys(polys), lo, hi) for _, polys in coupes]
    E = np.concatenate([E] + Ec) if Ec else E
    mode = "exact"
    try:
        P2, F = trianguler(pc["polys"], E, centre)
    except hou.OperationFailed:
        try:
            P2, F = trianguler(pc["polys"], E, centre, exact=True)
            mode = "exact_construction"
        except hou.OperationFailed:
            P2, F = trianguler(pc["polys"], np.zeros((0, 2, 2)), centre)
            mode = "sans_aretes_du_sol"
    if len(F) == 0:
        return None
    d = np.full(len(P2), np.inf)
    for k in range(0, len(R), 256):
        d = np.minimum(d, np.min(np.hypot(*(P2[:, None, :] - R[None, k:k + 256]).transpose(2, 0, 1)), axis=1))
    ctr = _aretes_polys(pc["polys"])
    dseg, iseg, _ = C.distance_segments(P2, ctr[:, 0], ctr[:, 1])
    P2, F = nettoyer(P2, F, d < 1e-5, segs=np.where(dseg < 1e-6, iseg, -1))
    G = P2[F].mean(axis=1)
    a_tri = aires_tri(P2, F)
    coupe = collections.Counter()
    garde = np.ones(len(F), bool)
    for motif, polys in coupes:
        m = garde & _dans(G, polys)
        coupe[motif] += float(a_tri[m].sum())
        garde &= ~m
    F, G, a_tri = F[garde], G[garde], a_tri[garde]
    sup = sol.localiser(G, cand)
    ok = sup >= 0
    hors = float(a_tri[~ok].sum())
    F, sup = F[ok], sup[ok]
    vide = {"P": np.zeros((0, 3)), "F": np.zeros((0, 3), np.int64), "sup": np.zeros(0, np.int64), "hors_sol_m2": hors,
            "coupe_m2": dict(coupe), "dechirure_m2": 0.0, "eclats_m2": 0.0, "mode": mode}
    if len(F) == 0:
        return vide
    Q = P2[F].reshape(-1, 2)
    if mode == "sans_aretes_du_sol":                           # repli : z du sol sous chaque sommet
        z, _ = sol.z_sous(Q)
        z = np.where(np.isfinite(z), z, sol.z_plan(np.repeat(sup, 3), Q))
    else:
        z = sol.z_plan(np.repeat(sup, 3), Q)
    # soudure plane : sommets de même (x, y) dont les altitudes diffèrent de moins de 2 mm -> altitude moyenne
    cxy = np.round(Q / SOUDURE).astype(np.int64)
    _, ixy = np.unique(cxy, axis=0, return_inverse=True)
    ixy = ixy.reshape(-1)
    zmin = np.full(ixy.max() + 1, np.inf)
    zmax = np.full(ixy.max() + 1, -np.inf)
    np.minimum.at(zmin, ixy, z)
    np.maximum.at(zmax, ixy, z)
    zs = np.zeros(ixy.max() + 1)
    ns = np.zeros(ixy.max() + 1)
    np.add.at(zs, ixy, z)
    np.add.at(ns, ixy, 1.0)
    serre = (zmax - zmin)[ixy] <= SEUIL_DECHIRURE
    z = np.where(serre, (zs / ns)[ixy], z)
    P3 = np.c_[Q, z + pc["dz"]]
    cle = np.round(P3 / SOUDURE).astype(np.int64)
    _, ui, inv = np.unique(cle, axis=0, return_index=True, return_inverse=True)
    ordre = np.argsort(ui)                                       # ordre d'apparition (déterministe)
    rang = np.empty_like(ordre)
    rang[ordre] = np.arange(len(ordre))
    P = P3[ui[ordre]]
    F2 = rang[inv.reshape(-1)].reshape(-1, 3)
    bon = (F2[:, 0] != F2[:, 1]) & (F2[:, 1] != F2[:, 2]) & (F2[:, 0] != F2[:, 2])
    F2, sup = F2[bon], sup[bon]
    # sol trop pentu (face de bordure, talus du sol v1) : pas de marque
    raide = sol.pente[sup] > PENTE_SOL_MAX
    coupe["pente"] += float(aires_tri(P, F2)[raide].sum())
    F2, sup = F2[~raide], sup[~raide]
    # régions séparées par les déchirures (arête plane commune, sommets différents)
    F2, sup, dech = _sans_dechirure(P, F2, sup, sol)
    # composantes hors chaussée d'une pièce qui a une partie sur la chaussée (au-delà d'une bordure, d'une marche)
    F2, sup, hc = _cote_chaussee(P, F2, sup, sol)
    coupe["hors_chaussee"] += hc
    # éclats de coupe
    F2, sup, ecl = _sans_eclats(P, F2, sup, pc)
    # sommets inutilisés retirés (ordre d'apparition gardé)
    used = np.unique(F2)
    remap = -np.ones(len(P), np.int64)
    remap[used] = np.arange(len(used))
    return {"P": P[used], "F": remap[F2], "sup": sup, "hors_sol_m2": hors, "coupe_m2": dict(coupe), "dechirure_m2": dech,
            "eclats_m2": ecl, "mode": mode}


def _aretes_faces(F):
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    f = np.tile(np.arange(len(F)), 3)
    return E, f


def _composantes(n, paires):
    par = np.arange(n)

    def rac(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for a, b in paires:
        ra, rb = rac(a), rac(b)
        if ra != rb:
            par[max(ra, rb)] = min(ra, rb)
    return np.array([rac(i) for i in range(n)])


def _sans_dechirure(P, F, sup, sol):
    """Faces gardées hors des régions qui déchirent une région mieux classée (chaussée, puis aire) ; une déchirure
    interne à une région (marche qui s'éteint) retire les faces du côté haut. -> (F, sup, aire retirée)."""
    if len(F) == 0:
        return F, sup, 0.0
    E, fe = _aretes_faces(F)
    kxy = np.round(P[:, :2] / SOUDURE).astype(np.int64)
    a, b = kxy[E[:, 0]], kxy[E[:, 1]]
    sw = (a[:, 0] > b[:, 0]) | ((a[:, 0] == b[:, 0]) & (a[:, 1] > b[:, 1]))
    cle_xy = np.where(sw[:, None], np.c_[b, a], np.c_[a, b])
    cle_v = np.sort(E, axis=1)
    _, gxy = np.unique(cle_xy, axis=0, return_inverse=True)
    gxy = gxy.reshape(-1)
    ordre = np.lexsort((fe, gxy))
    voisines, dechirures = [], []
    for i in range(len(ordre) - 1):
        u, v = ordre[i], ordre[i + 1]
        if gxy[u] != gxy[v]:
            continue
        if np.array_equal(cle_v[u], cle_v[v]):
            voisines.append((fe[u], fe[v]))
        else:
            dechirures.append((fe[u], fe[v]))
    if not dechirures:
        return F, sup, 0.0
    reg = _composantes(len(F), voisines)
    aire = aires_tri(P, F)
    route = sol.chaussee[sol.cl[sup]]
    stats = {}
    for r_ in np.unique(reg):
        m = reg == r_
        stats[int(r_)] = (float((aire[m] * route[m]).sum() / max(aire[m].sum(), 1e-12)) >= 0.5, float(aire[m].sum()), int(r_))
    conflits = collections.defaultdict(set)
    internes = []
    for fa, fb in dechirures:
        ra, rb = int(reg[fa]), int(reg[fb])
        if ra == rb:
            internes.append((fa, fb))
        else:
            conflits[ra].add(rb)
            conflits[rb].add(ra)
    gardees, rejetees = set(), set()
    for r_ in sorted(stats, key=lambda r: (not stats[r][0], -stats[r][1], r)):
        if r_ in rejetees:
            continue
        gardees.add(r_)
        rejetees |= conflits[r_]
    garde = np.array([int(r) in gardees for r in reg])
    for fa, fb in internes:                                       # marche qui s'éteint dans la région : côté haut retiré
        za, zb = P[F[fa], 2].mean(), P[F[fb], 2].mean()
        haut = fa if (za > zb if route[fa] == route[fb] else not route[fa]) else fb
        garde[haut] = False
    return F[garde], sup[garde], float(aire[~garde].sum())


def _cote_chaussee(P, F, sup, sol):
    """Composantes (sommets partagés) : si l'une est sur la chaussée (≥ 50 % de son aire), celles qui n'y sont pas sont
    retirées. -> (F, sup, aire retirée)."""
    if len(F) == 0:
        return F, sup, 0.0
    E, fe = _aretes_faces(F)
    reg = _composantes(len(F), [(fe[i], fe[j]) for i, j in _paires_meme(np.unique(np.sort(E, axis=1), axis=0, return_inverse=True)[1].reshape(-1))])
    aire_f = aires_tri(P, F)
    route = sol.chaussee[sol.cl[sup]]
    roul = {}
    for r_ in np.unique(reg):
        m = reg == r_
        roul[int(r_)] = float((aire_f[m] * route[m]).sum()) >= 0.5 * float(aire_f[m].sum())
    if not any(roul.values()) or all(roul.values()):
        return F, sup, 0.0
    garde = np.array([roul[int(r)] for r in reg])
    return F[garde], sup[garde], float(aire_f[~garde].sum())


def _sans_eclats(P, F, sup, pc):
    """Composantes de la pièce dont le bord comporte une coupe (arête hors du contour de la marque) et plus étroites
    (2 aire / périmètre) que min(ECLAT_MAX, 0,75 x largeur de la pièce) : retirées. -> (F, sup, aire retirée)."""
    if len(F) == 0:
        return F, sup, 0.0
    A0 = sum(abs(aire(pp[0])) - sum(abs(aire(h)) for h in pp[1:]) for pp in pc["polys"])
    P0 = sum(float(np.hypot(*np.diff(np.vstack([r, r[:1]]), axis=0).T).sum()) for pp in pc["polys"] for r in pp)
    W0 = 2.0 * A0 / max(P0, 1e-9)
    E, fe = _aretes_faces(F)
    cle = np.sort(E, axis=1)
    _, gi, cnt = np.unique(cle, axis=0, return_inverse=True, return_counts=True)
    gi = gi.reshape(-1)
    bord = cnt[gi] == 1
    reg = _composantes(len(F), [(fe[i], fe[j]) for i, j in _paires_meme(gi)])
    contour = _aretes_polys(pc["polys"])
    A, B = contour[:, 0], contour[:, 1]
    mil = 0.5 * (P[E[:, 0], :2] + P[E[:, 1], :2])
    dmin, _, _ = C.distance_segments(mil[bord], A, B) if bord.any() else (np.zeros(0), None, None)
    coupee = np.zeros(len(E), bool)
    coupee[np.where(bord)[0]] = dmin > 1e-4
    aire_f = aires_tri(P, F)
    Lb = np.hypot(*(P[E[:, 0], :2] - P[E[:, 1], :2]).T)
    garde = np.ones(len(F), bool)
    retire = 0.0
    for r_ in np.unique(reg):
        mf = reg == r_
        me = mf[fe]
        if not (coupee & me).any():
            continue
        a_ = float(aire_f[mf].sum())
        w = 2.0 * a_ / max(float(Lb[bord & me].sum()), 1e-9)
        if w < min(ECLAT_MAX, 0.75 * W0):
            garde[mf] = False
            retire += a_
    return F[garde], sup[garde], retire


def _paires_meme(g):
    o = np.argsort(g, kind="stable")
    gs = g[o]
    return [(o[i], o[i + 1]) for i in range(len(o) - 1) if gs[i] == gs[i + 1]]


# =========================================================================== coupes
def bandes_bordures(description):
    """Bandes sous la tête des bordures v2 décrites : de l'arête avant (u = 0) à la base du profil le plus large de la
    bordure, côté haut (gauche de l'arête) ; une marque n'y est pas peinte (enfouie sous l'élément posé)."""
    try:
        desc = K.Description(description)
    except Exception:
        return []
    specs = desc.specs
    out = []
    for B in desc.bordures:
        base = 0.0
        for it in B.p.get("intervalles", []):
            try:
                base = max(base, specs.dims(it.get("profil", "T2"))[0])
            except Exception:
                base = max(base, 0.15)
        P = C.dedoublonner_sommets(np.asarray(B.P, float)[:, :2])
        if len(P) < 2 or base <= 0:
            continue
        Pg = C.decaler(P, base)
        r = np.vstack([P, Pg[::-1]])
        out.append((B.id, orienter([r]), (*r.min(axis=0), *r.max(axis=0))))
    return out


def faces_v1(log=journal):
    """Faces verticales des bordures v1 (paquet v1, /World/Bordures/faces_verticales) de plus de FACE_MIN, hors emprise pilote
    (sol v2) : segments au sol [(A, B, h)] (local) ; la face d'un triangle vertical est sa plus longue arête plane."""
    st = Usd.Stage.Open(str(V1_RACINE))
    pr = st.GetPrimAtPath("/World/Bordures/faces_verticales")
    if not pr or not pr.IsA(UsdGeom.Mesh):
        return np.zeros((0, 2)), np.zeros((0, 2)), np.zeros(0)
    m = UsdGeom.Mesh(pr)
    P = np.asarray(m.GetPointsAttr().Get(), dtype=np.float64)
    M_ = np.array(UsdGeom.Xformable(pr).ComputeLocalToWorldTransform(Usd.TimeCode.Default()), dtype=np.float64)
    if not np.allclose(M_, np.eye(4)):
        P = (np.c_[P, np.ones(len(P))] @ M_)[:, :3]
    cnt = np.asarray(m.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
    idx = np.asarray(m.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
    deb = np.r_[0, np.cumsum(cnt)[:-1]]
    F = np.vstack([np.c_[idx[deb[cnt > k + 1]], idx[deb[cnt > k + 1] + k], idx[deb[cnt > k + 1] + k + 1]] for k in range(1, int(cnt.max()) - 1)])
    T = P[F]
    h = T[:, :, 2].max(axis=1) - T[:, :, 2].min(axis=1)
    E = [(0, 1), (1, 2), (2, 0)]
    L = np.stack([np.hypot(*(T[:, a, :2] - T[:, b, :2]).T) for a, b in E], axis=1)
    k = np.argmax(L, axis=1)
    A = np.stack([T[np.arange(len(T)), [E[i][0] for i in k], :2]], axis=0)[0]
    B = np.stack([T[np.arange(len(T)), [E[i][1] for i in k], :2]], axis=0)[0]
    ok = (h > FACE_MIN) & (L.max(axis=1) > 0.02)
    A, B, h = A[ok], B[ok], h[ok]
    zp = [C.repere(np.asarray(r, float)[:, :2]) for r in C.anneaux(C.lire_geojson(C.ZONE)[0]["geometry"])[0]]
    hors = ~C.dans_polygone(0.5 * (A + B), zp)
    # dédoublonnage (deux triangles par quadrilatère de face) au 1/10 mm
    cle = np.round(np.c_[np.minimum(A, B), np.maximum(A, B)] / 1e-4).astype(np.int64)
    _, ui = np.unique(cle[hors], axis=0, return_index=True)
    sel = np.where(hors)[0][np.sort(ui)]
    log(f"   {len(sel)} segments de faces verticales v1 > {FACE_MIN * 100:.0f} cm (hors emprise pilote)")
    return A[sel], B[sel], h[sel]


def bandes_faces(A, B, marge=SECURITE_FACE):
    """Rectangles (segment élargi de `marge` de part et d'autre et prolongé de `marge`) autour des faces v1."""
    d = B - A
    L = np.maximum(np.hypot(*d.T), 1e-12)
    u = d / L[:, None]
    n = np.c_[-u[:, 1], u[:, 0]]
    a, b = A - u * marge, B + u * marge
    return [np.array([a[k] - n[k] * marge, b[k] - n[k] * marge, b[k] + n[k] * marge, a[k] + n[k] * marge]) for k in range(len(A))]


def _cle_prio(pc):
    return (PRIORITE.get(pc["classe"], 0), [-ord(c) for c in pc["entite"]])


def coupes_prioritaires(pieces, bandes, faces=None):
    """Pour chaque pièce : [(motif, polygones)] à retirer : découpes décrites (dégagement des bordures, marque voisine),
    bandes de tête de bordure v2 et bandes de sécurité des faces verticales v1 qui la touchent, puis pièces d'entités plus
    prioritaires (fantôme < zone < passage < ligne < flèche / symbole, puis id) qui la recouvrent (filet de sécurité : la
    description ne laisse plus de recouvrement)."""
    bb = []
    for pc in pieces:
        R = np.vstack([r for poly in pc["polys"] for r in poly])
        bb.append((*R.min(axis=0), *R.max(axis=0)))
    bb = np.array(bb)
    cles = [_cle_prio(pc) for pc in pieces]
    out = []
    for i, pc in enumerate(pieces):
        x0, y0, x1, y1 = bb[i]
        cp = []
        if pc.get("decoupes"):
            cp.append(("decoupe_description", pc["decoupes"]))
        bords = [polys for _, polys, b in bandes if not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)]
        if bords:
            cp.append(("bordure_v2", [poly for poly in bords]))
        if faces is not None and len(faces[0]):
            FA, FB = faces
            mf = ~((np.maximum(FA[:, 0], FB[:, 0]) < x0 - 0.05) | (np.minimum(FA[:, 0], FB[:, 0]) > x1 + 0.05)
                   | (np.maximum(FA[:, 1], FB[:, 1]) < y0 - 0.05) | (np.minimum(FA[:, 1], FB[:, 1]) > y1 + 0.05))
            if mf.any():
                cp.append(("face_bordure_v1", [orienter([r]) for r in bandes_faces(FA[mf], FB[mf])]))
        m = ~((bb[:, 2] < x0) | (bb[:, 0] > x1) | (bb[:, 3] < y0) | (bb[:, 1] > y1))
        prio = [pieces[j]["polys"] for j in np.where(m)[0]
                if pieces[j]["entite"] != pc["entite"] and cles[j] > cles[i]]
        if prio:
            cp.append(("marque_prioritaire", [poly for polys in prio for poly in polys]))
        out.append(cp)
    return out


# =========================================================================== fabrication
class Fabrication:
    def __init__(self, description=K.DESCRIPTION, fabrique=K.FABRIQUE, log=journal):
        self.log = log
        self.fabrique = Path(fabrique)
        t0 = time.time()
        log("pj_marquages : description")
        self.pc = Pieces(description, log)
        log("pj_marquages : sol")
        self.sol = Sol(fabrique, log)
        self.peinture = K.lire_json(PEINTURE)
        log("pj_marquages : triangulation et drapé")
        self.bandes = bandes_bordures(description)
        log(f"   {len(self.bandes)} bandes de tête de bordure v2 (marques coupées)")
        self.faces = faces_v1(log)
        coupes = coupes_prioritaires(self.pc.pieces, self.bandes, self.faces[:2])
        self.res = []
        for pc, cp in zip(self.pc.pieces, coupes):
            r = fabriquer_piece(pc, self.sol, cp)
            if r is not None:
                self.res.append((pc, r))
        log(f"   {sum(len(r['F']) for _, r in self.res)} triangles ({time.time() - t0:.0f} s)")
        self.traces_roues()
        try:
            self.desc_bordures = K.Description(description).bordures
        except Exception:
            self.desc_bordures = None
        self.axes_et_bordures()
        self.empilement = self.empiler()
        if self.empilement["abaissees"]:
            log(f"   empilement : {len(self.empilement['abaissees'])} entités abaissées sous une marque prioritaire")

    def traces_roues(self):
        """peinture.json usure.traces_de_roues_option : sommets de toutes les marques d'usure 1 à 3 (hors fantômes) :
        facteur de manque f = 1 + 1,5·exp(−((|t| − 0,85) / 0,20)²), t = écart au centre de la voie OpenDRIVE (roulable)
        sous le sommet ; 1 ailleurs (primvar manque_roues, par sommet) ; les marques neuves (usure 0) restent uniformes ;
        les barbes des flèches et les bouts de bandes s'usent, la tige et les lignes de voie (|t| ≈ demi-voie) restent."""
        loc = SY.Localisateur(self.pc.reseau)
        cache = {}
        n = 0
        for pc, r in self.res:
            r["roues"] = np.ones(len(r["P"]))
            if pc["classe"] == "fantome" or pc["usure"] in ("0", "F") or not len(r["P"]):
                continue
            for i, q in enumerate(r["P"][:, :2]):
                k = (round(float(q[0]), 3), round(float(q[1]), 3))
                if k not in cache:
                    vs = loc.voies(np.asarray(k), types=("driving", "bus"))
                    cache[k] = 1.0 + 1.5 * math.exp(-((vs[0]["ecart_centre"] - 0.85) / 0.20) ** 2) if vs else 1.0
                r["roues"][i] = cache[k]
            n += 1
        self.log(f"   traces de roues : {n} pièces")

    def axes_et_bordures(self):
        """Primvars par sommet : axe_marque (direction principale de la pièce, ACP de son contour : plaques de faïençage
        allongées en travers) et dist_bordure (distance plane à la face de bordure la plus proche : faces v1 > 2 cm et
        arêtes avant v2, salissure du caniveau)."""
        FA, FB, _ = self.faces
        segA, segB = [FA], [FB]
        for B in self.desc_bordures or []:
            segA.append(B.P[:-1, :2])
            segB.append(B.P[1:, :2])
        A, Bv = np.vstack(segA), np.vstack(segB)
        lo_s, hi_s = np.minimum(A, Bv), np.maximum(A, Bv)
        for pc, r in self.res:
            R = np.vstack([rr for poly in pc["polys"] for rr in poly])
            c = R.mean(axis=0)
            w, V = np.linalg.eigh((R - c).T @ (R - c))
            a = V[:, int(np.argmax(w))]
            if a[0] < 0 or (abs(a[0]) < 1e-12 and a[1] < 0):
                a = -a
            r["axe"] = np.tile(np.round(a, 5), (len(r["P"]), 1))
            if not len(r["P"]):
                r["dbord"] = np.zeros(0)
                continue
            lo, hi = r["P"][:, :2].min(axis=0) - 0.3, r["P"][:, :2].max(axis=0) + 0.3
            m = ~((hi_s[:, 0] < lo[0]) | (lo_s[:, 0] > hi[0]) | (hi_s[:, 1] < lo[1]) | (lo_s[:, 1] > hi[1]))
            if m.any():
                d, _, _ = C.distance_segments(r["P"][:, :2], A[m], Bv[m])
                r["dbord"] = np.round(np.minimum(d, 10.0), 4)
            else:
                r["dbord"] = np.full(len(r["P"]), 10.0)

    def empiler(self, pas=0.0005):
        """Marques d'entités différentes qui se recouvrent : la moins prioritaire (fantôme < zone < passage <
        ligne < flèche / symbole, puis id décroissant) passe au moins `pas` sous l'autre (pas de z-fighting)."""
        rec = recouvrements(self)
        classe = {pc["entite"]: pc["classe"] for pc, _ in self.res}
        dz = {pc["entite"]: pc["dz"] for pc, _ in self.res}
        cle = lambda e: (PRIORITE.get(classe[e], 0), [-ord(c) for c in e])
        paires = []
        for a, b, ar in rec["paires"]:
            hi, lo = (a, b) if cle(a) > cle(b) else (b, a)
            paires.append((hi, lo, ar))
        dz0 = dict(dz)
        for _ in range(20):
            change = False
            for hi, lo, _ in paires:
                if dz[lo] > dz[hi] - pas + 1e-9:
                    dz[lo] = round(dz[hi] - pas, 6)
                    change = True
            if not change:
                break
        abaissees = {e: [round(dz0[e] * 1000, 2), round(dz[e] * 1000, 2)] for e in sorted(dz) if dz[e] < dz0[e] - 1e-9}
        for pc, r in self.res:
            d = dz[pc["entite"]] - pc["dz"]
            if abs(d) > 1e-9:
                r["P"] = r["P"].copy()
                r["P"][:, 2] += d
                pc["dz"] = dz[pc["entite"]]
        return {"regle": f"recouvrement entre entités : la moins prioritaire ({' < '.join(k for k, _ in sorted(PRIORITE.items(), key=lambda kv: kv[1]))}, "
                         f"puis id) passe {pas * 1000:g} mm sous l'autre",
                "recouvrements_avant": rec, "abaissees": abaissees}

    # ------------------------------------------------------------------ maillages par classe
    def maillages(self, filtre=None):
        """{(couleur, usure): dict de tableaux} ; filtre(pièce, résultat) -> masque de faces."""
        groupes = collections.OrderedDict()
        for pc, r in self.res:
            m = np.ones(len(r["F"]), bool) if filtre is None else filtre(pc, r)
            if not m.any():
                continue
            k = (pc["couleur"], pc["usure"])
            g = groupes.setdefault(k, {"P": [], "F": [], "n": 0, "id": [], "type": [], "couv": [], "seuil": [], "sup": [], "roues": [],
                                       "axe": [], "dbord": []})
            F = r["F"][m]
            used = np.unique(F)
            remap = -np.ones(len(r["P"]), np.int64)
            remap[used] = np.arange(len(used))
            g["P"].append(r["P"][used])
            g["roues"].append(r["roues"][used] if "roues" in r else np.ones(len(used)))
            g["axe"].append(r["axe"][used] if "axe" in r else np.tile([1.0, 0.0], (len(used), 1)))
            g["dbord"].append(r["dbord"][used] if "dbord" in r else np.full(len(used), 10.0))
            g["F"].append(remap[F] + g["n"])
            g["n"] += len(used)
            nf = len(F)
            g["id"] += [pc["entite"]] * nf
            g["type"] += [pc["sous_type"]] * nf
            g["couv"].append(np.full(nf, pc["couverture"]))
            g["seuil"].append(np.full(nf, MM.seuil_face(self.peinture, pc["usure"], pc["couverture"])))
            g["sup"].append(self.sol.src[r["sup"][m]])
        cles = sorted(groupes, key=lambda k: (MM.COULEURS_ORDRE.index(k[0]) if k[0] in MM.COULEURS_ORDRE else 99, k[0],
                                              MM.USURES.index(k[1])))
        out = collections.OrderedDict()
        for k in cles:
            g = groupes[k]
            out[k] = {"P": np.vstack(g["P"]), "F": np.vstack(g["F"]), "id": g["id"], "type": g["type"],
                      "couv": np.concatenate(g["couv"]), "seuil": np.concatenate(g["seuil"]),
                      "sup": np.concatenate(g["sup"]), "roues": np.concatenate(g["roues"]),
                      "axe": np.vstack(g["axe"]), "dbord": np.concatenate(g["dbord"])}
        return out

    def ecrire_usd(self, chemin, doc, filtre=None, ref=None):
        ref = Path(ref or chemin)
        ms = self.maillages(filtre)
        st = U.scene(doc, data={"version": VERSION, "description_marquages": self.pc.hash,
                                "repere": "local = L93 − O (917279.43, 6460289.98), z = NGF − 216,30 ; m, Z haut"})
        U.xform(st, "/World/PJ_Marquages")
        K.typer_ue(st, "/World/PJ_Marquages")
        mats = MM.ecrire(st, list(ms), self.peinture, ref, K.Specs())
        comptes = {}
        for (c, u), g in ms.items():
            mid = MM.mid(c, u)
            path = f"/World/PJ_Marquages/{c}_u{u}"
            P = g["P"]
            N = U.normales_sommets(P, g["F"])
            sup = np.where(g["sup"] == 0, "v2", "v1")
            pv = {"couleur": (c, T.String, UsdGeom.Tokens.constant),
                  "usure": (u, T.String, UsdGeom.Tokens.constant),
                  "couverture": (U.vt(g["couv"], T.FloatArray), T.FloatArray, UsdGeom.Tokens.uniform),
                  "seuil_usure": (U.vt(g["seuil"], T.FloatArray), T.FloatArray, UsdGeom.Tokens.uniform),
                  "type": (Vt.StringArray(g["type"]), T.StringArray, UsdGeom.Tokens.uniform),
                  "id": (Vt.StringArray(g["id"]), T.StringArray, UsdGeom.Tokens.uniform),
                  "support": (Vt.StringArray([str(x) for x in sup]), T.StringArray, UsdGeom.Tokens.uniform),
                  "manque_roues": (U.vt(np.round(g["roues"], 4), T.FloatArray), T.FloatArray, UsdGeom.Tokens.vertex),
                  "axe_marque": (Vt.Vec2fArray([tuple(map(float, x)) for x in np.round(g["axe"], 5)]), T.Float2Array, UsdGeom.Tokens.vertex),
                  "dist_bordure": (U.vt(np.round(g["dbord"], 4), T.FloatArray), T.FloatArray, UsdGeom.Tokens.vertex),
                  # marque de 0,5 mm en réalité : pas d'ombre portée par le film décalé de 3 mm (trous sombres sinon)
                  "karma:object:rendervisibility": ("-shadow", T.String, UsdGeom.Tokens.constant)}
            m = U.maillage(st, path, np.round(P, 5), np.full(len(g["F"]), 3), g["F"].ravel(), normales=N,
                           st1=np.round(P[:, :2], 5), st1_interp="vertex", primvars=pv, materiau_id=mid)
            _, apercu, rug = mats[mid]
            UsdGeom.PrimvarsAPI(m).CreatePrimvar("displayColor", T.Color3fArray, UsdGeom.Tokens.constant).Set(
                Vt.Vec3fArray([tuple(map(float, apercu))]))
            m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set(f"/Game/PJ/Materials/MI_{mid}.MI_{mid}")
            U.lier_chemin(m.GetPrim(), f"{MM.LOOKS}/{mid}")
            K.lier_ue(m.GetPrim(), mid, apercu, rug)
            comptes[f"{c}_u{u}"] = {"triangles": int(len(g["F"])), "sommets": int(len(P)),
                                    "entites": len(set(g["id"]))}
        U.enregistrer(st, chemin)
        return comptes

    # ------------------------------------------------------------------ prototypes et points
    def ecrire_prototypes(self, chemin):
        """Gabarits à plat (z = 0, X = x du gabarit à droite, Y = sens de circulation, origine du gabarit)."""
        st = U.scene("Prototypes des symboles de marquage (pj_marquages.py) : gabarits IISR / site de "
                     "assets/specs/marquages_geometrie.json et formes unitaires, à plat, triangulés (Triangulate 2D) ; "
                     "X = x du gabarit (droite), Y = sens de circulation, Z haut, origine = origine du gabarit ; "
                     "posés par points/marquages_symboles.json (décalques ou maillages UE).",
                     data={"version": VERSION, "source": "assets/specs/marquages_geometrie.json"})
        U.xform(st, "/World/PJ_Marquages_Prototypes")
        K.typer_ue(st, "/World/PJ_Marquages_Prototypes")
        noms = sorted({s["asset"] for s in self.pc.symboles if not s["asset"].startswith("A_VECTORISER")})
        chev = {s["asset"]: s["x"]["chevron"] for s in self.pc.symboles if s["asset"].startswith("CHEVRON")}
        out = {}
        for nom in noms:
            if nom in self.pc.spec["gabarits"]:
                polys = [orienter(pp) for pp in MC.gabarit(nom)]
            elif nom == "RECT_UNITE":
                polys = [[np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])]]
            elif nom == "TRIANGLE_UNITE":
                polys = [[np.array([[-0.5, 0.0], [0.5, 0.0], [0.0, 1.0]])]]
            elif nom == "DISQUE_UNITE":
                polys = [[disque(np.zeros(2), 1.0, 0.0005)]]
            elif nom in self.pc.glyphes:
                polys = [orienter(pp) for pp in SY.construire_glyphe(self.pc.glyphes[nom])]
            elif nom.startswith("CHEVRON"):
                c = chev[nom]
                lb, ouv, tr = float(c["branche_m"]), math.radians(float(c["ouverture_deg"])), float(c["trait_m"])
                s2, c2 = math.sin(ouv / 2), math.cos(ouv / 2)
                e1, e2 = np.array([s2, -c2]) * lb, np.array([-s2, -c2]) * lb
                polys = [orienter([np.array([[0, 0], e2, e2 + np.array([c2, -s2]) * tr, [0, -tr / s2],
                                             e1 + np.array([-c2, -s2]) * tr, e1])])]
            else:
                continue
            P, F = trianguler(polys, [], np.zeros(2))
            m = U.maillage(st, f"/World/PJ_Marquages_Prototypes/{nom}", np.c_[P, np.zeros(len(P))],
                           np.full(len(F), 3), F.ravel(), normales=np.tile([0.0, 0.0, 1.0], (len(P), 1)),
                           st1=np.round(P, 5), st1_interp="vertex")
            a = float(aires_tri(P, F).sum())
            m.GetPrim().SetCustomDataByKey("aire_m2", round(a, 5))
            out[nom] = {"triangles": int(len(F)), "aire_m2": round(a, 5)}
        U.enregistrer(st, chemin)
        return out

    def points(self):
        """Poses des symboles : p = origine du gabarit au sol (+ 3 mm), lacet = cap − 90°, roulis / tangage = plan
        ajusté (moindres carrés) sur les sommets drapés de l'entité sous la boîte du symbole, pente bornée à
        PENTE_MAX (marche du sol v1 sous le symbole : plan non représentatif)."""
        pts = []
        cnt = collections.Counter()
        n_par = collections.Counter(s["entite"] for s in self.pc.symboles)
        sommets = collections.defaultdict(list)
        for pc, r in self.res:
            if len(r["P"]):
                sommets[pc["entite"]].append(r["P"] - np.array([0.0, 0.0, pc["dz"]]))
        sommets = {e: np.vstack(v) for e, v in sommets.items()}
        self.poses_bornees = []
        for s in self.pc.symboles:
            o = s["o"]
            d = dir_cap(s["cap"])
            ex = np.array([d[1], -d[0]])
            sx, sy = s["s"][0], s["s"][1]
            if s["asset"] in self.pc.spec["gabarits"]:
                b = self.pc.spec["gabarits"][s["asset"]]["boite"]
                bx, by = (b["x"][0] * sx, b["x"][1] * sx), (b["y"][0] * sy, b["y"][1] * sy)
            elif s["asset"] == "TRIANGLE_UNITE":
                bx, by = (-0.5 * sx, 0.5 * sx), (0.0, sy)
            else:
                bx, by = (-0.5 * sx, 0.5 * sx), (-0.5 * sy, 0.5 * sy)
            V = sommets.get(s["entite"], np.zeros((0, 3)))
            if len(V):
                u, v = (V[:, :2] - o) @ d, (V[:, :2] - o) @ ex
                V = V[(u >= by[0] - 0.05) & (u <= by[1] + 0.05) & (v >= bx[0] - 0.05) & (v <= bx[1] + 0.05)]
            cand = self.sol.candidats(o - 0.5, o + 0.5)
            t = self.sol.localiser(o[None], cand)
            gd = gx = 0.0
            z0 = float(self.sol.z_plan(t, o[None])[0]) if t[0] >= 0 else None
            if len(V) >= 3:
                A_ = np.c_[(V[:, :2] - o) @ d, (V[:, :2] - o) @ ex, np.ones(len(V))]
                if np.linalg.matrix_rank(A_) == 3:
                    (gd, gx, c0), *_ = np.linalg.lstsq(A_, V[:, 2], rcond=None)
                    if z0 is None:
                        z0 = float(c0)
            if max(abs(gd), abs(gx)) > PENTE_MAX:
                self.poses_bornees.append([s["entite"], round(float(gd), 3), round(float(gx), 3)])
                gd, gx = float(np.clip(gd, -PENTE_MAX, PENTE_MAX)), float(np.clip(gx, -PENTE_MAX, PENTE_MAX))
            if z0 is None:
                z0 = float(V[:, 2].mean()) if len(V) else 0.0
            # prototype : X = x du gabarit (droite), Y = sens de circulation ; R = Rz(y)·Ry(p)·Rx(r) :
            # y = cap − 90°, r = pente vers l'avant (+Y monte si r > 0), p = −pente vers la droite (+X)
            yaw = (s["cap"] - 90.0) % 360.0
            rpy = [round(math.degrees(math.atan(gd)), 3), round(-math.degrees(math.atan(gx)), 3), round(yaw, 3)]
            k = cnt[s["entite"]]
            cnt[s["entite"]] += 1
            pid = s["entite"] if n_par[s["entite"]] == 1 else f"{s['entite']}/{k:03d}"
            pts.append({"id": pid, "asset": s["asset"], "p": K.r3([o[0], o[1], z0 + DZ["marque"]], 4),
                        "q": K.q_xyzw(rpy), "rpy_deg": rpy, "s": K.r3(s["s"], 4), "graine": K.graine(pid, VERSION),
                        "cd": [round(s["couverture"], 3), {"0": 0, "1": 1, "2": 2, "3": 3, "F": 4}[s["usure"]]],
                        "x": dict({"entite": s["entite"], "classe": s["classe"], "type": s["type"],
                                   "couleur": s["couleur"], "usure": s["usure"],
                                   "materiau": MM.mid(s["couleur"], s["usure"]),
                                   "cap_deg": round(s["cap"], 3)}, **s["x"])})
        return pts


# =========================================================================== contrôles
def angles_min(P, F):
    a, b, c = P[F[:, 0], :2], P[F[:, 1], :2], P[F[:, 2], :2]
    out = []
    for u, v, w in ((a, b, c), (b, c, a), (c, a, b)):
        e1, e2 = v - u, w - u
        cs = np.einsum("ij,ij->i", e1, e2) / np.maximum(np.linalg.norm(e1, axis=1) * np.linalg.norm(e2, axis=1), 1e-15)
        out.append(np.degrees(np.arccos(np.clip(cs, -1, 1))))
    return np.min(out, axis=0)


def _stat(v, nd=4):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return None
    return {"n": int(len(v)), "min": round(float(v.min()), nd), "p5": round(float(np.percentile(v, 5)), nd),
            "mediane": round(float(np.median(v)), nd), "p95": round(float(np.percentile(v, 95)), nd),
            "max": round(float(v.max()), nd)}


def controles(fab, desc_bordures=None):
    sol, pcs = fab.sol, fab.pc
    out = {}
    # ---- aires fabriquées / attendues par entité
    aire_ent = collections.Counter()
    hors = collections.Counter()
    angmin = []
    for pc, r in fab.res:
        P, F = r["P"], r["F"]
        if len(F):
            aire_ent[pc["entite"]] += float(aires_tri(P, F).sum())
            angmin.append(angles_min(P, F))
        hors[pc["entite"]] += r["hors_sol_m2"]
    ecarts = []
    for eid, att in sorted(pcs.attendu.items()):
        a = att["aire"]
        if a is not None and a > 0:
            ecarts.append((abs(aire_ent.get(eid, 0.0) + hors.get(eid, 0.0) - a) / a, eid))
    ecarts.sort(reverse=True)
    out["aires"] = {"methode": "aire plane des triangles fabriqués (+ hors sol) / aire attendue des paramètres "
                               "(trait x largeur, gabarit x échelle², bandes, contour décrit)",
                    "ecart_relatif": _stat([e for e, _ in ecarts], 5),
                    "pires": [[i, round(e, 5)] for e, i in ecarts[:8]],
                    "hors_sol_m2": round(sum(hors.values()), 4),
                    "entites_hors_sol": sorted([i for i, v in hors.items() if v > 1e-4])}
    am = np.concatenate(angmin) if angmin else np.zeros(0)
    out["triangles"] = {"n": int(len(am)), "angle_min_deg": _stat(am, 2),
                        "n_angle_min_inf_1deg": int((am < 1.0).sum()), "n_angle_min_inf_5deg": int((am < 5.0).sum()),
                        "note": "les triangles fins viennent des arêtes du sol qui frôlent un sommet de marque "
                                "(drapé exact, triangle de marque dans un seul triangle de sol)"}
    # ---- gabarits : sommets fabriqués dans le repère du gabarit
    gab = []
    for pc, r in fab.res:
        att = pcs.attendu.get(pc["entite"], {})
        if "gabarit" not in att or not len(r["F"]):
            continue
        Qg = MC.dans_repere(r["P"][:, :2], att["origine"], att["cap"]) / att["echelle"]
        b = pcs.spec["gabarits"][att["gabarit"]]["boite"]
        dx = max(abs(Qg[:, 0].min() - b["x"][0]), abs(Qg[:, 0].max() - b["x"][1]))
        dy = max(abs(Qg[:, 1].min() - b["y"][0]), abs(Qg[:, 1].max() - b["y"][1]))
        ea = abs(aire_ent[pc["entite"]] - att["aire"]) / att["aire"]
        gab.append([pc["entite"], att["gabarit"], att["echelle"], round(max(dx, dy) * att["echelle"] * 1000, 3), round(ea * 100, 4)])
    out["gabarits"] = {"methode": "sommets fabriqués ramenés dans le repère du gabarit (origine, cap, échelle) : écart de la "
                                  "boîte à la boîte IISR (mm) et écart d'aire (%)",
                       "n": len(gab), "ecart_boite_max_mm": max((g[3] for g in gab), default=None),
                       "ecart_aire_max_pct": max((g[4] for g in gab), default=None), "detail": gab}
    out["fleches_hausdorff"] = hausdorff_fleches(fab)
    # ---- tirets
    nt = [(i, a["n_tirets"], a["n_complets"], a["n_tirets_decrits"]) for i, a in sorted(pcs.attendu.items())
          if a.get("n_tirets_decrits") is not None]
    out["tirets"] = {"methode": "tiret k = [phase + k (trait + vide), + trait] ∩ [0, L] hors interruptions (sémantique "
                                "de la description) ; complet si sa longueur ≥ trait − 1 mm ; n_tirets décrit = tirets complets",
                     "lignes": len(nt), "tirets_fabriques": sum(x[1] for x in nt), "tirets_complets": sum(x[2] for x in nt),
                     "tirets_partiels_aux_bouts": sum(x[1] - x[2] for x in nt),
                     "ecarts_complets_au_nombre_decrit": [[x[0], x[2], x[3]] for x in nt if x[2] != x[3]],
                     "ecart_longueur_axe_xodr_m": _stat([a["ecart_longueur_axe_m"] for a in pcs.attendu.values()
                                                          if "ecart_longueur_axe_m" in a], 6)}
    # ---- drapé : z de la marque − z du sol sous les centroïdes (échantillon déterministe)
    dzs, sup_cl = [], collections.defaultdict(float)
    for pc, r in fab.res:
        P, F = r["P"], r["F"]
        if not len(F):
            continue
        G = P[F].mean(axis=1)
        a_tri = aires_tri(P, F)
        for cl, a in zip(sol.cl[r["sup"]], a_tri):
            sup_cl[(pc["entite"], sol.classes[cl])] += float(a)
        k = np.arange(0, len(G), max(1, len(G) // 12))
        zs, _ = sol.z_sous(G[k, :2])
        dzs.append(np.c_[G[k, 2] - zs, np.full(len(k), pc["dz"])])
    d = np.vstack(dzs)
    ecart = d[:, 0] - d[:, 1]
    out["drape"] = {"methode": "centroïdes de triangles (1 sur 12 par pièce) : z marque − z sol composé (v2 puis v1) au "
                               "même point, moins dz de la classe ; enfouie si z marque < z sol",
                    "n": int(np.isfinite(ecart).sum()), "ecart_au_dz_mm": _stat(ecart * 1000, 3),
                    "marque_moins_sol_mm": _stat(d[:, 0] * 1000, 3),
                    "n_enfouis": int((d[:, 0] < 0).sum()), "n_sans_sol": int((~np.isfinite(d[:, 0])).sum())}
    # ---- support : part d'aire hors chaussée
    hors_ch = collections.defaultdict(dict)
    tot = collections.Counter()
    for (eid, cl), a in sup_cl.items():
        tot[eid] += a
    for (eid, cl), a in sorted(sup_cl.items()):
        src, nom = cl.split(":")
        roul = nom.startswith(CHAUSSEE_V1) if src == "v1" else nom in CHAUSSEE_V2
        if not roul and a / max(tot[eid], 1e-9) > 0.01:
            hors_ch[eid][cl] = round(a / tot[eid], 3)
    out["support"] = {"methode": "part de l'aire de chaque entité posée sur une classe de sol hors chaussée (v1 : "
                                 + ", ".join(CHAUSSEE_V1) + " ; v2 : enrobés de chaussée et de piste) au-delà de 1 %",
                      "aire_par_source_m2": {s: round(sum(a for (e, c), a in sup_cl.items() if c.startswith(s)), 3)
                                             for s in ("v2", "v1")},
                      "entites_hors_chaussee": {e: v for e, v in sorted(hors_ch.items())}}
    # ---- franchissements de bordure / ressauts : arête de marque à plus de 30 % de pente et 2 cm de dénivelé, ou
    # même point (x, y) à deux altitudes (bord de deux surfaces de sol disjointes, faces de bordure v1)
    pente_fr, dz_fr = FRANCHISSEMENT
    fr = collections.defaultdict(lambda: [0, 0.0])
    for pc, r in fab.res:
        P, F = r["P"], r["F"]
        if not len(F):
            continue
        E = np.unique(np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1), axis=0)
        dzv = np.abs(P[E[:, 0], 2] - P[E[:, 1], 2])
        L = np.hypot(*(P[E[:, 0], :2] - P[E[:, 1], :2]).T)
        raide = (dzv > dz_fr) & (dzv > pente_fr * L)
        cle = np.round(P[:, :2] / 1e-4).astype(np.int64)
        _, inv, cnt = np.unique(cle, axis=0, return_inverse=True, return_counts=True)
        doubles = cnt[inv.reshape(-1)] > 1
        if doubles.any():
            zz = collections.defaultdict(list)
            for k, z in zip(inv.reshape(-1)[doubles], P[doubles, 2]):
                zz[int(k)].append(z)
            saut = max((max(v) - min(v) for v in zz.values()), default=0.0)
        else:
            saut = 0.0
        if raide.any() or saut > dz_fr:
            fr[pc["entite"]][0] += int(raide.sum())
            fr[pc["entite"]][1] = max(fr[pc["entite"]][1], float(dzv[raide].max()) if raide.any() else 0.0, saut)
    out["franchissements"] = {"methode": f"arêtes de marque de pente > {pente_fr:.0%} et dénivelé > {dz_fr * 100:.0f} cm, ou sommets "
                                         f"superposés à des altitudes différentes de plus de {dz_fr * 100:.0f} cm (marque à cheval sur "
                                         "une bordure / un ressaut du sol) ; dénivelé maximal (m) ; bloquant",
                              "entites": {e: {"aretes_raides": v[0], "denivele_max_m": round(v[1], 3)}
                                          for e, v in sorted(fr.items())}}
    # ---- recouvrements entre entités au même dz (z-fighting) : après empilement (fab.empiler)
    out["empilement"] = fab.empilement
    out["recouvrements"] = recouvrements(fab)
    # ---- bordures v2 : marques sous la tête des bordures (emprise pilote)
    if desc_bordures is not None:
        out["bordures_v2"] = sous_bordures(fab, desc_bordures)
    out["coutures"] = coutures(fab)
    out["traversees_bordures"] = traversees_bordures(fab, desc_bordures)
    co = collections.defaultdict(float)
    for pc, r in fab.res:
        for k, v in r.get("coupe_m2", {}).items():
            co[k] += v
    out["coupes"] = {"methode": "aire retirée des marques (m²) : sous la tête des bordures v2, sous une marque prioritaire, "
                                "régions qui déchiraient une région mieux classée (marche du sol), éclats de coupe < 0,10 m",
                     "par_motif_m2": {k: round(v, 4) for k, v in sorted(co.items())},
                     "dechirures_m2": round(sum(r.get("dechirure_m2", 0.0) for _, r in fab.res), 4),
                     "eclats_m2": round(sum(r.get("eclats_m2", 0.0) for _, r in fab.res), 4),
                     "par_entite_m2": _coupes_par_entite(fab)}
    return out


def traversees_bordures(fab, desc_bordures=None):
    """Bords des marques (boucles de bord des triangles de chaque entité, soudure 1/100 mm) qui coupent une face verticale v1
    de plus de 2 cm (hors emprise pilote) ou une arête avant de bordure v2 hors abaissés franchissables (vue ≤ 0,02 m) :
    intersection propre de segments (paramètres dans ]0,001 ; 0,999[) ; bloquant."""
    FA, FB, _ = fab.faces
    segs_a, segs_b, noms = [FA], [FB], ["v1"] * len(FA)
    for B in desc_bordures or []:
        S = C.abscisses(B.P)
        ferme = [(a["s0"], a["s1"]) for a in B.p.get("abaisses", []) if (a.get("vue_m") if a.get("vue_m") is not None else 1) <= 0.02]
        ferme += [(it["s0"], it["s1"]) for it in B.p.get("intervalles", []) if (it.get("vue_m") or 0) <= 0.02]
        for k in range(len(B.P) - 1):
            sm = 0.5 * (S[k] + S[k + 1])
            if any(a <= sm <= b for a, b in ferme):
                continue
            segs_a.append(B.P[k:k + 1, :2])
            segs_b.append(B.P[k + 1:k + 2, :2])
            noms.append("v2:" + B.id)
    A = np.vstack(segs_a)
    Bv = np.vstack(segs_b)
    lo, hi = np.minimum(A, Bv) - 0.01, np.maximum(A, Bv) + 0.01
    par = collections.defaultdict(list)
    for pc, r in fab.res:
        if len(r["F"]):
            par[pc["entite"]].append(r)
    res = {}
    for eid, rs in sorted(par.items()):
        Ps, Fs, n = [], [], 0
        for r in rs:
            Ps.append(r["P"][:, :2])
            Fs.append(r["F"] + n)
            n += len(r["P"])
        P, F = np.vstack(Ps), np.vstack(Fs)
        k = np.round(P / 1e-5).astype(np.int64)
        _, inv = np.unique(k, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        Pu = np.zeros((inv.max() + 1, 2))
        Pu[inv] = P
        E = _bord(Pu, inv[F])
        if not len(E):
            continue
        Q0, Q1 = Pu[E[:, 0]], Pu[E[:, 1]]
        elo, ehi = np.minimum(Q0, Q1).min(axis=0), np.maximum(Q0, Q1).max(axis=0)
        cand = np.where((hi[:, 0] >= elo[0]) & (lo[:, 0] <= ehi[0]) & (hi[:, 1] >= elo[1]) & (lo[:, 1] <= ehi[1]))[0]
        touches = collections.Counter()
        for c in cand:
            a, b = A[c], Bv[c]
            rr = b - a
            sq = Q1 - Q0
            den = rr[0] * sq[:, 1] - rr[1] * sq[:, 0]
            okd = np.abs(den) > 1e-12
            w = Q0 - a
            t = np.where(okd, (w[:, 0] * sq[:, 1] - w[:, 1] * sq[:, 0]) / np.where(okd, den, 1), -1)
            u = np.where(okd, (w[:, 0] * rr[1] - w[:, 1] * rr[0]) / np.where(okd, den, 1), -1)
            hit = okd & (t > 0.001) & (t < 0.999) & (u > 0.001) & (u < 0.999)
            if hit.any():
                touches[noms[c]] += int(hit.sum())
        if touches:
            res[eid] = dict(sorted(touches.items()))
    return {"methode": "bords des marques contre les faces verticales v1 (> 2 cm, hors emprise pilote) et les arêtes avant v2 hors "
                       "abaissés franchissables : intersections propres ; bloquant", "entites": res}


def bloquants(fab, ctl):
    """Erreurs bloquantes de la fabrication -> liste de messages."""
    err = []
    for eid, v in ctl["franchissements"]["entites"].items():
        err.append(f"{eid} : franchissement ({v['aretes_raides']} arêtes raides, dénivelé {v['denivele_max_m']} m)")
    for eid, v in ctl["traversees_bordures"]["entites"].items():
        err.append(f"{eid} : bord de marque qui coupe une bordure {v}")
    # flèches et gabarits : jamais amputés de plus de COUPE_FLECHE_MAX de leur aire
    retire = collections.Counter()
    for pc, r in fab.res:
        retire[pc["entite"]] += sum(r.get("coupe_m2", {}).values()) + r.get("dechirure_m2", 0.0) + r.get("eclats_m2", 0.0) + r["hors_sol_m2"]
    for eid, att in sorted(fab.pc.attendu.items()):
        if "gabarit" in att and att.get("aire"):
            f = retire[eid] / att["aire"]
            if f > COUPE_FLECHE_MAX:
                err.append(f"{eid} : gabarit {att['gabarit']} coupé de {f:.1%} de son aire (> {COUPE_FLECHE_MAX:.0%})")
    if ctl["drape"]["n_enfouis"]:
        err.append(f"{ctl['drape']['n_enfouis']} points de marque sous le sol")
    if ctl["recouvrements"]["paires"]:
        err.append(f"recouvrements entre entités au même dz : {ctl['recouvrements']['paires'][:5]}")
    # correspondance v1 -> v2 : un MQ généré ou gardé doit être fabriqué ; un MQ gardé non fabriqué ne l'est pas
    corr = C.lire_geojson(fab.pc.dossier / "base/marquages_correspondance.geojson")
    avec = {pc["entite"] for pc, r in fab.res if len(r["F"])}
    for c in corr:
        q = c["properties"]
        if q["devenir"] in ("genere", "garde_simplifie") and q["entite"] not in avec:
            err.append(f"{q['id']} : devenir {q['devenir']} ({q['entite']}) sans aucun triangle fabriqué")
        if q["devenir"] == "garde_non_fabrique" and q["entite"] in avec:
            err.append(f"{q['id']} : devenir garde_non_fabrique mais {q['entite']} est fabriquée")
    return err


def _coupes_par_entite(fab):
    """{entité: {motif: m²}} des retraits de plus de 1 cm²."""
    d = collections.defaultdict(collections.Counter)
    for pc, r in fab.res:
        for k, v in r.get("coupe_m2", {}).items():
            d[pc["entite"]][k] += v
        d[pc["entite"]]["dechirure"] += r.get("dechirure_m2", 0.0)
        d[pc["entite"]]["eclats"] += r.get("eclats_m2", 0.0)
        d[pc["entite"]]["hors_sol"] += r["hors_sol_m2"]
    return {e: {k: round(v, 4) for k, v in sorted(c.items()) if v > 1e-4} for e, c in sorted(d.items())
            if sum(c.values()) > 1e-4}


def _bord(P, F):
    E = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    u, c = np.unique(E, axis=0, return_counts=True)
    return u[c == 1]


def hausdorff_fleches(fab):
    """Flèches : distance de Hausdorff (plan) entre le bord du maillage fabriqué (pièces réunies, soudure au 1/100 mm) et
    le polygone IISR posé (origine, cap, échelle) ; les flèches coupées (bordure, marque prioritaire, marche) sont
    signalées à part."""
    par = collections.defaultdict(list)
    coupees = set()
    for pc, r in fab.res:
        if pc["classe"] == "fleche" and len(r["F"]):
            par[pc["entite"]].append(r)
            if sum(r.get("coupe_m2", {}).values()) + r.get("dechirure_m2", 0.0) + r.get("eclats_m2", 0.0) > 1e-6:
                coupees.add(pc["entite"])
    det = []
    for eid in sorted(par):
        att = fab.pc.attendu[eid]
        Ps, Fs, n = [], [], 0
        for r in par[eid]:
            Ps.append(r["P"][:, :2])
            Fs.append(r["F"] + n)
            n += len(r["P"])
        P, F = np.vstack(Ps), np.vstack(Fs)
        k = np.round(P / 1e-5).astype(np.int64)
        _, inv = np.unique(k, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        Pu = np.zeros((inv.max() + 1, 2))
        Pu[inv] = P
        B = _bord(Pu, inv[F])
        A, Bb = Pu[B[:, 0]], Pu[B[:, 1]]
        T = [MC.poser(rr, att["origine"], att["cap"], att["echelle"]) for poly in MC.gabarit(att["gabarit"]) for rr in poly]
        TA = np.vstack([t for t in T])
        TB = np.vstack([np.roll(t, -1, axis=0) for t in T])
        d1, _, _ = C.distance_segments(TA, A, Bb)
        d2, _, _ = C.distance_segments(Pu[np.unique(B)], TA, TB)
        h = float(max(d1.max(), d2.max()))
        det.append([eid, att["gabarit"], round(h * 1000, 3), eid in coupees])
    ok = [d[2] for d in det if not d[3]]
    return {"methode": "Hausdorff plan (mm) entre le bord fabriqué et le polygone IISR posé ; [id, gabarit, mm, coupée]",
            "n": len(det), "max_mm_non_coupees": max(ok) if ok else None, "sup_2mm": [d for d in det if d[2] > 2.0], "detail": det}


def coutures(fab):
    """Sommets d'une même entité superposés en plan (1/10 mm) à des altitudes différentes de plus de 2 mm (déchirures)
    et T-jonctions de bord (sommet sur une arête de bord de la même pièce)."""
    dech = collections.defaultdict(float)
    tj = collections.Counter()
    par = collections.defaultdict(list)
    for pc, r in fab.res:
        if len(r["F"]):
            par[pc["entite"]].append(r)
    for eid, rs in sorted(par.items()):
        P = np.vstack([r["P"][np.unique(r["F"])] for r in rs])
        k = np.round(P[:, :2] / 1e-4).astype(np.int64)
        _, inv = np.unique(k, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        zmax = np.full(inv.max() + 1, -np.inf)
        zmin = np.full(inv.max() + 1, np.inf)
        np.maximum.at(zmax, inv, P[:, 2])
        np.minimum.at(zmin, inv, P[:, 2])
        g = float((zmax - zmin).max())
        if g > SEUIL_DECHIRURE:
            dech[eid] = round(g, 4)
        for r in rs:
            B = _bord(r["P"], r["F"])
            if not len(B):
                continue
            V = np.unique(B)
            a, b = r["P"][B[:, 0], :2], r["P"][B[:, 1], :2]
            ab = b - a
            L2 = np.maximum((ab * ab).sum(1), 1e-18)
            for v in V:
                q = r["P"][v, :2]
                t = ((q - a) * ab).sum(1) / L2
                d = np.hypot(*(a + t[:, None] * ab - q).T)
                if ((t > 1e-4) & (t < 1 - 1e-4) & (d < 2e-5) & (B[:, 0] != v) & (B[:, 1] != v)).any():
                    tj[eid] += 1
    return {"methode": f"sommets superposés en plan à des altitudes différentes de plus de {SEUIL_DECHIRURE * 1000:g} mm "
                       "(par entité : écart maximal, m) ; T-jonctions de bord (nombre de sommets)",
            "dechirures": dict(sorted(dech.items())), "t_jonctions": dict(sorted(tj.items()))}


def controle_points(fab, pts):
    """Gabarits posés par les points (p, q, s) comparés aux gabarits posés par la description (origine, cap, échelle) :
    écart plan maximal des sommets (m) et écart entre q et rpy_deg."""
    spec = fab.pc.spec["gabarits"]
    pose = {s["entite"]: s for s in fab.pc.symboles}
    ec, eq = [], []
    for p in pts:
        s = pose.get(p["x"]["entite"])
        if p["asset"] not in spec or s is None or p["x"].get("file") is not None:
            continue
        P = np.asarray(spec[p["asset"]]["polygone"], float)
        ref = MC.poser(P, s["o"], s["cap"], s["s"][0])
        R = K.rotation_rpy(p["rpy_deg"])
        Q = (R @ np.c_[P * p["s"][0], np.zeros(len(P))].T).T[:, :2] + np.asarray(p["p"][:2])
        ec.append(float(np.abs(Q - ref).max()))
        x, y, z, w = p["q"]
        Rq = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                       [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                       [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        eq.append(float(np.abs(Rq - R).max()))
    return {"methode": "sommets du gabarit transformés par (p, rpy, s) contre le gabarit posé par la description (plan) ; "
                       "q contre rpy", "n": len(ec), "ecart_plan_max_m": round(max(ec), 4) if ec else None,
            "ecart_q_rpy_max": round(max(eq), 6) if eq else None}


def recouvrements(fab, pas=0.02):
    """Triangles de marques d'entités différentes au même dz qui se recouvrent : points d'une grille de
    `pas` m à l'intérieur de chaque triangle testés contre les triangles des autres entités (index 1 m)."""
    tri, ent, dz = [], [], []
    for pc, r in fab.res:
        if len(r["F"]):
            tri.append(r["P"][r["F"]])
            ent += [pc["entite"]] * len(r["F"])
            dz += [pc["dz"]] * len(r["F"])
    Tm = np.vstack(tri)
    ent = np.array(ent)
    dz = np.array(dz)
    G = Tm.mean(axis=1)[:, :2]
    cel = np.floor(G / 1.0).astype(np.int64)
    cle = cel[:, 0] * 100000 + cel[:, 1]
    o = np.argsort(cle, kind="stable")
    cs = cle[o]
    paires = collections.Counter()
    # échantillons : centroïdes + milieux des sous-triangles
    for i in range(len(Tm)):
        lo = Tm[i, :, :2].min(axis=0)
        hi = Tm[i, :, :2].max(axis=0)
        ks = [(x, y) for x in range(int(math.floor(lo[0])) - 1, int(math.floor(hi[0])) + 2)
              for y in range(int(math.floor(lo[1])) - 1, int(math.floor(hi[1])) + 2)]
        cands = []
        for x, y in ks:
            k = x * 100000 + y
            a, b = np.searchsorted(cs, k, "left"), np.searchsorted(cs, k, "right")
            if b > a:
                cands.append(o[a:b])
        if not cands:
            continue
        cand = np.concatenate(cands)
        cand = cand[(ent[cand] != ent[i]) & (np.abs(dz[cand] - dz[i]) < 1e-4) & (cand > i)]
        if len(cand) == 0:
            continue
        q = Tm[i].mean(axis=0)[:2]
        A, B, Cc = Tm[cand, 0, :2], Tm[cand, 1, :2], Tm[cand, 2, :2]
        v0, v1, v2 = B - A, Cc - A, q - A
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1)
        d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1)
        den = d00 * d11 - d01 * d01
        lv = (d11 * d20 - d01 * d21) / den
        lw = (d00 * d21 - d01 * d20) / den
        ins = (lv > 1e-6) & (lw > 1e-6) & (1 - lv - lw > 1e-6)
        if ins.any():
            e1, e2 = Tm[i, 1, :2] - Tm[i, 0, :2], Tm[i, 2, :2] - Tm[i, 0, :2]
            a_i = 0.5 * abs(float(e1[0] * e2[1] - e1[1] * e2[0]))
            for j in cand[ins]:
                paires[tuple(sorted((ent[i], ent[j])))] += a_i
    return {"methode": "centroïde de chaque triangle de marque testé contre les triangles des autres entités au même dz "
                       "(aire du triangle comptée par paire)",
            "paires": [[a, b, round(v, 4)] for (a, b), v in sorted(paires.items()) if v > 1e-4],
            "aire_totale_m2": round(sum(paires.values()), 4)}


def sous_bordures(fab, bordures):
    """Marques drapées sur le sol v2 dont des sommets tombent sous la tête d'une bordure (côté haut de
    l'arête avant, jusqu'à la base du profil) : enfouies sous l'élément posé."""
    specs = K.Specs()
    zone = []
    for B in bordures:
        prof = B.p.get("intervalles", [{}])[0].get("profil", "T2")
        try:
            base, _ = specs.dims(prof)
        except Exception:
            base = 0.15
        zone.append((B, base))
    touche = collections.Counter()
    for pc, r in fab.res:
        if not len(r["F"]):
            continue
        v2 = fab.sol.src[r["sup"]] == 0
        if not v2.any():
            continue
        Q = r["P"][np.unique(r["F"][v2])][:, :2]
        for B, base in zone:
            lo, hi = B.P.min(axis=0) - 0.5, B.P.max(axis=0) + 0.5
            m = (Q[:, 0] > lo[0]) & (Q[:, 0] < hi[0]) & (Q[:, 1] > lo[1]) & (Q[:, 1] < hi[1])
            if not m.any():
                continue
            s, dl, cote = C.projeter(B.P, Q[m])
            S = C.abscisses(B.P)
            dedans = (cote > 0) & (dl > 0.005) & (dl < base - 0.002) & (s > 0.01) & (s < S[-1] - 0.01)
            if dedans.any():
                touche[(pc["entite"], B.id)] += int(dedans.sum())
    return {"methode": "sommets des marques posées sur le sol v2 à gauche (côté haut) de l'arête avant d'une bordure "
                       "décrite, entre 5 mm et la base du profil",
            "paires": [[e, b, n] for (e, b), n in sorted(touche.items())]}


# =========================================================================== orchestration
def fichiers_sortie(sortie):
    s = Path(sortie)
    return [s / "marquages.usda", s / "marquages_pilote.usda", s / "marquages_prototypes.usda",
            s / "points/marquages_symboles.json"]


def fabriquer(sortie=K.FABRIQUE, description=K.DESCRIPTION, log=journal, sol_dossier=None, canon=K.FABRIQUE):
    """Fabrique les marquages dans `sortie` (sol lu dans sol_dossier, défaut : sortie) ; renvoie le manifeste."""
    t0 = time.time()
    sortie = Path(sortie)
    fab = Fabrication(description, sol_dossier or sortie, log)
    canon = Path(canon)
    log("pj_marquages : écriture")
    c_site = fab.ecrire_usd(sortie / "marquages.usda",
                            "Marquages v2 du site (pj_marquages.py) : géométrie exacte construite depuis la description "
                            "(famille marquages, schéma 0.2) et les gabarits IISR, triangulée (Triangulate 2D) et drapée "
                            "sur le sol (v2 dans l'emprise pilote, v1 ailleurs) à +3 mm (surface colorée +2,5 mm, "
                            "fantômes +2 mm). Un maillage par classe de peinture peinture_<couleur>_u<usure>.",
                            ref=canon / "marquages.usda")
    pilote = {pc["entite"] for pc, r in fab.res if len(r["F"]) and (fab.sol.src[r["sup"]] == 0).any()}
    c_pil = fab.ecrire_usd(sortie / "marquages_pilote.usda",
                           "Marquages v2 de la zone pilote (pj_marquages.py) : entités de marquages.usda dont une partie est "
                           "posée sur le sol v2 (fabrique/sol.usda), entières (y compris leur partie sur le sol v1) ; remplace "
                           "les zébras provisoires de pj_decals dans rendu_pilote.usda.",
                           filtre=lambda pc, r: np.full(len(r["F"]), pc["entite"] in pilote), ref=canon / "marquages_pilote.usda")
    protos = fab.ecrire_prototypes(sortie / "marquages_prototypes.usda")
    pts = fab.points()
    K.ecrire_points(sortie / "points/marquages_symboles.json", "marquages_symboles", pts, fab.pc.hash, {
        "repere": "local (L93 − O, z = NGF − 216,30), m, Z haut ; p = origine du gabarit sur le sol + 3 mm",
        "convention_rpy": "rpy_deg = [r, p, y] ZYX intrinsèques, R = Rz(y)·Ry(p)·Rx(r) (pj_commun.rotation_rpy) ; "
                          "y = cap − 90° (X du prototype = droite du gabarit, Y = sens de circulation) ; r, p : plan du "
                          "sol sous la boîte du gabarit ; UE : Rotator(roll = r, pitch = −p, yaw = −y)",
        "asset": "nom de gabarit de assets/specs/marquages_geometrie.json (TD, TAD, TAG, TD_TAD, TD_TAG, VELO, "
                 "PAVE_CHRONOVELO, CARRE_TRAVERSEE_CYCLABLE...) ou forme : RECT_UNITE, TRIANGLE_UNITE, DISQUE_UNITE "
                 "(s = dimensions), CHEVRON_b<branche mm>_o<ouverture 0,1°>_t<trait mm> ; prototypes à plat dans "
                 "marquages_prototypes.usda ; A_VECTORISER_* : boîte seulement (pictogramme à vectoriser)",
        "s": "échelle (gabarit) ou dimensions [x, y, 1] en m (formes unitaires)",
        "cd": "[couverture, usure (0, 1, 2, 3, 4 = F)]",
        "doublon": "les mêmes symboles sont aussi dans marquages.usda (maillages drapés) : en UE, poser soit les "
                   "maillages, soit les décalques"})
    log("pj_marquages : contrôles")
    try:
        desc_b = K.Description(description).bordures
    except Exception as e:                                   # description sol absente : contrôle omis
        log("   bordures v2 non lues :", e)
        desc_b = None
    ctl = controles(fab, desc_b)
    ctl["points_symboles"] = controle_points(fab, pts)
    ctl["bloquants"] = bloquants(fab, ctl)
    # filet de sécurité : découpe par une marque prioritaire (la description ne laisse plus de recouvrement) -> avertissement
    #   (fantômes, surface colorée et zones hachurées sous les marques, lignes jointives : recouvrements permis, comptés à part)
    cl = {f["properties"]["id"]: (f["properties"]["classe"], f["properties"]["type"]) for f in fab.pc.features}
    permis_ = lambda e: cl[e][0] in ("fantome", "ligne") or cl[e][1] in ("surface_coloree", "hachures")
    prio = {e: v["marque_prioritaire"] for e, v in sorted(ctl["coupes"]["par_entite_m2"].items()) if v.get("marque_prioritaire", 0) > 1e-4}
    ctl["avertissements"] = [f"{e} : {a} m² retirés sous une marque prioritaire (recouvrement résiduel de la description)"
                             for e, a in prio.items() if not permis_(e)]
    ctl["coupes"]["sous_marque_prioritaire_permis_m2"] = {e: a for e, a in prio.items() if permis_(e)}
    for x in ctl["bloquants"]:
        log("   BLOQUANT :", x)
    comptes = comptes_fab(fab)
    avec = {pc["entite"] for pc, r in fab.res if len(r["F"])}
    deja = {x["id"] for x in fab.pc.non_fabriques}
    hors = collections.Counter()
    for pc, r in fab.res:
        hors[pc["entite"]] += r["hors_sol_m2"] + sum(r.get("coupe_m2", {}).values()) + r.get("dechirure_m2", 0.0) + r.get("eclats_m2", 0.0)
    for f in fab.pc.features:
        i = f["properties"]["id"]
        if i not in avec and i not in deja:
            fab.pc.non_fabriques.append({"id": i, "raison": "aucun triangle : hors du sol modélisé ou entièrement coupée "
                                                            f"({hors.get(i, 0.0):.3f} m² retirés)"})
    fab.pc.non_fabriques.sort(key=lambda x: x["id"])
    entrees = {K.rel(f): K.sha256(f) for f in [fab.pc.fichier, Path(description) / "description_scene_v2.json", SPEC,
                                               PEINTURE, X.XODR, (sol_dossier or sortie) / SOL_V2,
                                               (sol_dossier or sortie) / MASQUE_V1, V1_RACINE]
               + sorted((K.PAQUET_V1 / "layers").glob("*"))}
    scripts = {f.name: K.sha256(f) for f in [ICI / "pj_marquages.py", ICI / "pj_marquages_materiaux.py"]
               + [K.RACINE / "recon/pcg/decrire" / n for n in ("marquages_commun.py", "marquages_lignes.py", "marquages_symboles.py",
                                                            "marquages_glyphes.py", "marquages_gam.py", "marquages_ortho.py",
                                                            "xodr_echantillonne.py")]}
    sorties = {f.relative_to(sortie).as_posix(): K.sha256(f) for f in fichiers_sortie(sortie)}
    fab.pc.non_fabriques = [{k: v for k, v in x.items() if k != "decrit_non_fabrique"} for x in fab.pc.non_fabriques]
    man = {"schema": "pj_manifest_marquages/0.1", "version": VERSION, "houdini": hou.applicationVersionString(),
           "description": {"hash_marquages": fab.pc.hash, "schema": fab.pc.manifeste.get("schema")},
           "regles": {"dz_m": DZ, "troncon_max_m": TRONCON_MAX, "tolerance_plan_m": TOL_PLAN, "onglet_max": ONGLET_MAX,
                      "soudure_m": SOUDURE, "materiaux": MM.doc_recette()},
           "entrees": entrees, "scripts": scripts, "comptes": comptes, "prototypes": protos,
           "maillages": {"site": c_site, "pilote": c_pil}, "points_symboles": len(pts),
           "points_poses_bornees": {"regle": f"pente du plan de pose bornée à {PENTE_MAX} (marche du sol sous le symbole)",
                                    "entites": fab.poses_bornees},
           "non_fabriques": fab.pc.non_fabriques, "controles": ctl, "sorties": sorties,
           "hash_sorties": hashlib.sha256("".join(f"{k}:{v}\n" for k, v in sorted(sorties.items())).encode()).hexdigest()}
    K.ecrire_json(sortie / "marquages_manifest.json", man)
    log(f"pj_marquages : terminé en {time.time() - t0:.0f} s ; hash des sorties {man['hash_sorties'][:16]}")
    return man


def comptes_fab(fab):
    ent = collections.Counter()
    pcs = collections.Counter()
    tris = collections.Counter()
    aire_ = collections.Counter()
    vus = set()
    for pc, r in fab.res:
        k = f"{pc['classe']}/{pc['type']}"
        if pc["entite"] not in vus and len(r["F"]):
            ent[k] += 1
            vus.add(pc["entite"])
        pcs[k] += 1
        tris[k] += int(len(r["F"]))
        if len(r["F"]):
            P, F = r["P"], r["F"]
            aire_[k] += float(aires_tri(P, F).sum())
    modes = collections.Counter(r.get("mode", "exact") for _, r in fab.res)
    return {"entites_decrites": len(fab.pc.features), "entites_fabriquees": len(vus),
            "modes_triangulation": dict(sorted(modes.items())),
            "pieces": sum(pcs.values()), "triangles": sum(tris.values()),
            "par_type": {k: {"entites": ent[k], "pieces": pcs[k], "triangles": tris[k], "aire_m2": round(aire_[k], 3)}
                         for k in sorted(pcs)},
            "aire_totale_m2": round(sum(aire_.values()), 3)}


def main():
    ap = argparse.ArgumentParser(description="Fabrication des marquages v2 (hython)")
    ap.add_argument("--sortie", default=str(K.FABRIQUE))
    ap.add_argument("--description", default=str(K.DESCRIPTION))
    ap.add_argument("--sol", help="dossier fabrique/ où lire sol.usda et le masque v1 (défaut : --sortie, sinon fabrique/)")
    ap.add_argument("--verifier-determinisme", action="store_true")
    a = ap.parse_args()
    executer(a.sortie, a.description, a.sol, a.verifier_determinisme)


def executer(sortie, description, sol=None, verifier=False):
    sortie = Path(sortie).resolve()
    sol_d = Path(sol).resolve() if sol else (sortie if (sortie / SOL_V2).exists() else K.FABRIQUE)
    man = fabriquer(sortie, description, sol_dossier=sol_d)
    if verifier:
        import shutil
        import subprocess
        verif = sortie / "_verif_marquages"
        t1 = time.time()
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--sortie", str(verif), "--description",
                            str(description), "--sol", str(sol_d)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace")
        autre = K.lire_json(verif / "marquages_manifest.json") if (verif / "marquages_manifest.json").exists() else {"sorties": {}}
        diff = sorted(k for k in set(man["sorties"]) | set(autre["sorties"]) if man["sorties"].get(k) != autre["sorties"].get(k))
        cm = (K.sha256(sortie / "marquages_manifest.json") == K.sha256(verif / "marquages_manifest.json")) \
            if (verif / "marquages_manifest.json").exists() else False
        man["determinisme"] = {"methode": "deuxième exécution dans un autre processus hython ; sha256 fichier par fichier",
                               "fichiers_compares": len(man["sorties"]), "differences": diff,
                               "manifeste_identique": cm, "identique_a_l_octet": not diff and r.returncode in (0, 2),
                               "duree_s": round(time.time() - t1)}
        if r.returncode not in (0, 2):
            man["determinisme"]["erreur"] = r.stderr[-2000:]
        K.ecrire_json(sortie / "marquages_manifest.json", man)
        shutil.rmtree(verif, ignore_errors=True)
        journal(f"déterminisme : {len(man['sorties'])} fichiers comparés, {len(diff)} différence(s)")
    if man["controles"]["bloquants"]:
        journal(f"ÉCHEC : {len(man['controles']['bloquants'])} contrôle(s) bloquant(s) (marquages_manifest.json controles.bloquants)")
        sys.exit(2)
    return man


if __name__ == "__main__":
    main()
