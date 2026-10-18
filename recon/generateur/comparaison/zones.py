"""Zones d'intérêt d'un site fabriqué, dans le repère du modèle (s, t) de la comparaison, et leur visibilité depuis une
vue (comparaison v2 : sélection des photos guidée par la couverture, carte de couverture).

Sources (lecture seule) :
- `modele_voie.json` (repère Lambert-93, `repere.crs` = EPSG:2154) quand il décrit des carrefours :
  - carrefour plan : **centre** = `zone_conflit` du carrefour (sinon enveloppe des trajectoires, sinon disque de 12 m) ;
  - giratoire (`anneau`) : **anneau** découpé en secteurs (un par branche, limites aux bissectrices entre branches
    voisines : c'est là que se font les entrées, les sorties et les conflits) et **îlot central** ;
  - **îlots** (`ilots[].polygone`), hors îlot central ;
  - **passages** (`marquages` de type passage_pieton, traversee_cyclable…, fusionnés par traversée : morceaux à
    moins de 4 m) ;
  - **approches** : pour chaque branche, la chaussée de la route sur les 45 m qui précèdent la frontière du carrefour
    (ligne de référence de la route, s de frontière de la branche ou de `frontiere[]`), limitée aux faces de chaussée
    du sol fabriqué (voies, voies de tourne-à-gauche ou à droite, zone neutralisée, terre-plein) ;
- sinon (tronçon courant) : **tronçon** découpé en cases de 20 m sur la chaussée et **passages** peints (l2b, classe
  « passage »).

Chaque zone porte des points d'échantillonnage au sol (pas de 1 m, au plus 400 points), son polygone (shapely) et un
poids dans la sélection. Visibilité d'une zone par une vue : part pondérée des points vus (dans l'image, à 1,5-50 m,
hors porteur, sans bâtiment OSM ni îlot central de giratoire (supposé opaque : planté, muret) entre la caméra et le
point ; poids 1 jusqu'à 20 m puis décroissant jusqu'à 0 à 50 m)
et direction d'observation (azimut grille de la caméra vers le barycentre des points vus, en 8 secteurs de 45°).
Déterministe.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

POIDS = {"centre": 3.0, "anneau": 2.0, "ilot_central": 1.0, "ilot": 1.5, "passage": 1.5, "approche": 1.0,
         "troncon": 1.0}
LIBELLES = {"centre": "zone centrale de conflit", "anneau": "anneau (secteur)", "ilot_central": "îlot central",
            "ilot": "îlot", "passage": "passage", "approche": "approche", "troncon": "tronçon"}
COULEURS = {"centre": (230, 40, 40), "anneau": (230, 40, 40), "ilot_central": (150, 90, 30), "ilot": (200, 120, 0),
            "passage": (40, 90, 230), "approche": (120, 60, 170), "troncon": (120, 60, 170)}
PAS_POINTS = 1.0
N_POINTS_MAX = 400
LONGUEUR_APPROCHE = 45.0
CLASSES_CHAUSSEE = ("voie_circulation", "voie_tourne_gauche", "voie_tourne_droite", "zone_neutralisee", "terre_plein",
                    "carrefour_chaussee")
D_MIN, D_PLEIN, D_MAX = 1.5, 20.0, 50.0       # distances de visibilité (m) : poids 1 jusqu'à D_PLEIN, 0 à D_MAX
SECTEURS = ("N", "NE", "E", "SE", "S", "SO", "O", "NO")
SEUIL_VOIT = 0.20                             # part pondérée des points d'une zone au-delà de laquelle la vue « voit » la zone


@dataclass
class Zone:
    id: str
    type: str
    nom: str
    poly: object                      # shapely Polygon / MultiPolygon (repère du modèle)
    pts: np.ndarray = field(default=None)   # (N, 3) points au sol
    poids: float = 1.0
    meta: dict = field(default_factory=dict)

    @property
    def centre(self):
        c = self.poly.centroid
        return float(c.x), float(c.y)

    def dict(self, precision=2):
        from shapely.geometry import mapping
        g = mapping(self.poly.simplify(0.05))

        def arr(c):
            if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
                return [round(float(v), precision) for v in c]
            return [arr(x) for x in c]
        return {"id": self.id, "type": self.type, "nom": self.nom, "poids": self.poids,
                "aire_m2": round(float(self.poly.area), 1), "centre": [round(v, 2) for v in self.centre],
                "n_points": int(len(self.pts)), "geometrie": {"type": g["type"], "coordinates": arr(g["coordinates"])},
                **({"meta": self.meta} if self.meta else {})}


# ------------------------------------------------------------------------------------------------ outils
def _vers_modele(ancrage, pts_l93):
    a = np.asarray(pts_l93, dtype=np.float64)[:, :2]
    s, t = ancrage.vers_modele(a[:, 0], a[:, 1])
    return np.c_[s, t]


def _poly(ancrage, anneau_l93):
    from shapely.geometry import Polygon
    p = Polygon(_vers_modele(ancrage, anneau_l93))
    return p if p.is_valid else p.buffer(0)


def _points_dans(poly, modele, pas=PAS_POINTS, filtre=None):
    """Points d'une grille de pas `pas` dans le polygone (au moins le centroïde), z du sol du modèle ; filtre(xy) ->
    masque optionnel (faces de chaussée…) ; au plus N_POINTS_MAX (sous-échantillonnage régulier)."""
    import shapely
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / pas) * pas + pas / 2, x1, pas)
    ys = np.arange(math.floor(y0 / pas) * pas + pas / 2, y1, pas)
    if len(xs) and len(ys):
        X, Y = np.meshgrid(xs, ys)
        xy = np.c_[X.ravel(), Y.ravel()]
        dedans = shapely.contains_xy(poly, xy[:, 0], xy[:, 1])
        xy = xy[dedans]
    else:
        xy = np.zeros((0, 2))
    if filtre is not None and len(xy):
        xy = xy[filtre(xy)]
    if not len(xy):
        c = poly.representative_point()
        xy = np.array([[c.x, c.y]])
    if len(xy) > N_POINTS_MAX:
        xy = xy[np.linspace(0, len(xy) - 1, N_POINTS_MAX).round().astype(int)]
    z = np.array([modele.z_sol(float(a), float(b)) for a, b in xy])
    return np.c_[xy, z]


def _classes_faces(modele):
    """Arbre des centres des faces utiles et leur classe (pour filtrer les points de chaussée)."""
    from scipy.spatial import cKDTree
    idx = np.nonzero(modele.utile)[0]
    return cKDTree(modele.centres[idx, :2]), modele.classe_face[idx]


def _filtre_classes(arbre, classes, gardees, dmax=1.2):
    gardees = set(gardees)

    def f(xy):
        d, i = arbre.query(xy)
        return (d <= dmax) & np.array([c in gardees for c in classes[i]])
    return f


def _abscisses(poly):
    d = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(poly, axis=0), axis=1))]
    return d


def _sous_ligne(xy, s0, s1):
    """Morceau d'une polyligne (N, 2) entre les abscisses curvilignes s0 < s1."""
    d = _abscisses(xy)
    s0, s1 = max(0.0, s0), min(d[-1], s1)
    if s1 - s0 < 1.0:
        return None
    pts = [np.interp(s0, d, xy[:, 0]), np.interp(s0, d, xy[:, 1])]
    out = [pts]
    for k in range(len(d)):
        if s0 < d[k] < s1:
            out.append(list(xy[k]))
    out.append([np.interp(s1, d, xy[:, 0]), np.interp(s1, d, xy[:, 1])])
    return np.array(out, dtype=np.float64)


# ------------------------------------------------------------------------------------------------ zones du site
def zones_site(modele, ancrage, dossier_modele):
    """Zones d'intérêt du site : (genre, [Zone]) ; genre = « carrefour », « giratoire » ou « section »."""
    from shapely.geometry import LineString, MultiPoint, Point, Polygon
    from shapely.ops import unary_union
    f = Path(dossier_modele) / "modele_voie.json"
    mv = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    zones = []
    arbre, classes = _classes_faces(modele)
    chaussee = _filtre_classes(arbre, classes, CLASSES_CHAUSSEE)
    l93 = str((mv.get("repere") or {}).get("crs", "")) == "EPSG:2154"
    carrefours = mv.get("carrefours") or []
    genre = "section"
    if l93 and carrefours:
        routes = {r["id"]: r for r in mv.get("routes", [])}
        ilots_centraux = set()
        for c in carrefours:
            cid = c["id"]
            C = _vers_modele(ancrage, [c["centre"]])[0]
            # branches : ligne de la route (repère du modèle), abscisse de la frontière, direction depuis le centre
            # (lacet du point de la route 10 m au-delà de la frontière ; « azimut_deg » de modele_voie est un angle
            # trigonométrique, on ne s'y fie pas)
            front = {(fz.get("route"), fz.get("extremite")): float(fz.get("s0", 0.0)) for fz in c.get("frontiere", [])}
            branches = []
            for b in c.get("branches", []):
                r = routes.get(b.get("route"))
                if not r:
                    continue
                xy = _vers_modele(ancrage, r["ligne_reference"]["geometrie"])
                d = _abscisses(xy)
                L = float(d[-1])
                ext = b.get("extremite", "fin")
                sf = b.get("s_frontiere_m")
                sf = float(sf) if sf is not None else front.get((b.get("route"), ext), L if ext == "fin" else 0.0)
                s_dehors = sf - 10.0 if ext == "fin" else sf + 10.0
                px, py = np.interp(s_dehors, d, xy[:, 0]), np.interp(s_dehors, d, xy[:, 1])
                lac = math.degrees(math.atan2(py - C[1], px - C[0]))
                branches.append({"b": b, "r": r, "xy": xy, "L": L, "ext": ext, "sf": sf, "lacet": lac})
            an = c.get("anneau")
            if an:
                genre = "giratoire"
                Re = float(an.get("rayon_exterieur_m") or 0.0)
                Ri = float(an.get("rayon_ilot_central_m") or max(0.0, Re - float(an.get("largeur_anneau_m") or 8.0)))
                fr = float(an.get("bande_franchissable_m") or 0.0)
                Rin = max(0.5, Ri - fr)
                ilots_centraux.add(an.get("ilot_central"))
                br = sorted(branches, key=lambda x: x["lacet"] % 360.0)
                lacs = [x["lacet"] % 360.0 for x in br]
                if len(br) >= 2:
                    for k, x in enumerate(br):
                        a = lacs[k]
                        a0 = a - ((a - lacs[k - 1]) % 360.0) / 2.0
                        a1 = a + ((lacs[(k + 1) % len(lacs)] - a) % 360.0) / 2.0
                        angs = np.radians(np.linspace(a0, a1, 24))
                        ext_ = [(C[0] + Re * math.cos(u), C[1] + Re * math.sin(u)) for u in angs]
                        inn = [(C[0] + Rin * math.cos(u), C[1] + Rin * math.sin(u)) for u in angs[::-1]]
                        bid = x["b"]["id"]
                        zones.append(Zone(f"anneau.{bid.replace('B-', '')}", "anneau", f"anneau, secteur de {bid}",
                                          Polygon(ext_ + inn),
                                          meta={"carrefour": cid, "branche": bid,
                                                "azimut_grille_branche_deg": round(ancrage.az_grille(x["lacet"]), 1),
                                                "rayons_m": [round(Rin, 2), round(Re, 2)]}))
                else:
                    p = Point(*C).buffer(Re).difference(Point(*C).buffer(Rin))
                    zones.append(Zone("anneau", "anneau", "anneau", p, meta={"carrefour": cid}))
                zones.append(Zone("ilot_central", "ilot_central", "îlot central", Point(*C).buffer(Rin, 48),
                                  meta={"carrefour": cid, "rayon_m": round(Rin, 2)}))
            else:
                genre = "carrefour" if genre == "section" else genre
                zc = c.get("zone_conflit")
                if zc and len(zc.get("exterieur", [])) >= 3:
                    p, src = _poly(ancrage, zc["exterieur"]), "zone_conflit du carrefour"
                else:
                    tr = [np.asarray(t["geometrie"])[:, :2] for t in c.get("trajectoires", []) if t.get("geometrie")]
                    if tr:
                        p = MultiPoint(_vers_modele(ancrage, np.concatenate(tr))).convex_hull
                        src = "enveloppe des trajectoires"
                    else:
                        p, src = Point(*C).buffer(12.0), "disque de 12 m (ni zone de conflit ni trajectoire)"
                zones.append(Zone(f"centre.{cid}" if len(carrefours) > 1 else "centre", "centre",
                                  f"zone centrale de conflit ({cid})", p, meta={"carrefour": cid, "source": src}))
            # approches : 45 m de chaussée avant la frontière
            for x in branches:
                b, r = x["b"], x["r"]
                s0, s1 = (x["sf"] - LONGUEUR_APPROCHE, x["sf"]) if x["ext"] == "fin" else (x["sf"], x["sf"] + LONGUEUR_APPROCHE)
                ligne = _sous_ligne(x["xy"], s0, s1)
                if ligne is None:
                    continue
                p = LineString(ligne).buffer(10.0, cap_style=2)
                zones.append(Zone(f"approche.{b['id'].replace('B-', '')}", "approche",
                                  f"approche {b['id']} ({r.get('nom', r['id'])})", p,
                                  meta={"carrefour": cid, "branche": b["id"], "route": r["id"],
                                        "s_route": [round(max(0.0, s0), 1), round(min(x["L"], s1), 1)],
                                        "azimut_grille_deg": round(ancrage.az_grille(x["lacet"]), 1)}))
        # îlots
        for il in mv.get("ilots", []):
            if il.get("id") in ilots_centraux or not (il.get("polygone") or {}).get("exterieur"):
                continue
            p = _poly(ancrage, il["polygone"]["exterieur"])
            if p.area < 0.3:
                continue
            tp = il.get("terre_plein") or {}
            zones.append(Zone(f"ilot.{il['id'].split('.', 1)[-1]}", "ilot", f"îlot {il['id']} ({il.get('type', '')})",
                              p, meta={"ilot": il["id"], "type": il.get("type"),
                                       "remplissage": (tp.get("remplissage") or {}).get("materiau_id"),
                                       "franchissable": tp.get("franchissable"),
                                       "refuge": bool(il.get("refuge"))}))
        # passages (morceaux fusionnés par traversée)
        morceaux = []
        for m in mv.get("marquages", []):
            if not str(m.get("type", "")).startswith(("passage", "traversee")):
                continue
            g = (m.get("geometrie") or {}).get("exterieur")
            if g and len(g) >= 3:
                morceaux.append((m["id"], m["type"], _poly(ancrage, g), (m.get("ancrage") or {}).get("route")))
        groupes = []
        for mid, typ, p, rte in morceaux:
            for gr in groupes:
                if gr["poly"].distance(p) < 4.0 and gr["type"] == typ and gr["route"] == rte:
                    gr["poly"] = gr["poly"].union(p)
                    gr["ids"].append(mid)
                    break
            else:
                groupes.append({"poly": p, "ids": [mid], "type": typ, "route": rte})
        for k, gr in enumerate(groupes):
            p = gr["poly"].convex_hull
            zones.append(Zone(f"passage.{k + 1}", "passage", f"{gr['type'].replace('_', ' ')} {', '.join(gr['ids'])}", p,
                              meta={"marquages": gr["ids"], "type": gr["type"], "route": gr["route"]}))
    else:
        # tronçon courant : cases de 20 m sur la chaussée, passages peints de l2b
        ch = modele.chaussee()
        s = np.arange(math.floor(modele.s_min / 20.0) * 20.0, modele.s_max, 20.0)
        for k, a in enumerate(s):
            sel = (ch[:, 0] >= a) & (ch[:, 0] < a + 20.0) & ~np.isnan(ch[:, 1])
            if not sel.any():
                continue
            lo, hi = float(np.nanmin(ch[sel, 1])), float(np.nanmax(ch[sel, 2]))
            p = Polygon([(max(a, modele.s_min), lo), (min(a + 20, modele.s_max), lo), (min(a + 20, modele.s_max), hi),
                         (max(a, modele.s_min), hi)])
            if p.area > 5:
                zones.append(Zone(f"troncon.{int(a):+04d}", "troncon", f"chaussée de s = {a:.0f} à {a + 20:.0f} m", p))
        for k, p in enumerate(_passages_l2b(modele.dossier)):
            zones.append(Zone(f"passage.{k + 1}", "passage", "passage peint (l2b)", p))
    for z in zones:
        z.poids = POIDS[z.type]
        filtre = chaussee if z.type == "approche" else None
        z.pts = _points_dans(z.poly, modele, filtre=filtre)
        if z.type == "approche":                      # polygone de dessin : enveloppe des points de chaussée
            if len(z.pts) >= 3:
                z.poly = MultiPoint(z.pts[:, :2]).buffer(0.75).simplify(0.3)
    zones = [z for z in zones if len(z.pts)]
    return genre, zones


def _passages_l2b(dossier):
    """Polygones des passages peints (classe « passage » de l2b), regroupés à moins de 3 m."""
    from shapely.geometry import MultiPoint
    d = Path(dossier) / "l2b"
    if not (d / "peinture_points.npy").exists():
        return []
    voc = json.loads((d / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
    if "passage" not in voc.get("classe", []):
        return []
    PP, FF, CC, AA = (np.load(d / f"peinture_{n}.npy") for n in ("points", "faces", "comptes", "attributs"))
    ic = voc["colonnes"].index("classe")
    k = voc["classe"].index("passage")
    off = np.concatenate([[0], np.cumsum(CC)[:-1]])
    sel = np.nonzero(AA[:, ic] == k)[0]
    if not len(sel):
        return []
    pts = np.concatenate([PP[FF[off[i]:off[i] + CC[i]], :2] for i in sel])
    from scipy.cluster.hierarchy import fcluster, linkage
    q = pts[:: max(1, len(pts) // 3000)]
    lab = fcluster(linkage(q, "single"), 3.0, "distance") if len(q) > 1 else np.ones(1, int)
    return [MultiPoint(q[lab == g]).convex_hull.buffer(0.5) for g in np.unique(lab)]


# ------------------------------------------------------------------------------------------------ visibilité
class Visibilite:
    """Visibilité des zones depuis des vues ; occultation par les bâtiments OSM calculée une fois par position."""

    def __init__(self, zones, ancrage, batiments=None):
        self.zones = zones
        self.anc = ancrage
        self.bat = batiments
        self.P = np.concatenate([z.pts for z in zones]) if zones else np.zeros((0, 3))
        self.zid = np.concatenate([np.full(len(z.pts), k) for k, z in enumerate(zones)]) if zones else np.zeros(0, int)
        x, y = ancrage.vers_l93(self.P[:, 0], self.P[:, 1])
        self.XY = np.c_[x, y]
        self._occ = {}
        # îlot central d'un giratoire : opaque (planté, muret, relief : essai du 18/10/2026 sur le Rond-point du Lycée,
        # parc boisé ceint d'un muret) ; ses propres points restent visibles depuis l'anneau
        self.ilots_opaques = [(np.array(z.centre), float(z.meta["rayon_m"]) - 1.0, k) for k, z in enumerate(zones)
                              if z.type == "ilot_central" and z.meta.get("rayon_m")]

    def dans_ilot_opaque(self, s, t):
        return any(math.hypot(s - O[0], t - O[1]) < r for O, r, _ in self.ilots_opaques)

    def _masque_ilots(self, C):
        """Points dont la ligne de visée depuis C (en plan) traverse un îlot central opaque."""
        ok = np.ones(len(self.P), bool)
        for O, r, k in self.ilots_opaques:
            if r <= 0.5:
                continue
            A = np.asarray(C[:2], dtype=np.float64)
            B = self.P[:, :2]
            AB = B - A
            L2 = np.maximum((AB ** 2).sum(1), 1e-9)
            u = np.clip(((O - A) * AB).sum(1) / L2, 0.0, 1.0)
            d = np.hypot(*(A + u[:, None] * AB - O).T)
            cache = (d < r) & (self.zid != k)
            ok &= ~cache
        return ok

    def occultation(self, C):
        """Masque des points vus en plan depuis la position C (s, t) : aucun bâtiment entre."""
        cle = (round(float(C[0]), 2), round(float(C[1]), 2))
        if cle not in self._occ:
            if self.bat is None or not len(self.P):
                self._occ[cle] = np.ones(len(self.P), bool)
            else:
                x, y = self.anc.vers_l93(C[0], C[1])
                self._occ[cle] = self.bat.visibles(float(x), float(y), self.XY)
            if self.ilots_opaques and len(self.P):
                self._occ[cle] = self._occ[cle] & self._masque_ilots(C)
        return self._occ[cle]

    def evaluer(self, cam, porteur):
        """Pour chaque zone vue : part pondérée des points vus, secteur et azimut d'observation, distance médiane,
        nombre de points vus. Renvoie {indice de zone: dict}."""
        import vues as V
        if not len(self.P):
            return {}
        uv, prof, devant = cam.projeter(self.P)
        ok = devant & (prof >= D_MIN) & (prof <= D_MAX) & self.occultation(cam.C)
        ok &= (uv[:, 0] >= 0) & (uv[:, 0] < cam.W) & (uv[:, 1] >= 0) & (uv[:, 1] < cam.H)
        if ok.any():
            r = cam.rayons(uv[ok])
            el = np.degrees(np.arcsin(np.clip(r[:, 2], -1, 1)))
            p = V.PORTEURS[porteur]
            bon = el > p["el_min"]
            if p["bas_masque"] > 0:
                bon &= uv[ok][:, 1] < cam.H * (1 - p["bas_masque"])
            idx = np.nonzero(ok)[0]
            ok[idx[~bon]] = False
        d = np.hypot(self.P[:, 0] - cam.C[0], self.P[:, 1] - cam.C[1])
        w = np.clip((D_MAX - d) / (D_MAX - D_PLEIN), 0.0, 1.0) * ok
        out = {}
        for k, z in enumerate(self.zones):
            m = self.zid == k
            n_vus = int(ok[m].sum())
            if n_vus == 0:
                continue
            f = float(w[m].sum() / m.sum())
            Q = self.P[m][ok[m]]
            cx, cy = float(Q[:, 0].mean()), float(Q[:, 1].mean())
            # azimut grille de la caméra vers le barycentre des points vus (si la caméra est dans la zone : sa visée)
            if math.hypot(cx - cam.C[0], cy - cam.C[1]) > 1.0:
                lac = math.degrees(math.atan2(cy - cam.C[1], cx - cam.C[0]))
            else:
                lac = cam.lacet
            az = self.anc.az_grille(lac)
            out[k] = {"part": round(f, 4), "n_vus": n_vus, "azimut_grille_deg": round(az, 1),
                      "secteur": int(round(az / 45.0)) % 8, "distance_m": round(float(np.median(d[m][ok[m]])), 1)}
        return out


def dans_ou_au_bord(zone, s, t, marge=3.0):
    from shapely.geometry import Point
    return zone.poly.distance(Point(s, t)) <= marge


# ------------------------------------------------------------------------------------------------ couverture
def couverture(zones, vues_eval, seuil=SEUIL_VOIT):
    """Bilan de couverture : vues_eval = [(cle, id_photo, {indice zone: éval})]. Par zone : vues qui la voient
    (part ≥ seuil), photos, secteurs couverts, part maximale, zone aveugle (aucune vue)."""
    out = []
    for k, z in enumerate(zones):
        vv = [(cle, pid, e[k]) for cle, pid, e in vues_eval if k in e and e[k]["part"] >= seuil]
        sect = sorted({e["secteur"] for _, _, e in vv})
        out.append({"zone": z.id, "type": z.type, "nom": z.nom, "poids": z.poids,
                    "n_vues": len(vv), "n_photos": len({pid for _, pid, _ in vv}),
                    "secteurs": [SECTEURS[s] for s in sect], "n_secteurs": len(sect),
                    "part_max": round(max([e["part"] for _, _, e in vv] or [0.0]), 3),
                    "aveugle": not vv,
                    "vues": [{"cle": cle, "part": e["part"], "secteur": SECTEURS[e["secteur"]], "distance_m": e["distance_m"]}
                             for cle, _, e in sorted(vv, key=lambda x: -x[2]["part"])]})
    return out
