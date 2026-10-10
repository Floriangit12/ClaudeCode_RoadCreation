"""Lignes longitudinales et transversales : ancrage OpenDRIVE (bord de voie + t_off) ou axe propre
(levé GAM, sinon axe ajusté sur les polygones v1), modulation, phase des tirets, largeur, interruptions aux
zébras.

Ligne (classe ligne) :
    géométrie = axe de la ligne (LineString, Douglas-Peucker 1 mm de l'axe exact) ; σ = abscisse
    curviligne le long de cet axe depuis son premier sommet ;
    ancrage {type: "xodr", route, bords: [{section_s, voie, s0, s1}], t_off_m} : axe = bord extérieur de
        la voie `voie` de la laneSection (voie 0 : référence + laneOffset) décalé de t_off (t > 0 à
        gauche, comme OpenDRIVE) entre les abscisses de route s0 et s1 ;
    ancrage {type: "axe", source: gam | v1} : l'axe est la géométrie elle-même (sommets anguleux du levé
        raccordés par des congés, marquages_glyphes.adoucir) ;
    discontinue : tiret k = [phase_m + k·(trait_m + vide_m), … + trait_m] ∩ [0, longueur_m], hors
        `interruptions` [[σ0, σ1], …] ; modulation = code IISR, modulation_source IISR | mesuree ; l'axe
        commence et finit sur un tiret (tiret partiel gardé seulement s'il fait au moins la moitié du trait) ; quand
        la phase vient de l'ortho, l'axe garde l'étendue observée (fenêtre de la corrélation) et les tirets de bout
        trop courts sont masqués par des interruptions de bout (interruptions_bouts, comprises dans interruptions).
Axe levé GAM : deux lignes GAM parallèles à 0,06-0,25 m sont les deux bords d'une marque (axe = médiane,
    largeur = écartement : marquages_gam.axes_leves).
Phase des tirets, par ordre de preuve (prov.phase_m) :
    1. tirets levés un à un dans le GAM (lignes ouvertes droites isolées de 0,3 à 6,5 m à moins de 0,30 m de
       l'axe ; les morceaux d'une polyligne chaînée ne sont pas des tirets) ;
    2. ortho PCRS 5 cm 2022 : corrélation luminance / motif (modulation gardée), pic ≥ 0,25 pour les états
       conserve / refait_2025_identique, ≥ 0,5 pour une ligne repeinte en 2025 sur ses tirets 2022 ; revérifiée
       après rognage de l'axe ;
    3. tirets v1 observés (plan projet 2025, ortho top-hat) ; sinon tirets v1 synthétiques (« GAM + tirets
       mesurés », « complété au pas mesuré », « + IISR ») : confiance faible. Des tirets synthétiques espacés de
       moins de 0,30 m font une ligne continue.
Largeur (prov.largeur_m) : u homogène par itinéraire (Verdun et centre du carrefour u = 0,06, autres u =
    0,05, pistes u = 0,03) x rôle (axe / délimitation / stationnement 2u, rive et contour 3u, bande cyclable
    ou couloir bus 5u, rôle lu sur les voies OpenDRIVE voisines) ; largeur levée (paire de bords GAM) gardée
    seulement quand elle diffère de plus de 2,5 cm de 2u / 3u / 5u.
Transversale (classe transversale, ligne d'effet des feux T'2 0,15) : axe en travers des voies, n =
    ⌊(L + vide) / (trait + vide)⌋ tirets centrés sur l'axe ; ancrage sur l'objet stopLine du .xodr et la route.
"""
import collections
import functools
import math

import numpy as np

import marquages_commun as M
import marquages_gam as MG
import marquages_glyphes as GL
import marquages_ortho as MO
import xodr_echantillonne as X
from commun import abscisses, couper_polyligne, densifier, point_a, projeter

U_VERDUN, U_DEFAUT, U_PISTE = 0.06, 0.05, 0.03
TOL_LAT = 0.30               # écart latéral maximal à un bord de voie pour l'ancrage xodr
TOL_PAR = 0.985              # cosinus minimal entre la ligne et le bord
TOL_LAT_GAM = 0.04           # écart p95 bord + t_off / levé GAM au-delà duquel on ancre sur l'axe GAM
BRANCHES_VERDUN = ("verdun_sw", "verdun_ne", "verdun_sw_lointain", "centre")
RESEAU = []                  # réseau courant (largeurs des roadMarks, rôles des voies)
PARTIEL_MIN = 0.5            # tiret de bout gardé s'il fait au moins cette part du trait
ROLES_U = {"axe": 2, "delimitation": 2, "stationnement": 2, "rive": 3, "bande": 5, "rive_piste": 3}
SYNTHETIQUES = ("tirets mesurés", "IISR T3", "complété au pas")


def modulations():
    return M.spec()["modulations"]["table"]


@functools.lru_cache(maxsize=None)
def LIBRES_GAM():
    """Lignes GAM ouvertes non rattachées au v1 (prolongements possibles d'une marque levée)."""
    refs = {k for m in M.v1() for k in M.gam_refs(m["p"])}
    return frozenset(k for k, P in enumerate(M.gam_lin()) if k not in refs and MG.ouverte(P))


def synthetique(m):
    """Tiret v1 synthétique (position déduite d'une modulation, pas observée)."""
    return any(k in m["p"]["source"] for k in SYNTHETIQUES)


# --------------------------------------------------------------------------- axe d'un polygone v1
def axe_bande(r, largeur=None):
    """Axe d'une bande obtenue par tampon d'une polyligne (sommets appariés gauche/droite), sinon None."""
    n2 = len(r)
    if n2 < 6 or n2 % 2:
        return None
    n = n2 // 2
    best = None
    for k in range(n2):
        idx_a = (np.arange(n) + k) % n2
        idx_b = (2 * n - 1 - np.arange(n) + k) % n2
        d = np.hypot(*(r[idx_a] - r[idx_b]).T)
        cle = float(np.std(d))
        if best is None or cle < best[0]:
            best = (cle, idx_a, idx_b, d)
    cle, ia, ib, d = best
    w = float(np.median(d))
    if cle > 0.03 or (largeur and abs(w - largeur) > 0.08) or w > 0.6:
        return None
    return 0.5 * (r[ia] + r[ib])


def axe_marque(m):
    """Axe (polyligne locale) d'une marque v1 linéaire."""
    o = m["obb"]
    gam = M.gam_refs(m["p"])
    if gam and o["W"] > 0.35:
        o_ = m["obb"]
        P, _ = _gam_axe(gam, np.vstack([o_["c"] - o_["u"] * o_["L"] / 2, o_["c"], o_["c"] + o_["u"] * o_["L"] / 2]))
        s, d, _ = projeter(P, m["r"])
        if np.median(d) < 0.3:
            s = s[d <= 0.5]
            return _sous(P, s.min(), s.max())
    if o["W"] > 0.35:
        a = axe_bande(m["r"], m["p"].get("largeur_m"))
        if a is not None:
            return a
    return np.vstack([o["c"] - o["u"] * o["L"] / 2, o["c"] + o["u"] * o["L"] / 2])


def _sous(P, s0, s1):
    S = abscisses(P)
    pts, _ = point_a(P, np.r_[s0, S[(S > s0) & (S < s1)], s1])
    return M.dedoublonner(pts)


# --------------------------------------------------------------------------- chaînes de bords OpenDRIVE
class ChaineBord:
    """Bord de voie continu d'une route à travers ses laneSections (même ligne physique)."""

    def __init__(self, route, bords):
        self.route = route
        self.bords = bords
        self.s = np.concatenate([b.s if i == 0 else b.s[1:] for i, b in enumerate(bords)])
        self.xy = np.vstack([b.xy if i == 0 else b.xy[1:] for i, b in enumerate(bords)])
        self.hdg = np.concatenate([b.hdg if i == 0 else b.hdg[1:] for i, b in enumerate(bords)])
        self.sig = abscisses(self.xy)
        self.cle = f"{route}:" + "|".join(f"{b.section_s:g}/{b.voie}" for b in bords)
        self.bbox = (*self.xy.min(axis=0) - 1.0, *self.xy.max(axis=0) + 1.0)

    def s_de_sig(self, sig):
        return np.interp(sig, self.sig, self.s)

    def axe(self, t_off, s0, s1, avec_s=False, profil=None):
        """Axe décalé de t_off (normale de la référence) entre les abscisses de route s0 et s1 ; profil [[s, δt], ...] :
        écart latéral supplémentaire interpolé linéairement en s (constant au-delà des nœuds)."""
        m = (self.s > s0 + 1e-6) & (self.s < s1 - 1e-6)
        ss = np.r_[s0, self.s[m], s1]
        if profil:
            ks = np.array([p[0] for p in profil], float)
            ss = np.unique(np.r_[ss, ks[(ks > s0 + 1e-6) & (ks < s1 - 1e-6)]])
        x = np.interp(ss, self.s, self.xy[:, 0])
        y = np.interp(ss, self.s, self.xy[:, 1])
        h = np.interp(ss, self.s, np.unwrap(self.hdg))
        t = t_off + (np.interp(ss, [p[0] for p in profil], [p[1] for p in profil]) if profil else 0.0)
        P = np.c_[x - t * np.sin(h), y + t * np.cos(h)]
        garde = np.r_[True, np.hypot(*np.diff(P, axis=0).T) > 1e-4]
        return (P[garde], ss[garde]) if avec_s else P[garde]

    def troncons(self, s0, s1):
        out = []
        for b in self.bords:
            a, z = max(s0, b.s0), min(s1, b.s1)
            if z - a > 1e-6:
                out.append({"section_s": round(b.section_s, 3), "voie": b.voie, "s0": round(a, 3), "s1": round(z, 3)})
        return out


def chaines_reseau(reseau):
    out = []
    for rid in sorted(reseau, key=int):
        bords = X.bords_route(reseau[rid])
        par_sec = collections.defaultdict(list)
        for b in bords:
            par_sec[b.section_s].append(b)
        secs = sorted(par_sec)
        suite = {}
        for s_a, s_b in zip(secs[:-1], secs[1:]):
            for b in par_sec[s_a]:
                cands = [(float(np.hypot(*(c.xy[0] - b.xy[-1]))), c.voie, c) for c in par_sec[s_b]]
                d, _, c = min(cands, key=lambda x: (x[0], x[1]))
                if d < 0.05:
                    suite[id(b)] = c
        vus = set()
        for s_a in secs:
            for b in sorted(par_sec[s_a], key=lambda b: b.voie):
                if id(b) in vus:
                    continue
                ch = [b]
                vus.add(id(b))
                while id(ch[-1]) in suite and id(suite[id(ch[-1])]) not in vus:
                    ch.append(suite[id(ch[-1])])
                    vus.add(id(ch[-1]))
                out.append(ChaineBord(rid, ch))
    return out


def ancrer(chaines, P, u, tous=False):
    """Meilleure chaîne de bord pour un axe P (local) de direction moyenne u : (chaîne, t_off, frac) ou
    None ; tous=True : liste de toutes les chaînes acceptables [(clé de tri, chaîne, t_off, frac)]."""
    Q, _ = densifier(P, 0.25)
    best = None
    ok_ = []
    for ch in chaines:
        x0, y0, x1, y1 = ch.bbox
        if Q[:, 0].max() < x0 or Q[:, 0].min() > x1 or Q[:, 1].max() < y0 or Q[:, 1].min() > y1:
            continue
        sig, d, cote = projeter(ch.xy, Q)
        i = np.clip(np.searchsorted(ch.sig, sig) - 1, 0, len(ch.sig) - 2)
        tg = ch.xy[i + 1] - ch.xy[i]
        tg /= np.maximum(np.hypot(*tg.T), 1e-12)[:, None]
        par = np.abs(tg @ u)
        ok = (d < TOL_LAT) & (par > TOL_PAR) & (sig > 0.02) & (sig < ch.sig[-1] - 0.02)
        frac = float(ok.mean())
        if frac < 0.8:
            continue
        t = (cote * d)[ok]
        cle = (round(float(np.median(np.abs(t))), 2), int(ch.route), abs(ch.bords[0].voie))
        ok_.append((cle, ch, float(np.median(t)), frac))
        if best is None or cle < best[0]:
            best = (cle, ch, float(np.median(t)), frac)
    if tous:
        return ok_
    return None if best is None else best[1:]


# --------------------------------------------------------------------------- modulation et phase
TOL_PHASE = 0.10             # écart maximal d'un début / fin de tiret au modèle (m)
PARTIEL = 0.85               # tiret v1 plus court que 0,85·trait : partiel (occultation), une seule extrémité fiable


def _residus(a, b, T, P, phi):
    """Écarts des débuts / fins observés au modèle [φ + kP, φ + kP + T] ; par tiret : max des deux
    écarts (tiret complet) ou min (tiret partiel)."""
    k = np.round(((a + b) / 2 - phi - T / 2) / P)
    ra = a - (phi + k * P)
    rb = b - (phi + k * P + T)
    partiel = (b - a) < PARTIEL * T
    r = np.where(partiel, np.minimum(np.abs(ra), np.abs(rb)), np.maximum(np.abs(ra), np.abs(rb)))
    return ra, rb, k, r, partiel


def _phase(a, b, T, P):
    """Phase φ (début de tiret, modulo P) : moyenne circulaire des débuts (et fins − T) des tirets
    complets, puis 3 itérations de moindres carrés robustes (médiane des écarts fiables)."""
    comp = (b - a) >= PARTIEL * T
    if not comp.any():
        comp = np.ones(len(a), bool)
    z = np.exp(2j * np.pi * np.r_[a[comp], b[comp] - T] / P)
    phi = (np.angle(z.mean()) / (2 * np.pi) * P) % P
    for _ in range(3):
        ra, rb, _, _, partiel = _residus(a, b, T, P, phi)
        e = np.r_[ra[~partiel], rb[~partiel]]
        if partiel.any():
            e = np.r_[e, np.where(np.abs(ra) < np.abs(rb), ra, rb)[partiel]]
        phi = (phi + float(np.median(e))) % P
    return phi


def ajuster(a, b, code):
    """Modèle d'un groupe de tirets : IISR (code) s'il tient à TOL_PHASE, sinon mesuré (trait médian
    des tirets complets, période par régression des débuts). -> dict ou None."""
    tab = modulations()
    nom = tab.get(code)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if nom:
        T, P = nom["trait_m"], nom["periode_m"]
        phi = _phase(a, b, T, P)
        r = _residus(a, b, T, P, phi)[3]
        if r.max() <= TOL_PHASE:
            return {"src": "IISR", "code": code, "T": T, "P": P, "phi": phi, "r": r}
    lg = b - a
    if len(a) == 1:
        T = float(lg[0])
        P = T + (nom["vide_m"] if nom else T)
        return dict(_source_modulation(code, T, P), T=T, P=P, phi=float(a[0]), r=np.zeros(1))
    T = float(np.median(lg[lg >= PARTIEL * lg.max()]))
    comp = lg >= PARTIEL * T
    deb = a[comp] if comp.sum() >= 2 else a
    d = np.diff(np.sort(deb))
    if not np.any(d > T * 0.9):
        return None
    P = float(np.min(d[d > T * 0.9]))
    if nom and abs(P - nom["periode_m"]) / nom["periode_m"] < 0.1:
        P = nom["periode_m"]
    for _ in range(3):
        k = np.round((deb - deb[0]) / P)
        if len(np.unique(k)) < 2:
            return None
        (c0, P), *_ = np.linalg.lstsq(np.c_[np.ones(len(k)), k], deb, rcond=None)
        if P <= T + 0.02:
            return None
    phi = _phase(a, b, T, P)
    r = _residus(a, b, T, P, phi)[3]
    if r.max() > TOL_PHASE:
        return None
    return dict(_source_modulation(code, T, float(P)), T=T, P=float(P), phi=phi, r=r)


def segmenter(a, b, code):
    """Découpe gloutonne d'une suite de tirets (triés) en segments réguliers : [(i0, i1, modèle)]."""
    out, i = [], 0
    while i < len(a):
        fit = ajuster(a[i:i + 1], b[i:i + 1], code)
        j = i
        while j + 1 < len(a):
            f2 = ajuster(a[i:j + 2], b[i:j + 2], code)
            if f2 is None:
                break
            fit, j = f2, j + 1
        out.append((i, j, fit))
        i = j + 1
    return out


def _code_proche(T, P):
    for code, v in modulations().items():
        if abs(P - v["periode_m"]) / v["periode_m"] < 0.06 and abs(T - v["trait_m"]) / v["trait_m"] < 0.12:
            return code
    return None


# --------------------------------------------------------------------------- largeur
def u_itineraire(branche, piste=False):
    if piste:
        return U_PISTE
    return U_VERDUN if branche in BRANCHES_VERDUN else U_DEFAUT


def role_xodr(ch, s):
    """Rôle d'une ligne portée par un bord OpenDRIVE à l'abscisse s : (rôle, référence)."""
    if not RESEAU or ch is None:
        return None
    route = RESEAU[0][ch.route]
    for b in ch.bords:
        if b.s0 - 1e-6 <= s <= b.s1 + 1e-6:
            sec = next((x for x in route.sections if abs(x.s - b.section_s) < 1e-6), None)
            if sec is None:
                return None
            if b.voie == 0:
                return "axe", f"route {ch.route} : axe (voie 0)"
            sg = 1 if b.voie > 0 else -1
            ti = sec.voies[b.voie].type if b.voie in sec.voies else None
            te = sec.voies[b.voie + sg].type if (b.voie + sg) in sec.voies else None
            ref = f"route {ch.route} section {sec.s:g} : voie {b.voie} ({ti}) | voie {b.voie + sg} ({te})"
            if {ti, te} & {"bus", "biking"} and {ti, te} & {"driving"}:
                return "bande", ref
            if ti == "driving" and te in (None, "curb", "border", "sidewalk", "shoulder", "median"):
                return "rive", ref
            return "delimitation", ref
    return None


def role_ligne(ms, tl, code, ch=None, s=None):
    """(rôle, référence) : groupe v1 (stationnement, rive), modulation de rive (T2, T'3), voies OpenDRIVE."""
    g = _maj(ms, "groupe") or ""
    code = (code or "").replace("_site", "")
    if "stationnement" in g:
        return "stationnement", f"groupe v1 {g}"
    if "rive" in g:
        return "rive", f"groupe v1 {g}"
    if code in ("T2", "T'3"):
        return "rive", f"modulation {code} (rive, IISR art. 113-2)"
    r = role_xodr(ch, s) if ch is not None and s is not None else None
    return r or ("axe", "défaut : axe / délimitation de voies")


def largeur(ms, type_ligne, branche, role, paire=None):
    """(largeur_m, prov) : largeur levée d'une paire de bords GAM si elle s'écarte de plus de 2,5 cm de 2u / 3u /
    5u (sinon la valeur IISR la plus proche) ; rive de piste 3u (u = 0,03) ; sinon n·u du rôle, u homogène sur
    l'itinéraire (Verdun et centre 0,06, autres 0,05)."""
    piste = any("chronovelo" in (m["p"]["groupe"] or "") for m in ms)
    u = u_itineraire(branche, piste)
    if paire is not None and 0.06 <= paire <= 0.35:
        n = min((2, 3, 5), key=lambda k: (round(abs(paire - k * u), 4), k))
        if abs(paire - n * u) <= 0.025:
            return round(n * u, 3), {"src": "gam", "ref": f"bords levés écartés de {paire:.3f} m -> {n}u, u = {u}", "conf": "haute"}
        return round(paire, 2), {"src": "gam", "ref": f"bords levés écartés de {paire:.3f} m (hors 2u / 3u / 5u, u = {u}) : largeur levée gardée", "conf": "haute"}
    if piste:
        return round(3 * U_PISTE, 3), {"src": "regle:marquages_geometrie.cycles", "ref": "rive de piste 3u, u = 0,03", "conf": "moyenne"}
    r, ref = role
    n = ROLES_U[r]
    return round(n * u, 3), {"src": "regle:marquages_geometrie.largeurs_par_ligne",
                             "ref": f"{r} {n}u, u = {u} homogène sur l'itinéraire ({branche}) ; {ref}", "conf": "moyenne"}


LARGEUR_T3 = 0.12            # ARCHITECTURE.md, phase 2 : « largeurs T3 harmonisées (0,12 ou 0,15, documenté) »


def harmoniser_t3(e, role, w, pw):
    """Lignes T3 (axe / délimitation / rive, hors bandes cyclables et couloirs bus 5u) : largeur unique LARGEUR_T3 =
    2u avec u = 0,06 (valeur mesurée dominante, décision utilisateur n° 10 en attente) ; la largeur qu'aurait donnée la
    règle d'itinéraire est notée dans la provenance."""
    if e.get("modulation", "").replace("_site", "") != "T3" or role[0] in ("bande",):
        return w, pw
    if abs(w - LARGEUR_T3) < 1e-6:
        return w, dict(pw, ref=pw["ref"] + " ; T3 harmonisée à 0,12 (critère phase 2)")
    return LARGEUR_T3, {"src": "regle:marquages_geometrie.largeurs_par_ligne",
                        "ref": f"T3 harmonisée à {LARGEUR_T3} (2u, u = 0,06 ; critère phase 2 « largeurs T3 harmonisées 0,12 ou "
                               f"0,15 » ; décision utilisateur n° 10 en attente) ; règle d'itinéraire : {w} ({pw['ref']})",
                        "conf": "moyenne"}


def largeur_xodr(reseau, ch, s0, s1, tl):
    """Largeur du roadMark peint du bord (type compatible) au milieu de [s0, s1], ou None."""
    s = 0.5 * (s0 + s1)
    for b in ch.bords:
        if b.s0 - 1e-6 <= s <= b.s1 + 1e-6:
            m = X.marque_active(reseau[ch.route], b.section_s, b.voie, s)
            if m and (("broken" in m["type"]) == (tl == "discontinue")) and m["type"] not in ("none", "curb"):
                return float(m.get("width") or 0) or None
    return None


# --------------------------------------------------------------------------- construction
def _intervalles(axe, ms):
    """Intervalles σ [min, max] des sommets de chaque marque projetés sur l'axe."""
    out = []
    for m in ms:
        pts = np.vstack([r for poly in m["polys"] for r in poly[:1]])
        s, d, _ = projeter(axe, pts)
        proche = d <= max(0.5, 2.0 * float(np.median(d)) + 0.05)
        s = s[proche] if proche.any() else s
        out.append((float(s.min()), float(s.max()), float(np.median(d))))
    return out


def _unions(items, lie):
    par = list(range(len(items)))

    def rac(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if lie(items[i], items[j]):
                par[rac(j)] = rac(i)
    g = collections.defaultdict(list)
    for i, it in enumerate(items):
        g[rac(i)].append(it)
    return sorted(g.values(), key=lambda x: x[0]["id"])


def _ecart_max(type_ligne, code):
    if type_ligne == "continue":
        return 0.5
    nom = modulations().get(code)
    return 2 * nom["periode_m"] + 0.5 if nom else 15.0


def _usure(ms):
    c = collections.Counter(m["p"]["usure"] for m in ms)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _maj(ms, cle):
    c = collections.Counter(m["p"][cle] for m in ms)
    return sorted(c.items(), key=lambda kv: (-kv[1], str(kv[0])))[0][0]


def lignes(reseau, emprises_zebras):
    """Lignes longitudinales -> (entités, devenir, mesures)."""
    tous = [m for m in M.v1() if m["p"]["type"] in ("ligne_continue", "ligne_discontinue")
            and m["p"]["groupe"] not in ("piste_chronovelo_axe", "hachures")]
    chaines = chaines_reseau(reseau)
    RESEAU[:] = [reseau]
    for m in tous:
        m["_axe"] = axe_marque(m)
        P = m["_axe"]
        u = P[-1] - P[0]
        m["_u"] = u / max(np.hypot(*u), 1e-9)
        m["_cands"] = ancrer(chaines, P, m["_u"], tous=True)
    # vote : chaque marque prend, parmi ses bords acceptables à moins de 2 cm du meilleur, la chaîne
    # acceptable pour le plus de marques (une ligne physique portée par deux routes reste d'un seul tenant)
    pop = collections.Counter(c[1].cle for m in tous for c in m["_cands"])
    for m in tous:
        if not m["_cands"]:
            m["_anc"] = None
            continue
        dmin = min(c[0][0] for c in m["_cands"])
        proches = [c for c in m["_cands"] if c[0][0] <= dmin + 0.02]
        c = min(proches, key=lambda c: (-pop[c[1].cle], c[0]))
        m["_anc"] = (c[1], c[2], c[3])
    entites, devenir = [], {}
    mesures = {"lateral_gam": [], "phase_gam": [], "phase_tous": [], "par_entite": [], "phase_source": collections.Counter()}

    # ---- ancrées sur un bord de voie
    anc = [m for m in tous if m["_anc"]]
    groupes = collections.defaultdict(list)
    for m in anc:
        ch, t, _ = m["_anc"]
        tl = _tl(m)
        groupes[(ch.cle, tl, m["p"]["couleur"])].append(m)
    for (cle, tl, couleur), ms in sorted(groupes.items()):
        ch = ms[0]["_anc"][0]
        # grappes de t_off (lignes doubles) puis de code de modulation
        for g in _unions(ms, lambda a, b: abs(a["_anc"][1] - b["_anc"][1]) < 0.06 or _suite(a, b, ch)):
            for g2 in _unions(g, lambda a, b: _code_v1(a) == _code_v1(b)):
                for chaine in _chaines_s(g2, ch, tl):
                    for e in _entite_xodr(chaine, ch, tl, couleur, emprises_zebras, mesures):
                        entites.append(e)
                        for i in e["lien_v1"]:
                            devenir[i] = ("genere", e["id"], "ligne ancrée sur un bord de voie OpenDRIVE")

    # ---- hors réseau : axe propre
    libres = [m for m in tous if not m["_anc"]]

    def lie(a, b):
        if a["p"]["type"] != b["p"]["type"] or a["p"]["couleur"] != b["p"]["couleur"]:
            return False
        if a["p"]["groupe"] != b["p"]["groupe"] or _code_v1(a) != _code_v1(b):
            return False
        ga, gb = M.gam_refs(a["p"]), M.gam_refs(b["p"])
        if ga and gb and ga == gb:
            return True
        if ga and gb and a["p"]["type"] == "ligne_continue":
            return False
        if abs(a["_u"] @ b["_u"]) < math.cos(math.radians(4)):
            return False
        Pa, Pb = a["_axe"], b["_axe"]
        n = np.array([-a["_u"][1], a["_u"][0]])
        if abs((Pb.mean(axis=0) - Pa.mean(axis=0)) @ n) > 0.12:
            return False
        sa, sb = Pa @ a["_u"], Pb @ a["_u"]
        gap = max(sb.min() - sa.max(), sa.min() - sb.max())
        tl = _tl(a)
        if tl == "continue" and a["p"]["type"] == "ligne_discontinue":
            return gap < _ecart_max("discontinue", a["p"]["modulation"])
        return gap < _ecart_max(tl, _code_v1(a))
    for g in _unions(libres, lie):
        tl = _tl(g[0])
        for e in _entite_axe(g, tl, emprises_zebras, mesures):
            entites.append(e)
            for i in e["lien_v1"]:
                devenir[i] = ("genere", e["id"], "ligne sur axe propre (" + e["ancrage"]["source"] + ")")
    return entites, devenir, mesures


def _suite(a, b, ch):
    """Deux tirets v1 du même bord, décalés latéralement de moins de 0,20 m, qui se suivent le long de la route
    (recouvrement en s < 1 m, écart < une période) : même ligne (tirets du plan décalés au tracé) et non une ligne
    double ; sinon deux entités se chevaucheraient en baïonnette."""
    if a["p"]["type"] != "ligne_discontinue" or b["p"]["type"] != "ligne_discontinue" or _code_v1(a) != _code_v1(b):
        return False
    if abs(a["_anc"][1] - b["_anc"][1]) >= 0.20:
        return False
    sa = projeter(ch.xy, np.vstack([poly[0] for poly in a["polys"]]))[0]
    sb = projeter(ch.xy, np.vstack([poly[0] for poly in b["polys"]]))[0]
    rec = min(sa.max(), sb.max()) - max(sa.min(), sb.min())
    tp = _modele_v1(a)
    per = tp[1] if tp else 5.0
    return -per < rec < 1.0


def _tl(m):
    """Type de ligne : des tirets v1 synthétiques séparés de moins de 0,30 m (« tirets mesurés 2,96/0,20 ») ou portés
    par une paire de bords levés GAM continue sur plus de 6,5 m sont une ligne continue (le levé dessine chaque tiret
    d'une ligne discontinue ; des bords continus sont une bande peinte continue)."""
    if m["p"]["type"] == "ligne_continue":
        return "continue"
    tp = _modele_v1(m)
    if synthetique(m) and tp and tp[1] - tp[0] < 0.30:
        return "continue"
    G = M.gam_lin()
    pp = MG.paires()
    if synthetique(m) and any(k in pp and float(abscisses(G[k])[-1]) >= 6.5 for k in M.gam_refs(m["p"])):
        return "continue"            # bords levés continus sur plus d'un tiret : marque continue (tirets v1 synthétiques)
    return "discontinue"


def _code_v1(m):
    mod = m["p"]["modulation"]
    if _tl(m) == "continue" or mod in (None, "continue"):
        return "continue"
    src = m["p"]["source"]
    if "tirets mesurés" in src:
        return src[src.find("tirets mesurés"):].split(")")[0]
    return mod


def _modele_v1(m):
    """(trait, période) d'une modulation v1 « tirets mesurés a/b m » ou d'un code IISR, sinon None."""
    src = m["p"]["source"]
    if "tirets mesurés" in src:
        try:
            t, v = src[src.find("tirets mesurés") + len("tirets mesurés"):].split("m)")[0].strip().split("/")
            return float(t), float(t) + float(v)
        except ValueError:
            pass
    nom = modulations().get(m["p"]["modulation"])
    return (nom["trait_m"], nom["periode_m"]) if nom else None


def _chaines_s(ms, ch, tl):
    """Découpe les marques d'un même bord en chaînes continues le long de s."""
    for m in ms:
        pts = np.vstack([poly[0] for poly in m["polys"]])
        sig, _, _ = projeter(ch.xy, pts)
        m["_s"] = (float(ch.s_de_sig(sig.min())), float(ch.s_de_sig(sig.max())))
    ms = sorted(ms, key=lambda m: (m["_s"][0], m["id"]))
    gmax = _ecart_max(tl, _code_v1(ms[0]))
    if tl == "continue" and ms[0]["p"]["type"] == "ligne_discontinue":
        gmax = _ecart_max("discontinue", ms[0]["p"]["modulation"])      # tirets synthétiques devenus ligne continue
    out, cur = [], [ms[0]]
    for m in ms[1:]:
        if m["_s"][0] - max(x["_s"][1] for x in cur) > gmax:
            out.append(cur)
            cur = [m]
        else:
            cur.append(m)
    out.append(cur)
    return out


def _gam_axe(refs, pts):
    """Axe GAM d'un groupe de marques : axes levés (médiane des paires de bords, sinon ligne) chaînés quand leurs
    extrémités se touchent (< 0,5 m), puis la chaîne la plus proche des points. -> (axe, écartement de paire ou None)."""
    axes = MG.axes_leves(refs)
    chaines = []
    for P, e, ks in axes:
        place = False
        for ch in chaines:
            for Q, ou in ((P, "fin"), (P[::-1], "fin"), (P, "debut"), (P[::-1], "debut")):
                d = np.hypot(*((Q[0] - ch[0][-1][-1]) if ou == "fin" else (Q[-1] - ch[0][0][0])))
                if d < 0.5:
                    ch[0].insert(len(ch[0]) if ou == "fin" else 0, Q)
                    ch[1].append(e)
                    place = True
                    break
            if place:
                break
        if not place:
            chaines.append(([P], [e]))
    cands = [(M.dedoublonner(np.vstack(c)), [x for x in es if x is not None]) for c, es in chaines]
    C, es = min(cands, key=lambda c: (round(float(np.median(projeter(c[0], pts)[1])), 3), -len(c[0])))
    return C, (float(np.median(es)) if es else None)


def _peint(e, L):
    """Parties peintes (σ0, σ1) d'une entité ligne de longueur L."""
    if e["type"] == "discontinue":
        return MO.pieces(e, L)
    iv = [(0.0, L)]
    for a0, b0 in e.get("interruptions", []):
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
    return iv


REF_ETRANGERE = 0.10         # axe levé GAM référencé à plus de 0,10 m (médiane) de la ligne : autre marque


def refs_etrangeres(axe, refs):
    """Lignes GAM référencées par les MQ d'une ligne dont l'axe levé est à plus de REF_ETRANGERE (médiane) de l'axe de
    la ligne : une autre marque (hachures, tirets voisins) -> [indices GAM]."""
    out = []
    for G, _, ks in MG.axes_leves(refs):
        Q, _ = densifier(G, 0.10)
        s, d, _ = projeter(axe, Q)
        L = float(abscisses(axe)[-1])
        ok = (s > 0.05) & (s < L - 0.05)
        if ok.sum() >= 3 and float(np.median(d[ok])) > REF_ETRANGERE:
            out += list(ks)
    return sorted(out)


def _metriques(e, axe, ms, mesures):
    """Écart latéral au levé GAM : axes levés des polylignes référencées (médiane des paires de bords), au pas
    0,10 m, distance à l'axe final sur ses parties peintes (projection intérieure, < 0,5 m) ; les lignes GAM d'une
    autre marque (refs_etrangeres) sont écartées et notées (gam_refs_exclues)."""
    refs = sorted({i for m in ms for i in M.gam_refs(m["p"])})
    if not refs:
        return
    exclues = refs_etrangeres(axe, refs)
    if exclues:
        e["gam_refs_exclues"] = exclues
        refs = [k for k in refs if k not in exclues]
        if not refs:
            return
    L = float(abscisses(axe)[-1])
    iv = _peint(e, L)
    lat = []
    for G, _, _ in MG.axes_leves(refs):
        Q, _ = densifier(G, 0.10)
        s, d, _ = projeter(axe, Q)
        ok = (s > 0.05) & (s < L - 0.05) & (d < 0.5)
        ok &= np.array([any(a <= x <= b for a, b in iv) for x in s], bool) if len(iv) else False
        lat.append(d[ok])
    lat = np.concatenate(lat) if lat else np.zeros(0)
    if len(lat):
        e["mesures"]["lateral_gam_p50_m"] = round(float(np.median(lat)), 4)
        e["mesures"]["lateral_gam_p95_m"] = round(float(np.percentile(lat, 95)), 4)
        e["mesures"]["lateral_gam_max_m"] = round(float(lat.max()), 4)
        mesures["lateral_gam"].append((e["id"], e["ancrage"]["type"], lat))


def _base(ms, tl):
    return {"classe": "ligne", "type": tl, "couleur": ms[0]["p"]["couleur"],
            "usure": _usure(ms), "couverture": M.mediane_ou([m["p"]["couverture"] for m in ms]),
            "etat": _maj(ms, "etat"), "groupe": _maj(ms, "groupe"), "branche": _maj(ms, "branche"),
            "lien_v1": sorted(m["id"] for m in ms)}


def _modele(a, b, code, T_P=None):
    """Modèle (IISR, sinon mesuré) d'une suite de tirets observés ; repli : modulation imposée T_P."""
    fit = ajuster(a, b, code)
    if fit is None and T_P:
        T, P = T_P
        phi = _phase(a, b, T, P)
        fit = dict(_source_modulation(code, T, P), T=T, P=P, phi=phi, r=_residus(a, b, T, P, phi)[3])
    return fit


def _source_modulation(code, T, P):
    """{src, code} : IISR seulement si (trait, période) sont ceux de la table pour ce code (± 1 cm) ; sinon mesurée,
    code « <code proche>_site » (ou « mesuree »)."""
    nom = modulations().get(code)
    if nom and abs(T - nom["trait_m"]) <= 0.01 and abs(P - nom["periode_m"]) <= 0.01:
        return {"src": "IISR", "code": code}
    proche = _code_proche(T, P) or (code if code in modulations() else None)
    return {"src": "mesuree", "code": f"{proche}_site" if proche else "mesuree"}


def _segments(sa, sb, kinds, code, T_P):
    """Segments réguliers [(indices, modèle, source)] d'une chaîne de tirets : preuves de phase = tirets levés GAM
    s'il y en a, sinon tirets v1 observés ; les tirets v1 synthétiques ne servent qu'à l'étendue."""
    kinds = np.asarray(kinds)
    for src in ("gam", "v1"):
        idx = np.where(kinds == src)[0]
        if len(idx):
            break
    else:
        idx = np.where(kinds == "synth")[0]
        src = "synth"
        if T_P is None:
            T_P = (float(np.median(sb[idx] - sa[idx])), float(np.median(sb[idx] - sa[idx])) * 2)
        T, P = T_P
        phi = _phase(sa[idx], sb[idx], T, P)
        fit = dict(_source_modulation(code, T, P), T=T, P=P, phi=phi, r=_residus(sa[idx], sb[idx], T, P, phi)[3])
        return [(list(range(len(sa))), fit, src)]
    o = idx[np.argsort(sa[idx], kind="stable")]
    out = []
    tab = modulations()
    for i0, i1, fit in segmenter(sa[o], sb[o], code):
        if fit is None:
            fit = _modele(sa[o[i0:i1 + 1]], sb[o[i0:i1 + 1]], code, T_P)
        if src == "v1" and fit is not None and fit["src"] == "mesuree" and i1 - i0 + 1 <= 2 and code in tab:
            # deux tirets v1 (plan, ortho) ne mesurent pas une période : modulation IISR du code v1, phase ajustée sur eux
            T, P = tab[code]["trait_m"], tab[code]["periode_m"]
            a_, b_ = sa[o[i0:i1 + 1]], sb[o[i0:i1 + 1]]
            phi = _phase(a_, b_, T, P)
            fit = {"src": "IISR", "code": code, "T": T, "P": P, "phi": phi, "r": _residus(a_, b_, T, P, phi)[3]}
        out.append(([int(k) for k in o[i0:i1 + 1]], fit, src))
    # rattachement des autres observations (v1 hors preuve) au segment le plus proche
    autres = [k for k in range(len(sa)) if k not in set(i for s, _, _ in out for i in s)]
    for k in autres:
        c = 0.5 * (sa[k] + sb[k])
        j = min(range(len(out)), key=lambda j: (max(0.0, min(sa[i] for i in out[j][0]) - c, c - max(sb[i] for i in out[j][0])), j))
        out[j][0].append(k)
    return out


def _rephaser_ortho(e, axe, seuil=None):
    """Phase recalée sur l'ortho 2022 (modulation gardée) : corrélation luminance / motif, pic ≥ MO.PIC_RECALAGE (ou
    `seuil`) ; renvoie la preuve (avec le décalage « _delta ») ou None."""
    r = MO.phase_ortho(axe, e)
    seuil = MO.PIC_RECALAGE if seuil is None else seuil
    if r is None or r["corr_max"] < seuil:
        return None
    return {"src": "ortho2022", "ref": f"corrélation luminance PCRS 5 cm 2022 / motif : {r['corr_max']:.2f} (avant {r['corr_v2']:.2f}), "
                                      f"décalage {r['delta_m']:+.2f} m", "conf": "haute" if r["corr_max"] >= 0.6 else "moyenne", "_delta": r["delta_m"]}


def _calage_gam(e, axe, etendue=None, ecart_max=0.30):
    """Décalage médian (≤ ecart_max) entre les milieux des lignes GAM ouvertes courtes (0,3-6,5 m, droites, à moins de
    0,10 m de l'axe en médiane, chaînées ou non) et les milieux des tirets (dans `etendue` σ) qu'elles recouvrent à plus de moitié :
    (δ, [k]) ou None."""
    G = M.gam_lin()
    L = float(abscisses(axe)[-1])
    ea, eb = etendue or (0.0, L)
    iv = [(max(x, ea), min(y, eb)) for x, y in MO.pieces(dict(e, interruptions=[]), L) if y > ea and x < eb]
    lo, hi = axe.min(axis=0) - 7.0, axe.max(axis=0) + 7.0
    ds, ks = [], []
    for k, g in enumerate(G):
        if not MG.ouverte(g) or g[:, 0].max() < lo[0] or g[:, 0].min() > hi[0] or g[:, 1].max() < lo[1] or g[:, 1].min() > hi[1]:
            continue
        Lg = float(abscisses(g)[-1])
        if not (0.3 <= Lg <= 6.5) or float(np.hypot(*(g[-1] - g[0]))) < 0.97 * Lg:
            continue
        sg, dg, _ = projeter(axe, g)
        if dg.max() > 0.40 or float(np.median(dg)) > REF_ETRANGERE:
            continue                 # au-delà : tiret d'une autre marque (hachures voisines, ligne parallèle)
        a, b = float(sg.min()), float(sg.max())
        if a < -0.3 or b > L + 0.3:
            continue
        best = max(iv, key=lambda x: min(x[1], b) - max(x[0], a)) if iv else None
        if best is None or min(best[1], b) - max(best[0], a) < 0.5 * (b - a):
            continue
        d = 0.5 * (a + b) - 0.5 * (best[0] + best[1])
        if abs(d) <= ecart_max:
            ds.append(d)
            ks.append(k)
    if not ds:
        return None
    d = float(np.median(ds))
    return (d, ks) if abs(d) > 0.005 else None


def _fusion_iv(iv):
    out = []
    for a, b in sorted([list(x) for x in iv]):
        if out and a <= out[-1][1] + 1e-6:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


def _bouts(e, L):
    """Interruptions de bout : tiret partiel au début ou à la fin de l'axe visible sur moins de PARTIEL_MIN du trait."""
    T, per, ph = e["trait_m"], e["trait_m"] + e["vide_m"], e["phase_m"]
    out = []
    a = ph - per * math.ceil(ph / per)              # début du tiret qui précède ou contient σ = 0
    if a < 0 < a + T and (a + T) < PARTIEL_MIN * T - 1e-6:
        out.append([0.0, round(a + T, 3)])
    k = math.floor((L - ph) / per)
    a = ph + k * per                                 # dernier tiret commencé avant L
    if a < L < a + T and (L - a) < PARTIEL_MIN * T - 1e-6:
        out.append([round(a, 3), round(L, 3)])
    if out and not any(y - x >= PARTIEL_MIN * T - 1e-6 for x, y in MO.pieces(dict(e, interruptions=out), L)):
        return []                                    # jamais toute la ligne : le tiret observé reste peint
    return out


def _rogner(e, L):
    """[σa, σb] : l'axe commence au début du premier tiret et finit à la fin du dernier ; un tiret partiel de
    bout n'est gardé que s'il fait au moins PARTIEL_MIN du trait."""
    T, per, ph = e["trait_m"], e["trait_m"] + e["vide_m"], e["phase_m"]
    k = math.floor(-ph / per) - 1
    deb = None
    while ph + k * per < L:
        a, b = ph + k * per, ph + k * per + T
        vis = min(b, L) - max(a, 0.0)
        if vis >= PARTIEL_MIN * T - 1e-6:
            deb = max(a, 0.0)
            break
        k += 1
    if deb is None:
        return None
    k = math.floor((L - ph) / per) + 1
    fin = None
    while ph + k * per + T > deb:
        a, b = ph + k * per, ph + k * per + T
        vis = min(b, L) - max(a, 0.0)
        if vis >= PARTIEL_MIN * T - 1e-6:
            fin = min(b, L)
            break
        k -= 1
    if fin is None or fin - deb < 0.5 * T:
        return None
    return deb, fin


def _construire(ms, tl, axe_complet, faire_axe, ancrage_fn, prov_geo, emprises_zebras, mesures, ctx):
    """Entités d'une chaîne de marques sur un axe : continue -> une entité ; discontinue -> une entité par segment
    régulier (phase propre, preuves ordonnées : tirets GAM > ortho 2022 > tirets v1). ctx : chaine (bord xodr ou
    None), s_de (σ -> s de route ou None), paire (écartement des bords levés ou None)."""
    iv = _intervalles(axe_complet, ms)
    o = np.argsort([x[0] for x in iv], kind="stable")
    ms = [ms[i] for i in o]
    a = np.array([iv[i][0] for i in o])
    b = np.array([iv[i][1] for i in o])
    code = ms[0]["p"]["modulation"] if ms[0]["p"]["modulation"] in modulations() else None
    Lc = float(abscisses(axe_complet)[-1])
    out = []
    if tl == "continue":
        morceaux = [(list(range(len(ms))), None, None, [], float(a.min()), float(b.max()))]
        refs = {k for m in ms for k in M.gam_refs(m["p"])}
        if refs:
            libres = LIBRES_GAM()
            G_ = M.gam_lin()
            ext = []
            for A_, _, ks in MG.axes_leves(sorted(MG.chaine(refs, libres) - refs)):
                sg, dg, _ = projeter(axe_complet, A_)
                if float(np.median(dg)) < 0.06 and not set(ks) & refs:
                    ext.append((float(sg.min()), float(sg.max()), ks))
            if ext:
                lo_, hi_ = min([a.min()] + [x[0] for x in ext]), max([b.max()] + [x[1] for x in ext])
                morceaux = [(list(range(len(ms))), None, None, [], float(lo_), float(hi_))]
                ctx = dict(ctx, chaine_gam=sorted(k for x in ext for k in x[2]))
    else:
        T_P = _modele_v1(ms[0])
        per = T_P[1] if T_P else 5.0
        G_ = M.gam_lin()
        propres = {k for m in ms if synthetique(m) for k in M.gam_refs(m["p"])
                   if MG.ouverte(G_[k]) and float(abscisses(G_[k])[-1]) <= 6.5}
        gd = [x for x in MG.tirets_leves(axe_complet, inclure=propres) if x[1] > a.min() - per - 1.0 and x[0] < b.max() + per + 1.0]
        kinds = ["synth" if synthetique(m) else "v1" for m in ms]
        sa, sb = list(a), list(b)
        for x in gd:
            sa.append(x[0])
            sb.append(x[1])
            kinds.append("gam")
        sa, sb = np.array(sa), np.array(sb)
        morceaux = []
        for idx, fit, src in _segments(sa, sb, kinds, code, T_P):
            mi = sorted(i for i in idx if i < len(ms))
            morceaux.append((mi, fit, src, [gd[i - len(ms)] for i in idx if i >= len(ms)], sa[idx].min(), sb[idx].max()))
        # marques v1 sans segment (aucune preuve à leur hauteur) : segment le plus proche
        pris = {i for mm in morceaux for i in mm[0]}
        for i in range(len(ms)):
            if i not in pris:
                c = 0.5 * (a[i] + b[i])
                j = min(range(len(morceaux)), key=lambda j: (max(0.0, morceaux[j][4] - c, c - morceaux[j][5]), j))
                morceaux[j][0].append(i)
        morceaux = [(sorted(mm[0]), mm[1], mm[2], mm[3], mm[4], mm[5]) for mm in morceaux if mm[0]]
    for mm in morceaux:
        mi, fit, src, gds = mm[:4]
        sm = [ms[i] for i in mi]
        s0 = float(min([a[i] for i in mi] + [mm[4]]))
        s1 = float(max([b[i] for i in mi] + [mm[5]]))
        s0, s1 = max(0.0, s0), min(Lc, s1)
        e = _base(sm, tl)
        e["id"] = M.ident("ML", e["lien_v1"])
        e["prov"] = dict(prov_geo)
        e["mesures"] = {}
        if tl == "discontinue":
            T, P = fit["T"], fit["P"]
            e.update({"modulation": fit["code"], "trait_m": round(T, 3), "vide_m": round(P - T, 3),
                      "phase_m": round((fit["phi"] - s0) % P, 3), "modulation_source": fit["src"],
                      "modulation_v1": sm[0]["p"]["modulation"]})
            e["prov"]["modulation"] = ({"src": "norme:IISR_7_art113-1", "ref": f"{e['modulation']} {e['trait_m']}/{e['vide_m']}", "conf": "haute"}
                                       if fit["src"] == "IISR" else
                                       {"src": "gam" if src == "gam" else _src_mesure(sm),
                                        "ref": f"modulation mesurée (hors table IISR) sur les tirets {'levés GAM' if src == 'gam' else 'v1 ' + _mesure_v1(sm)} : "
                                               f"trait {e['trait_m']}, vide {e['vide_m']}, période {round(P, 3)}",
                                        "conf": "moyenne" if len(fit["r"]) > 1 else "faible"})
            axe0 = faire_axe(s0, s1)
            L0 = float(abscisses(axe0)[-1])
            if src == "gam":
                e["prov"]["phase_m"] = {"src": "gam", "ref": f"moindres carrés sur {len(gds)} tiret(s) levé(s) GAM " + ",".join(str(k) for g in gds for k in g[3]), "conf": "haute"}
                ra, rb, kk, r, partiel = _residus(np.array([g[0] for g in gds]) - s0, np.array([g[1] for g in gds]) - s0, T, P, e["phase_m"])
                fiab = np.r_[np.abs(ra[~partiel]), np.abs(rb[~partiel]), np.minimum(np.abs(ra), np.abs(rb))[partiel]]
                mesures["phase_gam"].append((len(gds), fiab))
            else:
                e["interruptions"] = sorted([round(z0, 3), round(z1, 3)] for _, poly in emprises_zebras
                                            for z0, z1 in couper_polyligne(axe0, [poly]))
                if e["etat"] in MO.ETATS_2022:
                    rp = _rephaser_ortho(e, axe0)
                else:
                    # ligne repeinte en 2025 : le plan projet ne cote pas la phase ; si l'ortho montre nettement les tirets
                    # 2022 au même endroit (repeints par-dessus), la phase est prise sur eux
                    rp = _rephaser_ortho(e, axe0, seuil=0.5)
                    if rp:
                        rp["ref"] += " ; ligne repeinte en 2025 sur les tirets 2022 (le plan ne cote pas la phase)"
                if rp:
                    # le motif glisse avec son étendue (tirets v1 mal placés) : extension bornée à l'axe complet
                    d = rp.pop("_delta")
                    a2, b2 = max(0.0, s0 + d), min(Lc, s1 + d)
                    e["phase_m"] = round((e["phase_m"] + (s0 + d) - a2) % (e["trait_m"] + e["vide_m"]), 3)
                    s0, s1 = a2, b2
                    axe0 = faire_axe(s0, s1)
                    L0 = float(abscisses(axe0)[-1])
                    e["prov"]["phase_m"] = rp
                    src = "ortho"
                elif src == "synth":
                    e["prov"]["phase_m"] = {"src": "a_priori:tirets_v1_synthetiques", "ref": f"tirets v1 synthétiques ({len(sm)}, {sm[0]['p']['source'][:60]}) : phase non vérifiable (ortho sans pic net ou état 2025)", "conf": "faible"}
                else:
                    e["prov"]["phase_m"] = {"src": _src_v1(sm), "ref": f"moindres carrés sur {len(sm)} tiret(s) v1 observé(s)", "conf": "moyenne"}
            mesures["phase_source"][src] += 1
            # axe rogné aux tirets (partiel de bout ≥ PARTIEL_MIN), sauf phase prise sur l'ortho : la fenêtre de corrélation
            # reste l'étendue observée (sinon l'optimum dépend du rognage) et les tirets de bout trop courts sont des
            # interruptions de bout ; phase revérifiée sur la fenêtre finale
            per = e["trait_m"] + e["vide_m"]
            seuil = MO.PIC_RECALAGE if e["etat"] in MO.ETATS_2022 else 0.5
            rg = None
            if src != "ortho":
                rg = _rogner(e, L0)
                if rg is None:
                    # aucun tiret visible à moitié dans l'étendue observée : étendue gardée telle quelle
                    rg = (0.0, L0)
                    e["note"] = "étendue observée gardée (aucun tiret entier du modèle à l'intérieur)"
                s0, s1 = s0 + rg[0], s0 + rg[1]
                e["phase_m"] = round((e["phase_m"] - rg[0]) % per, 3)
                axe0 = faire_axe(s0, s1)
                L0 = float(abscisses(axe0)[-1])
            if src != "gam":
                zeb0 = sorted([round(z0, 3), round(z1, 3)] for _, poly in emprises_zebras for z0, z1 in couper_polyligne(axe0, [poly]))
                for _ in range(3):
                    e1 = dict(e, interruptions=_fusion_iv(zeb0 + (_bouts(e, L0) if src == "ortho" else [])))
                    r1 = MO.phase_ortho(axe0, e1)
                    if r1 is None or r1["corr_max"] < seuil or abs(r1["delta_m"]) <= 0.015:
                        break
                    e["phase_m"] = round((e["phase_m"] + r1["delta_m"]) % per, 3)
                    if src != "ortho":
                        mesures["phase_source"][src] -= 1
                        mesures["phase_source"]["ortho"] += 1
                        src = "ortho"
                        e["prov"]["phase_m"] = {"src": "ortho2022", "conf": "haute" if r1["corr_max"] >= 0.6 else "moyenne",
                                                "ref": f"corrélation luminance PCRS 5 cm 2022 / motif : {r1['corr_max']:.2f} "
                                                       f"(avant {r1['corr_v2']:.2f}), décalage {r1['delta_m']:+.2f} m"}
            if e["phase_m"] > per - 2e-3:
                e["phase_m"] = 0.0
            if src == "ortho":
                e["_bouts"] = True
            if src != "gam":
                # ajustement fin sur les lignes GAM courtes qui recouvrent un tiret (morceaux de polyligne compris) ;
                # le motif glisse avec son étendue
                se0, se1 = max(0.0, s0 - 1.0), min(Lc, s1 + 1.0)
                d_ = _calage_gam(dict(e, phase_m=(e["phase_m"] + s0 - se0) % per), faire_axe(se0, se1), (s0 - se0, s1 - se0))
                if d_ is not None:
                    a2, b2 = max(0.0, s0 + d_[0]), min(Lc, s1 + d_[0])
                    e["phase_m"] = round((e["phase_m"] + (s0 + d_[0]) - a2) % per, 3)
                    s0, s1 = a2, b2
                    e["prov"]["phase_m"] = dict(e["prov"]["phase_m"], ref=e["prov"]["phase_m"]["ref"]
                                                + f" ; calée de {d_[0]:+.3f} m sur les lignes GAM {','.join(map(str, d_[1]))} qui recouvrent les tirets")
        e["ancrage"] = ancrage_fn(s0, s1)
        if ctx.get("chaine_gam"):
            e["prolongements_gam"] = [[k] for k in ctx["chaine_gam"]]
            e["prov"]["geometrie"] = dict(e["prov"]["geometrie"], ref=e["prov"]["geometrie"]["ref"]
                                          + f" ; étendue à la marque levée jointive (lignes GAM {','.join(map(str, ctx['chaine_gam']))}, non rattachées au v1)")
        axe = faire_axe(s0, s1)
        e["geom"] = ("LineString", M.douglas_peucker(axe, 0.001))
        L = float(abscisses(axe)[-1])
        e["longueur_m"] = round(L, 3)
        if tl == "discontinue":
            e["n_tirets"] = sum(1 for x, y in MO.pieces(dict(e, interruptions=[]), L) if y - x >= e["trait_m"] - 1e-3)
            e["mesures"].update({"n_tirets_v1": len(sm), "n_tirets_gam": len(gds),
                                 "tirets_partiels_v1": int(sum(1 for i in mi if b[i] - a[i] < PARTIEL * e["trait_m"])),
                                 "residu_phase_max_m": round(float(np.max(fit["r"])), 3) if len(fit["r"]) else None})
        else:
            e["modulation"] = "continue"
        inter = []
        for zid, poly in emprises_zebras:
            for z0, z1 in couper_polyligne(axe, [poly]):
                inter.append((round(z0, 3), round(z1, 3), zid))
        e["interruptions"] = [[x[0], x[1]] for x in sorted(inter)]
        if inter:
            e["interruptions_zebras"] = sorted({x[2] for x in inter})
        if e.pop("_bouts", False):
            bouts = _bouts(e, L)
            if bouts:
                e["interruptions_bouts"] = bouts
                e["interruptions"] = _fusion_iv(e["interruptions"] + bouts)
        s_mid = ctx["s_de"](0.5 * (s0 + s1)) if ctx.get("s_de") else None
        role = role_ligne(sm, tl, e.get("modulation"), ctx.get("chaine"), s_mid)
        w, pw = largeur(sm, tl, e["branche"], role, ctx.get("paire"))
        if pw["src"] == "regle:marquages_geometrie.cycles":
            role = ("rive_piste", "piste cyclable (Chronovélo) : rive de piste 3u, u = 0,03")
        w, pw = harmoniser_t3(e, role, w, pw)
        e["largeur_m"] = w
        e["role"] = role[0]
        e["prov"]["largeur_m"] = pw
        _metriques(e, axe, sm, mesures)
        out.append(e)
    return out


def _src_mesure(ms):
    """Source d'une mesure de modulation sur des tirets v1 : « tirets mesurés » de l'ortho 2022 (tirets v1 synthétiques)."""
    s = ms[0]["p"]["source"]
    return "ortho2022" if "tirets mesurés" in s or "ortho" in s else _src_v1(ms)


def _mesure_v1(ms):
    s = ms[0]["p"]["source"]
    return f"({s[s.find('tirets mesurés'):].split(')')[0]})" if "tirets mesurés" in s else f"({_src_v1(ms)})"


def _src_v1(ms):
    s = ms[0]["p"]["source"]
    return "gam" if s.startswith("GAM") else ("plan2025" if s.startswith("plan") else "ortho2022")


def _entite_xodr(ms, ch, tl, couleur, emprises_zebras, mesures):
    marge = 35.0 if tl == "continue" else 7.0
    s_lo = max(min(m["_s"][0] for m in ms) - marge, float(ch.s[0]))
    s_hi = min(max(m["_s"][1] for m in ms) + marge, float(ch.s[-1]))
    t_off, src_t, paire = _t_off(ms, ch)
    axe_c, ss = ch.axe(t_off, s_lo, s_hi, avec_s=True)
    ecart = _ecart_gam(axe_c, ms)
    if ecart is not None and ecart > TOL_LAT_GAM and all(M.gam_refs(m["p"]) for m in ms):
        # le bord OpenDRIVE s'écarte du levé le long de la ligne : ancrage sur l'axe GAM
        es = _entite_axe(ms, tl, emprises_zebras, mesures)
        for e in es:
            e["prov"]["ancrage"] = {"src": "gam", "ref": f"bord xodr {ch.cle} écarté : p95 {ecart:.3f} m > {TOL_LAT_GAM} m du levé", "conf": "haute"}
        return es
    if src_t == "marques v1" and tl == "discontinue":
        # tirets levés GAM sans rattachement v1 le long de la ligne : décalage latéral pris sur eux
        sig_c = abscisses(axe_c)
        lo = float(np.interp(min(m["_s"][0] for m in ms), ss, sig_c)) - 1.0
        hi = float(np.interp(max(m["_s"][1] for m in ms), ss, sig_c)) + 1.0
        gd = [g for g in MG.tirets_leves(axe_c) if g[1] > lo and g[0] < hi]
        if gd:
            dt = float(np.median([g[2] for g in gd]))
            if abs(dt) > 0.01:
                t_off += dt
                src_t = f"tirets levés GAM {','.join(str(k) for g in gd for k in g[3])}"
                axe_c, ss = ch.axe(t_off, s_lo, s_hi, avec_s=True)
    t_off = round(t_off, 4)
    prof = _profil_gam(ch, t_off, axe_c, ss, ms)
    if prof:
        axe_c, ss = ch.axe(t_off, s_lo, s_hi, avec_s=True, profil=prof)
        src_t += f" ; écart au levé GAM suivi par un profil t(s) lissé ({len(prof)} nœuds)"
    sig_c = abscisses(axe_c)

    def s_de(x):
        return float(np.interp(x, sig_c, ss))

    def faire_axe(a, b):
        return ch.axe(t_off, s_de(a), s_de(b), profil=prof)

    def anc(a, b):
        out = {"type": "xodr", "route": ch.route, "bords": ch.troncons(s_de(a), s_de(b)),
               "s0": round(s_de(a), 3), "s1": round(s_de(b), 3), "t_off_m": t_off}
        if prof:
            out["t_off_profil"] = prof
        return out
    prov = {"geometrie": {"src": "xodr", "ref": f"bord {ch.cle} + t_off médian ({src_t})", "conf": "haute"},
            "ancrage": {"src": "xodr", "ref": "paquet_jardin_2026.xodr", "conf": "haute"}}
    return _construire(ms, tl, axe_c, faire_axe, anc, prov, emprises_zebras, mesures,
                       {"chaine": ch, "s_de": s_de, "paire": paire})


PROFIL_SEUIL = 0.03          # écart p95 au levé GAM au-delà duquel t_off suit un profil t(s)
PROFIL_PAS = 4.0             # pas des nœuds du profil (m de route)


def _profil_gam(ch, t_off, axe_c, ss, ms):
    """Profil t(s) [[s, δt], ...] (nœuds au pas PROFIL_PAS sur l'étendue levée, moindres carrés lissés, δt borné à
    ± 0,15 m) quand l'axe bord + t_off s'écarte de plus de PROFIL_SEUIL (p95) des axes levés GAM des marques ; sinon None."""
    return profil_refs(sorted({i for m in ms for i in M.gam_refs(m["p"])}), axe_c, ss)


def profil_refs(refs, axe_c, ss):
    """Profil t(s) (voir _profil_gam) contre les axes levés des lignes GAM `refs` ; axe_c : axe courant, ss : s de route
    de ses sommets."""
    if not refs:
        return None
    sig_c = abscisses(axe_c)
    sv, rv = [], []
    for G, _, ks in MG.axes_leves(refs):
        Q, _ = densifier(G, 0.10)
        sg, d, cote = projeter(axe_c, Q)
        if float(np.median(d)) > REF_ETRANGERE:
            continue
        ok = (sg > 0.05) & (sg < sig_c[-1] - 0.05) & (d < 0.30)
        sv.append(np.interp(sg[ok], sig_c, ss))
        rv.append((cote * d)[ok])
    if not sv:
        return None
    s_, r_ = np.concatenate(sv), np.concatenate(rv)
    if len(s_) < 20 or float(np.percentile(np.abs(r_), 95)) <= PROFIL_SEUIL:
        return None
    a, b = float(s_.min()), float(s_.max())
    n = max(2, int(math.ceil((b - a) / PROFIL_PAS)) + 1)
    kn = np.linspace(a, b, n)
    # base des chapeaux (interpolation linéaire entre nœuds)
    Bm = np.zeros((len(s_), n))
    j = np.clip(np.searchsorted(kn, s_, side="right") - 1, 0, n - 2)
    t = (s_ - kn[j]) / np.maximum(kn[j + 1] - kn[j], 1e-9)
    Bm[np.arange(len(s_)), j] = 1 - t
    Bm[np.arange(len(s_)), j + 1] = t
    lam = 2.0
    D = np.zeros((max(0, n - 2), n))
    for k in range(n - 2):
        D[k, k:k + 3] = [1, -2, 1]
    A = np.vstack([Bm, math.sqrt(lam * len(s_) / max(n, 1)) * 0.1 * D])
    y = np.r_[r_, np.zeros(len(D))]
    c, *_ = np.linalg.lstsq(A, y, rcond=None)
    c = np.clip(c, -0.15, 0.15)
    res = r_ - Bm @ c
    if float(np.percentile(np.abs(res), 95)) >= float(np.percentile(np.abs(r_), 95)) - 0.005:
        return None
    return [[round(float(x), 3), round(float(v), 4)] for x, v in zip(kn, c)]


def _ecart_gam(axe, ms):
    """p95 de l'écart d'un axe aux axes levés GAM (médiane des paires) des marques, sur leur étendue."""
    refs = sorted({i for m in ms for i in M.gam_refs(m["p"])})
    if not refs:
        return None
    pts = np.vstack([m["_axe"] for m in ms])
    s, _, _ = projeter(axe, pts)
    Q, _ = densifier(_sous(axe, s.min(), s.max()), 0.10)
    dmin = np.full(len(Q), np.inf)
    for G, _, _ in MG.axes_leves(refs):
        sg, d, _ = projeter(G, Q)
        dmin = np.where((sg > 0.05) & (sg < abscisses(G)[-1] - 0.05), np.minimum(dmin, d), dmin)
    dmin = dmin[np.isfinite(dmin) & (dmin < 0.5)]
    return float(np.percentile(dmin, 95)) if len(dmin) else None


def _t_off(ms, ch):
    """Décalage latéral médian au bord : axe levé GAM (médiane d'une paire de bords, sinon la ligne référencée la
    plus proche de chaque marque, sur l'étendue de la marque) quand il existe, sinon axes des polygones v1.
    -> (t_off, source, écartement de paire ou None)."""
    vals, paires = [], []
    for m in ms:
        refs = M.gam_refs(m["p"])
        if not refs:
            continue
        G, e, _ = min(MG.axes_leves(refs), key=lambda c: float(np.median(projeter(c[0], m["_axe"])[1])))
        sg, d, _ = projeter(G, m["_axe"])
        if np.median(d) > 0.4:
            continue
        if e is not None:
            paires.append(e)
        Q, _ = densifier(_sous(G, sg.min(), sg.max()), 0.25)
        sig, dd, cote = projeter(ch.xy, Q)
        ok = (sig > 0.02) & (sig < ch.sig[-1] - 0.02) & (dd < TOL_LAT + 0.2)
        vals.append((cote * dd)[ok])
    vals = np.concatenate(vals) if vals else np.array([])
    paire = float(np.median(paires)) if paires else None
    if len(vals) >= 3:
        return float(np.median(vals)), "levé GAM" + (" (médiane des bords)" if paire else ""), paire
    sig, d, cote = projeter(ch.xy, densifier_pts(ms))
    return float(np.median(cote * d)), "marques v1", None


def densifier_pts(ms):
    return np.vstack([densifier(m["_axe"], 0.25)[0] for m in ms])


def _entite_axe(ms, tl, emprises_zebras, mesures):
    refs = sorted({i for m in ms for i in M.gam_refs(m["p"])})
    pts = np.vstack([poly[0] for m in ms for poly in m["polys"]])
    G, paire = _gam_axe(refs, densifier_pts(ms)) if refs and all(M.gam_refs(m["p"]) for m in ms) else (None, None)
    couvre = False
    if G is not None:
        s, d, _ = projeter(G, pts)
        s = s[d <= 0.5] if np.any(d <= 0.5) else s
        sm = np.array([np.median(projeter(G, m["_axe"])[0]) for m in ms])
        couvre = bool(np.percentile(d, 90) < 0.45 and np.all((sm > 0.0) & (sm < abscisses(G)[-1])))
    if couvre:
        axe_c = _sous(G, max(0.0, s.min() - 7.0), min(abscisses(G)[-1], s.max() + 7.0))
        source = "gam"
        prov = {"geometrie": {"src": "gam", "ref": "axe levé GAM " + ",".join(map(str, refs)) + (" (médiane des bords)" if paire else ""), "conf": "haute"}}
    elif G is not None:
        axe_c = _axe_tirets_gam(ms, prolonge=1.0)
        source = "gam"
        prov = {"geometrie": {"src": "gam", "ref": "axes levés GAM des tirets " + ",".join(map(str, refs)) + " mis bout à bout", "conf": "haute"}}
    else:
        axe_c = _axe_ajuste(ms, prolonge=1.0)
        source = "v1"
        prov = {"geometrie": {"src": _src_v1(ms), "ref": f"axe ajusté sur {len(ms)} polygone(s) v1", "conf": "moyenne"}}
    # lignes de guidage du carrefour : le levé GAM brise une courbe en segments ; congé jusqu'à 10 cm du sommet levé
    em = 0.03                        # congé à moins de 3 cm du sommet levé (revue du 10/10 : 10 cm sur le guidage, trop loin)
    lisse = GL.adoucir(axe_c, ecart_max=em)
    if len(lisse) != len(axe_c) or not np.allclose(lisse, axe_c):
        prov["geometrie"]["ref"] += f" ; sommets anguleux (> 10°) raccordés par des congés (R ≤ 6 m, à moins de {em * 100:.0f} cm du levé)"
        axe_c = lisse
    return _construire(ms, tl, axe_c, lambda a, b: _sous(axe_c, a, b), lambda a, b: {"type": "axe", "source": source},
                       prov, emprises_zebras, mesures, {"paire": paire})


def _axe_tirets_gam(ms, prolonge=0.0):
    """Axe d'une suite de tirets levés un à un (GAM) : axe levé de chaque tiret sur son étendue,
    orientés et ordonnés le long de la suite, reliés par des segments droits ; prolongé aux bouts."""
    pts = np.vstack([m["_axe"] for m in ms])
    c = pts.mean(axis=0)
    w, V = np.linalg.eigh((pts - c).T @ (pts - c))
    u = V[:, int(np.argmax(w))]
    if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
        u = -u
    parts = []
    for m in ms:
        G = min((ax[0] for ax in MG.axes_leves(M.gam_refs(m["p"]))), key=lambda P: float(np.median(projeter(P, m["_axe"])[1])))
        sg, dg, _ = projeter(G, m["r"])
        sg = sg[dg <= 0.5] if np.any(dg <= 0.5) else sg
        P = _sous(G, sg.min(), sg.max())
        if (P[-1] - P[0]) @ u < 0:
            P = P[::-1]
        parts.append(P)
    parts.sort(key=lambda P: float(P[0] @ u))
    A = M.dedoublonner(np.vstack(parts))
    u0 = (A[1] - A[0]) / np.hypot(*(A[1] - A[0]))
    u1 = (A[-1] - A[-2]) / np.hypot(*(A[-1] - A[-2]))
    return np.vstack([A[0] - u0 * prolonge, A, A[-1] + u1 * prolonge])


def _axe_ajuste(ms, prolonge=0.0):
    """Axe d'une chaîne de marques hors réseau : droite (ACP) si les axes v1 y tiennent à 4 cm,
    sinon polynôme de degré ≤ 3 de l'écart latéral, échantillonné à 0,25 m ; prolongé de `prolonge`."""
    if len(ms) == 1 and len(ms[0]["_axe"]) > 2:
        P = ms[0]["_axe"]
        u0 = (P[1] - P[0]) / np.hypot(*(P[1] - P[0]))
        u1 = (P[-1] - P[-2]) / np.hypot(*(P[-1] - P[-2]))
        return np.vstack([P[0] - u0 * prolonge, P, P[-1] + u1 * prolonge])
    pts = np.vstack([densifier(m["_axe"], 0.25)[0] for m in ms])
    c = pts.mean(axis=0)
    w, V = np.linalg.eigh((pts - c).T @ (pts - c))
    u = V[:, int(np.argmax(w))]
    if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
        u = -u
    n = np.array([-u[1], u[0]])
    s, t = (pts - c) @ u, (pts - c) @ n
    allp = np.vstack([poly[0] for m in ms for poly in m["polys"]])
    sa = (allp - c) @ u
    lo, hi = sa.min() - prolonge, sa.max() + prolonge
    if np.max(np.abs(t - t.mean())) <= 0.04:
        return np.vstack([c + u * lo + n * t.mean(), c + u * hi + n * t.mean()])
    deg = 2 if np.ptp(s) < 15 else 3
    coef = np.polyfit(s, t, deg)
    g = np.linspace(lo, hi, max(2, int(math.ceil((hi - lo) / 0.25)) + 1))
    return c + np.outer(g, u) + np.outer(np.polyval(coef, g), n)


# --------------------------------------------------------------------------- transversales
def transversales(reseau, objets):
    """Lignes d'effet des feux (T'2 0,15) : une entité par groupe v1, axe ACP des tirets ; n = ⌊(L + vide) /
    (trait + vide)⌋ tirets centrés sur l'axe (phase ignorée : motif symétrique sur la largeur des voies)."""
    ms_all = [m for m in M.v1() if m["p"]["type"] == "ligne_effet_feux"]
    entites, devenir = [], {}
    for g in _unions(ms_all, lambda a, b: a["p"]["groupe"] == b["p"]["groupe"]):
        c = np.array([m["obb"]["c"] for m in g])
        cc = c - c.mean(axis=0)
        w, V = np.linalg.eigh(cc.T @ cc)
        u = V[:, int(np.argmax(w))]
        if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
            u = -u
        n = np.array([-u[1], u[0]])
        allp = np.vstack([m["r"] for m in g])
        s = (allp - c.mean(axis=0)) @ u
        t0 = float(np.median(cc @ n))
        A = c.mean(axis=0) + u * s.min() + n * t0
        B = c.mean(axis=0) + u * s.max() + n * t0
        axe = np.vstack([A, B])
        L = float(np.hypot(*(B - A)))
        iv = _intervalles(axe, g)
        a = np.array([x[0] for x in iv])
        b = np.array([x[1] for x in iv])
        T, V_ = 0.5, 0.5
        nt = int(math.floor((L + V_) / (T + V_) + 1e-6))
        phi = (L - (nt * T + (nt - 1) * V_)) / 2.0
        r = _residus(a, b, T, T + V_, phi)[3]
        ids = sorted(m["id"] for m in g)
        # objet stopLine le plus proche
        ob = min(objets, key=lambda o: float(np.min(np.hypot(*(o["anneau"] - (A + B) / 2).T)))) if objets else None
        mid = (A + B) / 2
        e = {"id": M.ident("MT", ids), "classe": "transversale", "type": "effet_feux", "couleur": "blanc",
             "geom": ("LineString", axe), "longueur_m": round(L, 3),
             "modulation": "T'2", "trait_m": T, "vide_m": V_, "phase_m": round(phi, 3), "modulation_source": "IISR",
             "largeur_m": 0.15, "n_tirets": nt, "interruptions": [],
             "mesures_tirets": {"n_v1": len(g), "residu_p95_m": round(float(np.percentile(r, 95)), 3), "residu_max_m": round(float(r.max()), 3)},
             "usure": _usure(g), "couverture": M.mediane_ou([m["p"]["couverture"] for m in g]), "etat": _maj(g, "etat"),
             "groupe": g[0]["p"]["groupe"], "branche": g[0]["p"]["branche"], "lien_v1": ids,
             "prov": {"geometrie": {"src": "plan2025", "ref": f"axe ACP de {len(g)} tirets v1 (plan projet)", "conf": "moyenne"},
                      "largeur_m": {"src": "norme:IISR_7_art117-4", "ref": "effet des feux T'2 0,15", "conf": "haute"},
                      "phase_m": {"src": "regle:marquages_geometrie.lignes_transversales", "ref": f"{nt} tirets T'2 centrés sur l'axe de {L:.2f} m", "conf": "moyenne"}}}
        if ob is not None and float(np.min(np.hypot(*(ob["anneau"] - mid).T))) < 6.0:
            e["ancrage"] = {"type": "xodr_objet", "route": ob["route"], "objet": ob["id"], "s": round(ob["s"], 3)}
            e["prov"]["ancrage"] = {"src": "xodr", "ref": f"objet stopLine {ob['id']} ({ob['nom']})", "conf": "haute"}
        else:
            e["ancrage"] = {"type": "axe", "source": "v1"}
        entites.append(e)
        for m in g:
            devenir[m["id"]] = ("genere", e["id"], "tiret de la ligne d'effet des feux")
    return entites, devenir
