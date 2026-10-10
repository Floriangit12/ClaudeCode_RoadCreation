"""Famille `bordures` de la description v2 : une polyligne d'arête avant par bordure, profils NF par
intervalles, abaissés (traversées, entrées charretières) avec chartières, matériau, aspect et Z.

Chaîne (déterministe, numpy seul) :
1. lignes de relief/bordures_hauteurs.geojson (tronçons de 1 m des lignes GAM / PCRS 2019 / plan
   projet 2025 : h_vue_m, statut, cote_haut, traversee...) recousues par `ligne` ;
2. dédoublonnage : le levé GAM trace deux arêtes par bordure (écart 0,10 m ; 0,15 m aux Saules
   Blancs) ; on apparie les traits parallèles distants de ≤ 0,30 m sur ≥ 1 m et on garde celui du
   côté bas (MNT 2026 de part et d'autre), départage par cote_haut puis par numéro de ligne ; décision
   prise une fois par paire (exactement une arête gardée) ; deux traits confondus (< 3 cm) : la ligne
   la plus longue reste ;
3. orientation : chaque bordure est orientée côté haut à GAUCHE, donc face vue à DROITE ;
4. découpe par la zone pilote ;
5. profil par mètre (bordures.json regles_affectation sur h_vue lissée sur 7 m, changements de profil
   de moins de 5 m fusionnés) ; les hauteurs « estimee » (standards de l'atelier relief) ne sont
   gardées que face à une chaussée, sinon limite de piste (A2 0,05) ou d'espace vert (P1 0,02) ;
6. abaissés : emprises des passages piétons dessinés (bandes groupées, prolongées de 1,5 m dans le
   sens de la marche), mais seulement là où la bordure COUPE la marche (> 45°) ; zones et drapeaux
   « traversée » de l'atelier relief loin des passages ; entrées charretières là où l'axe d'un accès
   riverain coupe la bordure ; extrémités recalées (≤ 1 m) sur les blocs CHARTIERE GAM ; vue 0,02 m
   (traversée) ou 0,02-0,04 m (charretière), chartières de 1 m vers la vue courante dès 1 cm d'écart ;
   changements de profil courant de ≥ 1 cm de vue : raccord de 1 m (rôle chartière, sans abaissé) ;
7. BEV (famille ponctuels_sol) : traversées dont le côté bas est la chaussée 2026 et le côté haut
   piéton, sauf OSM tactile_paving=no ; dalles 0,40 m à 0,50 m du nez, rognées hors îlots ;
8. Z de chaque sommet = fil d'eau NGF : MNT 2026 à 0,30 m devant la face (jamais les maillages v1),
   régularisé (regle:fil_eau_regulier : médiane glissante ±1,5 m, côté haut − vue là où le devant est
   accidenté, lissage gaussien σ 0,6 m), comparé au fil d'eau LiDAR 2021 (écart consigné) ;
   z_ref = modele_2026 ;
9. caniveau CS2 là où une ligne SOL_CANIVEAU GAM longe la face vue.
"""
import collections
import math
import re

import numpy as np

import contexte as ctx
from commun import (DONNEES, SPECS, abscisses, aire_signee, arrondi, coords_geojson, dans_polygone,
                    dans_polygones, decaler, dedoublonner_sommets, densifier, distance_segments,
                    intervalles_masque, lire_geojson, lire_json, mediane_glissante, normale_gauche,
                    point_a, projeter, rayon_courbure, repere, sous_polyligne, couper_polyligne)

PAS_APP = 0.20            # échantillonnage de l'appariement (m)
D_PAIRE_MAX = 0.30        # écart maximal entre les deux arêtes d'une même bordure (m)
COS_PAIRE = 0.90
RUN_PAIRE_MIN = 1.0       # longueur minimale d'appariement (m)
L_MIN = 1.0               # morceau de bordure minimal (m) : moins d'un élément = bruit de levé
PAS_AB = 0.25             # échantillonnage des abaissés (m)
CHARTIERE_M = 1.0         # longueur d'un élément de raccord (chartière)
ECART_RESSAUTS_M = 2.5    # arrêté du 15/01/2007 : ressauts successifs espacés d'au moins 2,50 m
VUE_TRAVERSEE = 0.02
LARGEUR_ABAISSE_MIN = 1.20  # arrêté du 15/01/2007 : largeur minimale d'un abaissé
H_LIMITE_PISTE = 0.05      # bordures.json usage_site : séparateurs et rives de piste en A2 (0,05-0,09)
H_LIMITE_ESPACE_VERT = 0.02  # bordures.json usage_site : limites à niveau (P1, 0-0,05)
VUE_CHARRETIERE = 0.03
INTERVALLE_MIN = 5.0       # longueur minimale d'un changement de profil (m)
FENETRE_H = 7             # médiane glissante de h_vue (m)
BEV_RETRAIT, BEV_PROFONDEUR = 0.50, 0.40
CALAGE_MAX = 1.0          # recalage maximal d'une extrémité de bateau sur un bloc CHARTIERE (m)
COS_MARCHE_MAX = 0.707    # bordure abaissée si elle coupe la marche à plus de 45°
REGLE = "regle:bordures.regles_affectation"
SEUILS = [(0.03, "P1"), (0.09, "A2"), (0.175, "T2"), (0.30, "T3")]
VUE_PLAGE = {"P1": (0.0, 0.03), "A2": (0.03, 0.09), "T2": (0.09, 0.175), "T3": (0.175, 0.30),
             "QUAI_BUS": (0.15, 0.24), "T2_bateau": (0.0, 0.04), "MURET_TALUS": (0.30, 1.5)}
STATUTS_MESURES = {"mesuree", "sans_ressaut_mesuree", "abaissee_mesuree"}
PIETON = {"trottoir", "ilot", "quai_bus", "terre_plein_vegetal"}   # classes v1 d'un côté haut piéton


# --------------------------------------------------------------------------- spec
def verifier_regles(spec):
    """Les seuils codés ici doivent être ceux de bordures.json (regles_affectation)."""
    txt = " ".join(r["si"] for r in spec["regles_affectation"]).replace(",", ".")
    nombres = {float(x) for x in re.findall(r"\d+\.\d+", txt)}
    attendus = {0.06, 0.15, 0.03, 0.09, 0.175, 0.30}
    if not attendus <= nombres:
        raise SystemExit(f"bordures.json regles_affectation a changé : seuils {sorted(nombres)}")
    for i, r in enumerate(spec["regles_affectation"]):
        r["_ref"] = f"{REGLE}[{i}]"
    return {r["profil"]: r["_ref"] for r in spec["regles_affectation"]}


def profil_de(h):
    for s, p in SEUILS:
        if h < s:
            return p
    return "MURET_TALUS"


# --------------------------------------------------------------------------- lignes
class Ligne:
    def __init__(self, num, feats):
        feats.sort(key=lambda f: f["properties"]["troncon"])
        pts, bornes = [], [0.0]
        for f in feats:
            c = repere(np.asarray(f["geometry"]["coordinates"], dtype=float)[:, :2])
            pts.append(c if not pts else c[1:])
            bornes.append(bornes[-1] + float(abscisses(c)[-1]))
        self.num = num
        self.P = dedoublonner_sommets(np.vstack(pts))
        self.S = abscisses(self.P)
        self.bornes = np.array(bornes) * (self.S[-1] / max(bornes[-1], 1e-9))
        self.props = [f["properties"] for f in feats]
        p0 = self.props[0]
        self.source = p0["source"]
        self.gam_index = p0["gam_index"]

    @property
    def longueur(self):
        return float(self.S[-1])

    def indice(self, s):
        return np.clip(np.searchsorted(self.bornes, s, side="right") - 1, 0, len(self.props) - 1)

    def attr(self, s, cle):
        return [self.props[i][cle] for i in self.indice(np.atleast_1d(s))]


def charger_lignes():
    par = collections.defaultdict(list)
    for f in lire_geojson(DONNEES / "relief/bordures_hauteurs.geojson"):
        par[f["properties"]["ligne"]].append(f)
    lignes = {}
    for num in sorted(par):
        lg = Ligne(num, par[num])
        if ctx.dans_emprise(lg.P).any():
            lignes[num] = lg
    return lignes


def code_source(lg):
    s = lg.source.lower()
    if s.startswith("gam"):
        return "gam", f"gam_topo_sol_bordure_lin index {lg.gam_index} (bordures_hauteurs ligne {lg.num})"
    if s.startswith("pcrs"):
        return "pcrs2019", f"PCRS 2019 limite_voirie (bordures_hauteurs ligne {lg.num})"
    return "plan2025", f"plan projet 2025 (bordures_hauteurs ligne {lg.num})"


# --------------------------------------------------------------------------- dédoublonnage
def apparier(lignes, mnt):
    """Morceaux gardés [(ligne, s0, s1, doublons)] après suppression des arêtes arrière."""
    nums = sorted(lignes)
    A = np.vstack([lignes[n].P[:-1] for n in nums])
    B = np.vstack([lignes[n].P[1:] for n in nums])
    L = np.concatenate([np.full(len(lignes[n].P) - 1, n) for n in nums])
    D = (B - A) / np.maximum(np.hypot(*(B - A).T), 1e-12)[:, None]
    morceaux, stats = [], collections.Counter()
    # décision par paire {n, p}, prise une seule fois (au passage de la ligne de plus petit numéro) et
    # réutilisée au passage de l'autre : exactement une des deux arêtes est gardée (sinon deux lignes
    # GAM superposées, ex. 600/614, ou à niveau, ex. 619/620, se gardaient l'une l'autre)
    gagnant = {}
    for n in nums:
        lg = lignes[n]
        k = max(2, int(math.ceil(lg.longueur / PAS_APP)) + 1)
        s = np.linspace(0.0, lg.longueur, k)
        q, tg = point_a(lg.P, s)
        m = L != n
        d, j, pr = distance_segments(q, A[m], B[m])
        part = L[m][j]
        cos = np.abs(np.einsum("ij,ij->i", tg, D[m][j]))
        app = (d <= D_PAIRE_MAX) & (cos >= COS_PAIRE)
        # runs d'appariement assez longs, partenaire constant
        garde = np.ones(len(s), dtype=bool)
        retire = np.full(len(s), -1)                   # partenaire supprimé (arête arrière) par échantillon
        for s0, s1 in intervalles_masque(app, s):
            sel = (s >= s0 - 1e-9) & (s <= s1 + 1e-9) & app
            if s1 - s0 < RUN_PAIRE_MIN:
                continue
            for p in sorted(set(part[sel])):
                ss = sel & (part == p)
                if ss.sum() * PAS_APP < RUN_PAIRE_MIN:
                    continue
                cle = (min(n, int(p)), max(n, int(p)))
                if cle in gagnant:
                    devant, crit = gagnant[cle] == n, "paire"
                elif float(np.median(d[ss])) < 0.03:
                    # deux traits confondus (même arête levée deux fois) : la ligne la plus longue reste
                    lp = lignes[int(p)].longueur
                    devant, crit = (lg.longueur, -n) >= (lp, -int(p)), "superposees"
                else:
                    nrm = normale_gauche(tg[ss])
                    cote = np.sign(np.einsum("ij,ij->i", pr[ss] - q[ss], nrm))
                    cote[cote == 0] = 1
                    z_soi = mnt(*(repere(q[ss] - nrm * cote[:, None] * 0.30, "l93").T))
                    z_part = mnt(*(repere(pr[ss] + nrm * cote[:, None] * 0.30, "l93").T))
                    dz = float(np.median(z_part - z_soi))      # > 0 : soi du côté bas = arête avant
                    if dz > 0.02:
                        devant, crit = True, "mnt"
                    elif dz < -0.02:
                        devant, crit = False, "mnt"
                    else:
                        ch = collections.Counter(lg.attr(s[ss], "cote_haut")).most_common()
                        ch = [c for c, _ in ch if c]
                        if ch:
                            haut = 1 if ch[0] == "gauche" else -1
                            devant, crit = bool(np.median(cote) == haut), "cote_haut"
                        else:
                            devant, crit = n < p, "numero"
                gagnant.setdefault(cle, n if devant else int(p))
                stats[crit] += 1
                if not devant:
                    garde[ss] = False
                else:
                    retire[ss] = p
        for s0, s1 in intervalles_masque(garde, s):
            if s1 - s0 >= L_MIN:
                sel = (s >= s0) & (s <= s1) & (retire >= 0)
                doublons = sorted({int(x) for x in retire[sel]})
                morceaux.append((n, float(s0), float(s1), doublons))
    return morceaux, stats


# --------------------------------------------------------------------------- orientation
def classe_niveau(pts):
    """Rang de niveau de la surface v1 sous chaque point : 0 bas (chaussée...), 1 haut, -1 inconnu."""
    rang = {"chaussee": 0, "piste_cyclable": 0, "parking": 0, "acces_riverain": 0,
            "trottoir": 1, "ilot": 1, "terre_plein_vegetal": 1, "espace_vert": 1, "quai_bus": 1}
    out = np.full(len(pts), -1)
    for _, p, polys in ctx.surfaces_v1():
        r = rang.get(p["classe"])
        if r is None:
            continue
        m = dans_polygones(pts, polys)
        out[m & (out < 0)] = r
    return out


def cote_haut(P, lg, s_src, sens, mnt):
    """+1 si le côté haut est à gauche du sens de P, -1 sinon ; et le critère retenu."""
    S = abscisses(P)
    s = np.linspace(0.0, S[-1], max(3, int(S[-1] / 0.5) + 1))
    q, tg = point_a(P, s)
    n = normale_gauche(tg)
    zg = mnt(*(repere(q + n * 0.45, "l93").T))
    zd = mnt(*(repere(q - n * 0.25, "l93").T))
    dz = float(np.median(zg - zd))
    if abs(dz) >= 0.025:
        return (1 if dz > 0 else -1), "mnt_2026", dz
    ch = [c for c in lg.attr(s_src(s), "cote_haut") if c]
    if ch:
        c = collections.Counter(ch).most_common(1)[0][0]
        v = 1 if c == "gauche" else -1
        return v * sens, "cote_haut_relief", dz
    rg, rd = classe_niveau(q + n * 0.6), classe_niveau(q - n * 0.6)
    ok = (rg >= 0) & (rd >= 0) & (rg != rd)
    if ok.any():
        return (1 if np.mean(rg[ok] > rd[ok]) >= 0.5 else -1), "surfaces_v1", dz
    return 1, "defaut", dz


# --------------------------------------------------------------------------- outils intervalles
def runs(valeurs):
    """[(i0, i1, valeur)] des suites constantes (i1 exclus)."""
    out, i = [], 0
    while i < len(valeurs):
        j = i
        while j + 1 < len(valeurs) and valeurs[j + 1] == valeurs[i]:
            j += 1
        out.append([i, j + 1, valeurs[i]])
        i = j + 1
    return out


def fusionner_courts(prof, h, lmin):
    """Fusionne les suites de profil plus courtes que lmin (en échantillons de 1 m) dans le voisin
    dont la vue médiane est la plus proche (itératif, déterministe)."""
    prof = list(prof)
    while True:
        rs = runs(prof)
        courts = [r for r in rs if r[1] - r[0] < lmin and len(rs) > 1]
        if not courts:
            return prof
        r = min(courts, key=lambda r: (r[1] - r[0], r[0]))
        k = rs.index(r)
        hm = np.nanmedian(h[r[0]:r[1]])
        cands = []
        for kk in (k - 1, k + 1):
            if 0 <= kk < len(rs):
                o = rs[kk]
                cands.append((abs(np.nanmedian(h[o[0]:o[1]]) - hm), kk))
        _, kk = min(cands)
        for i in range(r[0], r[1]):
            prof[i] = rs[kk][2]


def nettoyer_masque(m, s, trou_max, run_min):
    """Bouche les trous < trou_max et retire les runs < run_min (abscisses s régulières)."""
    m = m.copy()
    iv = intervalles_masque(m, s)
    for (a0, a1), (b0, b1) in zip(iv[:-1], iv[1:]):
        if b0 - a1 < trou_max:
            m[(s > a1 - 1e-9) & (s < b0 + 1e-9)] = True
    for a0, a1 in intervalles_masque(m, s):
        if a1 - a0 < run_min:
            m[(s >= a0) & (s <= a1)] = False
    return m


# --------------------------------------------------------------------------- abaissés
def direction_marche(q, pps, dmax=4.0):
    """Direction de marche (unitaire) du passage piéton dont l'emprise contient chaque point, ou du
    plus proche à moins de dmax ; (directions, indice du passage ou -1)."""
    V = np.zeros((len(q), 2))
    idx = np.full(len(q), -1)
    best = np.full(len(q), np.inf)
    for k, g in enumerate(pps):
        r = g["anneau"]
        d, _, _ = distance_segments(q, r, np.roll(r, -1, axis=0))
        d[dans_polygone(q, [r])] = 0.0
        m = (d < best) & (d <= dmax)
        best[m], idx[m], V[m] = d[m], k, g["v"]
    return V, idx


def detecter_abaisses(P, L, attr, mnt):
    """Intervalles abaissés [s0, s1, type, sources, vue_mesurée, passages, accès] le long de la
    bordure orientée. Une bordure n'est abaissée pour un passage que si elle COUPE le sens de marche
    (angle > 45° avec la direction de marche) : les flancs d'îlots longés par le passage restent hauts."""
    n = max(1, int(round(L / PAS_AB)))
    s = (np.arange(n) + 0.5) * (L / n)
    q, tg = point_a(P, s)
    nrm = normale_gauche(tg)
    sondes = [q, q + nrm * 0.3, q - nrm * 0.3]
    pps = ctx.passages_pietons()
    V, gi = direction_marche(q, pps)
    coupe_marche = np.ones(n, bool)
    a_pp = gi >= 0
    coupe_marche[a_pp] = np.abs(np.einsum("ij,ij->i", tg[a_pp], V[a_pp])) <= COS_MARCHE_MAX
    rz = [p for _, _, p in ctx.zones_relief("traversee_bordure_abaissee")]
    m_rz = np.zeros(n, bool)
    for p in rz:
        for sd in sondes:
            m_rz |= dans_polygone(sd, p)
    m_rz &= coupe_marche
    m_pp = np.zeros(n, bool)
    pp_ids = [set() for _ in range(n)]
    for g in pps:
        dd = dans_polygone(q, [g["anneau"]]) & coupe_marche
        m_pp |= dd
        for i in np.nonzero(dd)[0]:
            pp_ids[i].add(g["id"])
    m_tf = np.array(attr(s, "traversee"), dtype=bool) & coupe_marche
    h = np.array([np.nan if v is None else v for v in attr(s, "h_vue_m")], dtype=float)
    statut = attr(s, "statut")
    # entrée charretière : bordure en contact avec un accès riverain et COUPÉE par son axe
    # (les bordures qui longent l'accès n'en sont que les rives)
    m_ar = np.zeros(n, bool)
    ar_ids = [set() for _ in range(n)]
    for sid, _, polys in ctx.acces_riverains():
        dd = np.zeros(n, bool)
        for sd in sondes:
            dd |= dans_polygones(sd, polys)
        if not dd.any():
            continue
        axe = ctx.axe_local_polygone(polys, q[dd])
        dd[np.nonzero(dd)[0]] = np.abs(np.einsum("ij,ij->i", tg[dd], axe)) <= COS_MARCHE_MAX
        m_ar |= dd
        for i in np.nonzero(dd)[0]:
            ar_ids[i].add(sid)
    # les zones et drapeaux de l'atelier relief ne servent que loin des passages dessinés
    pres_pp = gi >= 0
    m = nettoyer_masque(m_pp | ((m_rz | m_tf) & ~pres_pp) | m_ar, s, 1.0, 0.5)
    out = []
    for s0, s1 in intervalles_masque(m, s, 0.0, L):
        if s1 - s0 < LARGEUR_ABAISSE_MIN:           # arrêté du 15/01/2007 : abaissé ≥ 1,20 m
            c, h_ = 0.5 * (s0 + s1), LARGEUR_ABAISSE_MIN / 2
            s0, s1 = max(0.0, min(c - h_, L - LARGEUR_ABAISSE_MIN)), min(L, max(c + h_, LARGEUR_ABAISSE_MIN))
        sel = (s >= s0) & (s <= s1)
        srcs = []
        if (m_rz & ~pres_pp)[sel].any():
            srcs.append("relief_zones:traversee_bordure_abaissee")
        if (m_tf & ~pres_pp)[sel].any():
            srcs.append("bordures_hauteurs:traversee")
        pp = sorted(set().union(*[pp_ids[i] for i in np.nonzero(sel)[0]]))
        srcs += [f"passage:{p}" for p in pp]
        ar = sorted(set().union(*[ar_ids[i] for i in np.nonzero(sel)[0]]))
        srcs += [f"acces_riverain:{a}" for a in ar]
        typ = "charretiere" if ar and m_ar[sel].mean() >= 0.5 else "traversee"
        mes = [hh for hh, st in zip(h[sel], np.array(statut, dtype=object)[sel])
               if st in STATUTS_MESURES and np.isfinite(hh)]
        out.append([float(s0), float(s1), typ, srcs, float(np.median(mes)) if mes else None, pp, ar])
    # fusion des abaissés trop rapprochés (pas de ressauts successifs à moins de 2,50 m)
    fus = []
    for a in out:
        if fus and a[0] - fus[-1][1] < ECART_RESSAUTS_M and a[2] == fus[-1][2]:
            f = fus[-1]
            f[1] = a[1]
            f[3] = sorted(set(f[3]) | set(a[3]))
            f[5] = sorted(set(f[5]) | set(a[5]))
            f[6] = sorted(set(f[6]) | set(a[6]))
            f[4] = f[4] if a[4] is None else (a[4] if f[4] is None else min(f[4], a[4]))
        else:
            fus.append(a)
    return fus


def caler_chartieres(P, L, abaisses):
    """Blocs CHARTIERE GAM à moins de 1,0 m de la bordure : on prend le point d'insertion du bloc
    comme extrémité du bateau (le bateau couvre alors la largeur du passage : 3,0 m entre les deux
    blocs de la traversée NE pour des bandes de 2,98 m) ; la chartière de 1 m est posée au-delà.
    L'extrémité d'abaissé la plus proche (à ≤ 1,0 m) est recalée sur le bloc ; au-delà, le bloc est
    ignoré (bloc isolé ou d'une autre traversée)."""
    blocs = ctx.chartieres_gam()
    if not blocs:
        return []
    xy = np.array([b["xy"] for b in blocs])
    s, d, _ = projeter(P, xy)
    cales = []
    for b, sb, db in zip(blocs, s, d):
        if db > 1.0 or sb < -0.5 or sb > L + 0.5:
            continue
        best = None
        for a in abaisses:
            for bord in (0, 1):
                e = abs(a[bord] - sb)
                if e <= CALAGE_MAX and (best is None or e < best[0]):
                    best = (e, a, bord)
        if best is None:
            continue
        _, a, bord = best
        if bord == 0:
            a[0] = float(np.clip(sb, 0.0, a[1] - 0.5))
        else:
            a[1] = float(np.clip(sb, a[0] + 0.5, L))
        a[3] = sorted(set(a[3]) | {"chartiere_gam"})
        cales.append({"bloc": b["bloc"], "s": float(sb), "ref": b["ref"]})
    return cales


# --------------------------------------------------------------------------- bordure complète
def construire_bordure(kid, lg, P, s_src, sens, coupe, mnt, spec_refs, crit_haut, morceau):
    L = float(abscisses(P)[-1])
    attr = lambda s, cle: lg.attr(s_src(np.atleast_1d(s)), cle)
    n1 = max(1, int(round(L)))
    s1m = (np.arange(n1) + 0.5) * (L / n1)
    h = np.array([np.nan if v is None else v for v in attr(s1m, "h_vue_m")], dtype=float)
    statut = attr(s1m, "statut")
    # bordure neuve : créée après 2021, rehaussée en 2025 ou issue du plan projet (pas seulement
    # « dans l'emprise des travaux » : beaucoup de bordures mesurées en 2021 y sont conservées)
    travaux = (np.array(attr(s1m, "creee_apres_2021"), bool)
               | np.array([st == "modifiee_2025" for st in attr(s1m, "statut")])
               | np.array(["plan projet" in src for src in attr(s1m, "source")]))
    zone_trav = float(np.mean(attr(s1m, "zone_travaux_2025"))) >= 0.5
    contexte_ = attr(s1m, "contexte")
    q1, tg1 = point_a(P, s1m)
    nv1 = normale_gauche(tg1)
    cl_bas = ctx.classe_surface(q1 - nv1 * 0.5)
    cl_haut = ctx.classe_surface(q1 + nv1 * 0.6)
    ch_bas = ctx.dans_chaussee_2026(q1 - nv1 * 0.5)
    # hauteurs « estimee » (standard 0,14-0,20 de l'atelier relief, bordure postérieure à 2021) :
    # gardées si le côté bas est une chaussée ; sinon limite piste (A2) ou limite d'espace vert (P1)
    est = np.array([st == "estimee" for st in statut])
    vehic = ch_bas | np.isin(cl_bas, ["chaussee", "parking", "acces_riverain"])
    h_apriori = []
    for i in np.nonzero(est & ~vehic)[0]:
        if cl_bas[i] == "piste_cyclable":
            h[i] = H_LIMITE_PISTE
            h_apriori.append("a_priori:limite_piste_a2")
        else:
            h[i] = H_LIMITE_ESPACE_VERT
            h_apriori.append("a_priori:limite_espace_vert_p1")

    abaisses = detecter_abaisses(P, L, attr, mnt)
    cales = caler_chartieres(P, L, abaisses)

    # ---- profil courant (hors abaissés et chartières)
    dans_ab = np.zeros(n1, bool)
    for a in abaisses:
        dans_ab |= (s1m >= a[0] - CHARTIERE_M) & (s1m <= a[1] + CHARTIERE_M)
    hc = h.copy()
    hc[dans_ab] = np.nan
    if np.isfinite(hc).any():
        idx = np.arange(n1)
        ok = np.isfinite(hc)
        hc = np.interp(idx, idx[ok], hc[ok])
    elif np.isfinite(h).any():
        hc = np.full(n1, np.nanmax(h))
    else:
        hc = np.full(n1, 0.14)
    hl = mediane_glissante(hc, FENETRE_H)
    prof = [("QUAI_BUS" if c == "quai_bus" and v >= 0.15 else profil_de(v)) for v, c in zip(hl, contexte_)]
    prof = fusionner_courts(prof, hl, INTERVALLE_MIN)
    base = []
    for i0, i1, p in runs(prof):
        a0, a1 = (0.0 if i0 == 0 else i0 * L / n1), (L if i1 == n1 else i1 * L / n1)
        lo, hi = VUE_PLAGE[p]
        vue = float(np.clip(round(float(np.median(hc[i0:i1])) / 0.005) * 0.005, lo, hi - 1e-9 if p != "MURET_TALUS" else hi))
        st = collections.Counter(statut[i0:i1]).most_common(1)[0][0]
        base.append({"s0": a0, "s1": a1, "profil": p, "vue_m": round(vue, 3), "role": "courant", "_statut": st})

    def courant_a(sv):
        for b in base:
            if b["s0"] - 1e-9 <= sv <= b["s1"] + 1e-9:
                return b
        return base[-1]

    # ---- abaissés : bateau + chartières
    ab_out, overlay = [], []
    for k, a in enumerate(abaisses):
        s0, s1, typ, srcs, vmes, pp, ar = a
        if s1 - s0 < 0.3:
            continue
        cg, cd = courant_a(max(0.0, s0 - 0.5)), courant_a(min(L, s1 + 0.5))
        vue_c = max(cg["vue_m"], cd["vue_m"])
        if typ == "traversee":
            vue_b, src_vue = VUE_TRAVERSEE, "norme:arrete_2007-01-15_art1_ressaut_2cm"
        else:
            vue_b = VUE_CHARRETIERE if vmes is None else float(np.clip(round(vmes / 0.005) * 0.005, 0.02, 0.04))
            src_vue = "a_priori:charretiere_vue_2_4cm" if vmes is None else "lidar2021"
        vue_b = min(vue_b, vue_c)
        sel_b = (s1m >= s0) & (s1m <= s1)
        if not sel_b.any():
            sel_b = np.abs(s1m - 0.5 * (s0 + s1)) == np.min(np.abs(s1m - 0.5 * (s0 + s1)))
        bas_chaussee = float(np.mean(ch_bas[sel_b] | np.isin(cl_bas[sel_b], ["chaussee"]))) >= 0.5
        haut_pieton = float(np.mean(~ctx.dans_chaussee_2026(q1[sel_b] + nv1[sel_b] * 0.6)
                                    | np.isin(cl_haut[sel_b], list(PIETON)))) >= 0.5
        prof_b = "T2_bateau" if (vue_c >= 0.09 or bas_chaussee) else courant_a(0.5 * (s0 + s1))["profil"]
        if prof_b == "T2_bateau":
            prof_b_ref = spec_refs["T2_bateau"]
        else:
            prof_b_ref = spec_refs.get(prof_b, REGLE)
        raccords = []
        if vue_c - vue_b > 0.0095:                   # chartière dès 1 cm d'écart de vue (marche de tête)
            if s0 > 0.3:
                r0 = max(0.0, s0 - CHARTIERE_M)
                raccords.append({"s0": r0, "s1": s0, "cote": "debut", "vue_m": cg["vue_m"], "vue_m_fin": vue_b,
                                 "profil": cg["profil"]})
            if s1 < L - 0.3:
                r1 = min(L, s1 + CHARTIERE_M)
                raccords.append({"s0": s1, "s1": r1, "cote": "fin", "vue_m": vue_b, "vue_m_fin": cd["vue_m"],
                                 "profil": cd["profil"]})
        aid = f"A-{kid[2:]}-{k + 1}"
        bev = None
        if typ == "traversee" and bas_chaussee and haut_pieton:
            bev = bev_attendue(P, s0, s1, pp)
        ab_out.append({"id": aid, "type": typ, "s0": s0, "s1": s1, "vue_m": round(vue_b, 3),
                       "profil": prof_b, "raccords": raccords, "bev": bev, "passages": pp,
                       "acces_riverains": ar, "sources": srcs,
                       "_src_vue": src_vue, "_prof_ref": prof_b_ref})
        overlay.append((s0, s1, {"profil": prof_b, "vue_m": round(vue_b, 3), "role": "bateau", "abaisse": aid}))
        for r in raccords:
            overlay.append((r["s0"], r["s1"], {"profil": r["profil"], "vue_m": r["vue_m"],
                                               "vue_m_fin": r["vue_m_fin"], "role": "chartiere", "abaisse": aid}))

    rac_prof = raccords_de_profil(base, overlay, L)
    intervalles = superposer(base, overlay + rac_prof, L)

    # ---- courbure : éléments de 0,50 m si R < 12 m, pièces courbes si R < 3 m (pratique, flèche L²/8R)
    sc = np.arange(0.25, L, 0.5) if L > 0.5 else np.array([L / 2])
    R = rayon_courbure(P, sc, h=min(1.0, L / 3))
    courbes = []
    for cls, (rmin, rmax) in (("piece_courbe", (0, 3.0)), ("element_0_50", (3.0, 12.0))):
        m = (R >= rmin) & (R < rmax)
        for a0, a1 in intervalles_masque(m, sc, 0.0, L):
            if a1 - a0 >= 0.5:
                sel = (sc >= a0) & (sc <= a1)
                courbes.append({"s0": max(0.0, a0 - 0.25), "s1": min(L, a1 + 0.25),
                                "r_min_m": float(np.min(R[sel])), "pose": cls})
    courbes.sort(key=lambda c: c["s0"])
    fus = []
    for c in courbes:                                   # intervalles de même pose distants de ≤ 0,5 m fusionnés
        if fus and c["pose"] == fus[-1]["pose"] and c["s0"] - fus[-1]["s1"] <= 0.5:
            fus[-1]["s1"] = max(fus[-1]["s1"], c["s1"])
            fus[-1]["r_min_m"] = min(fus[-1]["r_min_m"], c["r_min_m"])
        else:
            fus.append(c)
    courbes = fus

    # ---- caniveau GAM au pied de la face vue (côté droit, parallèle, ≤ 0,40 m)
    caniveau, prov_can = None, None
    can = ctx.caniveaux_gam()
    if can:
        sc2 = np.arange(0.25, L, 0.5) if L > 0.5 else np.array([L / 2])
        q2, tg2 = point_a(P, sc2)
        devant_ = q2 - normale_gauche(tg2) * 0.15
        A = np.vstack([c[1][:-1] for c in can])
        B_ = np.vstack([c[1][1:] for c in can])
        ref_i = np.concatenate([np.full(len(c[1]) - 1, c[0]) for c in can])
        d, j, _ = distance_segments(devant_, A, B_)
        dirc = (B_[j] - A[j]) / np.maximum(np.hypot(*(B_[j] - A[j]).T), 1e-9)[:, None]
        m = (d <= 0.40) & (np.abs(np.einsum("ij,ij->i", tg2, dirc)) >= 0.9)
        ivs = [(a0, a1) for a0, a1 in intervalles_masque(m, sc2, 0.0, L) if a1 - a0 >= 1.0]
        if ivs:
            caniveau = {"profil": "CS2", "cote": "avant", "largeur_m": 0.25,
                        "intervalles": [[a0, a1] for a0, a1 in ivs],
                        "lignes_gam": sorted({int(x) for x in ref_i[j][m]})}
            prov_can = {"src": "gam", "ref": "SOL_CANIVEAU (caniveau_lin_L93) ; profil CS2 : bordures.json caniveaux", "conf": "moyenne"}

    # ---- matériau et aspect (a priori, sauf constat)
    neuf = float(travaux.mean()) >= 0.5
    materiau = "beton_clair" if neuf else "beton_gris"
    prov_mat = {"src": "a_priori:bordure_neuve_2025_beton_clair" if neuf else "a_priori:bordure_existante_beton_gris",
                "ref": ("bordure posée après 2021 (architecture v2, D5)" if neuf else "bordure mesurée au LiDAR 2021, conservée")
                + " ; manifeste_cc0 beton_bordure (albédo linéaire 0,35)", "conf": "faible"}
    for cid, lignes, mat, note in CONSTATS_MATERIAU:
        if lg.num in lignes:
            materiau = mat
            prov_mat = {"src": f"constat:{cid}", "ref": note, "conf": "moyenne"}
    aspect = dict(ASPECT_NEUF if neuf else ASPECT_ANCIEN)
    prov_aspect = {"src": "a_priori:usure_par_age", "ref": "neuve (posée après 2021)" if neuf else "existante", "conf": "faible"}
    for cid, lignes, maj, note in CONSTATS_ASPECT:
        if lg.num in lignes:
            aspect.update(maj)
            prov_aspect = {"src": f"constat:{cid}", "ref": note, "conf": "moyenne"}

    # ---- Z : fil d'eau (MNT 2026 à 0,30 m devant la face, côté droit), régularisé
    pts, sv = densifier(P, 1.0)
    _, tgv = point_a(P, sv)
    nlv = normale_gauche(tgv)
    devant = pts - nlv * 0.30
    z_av = mnt(*(repere(devant, "l93").T))
    vue_s = vue_aux(intervalles, sv)
    larg = np.array([largeur_base(intervalle_a(intervalles, x)["profil"]) for x in sv])
    z_ar = mnt(*(repere(pts + nlv * (larg + 0.30)[:, None], "l93").T)) - vue_s
    z, n_reg = regulariser_fil_eau(sv, z_av, z_ar)
    zf21 = np.array([np.nan if v is None else v for v in attr(sv, "z_fil_eau_2021_m")], float)
    st_v = attr(sv, "statut")
    tv = np.array(attr(sv, "zone_travaux_2025"), bool)
    ok21 = np.isfinite(zf21) & np.array([x in STATUTS_MESURES for x in st_v]) & ~tv
    ecart21 = float(np.median(np.abs(zf21[ok21] - z[ok21]))) if ok21.sum() >= 3 else None
    geom = coords_geojson(np.c_[repere(pts, "l93"), z])

    statut_major = collections.Counter(statut).most_common(1)[0][0]
    conf_h = "moyenne" if statut_major in STATUTS_MESURES else "faible"
    if len(h_apriori) >= 0.5 * n1:
        prov_intervalles = {"src": collections.Counter(h_apriori).most_common(1)[0][0],
                            "ref": f"{REGLE} ; hauteur standard de l'atelier relief remplacée (côté bas : {collections.Counter(cl_bas).most_common(1)[0][0] or 'hors surfaces'})",
                            "conf": "faible"}
    else:
        prov_intervalles = {"src": "lidar2021" if conf_h == "moyenne" else "a_priori:relief_hauteur_standard",
                            "ref": f"{REGLE} sur h_vue_m (bordures_hauteurs, statut majoritaire {statut_major})", "conf": conf_h}
    if rac_prof:
        prov_intervalles = dict(prov_intervalles, ref=prov_intervalles["ref"] + " ; raccords de profil : "
                                + ", ".join(f"{r0:.1f}-{r1:.1f} m" for r0, r1, _ in rac_prof)
                                + " (regle:raccord_profil, chartière de 1 m, écart de vue ≥ 1 cm)")
    src_geo, ref_geo = code_source(lg)
    props = {
        "id": kid,
        "famille": "bordures",
        "ligne_ref": "arete_avant",
        "face_vue": "droite",
        "longueur_m": L,
        "intervalles": intervalles,
        "abaisses": [{k: v for k, v in a.items() if not k.startswith("_")} for a in ab_out],
        "materiau": materiau,
        "finition": "lisse",
        "element_m": "auto",
        "joint_mm": 6,
        "phase_m": None,
        "courbes": courbes,
        "caniveau": caniveau,
        "aspect": aspect,
        "z_ref": "modele_2026",
        "zone_travaux_2025": bool(zone_trav),
        "coupe_zone": {"debut": bool(coupe[0]), "fin": bool(coupe[1])},
        "chartieres_gam": cales,
        "source": {"ligne": lg.num, "gam_index": lg.gam_index, "s_src_m": [round(morceau[0], 3), round(morceau[1], 3)],
                   "sens": "inverse" if sens < 0 else "direct", "doublons_supprimes": morceau[2],
                   "statut_hauteur": statut_major, "ecart_fil_eau_2021_mnt_m": ecart21},
        "prov": {
            "geometrie": {"src": src_geo, "ref": ref_geo, "conf": "haute" if src_geo == "gam" else "moyenne"},
            "face_vue": {"src": {"mnt_2026": "lidar2021", "cote_haut_relief": "lidar2021",
                                 "surfaces_v1": "a_priori:classes_surfaces_v1", "defaut": "a_priori:sens_numerisation"}[crit_haut[0]],
                         "ref": f"{crit_haut[0]} (dz gauche-droite {crit_haut[1]:+.3f} m)", "conf": "haute" if crit_haut[0] == "mnt_2026" else "moyenne"},
            "intervalles": prov_intervalles,
            "materiau": prov_mat,
            "aspect": prov_aspect,
            "element_m": {"src": "norme:NF_EN_1340", "ref": "éléments 0,994 m + joint 6 mm ; 0,50 m si R < 12 m", "conf": "moyenne"},
            "z": {"src": "a_priori:mnt_2026_fil_eau",
                  "ref": "heightmap_3025_10cm (sol 2026) à 0,30 m devant la face, régularisé (regle:fil_eau_regulier : "
                         "médiane glissante ±1,5 m, côté haut − vue si le devant est accidenté, lissage σ 0,6 m)"
                         + (f" ; {n_reg} sommet(s) corrigé(s) de plus de 2 cm" if n_reg else ""), "conf": "moyenne"},
        },
    }
    if prov_can:
        props["prov"]["caniveau"] = prov_can
    if ab_out:
        props["prov"]["abaisses"] = {"src": "lidar2021" if any(a["_src_vue"] == "lidar2021" for a in ab_out) else ab_out[0]["_src_vue"],
                                     "ref": "; ".join(sorted({s for a in ab_out for s in a["sources"]}))[:300],
                                     "conf": "moyenne"}
    feat = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": geom},
            "properties": arrondi(props)}
    return feat, ab_out


_SPEC_BORDURES = None


def largeur_base(profil):
    """Largeur (base) du profil, bordures.json (0,15 m par défaut)."""
    global _SPEC_BORDURES
    if _SPEC_BORDURES is None:
        _SPEC_BORDURES = lire_json(SPECS / "bordures.json")
    p = _SPEC_BORDURES["profils"].get(profil, {})
    return float(p.get("base") or p.get("largeur") or 0.15)


def intervalle_a(intervalles, s):
    for it in intervalles:
        if it["s0"] - 1e-9 <= s <= it["s1"] + 1e-9:
            return it
    return intervalles[-1]


def vue_aux(intervalles, sv):
    """Vue (m) aux abscisses sv, linéaire dans les chartières."""
    out = []
    for x in np.atleast_1d(sv):
        it = intervalle_a(intervalles, x)
        if "vue_m_fin" in it and it["s1"] > it["s0"]:
            t = float(np.clip((x - it["s0"]) / (it["s1"] - it["s0"]), 0, 1))
            out.append(it["vue_m"] + (it["vue_m_fin"] - it["vue_m"]) * t)
        else:
            out.append(it["vue_m"])
    return np.array(out)


def _mediane_s(s, v, demi):
    return np.array([np.median(v[np.abs(s - x) <= demi]) for x in s])


def regulariser_fil_eau(s, z_av, z_ar, demi=1.5, tol=0.02, sigma=0.6):
    """Fil d'eau régulier (regle:fil_eau_regulier). Le MNT à 0,30 m devant la face est bruité près des
    nez, des îlots et des talus (K-0507 : talus de noue, −1,34 → −0,51 m en 1 m ; K-0394 : −0,02 → −0,34
    au dernier sommet) ; une bordure préfabriquée suit une ligne régulière.
    1. estimation devant (z_av) et côté haut − vue (z_ar, MNT à base + 0,30 m derrière), recalée sur
       z_av par l'écart médian là où les deux sont réguliers ;
    2. par échantillon : z_av s'il s'écarte de moins de `tol` de sa médiane glissante (±1,5 m), sinon
       z_ar s'il est plus régulier, sinon la médiane de z_av ;
    3. points aberrants (> tol de la médiane glissante) remplacés, lissage gaussien σ = 0,6 m.
    Renvoie (z, nombre de sommets déplacés de plus de 2 cm)."""
    s = np.asarray(s, float)
    if len(s) < 3:
        return np.asarray(z_av, float), 0
    ma, mr = _mediane_s(s, z_av, demi), _mediane_s(s, z_ar, demi)
    ra, rr = np.abs(z_av - ma), np.abs(z_ar - mr)
    ok = (ra <= tol) & (rr <= tol)
    biais = float(np.median((z_av - z_ar)[ok])) if ok.sum() >= 3 else 0.0
    z_ar = z_ar + biais
    z = np.where(ra <= tol, z_av, np.where(rr < ra, z_ar, ma))
    mz = _mediane_s(s, z, demi)
    z = np.where(np.abs(z - mz) > tol, mz, z)
    w = np.exp(-0.5 * ((s[:, None] - s[None, :]) / sigma) ** 2)
    z = (w @ z) / w.sum(axis=1)
    return z, int((np.abs(z - z_av) > 0.02).sum())


def raccords_de_profil(base, overlay, L):
    """Changements de vue d'au moins 1 cm entre deux profils courants : élément de raccord (rôle
    chartière, 1 m centré sur le changement, loft du profil haut vers le profil bas ; pratique de pose,
    une marche de tête de 3 à 9 cm n'existe pas). Pas de raccord sous un abaissé."""
    out = []
    for b0, b1 in zip(base[:-1], base[1:]):
        if abs(b0["vue_m"] - b1["vue_m"]) < 0.0095:
            continue
        sb = b1["s0"]
        r0, r1 = max(b0["s0"], sb - CHARTIERE_M / 2), min(b1["s1"], sb + CHARTIERE_M / 2)
        if r1 - r0 < 0.5 or any(o0 < r1 + 0.05 and o1 > r0 - 0.05 for o0, o1, _ in overlay):
            continue
        haut = b0 if b0["vue_m"] >= b1["vue_m"] else b1
        out.append((r0, r1, {"profil": haut["profil"], "vue_m": b0["vue_m"], "vue_m_fin": b1["vue_m"],
                             "role": "chartiere"}))
    return out


def superposer(base, overlay, L):
    """Intervalles finaux : profil courant découpé par les bateaux et chartières (partition de [0, L])."""
    coupes = {0.0, L}
    for b in base:
        coupes |= {b["s0"], b["s1"]}
    for s0, s1, _ in overlay:
        coupes |= {max(0.0, s0), min(L, s1)}
    cs = sorted(c for c in coupes if 0.0 <= c <= L)
    out = []
    for a0, a1 in zip(cs[:-1], cs[1:]):
        if a1 - a0 < 1e-6:
            continue
        m = 0.5 * (a0 + a1)
        it = None
        for s0, s1, d in overlay:
            if s0 <= m <= s1 and (it is None or d["role"] == "bateau"):
                it = dict(d)
                if "vue_m_fin" in d:
                    t0, t1 = (a0 - s0) / (s1 - s0), (a1 - s0) / (s1 - s0)
                    it["vue_m"] = round(d["vue_m"] + (d["vue_m_fin"] - d["vue_m"]) * t0, 3)
                    it["vue_m_fin"] = round(d["vue_m"] + (d["vue_m_fin"] - d["vue_m"]) * t1, 3)
        if it is None:
            for b in base:
                if b["s0"] <= m <= b["s1"]:
                    it = {k: v for k, v in b.items() if not k.startswith("_")}
        it["s0"], it["s1"] = a0, a1
        if out and all(out[-1].get(k) == it.get(k) for k in ("profil", "vue_m", "role", "abaisse")) \
                and "vue_m_fin" not in it and "vue_m_fin" not in out[-1]:
            out[-1]["s1"] = a1
        else:
            out.append(it)
    ordre = ["s0", "s1", "profil", "vue_m", "vue_m_fin", "role", "abaisse"]
    return [{k: x[k] for k in ordre if k in x} for x in out]


def bev_attendue(P, s0, s1, passages):
    """BEV attendue sur un abaissé de traversée : norme (NF P98-351) sauf OSM tactile_paving=no."""
    mid, _ = point_a(P, 0.5 * (s0 + s1))
    osm = ctx.osm_traversees()
    if osm:
        xy = np.array([o["xy"] for o in osm])
        d = np.hypot(*(xy - mid[0]).T)
        i = int(np.argmin(d))
        if d[i] < 6.0 and osm[i]["tactile_paving"] in ("yes", "no"):
            return {"present": osm[i]["tactile_paving"] == "yes",
                    "prov": {"src": f"osm:{osm[i]['osm']}", "ref": f"tactile_paving={osm[i]['tactile_paving']} à {d[i]:.1f} m", "conf": "moyenne"}}
    return {"present": True, "prov": {"src": "norme:NF_P98-351", "ref": "BEV en tête de traversée", "conf": "moyenne"}}


def ponctuel_bev(kid, P, ab, mnt, exclusions=()):
    """Bande de BEV (dalles 0,40 × 0,40) derrière le bateau, à 0,50 m du nez, côté haut (gauche).
    La bande est rognée à la plus longue portion hors des îlots voisins (`exclusions`, polygones
    locaux) et de la zone pilote ; moins de deux dalles : pas de BEV."""
    s = np.arange(ab["s0"], ab["s1"] + 1e-9, 0.1)
    if len(s) < 2:
        return None
    q, tg = point_a(P, s)
    n = normale_gauche(tg)
    zone = ctx.zone_pilote()["anneau"]
    libre = np.ones(len(s), bool)
    for d in (BEV_RETRAIT, BEV_RETRAIT + BEV_PROFONDEUR / 2, BEV_RETRAIT + BEV_PROFONDEUR):
        libre &= dans_polygone(q + n * d, [zone])
        for poly in exclusions:
            libre &= ~dans_polygone(q + n * d, poly)
    runs_ = intervalles_masque(libre, s)
    if not runs_:
        return None
    s0, s1 = max(runs_, key=lambda r: (r[1] - r[0], -r[0]))
    if s1 - s0 < 2 * 0.40 - 1e-6:
        return None
    seg = sous_polyligne(P, s0, s1)
    a = decaler(seg, BEV_RETRAIT)
    b = decaler(seg, BEV_RETRAIT + BEV_PROFONDEUR)
    anneau = np.vstack([a, b[::-1]])
    if aire_signee(anneau) < 0:
        anneau = anneau[::-1]
    z = mnt(*(repere(anneau, "l93").T))
    ring = np.c_[repere(anneau, "l93"), z]
    ring = np.vstack([ring, ring[:1]])
    long = float(abscisses(seg)[-1])
    rogne = (s1 - s0) < (ab["s1"] - ab["s0"]) - 0.05
    return {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords_geojson(ring)]},
            "properties": arrondi({
                "id": f"BEV-{ab['id'][2:]}", "famille": "ponctuels_sol", "type": "bev",
                "materiau_id": "bev_podotactile", "module_m": [0.40, 0.40], "profondeur_m": BEV_PROFONDEUR,
                "retrait_nez_m": BEV_RETRAIT, "longueur_m": long, "nb_dalles": max(1, int(round(long / 0.40))),
                "ancrage": {"bordure": kid, "abaisse": ab["id"], "s0": s0, "s1": s1, "cote": "gauche",
                            "rognee": bool(rogne)},
                "prov": {"geometrie": {"src": "norme:NF_P98-351", "ref": "mobilier.json bev_podotactile : première ligne de plots à 0,50 m du nez ; dalles 0,40 ; rognée hors îlots", "conf": "moyenne"},
                         "presence": ab["bev"]["prov"]}})}


def bev(candidats, mnt, exclusions=()):
    out = []
    for kid, P, ab in candidats:
        f = ponctuel_bev(kid, P, ab, mnt, exclusions)
        if f:
            out.append(f)
    return out


# Constats appliqués aux bordures, par ligne source (numéros GAM / plan projet stables)
CONSTATS_MATERIAU = [
    ("p2025_01_vercors-26", {372, 389, 390, 629}, "beton_clair",
     "îlots du Vercors : bordures claires, presque blanches (12/01/2025, avant reprise 2025)"),
]
CONSTATS_ASPECT = [
    ("p2025_05_360-32", {353, 354}, {"herbe_joints": 0.6, "salissure": 0.5},
     "accotement non tondu de l'approche NE : l'herbe déborde sur la bordure béton (18/05/2025)"),
    ("p2025_01_vercors-26", {372, 389, 390, 629}, {"epaufrures": 0.15, "mousse_joints": 0.1},
     "bordures continues, quelques épaufrures, mousses et feuilles (12/01/2025)"),
]
ASPECT_NEUF = {"epaufrures": 0.05, "mousse_joints": 0.0, "herbe_joints": 0.05, "salissure": 0.15}
ASPECT_ANCIEN = {"epaufrures": 0.3, "mousse_joints": 0.35, "herbe_joints": 0.3, "salissure": 0.45}


def construire(mnt):
    """Bordures de la zone pilote : (features bordures, features BEV, rapport)."""
    spec = lire_json(SPECS / "bordures.json")
    spec_refs = verifier_regles(spec)
    lignes = charger_lignes()
    morceaux, st_app = apparier(lignes, mnt)
    zone = ctx.zone_pilote()["anneau"]
    feats, bevs, rapport = [], [], {"appariement": dict(st_app), "orientation": collections.Counter()}
    par_ligne = collections.defaultdict(list)
    for n, s0, s1, dbl in morceaux:
        lg = lignes[n]
        P0 = sous_polyligne(lg.P, s0, s1)
        L0 = float(abscisses(P0)[-1])
        f_src = lambda s, s0=s0: s0 + s
        sens, crit, dz = cote_haut(P0, lg, f_src, 1, mnt)
        rapport["orientation"][crit] += 1
        P1 = P0 if sens > 0 else P0[::-1]
        for c0, c1 in couper_polyligne(P1, [zone]):
            if c1 - c0 < L_MIN:
                continue
            P = sous_polyligne(P1, c0, c1)
            if sens > 0:
                s_src = (lambda s, a=s0 + c0: a + s)
            else:
                s_src = (lambda s, a=s0 + L0 - c0: a - s)
            coupe = (c0 > 1e-6, c1 < float(abscisses(P1)[-1]) - 1e-6)
            par_ligne[n].append((c0 if sens > 0 else L0 - c1, P, s_src, sens, coupe, (crit, dz), (s0, s1, dbl)))
    for n in sorted(par_ligne):
        ms = sorted(par_ligne[n], key=lambda m: m[0])
        for k, (_, P, s_src, sens, coupe, crit, morceau) in enumerate(ms):
            kid = f"K-{n:04d}" + ("" if len(ms) == 1 else "abcdefghijklmnopqrstuvwxyz"[k])
            f, abs_ = construire_bordure(kid, lignes[n], P, s_src, sens, coupe, mnt, spec_refs, crit, morceau)
            feats.append(f)
            for a in abs_:
                if a["bev"] and a["bev"]["present"]:
                    bevs.append((kid, P, a))
    rapport["orientation"] = dict(rapport["orientation"])
    return feats, bevs, rapport
