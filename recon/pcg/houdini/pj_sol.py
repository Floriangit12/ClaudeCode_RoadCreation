"""pj_sol : sol de la zone pilote (chaussée, trottoirs, accès, espaces verts, îlots, BEV) en maillages
découpés exactement aux bordures posées.

Méthode (vectorielle, aucune décision au pixel) :
1. pour chaque bordure, bande occupée par les éléments : de la ligne avant (u = croisement du contour
   du profil, posé à sa vue, avec le niveau de la chaussée, + 12 mm SOUS la bordure) à la ligne
   arrière (u = base − 12 mm, sous la bordure) : le sol s'arrête sous l'élément, donc ni interstice ni
   recouvrement visible, même avec la flèche des éléments droits (≤ 10,5 mm) et le jitter (±1 mm) ;
2. triangulation 2D contrainte (Houdini Triangulate 2D, raffinée ≤ 0,25 m², angle ≥ 22°) de
   l'emprise pilote : lignes avant / arrière des bordures et lignes à 0,15 m de part et d'autre,
   limites de surfaces (hors 0,30 m autour des bordures, où la bordure fait foi), contour des modules
   BEV entiers (modules_bev) ; triangles des bandes retirés ;
3. classe et materiau_id par triangle : îlot (remplissage : polygone décrit ou intérieur de la ceinture
   fermée, côté haut de toutes les bordures de sa ceinture à moins de 2 m) > BEV > surface (polygones
   régularisés par pj_limites) contenant le centroïde ; à moins de 0,35 m d'une bordure : étiquette du
   côté, sondée à 0,40 / 0,70 m hors de la bande et lissée le long de la bordure ; gazon côté chaussée
   d'une bordure de chaussée (vue ≥ 6 cm, < 2 m) : revêtement de chaussée sondé plus loin ;
4. Z par sommet = MNT 2026 + corrections des bordures voisines (aucun maillage v1) :
   côté chaussée : fil d'eau de la description (MNT à 0,30 m de la face) jusqu'à 0,35 m, puis MNT ;
   côté haut : dessus de bordure − 4 mm à l'arête arrière, dévers de 1,5 % qui monte en s'éloignant
   de la chaussée, raccord au MNT sur D = 30·|écart| m (0,6-4 m, max glissant 3 m), pondération 1/d²
   entre bordures voisines ; extrémités de bordure : correction éteinte sur 0,6 m ;
   îlots : tête de ceinture (pondération 1/d⁴) − retrait + bombement, borné à 3-5 cm sous la tête
   locale de chaque bordure de ceinture ; arasement des surfaces marquées ;
   rampes derrière les bordures abaissées (regle:pj_sol.rampe_pmr, revue conformité r2) : rampe PLANE
   depuis la tête du bateau − 4 mm, sur la profondeur marchable (arrêt à 0,25 m d'une autre bordure, au
   premier revêtement non marchable ou à 4 m) : vers le niveau de la bordure qui arrête la rangée (≤ 4 %)
   ou pente moyenne du MNT (≤ 3,5 %) ; elle prime sur les corrections des autres bordures ; raccord au
   MNT au-delà, sur une longueur ∝ à l'écart ;
   massifs de BRF / gravier / paillage hors îlots (regle:pj_sol.decaisse_massif) : décaissés de 4 / 3 cm
   (talus dans le dernier rang de triangles du massif, le trottoir voisin reste plan) ;
   caniveaux : la chaussée s'arrête à leur bord (u = −largeur) au niveau fil d'eau + 2,5 cm (CS2) ;
   bornes près des faces : chaussée entre fil d'eau − 5 mm et tête − (vue − 5 mm) à moins de 0,15 m
   devant (vue réelle = vue décrite ± 5 mm), sol ≤ tête − 2 mm + 3,5 % à moins de 0,20 m derrière
   (aucune bordure enterrée, pas de sol au-dessus de la tête) ;
   pente maximale (regle:pj_sol.pente_max, revue UE du 10/10 : pointes de sol aux fins de bordure) : enveloppe
   inférieure z_v ≤ z_u + 0,5·|uv| près des bordures, hors noues, îlots et bord d'emprise (abaisse seulement) ;
   BEV : un plan par rangée de modules, raccordé autour (dalles 3D à fleur).
Limites de surfaces : polygones régularisés par pj_limites (arcs partagés, Douglas-Peucker, Chaikin,
calage sur les bordures, reprises neuf / ancien sciées).
UV st1 = (x, y) en mètres (BEV : repère de la bordure, dalles alignées) ; primvar `salissure`
(fil d'eau sur 10-25 cm, pied de bordure) ; un maillage par materiau_id, normales par sommet de face à
angle de rupture de 30° (lisses sur le terrain, cassées aux talus, marches et bords de bande) ; sous les
dalles podotactiles 3D (pj_decals), le sol BEV n'est visible que dans les joints (mortier sombre, Karma et
UE). Export UE (recon/pcg/ue/CONTRAT_EXPORT.md) : kinds, Material /World/Looks/<id> et liaison
material:binding:preview ; la liaison Karma (material:binding -> /World/Looks_v2) est inchangée.
"""
import math

import hou
import numpy as np

import pj_commun as K
import pj_usd as U
from pxr import Sdf, UsdGeom, Vt

C = K.C
T = Sdf.ValueTypeNames
CAT = hou.sopNodeTypeCategory()
MARGE = 0.012          # recouvrement du sol sous la bordure (m)
D_ROUTE = 0.35         # largeur du raccord chaussée -> MNT
DEVERS = 0.015         # dévers des trottoirs (monte en s'éloignant de la chaussée)
RETRAIT_TROTTOIR = 0.004
SONDE = 0.40
AIRE_MAX = 0.25
CLASSES_ECRETEES = ["enrobe_bbsg_ancien", "enrobe_bbsg_neuf_2025"]     # chaussées
PENTE_RAMPE = 0.035    # rampe derrière un abaissé (≤ 5 % visé, marge pour l'interpolation des triangles)
D_RAMPE = 4.0          # profondeur maximale du profil de rampe (m)
PENTE_MAX_SOL = 0.5    # regle:pj_sol.pente_max : pente maximale d'une arête du sol près des bordures (26,6°)
D_PENTE_MAX = 1.2      # rayon d'application autour des bordures (m)
CLASSES_TALUS = ["noue_plantee"]   # talus réels (pente non bornée)
MARCHABLES = ["enrobe_trottoir", "bev_podotactile", "enrobe_piste_cyclable", "beton_balaye", "dalles_beton",
              "paves_beton", "paves_granit", "stabilise_beige", "beton_desactive", "enrobe_bbsg_ancien",
              "enrobe_bbsg_neuf_2025", "enrobe_reprise_tranchee", "enrobe_clair_granulats", "enrobe_colore_ocre",
              "resine_verte", "resine_cyan"]
DECAISSE = {"brf_bois_concasse": 0.04, "gravier_concasse_6_10": 0.03, "paillage_mineral": 0.03,
            "gravillons_ilot": 0.03}


# --------------------------------------------------------------------------- profils posés
def u_route(specs, profil, vue):
    """u où la face avant du contour (posé à `vue`) coupe le niveau de la chaussée."""
    c = specs.contour(profil)
    base, H = specs.dims(profil)
    vr = H - vue
    i_top = int(np.argmax(c[:, 1] >= H - 1e-9))
    ch = c[:i_top + 1]
    for a, b in zip(ch[:-1], ch[1:]):
        if (a[1] - vr) * (b[1] - vr) <= 0 and abs(b[1] - a[1]) > 1e-12:
            t = (vr - a[1]) / (b[1] - a[1])
            return float(a[0] + t * (b[0] - a[0]))
    return 0.0 if vr <= ch[0][1] else float(ch[-1][0])


class Bande:
    """Échantillonnage d'une bordure : face (u = 0), lignes avant / arrière du sol, dessus, fil d'eau."""

    def __init__(self, B, specs):
        self.B = B
        bornes = [i["s0"] for i in B.iv[1:]]           # changements de profil / de vue : marches nettes
        for a_, b_ in (B.p.get("caniveau") or {}).get("intervalles", []):
            bornes += [float(B.s_nouveau(a_)), float(B.s_nouveau(b_))]
        s = np.unique(np.r_[B.S, np.arange(0.0, B.L, 0.10), B.L,
                            [x - 5e-4 for x in bornes], [x + 5e-4 for x in bornes]])
        s = s[(s >= 0.0) & (s <= B.L)]
        self.s = s
        self.P, _ = B.point(s)
        self.n = K.normales_gauches(self.P)       # sommets de polyligne : moyenne des deux côtés
        self.vue = B.vue(s)
        self.zfe = B.z_fe(s)
        uf, ub, base, dzr = [], [], [], []
        for x, v in zip(s, self.vue):
            iv = B.intervalle(x)
            prof = iv["profil"]
            b, _ = specs.dims(prof)
            cv = B.caniveau_a(x)
            if cv is not None:                   # caniveau devant la face : la chaussée s'arrête à son bord
                larg, h_bord, h_ch = specs.caniveau(cv)
                uf.append(-larg + MARGE)
                ub.append(b - MARGE)
                base.append(b)
                dzr.append(h_ch - h_bord)
                continue
            dzr.append(0.0)
            if iv["role"] == "chartiere":
                pb = B.profil_bas(iv)
                t = (x - iv["s0"]) / max(iv["s1"] - iv["s0"], 1e-9)
                hi, lo = max(iv["vue_m"], iv["vue_m_fin"]), min(iv["vue_m"], iv["vue_m_fin"])
                th = (1 - t) if iv["vue_m"] > iv["vue_m_fin"] else t
                u = th * u_route(specs, prof, hi) + (1 - th) * u_route(specs, pb, lo)
                b = th * b + (1 - th) * specs.dims(pb)[0]       # loft : base du profil haut vers celle du bas
            else:
                u = u_route(specs, prof, float(v))
            uf.append(u + MARGE)
            ub.append(b - MARGE)
            base.append(b)
        self.uf, self.ub, self.base = np.array(uf), np.array(ub), np.array(base)
        self.zroute = self.zfe + np.array(dzr)          # niveau de chaussée au bord avant (caniveau : + 2,5 cm)
        self.avant = self.P + self.n * self.uf[:, None]
        self.arriere = self.P + self.n * self.ub[:, None]
        self.ztop = self.zfe + self.vue
        lo = np.minimum(self.avant.min(axis=0), self.arriere.min(axis=0))
        hi = np.maximum(self.avant.max(axis=0), self.arriere.max(axis=0))
        self.bbox = (lo, hi)

    def projeter(self, Q):
        """(s, d_gauche signé, distance, dépassement des bouts) des points Q sur la face."""
        F = self.B.P
        s, d, cote = C.projeter(F, Q)
        # dépassement : distance au-delà des extrémités le long de la tangente
        P0, P1 = F[0], F[-1]
        t0 = (F[1] - P0) / max(np.hypot(*(F[1] - P0)), 1e-12)
        t1 = (P1 - F[-2]) / max(np.hypot(*(P1 - F[-2])), 1e-12)
        e0 = np.maximum(-(Q - P0) @ t0, 0.0)
        e1 = np.maximum((Q - P1) @ t1, 0.0)
        ex = np.where(s <= 1e-6, e0, np.where(s >= self.B.L - 1e-6, e1, 0.0))
        dl = d * cote
        # au-delà d'un bout, la distance latérale est mesurée perpendiculairement à la tangente
        lat0 = (Q - P0) @ np.array([-t0[1], t0[0]])
        lat1 = (Q - P1) @ np.array([-t1[1], t1[0]])
        dl = np.where(s <= 1e-6, lat0, np.where(s >= self.B.L - 1e-6, lat1, dl))
        return s, dl, d, ex

    def interp(self, champ, s):
        return np.interp(s, self.s, champ)


# --------------------------------------------------------------------------- outils 2D
def couper_rect(Q, R, eps=1e-9):
    """Morceaux d'une polyligne à l'intérieur du rectangle R = (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = R
    dedans = lambda p: x0 - eps <= p[0] <= x1 + eps and y0 - eps <= p[1] <= y1 + eps
    morceaux, cur = [], []
    for i in range(len(Q)):
        p = Q[i]
        if dedans(p):
            if not cur and i > 0:
                cur.append(_inter_rect(Q[i - 1], p, R))
            cur.append(p)
        else:
            if cur:
                cur.append(_inter_rect(cur[-1], p, R))
                morceaux.append(np.array(cur))
                cur = []
    if cur:
        morceaux.append(np.array(cur))
    return [m for m in morceaux if len(m) >= 2]


def _inter_rect(a, b, R):
    """Point de [a, b] sur le bord du rectangle (a dedans ou b dedans)."""
    x0, y0, x1, y1 = R
    lo, hi = 0.0, 1.0
    ina = x0 <= a[0] <= x1 and y0 <= a[1] <= y1
    for _ in range(40):
        m = 0.5 * (lo + hi)
        p = a + (b - a) * m
        inside = x0 <= p[0] <= x1 and y0 <= p[1] <= y1
        if inside == ina:
            lo = m
        else:
            hi = m
    return a + (b - a) * (0.5 * (lo + hi))


def simplifier(Q, tol):
    """Douglas-Peucker (itératif) : sommets à garder pour un écart max `tol`."""
    Q = np.asarray(Q, dtype=np.float64)
    if len(Q) < 3:
        return Q
    garde = np.zeros(len(Q), dtype=bool)
    garde[[0, -1]] = True
    pile = [(0, len(Q) - 1)]
    while pile:
        i, j = pile.pop()
        if j <= i + 1:
            continue
        a, b = Q[i], Q[j]
        d = b - a
        L = max(np.hypot(*d), 1e-12)
        e = np.abs((Q[i + 1:j, 0] - a[0]) * d[1] - (Q[i + 1:j, 1] - a[1]) * d[0]) / L
        k = int(np.argmax(e))
        if e[k] > tol:
            garde[i + 1 + k] = True
            pile += [(i, i + 1 + k), (i + 1 + k, j)]
    return Q[garde]


def densifier(Q, pas, ferme=False):
    Q = np.asarray(Q, dtype=np.float64)
    if ferme:
        Q = np.vstack([Q, Q[:1]])
    out = [Q[0]]
    for a, b in zip(Q[:-1], Q[1:]):
        n = max(1, int(math.ceil(np.hypot(*(b - a)) / pas)))
        for k in range(1, n + 1):
            out.append(a + (b - a) * k / n)
    out = np.array(out)
    return out[:-1] if ferme else out


# --------------------------------------------------------------------------- sol
class Sol:
    def __init__(self, desc, specs, log=print):
        self.desc, self.specs, self.log = desc, specs, log
        self.R = desc.zone
        self.bandes = {B.id: Bande(B, specs) for B in desc.bordures}

    # ---------------------------------------------------------------- triangulation
    def contraintes(self):
        R = self.R
        lignes = []
        for bid in sorted(self.bandes):
            b = self.bandes[bid]
            for Q in (b.avant, b.arriere):
                lignes += couper_rect(simplifier(Q, 0.002), R)
            for k in (0, -1):
                lignes += couper_rect(np.array([b.avant[k], b.arriere[k]]), R)
            # lignes à 0,15 m de part et d'autre de la bande : des sommets proches de la face portent les
            # bornes de corriger() (chaussée sous la tête, trottoir pas au-dessus) ; écartées là où le
            # décalage se replie (nez de petit rayon)
            for u_off in (b.uf - 0.15, b.ub + 0.15):
                O = b.P + b.n * u_off[:, None]
                s_, dl_, d_, ex_ = b.projeter(O)
                ok = (np.abs(dl_ - u_off) < 0.02) & (ex_ <= 0)
                i = 0
                while i < len(O):
                    if not ok[i]:
                        i += 1
                        continue
                    j = i
                    while j + 1 < len(O) and ok[j + 1]:
                        j += 1
                    if j - i >= 3:
                        lignes += couper_rect(simplifier(O[i:j + 1], 0.003), R)
                    i = j + 1
        # limites des surfaces, hors abords des bordures
        A = np.vstack([b.P[:-1] for b in self.bandes.values()])
        Bq = np.vstack([b.P[1:] for b in self.bandes.values()])
        for srf in self.desc.surfaces:
            for poly in srf.get("polys_fab", srf["polys"]):
                for r in poly:
                    Q = densifier(r, 0.25, ferme=True)
                    Q = np.vstack([Q, Q[:1]])
                    d, _, _ = C.distance_segments(Q, A, Bq)
                    garde = d > 0.30
                    i = 0
                    while i < len(Q):
                        if garde[i]:
                            j = i
                            while j + 1 < len(Q) and garde[j + 1]:
                                j += 1
                            if j > i:
                                lignes += couper_rect(Q[i:j + 1], R)
                            i = j + 1
                        else:
                            i += 1
        # BEV : contour des modules entiers posés (pj_sol.modules_bev ; plus de fragment rogné)
        self.bev = []
        for pc, mods in self.modules_bev():
            if not mods:
                continue
            r = self.contour_modules(mods)
            self.bev.append((pc, r))
            lignes.append(np.vstack([densifier(r, 0.2, ferme=True), r[:1]]))
        x0, y0, x1, y1 = R
        cadre = densifier(np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), 0.5, ferme=True)
        lignes.append(np.vstack([cadre, cadre[:1]]))
        return [densifier(l, 0.30) for l in lignes if len(l) >= 2]

    def modules_bev(self):
        """Modules de dalles podotactiles posés (regle:pj_sol.bev_modules, revue conformité r2 : BEV-0388-1 en
        deux morceaux dont un éclat de 0,03 m²) : modules entiers de module_m alignés sur l'abaissé, de
        `retrait_nez_m` à `retrait_nez_m + profondeur_m` de la face, centrés sur [s0, s1] ; un module n'est gardé
        que si ses 4 coins sont dans le contour décrit (à 2 cm près). Renvoie [(ponctuel, [module])], module =
        {s, u, centre, tangente, coins, demi}."""
        if hasattr(self, "_modules_bev"):
            return self._modules_bev
        out = []
        for pc in sorted(self.desc.ponctuels, key=lambda x: x["id"]):
            p = pc["p"]
            if p.get("type") != "bev":
                continue
            an = p["ancrage"]
            b = self.bandes.get(an["bordure"])
            mods = []
            if b is not None:
                B = b.B
                s0, s1 = float(B.s_nouveau(an["s0"])), float(B.s_nouveau(an["s1"]))
                mod = float((p.get("module_m") or [0.4, 0.4])[0])
                prof = float(p.get("profondeur_m", 0.4))
                ret = float(p.get("retrait_nez_m", 0.5))
                n = int(math.floor((s1 - s0) / mod + 1e-6))
                marge = 0.5 * ((s1 - s0) - n * mod)
                r = pc["rings"][0][:, :2]
                if np.allclose(r[0], r[-1]):
                    r = r[:-1]
                A_, B_ = C.aretes([r])
                for k in range(max(n, 0)):
                    sc = s0 + marge + (k + 0.5) * mod
                    for jr in range(max(1, int(round(prof / mod)))):
                        uc = ret + (jr + 0.5) * mod
                        q, tg = B.point(sc)
                        nl = np.array([-tg[0, 1], tg[0, 0]])
                        c = q[0] + nl * uc
                        h = 0.5 * mod
                        coins = np.array([c + tg[0] * dx + nl * dy for dx, dy in ((-h, -h), (h, -h), (h, h), (-h, h))])
                        d, _, _ = C.distance_segments(coins, A_, B_)
                        if np.all(C.dans_polygone(coins, [r]) | (d < 0.02)) and not self._sous_bordure(coins):
                            mods.append({"s": sc, "u": uc, "centre": c, "tangente": tg[0], "coins": coins, "demi": h,
                                         "id": f"{pc['id']}/D{k:02d}{jr}"})
            out.append((pc, mods))
        self._modules_bev = out
        return out

    def _sous_bordure(self, coins, marge=0.01):
        """Vrai si le module (4 coins, bords et centre échantillonnés) empiète sur l'emprise d'un élément de bordure
        (de la face vue à la base + marge ; revue UE du 10/10 : dernière paire du BEV de K-0385 posée sur la
        bordurette P1 K-9297a, basculée de 4 cm)."""
        u, v = np.meshgrid(np.linspace(0.0, 1.0, 9), np.linspace(0.0, 1.0, 9))          # pas de 5 cm
        u, v = u.ravel()[:, None], v.ravel()[:, None]
        Q = (1 - u) * (1 - v) * coins[0] + u * (1 - v) * coins[1] + u * v * coins[2] + (1 - u) * v * coins[3]
        for bid, m, s, dl, d, ex in self.projections(Q, rayon=0.5):
            b = self.bandes[bid]
            base = b.interp(b.base, s)
            if np.any((ex <= marge) & (dl >= -marge) & (dl <= base + marge)):
                return True
        return False

    @staticmethod
    def contour_modules(mods):
        """Contour (anneau) de modules alignés : rectangle du premier au dernier module (une rangée), sinon
        enveloppe des coins."""
        t = mods[0]["tangente"]
        nl = np.array([-t[1], t[0]])
        o = mods[0]["centre"]
        X = np.vstack([m["coins"] for m in mods])
        a, b = (X - o) @ t, (X - o) @ nl
        return np.array([o + t * a.min() + nl * b.min(), o + t * a.max() + nl * b.min(),
                         o + t * a.max() + nl * b.max(), o + t * a.min() + nl * b.max()])

    def trianguler(self):
        lignes = self.contraintes()
        g = hou.Geometry()
        polys = []
        o = 0
        pts = []
        for l in lignes:
            pts += [hou.Vector3(float(p[0]), float(p[1]), 0.0) for p in l]
            polys.append(tuple(range(o, o + len(l))))
            o += len(l)
        g.createPoints(pts)
        for pl in polys:
            pr = g.createPolygon(is_closed=False)
            for i in pl:
                pr.addVertex(g.point(i))
        grp = g.createPrimGroup("contraintes")
        grp.add(g.prims())
        v = CAT.nodeVerb("triangulate2d::3.0")
        v.setParms({"planepossrc": 1, "origin": hou.Vector3(0, 0, 0), "dir": hou.Vector3(0, 0, 1),
                    "useconstrpolys": 1, "constrpolys": "contraintes", "allowconstrsplit": 1,
                    "removeduplicatepoints": 1, "refine": 1, "trianglesize": 1, "maxarea": AIRE_MAX,
                    "minangle": 22.0, "maxnewpts": 2000000, "keepprims": 0, "removeunusedpoints": 1})
        out = hou.Geometry()
        v.execute(out, [g])
        P = np.array(out.pointFloatAttribValues("P"), dtype=np.float64).reshape(-1, 3)[:, :2]
        tris = []
        for pr in out.prims():
            vs = pr.vertices()
            if len(vs) == 3:
                tris.append((vs[0].point().number(), vs[2].point().number(), vs[1].point().number()))
        tris = np.array(tris, dtype=np.int64)
        # orientation : normales vers +Z (sens direct)
        a, b, c = P[tris[:, 0]], P[tris[:, 1]], P[tris[:, 2]]
        cr = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
        tris[cr < 0] = tris[cr < 0][:, [0, 2, 1]]
        keep = np.abs(cr) > 1e-10
        self.log(f"   triangulation : {len(P)} points, {keep.sum()} triangles, {len(lignes)} contraintes")
        return P, tris[keep]

    # ---------------------------------------------------------------- classes
    def projections(self, Q, rayon=4.5):
        """Pour chaque bordure proche : (bid, indices, s, dl, d, ex)."""
        out = []
        for bid in sorted(self.bandes):
            b = self.bandes[bid]
            lo, hi = b.bbox
            m = np.where((Q[:, 0] > lo[0] - rayon) & (Q[:, 0] < hi[0] + rayon) &
                         (Q[:, 1] > lo[1] - rayon) & (Q[:, 1] < hi[1] + rayon))[0]
            if len(m) == 0:
                continue
            s, dl, d, ex = b.projeter(Q[m])
            out.append((bid, m, s, dl, d, ex))
        return out

    def classer(self, P, tris):
        G = P[tris].mean(axis=1)
        n = len(G)
        dans_bande = np.zeros(n, dtype=bool)
        proche = np.full(n, np.inf)
        cote = np.zeros(n)
        pied = np.zeros((n, 2))
        nrm = np.zeros((n, 2))
        ub_proche = np.zeros(n)
        bid_proche = np.full(n, "", dtype=object)
        s_proche = np.zeros(n)
        for bid, m, s, dl, d, ex in self.projections(G, rayon=1.0):
            b = self.bandes[bid]
            uf, ub = b.interp(b.uf, s), b.interp(b.ub, s)
            interieur = (s > 1e-6) & (s < b.B.L - 1e-6) & (dl > uf) & (dl < ub)
            dans_bande[m[interieur]] = True
            mieux = d < proche[m]
            mm = m[mieux]
            proche[mm] = d[mieux]
            cote[mm] = np.sign(dl[mieux] - 0.5 * (uf[mieux] + ub[mieux]))
            pts, tg = C.point_a(b.P, s[mieux])
            pied[mm] = pts
            nrm[mm] = np.c_[-tg[:, 1], tg[:, 0]]
            ub_proche[mm] = ub[mieux]
            bid_proche[mm] = bid
            s_proche[mm] = s[mieux]
        garde = ~dans_bande
        # îlots (remplissages)
        classe = np.full(n, "", dtype=object)
        ilot = np.full(n, "", dtype=object)
        for il in self.desc.ilots:
            m = np.where(garde)[0]
            dedans = C.dans_polygones(G[m], il["polys"])
            an = self.anneau_ceinture(il)
            if an is not None:                 # tout l'intérieur de la ceinture fermée (revue conformité r2 :
                dedans |= C.dans_polygone(G[m], [an])     # enrobé dans I-0629 près de K-0629z)
            m = m[dedans]
            if len(m) == 0:
                continue
            # côté haut de TOUTES les bordures de ceinture à moins de 2 m (les nez arrondis rognent le
            # polygone ; un polygone v1 plus large que la ceinture ne déborde pas au-delà d'une bordure)
            dmin = np.full(len(m), np.inf)
            ok = np.ones(len(m), dtype=bool)
            for bid in il["p"].get("ceinture", []):
                b = self.bandes.get(bid)
                if b is None:
                    continue
                s, dl, d, ex = b.projeter(G[m])
                ub = b.interp(b.ub, s)
                proche_b = (d < 2.0) & (ex < 0.05)
                ok &= ~proche_b | (dl >= ub - 1e-3)
                ok &= ~((d < 0.6) & (ex >= 0.05))              # au-delà d'un bout de ceinture : hors îlot
                dmin = np.minimum(dmin, d)
            ok |= dmin > 3.0
            ilot[m[ok]] = il["id"]
            classe[m[ok]] = il["p"]["remplissage"]["materiau_id"]
        # BEV
        bev_de = np.full(n, "", dtype=object)
        for pc, r in self.bev:
            m = np.where(garde & (classe == ""))[0]
            dd = C.dans_polygone(G[m], [r])
            bev_de[m[dd]] = pc["id"]
            classe[m[dd]] = pc["p"].get("materiau_id", "bev_podotactile")
        # surfaces (sonde hors bande près des bordures)
        sonde = G.copy()
        pres = garde & (proche < 0.35) & (classe == "")
        dec = np.where(cote > 0, ub_proche + SONDE, -SONDE)
        sonde[pres] = pied[pres] + nrm[pres] * dec[pres][:, None]
        surf = np.full(n, "", dtype=object)
        # près d'une bordure : étiquette du côté (sondes à 0,40 / 0,70 m hors de la bande, mode glissant sur
        # ±0,8 m le long de la bordure) : une limite raster qui traverse la bordure ne fait plus d'enclave
        pres_i = np.where(pres)[0]
        if len(pres_i):
            et = self.etiquettes_cotes()
            for i in pres_i:
                lab = et.get((bid_proche[i], int(cote[i] > 0)))
                if lab is None:
                    continue
                ss, ll = lab
                k = int(np.clip(round(s_proche[i] / (ss[1] - ss[0] if len(ss) > 1 else 1.0)), 0, len(ss) - 1))
                if ll[k]:
                    surf[i] = ll[k]
        reste = np.where(garde & (classe == "") & (surf == ""))[0]
        for srf in self.desc.surfaces:
            if len(reste) == 0:
                break
            dd = C.dans_polygones(sonde[reste], srf.get("polys_fab", srf["polys"]))
            surf[reste[dd]] = srf["id"]
            reste = reste[~dd]
        if len(reste):                       # sonde hors de toute surface : centroïde
            for srf in self.desc.surfaces:
                dd = C.dans_polygones(G[reste], srf.get("polys_fab", srf["polys"]))
                surf[reste[dd]] = srf["id"]
                reste = reste[~dd]
                if len(reste) == 0:
                    break
        if len(reste):                       # trous entre polygones v1 : surface du voisin le plus proche
            ok = np.where(garde & (surf != ""))[0]
            for i in reste:
                j = ok[np.argmin(np.hypot(*(G[ok] - G[i]).T))]
                surf[i] = surf[j]
        par_id = {s["id"]: s for s in self.desc.surfaces}
        # gazon côté chaussée d'une bordure de chaussée (vue ≥ 6 cm) à moins de 2 m de sa face : polygone d'herbe
        # d'origine raster qui déborde sur la chaussée (revue réalisme r2, vue c) -> revêtement de chaussée sondé
        # plus loin du même côté
        herbes = ("gazon_tondu", "herbe_haute", "gazon_sec")
        cand = np.where(garde & (classe == "") & np.array([bool(x) and par_id[x]["p"]["revetement"]["materiau_id"] in herbes
                                                            for x in surf], dtype=bool))[0]
        self.n_herbe_chaussee = 0
        if len(cand):
            dmin = np.full(len(cand), np.inf)
            nouv = np.full(len(cand), "", dtype=object)
            for bid, m, s, dl, d, ex in self.projections(G[cand], rayon=2.0):
                b = self.bandes[bid]
                uf = b.interp(b.uf, s)
                ok = (ex <= 0) & (dl < uf) & (d < 2.0) & (d < dmin[m]) & (b.interp(b.vue, s) >= 0.06)
                for i in np.where(ok)[0]:
                    lab = self._label_route(b, float(s[i]))
                    if lab:
                        nouv[m[i]] = lab
                        dmin[m[i]] = d[i]
            for i, lab in zip(cand, nouv):
                if lab:
                    surf[i] = lab
                    self.n_herbe_chaussee += 1
        # surfaces « ilot » v1 dont les îlots sont décrits : hors des remplissages, c'est la chaussée
        # voisine (nez arrondis, polygones v1 plus larges que la ceinture)
        orph = np.array([bool(sid) and par_id[sid]["p"]["classe"] == "ilot" and bool(par_id[sid]["p"].get("ilots"))
                         for sid in surf]) & garde & (classe == "")
        if orph.any():
            ok = np.where(garde & (classe == "") & ~orph & (surf != ""))[0]
            ok = ok[np.array([par_id[surf[j]]["p"]["classe"] != "ilot" for j in ok], dtype=bool)]
            for i in np.where(orph)[0]:
                j = ok[np.argmin(np.hypot(*(G[ok] - G[i]).T))]
                surf[i] = surf[j]
        self.n_orphelins_ilot = int(orph.sum())
        for i in np.where(garde & (classe == ""))[0]:
            classe[i] = par_id[surf[i]]["p"]["revetement"]["materiau_id"]
        self.n_bande = int(dans_bande.sum())
        return garde, classe, surf, ilot, bev_de

    def _label_route(self, b, s):
        """Première surface de chaussée (enrobé de chaussée) sondée côté bas de la bordure à 0,4-4 m de la face."""
        cle = (b.B.id, round(s, 1))
        cache = self.__dict__.setdefault("_cache_route", {})
        if cle not in cache:
            cache[cle] = self._label_route_calc(b, round(s, 1))
        return cache[cle]

    def _label_route_calc(self, b, s):
        q, tg = C.point_a(b.B.P, np.array([s]))
        nl = np.array([-tg[0, 1], tg[0, 0]])
        uf = float(b.interp(b.uf, s))
        for off in (0.4, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0):
            Q = (q[0] + nl * (uf - off))[None]
            for srf in self.desc.surfaces:
                if C.dans_polygones(Q, srf.get("polys_fab", srf["polys"]))[0]:
                    if srf["p"]["revetement"]["materiau_id"] in CLASSES_ECRETEES:
                        return srf["id"]
                    break
        return ""

    def anneau_ceinture(self, il, tol=1.0):
        """Polygone fermé des faces vues de la ceinture d'un îlot (bordures chaînées par leurs extrémités à
        moins de `tol` m), ou None si la ceinture ne se referme pas."""
        if not hasattr(self, "_anneaux_c"):
            self._anneaux_c = {}
        if il["id"] in self._anneaux_c:
            return self._anneaux_c[il["id"]]
        lignes = [self.bandes[k].P for k in il["p"].get("ceinture", []) if k in self.bandes]
        an = None
        if len(lignes) == 1 and np.hypot(*(lignes[0][0] - lignes[0][-1])) < tol:
            an = lignes[0]
        elif lignes:
            ch, reste = lignes[0].copy(), lignes[1:]
            while reste:
                d = [(min(np.hypot(*(l[0] - ch[-1])), np.hypot(*(l[-1] - ch[-1]))), i) for i, l in enumerate(reste)]
                dmin, i = min(d)
                if dmin > tol:
                    break
                l = reste.pop(i)
                ch = np.vstack([ch, l if np.hypot(*(l[0] - ch[-1])) <= np.hypot(*(l[-1] - ch[-1])) else l[::-1]])
            if not reste and np.hypot(*(ch[0] - ch[-1])) < tol:
                an = ch
        self._anneaux_c[il["id"]] = an
        return an

    def etiquettes_cotes(self, pas=0.2, demi=0.8):
        """{(bordure, côté haut ?): (s, surface)} : surface sondée à 0,40 m (à défaut 0,70 m) au-delà de la
        bande de part et d'autre de chaque bordure, lissée par mode glissant sur ±demi."""
        if hasattr(self, "_etiq"):
            return self._etiq
        out = {}
        for bid in sorted(self.bandes):
            b = self.bandes[bid]
            ss = np.arange(0.0, b.B.L + 1e-9, pas)
            q, tg = C.point_a(b.B.P, ss)
            nl = np.c_[-tg[:, 1], tg[:, 0]]
            for haut in (0, 1):
                labs = np.full(len(ss), "", dtype=object)
                for off in (0.40, 0.70):
                    u = b.interp(b.ub, ss) + off if haut else b.interp(b.uf, ss) - off
                    Q = q + nl * u[:, None]
                    vide = np.where(labs == "")[0]
                    for srf in self.desc.surfaces:
                        if len(vide) == 0:
                            break
                        dd = C.dans_polygones(Q[vide], srf.get("polys_fab", srf["polys"]))
                        labs[vide[dd]] = srf["id"]
                        vide = vide[~dd]
                k = int(round(demi / pas))
                lisse = labs.copy()
                for i in range(len(ss)):
                    w = [x for x in labs[max(0, i - k):i + k + 1] if x]
                    if w:
                        vals, cnt = np.unique(np.array(w, dtype=str), return_counts=True)
                        best = vals[cnt == cnt.max()]
                        lisse[i] = labs[i] if labs[i] in best else str(best[0])
                out[(bid, haut)] = (ss, lisse)
        self._etiq = out
        return out

    # ---------------------------------------------------------------- altitudes
    def corriger(self, P, z0):
        """Corrections des bordures voisines sur un MNT : renvoie (z, salissure).
        Pondération 1/d² (transitions douces entre bordures voisines) ; derrière un
        abaissé, la cible du côté haut est le profil de rampe (déjà dans z0) ; bornes finales (revue
        conformité r1 : bordures enterrées, sol au-dessus de la tête) : à moins de 0,15 m devant la face,
        chaussée ≤ tête − max(5 mm, vue / 2) ; à moins de 0,20 m derrière, sol ≤ tête − 2 mm + 4 % (des
        lignes de contrainte à 0,15 m de la bande portent des sommets à ces distances)."""
        n = len(P)
        num = np.zeros(n)
        den = np.zeros(n)
        prod = np.ones(n)
        sal = np.zeros(n)
        borne = np.full(n, np.inf)
        borne_bas = np.full(n, -np.inf)
        self.stats_D = []
        _, w_r, bid_r = self.rampes(P, None)
        for bid, m, s, dl, d, ex in self.projections(P, rayon=4.5):
            b = self.bandes[bid]
            uf, ub = b.interp(b.uf, s), b.interp(b.ub, s)
            zfe, ztop = b.interp(b.zroute, s), b.interp(b.ztop, s)
            fin = 1.0 - K.smoothstep(ex / 0.6)
            # côté chaussée
            dd = uf - dl
            route = dd >= -0.004                      # sommets des lignes de bande : tolérance 4 mm
            vue_s = b.interp(b.vue, s)
            cible_r = zfe - np.where((np.abs(dd) < 0.004) & (vue_s < 0.006), 0.003, 0.0)   # bordure à niveau : pas de z-fighting
            f_r = (1.0 - K.smoothstep(np.maximum(dd - 0.30, 0.0) / (D_ROUTE - 0.30 + 0.25))) * fin
            # côté haut
            dp = dl - ub
            haut = dp >= -0.004
            Dh = self._D_haut(b)
            Dh_s = b.interp(Dh, s)
            cible_h = ztop - RETRAIT_TROTTOIR + DEVERS * np.maximum(dp, 0.0)
            wr = np.where(bid_r[m] == bid, w_r[m], 0.0)                   # rampe d'abaissé : profil imposé (z0)
            cible_h = cible_h * (1.0 - wr) + z0[m] * wr
            f_h = (1.0 - K.smoothstep(np.maximum(dp, 0.0) / Dh_s)) * fin
            # bornes près de la face (hors bouts de bordure)
            ok_b = ex <= 0
            # vue réelle = vue décrite ± 5 mm (revue conformité r2 : bateau d'A-0178-1 à 9,5 mm au lieu de
            # 20, vues gonflées de 3 à 6 cm) : chaussée entre fil d'eau − 5 mm et tête − (vue − 5 mm)
            pres_r = ok_b & route & (dd < 0.15 + (uf - np.minimum(uf, 0.0)))
            borne[m[pres_r]] = np.minimum(borne[m[pres_r]], (ztop - np.maximum(0.004, vue_s - 0.005))[pres_r])
            borne_bas[m[pres_r]] = np.maximum(borne_bas[m[pres_r]], (zfe - 0.005 - np.where(vue_s < 0.006, 0.003, 0.0))[pres_r])
            pres_h = ok_b & haut & ~route & (dp < 0.2)
            borne[m[pres_h]] = np.minimum(borne[m[pres_h]], (ztop - 0.002 + PENTE_RAMPE * np.maximum(dp, 0.0))[pres_h])
            for msk, cible, f, dist in ((route & (d < 4.5), cible_r, f_r, np.maximum(dd, 0.0)),
                                        (haut & ~route, cible_h, f_h, np.maximum(dp, 0.0))):
                mm = m[msk]
                if len(mm) == 0:
                    continue
                c = cible[msk] - z0[mm]
                # rampe d'abaissé d'une AUTRE bordure (plan déjà calé sur le niveau de cette bordure) : elle prime
                # (revue conformité r2 : la pondération 1/d² entre deux bordures faisait des S à 8-10 %)
                ff = f[msk] * (1.0 - np.where(bid_r[mm] != bid, w_r[mm], 0.0))
                w = ff / np.maximum(dist[msk], 0.004) ** 2
                num[mm] += w * c
                den[mm] += w
                prod[mm] *= 1.0 - ff
            # salissure : fil d'eau devant la face, pied arrière
            mm = m[route]
            sal[mm] = np.maximum(sal[mm], 0.9 * np.exp(-np.maximum(dd[route], 0) / 0.18) * fin[route])   # fil d'eau : bande de 10-25 cm (revue réalisme r2)
            mm = m[haut & ~route]
            sal[mm] = np.maximum(sal[mm], 0.25 * np.exp(-np.maximum(dp[haut & ~route], 0) / 0.08) * fin[haut & ~route])
        F = 1.0 - prod
        z = z0 + np.where(den > 0, F * num / np.maximum(den, 1e-30), 0.0)
        return np.minimum(np.maximum(z, borne_bas), borne), sal

    def z_points(self, Q):
        """Altitude du sol v2 en des points quelconques (contexte : raccords, fondu du v1)."""
        Q = np.asarray(Q, dtype=np.float64)[:, :2]
        z, _ = self.corriger(Q, self.mnt_corrige(Q))
        if getattr(self, "z_ilots", None):
            for il in self.desc.ilots:
                if il["id"] not in self.z_ilots:
                    continue
                m = np.where(C.dans_polygones(Q, il["polys"]))[0]
                vs = self.z_ilots[il["id"]][0]
                for i in m:
                    j = vs[np.argmin(np.hypot(*(self.P3[vs, :2] - Q[i]).T))]
                    z[i] = self.P3[j, 2]
        return z

    def ouverture_mnt(self, Q, fenetre=1.3, pas=0.1):
        """Ouverture morphologique du MNT (érosion puis dilatation, fenêtre carrée de 1,3 m) : enlève
        les reliefs étroits (anciens îlots, pointes effilées, flou des marches de bordure) et garde les
        pentes et bombements de la chaussée (une fonction linéaire est invariante)."""
        if not hasattr(self, "_ouv"):
            x0, y0, x1, y1 = self.R
            xs = np.arange(x0 - 2.0, x1 + 2.0 + 1e-9, pas)
            ys = np.arange(y0 - 2.0, y1 + 2.0 + 1e-9, pas)
            X, Y = np.meshgrid(xs, ys)
            Z = K.mnt_local(X, Y)
            k = int(round(fenetre / pas)) | 1
            h = k // 2
            from numpy.lib.stride_tricks import sliding_window_view as fen

            def filtre(A, f):
                A = f(fen(np.pad(A, ((0, 0), (h, h)), mode="edge"), k, axis=1), axis=-1)
                return f(fen(np.pad(A, ((h, h), (0, 0)), mode="edge"), k, axis=0), axis=-1)
            self._ouv = (xs, ys, filtre(filtre(Z, np.min), np.max))
        xs, ys, O = self._ouv
        fx = np.clip((Q[:, 0] - xs[0]) / (xs[1] - xs[0]), 0, len(xs) - 1.000001)
        fy = np.clip((Q[:, 1] - ys[0]) / (ys[1] - ys[0]), 0, len(ys) - 1.000001)
        c, r = np.floor(fx).astype(int), np.floor(fy).astype(int)
        tx, ty = fx - c, fy - r
        return ((O[r, c] * (1 - tx) + O[r, c + 1] * tx) * (1 - ty) + (O[r + 1, c] * (1 - tx) + O[r + 1, c + 1] * tx) * ty)

    def altitudes(self, P, tris, garde, classe, surf, ilot):
        z0 = self.mnt_corrige(P)
        # chaussées : reliefs étroits du MNT écrêtés (îlots anciens ou raccourcis par les nez arrondis)
        route = np.zeros(len(P), dtype=bool)
        for k in np.where(garde & np.isin(classe, CLASSES_ECRETEES))[0]:
            route[tris[k]] = True
        for k in np.where(garde & ~np.isin(classe, CLASSES_ECRETEES))[0]:
            route[tris[k]] = False
        if route.any():
            zo = self.ouverture_mnt(P[route]) + 0.01
            self.n_ecretes = int((z0[route] > zo).sum())
            z0[route] = np.minimum(z0[route], zo)
        z, sal = self.corriger(P, z0)
        # massifs (BRF, gravier, paillage) hors îlots : décaissés sous le niveau voisin, talus d'un triangle
        G_ = P[tris]
        aire = 0.5 * np.abs((G_[:, 1, 0] - G_[:, 0, 0]) * (G_[:, 2, 1] - G_[:, 0, 1]) -
                            (G_[:, 1, 1] - G_[:, 0, 1]) * (G_[:, 2, 0] - G_[:, 0, 0]))
        ret_t = np.array([DECAISSE.get(c, 0.0) if i_ == "" else 0.0 for c, i_ in zip(classe, ilot)]) * garde
        num = np.zeros(len(P))
        autre = np.zeros(len(P))
        for k in range(3):
            np.add.at(num, tris[:, k], ret_t)
            np.add.at(autre, tris[:, k], ((ret_t == 0) & garde).astype(float))
        n_inc = np.zeros(len(P))
        for k in range(3):
            np.add.at(n_inc, tris[:, k], (ret_t > 0).astype(float))
        # sommets entourés de massif seulement : le talus reste dans le massif, le trottoir voisin ne penche pas
        dec = np.where((autre == 0) & (n_inc > 0), num / np.maximum(n_inc, 1), 0.0)
        z = z - np.maximum(dec - RETRAIT_TROTTOIR * (dec > 0), 0.0)
        self.n_decaisses = int((dec > 0).sum())

        # îlots : dessus de ceinture − retrait + bombement
        sommets_ilot = {}
        for k in np.where(garde & (ilot != ""))[0]:
            for v in tris[k]:
                sommets_ilot[int(v)] = ilot[k]
        self.z_ilots = {}
        for il in self.desc.ilots:
            vs = np.array(sorted(v for v, i in sommets_ilot.items() if i == il["id"]), dtype=np.int64)
            if len(vs) == 0:
                continue
            rem = il["p"]["remplissage"]
            zt = np.zeros(len(vs))
            wt = np.zeros(len(vs))
            din = np.full(len(vs), np.inf)
            for bid in il["p"].get("ceinture", []):
                b = self.bandes.get(bid)
                if b is None:
                    continue
                s, dl, d, ex = b.projeter(P[vs])
                ub = b.interp(b.ub, s)
                w = 1.0 / np.maximum(d, 0.02) ** 4 * (ex < 0.3)     # 1/d⁴ : la tête la plus proche commande au bord
                zt += w * b.interp(b.ztop, s)
                wt += w
                din = np.minimum(din, np.where(ex < 0.3, np.maximum(dl - ub, 0.0), np.inf))
            zt = np.where(wt > 0, zt / np.maximum(wt, 1e-30), z[vs] + float(rem.get("retrait_sous_bordure_m", 0.0)))
            din = np.where(np.isfinite(din), din, 0.0)
            Dd = max(0.25, min(1.2, 0.5 * float(din.max())))
            retrait = float(rem.get("retrait_sous_bordure_m", 0.0)) or RETRAIT_TROTTOIR
            z[vs] = zt - retrait + float(rem.get("bombement_m", 0.0)) * K.smoothstep(din / Dd)
            # retrait minimal sous la tête LOCALE de chaque bordure de ceinture à moins de 0,6 m (revue
            # conformité r2 : gravier à fleur derrière K-0629/E000, à 0,8 cm derrière E017)
            if retrait >= 0.02:
                bornes_h = np.full(len(vs), np.inf)
                bornes_b = np.full(len(vs), -np.inf)
                for bid in il["p"].get("ceinture", []):
                    b = self.bandes.get(bid)
                    if b is None:
                        continue
                    s, dl, d, ex = b.projeter(P[vs])
                    pres = (d < 0.6) & (ex < 0.05)
                    bornes_h[pres] = np.minimum(bornes_h[pres], b.interp(b.ztop, s[pres]) - max(0.03, retrait - 0.005))
                    pres = (d < 0.35) & (ex < 0.05)
                    bornes_b[pres] = np.maximum(bornes_b[pres], b.interp(b.ztop, s[pres]) - min(0.05, retrait + 0.008))
                z[vs] = np.minimum(np.maximum(z[vs], bornes_b), bornes_h)          # 3-5 cm sous la tête locale
            self.z_ilots[il["id"]] = (vs, zt)
        z = self.limiter_pentes(P, tris, garde, classe, ilot, z)
        # sous chaque rangée de modules BEV : sol ramené au plan moyen de la rangée (un plan par BEV : les sommets
        # partagés par deux modules voisins ne sont plus réécrits par le second ajustement), plan prolongé sur 0,10 m et
        # raccordé sur 0,30 m au-delà, hors îlots (revue UE du 10/10 : dalles en saillie de 1 à 4 cm, chant et ombre
        # visibles) : la dalle 3D posée
        # dessus (pj_decals.dalles_bev, dessus à +0,8 mm) affleure le trottoir voisin
        self.bev_plans = {}
        sous_dalle = np.zeros(len(P), dtype=bool)
        dans_ilot = np.zeros(len(P), dtype=bool)                  # remplissages bornés sous la tête : hors raccord
        dans_ilot[tris[garde & (ilot != "")].ravel()] = True
        for pc, mods in self.modules_bev():
            if not mods:
                continue
            t = mods[0]["tangente"]
            nl = np.array([-t[1], t[0]])
            o = mods[0]["centre"]
            dmin = np.full(len(P), np.inf)
            for md in mods:
                X = P[:, :2] - md["centre"]
                a, b_ = np.abs(X @ md["tangente"]) - md["demi"], np.abs(X @ np.array([-md["tangente"][1], md["tangente"][0]])) - md["demi"]
                dmin = np.minimum(dmin, np.hypot(np.maximum(a, 0.0), np.maximum(b_, 0.0)) + np.minimum(np.maximum(a, b_), 0.0))
            dedans = np.where(dmin <= 0.01)[0]
            if len(dedans) < 3:
                continue
            sous_dalle[dedans] = True
            X = P[:, :2] - o
            A = np.c_[X @ t, X @ nl, np.ones(len(P))]
            coef = np.linalg.lstsq(A[dedans], z[dedans], rcond=None)[0]
            residu = float(np.abs(A[dedans] @ coef - z[dedans]).max())
            w = np.where(dmin <= 0.10, 1.0, 1.0 - K.smoothstep((dmin - 0.10) / 0.30)) * (~dans_ilot | (dmin <= 0.01))
            k = np.where(w > 0)[0]
            # près d'une bordure, le raccord s'efface (tête − 2 mm au plus derrière la face : conformité « enterrés »)
            dbord = np.full(len(k), np.inf)
            for bid, mm, s_, dl, d, ex in self.projections(P[k, :2], rayon=0.5):
                b = self.bandes[bid]
                dbord[mm] = np.minimum(dbord[mm], np.where(ex <= 0.05, np.abs(dl - 0.5 * b.interp(b.base, s_))
                                                                       - 0.5 * b.interp(b.base, s_), np.inf))
            w[k] *= np.where(dmin[k] <= 0.01, 1.0, K.smoothstep(np.clip((dbord - 0.02) / 0.15, 0.0, 1.0)))
            k = np.where(w > 0)[0]
            z[k] = z[k] * (1.0 - w[k]) + (A[k] @ coef) * w[k]
            self.bev_plans[pc["id"]] = {"pente_pct": round(100.0 * float(math.hypot(coef[0], coef[1])), 2),
                                        "residu_avant_mm": round(1000.0 * residu, 2)}
        if self.bev_plans:                     # le raccord ne remonte pas le sol au-dessus d'une tête (bornes de corriger)
            for bid, m, s_, dl, d, ex in self.projections(P[:, :2], rayon=0.5):
                b = self.bandes[bid]
                dp = dl - b.interp(b.ub, s_)
                pres = (ex <= 0) & (dp >= -0.004) & (dp < 0.2) & (dl > b.interp(b.uf, s_) + 0.004)
                z[m[pres]] = np.minimum(z[m[pres]], (b.interp(b.ztop, s_) - 0.002 + PENTE_RAMPE * np.maximum(dp, 0.0))[pres])
            z = self.limiter_pentes(P, tris, garde, classe, ilot, z, fixes=sous_dalle)   # pas de marche créée par la borne
        self.sal = sal
        return z

    def limiter_pentes(self, P, tris, garde, classe, ilot, z, fixes=None):
        """regle:pj_sol.pente_max (revue UE du 10/10 : pointes de sol de 6 à 23 cm, jusqu'à 89°, à 24 fins de bordure
        sur 128, là où deux bordures voisines imposent des niveaux incompatibles ; ex. bordurette P1 K-9297a dont le
        fil d'eau décrit (0,197) domine de 10 cm la rampe du bateau K-0385 (0,09) sur la bande de 0,25 m que la rampe
        laisse devant elle) : enveloppe inférieure lipschitzienne z_v ≤ z_u + PENTE_MAX_SOL·|uv| sur les arêtes du sol
        visible hors talus (noues), pour les sommets à moins de D_PENTE_MAX d'une bordure, hors îlots (remplissage borné
        à 3-5 cm sous la tête locale) et à plus de 0,5 m du bord de l'emprise (raccord au v1 inchangé). N'abaisse jamais
        sous un voisin : aucun bloc ne se découvre par-dessous (dessous des éléments sous le fil d'eau)."""
        T_ = tris[garde & ~np.isin(classe, CLASSES_TALUS)]
        E = np.unique(np.sort(np.vstack([T_[:, [0, 1]], T_[:, [1, 2]], T_[:, [2, 0]]]), axis=1), axis=0)
        L = np.hypot(*(P[E[:, 0], :2] - P[E[:, 1], :2]).T)
        pres = np.zeros(len(P), dtype=bool)
        for bid, m, s, dl, d, ex in self.projections(P[:, :2], rayon=D_PENTE_MAX):
            pres[m[d < D_PENTE_MAX]] = True
        x0, y0, x1, y1 = self.R
        bord = np.minimum.reduce([P[:, 0] - x0, x1 - P[:, 0], P[:, 1] - y0, y1 - P[:, 1]])
        dans_ilot = np.zeros(len(P), dtype=bool)
        dans_ilot[tris[garde & (ilot != "")].ravel()] = True
        mobile = pres & (bord > 0.5) & ~dans_ilot & (~fixes if fixes is not None else True)
        z1 = z.copy()
        for it in range(2000):
            cand = np.full(len(P), np.inf)
            np.minimum.at(cand, E[:, 0], z1[E[:, 1]] + PENTE_MAX_SOL * L)
            np.minimum.at(cand, E[:, 1], z1[E[:, 0]] + PENTE_MAX_SOL * L)
            nz = np.where(mobile, np.minimum(z1, cand), z1)
            if np.max(z1 - nz) < 1e-6:
                z1 = nz
                break
            z1 = nz
        dz = z - z1
        ab = np.where(dz > 0.001)[0]
        top = ab[np.argsort(-dz[ab])][:12]
        self.stats_pente = getattr(self, "stats_pente", None) or {}
        self.stats_pente = {"regle": "regle:pj_sol.pente_max", "pente_max": PENTE_MAX_SOL, "rayon_m": D_PENTE_MAX,
                            "passe_precedente": self.stats_pente or None,
                            "iterations": it + 1, "sommets_abaisses": int(len(ab)),
                            "abaissement_max_m": round(float(dz.max()), 3) if len(dz) else 0.0,
                            "plus_forts": [{"xy": K.r3(P[i, :2], 2), "dz_m": round(float(dz[i]), 3)} for i in top]}
        return z1

    def mnt_corrige(self, P):
        """MNT 2026 ; surfaces à araser (niveau.arasement : le MNT garde un relief disparu) : plan
        ajusté sur le MNT à 0,7-1,2 m autour de la surface, raccordé au MNT sur 0,6 m à l'extérieur."""
        z = K.mnt_local(P[:, 0], P[:, 1])
        for srf in self.desc.surfaces:
            if not (srf["p"].get("niveau") or {}).get("arasement"):
                continue
            A, Bq = C.aretes(srf["polys"][0])
            ext = srf["polys"][0][0]
            lo, hi = ext.min(axis=0) - 1.5, ext.max(axis=0) + 1.5
            gx, gy = np.meshgrid(np.arange(lo[0], hi[0], 0.1), np.arange(lo[1], hi[1], 0.1))
            Q = np.c_[gx.ravel(), gy.ravel()]
            dq, _, _ = C.distance_segments(Q, A, Bq)
            dedans_q = C.dans_polygones(Q, srf["polys"])
            anneau = (~dedans_q) & (dq > 0.7) & (dq < 1.2)
            Qa = Q[anneau]
            za = K.mnt_local(Qa[:, 0], Qa[:, 1])
            M = np.c_[Qa, np.ones(len(Qa))]
            coef, *_ = np.linalg.lstsq(M, za, rcond=None)
            m = (P[:, 0] > lo[0]) & (P[:, 0] < hi[0]) & (P[:, 1] > lo[1]) & (P[:, 1] < hi[1])
            idx = np.where(m)[0]
            if len(idx) == 0:
                continue
            d, _, _ = C.distance_segments(P[idx], A, Bq)
            dedans = C.dans_polygones(P[idx], srf["polys"])
            w = np.where(dedans, 1.0, 1.0 - K.smoothstep(d / 0.6))
            plan = P[idx] @ coef[:2] + coef[2]
            z[idx] = z[idx] * (1 - w) + plan * w
            self.arasements = getattr(self, "arasements", {})
            if srf["id"] not in self.arasements:
                self.arasements[srf["id"]] = {"plan": K.r3(coef, 5), "dz_max_m": round(float(np.max((K.mnt_local(P[idx, 0], P[idx, 1]) - z[idx]))), 3)}
        z = self._route_sous_ilots(P, z)
        z, _, _ = self.rampes(P, z)
        return z

    # ---------------------------------------------------------------- rampes PMR
    def materiau_aux(self, Q):
        """materiau_id de la description aux points Q (îlot : remplissage ; sinon surface ; '' hors de tout)."""
        Q = np.asarray(Q, dtype=np.float64)[:, :2]
        out = np.full(len(Q), "", dtype=object)
        reste = np.arange(len(Q))
        for il in self.desc.ilots:
            if len(reste) == 0:
                break
            dd = C.dans_polygones(Q[reste], il["polys"])
            out[reste[dd]] = il["p"]["remplissage"]["materiau_id"]
            reste = reste[~dd]
        for srf in self.desc.surfaces:
            if len(reste) == 0:
                break
            dd = C.dans_polygones(Q[reste], srf.get("polys_fab", srf["polys"]))
            out[reste[dd]] = srf["p"]["revetement"]["materiau_id"]
            reste = reste[~dd]
        return out

    def _profils_rampes(self):
        """Profils de rampe derrière chaque bateau (vue ≤ 0,04 ; regle:pj_sol.rampe_pmr, revue conformité r2) :
        grilles (s, d) -> z, d mesuré depuis la ligne arrière du sol (ub).
        - Profondeur utile Dl de chaque rangée : jusqu'à 0,25 m d'une autre bordure, au premier revêtement non
          marchable (gazon, massif, îlot) ou à D_RAMPE.
        - Rampe PLANE depuis la tête du bateau − 4 mm : si la rangée bute sur une autre bordure, pente vers son
          niveau (tête − 4 mm de son côté haut, fil d'eau de son côté bas) ; sinon pente moyenne du MNT sur la
          profondeur utile (moindres carrés). Pente bornée à ±PENTE_RAMPE : le MNT 2021-2026 garde des marches
          d'anciennes bordures et des bosses que la rampe ne suit plus.
        - Au-delà de Dl : raccord au MNT sur une longueur ∝ à l'écart (pente de raccord ≤ 8 %, 0,6 à 3 m),
          hors de la zone marchable ou au-delà de D_RAMPE."""
        if hasattr(self, "_rampes_cache"):
            return self._rampes_cache
        out = []
        autres = {bid: (bb.B.P[:-1], bb.B.P[1:]) for bid, bb in self.bandes.items()}
        for bid in sorted(self.bandes):
            b = self.bandes[bid]
            for iv in b.B.iv:
                if iv["role"] != "bateau" or iv["vue_m"] > 0.04 or iv["s1"] - iv["s0"] < 0.6:
                    continue
                Lf = 1.0
                ss = np.arange(max(0.0, iv["s0"] - Lf), min(b.B.L, iv["s1"] + Lf) + 1e-9, 0.1)
                dd = np.arange(0.0, D_RAMPE + 3.0 + 1e-9, 0.05)
                q, tg = C.point_a(b.B.P, ss)
                nl = np.c_[-tg[:, 1], tg[:, 0]]
                ub = b.interp(b.ub, ss)
                X = q[:, None, :] + nl[:, None, :] * (ub[:, None] + dd[None, :])[..., None]
                zm = K.mnt_local(X[..., 0], X[..., 1])
                Dl = np.full(len(ss), D_RAMPE)
                cible = np.full(len(ss), np.nan)            # niveau de la bordure qui arrête la rangée
                ids = [k for k in sorted(autres) if k != bid]
                A = np.vstack([autres[k][0] for k in ids])
                Bq = np.vstack([autres[k][1] for k in ids])
                seg_bid = np.concatenate([[k] * len(autres[k][0]) for k in ids])
                dist, jseg, _ = C.distance_segments(X.reshape(-1, 2), A, Bq)
                dist, jseg = dist.reshape(X.shape[:2]), jseg.reshape(X.shape[:2])
                mat = self.materiau_aux(X[:, :int(D_RAMPE / 0.05) + 1].reshape(-1, 2)).reshape(len(ss), -1)
                for r in range(len(ss)):
                    k = np.where(dist[r, :len(mat[r])] < 0.25)[0]
                    nm = np.where(~np.isin(mat[r], MARCHABLES))[0]
                    nm = nm[nm > 2]                         # bande de pose et raccord de la bordure elle-même
                    kb = int(k[0]) if len(k) else 10 ** 6
                    kn = int(nm[0]) if len(nm) else 10 ** 6
                    if kb <= kn and kb < 10 ** 6:
                        Dl[r] = max(dd[kb], 0.0)
                        # niveau de l'autre bordure au point d'arrêt (côté haut : tête − 4 mm ; bas : fil d'eau)
                        o = self.bandes[seg_bid[jseg[r, kb]]]
                        so, dlo, _, exo = o.projeter(X[r, kb][None])
                        if exo[0] <= 0.05:
                            haut = dlo[0] > 0.5 * float(o.interp(o.uf, so)[0] + o.interp(o.ub, so)[0])
                            cible[r] = float(o.interp(o.ztop, so)[0]) - RETRAIT_TROTTOIR if haut else float(o.interp(o.zroute, so)[0])
                    elif kn < 10 ** 6:
                        Dl[r] = max(dd[kn] - 0.05, 0.3)
                z0 = b.interp(b.ztop, ss) - RETRAIT_TROTTOIR
                ZR = np.empty_like(zm)
                Lr = np.full(len(ss), 0.6)
                h, g = dd[1] - dd[0], PENTE_RAMPE
                for r in range(len(ss)):
                    m = C.mediane_glissante(zm[r], 5)
                    m = np.convolve(np.pad(m, 2, mode="edge"), np.ones(5) / 5, mode="valid")
                    nD = max(2, int(round(Dl[r] / h)) + 1)
                    d_ = dd[:nD]
                    if np.isfinite(cible[r]):            # vers la bordure qui arrête la rangée : droite exacte
                        p = (cible[r] - z0[r]) / max(Dl[r] + 0.25, 0.3)   # jusqu'à 4 % (au-delà : non conforme)
                        p = float(np.clip(p, -0.04, 0.04))
                    else:
                        p = float(np.sum(d_ * (m[:nD] - z0[r])) / max(np.sum(d_ ** 2), 1e-9))
                        p = float(np.clip(p, -g, g))
                    ZR[r, :nD] = z0[r] + p * d_
                    ZR[r, nD:] = m[nD:]
                    Lr[r] = float(np.clip(abs(m[min(nD, len(m) - 1)] - ZR[r, nD - 1]) / 0.08, 0.6, 3.0))
                # lissage le long de la bordure (σ 0,3 m)
                w = np.exp(-0.5 * ((ss[:, None] - ss[None, :]) / 0.3) ** 2)
                ZR = (w @ ZR) / w.sum(axis=1)[:, None]
                out.append({"bordure": bid, "s0": iv["s0"], "s1": iv["s1"], "Lf": Lf, "ss": ss, "dd": dd,
                            "z": ZR, "Dl": Dl, "Lr": Lr, "bute": np.isfinite(cible)})
        self._rampes_cache = out
        return out

    def rampes(self, P, z):
        """Applique les profils de rampe (z None : poids seulement) ; renvoie (z, poids, bordure)."""
        P = np.asarray(P, dtype=np.float64)[:, :2]
        w_tot = np.zeros(len(P))
        bid_w = np.full(len(P), "", dtype=object)
        z = None if z is None else np.array(z, dtype=np.float64)
        for R in self._profils_rampes():
            b = self.bandes[R["bordure"]]
            ss, dd = R["ss"], R["dd"]
            Dmax = float(dd[-1])
            lo, hi = b.bbox
            m = np.where((P[:, 0] > lo[0] - Dmax) & (P[:, 0] < hi[0] + Dmax) &
                         (P[:, 1] > lo[1] - Dmax) & (P[:, 1] < hi[1] + Dmax))[0]
            if len(m) == 0:
                continue
            s, dl, d, ex = b.projeter(P[m])
            dp = dl - b.interp(b.ub, s)
            ok = (ex <= 0) & (s >= ss[0]) & (s <= ss[-1]) & (dp > -0.02) & (dp < Dmax)
            if not ok.any():
                continue
            m, s, dp = m[ok], s[ok], np.maximum(dp[ok], 0.0)
            Dl = np.interp(s, ss, R["Dl"])
            Lr = np.interp(s, ss, R["Lr"])
            bute = np.interp(s, ss, R["bute"].astype(float)) > 0.5
            hors = np.maximum(np.maximum(R["s0"] - s, s - R["s1"]), 0.0)
            ws = 1.0 - K.smoothstep(hors / R["Lf"])
            # rangée arrêtée par une autre bordure : ses propres cibles prennent le relais (fondu court)
            wd = np.where(bute, 1.0 - K.smoothstep((dp - (Dl - 0.3)) / 0.3),
                          1.0 - K.smoothstep((dp - Dl) / Lr))
            w = ws * wd * np.where(bute, dp < Dl, dp < Dl + Lr)
            fs = np.clip((s - ss[0]) / (ss[1] - ss[0]), 0, len(ss) - 1.000001)
            fd = np.clip(dp / (dd[1] - dd[0]), 0, len(dd) - 1.000001)
            i, j = np.floor(fs).astype(int), np.floor(fd).astype(int)
            a, c = fs - i, fd - j
            Z = R["z"]
            zr = (Z[i, j] * (1 - a) + Z[i + 1, j] * a) * (1 - c) + (Z[i, j + 1] * (1 - a) + Z[i + 1, j + 1] * a) * c
            mieux = w > w_tot[m]
            w_tot[m[mieux]] = w[mieux]
            bid_w[m[mieux]] = R["bordure"]
            if z is not None:
                z[m] = z[m] * (1 - w) + zr * w
        return z, w_tot, bid_w

    def _route_sous_ilots(self, P, z):
        """Îlots : le MNT y garde le relief de l'îlot (pointes effilées, nez) ; là où la ceinture posée
        (nez arrondis) laisse la chaussée, l'altitude vient du MNT de la chaussée autour de l'îlot
        (moyenne pondérée 1/d² des points à 0,6 m à l'extérieur du polygone de l'îlot)."""
        if not hasattr(self, "_anneaux_ilots"):
            self._anneaux_ilots = []
            tous = [il["polys"] for il in self.desc.ilots]
            for il in self.desc.ilots:
                r = C.orienter(il["polys"][0])[0]
                Q = densifier(r, 0.25, ferme=True)
                nl = K.normales_gauches(np.vstack([Q, Q[:1]]))[:-1]
                ext = Q - nl * 0.6                     # anneau anti-horaire : l'extérieur est à droite
                hors = np.ones(len(ext), dtype=bool)
                for polys in tous:
                    hors &= ~C.dans_polygones(ext, polys)
                ext = ext[hors]
                self._anneaux_ilots.append((il, ext, K.mnt_local(ext[:, 0], ext[:, 1])))
        for il, ext, zext in self._anneaux_ilots:
            if len(ext) < 3:
                continue
            lo, hi = il["polys"][0][0].min(axis=0) - 0.4, il["polys"][0][0].max(axis=0) + 0.4
            m = np.where((P[:, 0] > lo[0]) & (P[:, 0] < hi[0]) & (P[:, 1] > lo[1]) & (P[:, 1] < hi[1]))[0]
            if len(m) == 0:
                continue
            A, Bq = C.aretes(il["polys"][0])
            dbord, _, _ = C.distance_segments(P[m], A, Bq)
            dedans = C.dans_polygones(P[m], il["polys"])
            fondu = np.where(dedans, 1.0, 1.0 - K.smoothstep(dbord / 0.4))
            garde = fondu > 0
            m, fondu = m[garde], fondu[garde]
            if len(m) == 0:
                continue
            route = np.ones(len(m), dtype=bool)
            dmin = np.full(len(m), np.inf)
            for bid in il["p"].get("ceinture", []):
                b = self.bandes.get(bid)
                if b is None:
                    continue
                s, dl, d, ex = b.projeter(P[m])
                plus = d < dmin
                route[plus] = (dl[plus] < b.interp(b.uf, s[plus]) + 1e-3) | (ex[plus] > 0.05)
                dmin = np.minimum(dmin, d)
            k = route & (dmin < 3.0)
            m, fondu = m[k], fondu[k]
            if len(m) == 0:
                continue
            dd = np.hypot(P[m, 0][:, None] - ext[None, :, 0], P[m, 1][:, None] - ext[None, :, 1])
            w = 1.0 / np.maximum(dd, 0.05) ** 2
            zr = (w * zext[None]).sum(axis=1) / w.sum(axis=1)
            z[m] = z[m] * (1 - fondu) + zr * fondu
        return z

    def _D_haut(self, b):
        """Longueur de raccord du côté haut : 30 x |écart au MNT à 0,6 m derrière|, 0,6-4 m (1,5-4 m derrière
        une vue ≤ 0,06 m), max glissant sur 3 m."""
        if hasattr(b, "_Dh"):
            return b._Dh
        q = b.P + b.n * (b.ub + 0.6)[:, None]
        ecart = (b.ztop - RETRAIT_TROTTOIR + DEVERS * 0.6) - K.mnt_local(q[:, 0], q[:, 1])
        Dmin = np.where(b.vue <= 0.06, 1.5, 0.6)          # abaissés : rampe d'au moins 1,5 m
        D = np.clip(30.0 * np.abs(ecart), Dmin, 4.0)
        Dm = np.array([D[(b.s >= x - 1.5) & (b.s <= x + 1.5)].max() for x in b.s])
        b._Dh = Dm
        b._ecart = ecart
        return Dm

    # ---------------------------------------------------------------- sortie
    def fabriquer(self, chemin):
        P2, tris = self.trianguler()
        garde, classe, surf, ilot, bev_de = self.classer(P2, tris)
        z = self.altitudes(P2, tris, garde, classe, surf, ilot)
        P3 = np.c_[P2, z]
        T_ = tris[garde]
        cl = classe[garde]
        # normales par sommet de face sur le sol entier (continues d'un materiau_id à l'autre), cusp 30°
        Nc = K.normales_cusp(P3, np.full(len(T_), 3), T_.ravel()).reshape(-1, 3, 3)
        st = U.scene("Sol de la zone pilote ZP-01 (pj_sol.py) : maillages découpés sous les bordures posées, "
                     "Z = MNT 2026 + bordures de la description (jamais les maillages v1), un maillage par "
                     "materiau_id, UV st1 en mètres.", data={"version": K.VERSION, "description": self.desc.hash})
        U.xform(st, "/World/PJ_Sol")
        K.typer_ue(st, "/World/PJ_Sol")
        self.meshes = {}
        for mid in sorted(set(cl.tolist())):
            sel = T_[cl == mid]
            vs, inv = np.unique(sel.ravel(), return_inverse=True)
            idx = inv.reshape(-1, 3)
            st1 = P2[vs]        # BEV compris : sol des joints sous les dalles 3D, mortier uni (l'UV _uv_bev, inutile,
                                # dégénérait 2 triangles en bout de bande)
            m = U.maillage(st, f"/World/PJ_Sol/{mid}", P3[vs], np.full(len(idx), 3), idx.ravel(),
                           normales=Nc[cl == mid].reshape(-1, 3), st1=st1,
                           st1_interp="vertex", materiau_id=mid,
                           primvars={"salissure": (Vt.FloatArray.FromNumpy(self.sal[vs].astype(np.float32)),
                                                   T.FloatArray, UsdGeom.Tokens.vertex)})
            # BEV : sous les dalles 3D (pj_decals.dalles_bev, dessus à +0,8 mm), le sol ne se voit que dans les joints
            # de 3 mm -> mortier sombre (Karma et UE, qui importe aussi les dalles 3D)
            mue = "mortier_joint" if mid == "bev_podotactile" else mid
            m.GetPrim().CreateAttribute("unrealMaterial", T.String).Set(f"/Game/PJ/Materials/MI_{mue}.MI_{mue}")
            U.lier_chemin(m.GetPrim(), f"/World/Looks_v2/{mue}")
            K.lier_ue(m.GetPrim(), mue, *(((0.055, 0.055, 0.052), 0.95) if mue == "mortier_joint"
                                          else self.specs.apercu_ue(mue)))
            self.meshes[mid] = int(len(idx))
        U.enregistrer(st, chemin)
        self.P3, self.T, self.cl, self.ilot_tri = P3, T_, cl, ilot[garde]
        self.surf_tri = surf[garde]
        ctl = self.controles(P2, z)
        ctl["pente_max"] = getattr(self, "stats_pente", None)
        ctl["bev_plans"] = getattr(self, "bev_plans", None)
        return ctl

    def _uv_bev(self, P2, vs, _sel, _t, bevs):
        """UV des BEV dans le repère de leur bordure : dalles de 0,40 alignées sur le nez (inutilisé depuis les
        dalles 3D de pj_decals : le sol BEV n'est plus que le mortier des joints)."""
        st1 = P2[vs].copy()
        par = {pc["id"]: pc for pc, _ in self.bev}
        bid_v = {}
        for tri, b in zip(_t, bevs):
            for v in tri:
                bid_v[int(v)] = b
        for k, v in enumerate(vs):
            pc = par.get(bid_v.get(int(v)))
            if pc is None:
                continue
            an = pc["p"]["ancrage"]
            b = self.bandes[an["bordure"]]
            s, dl, d, ex = b.projeter(P2[v][None])
            st1[k] = (s[0] - float(b.B.s_nouveau(an["s0"])), dl[0] - pc["p"].get("retrait_nez_m", 0.5))
        return st1

    # ---------------------------------------------------------------- contrôles
    def controles(self, P2, z):
        """Écarts sol / bordure, rampes derrière les abaissés, dévers des trottoirs, retraits d'îlots."""
        P3, T_ = self.P3, self.T
        a, b, c = P3[T_[:, 0]], P3[T_[:, 1]], P3[T_[:, 2]]
        n = np.cross(b - a, c - a)
        n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
        pente = np.hypot(n[:, 0], n[:, 1]) / np.maximum(np.abs(n[:, 2]), 1e-9)
        G = P3[T_].mean(axis=1)
        out = {"triangles": int(len(T_)), "triangles_bandes_retires": self.n_bande,
               "maillages": dict(sorted(self.meshes.items()))}
        # rampes derrière les parties abaissées (bateaux) : triangles à moins de 2,5 m derrière
        rampes, devers = [], []
        marchables = ["enrobe_trottoir", "bev_podotactile", "enrobe_piste_cyclable", "beton_balaye", "dalles_beton",
                      "paves_beton", "enrobe_bbsg_ancien", "enrobe_bbsg_neuf_2025"]
        gx_, gy_ = -n[:, 0] / np.where(np.abs(n[:, 2]) > 1e-9, n[:, 2], 1e-9), -n[:, 1] / np.where(np.abs(n[:, 2]) > 1e-9, n[:, 2], 1e-9)
        # distance aux autres bordures (les ressauts voisins ne sont pas des rampes)
        A = np.vstack([bb.P[:-1] for bb in self.bandes.values()])
        Bq = np.vstack([bb.P[1:] for bb in self.bandes.values()])
        for bid in sorted(self.bandes):
            bd = self.bandes[bid]
            s, dl, d, ex = bd.projeter(G[:, :2])
            ub = bd.interp(bd.ub, s)
            dp = dl - ub
            tg = C.point_a(bd.B.P, s)[1]
            nl = np.c_[-tg[:, 1], tg[:, 0]]
            perp = gx_ * nl[:, 0] + gy_ * nl[:, 1]           # pente dans le sens de la marche (montée +)
            for iv in bd.B.iv:
                if iv["role"] != "bateau" or iv["vue_m"] > 0.03 or iv["s1"] - iv["s0"] < 0.6:
                    continue
                sel = (ex <= 0) & (s > iv["s0"] + 0.2) & (s < iv["s1"] - 0.2) & (dp > 0.05) & (dp < 2.0) & \
                    np.isin(self.cl, marchables)
                if sel.sum() < 3:
                    continue
                idx = np.where(sel)[0]
                dmin, _, _ = C.distance_segments(G[idx, :2], A, Bq)
                idx = idx[(dmin >= d[idx] - 1e-6) | (dmin > 0.3)]
                if len(idx) < 3:
                    continue
                rampes.append({"bordure": bid, "s0": round(iv["s0"], 2), "s1": round(iv["s1"], 2), "triangles": int(len(idx)),
                               "rampe_p95_pct": round(100 * float(np.percentile(np.abs(perp[idx]), 95)), 2),
                               "rampe_mediane_pct": round(100 * float(np.median(np.abs(perp[idx]))), 2),
                               "part_sup_5pct": round(float(np.mean(np.abs(perp[idx]) > 0.05)), 3),
                               "pente_totale_p95_pct": round(100 * float(np.percentile(pente[idx], 95)), 2)})
            # dévers : pente perpendiculaire à la bordure (+ = monte en s'éloignant), trottoirs
            sel = (ex <= 0) & (dp > 0.3) & (dp < 1.5) & (self.cl == "enrobe_trottoir")
            if sel.sum() > 5:
                devers.append(float(np.median(perp[sel])))
        out["rampes_abaisses"] = rampes
        out["devers_trottoirs_pct"] = {"mediane": round(100 * float(np.median(devers)), 2) if devers else None,
                                       "p10": round(100 * float(np.percentile(devers, 10)), 2) if devers else None,
                                       "p90": round(100 * float(np.percentile(devers, 90)), 2) if devers else None,
                                       "n_bordures": len(devers)}
        # retraits des remplissages d'îlots
        ri = {}
        for il in self.desc.ilots:
            if il["id"] not in self.z_ilots:
                continue
            vs, zt = self.z_ilots[il["id"]]
            rr = zt - P3[vs, 2]
            ri[il["id"]] = {"retrait_min_m": round(float(rr.min()), 4), "retrait_max_m": round(float(rr.max()), 4),
                            "retrait_bord_m": round(float(np.percentile(rr, 95)), 4), "sommets": int(len(vs))}
        out["retraits_ilots"] = ri
        # écart au MNT 2026 par classe (sommets) : corrections des bordures, rampes, décaissés, îlots
        zm = K.mnt_local(P3[:, 0], P3[:, 1])
        ec = {}
        for mid in sorted(set(self.cl.tolist())):
            vs = np.unique(T_[self.cl == mid].ravel())
            d = P3[vs, 2] - zm[vs]
            ec[mid] = {"mediane_m": round(float(np.median(d)), 3), "p5_m": round(float(np.percentile(d, 5)), 3),
                       "p95_m": round(float(np.percentile(d, 95)), 3), "part_sup_10cm": round(float(np.mean(np.abs(d) > 0.10)), 3)}
        out["sol_moins_mnt"] = ec
        return out
