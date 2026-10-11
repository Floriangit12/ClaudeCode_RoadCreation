"""Contrôles des marquages (MQ-*, INF-FLE-*, VAL-LIG-002, VAL-ZEB-003, VAL-FLE-001, TQ-MQG-*, TQ-VAL-002, TQ-MQR-005,
MQ-DET-010) sur la description (marquages.geojson) et sur la fabrication (marquages_lignes, passages, symboles, zones
.usda ; points/symboles.json posés sur prototypes/symboles.usda).

Conventions : peinture fabriquée = dessus (faces de normale |nz| > 0,9) ; empreinte = dessus + chanfreins (|nz| > 0,1).
Les épaisseurs sont mesurées contre le sol fabriqué (requête verticale exacte sur sol.usdc).
"""
import collections
import math
import re

import numpy as np

import ctl_commun as K
from ctl_commun import regle, r4, stats

BRANCHES_FEUX = ("verdun_sw", "verdun_ne", "reviree", "vercors", "centre")
SOL_ADMIS = {"chaussee", "parking", "piste_cyclable", "acces_riverain", "quai_bus", "autre"}


# =========================================================================== outils
def modulations(ctx):
    t = ctx.spec("marquages_geometrie")["modulations"]["table"]
    return {k: (v["trait_m"], v["vide_m"]) for k, v in t.items()}


def axe(e):
    if "lignes" not in e:
        return None
    return np.vstack(e["lignes"]) if len(e["lignes"]) == 1 else e["lignes"][0]


def longueur(P):
    return float(np.hypot(*np.diff(P, axis=0).T).sum())


def intervalles_peints(p, L, mods):
    """Parties peintes [s0, s1] d'une ligne : modulation (trait, vide), phase (MQ-DET-011 : ancrage aval si absente),
    interruptions."""
    tr, vi = p.get("trait_m"), p.get("vide_m")
    mod = p.get("modulation") or "continue"
    if (not tr or not vi) and mod in mods:
        tr, vi = mods[mod]
    if mod == "continue" or not tr or not vi:
        iv = [(0.0, L)]
    else:
        per = tr + vi
        ph = p.get("phase_m")
        if ph is None:
            ph = (L - tr) - per * math.floor((L - tr) / per)
        iv = [(max(ph + k * per, 0.0), min(ph + k * per + tr, L))
              for k in range(int(math.floor(-ph / per)) - 1, int(math.ceil((L - ph) / per)) + 2)]
        iv = [(a, b) for a, b in iv if b - a > 1e-4]
    for a0, b0 in p.get("interruptions") or []:
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
    return [(a, b) for a, b in iv if b - a >= 0.01]


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def fab_marquages(ctx):
    """{entité: {"T": triangles monde (n, 3, 3), "couche": nom, "instance": point ou None}}"""
    def f():
        out = {}
        for couche in ("marquages_lignes", "passages", "symboles", "zones"):
            c = ctx.fab_couche(couche)
            if c is None:
                continue
            for e, idx in sorted(ctx.fab_entites(couche).items()):
                eid = re.sub(r"_c\d+$", "", e).replace("_", "-", 1)       # tronçons ML_xxxx_cNN d'une même ligne
                T = c["T"][idx].astype(np.float64)
                if eid in out:
                    out[eid]["T"] = np.concatenate([out[eid]["T"], T])
                    out[eid]["troncons"] += 1
                else:
                    out[eid] = {"T": T, "couche": couche, "instance": None, "troncons": 1}
        proto = ctx.fab_couche("proto_symboles")
        pe = ctx.fab_entites("proto_symboles")
        for pt in ctx.points("symboles")["points"]:
            idx = pe.get(pt["asset"])
            if idx is None:
                out[pt["id"]] = {"T": np.zeros((0, 3, 3)), "couche": "instances", "instance": pt}
                continue
            T = proto["T"][idx].astype(np.float64) * np.asarray(pt["s"], float)
            M = quat_mat(pt["q"])
            T = T @ M.T + np.asarray(pt["p"], float)
            out[pt["id"]] = {"T": T, "couche": "instances", "instance": pt}
        return out
    return ctx._m("marq:fab", f)


def normales(T):
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    a = np.linalg.norm(n, axis=1)
    return n / np.maximum(a, 1e-15)[:, None], 0.5 * a


def dessus(T):
    n, a = normales(T)
    return np.abs(n[:, 2]) > 0.9


def aire_projetee(T, masque):
    t = T[masque]
    return float(0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                              - (t[:, 1, 1] - t[:, 0, 1]) * (t[:, 2, 0] - t[:, 0, 0])).sum())


def angles_min(T):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]

    def ang(u, v):
        cu = np.einsum("ij,ij->i", u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-15)
        return np.degrees(np.arccos(np.clip(cu, -1, 1)))
    return np.minimum(np.minimum(ang(b - a, c - a), ang(a - b, c - b)), ang(a - c, b - c))


def epaisseurs(ctx, eid):
    """Dessus de peinture − sol fabriqué aux sommets du dessus ; NaN hors sol. Mémorisé."""
    def f():
        T = fab_marquages(ctx)[eid]["T"]
        if not len(T):
            return np.zeros(0), np.zeros((0, 2)), np.zeros(0)
        m = dessus(T)
        P = np.unique(np.round(T[m].reshape(-1, 3), 5), axis=0)
        z, _, _ = ctx.requete("sol", 0.5).requete(P[:, :2])
        # bas des flancs : sommets des faces non horizontales
        Pb = T[~m].reshape(-1, 3)
        zb = np.zeros(0)
        if len(Pb):
            Pb = np.unique(np.round(Pb, 5), axis=0)
            zs, _, _ = ctx.requete("sol", 0.5).requete(Pb[:, :2])
            low = Pb[:, 2] < np.nanmedian(P[:, 2] - z) + zs - 0.0005 if np.isfinite(z).any() else np.zeros(len(Pb), bool)
            zb = (Pb[:, 2] - zs)[low]
        return P[:, 2] - z, P[:, :2], zb
    return ctx._m("marq:ep:" + eid, f)


def rect_zebra(p, A, B):
    u = np.array([math.cos(math.radians(p["cap_bandes_deg"])), math.sin(math.radians(p["cap_bandes_deg"]))])
    ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
    A2, B2 = A - 0.25 * ax, B + 0.25 * ax
    h = 0.5 * float(p.get("longueur_bande_m") or 3.0)
    return [np.array([A2 - h * u, B2 - h * u, B2 + h * u, A2 + h * u])]


def zebras(ctx):
    def f():
        out = {}
        for i, e in sorted(ctx.marquages.items()):
            p = e["p"]
            if p["classe"] == "passage" and p["type"] == "zebra" and ctx.fabrique_marquage(p):
                L = e["lignes"][0]
                out[i] = {"p": p, "A": L[0], "B": L[-1], "rect": rect_zebra(p, L[0], L[-1])}
        return out
    return ctx._m("marq:zebras", f)


def centroide(poly):
    """Centroïde d'aire d'un polygone [[ext, trous...]] (local)."""
    A, C = 0.0, np.zeros(2)
    for k, r in enumerate(poly):
        x, y = r[:, 0], r[:, 1]
        x1, y1 = np.roll(x, -1), np.roll(y, -1)
        cr = x * y1 - x1 * y
        a = 0.5 * cr.sum()
        c = np.array([((x + x1) * cr).sum(), ((y + y1) * cr).sum()]) / (6 * a) if abs(a) > 1e-12 else r.mean(0)
        a = abs(a) * (1 if k == 0 else -1)
        A += a
        C += a * c
    return C / A if abs(A) > 1e-12 else poly[0].mean(0)


def voie_de(ctx, xy):
    """(route, voie, s) de la voie OpenDRIVE hors jonction (driving / bus) contenant le point, sinon None."""
    for v in ctx.voies:
        if v["jonction"] or v["type"] not in ("driving", "bus"):
            continue
        if K.dans(xy[None], v["poly"])[0]:
            r = ctx.reseau[v["route"]]
            sref = np.linspace(0, r.longueur, int(r.longueur / 0.1) + 2)
            xr, yr, _ = r.reference(sref)
            s_ = float(K.C.projeter(np.c_[xr, yr], xy[None])[0][0])
            return v["route"], int(v["voie"]), s_
    return None


def voies_roulables(ctx):
    return ctx._m("marq:roul", lambda: [v["poly"] for v in ctx.voies if v["type"] in ("driving", "bus", "biking")
                                        or v["jonction"]])


def cap_voie(ctx, anc):
    """Cap de circulation (degrés) d'une voie OpenDRIVE à l'abscisse de l'ancrage."""
    r = ctx.reseau[str(anc["route"])]
    _, _, h = r.reference(np.array([anc["s"]]))
    c = math.degrees(float(h[0]))
    return (c + 180.0) % 360 if int(anc["voie"]) > 0 else c % 360


def lignes_peintes(ctx):
    """Lignes longitudinales fabriquées : {id: (axe, intervalles peints, p)}."""
    def f():
        mods = modulations(ctx)
        out = {}
        for i, e in sorted(ctx.marquages.items()):
            p = e["p"]
            if p["classe"] != "ligne" or not ctx.fabrique_marquage(p) or "lignes" not in e:
                continue
            P = axe(e)
            L = longueur(P)
            out[i] = (P, intervalles_peints(p, L, mods), p)
        return out
    return ctx._m("marq:lignes", f)


def points_peints(P, iv, pas=0.1):
    S = K.C.abscisses(P)
    s = np.concatenate([np.arange(a, b + 1e-9, pas) for a, b in iv]) if iv else np.zeros(0)
    if not len(s):
        return np.zeros((0, 2))
    return K.C.point_a(P, s)[0]


# =========================================================================== MQ-LIG-001 / 002 / 005 / 007 / 008 / 009
@regle("MQ-LIG-001", "les_deux", "majeur",
       "Aucune ligne longitudinale dans l'aire du carrefour (union des voies de la jonction 100) sauf lignes de guidage "
       "T'2 levées ou détectées : longueur peinte (intervalles de modulation) à l'intérieur de l'aire. Violation : plus "
       "de 1 m peint dans l'aire, d'une ligne inférée ou d'une ligne non T'2. Unité : ligne longitudinale fabriquée "
       "à moins de 10 m de l'aire.", "implemente")
def mq_lig_001(ctx, R):
    jn = ctx.jonction
    lo = np.min([p[0].min(0) for p in jn], axis=0) - 10
    hi = np.max([p[0].max(0) for p in jn], axis=0) + 10
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        if P[:, 0].max() < lo[0] or P[:, 0].min() > hi[0] or P[:, 1].max() < lo[1] or P[:, 1].min() > hi[1]:
            continue
        Q = points_peints(P, iv)
        if not len(Q):
            continue
        dedans = K.dans_liste(Q, jn)
        L = dedans.sum() * 0.1
        infere = str(p.get("src", "")).startswith("regle")
        guidage = p.get("modulation") == "T'2" and not infere
        ok = L <= 1.0 or guidage
        k = int(np.nonzero(dedans)[0][0]) if dedans.any() else 0
        R.tester(ok, entite=i, xy=Q[k], valeur=r4(L, 1), seuil="≤ 1 m dans l'aire (sauf guidage T'2 observé)",
                 detail=f"{L:.1f} m peints dans l'aire du carrefour ({p.get('modulation')}, src {p.get('src')}, "
                        f"rôle {p.get('role')})", ecart=L, severite="majeur" if infere else "mineur")


@regle("MQ-LIG-002", "les_deux", "majeur",
       "Interruption des lignes longitudinales à 0,50 m de part et d'autre de tout passage piéton : distance des parties "
       "peintes (modulation, phase, interruptions) au rectangle du zébra ≥ 0,40 m ; mesure aussi sur les maillages "
       "fabriqués (sommets du dessus). Unité : couple ligne / zébra à moins de 3 m.", "partiel",
       "« entre la LEF et le passage seule la ligne axiale » non contrôlé")
def mq_lig_002(ctx, R):
    Z = zebras(ctx)
    fab = fab_marquages(ctx)
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        Q = points_peints(P, iv, 0.05)
        if not len(Q):
            continue
        for zid, z in Z.items():
            rect = z["rect"]
            d = K.dist_polys(Q, [rect])
            d = np.where(K.dans(Q, rect), 0.0, d)
            if d.min() > 3.0:
                continue
            T = fab.get(i, {}).get("T")
            df = np.inf
            if T is not None and len(T):
                V = T[dessus(T)].reshape(-1, 3)[:, :2]
                dv = K.dist_polys(V, [rect])
                dv = np.where(K.dans(V, rect), 0.0, dv)
                df = float(dv.min())
            dm = min(float(d.min()), df)
            k = int(np.argmin(d))
            R.tester(dm >= 0.40 - 1e-6, entite=f"{i} / {zid}", xy=Q[k], valeur=r4(dm, 3), seuil="≥ 0,40 m (0,50 visé)",
                     detail=f"partie peinte à {d.min():.2f} m (décrite) / {df:.2f} m (fabriquée) du passage",
                     ecart=0.5 / max(dm, 0.05))


@regle("MQ-LIG-005", "description", "info",
       "Une ligne continue de délimitation entre voies de même sens mesure au moins 20 m (en agglomération). Unité : "
       "ligne continue de rôle « delimitation ».", "partiel", "annonce T3 de longueur L contrôlée par MQ-LIG-006")
def mq_lig_005(ctx, R):
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        if p.get("role") != "delimitation" or p.get("modulation") != "continue":
            continue
        L = longueur(P)
        R.tester(L >= 20.0, entite=i, xy=P[len(P) // 2], valeur=r4(L, 1), seuil="≥ 20 m",
                 detail=f"continue de délimitation de {L:.1f} m (src {p.get('src')})", ecart=20.0 / max(L, 0.5))


@regle("MQ-LIG-006", "description", "info",
       "Une ligne continue de délimitation est annoncée en amont par une T3 (2u) colinéaire d'au moins 20 m (L = 39 m à "
       "50 km/h, pratique parisienne 20 m). Unité : ligne continue de délimitation.", "partiel",
       "flèches de rabattement non concernées sur le site")
def mq_lig_006(ctx, R):
    L_ = lignes_peintes(ctx)
    t3 = {i: v for i, v in L_.items() if v[2].get("modulation") in ("T3", "T3_site")}
    for i, (P, iv, p) in L_.items():
        if p.get("role") != "delimitation" or p.get("modulation") != "continue":
            continue
        best = 0.0
        for j, (Q, _, q) in t3.items():
            d = min(np.hypot(*(Q[[0, -1]] - P[0]).T).min(), np.hypot(*(Q[[0, -1]] - P[-1]).T).min())
            if d < 1.5:
                best = max(best, longueur(Q))
        R.tester(best >= 20.0, entite=i, xy=P[0], valeur=r4(best, 1), seuil="T3 d'annonce ≥ 20 m",
                 detail=f"T3 colinéaire trouvée : {best:.1f} m", ecart=20.0 / max(best, 1.0))


@regle("MQ-LIG-007", "description", "info",
       "Avenue de Verdun (2 × 2 voies) : le terre-plein central physique (voie OpenDRIVE median) est délimité par une "
       "continue 3u ; son absence est signalée pour information. Mesure : part de la longueur du bord du median "
       "longée par une ligne continue fabriquée à moins de 0,40 m. Unité : section de route avec median.", "implemente")
def mq_lig_007(ctx, R):
    L_ = lignes_peintes(ctx)
    cont = [v[0] for v in L_.values() if v[2].get("modulation") == "continue"]
    A = np.vstack([c[:-1] for c in cont]) if cont else np.zeros((0, 2))
    B = np.vstack([c[1:] for c in cont]) if cont else np.zeros((0, 2))
    for rid in ("1", "2", "3", "4"):
        r = ctx.reseau[rid]
        for sec in r.sections:
            meds = [v for v in sec.voies if sec.voies[v].type == "median"]
            if not meds:
                continue
            s = np.linspace(sec.s, sec.s1, max(2, int((sec.s1 - sec.s) / 1.0)))
            tb = r.t_bords(s, sec)
            for v in meds:
                vi = v - 1 if v > 0 else v + 1
                t = tb[vi]
                x, y, _ = X_point(r, s, t)
                Q = np.c_[x, y]
                d, _, _ = K.C.distance_segments(Q, A, B) if len(A) else (np.full(len(Q), np.inf), 0, 0)
                part = float((d <= 0.40).mean())
                R.tester(part >= 0.5, entite=f"route {rid} s{sec.s:g} median {v}", xy=Q[len(Q) // 2],
                         valeur=r4(part, 2), seuil="continue 3u le long du TPC (≥ 50 %)",
                         detail=f"bord du median longé par une continue sur {part * 100:.0f} % de {sec.s1 - sec.s:.0f} m",
                         ecart=1.0)


def X_point(r, s, t):
    return K.X.point_st(r, s, t)


@regle("MQ-LIG-008", "description", "majeur",
       "Aucune ligne axiale sur une chaussée bidirectionnelle à deux voies de largeur circulable < 5,20 m (chemin de la "
       "Revirée, route 5) : lignes de rôle « axe » à moins de 0,5 m de la ligne de référence, aux abscisses où la "
       "somme des voies driving est < 5,20 m. Unité : ligne axiale le long de la route 5.", "implemente")
def mq_lig_008(ctx, R):
    r = ctx.reseau["5"]
    s = np.linspace(0, r.longueur, int(r.longueur / 0.5))
    x, y, _ = r.reference(s)
    larg = np.zeros(len(s))
    for k, si in enumerate(s):
        sec = r.section(si)
        tb = r.t_bords(np.array([si]), sec)
        w = 0.0
        for v, voie in sec.voies.items():
            if voie.type == "driving":
                vi = v - 1 if v > 0 else v + 1
                w += abs(float(tb[v][0] - tb[vi][0]))
        larg[k] = w
    ref = np.c_[x, y]
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        if p.get("role") != "axe":
            continue
        d = K.dist_polyligne(P, ref)
        if d.max() > 0.5:
            continue
        _, j, _ = K.C.distance_segments(P, ref[:-1], ref[1:])
        wmin = float(larg[np.clip(j, 0, len(larg) - 1)].min())
        R.tester(wmin >= 5.20, entite=i, xy=P[len(P) // 2], valeur=r4(wmin, 2), seuil="largeur ≥ 5,20 m",
                 detail=f"ligne axiale sur la Revirée où la chaussée fait {wmin:.2f} m", ecart=5.2 / max(wmin, 0.5))


@regle("MQ-LIG-009", "description", "mineur",
       "Pas de ligne de rive le long d'une chaussée bordée sauf si elle est levée ou détectée : lignes de rôle « rive » "
       "à moins de 0,6 m d'une bordure de chaussée, de source règle ou v1 seule. Unité : ligne de rive.", "implemente")
def mq_lig_009(ctx, R):
    from ctl_sol import kerbs_chaussee_index
    A, B = kerbs_chaussee_index(ctx)
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        if p.get("role") != "rive":
            continue
        d, _, _ = K.C.distance_segments(P, A, B)
        bordee = float(np.median(d)) <= 0.6
        src = str(p.get("src"))
        ok = not bordee or src in ("gam", "ortho2022", "plan2025")
        R.tester(ok, entite=i, xy=P[len(P) // 2], valeur=r4(float(np.median(d)), 2), seuil="rive le long d'une bordure "
                 "seulement si observée", detail=f"ligne de rive à {np.median(d):.2f} m d'une bordure, src {src}")


# =========================================================================== lignes transversales
def lefs(ctx):
    return {i: e for i, e in sorted(ctx.marquages.items()) if e["p"]["classe"] == "transversale"
            and e["p"]["type"] == "effet_feux"}


def r11(ctx):
    return [s for s in ctx.signaux if s["type"] == "1000001" and "principal" in s["nom"]]


def approche_r11(ctx, sig):
    """Voies commandées (côté de circulation) d'un R11 : voies driving du côté donné par l'orientation."""
    r = ctx.reseau[sig["route"]]
    sec = r.section(sig["s"])
    cote = -1 if sig["orientation"] == "+" else 1
    voies = sorted(v for v, l in sec.voies.items() if l.type == "driving" and np.sign(v) == cote)
    return r, sec, voies, cote


@regle("MQ-LEF-003", "description", "mineur",
       "Ligne d'effet des feux (peinte, hypothèse ou virtuelle) perpendiculaire à l'axe des voies commandées (90 ± 3°) "
       "et de longueur égale à la largeur des voies driving du côté commandé (±0,5 m). Unité : ligne d'effet.",
       "implemente")
def mq_lef_003(ctx, R):
    sigs = r11(ctx)
    for i, e in lefs(ctx).items():
        P = axe(e)
        c = P.mean(0)
        sig = min(sigs, key=lambda s: float(np.hypot(*(s["xy"] - c))))
        r, sec, voies, cote = approche_r11(ctx, sig)
        sref = np.linspace(0, r.longueur, int(r.longueur / 0.25) + 2)
        xr, yr, hr = r.reference(sref)
        _, j, _ = K.C.distance_segments(c[None], np.c_[xr, yr][:-1], np.c_[xr, yr][1:])
        s0 = sref[int(j[0])]
        h = math.degrees(float(hr[int(j[0])]))
        u = P[-1] - P[0]
        ang = abs(((K.cap_deg(u) - h) % 180) - 90)
        tb = r.t_bords(np.array([s0]), r.section(s0))
        larg = sum(abs(float(tb[v][0] - tb[v - cote][0])) for v in voies if v in tb and (v - cote) in tb)
        L = longueur(P)
        ok = ang <= 3.0 and abs(L - larg) <= 0.5
        R.tester(ok, entite=i, xy=c, valeur=r4(ang, 2), seuil="perpendiculaire ±3°, longueur = voies commandées ±0,5 m",
                 detail=f"écart à la perpendiculaire {ang:.1f}°, longueur {L:.2f} m pour {larg:.2f} m de voies commandées "
                        f"(route {r.id}, {sig['nom']})", ecart=max(ang / 3.0, abs(L - larg) / 0.5))


@regle("MQ-LEF-004", "description", "majeur",
       "Cohérence feu / ligne d'effet : le R11 principal de l'approche est à 0-4 m en aval de la ligne (projection sur "
       "l'axe de la route) ; une LEF peinte ou en hypothèse est parallèle au passage aval (±3°) et à 2,5-4,5 m de son "
       "bord ; une ligne virtuelle (MQ-LEF-002) est au bord amont du passage ou à l'aplomb du feu. Unité : ligne "
       "d'effet.", "implemente")
def mq_lef_004(ctx, R):
    sigs = r11(ctx)
    Z = zebras(ctx)
    for i, e in lefs(ctx).items():
        p = e["p"]
        P = axe(e)
        c = P.mean(0)
        sig = min(sigs, key=lambda s: float(np.hypot(*(s["xy"] - c))))
        r = ctx.reseau[sig["route"]]
        sref = np.linspace(0, r.longueur, int(r.longueur / 0.1) + 2)
        xr, yr, _ = r.reference(sref)
        ref = np.c_[xr, yr]
        s_l = K.C.projeter(ref, c[None])[0][0]
        s_s = K.C.projeter(ref, sig["xy"][None])[0][0]
        sens = 1.0 if sig["orientation"] == "+" else -1.0
        aval = (s_s - s_l) * sens
        det = [f"feu à {aval:.2f} m en aval"]
        ok = -0.3 <= aval <= 4.0 + 1e-6
        ec = max(0.0, -aval) / 0.3 + max(0.0, aval - 4.0)
        # passage aval le plus proche
        zz = sorted(Z.items(), key=lambda kv: float(np.min(K.dist_polys(c[None], [kv[1]["rect"]]))))
        if zz:
            zid, z = zz[0]
            dz = float(np.min(K.dist_polys(P, [z["rect"]])))
            ang = K.ecart_angle(K.cap_deg(P[-1] - P[0]), z["p"]["cap_bandes_deg"] + 90.0, 180.0)
            virt = bool(p.get("virtuelle"))
            if not virt:
                ok = ok and 2.5 - 1e-6 <= dz <= 4.5 + 1e-6 and ang <= 3.0
                ec = max(ec, abs(dz - 3.5) / 1.0 if not 2.5 <= dz <= 4.5 else 0.0, ang / 3.0)
            det.append(f"{'virtuelle' if virt else 'peinte/hypothèse'} à {dz:.2f} m du passage {zid}, angle {ang:.1f}°")
        R.tester(ok, entite=i, xy=c, valeur=r4(aval, 2), seuil="feu 0-4 m en aval ; LEF à 2,5-4,5 m du passage, ±3°",
                 detail=" ; ".join(det) + f" ({sig['nom']})", ecart=max(ec, 1.0))


@regle("MQ-LEF-008", "description", "majeur",
       "Sur une branche à feux, ni ligne STOP ni ligne cédez-le-passage : transversales de type stop / cedez dans les "
       "branches gérées par des feux. Unité : ligne transversale des branches à feux.", "implemente")
def mq_lef_008(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["classe"] != "transversale" or p.get("branche") not in BRANCHES_FEUX:
            continue
        mauvais = p["type"] in ("stop", "cedez", "cedez_le_passage")
        R.tester(not mauvais, entite=i, xy=axe(e).mean(0) if "lignes" in e else None, valeur=p["type"],
                 seuil="ni STOP ni cédez sur une branche à feux", detail=f"{p['type']} sur {p.get('branche')}")


@regle("MQ-TRV-005", "description", "mineur",
       "Cédez-le-passage cycliste au feu : aucune marque spécifique (seulement M12 / R19) : aucune transversale "
       "« cycliste » sur les branches à feux. Unité : transversale des branches à feux.", "implemente")
def mq_trv_005(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["classe"] != "transversale" or p.get("branche") not in BRANCHES_FEUX:
            continue
        R.tester("cycl" not in p["type"], entite=i, valeur=p["type"], seuil="aucune marque cycliste au feu")


# =========================================================================== passages piétons
@regle("MQ-PP-003", "description", "mineur",
       "Largeur de traversée (longueur des bandes) ≥ 2,50 m en ville et au moins la largeur de l'abaissé décrit qui la "
       "borde (abaissés de traversée à moins de 1,5 m d'une extrémité de l'axe). Une largeur mesurée plus faible est "
       "gardée et signalée. Unité : zébra.", "implemente")
def mq_pp_003(ctx, R):
    for zid, z in zebras(ctx).items():
        p = z["p"]
        Lb = float(p.get("longueur_bande_m") or 0)
        ab = []
        for bid, b in ctx.bordures.items():
            for a in b["p"]["abaisses"]:
                if a["type"] != "traversee":
                    continue
                m = K.point(b["P"][:, :2], (a["s0"] + a["s1"]) / 2)
                if min(np.hypot(*(m - z["A"])), np.hypot(*(m - z["B"]))) < 1.5:
                    ab.append((a["id"], a["s1"] - a["s0"]))
        lab = max([x[1] for x in ab], default=0.0)
        ok = Lb >= 2.5 - 1e-6 and Lb >= lab - 0.05
        R.tester(ok, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(Lb, 2), seuil="≥ 2,50 m et ≥ abaissé",
                 detail=f"bandes de {Lb:.2f} m ; abaissés voisins {[(a, round(l, 2)) for a, l in ab]}"
                        + (" ; " + "; ".join(p.get("ecarts_iisr", [])) if p.get("ecarts_iisr") else ""),
                 ecart=max(2.5 / max(Lb, 0.1), lab / max(Lb, 0.1)))


def intersections(P0, P1, Q):
    """Intersections du segment [P0, P1] avec la polyligne Q : liste (t le long du segment, indice de segment de Q)."""
    d = P1 - P0
    A, B = Q[:-1], Q[1:]
    e = B - A
    den = d[0] * e[:, 1] - d[1] * e[:, 0]
    ok = np.abs(den) > 1e-12
    w = A - P0
    t = np.where(ok, (w[:, 0] * e[:, 1] - w[:, 1] * e[:, 0]) / np.where(ok, den, 1), -1)
    u = np.where(ok, (w[:, 0] * d[1] - w[:, 1] * d[0]) / np.where(ok, den, 1), -1)
    k = np.nonzero(ok & (t >= 0) & (t <= 1) & (u >= 0) & (u <= 1))[0]
    return [(float(t[j]), int(j)) for j in k]


def axe_chaussee_zebra(ctx, z):
    """Cap (degrés, modulo 180) des faces de bordure coupées par l'axe du zébra prolongé de 3 m de part et d'autre
    (moyenne des deux côtés) ; None si aucune bordure n'est coupée."""
    A, B = z["A"], z["B"]
    ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
    caps = []
    for P0, P1 in ((A, A - 3.0 * ax), (B, B + 3.0 * ax)):
        best = None
        for bid, b in ctx.bordures.items():
            Q = b["P"][:, :2]
            lo, hi = Q.min(0), Q.max(0)
            if max(P0[0], P1[0]) < lo[0] or min(P0[0], P1[0]) > hi[0] or max(P0[1], P1[1]) < lo[1] \
                    or min(P0[1], P1[1]) > hi[1]:
                continue
            for t, j in intersections(P0, P1, Q):
                if best is None or t < best[0]:
                    best = (t, K.cap_deg(Q[j + 1] - Q[j]) % 180)
        if best:
            caps.append(best[1])
    if not caps:
        return None
    a = np.radians(np.array(caps) * 2)
    return (math.degrees(math.atan2(np.sin(a).mean(), np.cos(a).mean())) / 2) % 180


@regle("MQ-PP-005", "description", "mineur",
       "Passage au plus court : bandes parallèles à l'axe de la chaussée, pris comme la direction des faces de bordure "
       "coupées par l'axe du zébra prolongé de 3 m de chaque côté (traversée perpendiculaire aux bordures), écart ≤ 5° ; obliquité de la traversée rapportée (≤ 15° "
       "attendu). Unité : zébra bordé par des bordures à ses extrémités.", "implemente")
def mq_pp_005(ctx, R):
    for zid, z in zebras(ctx).items():
        p = z["p"]
        c = (z["A"] + z["B"]) / 2
        cap = axe_chaussee_zebra(ctx, z)
        if cap is None:
            continue
        ang = K.ecart_angle(p["cap_bandes_deg"], cap, 180.0)
        obl = abs(float(p.get("obliquite_deg") or 0.0))
        R.tester(ang <= 5.0 and obl <= 15.0, entite=zid, xy=c, valeur=r4(ang, 1), seuil="bandes // bordures ±5°, "
                 "obliquité ≤ 15°", detail=f"bandes à {ang:.1f}° des bordures d'extrémité, obliquité {obl:.0f}°",
                 ecart=max(ang / 5, obl / 15))


@regle("MQ-PP-008", "les_deux", "majeur",
       "Passages de branches contiguës sans chevauchement (rectangles des zébras décrits et empreintes fabriquées) et BEV "
       "écartées d'au moins 0,50 m. Unités : paire de zébras à moins de 5 m, paire de BEV à moins de 3 m.",
       "implemente")
def mq_pp_008(ctx, R):
    Z = list(zebras(ctx).items())
    fab = fab_marquages(ctx)
    for a in range(len(Z)):
        for b in range(a + 1, len(Z)):
            (ia, za), (ib, zb) = Z[a], Z[b]
            d = float(min(K.dist_polys(za["rect"][0], [zb["rect"]]).min(), K.dist_polys(zb["rect"][0], [za["rect"]]).min()))
            inter = bool(K.dans(za["rect"][0], zb["rect"]).any() or K.dans(zb["rect"][0], za["rect"]).any())
            if d > 5.0 and not inter:
                continue
            Ta, Tb = fab.get(ia, {}).get("T"), fab.get(ib, {}).get("T")
            chev = 0
            if Ta is not None and Tb is not None and len(Ta) and len(Tb):
                Va = Ta[dessus(Ta)].mean(1)[:, :2]
                rq = K.RequeteMaillage(Tb[dessus(Tb)], 0.25)
                z_, _, _ = rq.requete(Va)
                chev = int(np.isfinite(z_).sum())
            R.tester(not inter and chev == 0, entite=f"{ia} / {ib}", xy=(za["A"] + zb["A"]) / 2, valeur=r4(d, 2),
                     seuil="aucun chevauchement", detail=f"distance {d:.2f} m, rectangles {'sécants' if inter else 'disjoints'}, "
                                                         f"{chev} triangle(s) fabriqué(s) superposé(s)", ecart=2.0)
    B = [(i, v["poly"][0][0]) for i, v in sorted(ctx.ponctuels.items()) if v["p"].get("type") == "bev"]
    for a in range(len(B)):
        for b in range(a + 1, len(B)):
            d = float(K.dist_polys(B[a][1], [[B[b][1]]]).min())
            if d > 3.0:
                continue
            R.tester(d >= 0.5, entite=f"{B[a][0]} / {B[b][0]}", xy=B[a][1].mean(0), valeur=r4(d, 2), seuil="≥ 0,50 m",
                     detail=f"BEV distantes de {d:.2f} m", ecart=0.5 / max(d, 0.05))


@regle("MQ-PP-014", "les_deux", "mineur",
       "Contraste tactile des passages : bandes fabriquées en relief (épaisseur dessus − sol ≥ 2,5 mm, défaut 3 mm) ; "
       "signalement des traversées de plus de 12 m sans refuge (longueur d'axe du zébra). Unité : zébra.",
       "implemente")
def mq_pp_014(ctx, R):
    for zid, z in zebras(ctx).items():
        p = z["p"]
        ep, Q, _ = epaisseurs(ctx, zid)
        e = float(np.nanmedian(ep)) if len(ep) and np.isfinite(ep).any() else np.nan
        L = float(p.get("axe_m") or np.hypot(*(z["B"] - z["A"])))
        ok = np.isfinite(e) and e >= 0.0025 and L <= 12.0
        R.tester(ok, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(e, 4), seuil="relief ≥ 2,5 mm ; traversée ≤ 12 m",
                 detail=f"épaisseur fabriquée {e * 1000:.1f} mm, traversée de {L:.1f} m", ecart=max(L / 12, 0.0025 / max(e, 1e-4)
                                                                                                       if np.isfinite(e) else 2))


# =========================================================================== flèches
def fleches(ctx):
    return {i: e for i, e in sorted(ctx.marquages.items()) if e["p"]["classe"] == "fleche" and ctx.fabrique_marquage(e["p"])}


@regle("INF-FLE-004", "description", "majeur",
       "Type des flèches de chaque voie entrante = mouvements autorisés (manœuvres 2026) : attendu R1.v-1 TD_TAG, R1.v-2 "
       "TD_TAD, R3.v-1 TD_TAG, R3.v-2 TD_TAD, R6.v2 TAG, R6.v3 TD_TAD, R5 aucune (paramètres de la règle). Voie d'une "
       "flèche : polygone de voie lanes_2026 contenant son centroïde ; voie attendue sans flèche = violation. Unité : flèche "
       "ancrée sur une voie entrante, voie attendue.", "implemente")
def inf_fle_004(ctx, R):
    att = next(r for r in ctx.regles["regles"] if r["id"] == "INF-FLE-004")["parametres"]["attendu_site"]
    trouves = collections.defaultdict(list)
    for i, e in fleches(ctx).items():
        v = voie_de(ctx, centroide(e["poly"][0]))
        if v is None:
            continue
        cle = f"R{v[0]}.v{v[1]}"
        if cle in att or f"R{v[0]}" in att:
            trouves[cle if cle in att else f"R{v[0]}"].append(i)
    for cle, typ in sorted(att.items()):
        ids = trouves.get(cle, [])
        if typ == "aucune":
            for i in ids:
                p = ctx.marquages[i]["p"]
                R.tester(False, entite=i, xy=ctx.marquages[i]["poly"][0][0].mean(0), valeur=p.get("gabarit"),
                         seuil="aucune flèche", detail=f"flèche {p.get('gabarit')} sur {cle} (toutes directions)")
            if not ids:
                R.tester(True)
            continue
        if not ids:
            R.tester(False, entite=cle, valeur=None, seuil=typ, detail=f"aucune flèche {typ} décrite sur {cle}",
                     ecart=2.0)
            continue
        for i in ids:
            p = ctx.marquages[i]["p"]
            ok = p.get("gabarit") == typ
            R.tester(ok, entite=i, xy=ctx.marquages[i]["poly"][0][0].mean(0), valeur=p.get("gabarit"), seuil=typ,
                     detail=f"{cle} : {p.get('gabarit')} au lieu de {typ} (src {p.get('src')}"
                            + (", conflit_norme noté" if p.get("conflit_norme") else "") + ")",
                     ecart=1.5, severite="mineur" if p.get("conflit_norme") else None)


@regle("INF-FLE-006", "description", "majeur",
       "Exclusions d'implantation d'une flèche : pas dans l'aire du carrefour, ni sur un passage piéton ou une "
       "traversée cyclable, ni à moins de 0,50 m d'une ligne transversale peinte, ni entre une LEF et son passage. "
       "Unité : flèche fabriquée.", "implemente")
def inf_fle_006(ctx, R):
    jn = ctx.jonction
    Z = zebras(ctx)
    tc = [np.vstack(e["lignes"]) for e in ctx.marquages.values() if e["p"]["classe"] == "passage"
          and e["p"]["type"] == "traversee_cyclable" and "lignes" in e]
    tr = {i: axe(e) for i, e in lefs(ctx).items() if ctx.fabrique_marquage(e["p"])}
    for i, e in fleches(ctx).items():
        poly = e["poly"][0][0]
        Q = K.densifier(np.vstack([poly, poly[:1]]), 0.1)
        det = []
        dj = K.dans_liste(Q, jn).mean()
        if dj > 0.01:
            det.append(f"{dj * 100:.0f} % dans l'aire du carrefour")
        for zid, z in Z.items():
            if K.dans(Q, z["rect"]).any():
                det.append(f"sur le passage {zid}")
        for c in tc:
            if K.dist_polyligne(Q, c).min() < 1.0:
                det.append("sur une traversée cyclable")
        for lid, P in tr.items():
            d = float(K.dist_polyligne(Q, P).min())
            if d < 0.5:
                det.append(f"à {d:.2f} m de {lid}")
        R.tester(not det, entite=i, xy=poly.mean(0), valeur=len(det), seuil="hors carrefour, passages, ≥ 0,50 m des "
                 "transversales", detail=" ; ".join(det), ecart=1 + len(det))


@regle("MQ-FLE-008", "description", "mineur",
       "Affectation de voies (approches dont les flèches ne sont pas toutes TD) : un panneau C24 (ou Da30) doit être "
       "décrit à moins de 80 m en amont dans le mobilier. Unité : approche affectée.", "implemente")
def mq_fle_008(ctx, R):
    pan = [(f["properties"].get("code"), np.array([f["properties"]["x_local"], f["properties"]["y_local"]]))
           for f in ctx.mobilier if f["properties"]["type"] == "panneau"]
    par = collections.defaultdict(list)
    for i, e in fleches(ctx).items():
        a = e["p"].get("ancrage") or {}
        if a.get("type") == "xodr":
            par[(a["route"], int(np.sign(a["voie"])))].append((i, e["p"].get("gabarit"), e["poly"][0][0].mean(0)))
    for (rid, cote), fl in sorted(par.items()):
        if all(g == "TD" for _, g, _ in fl):
            continue
        c = np.mean([x for _, _, x in fl], axis=0)
        ok = any(code and code.startswith(("C24", "Da30")) and np.hypot(*(xy - c)) < 80 for code, xy in pan)
        R.tester(ok, entite=f"route {rid} côté {cote:+d}", xy=c, valeur=None, seuil="C24 / Da30 présent",
                 detail=f"flèches {sorted(set(g for _, g, _ in fl))} sans panneau C24 décrit")


@regle("MQ-FLE-009", "description", "mineur",
       "Flèches tout droit sur une voie de sortie ou à sens unique : seulement si observées (source gam, ortho, plan). "
       "Unité : flèche TD ancrée sur une route sortante (2, 4) ou hors réseau.", "implemente")
def mq_fle_009(ctx, R):
    for i, e in fleches(ctx).items():
        p = e["p"]
        a = p.get("ancrage") or {}
        if p.get("gabarit") != "TD" or (a.get("type") == "xodr" and a.get("route") not in ("2", "4")):
            continue
        ok = p.get("src") in ("gam", "ortho2022", "plan2025")
        R.tester(ok, entite=i, xy=e["poly"][0][0].mean(0), valeur=p.get("src"), seuil="observée",
                 detail=f"TD sur voie de sortie, src {p.get('src')}")


@regle("MQ-RAB-003", "description", "mineur",
       "Pas de flèche de rabattement sur une voie d'insertion en carrefour : flèches RAB_* dans l'aire du carrefour ou "
       "sur une route de liaison. Unité : flèche de rabattement.", "implemente")
def mq_rab_003(ctx, R):
    for i, e in fleches(ctx).items():
        if not str(e["p"].get("gabarit", "")).startswith("RAB"):
            continue
        dj = K.dans_liste(e["poly"][0][0], ctx.jonction).any()
        R.tester(not dj, entite=i, xy=e["poly"][0][0].mean(0), seuil="hors carrefour", detail="rabattement en carrefour")


@regle("VAL-FLE-001", "les_deux", "majeur",
       "Contrôle des flèches : (a) origine posée (instance de points/symboles.json ou centroïde du maillage drapé) − "
       "pose décrite (gabarit au point de pose, MQ-FLE-006) ; centroïde décrit − centroïde du contour GAM levé "
       "(référence) p95 ≤ 0,10 m ; (b) cap posé − cap décrit ≤ 2° et cap décrit − cap de la voie OpenDRIVE ≤ 2° ; "
       "(c) type = manœuvres (INF-FLE-004) ; (d) IoU de référence ≥ 0,6 (ortho) / 0,8 (plan) quand elle est mesurée ; "
       "(e) 2 flèches par voie affectée (MQ-FLE-003, site) ; (f) profil commun |Δs| ≤ 0,5 m entre voies d'une même "
       "approche. Unités : flèche, voie fléchée.", "implemente")
def val_fle_001(ctx, R):
    fab = fab_marquages(ctx)
    gam = ctx.gam("signalisation_horizontale_lin")
    spec = ctx.spec("marquages_geometrie")["gabarits"]
    d_o, d_ref, d_cap = [], [], []
    par_voie = collections.defaultdict(list)
    for i, e in fleches(ctx).items():
        p = e["p"]
        poly = e["poly"][0][0]
        det, ec = [], 0.0
        f = fab.get(i)
        pose = np.array(p["pose"]["point_l93"]) - np.array(K.O[:2])
        if f is None or not len(f["T"]):
            det.append("non fabriquée")
            ec = 3.0
        else:
            if f["instance"] is not None:
                pt = f["instance"]
                o = np.array(pt["p"][:2])
                cap_f = math.degrees(math.atan2(*quat_mat(pt["q"])[[1, 0], 0]))
            else:
                T = f["T"]
                m = dessus(T)
                o = T[m].reshape(-1, 3)[:, :2].mean(0)
                cap_f = p["pose"]["cap_deg"]
            # (a) l'origine du gabarit est le centroïde décrit moins le centroïde du gabarit tourné : on compare donc
            # les centroïdes des empreintes (fabriquée contre décrite)
            T = f["T"]
            m = dessus(T)
            cf = (T[m][:, :, :2].mean(1) * normales(T[m])[1][:, None]).sum(0) / normales(T[m])[1].sum()
            cd = centroide(e["poly"][0])
            do = float(np.hypot(*(cf - cd)))
            d_o.append(do)
            if do > 0.10:
                det.append(f"centroïde fabriqué à {do:.2f} m du décrit")
                ec = max(ec, do / 0.10)
            dc = K.ecart_angle(cap_f, p["pose"]["cap_deg"])
            d_cap.append(dc)
            if dc > 2.0:
                det.append(f"cap posé à {dc:.1f}° du décrit")
                ec = max(ec, dc / 2.0)
        if p.get("gam"):
            Ls = [K.ligne_local(gam[k]["geometry"])[0] for k in p["gam"] if k < len(gam)]
            if Ls:
                # centroïdes des contours (périmètres densifiés à 1 cm) : levé GAM contre polygone décrit
                cg = np.vstack([K.densifier(L_, 0.01) for L_ in Ls if len(L_) >= 2]).mean(0)
                r_ = e["poly"][0][0]
                cdp = K.densifier(np.vstack([r_, r_[:1]]), 0.01).mean(0)
                dr = float(np.hypot(*(cg - cdp)))
                d_ref.append(dr)
        a = p.get("ancrage") or {}
        if a.get("type") == "xodr":
            cv = cap_voie(ctx, a)
            dv = K.ecart_angle(p["pose"]["cap_deg"], cv)
            if dv > 2.0:
                det.append(f"cap décrit à {dv:.1f}° de la voie {a['route']}/{a['voie']}")
                ec = max(ec, dv / 2.0)
        v_ = voie_de(ctx, centroide(e["poly"][0]))
        if v_ is not None:
            par_voie[(v_[0], v_[1])].append((i, v_[2]))
        iou = p.get("iou_reference")
        if iou is not None:
            lim = 0.8 if p.get("src") == "plan2025" else 0.6
            if iou < lim:
                det.append(f"IoU de référence {iou:.2f} < {lim}")
                ec = max(ec, lim / max(iou, 0.05))
        R.tester(not det, entite=i, xy=poly.mean(0), valeur=r4(max([0.0] + d_o[-1:]), 3), seuil="origine ≤ 0,10, cap ≤ 2°",
                 detail=" ; ".join(det), ecart=max(ec, 1.0))
    R.mesure("a_ecart_centroide_fabrique_m", stats(d_o, (50, 95)))
    R.mesure("a_ecart_centroide_gam_m", stats(d_ref, (50, 95)))
    R.mesure("b_ecart_cap_pose_deg", stats(d_cap, (50, 95)))
    if d_ref and np.percentile(d_ref, 95) > 0.10:
        R.tester(False, entite="flèches levées GAM", valeur=r4(np.percentile(d_ref, 95), 3), seuil="p95 ≤ 0,10 m",
                 detail=f"centroïde décrit − contour GAM p95 {np.percentile(d_ref, 95):.3f} m", ecart=2.0)
    # (e) nombre par voie et (f) profil commun
    att = next(r for r in ctx.regles["regles"] if r["id"] == "INF-FLE-004")["parametres"]["attendu_site"]
    for cle, typ in sorted(att.items()):
        if typ == "aucune" or "." not in cle:
            continue
        rid, v = cle[1:].split(".v")
        fl = sorted(par_voie.get((rid, int(v)), []), key=lambda t: t[1])
        R.tester(len(fl) >= 2, entite=cle, valeur=len(fl), seuil="2 flèches par voie (site)",
                 detail=f"{len(fl)} flèche(s) décrite(s) : {[f[0] for f in fl]}", ecart=2.0 / max(len(fl), 0.5))
    for rid in ("1", "3", "6"):
        # flèche la plus en aval de chaque voie (sens de circulation : s croissant à droite, décroissant à gauche)
        voies = {}
        for (r, v), fl in par_voie.items():
            if r != rid:
                continue
            ss = [s_ for _, s_ in fl]
            voies[v] = max(ss) if v < 0 else min(ss)
        ks = sorted(voies)
        for a_, b_ in zip(ks[:-1], ks[1:]):
            if np.sign(a_) != np.sign(b_):
                continue
            ds = abs(voies[a_] - voies[b_])
            R.tester(ds <= 0.5, entite=f"route {rid} voies {a_}/{b_}", valeur=r4(ds, 2), seuil="|Δs| ≤ 0,5 m",
                     detail=f"dernières flèches des voies voisines décalées de {ds:.2f} m (profil commun)",
                     ecart=ds / 0.5)


# =========================================================================== cycles, stationnement, symboles
def dans_biking(ctx, Q):
    polys = [v["poly"] for v in ctx.voies if v["type"] == "biking"]
    return K.dans_liste(Q, polys)


@regle("MQ-CYC-012", "description", "mineur",
       "Marquage des pistes bidirectionnelles (u = 0,03 m) : lignes dont l'axe est à ≥ 80 % dans une voie OpenDRIVE "
       "biking : largeur 2u = 0,06 m (axe) ou 3u = 0,09 m (rive, ligne jaune Chronovélo) à ±0,01 m ; modulation "
       "continue, T'1 ou T3. Unité : ligne sur piste.", "implemente")
def mq_cyc_012(ctx, R):
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        Q = K.densifier(P, 0.25)
        if dans_biking(ctx, Q).mean() < 0.8:
            continue
        w = float(p.get("largeur_m") or 0.10)
        ok_w = min(abs(w - 0.06), abs(w - 0.09)) <= 0.01 + 1e-6
        ok_m = (p.get("modulation") or "continue") in ("continue", "T'1", "T3", "T3_site")
        R.tester(ok_w and ok_m, entite=i, xy=P[len(P) // 2], valeur=r4(w, 3), seuil="0,06 ou 0,09 m ; continue/T'1/T3",
                 detail=f"ligne de piste {w:.2f} m, {p.get('modulation')}, rôle {p.get('role')}, {p.get('couleur')}",
                 ecart=1 + min(abs(w - 0.06), abs(w - 0.09)) / 0.01)


@regle("MQ-CYC-001", "description", "mineur",
       "Bande cyclable : ligne T3 5u (0,25 / 0,30 m), interrompue dans l'aire du carrefour. Unité : ligne de rôle « bande ».",
       "implemente")
def mq_cyc_001(ctx, R):
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        if p.get("role") != "bande":
            continue
        w = float(p.get("largeur_m") or 0)
        inj = K.dans_liste(points_peints(P, iv), ctx.jonction).sum() * 0.1
        ok = p.get("modulation") in ("T3", "T3_site") and min(abs(w - 0.25), abs(w - 0.30)) <= 0.02 and inj <= 0.5
        R.tester(ok, entite=i, xy=P[len(P) // 2], valeur=r4(w, 3), seuil="T3 5u hors carrefour",
                 detail=f"{p.get('modulation')} {w:.2f} m, {inj:.1f} m dans le carrefour")


@regle("MQ-CHR-001", "description", "mineur",
       "Marques jaunes Chronovélo : posées seulement si observées (src gam / plan / ortho) et sur les gabarits du site : "
       "pavés 0,70 × 0,37 (pas 0,60), barrettes 0,62-0,82 × 0,10-0,18, points Ø 0,20, ligne 0,09 m (±0,02 m). Unité : "
       "marque jaune.", "implemente")
def mq_chr_001(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p.get("couleur") != "jaune" or not ctx.fabrique_marquage(p):
            continue
        det = []
        if p.get("src") not in ("gam", "plan2025", "ortho2022"):
            det.append(f"src {p.get('src')}")
        if p["classe"] == "symbole" and p["type"] == "barre" and p.get("rectangle"):
            L, l = p["rectangle"]["longueur_m"], p["rectangle"]["largeur_m"]
            if not (0.60 <= L <= 0.84 and 0.08 <= l <= 0.20):
                det.append(f"barrette {L:.2f} × {l:.2f} m")
        elif p["classe"] == "symbole" and p["type"] == "point" and p.get("disque"):
            if abs(p["disque"]["diametre_m"] - 0.20) > 0.02:
                det.append(f"point Ø {p['disque']['diametre_m']:.2f} m")
        elif p["classe"] == "ligne":
            w = float(p.get("largeur_m") or 0)
            if abs(w - 0.09) > 0.02:
                det.append(f"ligne jaune {w:.2f} m")
        elif p["classe"] == "passage":
            for fl in p.get("files") or []:
                if abs(fl.get("pas_m", 0.6) - 0.60) > 0.03:
                    det.append(f"pas des pavés {fl.get('pas_m')} m")
        c = e["poly"][0][0].mean(0) if "poly" in e else (np.vstack(e["lignes"]).mean(0) if "lignes" in e else None)
        R.tester(not det, entite=i, xy=c, valeur=None, seuil="gabarits Chronovélo du site", detail=" ; ".join(det))


@regle("MQ-RAL-001", "description", "mineur",
       "Triangles (dents de requin) des ralentisseurs et plateaux : base 0,70 × longueur 2,00 m (IISR) ou gabarit "
       "observé du site (base 0,79-0,81, hauteur 1,89) à ±0,05 m ; contigus (pas ≤ base + 0,15 m). Unité : triangle.",
       "implemente")
def mq_ral_001(ctx, R):
    tri = [(i, e) for i, e in sorted(ctx.marquages.items()) if e["p"]["type"] == "dent_requin"]
    cen = {i: e["poly"][0][0].mean(0) for i, e in tri}
    for i, e in tri:
        t = e["p"].get("triangle") or {}
        b, h = t.get("base_m", 0), t.get("hauteur_m", 0)
        iisr = abs(b - 0.70) <= 0.05 and abs(h - 2.00) <= 0.05
        site = 0.74 <= b <= 0.86 and abs(h - 1.89) <= 0.05
        voisins = [float(np.hypot(*(cen[j] - cen[i]))) for j, _ in tri if j != i]
        pas = min(voisins) if voisins else 0.0
        ok = (iisr or site) and pas <= b + 0.15 + 1e-6
        R.tester(ok, entite=i, xy=cen[i], valeur=r4(b, 3), seuil="0,70 × 2,00 (IISR) ou 0,80 × 1,89 (site)",
                 detail=f"base {b:.2f}, hauteur {h:.2f}, pas au voisin {pas:.2f} m", ecart=1.5)


@regle("MQ-STA-001", "description", "majeur",
       "Aucune place de stationnement (marques T de stationnement) à moins de 5 m d'un passage piéton. Unité : zébra.",
       "partiel", "places non décrites comme entités : seules les marques T et les zones de stationnement marquées sont lues")
def mq_sta_001(ctx, R):
    tm = [e["poly"] for e in ctx.marquages.values() if e["p"]["type"] == "t_stationnement" and "poly" in e]
    for zid, z in zebras(ctx).items():
        d = min([float(K.dist_polys(np.vstack([r for p in t for r in p]), [z["rect"]]).min()) for t in tm], default=np.inf)
        R.tester(d >= 5.0, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(d if np.isfinite(d) else -1, 2),
                 seuil="≥ 5 m", detail=f"marque de stationnement à {d:.1f} m")


@regle("MQ-STA-002", "description", "mineur",
       "Stationnement longitudinal délimité en T'2 2u : trait des marques T de stationnement = 0,10 ou 0,12 m (±0,01). "
       "Unité : marque T.", "partiel", "dimensions des places non décrites")
def mq_sta_002(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["type"] != "t_stationnement":
            continue
        t = (p.get("glyphe") or {}).get("trait_m")
        ok = t is not None and min(abs(t - 0.10), abs(t - 0.12)) <= 0.01 + 1e-6
        R.tester(ok, entite=i, xy=e["poly"][0][0].mean(0), valeur=t, seuil="2u (0,10 / 0,12 m)",
                 detail=f"trait {t} m")


@regle("MQ-STA-004", "description", "mineur",
       "Pictogramme PMR blanc de 0,50 × 0,60 (ou 0,25 × 0,30) sur les limites ou de 1,00 × 1,20 au centre : hauteur du "
       "glyphe décrit 0,30 / 0,60 / 1,20 m à ±10 %. Unité : pictogramme PMR.", "partiel",
       "largeur des places (3,30 m) et part de 2 % non mesurables (places non décrites)")
def mq_sta_004(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["type"] != "pmr":
            continue
        h = (p.get("glyphe") or {}).get("hauteur_m")
        ok = h is not None and any(abs(h - v) <= 0.1 * v for v in (0.30, 0.60, 1.20))
        R.tester(ok, entite=i, xy=e["poly"][0][0].mean(0), valeur=h, seuil="0,30 / 0,60 / 1,20 m",
                 detail=f"pictogramme de {h} m", ecart=min(abs(h - v) / (0.1 * v) for v in (0.3, 0.6, 1.2)) if h else 2)


# =========================================================================== validations des lignes et passages
@regle("VAL-LIG-002", "les_deux", "majeur",
       "Contrôle des lignes fabriquées : (a) largeur fabriquée (2 × p99 de la distance des sommets du dessus à l'axe) = "
       "largeur décrite ±5 mm, largeur décrite dans {2u, 3u, 5u} (0,06-0,30) ±0,02 m ; (b) aire peinte fabriquée / "
       "(largeur × longueur peinte attendue) − 1 ≤ 2 % (phase et modulation appliquées) ; (c) modulation IISR (table) "
       "ou continue ; (d) écart latéral de l'axe décrit au levé GAM (lignes de source GAM) p95 ≤ 0,05 m ; (e) résidu "
       "de phase décrit ≤ 0,10 m. Unité : ligne longitudinale fabriquée.", "implemente")
def val_lig_002(ctx, R):
    fab = fab_marquages(ctx)
    mods = modulations(ctx)
    gam = ctx.gam("signalisation_horizontale_lin")
    largeurs = [0.06, 0.09, 0.10, 0.12, 0.15, 0.18, 0.25, 0.30]
    e_aire, e_larg, e_lat = [], [], []
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        det, ec = [], 0.0
        w = float(p.get("largeur_m") or 0.10)
        if min(abs(w - x) for x in largeurs) > 0.02 + 1e-6:
            det.append(f"largeur décrite {w:.3f} hors {{2u, 3u, 5u}}")
            ec = max(ec, 2.0)
        f = fab.get(i)
        if f is None or not len(f["T"]):
            det.append("ligne non fabriquée")
            ec = max(ec, 3.0)
        else:
            T = f["T"]
            m = dessus(T)
            V = T[m].reshape(-1, 3)[:, :2]
            if not len(V):                                  # aucun triangle « de dessus » (ligne drapée sur une pente
                V = T.reshape(-1, 3)[:, :2]                 # forte) : tous les sommets (robustesse du contrôle)
            d = K.dist_polyligne(V, P)
            wf = 2 * float(np.percentile(d, 99))
            e_larg.append(wf - w)
            if abs(wf - w) > 0.005 + 1e-6:
                det.append(f"largeur fabriquée {wf * 1000:.0f} mm pour {w * 1000:.0f} mm")
                ec = max(ec, abs(wf - w) / 0.005)
            att = w * sum(b - a for a, b in iv)
            emp = aire_projetee(T, np.abs(normales(T)[0][:, 2]) > 0.1)
            r = emp / max(att, 1e-9) - 1.0
            e_aire.append(abs(r))
            if abs(r) > 0.02:
                det.append(f"aire peinte {r * 100:+.1f} % de l'attendu")
                ec = max(ec, abs(r) / 0.02)
        mod = p.get("modulation") or "continue"
        if mod not in mods and mod != "continue":
            det.append(f"modulation {mod} hors table IISR")
            ec = max(ec, 1.0)
        if p.get("src") == "gam" and p.get("gam"):
            Ls = [K.ligne_local(gam[k]["geometry"])[0] for k in p["gam"] if k < len(gam)]
            if Ls:
                dl = np.min([K.dist_polyligne(P, L_) for L_ in Ls], axis=0)
                # l'axe est entre les deux bords levés : on retire la demi-largeur si les bords sont levés
                lat = float(np.percentile(np.abs(dl - (w / 2 if np.median(dl) > w / 4 else 0.0)), 95))
                e_lat.append(lat)
                if lat > 0.05:
                    det.append(f"écart latéral au levé GAM p95 {lat * 100:.1f} cm")
                    ec = max(ec, lat / 0.05)
        rp = (p.get("mesures") or {}).get("residu_phase_max_m")
        if rp is not None and rp > 0.10:
            det.append(f"résidu de phase {rp:.2f} m")
            ec = max(ec, rp / 0.10)
        R.tester(not det, entite=i, xy=P[len(P) // 2], valeur=len(det), seuil="(a)-(e)", detail=" ; ".join(det),
                 ecart=max(ec, 1.0))
    R.mesure("a_largeur_fabriquee_moins_decrite_m", stats(e_larg, (5, 50, 95)))
    R.mesure("b_ecart_relatif_aire", stats(e_aire, (50, 95)))
    R.mesure("d_ecart_lateral_gam_m", stats(e_lat, (50, 95)))


def composantes_triangles(T):
    """Étiquettes de composantes connexes (sommets soudés à 0,01 mm) de triangles."""
    q = np.round(T.reshape(-1, 3) / 1e-5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    V = inv.reshape(-1, 3)
    lab = np.arange(V.max() + 1)
    while True:
        m = lab[V].min(1)
        nouv = lab.copy()
        for k in range(3):
            np.minimum.at(nouv, V[:, k], m)
        nouv = nouv[nouv]
        if np.array_equal(nouv, lab):
            break
        lab = nouv
    _, t = np.unique(lab[V[:, 0]], return_inverse=True)
    return t


@regle("VAL-ZEB-003", "les_deux", "majeur",
       "Contrôle des passages fabriqués (bandes = composantes connexes du dessus de passages.usda) : nombre de bandes = "
       "emplacements décrits − coupures et dans la table IISR selon la largeur roulable ; pas ±0,03 m ; angle ±3° ; "
       "longueur ±0,20 m (sauf découpes décrites) ; axe à ≤ 0,20 m de l'axe décrit ; intervalle d'extrémité aux faces "
       "de bordure = g décrit ±0,10 m. Unité : zébra.", "implemente")
def val_zeb_003(ctx, R):
    fab = fab_marquages(ctx)
    table = ctx.spec("marquages_geometrie")["passages_pietons"]["nombre_bandes"]
    kerbs = [(b, ctx.bordures[b]["P"][:, :2]) for b in sorted(ctx.bordures)]
    for zid, z in zebras(ctx).items():
        p = z["p"]
        A, B = z["A"], z["B"]
        ax = (B - A) / np.linalg.norm(B - A)
        u = np.array([math.cos(math.radians(p["cap_bandes_deg"])), math.sin(math.radians(p["cap_bandes_deg"]))])
        attendu = int(p.get("nb_emplacements") or p["nb_bandes"]) - len(p.get("coupures") or [])
        det, ec = [], 0.0
        f = fab.get(zid)
        if f is None or not len(f["T"]):
            R.tester(False, entite=zid, xy=(A + B) / 2, detail="zébra non fabriqué", seuil="fabriqué", ecart=3)
            continue
        T = f["T"][dessus(f["T"])]
        lab = composantes_triangles(T)
        bandes = []
        for k in range(lab.max() + 1):
            t = T[lab == k]
            Q = t.reshape(-1, 3)[:, :2]
            a = normales(t)[1]
            c = (t[:, :, :2].mean(1) * a[:, None]).sum(0) / a.sum()
            lu = np.ptp(Q @ u)
            C = t[:, :, :2].mean(1)
            cov = ((C - c).T * a) @ (C - c) / a.sum()
            ev, evec = np.linalg.eigh(cov)
            ang = math.degrees(math.acos(min(1.0, abs(float(evec[:, -1] @ u)))))
            if a.sum() > 0.02:
                bandes.append((float((c - A) @ ax), lu, ang, c))
        bandes.sort(key=lambda b: b[0])
        n = len(bandes)
        if n != attendu:
            det.append(f"{n} bandes fabriquées pour {attendu} décrites")
            ec = max(ec, 2.0)
        W = float(p.get("axe_m") or np.linalg.norm(B - A)) + 0.5 + 2 * float(p.get("intervalle_m") or 0.5)
        lignes_t = [t for t in table if t["largeur_roulable_m"][0] <= W < t["largeur_roulable_m"][1]]
        if lignes_t and not (lignes_t[0]["bandes"][0] <= p["nb_bandes"] <= lignes_t[0]["bandes"][1]):
            det.append(f"{p['nb_bandes']} bandes hors table IISR pour {W:.1f} m ({lignes_t[0]['bandes']})")
            ec = max(ec, 1.0)
        if n >= 2:
            pas = np.diff([b[0] for b in bandes])
            pas = pas[pas < 1.5 * p["pas_axe_m"]]
            if len(pas) and np.abs(pas - p["pas_axe_m"]).max() > 0.03:
                det.append(f"pas fabriqué jusqu'à {np.abs(pas - p['pas_axe_m']).max() * 100:.1f} cm du décrit")
                ec = max(ec, np.abs(pas - p["pas_axe_m"]).max() / 0.03)
        if bandes:
            amax = max(b[2] for b in bandes)
            if amax > 3.0:
                det.append(f"angle de bande {amax:.1f}°")
                ec = max(ec, amax / 3.0)
            if not p.get("decoupes"):
                lmax = max(abs(b[1] - p["longueur_bande_m"]) for b in bandes)
                if lmax > 0.20:
                    det.append(f"longueur de bande à {lmax:.2f} m de la décrite")
                    ec = max(ec, lmax / 0.2)
            cs = np.array([b[3] for b in bandes])
            dax = float(K.dist_polyligne(cs, np.vstack([A - 5 * ax, B + 5 * ax])).max())
            if dax > 0.20:
                det.append(f"bandes à {dax:.2f} m de l'axe")
                ec = max(ec, dax / 0.2)
            # intervalle d'extrémité aux faces de bordure (le long de l'axe)
            g = float(p.get("intervalle_m") or 0.5)
            for bout, cb in (("début", cs[0]), ("fin", cs[-1])):
                sgn = -1 if bout == "début" else 1
                Q = cb + sgn * ax * np.linspace(0.25, 3.0, 56)[:, None]
                dk = [(float(K.dist_polyligne(Q, P_).min()), b_) for b_, P_ in kerbs]
                dmin, bk = min(dk)
                if dmin < 0.03:
                    P_ = dict(kerbs)[bk]
                    dd = K.dist_polyligne(Q, P_)
                    kk = int(np.argmin(dd))
                    gap = 0.25 + kk * (2.75 / 55) - 0.25
                    if abs(gap - g) > 0.10:
                        det.append(f"intervalle d'extrémité ({bout}) {gap:.2f} m pour g = {g:.2f} m ({bk})")
                        ec = max(ec, abs(gap - g) / 0.10)
        R.tester(not det, entite=zid, xy=(A + B) / 2, valeur=n, seuil="bandes, pas ±0,03, angle ±3°, longueur ±0,20, "
                 "axe ≤ 0,20, g ±0,10", detail=" ; ".join(det), ecart=max(ec, 1.0))


# =========================================================================== MQ-DET-010
@regle("MQ-DET-010", "fabrication", "majeur",
       "Artefacts sur la scène fabriquée : (a) partie peinte d'une ligne longitudinale dans un zébra ; (b) recouvrement "
       "entre empreintes de deux marques (> 0,01 m², hors figurines et damiers prévus) ; (c) flèche hors des voies "
       "roulables (> 1 % de l'empreinte) ; (d) dessus de marque posé sur une bordure, un trottoir, un espace vert ou un "
       "îlot (> 0,02 m², sauf lignes jaunes sur bordure). Unité : marque fabriquée.", "implemente")
def mq_det_010(ctx, R):
    fab = fab_marquages(ctx)
    Z = zebras(ctx)
    from ctl_sol import grille
    G = grille(ctx)
    roul = voies_roulables(ctx)
    ids = sorted(i for i in fab if len(fab[i]["T"]))
    boites = {}
    reqs = {}
    for i in ids:
        T = fab[i]["T"]
        m = np.abs(normales(T)[0][:, 2]) > 0.1
        boites[i] = (T[m][:, :, :2].reshape(-1, 2).min(0), T[m][:, :, :2].reshape(-1, 2).max(0))
    for i in ids:
        T = fab[i]["T"]
        p = ctx.marquages.get(i, {}).get("p", {})
        mt = dessus(T)
        C = T[mt][:, :, :2].mean(1)
        a = normales(T[mt])[1]
        det, ec = [], 0.0
        if p.get("classe") == "ligne":
            for zid, z in Z.items():
                dz = K.dans(C, z["rect"])
                if dz.any():
                    det.append(f"(a) {a[dz].sum():.2f} m² peints dans {zid}")
                    ec = max(ec, 2 + a[dz].sum())
        lo, hi = boites[i]
        for j in ids:
            if j <= i:
                continue
            lo2, hi2 = boites[j]
            if lo[0] > hi2[0] or lo2[0] > hi[0] or lo[1] > hi2[1] or lo2[1] > hi[1]:
                continue
            pj = ctx.marquages.get(j, {}).get("p", {})
            if {p.get("type"), pj.get("type")} & {"velo", "chevron"} and "zebra" in {p.get("type"), pj.get("type")}:
                continue
            if j not in reqs:
                Tj = fab[j]["T"]
                reqs[j] = K.RequeteMaillage(Tj[dessus(Tj)], 0.25)
            z_, _, _ = reqs[j].requete(C)
            sup = np.isfinite(z_)
            if a[sup].sum() > 0.01:
                det.append(f"(b) recouvre {j} sur {a[sup].sum():.2f} m²")
                ec = max(ec, 1 + a[sup].sum() * 10)
        if p.get("classe") == "fleche":
            hors = ~K.dans_liste(C, roul)
            if a[hors].sum() > 0.01 * a.sum():
                det.append(f"(c) {a[hors].sum() / a.sum() * 100:.0f} % de la flèche hors des voies roulables")
                ec = max(ec, 1 + a[hors].sum())
        ii = np.clip(np.rint((C[:, 0] - K.X0) / K.PAS_GRILLE).astype(int), 0, K.N_GRILLE - 1)
        jj = np.clip(np.rint((C[:, 1] - K.Y0) / K.PAS_GRILLE).astype(int), 0, K.N_GRILLE - 1)
        cl = G["cl"][jj, ii]
        mal = ~np.isin(cl, list(SOL_ADMIS))
        sev = None
        if a[mal].sum() > 0.02 and not (p.get("couleur") == "jaune" and p.get("sur_bordure")):
            top = collections.Counter(cl[mal].tolist()).most_common(2)
            det.append(f"(d) {a[mal].sum():.2f} m² sur {', '.join(f'{c}' for c, _ in top)}"
                       + (" (support_sol accepté par la description)" if p.get("support_sol") else ""))
            ec = max(ec, 1 + a[mal].sum() * 5)
            if p.get("support_sol") and len(det) == 1:
                sev = "mineur"
        R.tester(not det, entite=i, xy=C.mean(0) if len(C) else None, valeur=len(det), seuil="(a)-(d)",
                 detail=" ; ".join(det), ecart=max(ec, 1.0), severite=sev)


# =========================================================================== TQ-MQG, TQ-VAL-002, TQ-MQR-005
E_TOP = {"ligne": 0.002}         # TQ-MQG-002 : lignes longitudinales en peinture ; le reste en enduit 3 mm


@regle("TQ-VAL-002", "fabrication", "majeur",
       "Marques en volume : (1) écart d'aire de l'empreinte fabriquée aux paramètres ≤ 0,5 % (lignes : largeur × "
       "longueur peinte ; zébras : bandes ; symboles : aire du polygone décrit, ≤ 2 % toléré pour les contours levés) ; "
       "(2) bas de jupe ≤ sol − 1,5 mm ; (3) dessus − sol constant à ±0,3 mm (p95 de l'écart à la médiane) ; (4) 0 "
       "sommet de dessus hors sol ; (5) angle minimal des triangles ≥ 15°. Unité : marque fabriquée.", "partiel",
       "0 avertissement LogStaticMesh : à mesurer à l'import UE")
def tq_val_002(ctx, R):
    fab = fab_marquages(ctx)
    mods = modulations(ctx)
    ecarts_aire, drap, jupes = [], [], []
    crit = collections.Counter()
    for i in sorted(fab):
        f = fab[i]
        T = f["T"]
        if not len(T):
            continue
        e = ctx.marquages.get(i)
        p = e["p"] if e else {}
        det, ec = [], 0.0
        emp = aire_projetee(T, np.abs(normales(T)[0][:, 2]) > 0.1)
        att, tol = None, 0.005
        if p.get("classe") == "ligne" and "lignes" in e:
            P = axe(e)
            att = float(p.get("largeur_m") or 0.1) * sum(b - a for a, b in intervalles_peints(p, longueur(P), mods))
        elif p.get("type") == "zebra":
            att = float(p["longueur_bande_m"]) * float(p["largeur_bande_m"]) * (
                int(p.get("nb_emplacements") or p["nb_bandes"]) - len(p.get("coupures") or []))
            tol = 0.02 if p.get("decoupes") else 0.005
        elif e is not None and "poly" in e:
            att = sum(K.aire_poly(pp) for pp in e["poly"])
            tol = 0.02
        if att:
            r = emp / att - 1
            ecarts_aire.append(abs(r))
            if abs(r) > tol:
                det.append(f"(1) aire {r * 100:+.2f} %")
                ec = max(ec, abs(r) / tol)
        ep, Q, zb = epaisseurs(ctx, i)
        ok = np.isfinite(ep)
        if (~ok).any():
            det.append(f"(4) {int((~ok).sum())} sommet(s) de dessus hors sol")
            ec = max(ec, 3.0)
        if ok.sum() > 3:
            med = float(np.median(ep[ok]))
            dev = float(np.percentile(np.abs(ep[ok] - med), 95))
            drap.append(dev)
            if dev > 0.0003:
                det.append(f"(3) dessus − sol varie de ±{dev * 1000:.1f} mm (p95)")
                ec = max(ec, dev / 0.0003)
        if len(zb):
            jmax = float(np.nanmax(zb)) if np.isfinite(zb).any() else -1
            jupes.append(jmax)
            if jmax > -0.0015:
                det.append(f"(2) bas de jupe à {jmax * 1000:+.1f} mm du sol")
                ec = max(ec, 1.5)
        ang = angles_min(T[dessus(T)])
        if len(ang) and ang.min() < 15.0:
            det.append(f"(5) angle min {ang.min():.1f}°")
            ec = max(ec, 15.0 / max(ang.min(), 0.5))
        for d_ in det:
            crit[d_[:3]] += 1
        R.tester(not det, entite=i, xy=T[:, :, :2].reshape(-1, 2).mean(0), valeur=len(det), seuil="(1)-(5)",
                 detail=" ; ".join(det), ecart=max(ec, 1.0), severite="mineur" if all(d.startswith(("(1)", "(5)"))
                                                                                  for d in det) else None)
    R.mesure("marques_en_defaut_par_critere", dict(sorted(crit.items())))
    R.mesure("1_ecart_aire_relatif", stats(ecarts_aire, (50, 95)))
    R.mesure("3_drape_p95_m", stats(drap, (50, 95)))
    R.mesure("2_bas_de_jupe_moins_sol_m", stats(jupes, (50, 95)))


@regle("TQ-MQG-004", "fabrication", "mineur",
       "Triangulation propre des marques : angle minimal des triangles du dessus ≥ 15° (tous) et p5 ≥ 20°. Unité : "
       "marque fabriquée.", "implemente")
def tq_mqg_004(ctx, R):
    fab = fab_marquages(ctx)
    tous = []
    for i in sorted(fab):
        T = fab[i]["T"]
        if not len(T):
            continue
        a = angles_min(T[dessus(T)])
        if not len(a):
            continue
        tous.append(a)
        ok = a.min() >= 15.0 and np.percentile(a, 5) >= 20.0
        R.tester(ok, entite=i, xy=T[:, :, :2].reshape(-1, 2).mean(0), valeur=r4(a.min(), 1), seuil="min ≥ 15°, p5 ≥ 20°",
                 detail=f"angle min {a.min():.1f}°, p5 {np.percentile(a, 5):.1f}° ({len(a)} triangles)",
                 ecart=15.0 / max(a.min(), 0.5))
    if tous:
        R.mesure("angle_min_deg", stats(np.concatenate(tous), (1, 5, 50)))


@regle("TQ-MQG-005", "fabrication", "bloquant",
       "Marques drapées uniquement sur le sol v2 : chaque sommet du dessus a du sol fabriqué sous lui et dessus − sol "
       "est dans [0,5 ; 6] mm (aucune marque hors sol, enterrée ou flottante). Unité : marque fabriquée.",
       "implemente")
def tq_mqg_005(ctx, R):
    fab = fab_marquages(ctx)
    for i in sorted(fab):
        if not len(fab[i]["T"]):
            continue
        ep, Q, _ = epaisseurs(ctx, i)
        hors = ~np.isfinite(ep)
        mal = np.isfinite(ep) & ((ep < 0.0005) | (ep > 0.006))
        n = int(hors.sum() + mal.sum())
        k = int(np.argmax(hors | mal)) if n else 0
        R.tester(n == 0, entite=i, xy=Q[k] if len(Q) else None, valeur=r4(ep[k] if np.isfinite(ep[k]) else -1, 4)
                 if len(ep) else None, seuil="dessus − sol dans [0,5 ; 6] mm",
                 detail=f"{int(hors.sum())} sommet(s) hors sol, {int(mal.sum())} enterré(s) ou flottant(s) "
                        f"(min {np.nanmin(ep) * 1000:.1f}, max {np.nanmax(ep) * 1000:.1f} mm)" if np.isfinite(ep).any()
                 else "aucun sol sous la marque", ecart=1 + n / 10)


@regle("TQ-MQG-006", "fabrication", "majeur",
       "Symboles posés en prototypes rigides (points/symboles.json) seulement si le sol est plan à 1 mm près sous "
       "l'emprise + 0,25 m : résidu max du plan ajusté sur le sol fabriqué (grille de 5 cm). Unité : instance.",
       "implemente")
def tq_mqg_006(ctx, R):
    for pt in ctx.points("symboles")["points"]:
        e = ctx.marquages.get(pt["id"])
        if e is None or "poly" not in e:
            continue
        poly = e["poly"][0][0]
        lo, hi = poly.min(0) - 0.25, poly.max(0) + 0.25
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0], 0.05), np.arange(lo[1], hi[1], 0.05))
        Q = np.c_[gx.ravel(), gy.ravel()]
        d = K.dist_polys(Q, [[poly]])
        Q = Q[K.dans(Q, [poly]) | (d <= 0.25)]
        z = ctx.requete("sol", 0.5).requete(Q)[0]
        ok = np.isfinite(z)
        if ok.sum() < 6:
            continue
        A = np.c_[Q[ok], np.ones(ok.sum())]
        c, *_ = np.linalg.lstsq(A, z[ok], rcond=None)
        res = float(np.abs(A @ c - z[ok]).max())
        R.tester(res <= 0.001, entite=pt["id"], xy=pt["p"], valeur=r4(res, 4), seuil="≤ 0,001 m",
                 detail=f"{pt['asset']} posé rigide sur un sol non plan (résidu {res * 1000:.1f} mm ; HDA "
                        f"{pt['x'].get('residu_plan_m')} m)", ecart=res / 0.001)


@regle("TQ-MQG-011", "fabrication", "mineur",
       "Épaisseur fabriquée des lignes longitudinales (médiane de dessus − sol) = height du roadMark OpenDRIVE "
       "(0,002 m) à 0,1 mm près (TQ-MQG-002 : peinture 2 mm). Unité : ligne longitudinale fabriquée.", "implemente")
def tq_mqg_011(ctx, R):
    for i, (P, iv, p) in lignes_peintes(ctx).items():
        ep, Q, _ = epaisseurs(ctx, i)
        if not np.isfinite(ep).any():
            continue
        e = float(np.nanmedian(ep))
        R.tester(abs(e - 0.002) <= 0.0001, entite=i, xy=P[len(P) // 2], valeur=r4(e, 4), seuil="0,002 ± 0,0001 m",
                 detail=f"épaisseur fabriquée {e * 1000:.2f} mm (roadMark height 2 mm)", ecart=abs(e - 0.002) / 0.0001)


@regle("TQ-MQG-014", "fabrication", "majeur",
       "Aucune marque sur une bordure ou un caniveau (hors ligne jaune sur bordure) : aire du dessus des marques au-dessus "
       "de l'emprise des bordures (surfaces emprise_bordure) et de la bande de caniveau CS2 (0,25 m devant la face) "
       "≤ 0,005 m². Unité : marque fabriquée.", "implemente")
def tq_mqg_014(ctx, R):
    fab = fab_marquages(ctx)
    from ctl_sol import grille
    G = grille(ctx)
    can = [(b, ctx.bordures[b]["P"][:, :2]) for b in sorted(ctx.bordures) if ctx.bordures[b]["p"].get("caniveau")]
    canA = np.vstack([P[:-1] for _, P in can]) if can else np.zeros((0, 2))
    canB = np.vstack([P[1:] for _, P in can]) if can else np.zeros((0, 2))
    canN = np.vstack([np.c_[-(P[1:] - P[:-1])[:, 1], (P[1:] - P[:-1])[:, 0]] /
                      np.maximum(np.hypot(*(P[1:] - P[:-1]).T), 1e-9)[:, None] for _, P in can]) if can else np.zeros((0, 2))
    for i in sorted(fab):
        T = fab[i]["T"]
        if not len(T):
            continue
        p = ctx.marquages.get(i, {}).get("p", {})
        mt = dessus(T)
        C = T[mt][:, :, :2].mean(1)
        a = normales(T[mt])[1]
        ii = np.clip(np.rint((C[:, 0] - K.X0) / K.PAS_GRILLE).astype(int), 0, K.N_GRILLE - 1)
        jj = np.clip(np.rint((C[:, 1] - K.Y0) / K.PAS_GRILLE).astype(int), 0, K.N_GRILLE - 1)
        sur_b = G["cl"][jj, ii] == "emprise_bordure"
        sur_c = np.zeros(len(C), bool)
        if len(canA):
            d, js, proj = K.C.distance_segments(C, canA, canB)
            cote = np.einsum("ij,ij->i", C - proj, canN[js])
            sur_c = (d <= 0.25) & (cote < 0)
        a_b, a_c = float(a[sur_b].sum()), float(a[sur_c & ~sur_b].sum())
        exc = p.get("couleur") == "jaune" and p.get("sur_bordure")
        ok = exc or (a_b + a_c) <= 0.005
        R.tester(ok, entite=i, xy=C[sur_b | sur_c].mean(0) if (sur_b | sur_c).any() else C.mean(0),
                 valeur=r4(a_b + a_c, 3), seuil="≤ 0,005 m²", detail=f"{a_b:.3f} m² sur bordure, {a_c:.3f} m² sur "
                 "caniveau", ecart=1 + (a_b + a_c) / 0.005 / 10)


@regle("TQ-MQR-005", "fabrication", "majeur",
       "Anti z-fighting : épaisseur minimale dessus − sol de chaque marque ≥ max(1,5 mm ; 2 × 0,3125 mm + écart de "
       "drapé p95). Unité : marque fabriquée.", "implemente")
def tq_mqr_005(ctx, R):
    fab = fab_marquages(ctx)
    for i in sorted(fab):
        if not len(fab[i]["T"]):
            continue
        ep, Q, _ = epaisseurs(ctx, i)
        ok_ = np.isfinite(ep)
        if ok_.sum() < 3:
            continue
        e = ep[ok_]
        med = float(np.median(e))
        dev = float(np.percentile(np.abs(e - med), 95))
        k = int(np.argmin(e))
        # e_top ≥ max(1,5 mm ; 2 × 0,3125 mm + écart de drapé) : épaisseur minimale et écart de drapé bornés
        ok = e.min() >= 0.0015 and med - 2 * 0.0003125 >= dev
        R.tester(ok, entite=i, xy=Q[ok_][k], valeur=r4(e.min(), 4), seuil="min ≥ 1,5 mm ; drapé p95 ≤ e − 0,63 mm",
                 detail=f"épaisseur min {e.min() * 1000:.2f} mm, médiane {med * 1000:.2f} mm, écart de drapé p95 "
                        f"{dev * 1000:.2f} mm", ecart=max(0.0015 / max(e.min(), 1e-4) if e.min() > 0 else 10.0,
                                                          dev / max(med - 0.000625, 1e-4)))


@regle("TQ-MQG-001", "description", "majeur",
       "Aucun contour issu d'un raster pour une marque réglementaire : entités drapeau contour_raster_v1, et contours "
       "décrits en marches d'escalier (marquages_commun.escalier). Unité : marque à contour polygonal.", "implemente")
def tq_mqg_001(ctx, R):
    import marquages_commun as MC
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if "poly" not in e or not ctx.fabrique_marquage(p):
            continue
        esc = sum(1 for pp in e["poly"] for r in pp if MC.escalier(r))
        ok = not p.get("contour_raster_v1") and esc == 0
        R.tester(ok, entite=i, xy=e["poly"][0][0].mean(0), valeur=esc, seuil="aucun contour raster",
                 detail=("contour raster v1 ; " if p.get("contour_raster_v1") else "") + f"{esc} anneau(x) en escalier "
                        f"(src {p.get('src')}, {p['classe']}/{p['type']})", ecart=2.0)


@regle("TQ-MQG-008", "fabrication", "info",
       "Regroupement des marques en components USD par (tuile de 50 m, classe sémantique, matériau) nommés "
       "MQ_<classe>_<i>_<j>_<materiau>, < 500 000 triangles : lecture des components des 4 couches de marquage. "
       "Unité : couche.", "implemente")
def tq_mqg_008(ctx, R):
    for couche in ("marquages_lignes", "passages", "symboles", "zones"):
        m = ctx.cache["couches"].get(couche, {})
        comps = sorted({p["composant"] for p in m.get("prims", [])})
        bons = [c for c in comps if c.split("/")[-1].startswith("MQ_")]
        tri = max([p["triangles"] for p in m.get("prims", [])], default=0)
        R.tester(len(bons) == len(comps) and tri < 500000, entite=couche, valeur=len(comps),
                 seuil="components MQ_<classe>_<i>_<j>_<mat>", detail=f"{len(comps)} components par entité "
                 f"({len(bons)} au format MQ_*) ; max {tri} triangles par mesh", ecart=1.0)


@regle("TQ-REF-002", "fabrication", "info",
       "Marques en maillages séparés de la route (pratique CARLA / RoadRunner) : aucune peinture dans sol.usdc et aucun "
       "matériau de sol dans les couches de marquage. Unité : couche.", "partiel",
       "classement /Game/PJ/Marquages/<classe>/ et collisions : côté UE")
def tq_ref_002(ctx, R):
    sol = set(map(str, ctx.fab_couche("sol")["mats"]))
    R.tester(not any(m.startswith("PJ_Peinture") for m in sol), entite="sol.usdc", detail="peinture dans le sol",
             seuil="séparé")
    for couche in ("marquages_lignes", "passages", "symboles", "zones"):
        mats = set(map(str, ctx.fab_couche(couche)["mats"]))
        R.tester(all(m.startswith("PJ_Peinture") for m in mats), entite=couche, valeur=sorted(mats)[:4],
                 seuil="peinture seulement", detail=f"matériaux {sorted(mats)}")


@regle("MQ-RAB-002", "description", "mineur",
       "Rabattement : la voie supprimée est la plus à gauche, les flèches de rabattement (RAB_D / RAB_G) sont dans l'axe "
       "de la voie supprimée. Unité : flèche de rabattement (aucune décrite sur le site).", "implemente")
def mq_rab_002(ctx, R):
    for i, e in fleches(ctx).items():
        g = str(e["p"].get("gabarit", ""))
        if not g.startswith("RAB"):
            continue
        v = voie_de(ctx, centroide(e["poly"][0]))
        R.tester(v is not None, entite=i, xy=centroide(e["poly"][0]), valeur=g, seuil="dans une voie",
                 detail="flèche de rabattement hors voie")


@regle("MQ-CYC-010", "description", "mineur",
       "La figurine vélo encadrée ne signale que l'entrée d'une piste ou d'une bande : figurines décrites avec un cadre "
       "(glyphe encadré) à plus de 15 m d'une extrémité de voie biking. Unité : figurine encadrée.", "implemente")
def mq_cyc_010(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["type"] != "velo" or not (p.get("glyphe") or {}).get("cadre"):
            continue
        R.tester(False, entite=i, detail="figurine encadrée à contrôler (entrée de piste)", seuil="entrée seulement")
