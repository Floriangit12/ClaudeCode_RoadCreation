"""Carte sémantique du site entier pour le solveur de cohérence (repère local).

Raster 5 cm (emprise LiDAR 300 × 300 m) pour des requêtes ponctuelles rapides, plus vecteurs :
- classe de base par ordre de priorité : îlots v2 > surfaces v2 (zone pilote) > bâtiments
  (batiments_local, seulement sur « autre » ou vide) > surfaces_2026 v1 ;
- zones dérivées (masque de bits) choisies selon `vocabulaire.precedence_zones` des règles :
  passage piéton et traversée cyclable (marquages v2), îlot peint (hachures, aplats, terre-plein
  peint v2), voie bus et bande cyclable (lanes_2026 sur chaussée), abaissé de traversée, palier et
  BEV (abaissés v2, sinon déduits des passages : profondeur de rampe 1,20 m par défaut), clôtures ;
- bordures orientées (côté haut à gauche) : v2 dans la zone pilote, ailleurs lignes de
  relief/bordures_hauteurs dédoublonnées (bordures.apparier) et orientées par le MNT 2026
  (bordures.cote_haut) ; requête (bordure de référence, s, t signé : t > 0 côté haut) ;
- voies OpenDRIVE (lanes_2026) : voie sous un point ou la plus proche, sens de circulation
  (voie < 0 dans le sens de la ligne de référence, voie > 0 en sens inverse) ;
- largeur libre de cheminement par coupe perpendiculaire à la bordure (PMR-01).

Aucune écriture dans le paquet ni dans la description de base : sorties sous
recon/out/paquet_jardin/v2/description/coherence/carte/.
"""
import functools
import hashlib
import math

import numpy as np
from PIL import Image, ImageDraw

import contexte as ctx
from commun import (DONNEES, MNT, RACINE, SORTIE, abscisses, aretes, arrondi, coords_geojson,
                    couper_polyligne, dans_polygone, distance_segments, ecrire_geojson, ecrire_json,
                    lire_geojson, lire_json, normale_gauche, point_a, repere, sous_polyligne)
from commun import projeter as projeter_polyligne

# --------------------------------------------------------------------------- constantes
EMPRISE = (-150.0, -150.0, 150.0, 150.0)      # x0, y0, x1, y1 local (emprise LiDAR / surfaces v1)
PAS = 0.05
N = int(round((EMPRISE[2] - EMPRISE[0]) / PAS))
COHERENCE = SORTIE / "coherence"
CARTE = COHERENCE / "carte"
BASE_V2 = SORTIE / "base"
REGLES = RACINE / "assets/specs/regles_implantation.json"

CLASSES = ["", "chaussee", "trottoir", "ilot", "piste_cyclable", "quai_bus", "espace_vert",
           "terre_plein_vegetal", "parking", "acces_riverain", "batiment", "autre"]
CID = {c: i for i, c in enumerate(CLASSES)}
SRC_BASE = ["", "surfaces_2026", "surfaces_v2", "ilots_v2", "batiments_local"]
# bits de zones dérivées
ZONES = ["passage_pietons", "traversee_cyclable", "bev", "abaisse_traversee", "palier_abaisse",
         "ilot_peint", "voie_bus", "bande_cyclable", "stationnement_chaussee", "cloture"]
ZBIT = {z: 1 << i for i, z in enumerate(ZONES)}
CIRCULEES = {"chaussee", "voie_bus", "bande_cyclable", "piste_cyclable", "passage_pietons",
             "traversee_cyclable", "parking", "acces_riverain", "stationnement_chaussee"}
VEHICULES_BAS = {"chaussee", "piste_cyclable", "parking", "acces_riverain"}
PIETONNES = {"trottoir", "quai_bus", "ilot", "acces_riverain"}
PROFONDEUR_RAMPE_DEFAUT = 1.20     # GEN-02 (abaissés v2 absents hors zone pilote)
LARGEUR_PALIER = 0.80
COULEURS = {"": (0, 0, 0), "chaussee": (90, 90, 90), "trottoir": (200, 190, 170), "ilot": (230, 160, 90),
            "piste_cyclable": (190, 60, 60), "quai_bus": (150, 120, 200), "espace_vert": (90, 170, 80),
            "terre_plein_vegetal": (60, 130, 60), "parking": (120, 120, 150), "acces_riverain": (170, 150, 120),
            "batiment": (40, 40, 60), "autre": (140, 140, 110)}


def _hash_fichiers(chemins):
    h = hashlib.sha256()
    for c in chemins:
        h.update(open(c, "rb").read())
    return h.hexdigest()[:16]


def azimut(v):
    """Azimut (deg, nord grille = 0, horaire) d'un vecteur (vx, vy)."""
    return math.degrees(math.atan2(v[0], v[1])) % 360.0


def ecart_angle(a, b):
    """|a − b| ramené dans [0, 180]."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _polys_locaux(geom):
    t = geom["type"]
    polys = [geom["coordinates"]] if t == "Polygon" else geom["coordinates"] if t == "MultiPolygon" else []
    out = []
    for p in polys:
        rs = []
        for r in p:
            a = np.asarray(r, dtype=np.float64)[:, :2]
            if len(a) > 1 and np.allclose(a[0], a[-1]):
                a = a[:-1]
            if len(a) >= 3:
                rs.append(a)
        if rs:
            out.append(rs)
    return out


# --------------------------------------------------------------------------- raster
class Grille:
    """Raster local 5 cm : pixel (r, c) centré en (x0 + (c + 0,5)·pas, y1 − (r + 0,5)·pas)."""

    def __init__(self):
        self.x0, self.y0, self.x1, self.y1 = EMPRISE
        self.pas, self.n = PAS, N

    def rc(self, xy):
        xy = np.atleast_2d(np.asarray(xy, dtype=np.float64))
        c = np.floor((xy[:, 0] - self.x0) / self.pas).astype(np.int64)
        r = np.floor((self.y1 - xy[:, 1]) / self.pas).astype(np.int64)
        ok = (c >= 0) & (c < self.n) & (r >= 0) & (r < self.n)
        return np.clip(r, 0, self.n - 1), np.clip(c, 0, self.n - 1), ok

    def pil(self, xy):
        """Coordonnées PIL (centre de pixel aux entiers) d'un anneau local."""
        xy = np.asarray(xy, dtype=np.float64)
        return [((x - self.x0) / self.pas - 0.5, (self.y1 - y) / self.pas - 0.5) for x, y in xy]

    def masque_polygone(self, poly):
        """(r0, c0, masque bool) du polygone (anneau extérieur + trous) dans sa boîte englobante."""
        ext = poly[0]
        x0, y0 = ext.min(axis=0)
        x1, y1 = ext.max(axis=0)
        c0 = max(int(math.floor((x0 - self.x0) / self.pas)) - 1, 0)
        c1 = min(int(math.ceil((x1 - self.x0) / self.pas)) + 1, self.n)
        r0 = max(int(math.floor((self.y1 - y1) / self.pas)) - 1, 0)
        r1 = min(int(math.ceil((self.y1 - y0) / self.pas)) + 1, self.n)
        if c1 <= c0 or r1 <= r0:
            return None
        im = Image.new("L", (c1 - c0, r1 - r0), 0)
        dr = ImageDraw.Draw(im)
        for k, r in enumerate(poly):
            pts = [(u - c0, v - r0) for u, v in self.pil(r)]
            if len(pts) >= 3:
                dr.polygon(pts, fill=0 if k else 1, outline=0 if k else 1)
        return r0, c0, np.asarray(im, dtype=bool)


# --------------------------------------------------------------------------- bordures site
def _bordures_site(mnt):
    """Bordures orientées (côté haut à gauche) sur tout le site : v2 dans la zone pilote,
    relief/bordures_hauteurs dédoublonnées et orientées ailleurs. Cache : carte/bordures_site.geojson."""
    import bordures as B
    sources = [DONNEES / "relief/bordures_hauteurs.geojson", BASE_V2 / "bordures.geojson",
               RACINE / "recon/pcg/zone_pilote.geojson"]
    cle = _hash_fichiers(sources) + "-v2"
    cache = CARTE / "bordures_site.geojson"
    if cache.exists():
        d = lire_json(cache)
        if d.get("description_v2", {}).get("hash_sources") == cle:
            return [dict(id=f["properties"]["id"], P=repere(np.asarray(f["geometry"]["coordinates"])[:, :2]),
                         **{k: v for k, v in f["properties"].items() if k != "id"}) for f in d["features"]]
    import collections
    par = collections.defaultdict(list)
    for f in lire_geojson(DONNEES / "relief/bordures_hauteurs.geojson"):
        par[f["properties"]["ligne"]].append(f)
    lignes = {n: B.Ligne(n, par[n]) for n in sorted(par)}

    def modifiee(lg, sm):
        """Bordure reconstruite par les travaux : créée après 2021, modifiée 2025 ou issue du plan projet."""
        st = lg.attr(sm, "statut")
        cr = lg.attr(sm, "creee_apres_2021")
        src = lg.attr(sm, "source")
        return bool(np.mean([a == "modifiee_2025" or bool(b) or "plan projet" in c for a, b, c in zip(st, cr, src)]) >= 0.5)
    morceaux, _ = B.apparier(lignes, mnt)
    zone = ctx.zone_pilote()["anneau"]
    out = []
    compte = collections.Counter()
    for n, s0, s1, dbl in morceaux:
        lg = lignes[n]
        P0 = sous_polyligne(lg.P, s0, s1)
        sens, crit, dz = B.cote_haut(P0, lg, lambda s, a=s0: a + s, 1, mnt)
        P1 = P0 if sens > 0 else P0[::-1]
        L1 = float(abscisses(P1)[-1])
        dedans = couper_polyligne(P1, [zone])
        bornes, cur = [], 0.0
        for a, b in dedans:
            if a - cur >= 0.5:
                bornes.append((cur, a))
            cur = b
        if L1 - cur >= 0.5:
            bornes.append((cur, L1))
        src = lg.source.lower()
        code = "gam" if src.startswith("gam") else "pcrs2019" if src.startswith("pcrs") else "plan2025"
        sm = np.linspace(s0, s1, max(2, int(s1 - s0) + 1))
        trav = float(np.mean(lg.attr(sm, "zone_travaux_2025")))
        for a, b in bornes:
            P = sous_polyligne(P1, a, b)
            compte[n] += 1
            out.append(dict(id=f"KS-{n:04d}-{compte[n]}", P=P, source=code, ligne=n,
                            zone_travaux_2025=bool(trav >= 0.5), modifiee_2025=modifiee(lg, sm),
                            orientation=crit, dz_mnt=round(float(dz), 3)))
    for f in lire_geojson(BASE_V2 / "bordures.geojson"):
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"], dtype=float)[:, :2])
        lg = lignes.get(p["source"].get("ligne"))
        s_src = p["source"].get("s_src_m") or [0.0, lg.longueur if lg else 0.0]
        mod = modifiee(lg, np.linspace(min(s_src), max(s_src), 8)) if lg is not None else bool(p.get("zone_travaux_2025"))
        out.append(dict(id=p["id"], P=P, source=p["prov"]["geometrie"]["src"], ligne=p["source"].get("ligne"),
                        zone_travaux_2025=bool(p.get("zone_travaux_2025")), modifiee_2025=mod, orientation="v2",
                        dz_mnt=None, abaisses=p.get("abaisses") or []))
    out.sort(key=lambda k: k["id"])
    feats = [{"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(repere(k["P"], "l93"))},
              "properties": {"id": k["id"], **{c: v for c, v in k.items() if c not in ("id", "P")}}} for k in out]
    ecrire_geojson(cache, feats, "bordures_site", {"hash_sources": cle, "orientation": "côté haut à gauche (t > 0)",
                                                    "sources": [str(s.relative_to(RACINE).as_posix()) for s in sources]})
    return out


# --------------------------------------------------------------------------- carte
class Carte:
    def __init__(self, verbeux=True):
        self._patch_contexte()
        self.g = Grille()
        self.mnt = MNT()
        self.regles = lire_json(REGLES)
        self.precedence = self.regles["vocabulaire"]["precedence_zones"]
        self.log = print if verbeux else (lambda *a, **k: None)
        self.base = np.zeros((N, N), np.uint8)
        self.src = np.zeros((N, N), np.uint8)
        self.faible = np.zeros((N, N), bool)          # classe de base peu sûre (raster, a priori, 2025)
        self.zones = np.zeros((N, N), np.uint16)
        self.zone_defaut = np.zeros((N, N), bool)     # zone dérivée à géométrie par défaut (a priori)
        self.notes = []
        self._base()
        self._lanes()
        self._marquages()
        self.bordures = _bordures_site(self.mnt)
        self._indexer_bordures()
        self._abaisses()
        self._clotures()
        self.log(f"carte : {len(self.bordures)} bordures, {len(self.lanes)} voies, {len(self.passages)} passages")

    # ---- contexte site entier (contexte.py est limité à la zone pilote pour les convertisseurs)
    @staticmethod
    def _patch_contexte():
        ctx.dans_emprise = lambda pts, marge=0.0: np.ones(len(np.atleast_2d(pts)), bool)
        ctx.touche_emprise = lambda polys, marge=0.0: True
        for f in (ctx.surfaces_v1, ctx.zones_relief, ctx.passages_pietons, ctx.mobilier, ctx.arbres,
                  ctx.osm_traversees, ctx.chartieres_gam, ctx.acces_riverains, ctx.caniveaux_gam):
            f.cache_clear()

    def _peindre(self, poly, valeur, cible, src=None, si=None, faible=None):
        m = self.g.masque_polygone(poly)
        if m is None:
            return 0
        r0, c0, mk = m
        sl = (slice(r0, r0 + mk.shape[0]), slice(c0, c0 + mk.shape[1]))
        if si is not None:
            mk = mk & si(sl)
        cible[sl][mk] = valeur
        if src is not None:
            self.src[sl][mk] = src
        if faible is not None:
            self.faible[sl][mk] = faible
        return int(mk.sum())

    def _bit(self, poly, bit, si=None, defaut=False):
        m = self.g.masque_polygone(poly)
        if m is None:
            return
        r0, c0, mk = m
        sl = (slice(r0, r0 + mk.shape[0]), slice(c0, c0 + mk.shape[1]))
        if si is not None:
            mk = mk & si(sl)
        self.zones[sl][mk] |= bit
        if defaut:
            self.zone_defaut[sl][mk] = True

    def _base(self):
        n1 = 0
        self.surfaces_v1 = []
        for f in lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"):
            p = f["properties"]
            faible = "raster" in p["source"] or p["etat"] == "modifie_2025"
            for poly in _polys_locaux(f["geometry"]):
                pl = [repere(r) for r in poly]
                n1 += self._peindre(pl, CID[p["classe"]], self.base, 1, faible=faible)
                self.surfaces_v1.append(dict(id=p["id"], classe=p["classe"], etat=p["etat"], source=p["source"], poly=pl,
                                             bmin=pl[0].min(0), bmax=pl[0].max(0)))
        vide = lambda sl: np.isin(self.base[sl], [0, CID["autre"]])
        for f in lire_geojson(DONNEES / "objets/batiments_local.geojson"):
            for poly in _polys_locaux(f["geometry"]):
                self._peindre(poly, CID["batiment"], self.base, 4, si=vide, faible=False)
        self.peint_v2 = []
        for f in lire_geojson(BASE_V2 / "surfaces.geojson"):
            p = f["properties"]
            for poly in _polys_locaux(f["geometry"]):
                pl = [repere(r) for r in poly]
                self._peindre(pl, CID[p["classe"]], self.base, 2,
                              faible=bool(p.get("limite_raster")) or p.get("etat_v1") == "modifie_2025")
                if p.get("sous_classe") == "terre_plein_peint":
                    self.peint_v2.append(pl)
        self.ilots_v2 = []
        for f in lire_geojson(BASE_V2 / "ilots.geojson"):
            p = f["properties"]
            for poly in _polys_locaux(f["geometry"]):
                pl = [repere(r) for r in poly]
                self._peindre(pl, CID["ilot"], self.base, 3, faible=False)
                self.ilots_v2.append(dict(id=p["id"], type=p.get("type"), poly=pl,
                                          nez=repere(np.array(p["nez"]["position"])[None])[0] if p.get("nez") else None,
                                          objets_portes=p.get("objets_portes") or []))

    def _lanes(self):
        self.refs = {}
        self.lanes = []
        for f in lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
            p, g = f["properties"], f["geometry"]
            if p.get("type") == "reference" and g["type"] == "LineString":
                self.refs.setdefault(p["route"], []).append(repere(np.asarray(g["coordinates"])[:, :2]))
        for f in lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
            p, g = f["properties"], f["geometry"]
            if g["type"] != "Polygon" or p.get("type") not in ("driving", "biking", "bus"):
                continue
            for poly in _polys_locaux(g):
                pl = [repere(r) for r in poly]
                self.lanes.append(dict(route=p["route"], voie=p["voie"], type=p["type"], nom=p.get("nom"),
                                       jonction=bool(p.get("jonction")), section_s=p.get("section_s"), poly=pl,
                                       bmin=pl[0].min(0), bmax=pl[0].max(0)))
                chaussee = lambda sl: self.base[sl] == CID["chaussee"]
                if p["type"] == "bus":
                    self._bit(pl, ZBIT["voie_bus"], si=chaussee)
                elif p["type"] == "biking":
                    self._bit(pl, ZBIT["bande_cyclable"], si=chaussee)
        self.lanes.sort(key=lambda l: (l["route"], l["voie"], l["section_s"] or 0.0))

    def _marquages(self):
        """Passages piétons (zébras v2), traversées cyclables, îlots peints, stationnement."""
        circ = lambda sl: np.isin(self.base[sl], [CID[c] for c in ("chaussee", "piste_cyclable", "parking",
                                                                   "acces_riverain", "")])
        chaussee = lambda sl: self.base[sl] == CID["chaussee"]       # zone dérivée « dans chaussee »
        self.passages = []
        self.marques = []          # (id, zone, état, anneau) : marquages datés (neuf_2025 = posé après travaux)
        cyc = []
        self.lignes_continues = []
        self.lignes_effet = []
        for f in lire_geojson(BASE_V2 / "marquages.geojson"):
            p, g = f["properties"], f["geometry"]
            if p["classe"] == "passage" and p["type"] == "zebra" and g["type"] == "LineString":
                A = repere(np.asarray(g["coordinates"])[:, :2])
                a, b = A[0], A[-1]
                u = (b - a) / max(np.hypot(*(b - a)), 1e-9)
                v = np.array([-u[1], u[0]])
                w = float(p.get("longueur_bande_m") or 2.5) / 2
                lb = float(p.get("largeur_bande_m") or 0.5) / 2
                a2, b2 = a - u * lb, b + u * lb
                anneau = np.array([a2 - v * w, b2 - v * w, b2 + v * w, a2 + v * w])
                self._bit([anneau], ZBIT["passage_pietons"], si=circ)
                self.passages.append(dict(id=p["id"], a=a2, b=b2, u=u, v=v, demi_largeur=w, anneau=anneau,
                                          branche=p.get("branche"), groupe=p.get("groupe"), etat=p.get("etat")))
                self.marques.append((p["id"], "passage_pietons", p.get("etat"), anneau))
            elif p["classe"] == "passage" and p["type"] == "traversee_cyclable":
                lc = [repere(np.asarray(c)[:, :2]) for c in (g["coordinates"] if g["type"] == "MultiLineString"
                                                              else [g["coordinates"]])]
                P = np.vstack(lc)
                if len(P) >= 2:
                    cyc.append((p["id"], P))
                    self.marques.append((p["id"], "traversee_cyclable", p.get("etat"), _enveloppe_tampon(P, 0.30)))
            elif p["classe"] == "zone" and p["type"] in ("hachures", "aplat", "chevron"):
                for poly in _polys_locaux(g):
                    self._bit([repere(r) for r in poly], ZBIT["ilot_peint"], si=chaussee)
            elif p["classe"] == "zone" and p["type"] == "t_stationnement":
                pass
            elif p["classe"] == "ligne" and p["type"] == "continue" and g["type"] in ("LineString", "MultiLineString"):
                for c in (g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]):
                    self.lignes_continues.append((p["id"], repere(np.asarray(c)[:, :2])))
            elif p["classe"] == "transversale" and p["type"] == "effet_feux":
                Pl = repere(np.asarray(g["coordinates"])[:, :2])
                self.lignes_effet.append(dict(id=p["id"], P=Pl, branche=p.get("branche")))
                self.marques.append((p["id"], "ligne_effet_feux", p.get("etat"), _enveloppe_tampon(Pl, 0.10)))
        for pl in self.peint_v2:
            self._bit(pl, ZBIT["ilot_peint"], si=chaussee)
        self.passages.sort(key=lambda q: q["id"])
        # traversées cyclables : une entité = une file de pavés (un bord) ; les files parallèles à
        # moins de 6 m forment une traversée (enveloppe) ; une file isolée : bande de 0,35 m
        cyc.sort(key=lambda c: c[0])
        axes = []
        for cid, P in cyc:
            c = P.mean(axis=0)
            w, V = np.linalg.eigh(np.cov((P - c).T)) if len(P) > 2 else (None, None)
            u = V[:, 1] if w is not None else (P[-1] - P[0]) / max(np.hypot(*(P[-1] - P[0])), 1e-9)
            axes.append((c, u))
        groupe = list(range(len(cyc)))
        for i in range(len(cyc)):
            for j in range(i + 1, len(cyc)):
                ci, ui = axes[i]
                cj, uj = axes[j]
                d_perp = abs(float(np.cross(ui, cj - ci)))
                d_long = abs(float(ui @ (cj - ci)))
                if abs(ui @ uj) > 0.95 and d_perp < 6.0 and d_long < 4.0:
                    gi, gj = groupe[i], groupe[j]
                    groupe = [gi if g == gj else g for g in groupe]
        for gid in sorted(set(groupe)):
            P = np.vstack([cyc[i][1] for i in range(len(cyc)) if groupe[i] == gid])
            self._bit([_enveloppe_tampon(P, 0.30)], ZBIT["traversee_cyclable"], si=circ)

    # ---- bordures
    def _indexer_bordures(self):
        A, B, K, S0 = [], [], [], []
        for k, kb in enumerate(self.bordures):
            P = kb["P"]
            S = abscisses(P)
            kb["L"] = float(S[-1])
            A.append(P[:-1])
            B.append(P[1:])
            K.append(np.full(len(P) - 1, k))
            S0.append(S[:-1])
        self.kA, self.kB = np.vstack(A), np.vstack(B)
        self.kK, self.kS0 = np.concatenate(K), np.concatenate(S0)
        # classes des deux côtés (échantillons tous les 1 m) : côté bas circulé ?
        for kb in self.bordures:
            s = np.linspace(0, kb["L"], max(2, int(kb["L"]) + 1))
            q, tg = point_a(kb["P"], s)
            nv = normale_gauche(tg)
            bas = self.classe(q - nv * 0.45)
            haut = self.classe(q + nv * 0.5)
            zb = self.zone(q - nv * 0.45)
            vals, cnt = np.unique(bas, return_counts=True)
            kb["classe_bas"] = str(vals[np.argmax(cnt)])
            vals, cnt = np.unique(haut, return_counts=True)
            kb["classe_haut"] = str(vals[np.argmax(cnt)])
            kb["circulee_bas"] = bool(np.mean([b in VEHICULES_BAS or z in CIRCULEES for b, z in zip(bas, zb)]) >= 0.5)
        self.kCirc = np.array([self.bordures[k]["circulee_bas"] for k in self.kK])

    def ref_bordure(self, Q, rayon=10.0, circulee=True, exclure=None):
        """Bordure de référence de chaque point : la plus proche (dont le côté bas est circulé si
        `circulee`) dans `rayon`. Renvoie liste de dict(k, id, s, t, d, tg (2,), proj) ou None."""
        Q = np.atleast_2d(np.asarray(Q, dtype=np.float64))
        lo, hi = Q.min(axis=0) - rayon, Q.max(axis=0) + rayon
        sel = ((np.minimum(self.kA, self.kB) <= hi) & (np.maximum(self.kA, self.kB) >= lo)).all(axis=1)
        if circulee:
            sel &= self.kCirc
        if exclure is not None:
            sel &= ~np.isin(self.kK, list(exclure))
        if not sel.any():
            return [None] * len(Q)
        A, B, K, S0 = self.kA[sel], self.kB[sel], self.kK[sel], self.kS0[sel]
        d, j, pr = distance_segments(Q, A, B)
        out = []
        for i in range(len(Q)):
            if not np.isfinite(d[i]) or d[i] > rayon:
                out.append(None)
                continue
            jj = j[i]
            seg = B[jj] - A[jj]
            L = max(float(np.hypot(*seg)), 1e-9)
            tg = seg / L
            v = Q[i] - pr[i]
            cote = 1.0 if (tg[0] * v[1] - tg[1] * v[0]) >= 0 else -1.0
            s = float(S0[jj] + np.hypot(*(pr[i] - A[jj])))
            k = int(K[jj])
            out.append(dict(k=k, id=self.bordures[k]["id"], s=s, t=cote * float(d[i]), d=float(d[i]), tg=tg,
                            proj=pr[i], classe_bas=self.bordures[k]["classe_bas"],
                            classe_haut=self.bordures[k]["classe_haut"],
                            travaux=self.bordures[k]["zone_travaux_2025"],
                            modifiee=bool(self.bordures[k].get("modifiee_2025")), source=self.bordures[k]["source"]))
        return out

    def point_bordure(self, k, s, t):
        """Point (s, t) dans le repère de la bordure k (t > 0 côté haut)."""
        P = self.bordures[k]["P"]
        q, tg = point_a(P, np.atleast_1d(s))
        return q + normale_gauche(tg) * np.atleast_1d(t)[:, None]

    # ---- abaissés, BEV, paliers
    def _abaisses(self):
        """Abaissés de traversée : v2 (zone pilote) ; ailleurs extrémités des passages sur les bordures
        (rampe 1,20 m par défaut, palier 0,80 m, BEV 0,40 m à 0,50 m du nez) : géométrie a priori."""
        self.abaisses = []
        haut_ok = lambda sl: np.isin(self.base[sl], [CID[c] for c in ("trottoir", "ilot", "quai_bus",
                                                                     "acces_riverain", "espace_vert",
                                                                     "terre_plein_vegetal", "autre")])
        for k, kb in enumerate(self.bordures):
            for a in kb.get("abaisses") or []:
                if a.get("type") != "traversee":
                    continue
                self._bande(k, a["s0"], a["s1"], 0.0, PROFONDEUR_RAMPE_DEFAUT, "abaisse_traversee", haut_ok, True)
                self._bande(k, a["s0"], a["s1"], PROFONDEUR_RAMPE_DEFAUT, PROFONDEUR_RAMPE_DEFAUT + LARGEUR_PALIER,
                            "palier_abaisse", haut_ok, True)
                self.abaisses.append(dict(id=a.get("id"), bordure=kb["id"], k=k, s0=a["s0"], s1=a["s1"], source="v2"))
        for f in lire_geojson(BASE_V2 / "ponctuels_sol.geojson"):
            if f["properties"]["type"] == "bev":
                for poly in _polys_locaux(f["geometry"]):
                    self._bit([repere(r) for r in poly], ZBIT["bev"])
        x0, y0, x1, y1 = ctx.zone_pilote()["emprise"]
        for pp in self.passages:
            for bout, sens in ((pp["a"], -1.0), (pp["b"], 1.0)):
                if x0 <= bout[0] <= x1 and y0 <= bout[1] <= y1:
                    continue                        # zone pilote : abaissés v2
                # bordure coupée par l'axe prolongé du passage au-delà de l'extrémité
                pts = bout + np.outer(np.linspace(0.0, 3.0, 31), pp["u"] * sens)
                r = self.ref_bordure(pts, rayon=0.3, circulee=False)
                hits = [x for x in r if x is not None]
                if not hits:
                    continue
                h = hits[0]
                kb = self.bordures[h["k"]]
                cosx = abs(float(h["tg"] @ pp["u"]))
                if cosx > 0.707:
                    continue                        # bordure parallèle à la marche : pas d'abaissé
                L = pp["demi_largeur"] / max(math.sqrt(1 - cosx ** 2), 0.5)
                s0, s1 = max(h["s"] - L, 0.0), min(h["s"] + L, kb["L"])
                self._bande(h["k"], s0, s1, 0.0, PROFONDEUR_RAMPE_DEFAUT, "abaisse_traversee", haut_ok, True)
                self._bande(h["k"], s0, s1, PROFONDEUR_RAMPE_DEFAUT, PROFONDEUR_RAMPE_DEFAUT + LARGEUR_PALIER,
                            "palier_abaisse", haut_ok, True)
                self._bande(h["k"], s0, s1, 0.50, 0.90, "bev", haut_ok, True)
                self.abaisses.append(dict(id=f"AD-{pp['id']}-{'ab'[int(sens > 0)]}", bordure=kb["id"], k=h["k"],
                                          s0=round(s0, 3), s1=round(s1, 3), source="deduit_passage"))

    def _bande(self, k, s0, s1, t0, t1, zone, si, defaut):
        P = self.bordures[k]["P"]
        if s1 - s0 < 0.1:
            return
        s = np.linspace(s0, s1, max(2, int((s1 - s0) / 0.25) + 1))
        q, tg = point_a(P, s)
        nv = normale_gauche(tg)
        anneau = np.vstack([q + nv * t0, (q + nv * t1)[::-1]])
        self._bit([anneau], ZBIT[zone], si=si, defaut=defaut)

    def _clotures(self):
        self.clotures = []
        im = Image.new("L", (N, N), 0)
        dr = ImageDraw.Draw(im)
        for f in lire_geojson(DONNEES / "objets/mobilier.geojson"):
            if f["properties"]["type"] != "cloture" or f["geometry"]["type"] != "LineString":
                continue
            P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            self.clotures.append((f["properties"]["id"], P))
            dr.line(self.g.pil(P), fill=1, width=2)
        m = np.asarray(im, dtype=bool)
        self.zones[m] |= ZBIT["cloture"]

    # ---- requêtes
    def classe(self, Q):
        r, c, ok = self.g.rc(Q)
        v = self.base[r, c]
        return np.where(ok, np.array(CLASSES, dtype=object)[v], "")

    def zone(self, Q, avec_cloture=False):
        """Zone la plus spécifique (precedence_zones) en chaque point."""
        r, c, ok = self.g.rc(Q)
        z = self.zones[r, c]
        out = np.array(CLASSES, dtype=object)[self.base[r, c]]
        out = out.copy()
        fait = np.zeros(len(out), bool)
        for nom in self.precedence:
            if nom in ZBIT:
                m = ((z & ZBIT[nom]) > 0) & ~fait
                out[m] = nom
                fait |= m
        out[~ok] = ""
        return out

    def surface_v1(self, q):
        """Surface v1 (surfaces_2026) sous le point : dict(id, classe, etat, source) ou None."""
        from commun import dans_polygone
        q = np.asarray(q, float)
        for s in self.surfaces_v1:
            if np.any(q < s["bmin"]) or np.any(q > s["bmax"]):
                continue
            if dans_polygone(q[None], s["poly"])[0]:
                return {k: s[k] for k in ("id", "classe", "etat", "source")}
        return None

    def marquages_poses_2025(self, q, rayon=0.15):
        """Marquages posés ou refaits en 2025 (preuve post-travaux) à moins de `rayon` du point."""
        from commun import dans_polygone
        out = []
        ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        Q = np.vstack([q, q + rayon * np.c_[np.cos(ang), np.sin(ang)]])
        for mid, zone, etat, anneau in self.marques:
            if not str(etat or "").startswith(("neuf_2025", "refait_2025")):
                continue
            if np.min(np.hypot(*(anneau - q).T)) > 15.0:
                continue
            if dans_polygone(Q, [anneau]).any():
                out.append(dict(id=mid, zone=zone, etat=etat))
        return out

    def zones_bits(self, Q):
        r, c, ok = self.g.rc(Q)
        z = self.zones[r, c]
        return [[nom for nom in ZONES if (zi & ZBIT[nom])] for zi in z]

    def faiblesse(self, Q):
        """Pour chaque point : (classe de base faible, zone dérivée par défaut, source de la classe)."""
        r, c, ok = self.g.rc(Q)
        return self.faible[r, c], self.zone_defaut[r, c], np.array(SRC_BASE, dtype=object)[self.src[r, c]]

    def z_sol(self, Q):
        Q = np.atleast_2d(Q)
        L = repere(Q, "l93")
        return self.mnt(L[:, 0], L[:, 1]) - 216.30

    def relief_local(self, q, r_in=0.5, r_out=(2.0, 4.0)):
        """Surélévation locale (m) : médiane du MNT dans r_in moins médiane de l'anneau r_out (îlot ?)."""
        ang = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        cin = np.vstack([q + np.c_[np.cos(ang), np.sin(ang)] * rr for rr in (0.0, r_in / 2, r_in)])
        cout = np.vstack([q + np.c_[np.cos(ang), np.sin(ang)] * rr for rr in np.linspace(*r_out, 3)])
        return float(np.median(self.z_sol(cin)) - np.median(self.z_sol(cout)))

    # ---- voies
    def _cap_route(self, route, q):
        best = None
        for R in self.refs.get(route, []):
            s, d, _ = projeter_polyligne(R, q[None])
            if best is None or d[0] < best[0]:
                _, tg = point_a(R, s)
                best = (d[0], tg[0])
        return None if best is None else best[1]

    def voies(self, q, types=("driving", "bus", "biking"), rayon=25.0, jonction=True):
        """Voies autour de q triées par distance : [dict(route, voie, type, d, cap_deg, dedans, jonction)]."""
        q = np.asarray(q, dtype=np.float64)
        out = []
        for i, l in enumerate(self.lanes):
            if l["type"] not in types or (not jonction and l["jonction"]):
                continue
            if np.any(q < l["bmin"] - rayon) or np.any(q > l["bmax"] + rayon):
                continue
            dedans = bool(dans_polygone(q[None], l["poly"])[0])
            A, B = aretes(l["poly"])
            d, _, _ = distance_segments(q[None], A, B)
            dd = 0.0 if dedans else float(d[0])
            if dd > rayon:
                continue
            tg = self._cap_route(l["route"], q)
            if tg is None:
                continue
            cap = azimut(tg) if l["voie"] < 0 else (azimut(tg) + 180.0) % 360.0
            out.append(dict(i=i, route=l["route"], voie=l["voie"], type=l["type"], d=dd, dedans=dedans,
                            cap_deg=cap, jonction=l["jonction"], nom=l["nom"]))
        out.sort(key=lambda v: (v["d"], v["jonction"], v["route"], v["voie"]))
        return out

    # ---- largeur libre (PMR-01)
    def coupe_pietonne(self, k, s, t_max=12.0, pas=0.05):
        """Profil le long de la normale à la bordure k en s : t (pas 5 cm) et masque piéton contigu
        depuis l'arrière de la bordure. Limites dures : classe non piétonne, bâtiment, clôture."""
        t = np.arange(0.05, t_max, pas)
        q = self.point_bordure(k, np.full(len(t), s), t)
        cl = self.classe(q)
        bits = self.zones_bits(q)
        ok = np.array([c in PIETONNES and "cloture" not in b for c, b in zip(cl, bits)])
        if not ok.any():
            return t, np.zeros(len(t), bool), ""
        i0 = int(np.argmax(ok))
        if t[i0] > 0.5:
            return t, np.zeros(len(t), bool), ""
        m = np.zeros(len(t), bool)
        i = i0
        while i < len(t) and ok[i]:
            m[i] = True
            i += 1
        fin = "fin_profil"
        if i < len(t):
            fin = "cloture" if "cloture" in bits[i] else (cl[i] or "hors")
        return t, m, fin

    @staticmethod
    def largeur_libre(t, m, obstacles):
        """Plus grand intervalle libre du profil (m) : obstacles = [(t_centre, demi_largeur)]."""
        libre = m.copy()
        for tc, w in obstacles:
            libre &= ~((t >= tc - w) & (t <= tc + w))
        best, cur = 0.0, 0.0
        pas = float(t[1] - t[0]) if len(t) > 1 else 0.05
        for v in libre:
            cur = cur + pas if v else 0.0
            best = max(best, cur)
        return round(best, 2)

    # ---- rasters d'index (requêtes rapides hors Python : composeur, Houdini, PCG)
    def raster_distance_bordure(self, pas=0.10, portee=6.0):
        """Distance signée (m) à l'arête avant de la bordure la plus proche (t > 0 côté haut) et indice de
        cette bordure, sur une grille `pas` ; NaN / -1 au-delà de `portee`."""
        n = int(round((EMPRISE[2] - EMPRISE[0]) / pas))
        D = np.full((n, n), np.inf, np.float32)
        T = np.full((n, n), np.nan, np.float32)
        K = np.full((n, n), -1, np.int32)
        xs = EMPRISE[0] + (np.arange(n) + 0.5) * pas
        ys = EMPRISE[3] - (np.arange(n) + 0.5) * pas
        for a, b, k in zip(self.kA, self.kB, self.kK):
            lo, hi = np.minimum(a, b) - portee, np.maximum(a, b) + portee
            c0, c1 = np.searchsorted(xs, lo[0]), np.searchsorted(xs, hi[0])
            r0, r1 = np.searchsorted(-ys, -hi[1]), np.searchsorted(-ys, -lo[1])
            if c1 <= c0 or r1 <= r0:
                continue
            X, Y = np.meshgrid(xs[c0:c1], ys[r0:r1])
            ab = b - a
            L2 = max(float(ab @ ab), 1e-12)
            u = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1]) / L2, 0.0, 1.0)
            px, py = a[0] + u * ab[0], a[1] + u * ab[1]
            d = np.hypot(X - px, Y - py).astype(np.float32)
            cote = np.where(ab[0] * (Y - py) - ab[1] * (X - px) >= 0, 1.0, -1.0).astype(np.float32)
            blk = D[r0:r1, c0:c1]
            m = d < blk
            blk[m] = d[m]
            T[r0:r1, c0:c1][m] = (cote * d)[m]
            K[r0:r1, c0:c1][m] = k
        T[D > portee] = np.nan
        K[D > portee] = -1
        return T, K

    def raster_voies(self, pas=0.25):
        """Indice de voie (lanes_2026, 0 = aucune) et cap de circulation (deg) sur une grille `pas`."""
        n = int(round((EMPRISE[2] - EMPRISE[0]) / pas))
        I = np.zeros((n, n), np.uint8)
        C = np.full((n, n), np.nan, np.float32)
        for i, l in enumerate(self.lanes):
            im = Image.new("L", (n, n), 0)
            dr = ImageDraw.Draw(im)
            for k, r in enumerate(l["poly"]):
                pts = [((x - EMPRISE[0]) / pas - 0.5, (EMPRISE[3] - y) / pas - 0.5) for x, y in r]
                dr.polygon(pts, fill=0 if k else 1)
            m = np.asarray(im, bool) & (I == 0)
            if not m.any():
                continue
            I[m] = i + 1
            rr, cc = np.nonzero(m)
            Q = np.c_[EMPRISE[0] + (cc + 0.5) * pas, EMPRISE[3] - (rr + 0.5) * pas]
            best_d = np.full(len(Q), np.inf)
            cap = np.zeros(len(Q))
            for R in self.refs.get(l["route"], []):
                s_, d_, _ = projeter_polyligne(R, Q)
                _, tg = point_a(R, s_)
                az = (np.degrees(np.arctan2(tg[:, 0], tg[:, 1])) + (0.0 if l["voie"] < 0 else 180.0)) % 360.0
                mm = d_ < best_d
                best_d[mm], cap[mm] = d_[mm], az[mm]
            C[rr, cc] = cap
        return I, C

    # ---- sorties
    def ecrire(self):
        CARTE.mkdir(parents=True, exist_ok=True)
        pal = []
        for c in CLASSES:
            pal += list(COULEURS[c])
        im = Image.fromarray(self.base, mode="P")
        im.putpalette(pal + [0] * (768 - len(pal)))
        im.save(CARTE / "classes_5cm.png", optimize=True)
        Image.fromarray(self.zones.astype(np.uint16)).save(CARTE / "zones_5cm.png")
        Image.fromarray((self.faible.astype(np.uint8) | (self.zone_defaut.astype(np.uint8) << 1))).save(
            CARTE / "faiblesse_5cm.png")
        T, K = self.raster_distance_bordure()
        enc = np.where(np.isfinite(T), np.clip(np.round((T + 10.0) * 1000.0), 1, 65535), 0).astype(np.uint16)
        Image.fromarray(enc).save(CARTE / "distance_bordure_10cm.png")
        Image.fromarray(np.where(K >= 0, K + 1, 0).astype(np.uint16)).save(CARTE / "bordure_proche_10cm.png")
        I, C = self.raster_voies()
        Image.fromarray(I).save(CARTE / "voies_25cm.png")
        Image.fromarray(np.where(np.isfinite(C), np.round(C * 100.0) + 1, 0).astype(np.uint16)).save(CARTE / "cap_voies_25cm.png")
        ecrire_json(CARTE / "carte.json", arrondi({
            "schema": "pj_carte_coherence/0.1",
            "repere": "local = L93 - (917279.43, 6460289.98) ; z = NGF - 216.30",
            "georef": {"x0_local": EMPRISE[0], "y1_local": EMPRISE[3], "pas_m": PAS, "taille_px": [N, N],
                       "pixel": "(r, c) centré en (x0 + (c + 0,5)·pas, y1 − (r + 0,5)·pas)"},
            "classes_5cm.png": {"valeurs": {str(i): c for i, c in enumerate(CLASSES)},
                                "priorite": "ilots v2 > surfaces v2 (zone pilote) > batiments_local (sur autre/vide) > surfaces_2026 v1"},
            "zones_5cm.png": {"bits": {z: ZBIT[z] for z in ZONES},
                              "precedence": self.precedence,
                              "sources": {"passage_pietons": "marquages v2 zebra (axe ± longueur de bande / 2) ∩ surfaces circulées",
                                          "traversee_cyclable": "marquages v2 traversee_cyclable (enveloppe des files + 0,35 m)",
                                          "ilot_peint": "marquages v2 hachures / aplat / chevron + surfaces v2 sous_classe terre_plein_peint",
                                          "voie_bus": "lanes_2026 bus ∩ chaussée", "bande_cyclable": "lanes_2026 biking ∩ chaussée",
                                          "abaisse_traversee": "abaissés v2 (zone pilote) ; ailleurs extrémités des passages sur les bordures (rampe 1,20 m a priori)",
                                          "palier_abaisse": "bande de 0,80 m derrière la rampe", "bev": "ponctuels_sol v2 ; ailleurs 0,50-0,90 m derrière le nez (a priori)",
                                          "cloture": "clôtures GAM (mobilier.geojson LineString)"}},
            "faiblesse_5cm.png": {"bit0": "classe de base faible (limite raster v1, surface modifiée 2025 a priori)",
                                  "bit1": "zone dérivée à géométrie par défaut (a priori)"},
            "distance_bordure_10cm.png": {"encodage": "uint16 : t = valeur / 1000 - 10 (m) ; 0 = au-delà de 6 m",
                                          "sens": "t > 0 côté haut (trottoir, îlot), t < 0 côté chaussée ; arête avant",
                                          "pas_m": 0.10},
            "bordure_proche_10cm.png": {"encodage": "uint16 : indice + 1 dans bordures_site.geojson (ordre des entités), 0 = aucune",
                                        "pas_m": 0.10},
            "voies_25cm.png": {"encodage": "uint8 : indice + 1 dans la table voies ci-dessous, 0 = hors voie", "pas_m": 0.25},
            "cap_voies_25cm.png": {"encodage": "uint16 : cap de circulation (deg) = (valeur - 1) / 100, 0 = hors voie",
                                   "pas_m": 0.25},
            "voies": [dict(indice=i + 1, route=l["route"], voie=l["voie"], type=l["type"], jonction=l["jonction"],
                           nom=l["nom"]) for i, l in enumerate(self.lanes)],
            "bordures": {"fichier": "bordures_site.geojson", "n": len(self.bordures),
                         "n_circulee_bas": int(sum(k["circulee_bas"] for k in self.bordures))},
            "abaisses": self.abaisses, "passages": [p["id"] for p in self.passages],
        }, 3))

    def apercu(self, chemin, emprise, res=0.05, objets=None):
        """PNG de contrôle : classes + zones + bordures (+ objets [(xy, couleur, libellé)])."""
        x0, y0, x1, y1 = emprise
        r0, c0, _ = self.g.rc([[x0, y1]])
        r1, c1, _ = self.g.rc([[x1, y0]])
        b = self.base[r0[0]:r1[0], c0[0]:c1[0]]
        z = self.zones[r0[0]:r1[0], c0[0]:c1[0]]
        rgb = np.array([COULEURS[c] for c in CLASSES], np.uint8)[b].astype(np.float32)
        for nom, col in (("passage_pietons", (255, 255, 255)), ("ilot_peint", (255, 255, 0)),
                         ("abaisse_traversee", (0, 200, 255)), ("bev", (255, 0, 255)), ("palier_abaisse", (0, 120, 160)),
                         ("bande_cyclable", (255, 120, 120)), ("traversee_cyclable", (255, 200, 0)),
                         ("cloture", (0, 0, 0))):
            m = (z & ZBIT[nom]) > 0
            rgb[m] = 0.45 * rgb[m] + 0.55 * np.array(col)
        im = Image.fromarray(rgb.astype(np.uint8))
        dr = ImageDraw.Draw(im)
        to = lambda P: [((x - x0) / PAS, (y1 - y) / PAS) for x, y in P]
        for kb in self.bordures:
            P = kb["P"]
            if P[:, 0].max() < x0 or P[:, 0].min() > x1 or P[:, 1].max() < y0 or P[:, 1].min() > y1:
                continue
            dr.line(to(P), fill=(255, 0, 0) if kb["circulee_bas"] else (120, 0, 0), width=2)
            s = np.arange(0.5, kb["L"], 2.0)
            if len(s):
                q, tg = point_a(P, s)
                nv = normale_gauche(tg)
                for a, bb in zip(q, q + nv * 0.6):
                    dr.line(to([a, bb]), fill=(255, 0, 0), width=1)
        for xy, col, lab in objets or []:
            u, v = to([xy])[0]
            dr.ellipse([u - 5, v - 5, u + 5, v + 5], outline=col, width=2)
            if lab:
                dr.text((u + 6, v - 6), lab, fill=col)
        im.save(chemin)
        return chemin


def _enveloppe_tampon(P, d):
    """Enveloppe convexe de P élargie de d (approximation par 16 directions)."""
    ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    Q = (P[:, None, :] + d * np.c_[np.cos(ang), np.sin(ang)][None]).reshape(-1, 2)
    return _enveloppe(Q)


def _enveloppe(P):
    P = np.unique(np.round(P, 6), axis=0)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]
    if len(P) < 3:
        return P
    def croix(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    bas, haut = [], []
    for p in P:
        while len(bas) >= 2 and croix(bas[-2], bas[-1], p) <= 0:
            bas.pop()
        bas.append(p)
    for p in P[::-1]:
        while len(haut) >= 2 and croix(haut[-2], haut[-1], p) <= 0:
            haut.pop()
        haut.append(p)
    return np.array(bas[:-1] + haut[:-1])


@functools.lru_cache(maxsize=1)
def carte():
    return Carte()


if __name__ == "__main__":
    import sys
    import time
    t0 = time.time()
    c = Carte()
    c.ecrire()
    print(f"{time.time() - t0:.1f} s")
    if len(sys.argv) > 1:
        c.apercu(sys.argv[1], (-40, -40, 40, 40))
