"""Contrôles du sol, des bordures, des abaissés et des cheminements (GA-*, TQ-SOL-*, TQ-BOR-*, VAL-SOL-009,
VAL-KRB-005) sur la description (bordures, surfaces, nivellement) et sur la fabrication (sol.usdc, bordures.usdc,
caniveaux.usda, ilots.usda, points/*.json).

Grille de contrôle : celle du nivellement (0,10 m, local [-150, 150]²). Le sol fabriqué y est échantillonné par
requête verticale exacte sur ses triangles (ctl_commun.RequeteMaillage) ; les classes de surface par
rasterisation des polygones de la description.
"""
import collections
import math
import re

import numpy as np

import ctl_commun as K
from ctl_commun import Resultat, regle, r4, stats

PAS = K.PAS_GRILLE
MEUBLES = {"gravillons_ilot", "brf_bois_concasse", "brf_bois_gris", "galets_20_40", "gravier_concasse_6_10",
           "paillage_mineral"}


# =========================================================================== outils locaux
def grille(ctx):
    """Champs partagés : Z fabriqué, classes, régions, masques ; mémorisés."""
    def f():
        Z, NB, ZM = ctx.sol_grille
        cl = ctx.classe_noeuds()
        ids, R = ctx.raster_surfaces
        g = K.grille_xy()
        sous = np.array([ctx.surfaces[s]["p"].get("sous_classe") or "" for s in ids] + [""])
        souscl = sous[np.where(R >= 0, R, len(ids))]
        ped = np.isin(cl, K.PIETON) & np.isfinite(Z)
        reg = np.load(ctx.dbase / "nivellement_grille.npz")["r0"]
        return {"Z": Z.astype(np.float64), "NB": NB, "ZM": ZM, "cl": cl, "R": R, "ids": ids, "g": g, "ped": ped,
                "sous": souscl, "reg": reg}
    return ctx._m("sol:grille", f)


def pentes(ctx, k):
    """Pentes (gx, gy) du sol fabriqué sur une base de 2k nœuds, valides si les deux extrémités sont dans la même
    surface ou deux surfaces piétonnes de la même région de nivellement."""
    def f():
        G = grille(ctx)
        Z, R = G["Z"], G["R"]
        reg = np.load(ctx.dbase / "nivellement_grille.npz")["r0"]
        out = []
        for di, dj in ((k, 0), (0, k)):
            za, zb = K.decaler(Z, -di, -dj, np.nan), K.decaler(Z, di, dj, np.nan)
            ra, rb = K.decaler(reg, -di, -dj, -9), K.decaler(reg, di, dj, -9)
            pa, pb = K.decaler(G["ped"], -di, -dj, False), K.decaler(G["ped"], di, dj, False)
            Ra, Rb = K.decaler(R, -di, -dj, -9), K.decaler(R, di, dj, -9)
            ok = (ra == rb) & (ra >= 0) & (((pa & pb) | (Ra == Rb)) & (Ra >= 0))
            g = np.where(ok, (za - zb) / (2 * k * PAS), np.nan)
            out.append(g)
        return out
    return ctx._m(f"sol:pentes:{k}", f)


def echantillons(ctx, bid, pas=0.5, marge=0.0):
    """Abscisses, points, normale gauche (côté haut) et tangente le long de l'arête avant d'une bordure."""
    b = ctx.bordures[bid]
    P, S = b["P"][:, :2], b["s"]
    L = float(S[-1])
    if L <= 2 * marge + 1e-6:
        s = np.array([L / 2])
    else:
        n = max(1, int(math.ceil((L - 2 * marge) / pas)))
        s = np.linspace(marge, L - marge, n + 1)
    k = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(S) - 2)
    t = (s - S[k]) / np.maximum(S[k + 1] - S[k], 1e-12)
    xy = P[k] + (P[k + 1] - P[k]) * t[:, None]
    tg = P[k + 1] - P[k]
    tg /= np.maximum(np.hypot(*tg.T), 1e-12)[:, None]
    return s, xy, np.c_[-tg[:, 1], tg[:, 0]], tg


def vue_a(p, s):
    """Vue décrite aux abscisses s (intervalles, chartières linéaires)."""
    s = np.atleast_1d(s)
    v = np.full(len(s), np.nan)
    for it in p["intervalles"]:
        m = (s >= it["s0"] - 1e-9) & (s <= it["s1"] + 1e-9)
        v0, v1 = it["vue_m"], it.get("vue_m_fin", it["vue_m"])
        t = (s[m] - it["s0"]) / max(it["s1"] - it["s0"], 1e-9)
        v[m] = v0 + (v1 - v0) * t
    return v


def dans_abaisse(p, s, marge=0.0):
    m = np.zeros(len(np.atleast_1d(s)), bool)
    for a in p["abaisses"]:
        lo = min([a["s0"]] + [r["s0"] for r in a.get("raccords", [])])
        hi = max([a["s1"]] + [r["s1"] for r in a.get("raccords", [])])
        m |= (s >= lo - marge) & (s <= hi + marge)
    return m


def largeur_base(p, s):
    import sol_geometrie as SG
    return SG.largeur_le_long(p["intervalles"], s)


def cotes(ctx, bid):
    d = ctx.cote_bordures.get(bid, {"avant": {}, "arriere": {}})
    return set(d["avant"].values()), set(d["arriere"].values())


def classes_cotes(ctx, bid, xy, nrm, s):
    """Classe de surface à 0,30 m devant la face (côté bas) et à largeur + 0,30 m derrière (côté haut)."""
    w = largeur_base(ctx.bordures[bid]["p"], s)
    _, cb = region_en(ctx, xy - 0.30 * nrm)
    _, ch = region_en(ctx, xy + (w + 0.30)[:, None] * nrm)
    return cb, ch


def dessus_bordure(ctx, bid, xy, nrm, tg, w):
    """Dessus du maillage de bordure fabriqué : maximum sur la largeur (u = 0,03 m à base − 0,01 m) et sur ±2 cm le
    long de la bordure (joints évités)."""
    bor = ctx.fab_couche("bordures")
    ents = ctx.fab_entites("bordures")
    e = bid.replace("-", "_")
    if e not in ents:
        return np.full(len(xy), np.nan)
    rq = ctx._m("rq_bord:" + bid, lambda: K.RequeteMaillage(bor["T"][ents[e]], 0.25))
    zs = []
    for f_ in (0.0, 0.33, 0.66, 1.0):
        u = 0.03 + f_ * np.maximum(w - 0.04, 0.0)
        for d in (-0.02, 0.0, 0.02):
            zs.append(rq.requete(xy + u[:, None] * nrm + d * tg)[0])
    return np.fmax.reduce(zs)


def requete_sol(ctx, Q):
    z, _, _ = ctx.requete("sol", 0.5).requete(Q)
    return z


def region_en(ctx, Q):
    """Région de nivellement et classe de surface au nœud le plus proche de chaque point."""
    G = grille(ctx)
    Q = np.atleast_2d(Q)
    i = np.clip(np.rint((Q[:, 0] - K.X0) / PAS).astype(int), 0, K.N_GRILLE - 1)
    j = np.clip(np.rint((Q[:, 1] - K.Y0) / PAS).astype(int), 0, K.N_GRILLE - 1)
    return G["reg"][j, i], G["cl"][j, i]


def regions_bordure(ctx, bid):
    b = ctx.niv.bordures.get(bid, {})
    return b.get("region_basse"), b.get("region_haute")


def tri_angles(T):
    a, b, c = T[:, 0], T[:, 1], T[:, 2]

    def ang(u, v):
        cu = np.einsum("ij,ij->i", u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-15)
        return np.degrees(np.arccos(np.clip(cu, -1, 1)))
    return np.minimum(np.minimum(ang(b - a, c - a), ang(a - b, c - b)), ang(a - c, b - c))


def grappes_noeuds(ctx, masque, rayon=0.3, n_max=None):
    """Grappes de nœuds d'un masque : [(xy centre, aire m², nb nœuds, surfaces majoritaires, (j, i))]."""
    G = grille(ctx)
    jj, ii = np.nonzero(masque)
    if not len(jj):
        return []
    Q = np.c_[G["g"][ii], G["g"][jj]]
    lab = K.grappes(Q, rayon)
    out = []
    for k in range(lab.max() + 1):
        s = lab == k
        sids = collections.Counter(G["R"][jj[s], ii[s]].tolist())
        surf = [G["ids"][a] for a, _ in sids.most_common(3) if a >= 0]
        out.append((Q[s].mean(0), s.sum() * PAS * PAS, int(s.sum()), surf, (jj[s], ii[s])))
    out.sort(key=lambda t: (-t[2], round(float(t[0][0]), 2), round(float(t[0][1]), 2)))
    return out[:n_max] if n_max else out


# =========================================================================== TQ-SOL-009 étanchéité
@regle("TQ-SOL-009", "fabrication", "bloquant",
       "Sol fabriqué (sol.usdc) soudé à 0,01 mm : arêtes non manifold, triangles doubles ou d'aire < 1e-6 m², angle "
       "minimal (p1 ≥ 20°) ; trous : nœuds de la grille de 0,10 m couverts par une surface décrite mais par aucun "
       "triangle de sol, d'îlot, de caniveau ou de bordure ; recouvrements : nœud contenu strictement dans deux "
       "triangles de sol (hors BEV), quel que soit l'écart (mesure séparée au-delà de 3 mm). Unité testée : tuile de sol.", "partiel",
       "auto-intersections non recherchées ; coutures contrôlées par TQ-SOL-008")
def tq_sol_009(ctx, R):
    sol = ctx.fab_couche("sol")
    T = sol["T"].astype(np.float64)
    q = np.round(T.reshape(-1, 3) / 1e-5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    V = inv.reshape(-1, 3)
    e = np.sort(np.concatenate([V[:, [0, 1]], V[:, [1, 2]], V[:, [2, 0]]]), axis=1)
    ue, cnt = np.unique(e, axis=0, return_counts=True)
    tri_ids = np.sort(V, axis=1)
    _, ctri = np.unique(tri_ids, axis=0, return_counts=True)
    ab = T[:, 1] - T[:, 0]
    ac = T[:, 2] - T[:, 0]
    aire = 0.5 * np.linalg.norm(np.cross(ab, ac), axis=1)
    ang = tri_angles(T)
    nm = int((cnt > 2).sum())
    R.mesure("triangles", int(len(T)))
    R.mesure("aretes_non_manifold", nm)
    R.mesure("triangles_doubles", int((ctri > 1).sum()))
    R.mesure("triangles_aire_inf_1e-6_m2", int((aire < 1e-6).sum()))
    R.mesure("angle_min_deg", {"p1": r4(np.percentile(ang, 1), 2), "p5": r4(np.percentile(ang, 5), 2),
                               "part_inf_20": r4((ang < 20).mean(), 4)})
    # trous et recouvrements sur la grille
    G = grille(ctx)
    Z, NB, ZM = G["Z"], G["NB"], G["ZM"]
    site = G["R"] >= 0
    trous = site & np.isnan(Z)
    jj, ii = np.nonzero(trous)
    Q = np.c_[G["g"][ii], G["g"][jj]]
    for nom in ("ilots", "caniveaux", "bordures"):
        if not len(Q):
            break
        z, _, _ = ctx.requete(nom, 0.5).requete(Q)
        ok = np.isfinite(z)
        trous[jj[ok], ii[ok]] = False
        Q, jj, ii = Q[~ok], jj[~ok], ii[~ok]
    rec3 = (NB > 1) & ((Z - ZM) > 0.003)
    # recouvrement : nœud contenu strictement dans au moins 2 triangles de sol (hors BEV), QUEL QUE SOIT l'écart
    # (revue conformité du 11/10/2026 : ≈ 2 400 m² de double couche coplanaire échappaient au seuil de 3 mm)
    rec = (ctx.sol_couches_strictes > 1) | rec3
    gt = grappes_noeuds(ctx, trous, 0.25)
    gr = grappes_noeuds(ctx, rec, 0.25)
    R.mesure("trous", {"noeuds": int(trous.sum()), "aire_m2": r4(trous.sum() * PAS * PAS, 2), "grappes": len(gt)})
    R.mesure("recouvrements_sup_3mm", {"noeuds": int(rec3.sum()), "aire_m2": r4(rec3.sum() * PAS * PAS, 2),
                                       "ecart_max_m": r4(np.nanmax(np.where(rec3, Z - ZM, np.nan))) if rec3.any() else 0})
    R.mesure("recouvrements_tous", {"noeuds": int(rec.sum()), "aire_m2": r4(rec.sum() * PAS * PAS, 2),
                                    "grappes": len(gr)})
    # unité : tuile de 50 m (indice de tuile par position)
    tuiles = collections.defaultdict(list)
    for c, a, n, surf, _ in gt:
        tuiles[(int((c[0] + 150) // 50), int((c[1] + 150) // 50))].append(("trou", c, a, surf))
    for c, a, n, surf, (j, i) in gr:
        dz = float(np.nanmax(np.where(np.isfinite(Z[j, i] - ZM[j, i]), Z[j, i] - ZM[j, i], 0.0)))
        tuiles[(int((c[0] + 150) // 50), int((c[1] + 150) // 50))].append(("recouvrement", c, a, surf, dz))
    c_e = (T[:, :, :2].mean(1) + 150) // 50
    for ti in range(6):
        for tj in range(6):
            cas = tuiles.get((ti, tj), [])
            mt = (c_e[:, 0] == ti) & (c_e[:, 1] == tj)
            dbl = 0
            if not cas and not (aire[mt] < 1e-6).any():
                R.tester(True)
                continue
            cas.sort(key=lambda x: -x[2])
            pire = cas[0] if cas else None
            a_tot = sum(x[2] for x in cas)
            R.tester(False, entite=f"T_{ti:02d}_{tj:02d}" + (f" ({', '.join(pire[3][:2])})" if pire else ""),
                     xy=pire[1] if pire else None, valeur=r4(a_tot, 2), seuil="0 m² de trou ou de recouvrement",
                     detail=f"{sum(1 for x in cas if x[0] == 'trou')} trou(s), "
                            f"{sum(1 for x in cas if x[0] == 'recouvrement')} recouvrement(s) ; pire : "
                            f"{pire[0]} {pire[2]:.2f} m²" if pire else f"{int((aire[mt] < 1e-6).sum()) + dbl} "
                                                                       "triangle(s) dégénéré(s)",
                     ecart=a_tot / 0.1)
    R.mesure("trous_principaux", [{"xy_local": [r4(c[0], 2), r4(c[1], 2)], "aire_m2": r4(a, 2), "surfaces": s}
                                  for c, a, n, s, _ in gt[:15]])
    R.mesure("recouvrements_principaux", [{"xy_local": [r4(c[0], 2), r4(c[1], 2)], "aire_m2": r4(a, 2),
                                           "surfaces": s} for c, a, n, s, _ in gr[:15]])


# =========================================================================== VAL-SOL-009
@regle("VAL-SOL-009", "fabrication", "bloquant",
       "(1) E8 : triangles de sol > 45° et > 3 cm de dénivelé (hors noue_plantee et bande de 0,5 m au bord) ; "
       "(2) assise : sol à 3 cm devant la face − pied décrit (|·| ≤ 2 mm) et sol à 3 cm derrière l'arête arrière − "
       "tête (−4 ± 2 mm sur trottoir) ; (3) E9 : dessus des dalles BEV − sol à 3 cm hors du module (≤ 5 mm, p75 "
       "des sondes de bord : les plots ne comptent pas) ; "
       "(3b) BEV basculée : plan de la dalle à ≤ 1,5° du plan du sol voisin ; (1b) talus de noue ≤ 1/3 "
       "(GA-ASS-005) ; (4) chaussée : cuvettes > 3 mm sur > 0,25 m² (remplissage des dépressions à 0,10 m) ; (5) marches > 2 cm "
       "entre nœuds voisins d'un cheminement. Unités : tuiles (1), bordures (2), BEV (3), surfaces de chaussée (4), "
       "surfaces piétonnes (5).", "implemente")
def val_sol_009(ctx, R):
    sol = ctx.fab_couche("sol")
    T = sol["T"].astype(np.float64)
    mats = sol["mats"]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    pente = np.degrees(np.arctan2(np.hypot(n[:, 0], n[:, 1]), np.abs(n[:, 2])))
    dz = T[:, :, 2].max(1) - T[:, :, 2].min(1)
    c = T.mean(1)
    noue = np.isin(mats[sol["mat"]], ["noue_plantee"])
    bord = (np.abs(c[:, 0]) > 149.5) | (np.abs(c[:, 1]) > 149.5)
    raide = (pente > 45) & (dz > 0.03) & ~noue & ~bord
    R.mesure("1_E8_triangles", int(raide.sum()))
    # (1b) talus de la noue à 1/3 au plus (GA-ASS-005, nivellement « noue_talus_1_3 ») : triangles de noue_plantee
    # de plus de 20° (1/3 = 18,4°, tolérance) avec plus de 3 cm de dénivelé
    mur = noue & (pente > 20.0) & (dz > 0.03)
    R.mesure("1b_noue_triangles_sup_1_3", int(mur.sum()))
    if noue.any():
        k = int(np.nonzero(noue)[0][np.argmax(np.where(noue, pente, -1)[noue])]) if mur.any() else int(np.nonzero(noue)[0][0])
        R.tester(not mur.any(), entite="noue (noue_plantee)", xy=c[k], valeur=r4(pente[k], 1), seuil="talus ≤ 1/3 (≈ 18,4°)",
                 detail=f"partie 1b : {int(mur.sum())} triangle(s) de noue à plus de 20° (pire {pente[k]:.0f}° sur "
                        f"{dz[k] * 100:.0f} cm)", ecart=pente[k] / 18.4)
    tuile = ((c[:, 0] + 150) // 50).astype(int) * 10 + ((c[:, 1] + 150) // 50).astype(int)
    for t in sorted(set(tuile.tolist())):
        m = raide & (tuile == t)
        if not m.any():
            R.tester(True)
            continue
        k = np.nonzero(m)[0][np.argmax(dz[m])]
        R.tester(False, entite=f"T_{t // 10:02d}_{t % 10:02d}", xy=c[k], valeur=r4(dz[k], 3),
                 seuil="aucun triangle > 45° et > 0,03 m", detail=f"partie 1 (E8) : {int(m.sum())} triangle(s) raide(s), "
                 f"pire {pente[k]:.0f}° sur {dz[k] * 100:.1f} cm ({mats[sol['mat'][k]]})", ecart=dz[k] / 0.03)
    # (2) assise des bordures
    av, ar_tr = [], []
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        p = b["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 0.5, 0.2)
        pied, tete, _ = ctx.niv.z_bordure(bid, s)
        w = largeur_base(p, s)
        q_av, q_ar = xy - 0.03 * nrm, xy + (w + 0.03)[:, None] * nrm
        z_av = requete_sol(ctx, q_av)
        z_ar = requete_sol(ctx, q_ar)
        rb, rh = regions_bordure(ctx, bid)
        reg_av, _ = region_en(ctx, q_av)
        reg_ar, cl_ar = region_en(ctx, q_ar)
        # sondes retenues seulement dans la région basse (devant) et sur un cheminement de la région haute (derrière)
        d_av = np.where(reg_av == rb, z_av - pied, np.nan)
        d_ar = np.where((reg_ar == rh) & np.isin(cl_ar, K.PIETON), z_ar - tete, np.nan)
        bas, haut = cotes(ctx, bid)
        trottoir = bool(haut & set(K.PIETON))
        av.append(d_av[np.isfinite(d_av)])
        ab = dans_abaisse(p, s, 0.0)
        if trottoir:
            ar_tr.append(d_ar[np.isfinite(d_ar) & ~ab])
        e1 = np.nanmax(np.abs(d_av)) if np.isfinite(d_av).any() else 0.0
        e2 = np.nanmax(np.abs(np.where(ab, np.nan, d_ar) + 0.004)) if trottoir and np.isfinite(
            np.where(ab, np.nan, d_ar)).any() else 0.0
        ok = e1 <= 0.002 + 1e-9 and e2 <= 0.002 + 1e-9
        if ok:
            R.tester(True)
            continue
        if e1 / 0.002 >= e2 / 0.002:
            k = int(np.nanargmax(np.abs(d_av)))
            det = f"partie 2 : sol devant − pied = {d_av[k] * 1000:+.1f} mm (s = {s[k]:.1f} m)"
            val, ec = d_av[k], e1 / 0.002
            pt = xy[k] - 0.03 * nrm[k]
        else:
            dd = np.where(ab, np.nan, d_ar)
            k = int(np.nanargmax(np.abs(dd + 0.004)))
            det = f"partie 2 : sol derrière − tête = {dd[k] * 1000:+.1f} mm (cible −4 ± 2 ; s = {s[k]:.1f} m)"
            val, ec = dd[k], e2 / 0.002
            pt = xy[k] + (w[k] + 0.03) * nrm[k]
        R.tester(False, entite=bid, xy=pt, valeur=r4(val, 4), seuil="±0,002 m", detail=det, ecart=ec,
                 severite="majeur")
    av = np.concatenate(av) if av else np.zeros(0)
    ar_tr = np.concatenate(ar_tr) if ar_tr else np.zeros(0)
    R.mesure("2_sol_devant_moins_pied_m", stats(av, (5, 50, 95)))
    R.mesure("2_part_devant_dans_2mm", r4((np.abs(av) <= 0.002).mean(), 3) if len(av) else None)
    R.mesure("2_sol_derriere_moins_tete_trottoir_m", stats(ar_tr, (5, 50, 95)))
    # (3) BEV : dessus des dalles − sol à 3 cm hors module
    ents = ctx.fab_entites("sol")
    for bev_id in sorted(ctx.ponctuels):
        e = bev_id.replace("-", "_")
        if e not in ents:
            R.tester(False, entite=bev_id, detail="partie 3 : BEV décrite absente de sol.usdc", severite="majeur",
                     seuil="présente")
            continue
        TB = sol["T"][ents[e]].astype(np.float64)
        haut = TB[:, :, 2].max()
        poly = ctx.ponctuels[bev_id]["poly"][0][0]
        Pp = K.densifier(np.vstack([poly, poly[:1]]), 0.2)
        cen = poly.mean(0)
        u = Pp - cen
        u /= np.maximum(np.hypot(*u.T), 1e-9)[:, None]
        Qo = Pp + 0.03 * u
        zs = requete_sol(ctx, Qo)
        rq = K.RequeteMaillage(TB, 0.25)
        zb, _, _ = rq.requete(Pp - 0.01 * u)
        d = zb - zs
        d = d[np.isfinite(d)]
        # p75 des sondes : une sonde qui tombe sur un plot (5 mm) ne compte pas comme dessus de dalle
        e9 = float(np.percentile(np.abs(d), 75)) if len(d) else 0.0
        R.tester(e9 <= 0.005, entite=bev_id, xy=cen, valeur=r4(e9, 4), seuil="≤ 0,005 m",
                 detail=f"partie 3 (E9) : bord de dalle − sol à 3 cm = {e9 * 1000:.1f} mm (p75 des sondes, max "
                        f"{np.abs(d).max() * 1000:.1f} mm)", ecart=e9 / 0.005, severite="majeur")
        # (3b) BEV basculée : plan des sommets hauts de la dalle contre plan du sol de l'anneau de 0,10 à 0,50 m
        V = TB.reshape(-1, 3)
        V = V[V[:, 2] >= np.percentile(V[:, 2], 50)]
        A1 = np.c_[V[:, :2], np.ones(len(V))]
        c1, *_ = np.linalg.lstsq(A1, V[:, 2], rcond=None)
        lo, hi = poly.min(0) - 0.5, poly.max(0) + 0.5
        gx, gy = np.meshgrid(np.arange(lo[0], hi[0], 0.05), np.arange(lo[1], hi[1], 0.05))
        Qr = np.c_[gx.ravel(), gy.ravel()]
        dd = K.dist_polys(Qr, [[poly]])
        Qr = Qr[~K.dans(Qr, [poly]) & (dd >= 0.10) & (dd <= 0.50)]
        zr = requete_sol(ctx, Qr)
        okr = np.isfinite(zr)
        if okr.sum() >= 6:
            A2 = np.c_[Qr[okr], np.ones(okr.sum())]
            c2, *_ = np.linalg.lstsq(A2, zr[okr], rcond=None)
            n1 = np.array([-c1[0], -c1[1], 1.0]); n2 = np.array([-c2[0], -c2[1], 1.0])
            ang = math.degrees(math.acos(min(1.0, float(n1 @ n2) / (np.linalg.norm(n1) * np.linalg.norm(n2)))))
            R.tester(ang <= 1.5, entite=bev_id, xy=cen, valeur=r4(ang, 2), seuil="≤ 1,5° du plan du sol voisin",
                     detail=f"partie 3b : dalles BEV basculées de {ang:.1f}° par rapport au trottoir voisin",
                     ecart=ang / 1.5, severite="majeur")
    # (4) cuvettes de chaussée : voir GA-CHA-004 (même calcul)
    cuv = cuvettes(ctx)
    for sid, cas in cuv["par_surface"].items():
        if not cas:
            R.tester(True)
            continue
        pire = max(cas, key=lambda x: x["profondeur_m"] * x["aire_m2"])
        R.tester(False, entite=sid, xy=pire["xy"], valeur=pire["profondeur_m"], seuil="cuvette ≤ 3 mm ou ≤ 0,25 m²",
                 detail=f"partie 4 : {len(cas)} cuvette(s), pire {pire['profondeur_m'] * 1000:.0f} mm sur "
                        f"{pire['aire_m2']:.2f} m²", ecart=pire["profondeur_m"] / 0.003, severite="majeur")
    R.mesure("4_cuvettes", {"n": cuv["n"], "aire_m2": cuv["aire_m2"]})
    # (5) marches > 2 cm sur cheminement
    G = grille(ctx)
    Z, ped = G["Z"], G["ped"] & (G["sous"] != "")
    ped = G["ped"]
    m = np.zeros_like(ped)
    for di, dj in ((1, 0), (0, 1)):
        z2 = K.decaler(Z, -di, -dj, np.nan)
        p2 = K.decaler(ped, -di, -dj, False)
        r2 = K.decaler(G["R"], -di, -dj, -9)
        marche = ped & p2 & (np.abs(Z - z2) > 0.02)
        m |= marche
    par = collections.defaultdict(list)
    for c, a, n_, surf, (j, i) in grappes_noeuds(ctx, m, 0.25):
        par[surf[0] if surf else "?"].append((c, a, n_))
    for sid in sorted(s for s in ctx.surfaces if ctx.surfaces[s]["p"]["classe"] in K.PIETON):
        cas = par.get(sid, [])
        if not cas:
            R.tester(True)
            continue
        c, a, n_ = max(cas, key=lambda x: x[2])
        R.tester(False, entite=sid, xy=c, valeur=n_, seuil="aucune marche > 0,02 m entre nœuds voisins",
                 detail=f"partie 5 : {len(cas)} ligne(s) de marche, la plus longue sur {n_} nœuds", ecart=2.0,
                 severite="majeur")


def cuvettes(ctx):
    """Dépressions du sol fabriqué sur les surfaces revêtues circulées (priorité-inondation à 0,10 m) : profondeur
    > 3 mm et aire > 0,25 m² (VAL-SOL-009 (4), GA-CHA-004). Avaloirs : ponctuels_sol de type avaloir (aucun)."""
    def f():
        import heapq
        G = grille(ctx)
        Z = G["Z"]
        cl = G["cl"]
        revetu = np.char.startswith(ctx.sol_materiau, "enrobe") | np.char.startswith(ctx.sol_materiau, "beton")             | np.char.startswith(ctx.sol_materiau, "pave")
        dom = np.isin(cl, ("chaussee", "parking", "acces_riverain", "quai_bus")) & np.isfinite(Z) & revetu
        # sous-échantillonnage à 0,20 m pour la vitesse
        s = 2
        Zs = Z[::s, ::s]
        D = dom[::s, ::s]
        ny, nx = Zs.shape
        W = np.where(D, Zs, np.inf)
        rempli = np.full_like(Zs, np.inf)
        vu = ~D
        tas = []
        bord = D & ~(K.eroder(D, 1))
        for j, i in zip(*np.nonzero(bord)):
            rempli[j, i] = W[j, i]
            vu[j, i] = True
            heapq.heappush(tas, (W[j, i], j, i))
        while tas:
            h, j, i = heapq.heappop(tas)
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                a, b = j + dj, i + di
                if 0 <= a < ny and 0 <= b < nx and not vu[a, b]:
                    vu[a, b] = True
                    rempli[a, b] = max(W[a, b], h)
                    heapq.heappush(tas, (rempli[a, b], a, b))
        prof = np.where(D, rempli - Zs, 0.0)
        m = prof > 0.003
        Gs = G["g"][::s]
        jj, ii = np.nonzero(m)
        out = {"n": 0, "aire_m2": 0.0, "par_surface": {sid: [] for sid in ctx.surfaces
                                                         if ctx.surfaces[sid]["p"]["classe"] in
                                                         ("chaussee", "parking", "acces_riverain", "quai_bus")},
               "cas": []}
        if len(jj):
            Q = np.c_[Gs[ii], Gs[jj]]
            lab = K.grappes(Q, 0.25)
            for k in range(lab.max() + 1):
                sel = lab == k
                a = sel.sum() * (s * PAS) ** 2
                if a <= 0.25:
                    continue
                pr = float(prof[jj[sel], ii[sel]].max())
                c = Q[sel].mean(0)
                sid_k = collections.Counter(G["R"][jj[sel] * s, ii[sel] * s].tolist()).most_common(1)[0][0]
                sid = G["ids"][sid_k] if sid_k >= 0 else "?"
                cas = {"xy": c, "aire_m2": r4(a, 2), "profondeur_m": r4(pr, 4), "surface": sid}
                out["cas"].append(cas)
                out["par_surface"].setdefault(sid, []).append(cas)
                out["n"] += 1
                out["aire_m2"] += a
        out["aire_m2"] = r4(out["aire_m2"], 1)
        return out
    return ctx._m("sol:cuvettes", f)


# =========================================================================== GA-CHA-004
@regle("GA-CHA-004", "fabrication", "majeur",
       "Points bas du sol fabriqué revêtu (enrobé, béton, pavé) sur chaussée, parking, accès et quais (dépressions "
       "> 3 mm sur > 0,25 m², grille de 0,20 m) ; un point bas est conforme s'il a un avaloir décrit (ponctuels_sol type avaloir) à moins de 1 m. "
       "Unité : point bas.", "implemente")
def ga_cha_004(ctx, R):
    cuv = cuvettes(ctx)
    avaloirs = [v["poly"][0][0].mean(0) for v in ctx.ponctuels.values() if v["p"].get("type") in ("avaloir", "grille")]
    A = np.array(avaloirs) if avaloirs else np.zeros((0, 2))
    R.mesure("avaloirs_decrits", len(A))
    for cas in sorted(cuv["cas"], key=lambda c: (-c["aire_m2"] * c["profondeur_m"], c["surface"])):
        d = float(np.min(np.hypot(*(A - cas["xy"]).T))) if len(A) else np.inf
        R.tester(d <= 1.0, entite=cas["surface"], xy=cas["xy"], valeur=cas["profondeur_m"],
                 seuil="avaloir à ≤ 1 m", detail=f"point bas de {cas['profondeur_m'] * 1000:.0f} mm sur "
                                                 f"{cas['aire_m2']:.2f} m² sans avaloir", ecart=cas["aire_m2"])


# =========================================================================== TQ-SOL-013
@regle("TQ-SOL-013", "les_deux", "majeur",
       "Modèle de nivellement unique : (a) par surface, sol fabriqué − z(x, y, surface) du modèle (p95 ≤ 3 cm, alerte "
       "5 cm ; bande de 1 m au bord du carré exclue) ; (b) par bordure, pied décrit − fil d'eau MNT 2026 à 0,30 m devant la face (contrôle : p95 ≤ 3 cm, "
       "alerte 5 cm) ; (c) tête = pied + vue décrite. Unités : surfaces non bâties, bordures.", "implemente")
def tq_sol_013(ctx, R):
    G = grille(ctx)
    Z, Rr, ids = G["Z"], G["R"], G["ids"]
    g = G["g"]
    XX, YY = np.meshgrid(g, g)
    idx = np.nonzero((Rr >= 0) & np.isfinite(Z) & (np.abs(XX) < 149.0) & (np.abs(YY) < 149.0))
    jj, ii = idx[0][::3], idx[1][::3]          # un nœud sur trois
    zf = Z[jj, ii]
    sids = Rr[jj, ii]
    zm = np.full(len(jj), np.nan)
    o = np.argsort(sids, kind="stable")
    b = np.searchsorted(sids[o], np.arange(len(ids) + 1))
    ecarts = {}
    for k, sid in enumerate(ids):
        sel = o[b[k]:b[k + 1]]
        if not len(sel):
            continue
        zm[sel] = ctx.niv.z(g[ii[sel]], g[jj[sel]], sid)
        d = zf[sel] - zm[sel]
        d = d[np.isfinite(d)]
        if len(d):
            ecarts[sid] = (d, sel)
    tout = np.concatenate([np.abs(d) for d, _ in ecarts.values()])
    R.mesure("a_sol_fabrique_moins_modele_m", stats(tout, (50, 95, 99)))
    par_classe = collections.defaultdict(list)
    for sid, (d, sel) in ecarts.items():
        par_classe[ctx.surfaces[sid]["p"]["classe"]].append(np.abs(d))
    R.mesure("a_par_classe_p95_m", {c: r4(np.percentile(np.concatenate(v), 95)) for c, v in sorted(par_classe.items())})
    for sid in sorted(ecarts):
        d, sel = ecarts[sid]
        if ctx.surfaces[sid]["p"]["classe"] == "emprise_bordure":
            continue
        p95 = float(np.percentile(np.abs(d), 95))
        k = sel[int(np.argmax(np.abs(d)))]
        R.tester(p95 <= 0.05, entite=sid, xy=(g[ii[k]], g[jj[k]]), valeur=r4(p95, 4), seuil="p95 ≤ 0,03 (alerte 0,05)",
                 detail=f"(a) {ctx.surfaces[sid]['p']['classe']} : |sol − modèle| p95 {p95 * 100:.1f} cm, max "
                        f"{np.abs(d).max() * 100:.1f} cm", ecart=p95 / 0.03)
    # (b) contrôle MNT et (c) tête = pied + vue
    mnt = ctx.mnt
    tous_b = []
    for bid in sorted(ctx.bordures):
        p = ctx.bordures[bid]["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 0.5, 0.1)
        pied, tete, _ = ctx.niv.z_bordure(bid, s)
        Qm = xy - 0.30 * nrm
        zmnt = mnt(Qm[:, 0] + K.O[0], Qm[:, 1] + K.O[1]) - K.O[2]
        d = pied - zmnt
        tous_b.append(d)
        v = vue_a(p, s)
        dv = np.nanmax(np.abs(tete - pied - v)) if np.isfinite(v).any() else 0.0
        p95 = float(np.percentile(np.abs(d), 95))
        k = int(np.argmax(np.abs(d)))
        ok = p95 <= 0.05 and dv <= 0.002
        R.tester(ok, entite=bid, xy=xy[k], valeur=r4(p95, 4), seuil="p95 ≤ 0,03 (alerte 0,05) ; tête = pied + vue",
                 detail=(f"(b) pied − fil d'eau MNT p95 {p95 * 100:.1f} cm (max {np.abs(d).max() * 100:.1f} cm)"
                         if p95 > 0.05 else f"(c) tête − pied − vue jusqu'à {dv * 1000:.1f} mm"),
                 ecart=max(p95 / 0.03, dv / 0.002))
    tb = np.concatenate(tous_b)
    R.mesure("b_pied_moins_mnt_m", stats(np.abs(tb), (50, 95, 99)))


# =========================================================================== TQ-SOL-003
@regle("TQ-SOL-003", "fabrication", "mineur",
       "Lignes de rupture : aucun triangle de sol ne chevauche le pied de face d'une bordure (face à 0 ou à +12 mm sous "
       "l'élément) ni une couture de tuile de 50 m ; sondes tous les 0,25 m à ±3 mm de la ligne : le triangle touché "
       "ne doit pas avoir de sommets de part et d'autre (à plus de 1 mm). Unités : bordures, tuiles.", "partiel",
       "couronne, changements de dévers et bords de rampe non contrôlés (non décrits comme lignes)")
def tq_sol_003(ctx, R):
    req = ctx.requete("sol", 0.5)
    T = req.T
    for bid in sorted(ctx.bordures):
        s, xy, nrm, tg = echantillons(ctx, bid, 0.25, 0.3)
        crois = np.zeros(len(s), bool)
        for off in (0.0, 0.012):
            mauvais = np.zeros(len(s), bool)
            for e in (-0.003, 0.003):
                Q = xy + (off + e) * nrm
                _, ti, _ = req.requete(Q)
                ok = ti >= 0
                d = np.einsum("tkj,tj->tk", T[ti[ok], :, :2] - (xy[ok] + off * nrm[ok])[:, None, :], nrm[ok])
                mauvais[ok] |= (d.max(1) > 0.001) & (d.min(1) < -0.001)
            crois = crois | (~mauvais) if off else ~mauvais
        bad = ~crois
        n_bad = int(bad.sum())
        if n_bad == 0:
            R.tester(True)
            continue
        k = int(np.nonzero(bad)[0][0])
        R.tester(False, entite=bid, xy=xy[k], valeur=n_bad, seuil="0 triangle à cheval sur le pied de face",
                 detail=f"{n_bad}/{len(s)} sondes où un triangle chevauche le pied (s = {s[k]:.2f} m)",
                 ecart=n_bad / max(len(s), 1) * 10)
    # coutures de tuiles
    sol = ctx.fab_couche("sol")
    c = sol["T"][:, :, :2].astype(np.float64)
    ent = sol["ent"]
    noms = sol["ents"]
    for k, nom in enumerate(noms):
        if not str(nom).startswith("T_"):
            continue
        ti, tj = int(str(nom)[2:4]), int(str(nom)[5:7])
        x0, y0 = -150 + 50 * ti, -150 + 50 * tj
        m = ent == k
        lo, hi = c[m].min(axis=(0, 1)), c[m].max(axis=(0, 1))
        hors = max(x0 - lo[0], y0 - lo[1], hi[0] - (x0 + 50), hi[1] - (y0 + 50))
        R.tester(hors <= 1e-4, entite=str(nom), xy=((x0 + 25), (y0 + 25)), valeur=r4(hors, 5),
                 seuil="triangles dans la tuile de 50 m", detail=f"débord de {hors:.4f} m hors de la tuile", ecart=hors / 1e-4)


# =========================================================================== TQ-SOL-008
@regle("TQ-SOL-008", "fabrication", "mineur",
       "Coutures entre tuiles de sol : sommets confondus (< 0,01 mm) appartenant à deux components T_ii_jj différents ; "
       "la normale moyenne des coins de chaque tuile doit être identique (écart ≤ 0,5°, cible 0°). Unité : paire de "
       "tuiles voisines.", "implemente")
def tq_sol_008(ctx, R):
    sol = ctx.fab_couche("sol")
    T = sol["T"].astype(np.float64)
    N = sol["N"].astype(np.float64).reshape(-1, 3)
    N /= np.maximum(np.linalg.norm(N, axis=1), 1e-12)[:, None]
    noms = sol["ents"]
    tuile = np.char.startswith(noms.astype(str), "T_")[sol["ent"]]
    P = T.reshape(-1, 3)
    E = np.repeat(sol["ent"], 3)
    garde = np.repeat(tuile, 3)
    P, N, E = P[garde], N[garde], E[garde]
    q = np.round(P / 1e-5).astype(np.int64)
    _, inv = np.unique(q, axis=0, return_inverse=True)
    # sommets partagés par au moins deux tuiles
    cle = inv.astype(np.int64) * 1000 + E
    u_cle, first = np.unique(cle, return_index=True)
    sommet = u_cle // 1000
    n_tuiles = np.bincount(sommet)
    partage = np.nonzero(n_tuiles >= 2)[0]
    R.mesure("sommets_de_couture", int(len(partage)))
    if not len(partage):
        R.tester(False, entite="sol.usdc", detail="aucun sommet partagé entre tuiles (tuiles disjointes ?)",
                 seuil="coutures soudées")
        return
    sel = np.isin(inv, partage)
    inv_s, E_s, N_s, P_s = inv[sel], E[sel], N[sel], P[sel]
    o = np.lexsort((E_s, inv_s))
    inv_s, E_s, N_s, P_s = inv_s[o], E_s[o], N_s[o], P_s[o]
    grp = np.r_[0, np.nonzero((np.diff(inv_s) != 0) | (np.diff(E_s) != 0))[0] + 1, len(o)]
    moy = np.add.reduceat(N_s, grp[:-1], axis=0)
    moy /= np.maximum(np.linalg.norm(moy, axis=1), 1e-12)[:, None]
    vg, eg, pg = inv_s[grp[:-1]], E_s[grp[:-1]], P_s[grp[:-1]]
    paires = collections.defaultdict(list)
    b = np.r_[0, np.nonzero(np.diff(vg))[0] + 1, len(vg)]
    for a0, a1 in zip(b[:-1], b[1:]):
        for i in range(a0, a1):
            for j in range(i + 1, a1):
                c = float(np.clip(moy[i] @ moy[j], -1, 1))
                paires[(int(eg[i]), int(eg[j]))].append((math.degrees(math.acos(c)), pg[i]))
    tous = []
    for (a, b_), v in sorted(paires.items()):
        angs = np.array([x[0] for x in v])
        tous.append(angs)
        k = int(np.argmax(angs))
        R.tester(angs.max() <= 0.5, entite=f"{noms[a]} / {noms[b_]}", xy=v[k][1], valeur=r4(angs.max(), 2),
                 seuil="≤ 0,5° (cible 0°)", detail=f"{(angs > 0.5).sum()}/{len(angs)} sommets de couture à normales "
                                                   f"différentes (max {angs.max():.1f}°)", ecart=angs.max() / 0.5)
    if tous:
        R.mesure("ecart_normales_couture_deg", stats(np.concatenate(tous), (50, 95, 99)))


# =========================================================================== TQ-SOL-010 / TQ-SOL-012
@regle("TQ-SOL-010", "fabrication", "info",
       "Tuiles de sol de 50 m (64 m au plus) et pivot au coin SO sur le mètre entier : emprise de chaque component "
       "T_ii_jj de sol.usdc et translation du component. Les réglages Nanite / collision sont côté UE (non lus).",
       "partiel", "Nanite, distance field et collision : réglages de l'import UE, hors des fichiers")
def tq_sol_010(ctx, R):
    prims = ctx.cache["couches"]["sol"]["prims"]
    comp = collections.defaultdict(list)
    for p in prims:
        comp[p["composant"]].append(p)
    for c in sorted(comp):
        ps = comp[c]
        lo = np.min([p["extent"][0] for p in ps], axis=0)
        hi = np.max([p["extent"][1] for p in ps], axis=0)
        taille = float(max(hi[0] - lo[0], hi[1] - lo[1]))
        piv = np.array(ps[0]["pivot_composant"])
        attendu = np.floor(lo[:2] + 1e-6)
        piv_ok = np.allclose(piv[:2], attendu, atol=1e-6) or np.allclose(piv[:2], np.floor(lo[:2] / 50) * 50, atol=1e-6)
        nom = c.split("/")[-1]
        if not nom.startswith("T_"):
            R.tester(taille <= 64.0, entite=nom, xy=(lo + hi)[:2] / 2, valeur=r4(taille, 2), seuil="≤ 64 m")
            continue
        ok = taille <= 64.0 and piv_ok
        R.tester(ok, entite=nom, xy=(lo + hi)[:2] / 2, valeur=r4(taille, 2), seuil="≤ 64 m, pivot coin SO entier",
                 detail=f"taille {taille:.1f} m, pivot du component {piv[:2].round(2).tolist()} "
                        f"(coin SO {np.floor(lo[:2] / 50) * 50})", ecart=1.0)


@regle("TQ-SOL-012", "fabrication", "info",
       "La voirie est faite de tuiles StaticMesh fabriquées par Houdini (sol.usdc, Mesh polygonaux), ni Landscape ni "
       "Mesh Terrain : types de prims de la couche de sol.", "implemente")
def tq_sol_012(ctx, R):
    prims = ctx.cache["couches"]["sol"]["prims"]
    R.tester(len(prims) > 0 and all(p["subdivision"] == "none" for p in prims), entite="sol.usdc",
             detail="maillages polygonaux subdivisionScheme = none attendus")


# =========================================================================== TQ-SOL-001
@regle("TQ-SOL-001", "description", "majeur",
       "Partition 2D du site : aire des surfaces + bâtiments = carré de 300 m (aucun recouvrement : somme des aires = "
       "aire couverte rasterisée à 0,10 m, ±0,5 %) ; sommets sur la grille de 1 mm ; arêtes de moins de 5 mm. "
       "Unité : surface.", "implemente")
def tq_sol_001(ctx, R):
    G = grille(ctx)
    somme = sum(K.aire_poly(p) for s in ctx.surfaces.values() for p in s["poly"])
    couvert = float((G["R"] >= 0).sum()) * PAS * PAS
    R.mesure("somme_aires_m2", r4(somme, 1))
    R.mesure("aire_couverte_raster_m2", r4(couvert, 1))
    R.mesure("ecart_relatif", r4((somme - couvert) / couvert, 4))
    lr = [s_["p"] for s_ in ctx.surfaces.values() if s_["p"].get("limite_raster")]
    R.mesure("limites_sans_source_vectorielle", {"surfaces_limite_raster": len(lr),
                                                  "fermetures_m": r4(sum(p.get("fermetures_m", 0.0) for p in lr), 1),
                                                  "par_classe": dict(sorted(collections.Counter(p["classe"] for p in lr).items()))})
    for sid in sorted(ctx.surfaces):
        s = ctx.surfaces[sid]
        courtes, hors_mm = 0, 0
        pire = None
        for p in s["poly"]:
            for r in p:
                d = np.hypot(*(np.roll(r, -1, 0) - r).T)
                courtes += int((d < 0.005).sum())
                if (d < 0.005).any() and pire is None:
                    pire = r[int(np.argmin(d))]
                hors_mm += int((np.abs(np.round((r + K.O[:2]) * 1000) - (r + K.O[:2]) * 1000) > 0.02).sum())
        ok = courtes == 0 and hors_mm == 0
        R.tester(ok, entite=sid, xy=pire if pire is not None else s["poly"][0][0][0], valeur=courtes,
                 seuil="0 arête < 5 mm, sommets au mm", detail=f"{courtes} arête(s) < 5 mm, {hors_mm} sommet(s) hors grille",
                 ecart=1 + courtes)
    if abs(somme - couvert) / couvert > 0.005:
        R.tester(False, entite="partition", valeur=r4(somme - couvert, 1), seuil="±0,5 %",
                 detail=f"somme des aires {somme:.0f} m² ≠ aire couverte {couvert:.0f} m² (recouvrements)", ecart=2)


# =========================================================================== TQ-SOL-014
@regle("TQ-SOL-014", "fabrication", "majeur",
       "Aire du carrefour (union des voies de la jonction 100, lanes_2026) sur le sol fabriqué : pente résultante ≥ "
       "0,5 % (base 1 m) hors 1 m autour d'un avaloir, pente locale ≤ 4 %, aucun minimum local (cuvette) dans un "
       "passage, une traversée cyclable ou un abaissé. Unités : critère pente minimale, critère pente maximale, "
       "chaque passage de l'aire du carrefour.", "partiel", "écart de pente au raccord des branches non mesuré")
def tq_sol_014(ctx, R):
    G = grille(ctx)
    g = G["g"]
    jn = ctx.jonction
    XX, YY = np.meshgrid(g, g)
    lo = np.min([p[0].min(0) for p in jn], axis=0)
    hi = np.max([p[0].max(0) for p in jn], axis=0)
    box = (XX >= lo[0]) & (XX <= hi[0]) & (YY >= lo[1]) & (YY <= hi[1])
    jj, ii = np.nonzero(box)
    Q = np.c_[g[ii], g[jj]]
    dedans = K.dans_liste(Q, jn)
    mj = np.zeros_like(box)
    mj[jj[dedans], ii[dedans]] = True
    Z = G["Z"]
    gx = (K.decaler(Z, -5, 0, np.nan) - K.decaler(Z, 5, 0, np.nan)) / 1.0
    gy = (K.decaler(Z, 0, -5, np.nan) - K.decaler(Z, 0, 5, np.nan)) / 1.0
    pen = np.hypot(gx, gy) * 100
    pen = np.where(mj & np.isfinite(pen), pen, np.nan)
    v = pen[np.isfinite(pen)]
    R.mesure("pente_jonction_pct", stats(v, (5, 50, 95)))
    R.mesure("aire_jonction_m2", r4(mj.sum() * PAS * PAS, 1))
    plat = np.isfinite(pen) & (pen < 0.5)
    raide = np.isfinite(pen) & (pen > 4.0)
    for nom, m, seuil, k in (("pente < 0,5 %", plat, "≥ 0,5 %", 0.5), ("pente > 4 %", raide, "≤ 4 %", 4.0)):
        part = float(m.sum()) / max(1, np.isfinite(pen).sum())
        gr = grappes_noeuds(ctx, m, 0.3, 3)
        R.tester(part <= 0.01, entite="jonction 100", xy=gr[0][0] if gr else None, valeur=r4(part, 3),
                 seuil=f"{seuil} partout (tolérance 1 % de l'aire)",
                 detail=f"{nom} sur {part * 100:.1f} % de l'aire ({m.sum() * PAS * PAS:.1f} m²)",
                 ecart=part / 0.01)
    cuv = cuvettes(ctx)
    for mid, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["classe"] != "passage" or not ctx.fabrique_marquage(p):
            continue
        c = np.vstack(e["lignes"]).mean(0)
        if not K.dans_liste(c[None], jn)[0] and float(K.dist_polys(c[None], jn)[0]) > 3.0:
            continue
        A = np.vstack(e["lignes"])
        larg = (p.get("longueur_bande_m") or 3.0) / 2 + 0.5
        dans_pp = [x for x in cuv["cas"] if float(K.dist_polyligne(np.asarray(x["xy"])[None], A)[0]) <= larg]
        R.tester(not dans_pp, entite=mid, xy=c, valeur=len(dans_pp), seuil="aucune cuvette dans le passage",
                 detail=f"{len(dans_pp)} cuvette(s) dans le passage" + (
                     f" (pire {max(x['profondeur_m'] for x in dans_pp) * 1000:.0f} mm)" if dans_pp else ""), ecart=2)


# =========================================================================== GA-CHA-001
@regle("GA-CHA-001", "fabrication", "mineur",
       "Dévers de la chaussée hors jonction sur le sol fabriqué : composante de la pente (base 1 m) perpendiculaire "
       "au cap de la route OpenDRIVE la plus proche, un nœud sur deux (0,20 m) des voies driving / bus ; conforme si la médiane de |dévers| "
       "est dans [1,5 ; 4] % et moins de 20 % des nœuds hors de [1,0 ; 4,5] %. Unité : voie OpenDRIVE (section).",
       "implemente")
def ga_cha_001(ctx, R):
    G = grille(ctx)
    g, Z = G["g"], G["Z"]
    gx = (K.decaler(Z, -5, 0, np.nan) - K.decaler(Z, 5, 0, np.nan)) / 1.0
    gy = (K.decaler(Z, 0, -5, np.nan) - K.decaler(Z, 0, 5, np.nan)) / 1.0
    tout = []
    for v in sorted(ctx.voies, key=lambda v: (int(v["route"]), float(v["section_s"] or 0), int(v["voie"] or 0))):
        if v["jonction"] or v["type"] not in ("driving", "bus"):
            continue
        r = ctx.reseau[v["route"]]
        poly = v["poly"]
        lo, hi = poly[0].min(0), poly[0].max(0)
        i0, i1 = np.searchsorted(g, lo[0]), np.searchsorted(g, hi[0])
        j0, j1 = np.searchsorted(g, lo[1]), np.searchsorted(g, hi[1])
        if i1 <= i0 or j1 <= j0:
            continue
        XX, YY = np.meshgrid(g[i0:i1:2], g[j0:j1:2])
        Q = np.c_[XX.ravel(), YY.ravel()]
        m = K.dans(Q, poly)
        Q = Q[m]
        jj = (np.searchsorted(g, Q[:, 1] - 1e-6))
        ii = (np.searchsorted(g, Q[:, 0] - 1e-6))
        ok = np.isin(G["cl"][jj, ii], ("chaussee",))
        Q, jj, ii = Q[ok], jj[ok], ii[ok]
        if len(Q) < 50:
            continue
        sref = np.linspace(0, r.longueur, max(2, int(r.longueur / 1.0)))
        xr, yr, hr = r.reference(sref)
        d, js, _ = K.C.distance_segments(Q, np.c_[xr, yr][:-1], np.c_[xr, yr][1:])
        h = hr[js]
        dev = (-np.sin(h) * gx[jj, ii] + np.cos(h) * gy[jj, ii]) * 100
        dev = dev[np.isfinite(dev)]
        if not len(dev):
            continue
        a = np.abs(dev)
        tout.append(a)
        med = float(np.median(a))
        hors = float(((a < 1.0) | (a > 4.5)).mean())
        ok = 1.5 - 1e-9 <= med <= 4.0 + 1e-9 and hors <= 0.2
        c = Q.mean(0)
        R.tester(ok, entite=f"route {v['route']} s{float(v['section_s'] or 0):g} voie {v['voie']}", xy=c,
                 valeur=r4(med, 2), seuil="médiane |dévers| dans [1,5 ; 4] %",
                 detail=f"|dévers| médian {med:.2f} %, {hors * 100:.0f} % des nœuds hors [1 ; 4,5] %",
                 ecart=max(1.5 / max(med, 0.05), med / 4.0, hors / 0.2))
    if tout:
        R.mesure("devers_abs_pct", stats(np.concatenate(tout), (5, 50, 95)))


# =========================================================================== GA-CHA-003
@regle("GA-CHA-003", "description", "mineur",
       "Fil d'eau (pied décrit, nivellement.json) des bordures de chaussée de plus de 20 m : aucun tronçon de 20 m de "
       "pente longitudinale < 0,5 % sans point bas équipé d'un avaloir. Unité : bordure de chaussée ≥ 20 m.",
       "implemente")
def ga_cha_003(ctx, R):
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        bas, _ = cotes(ctx, bid)
        if "chaussee" not in bas or b["s"][-1] < 20:
            continue
        s = np.arange(0, b["s"][-1], 1.0)
        pied, _, _ = ctx.niv.z_bordure(bid, s)
        pente = np.abs(pied[20:] - pied[:-20]) / 20 * 100 if len(s) > 20 else np.array([])
        if not len(pente):
            continue
        k = int(np.argmin(pente))
        R.tester(pente.min() >= 0.5, entite=bid, xy=K.point(b["P"][:, :2], s[k] + 10), valeur=r4(pente.min(), 3),
                 seuil="≥ 0,5 % sur 20 m", detail=f"pente du fil d'eau {pente.min():.2f} % sur 20 m (s {s[k]:.0f}-{s[k] + 20:.0f})",
                 ecart=0.5 / max(pente.min(), 0.05))


# =========================================================================== GA-TRO-003
def kerbs_chaussee_index(ctx):
    """Segments d'arête avant des bordures dont le côté bas est circulé (pour orienter le dévers)."""
    def f():
        A, B = [], []
        for bid in sorted(ctx.bordures):
            bas, haut = cotes(ctx, bid)
            if not (bas & set(K.CIRCULE)):
                continue
            P = ctx.bordures[bid]["P"][:, :2]
            A.append(P[:-1])
            B.append(P[1:])
        return np.vstack(A), np.vstack(B)
    return ctx._m("sol:kerbs_ch", f)


@regle("GA-TRO-003", "fabrication", "mineur",
       "Dévers des trottoirs et quais (hors rampes) sur le sol fabriqué, dans la bande de 0,25 à 4 m derrière les "
       "bordures de chaussée qui bordent la surface (surfaces.bords, côté arrière) : pente (base 1 m) projetée sur la "
       "direction de la bordure la plus proche, positive vers la chaussée ; conforme si la médiane est dans [1 ; 2] % "
       "(±0,25) et moins de 20 % des nœuds en dévers négatif. Le même calcul sur la grille du modèle décrit "
       "(nivellement_grille z0) est rapporté. Unité : surface piétonne bordée par une bordure de chaussée.",
       "implemente")
def ga_tro_003(ctx, R):
    G = grille(ctx)
    g = G["g"]
    gx, gy = pentes(ctx, 5)
    z0 = np.load(ctx.dbase / "nivellement_grille.npz")["z0"].astype(np.float64)
    dx0 = (K.decaler(z0, -5, 0, np.nan) - K.decaler(z0, 5, 0, np.nan)) / 1.0
    dy0 = (K.decaler(z0, 0, -5, np.nan) - K.decaler(z0, 0, 5, np.nan)) / 1.0
    tout_f, tout_d = [], []
    for k, sid in enumerate(G["ids"]):
        p = ctx.surfaces[sid]["p"]
        if p["classe"] not in K.PIETON or str(p.get("sous_classe") or "").startswith("rampe"):
            continue
        kb = [b["bordure"] for b in p.get("bords") or [] if b["cote"] == "arriere" and b["bordure"] in ctx.bordures
              and (cotes(ctx, b["bordure"])[0] & set(K.CIRCULE))]
        if not kb:
            continue
        A = np.vstack([ctx.bordures[b]["P"][:-1, :2] for b in kb])
        B = np.vstack([ctx.bordures[b]["P"][1:, :2] for b in kb])
        jj, ii = np.nonzero(G["R"] == k)
        if len(jj) > 4000:
            pas_ = int(math.ceil(len(jj) / 4000))
            jj, ii = jj[::pas_], ii[::pas_]
        Q = np.c_[g[ii], g[jj]]
        d, _, proj = K.C.distance_segments(Q, A, B)
        m = (d >= 0.25) & (d <= 4.0)
        if m.sum() < 10:
            continue
        jj, ii, Q, proj = jj[m], ii[m], Q[m], proj[m]
        u = proj - Q
        u /= np.maximum(np.hypot(*u.T), 1e-9)[:, None]
        dev = -(gx[jj, ii] * u[:, 0] + gy[jj, ii] * u[:, 1]) * 100
        dev_d = -(dx0[jj, ii] * u[:, 0] + dy0[jj, ii] * u[:, 1]) * 100
        ok = np.isfinite(dev)
        if ok.sum() < 10:
            continue
        v = dev[ok]
        tout_f.append(v)
        tout_d.append(dev_d[np.isfinite(dev_d)])
        med = float(np.median(v))
        neg = float((v < 0).mean())
        okk = 0.75 <= med <= 2.25 and neg <= 0.2
        c = Q[ok][int(np.argmin(v))] if neg > 0.2 else Q[ok].mean(0)
        md = float(np.median(dev_d[np.isfinite(dev_d)])) if np.isfinite(dev_d).any() else float("nan")
        R.tester(okk, entite=sid, xy=c, valeur=r4(med, 2), seuil="médiane dans [1 ; 2] %, ≤ 20 % négatif",
                 detail=f"dévers fabriqué médian {med:.2f} % ({neg * 100:.0f} % négatif, p5 {np.percentile(v, 5):.1f}, "
                        f"p95 {np.percentile(v, 95):.1f} %) ; modèle décrit {md:.2f} %",
                 ecart=max(med / 2.0, 1.0 / max(med, 0.1), neg / 0.2))
    if tout_f:
        v = np.concatenate(tout_f)
        R.mesure("devers_fabrique_pct", stats(v, (5, 50, 95)))
        R.mesure("fabrique_part_1_2", r4(((v >= 1) & (v <= 2)).mean(), 3))
        R.mesure("fabrique_part_negatif", r4((v < 0).mean(), 3))
        w = np.concatenate(tout_d)
        R.mesure("devers_modele_decrit_pct", stats(w, (5, 50, 95)))
        R.mesure("modele_part_negatif", r4((w < 0).mean(), 3))


# =========================================================================== GA-TRO-004
@regle("GA-TRO-004", "fabrication", "majeur",
       "Pente longitudinale des cheminements (trottoirs, quais, rampes) sur le sol fabriqué : |pente| sur fenêtres de "
       "2,00 m (base 2 m) et de 0,50 m (base 0,5 m), extrémités dans la même surface ou dans deux surfaces piétonnes de "
       "la même région de nivellement. Violation : > 0,25 m² au-dessus de 8 % sur 2 m ou > 0,10 m² au-dessus de 12 % "
       "sur 0,5 m ; la part au-dessus de 5 % est rapportée (tolérance). Unité : surface piétonne.", "implemente")
def ga_tro_004(ctx, R):
    G = grille(ctx)
    gx2, gy2 = pentes(ctx, 10)
    s2 = np.hypot(gx2, gy2) * 100
    Z = G["Z"]
    # base 0,5 m : moyenne des différences décalées (2 et 3 nœuds)
    comps = []
    for di, dj in ((1, 0), (0, 1)):
        za = 0.5 * (K.decaler(Z, -3 * di, -3 * dj, np.nan) + K.decaler(Z, -2 * di, -2 * dj, np.nan))
        zb = 0.5 * (K.decaler(Z, 2 * di, 2 * dj, np.nan) + K.decaler(Z, 3 * di, 3 * dj, np.nan))
        comps.append((za - zb) / 0.5)
    gx5, gy5 = pentes(ctx, 3)
    ok5 = np.isfinite(gx5) & np.isfinite(gy5)
    s05 = np.where(ok5, np.hypot(*comps) * 100, np.nan)
    ped = G["ped"]
    v2 = s2[ped & np.isfinite(s2)]
    R.mesure("pente_2m_pct", stats(v2, (50, 95, 99)))
    R.mesure("part_2m_sup_5pct", r4((v2 > 5).mean(), 3))
    R.mesure("part_2m_sup_8pct", r4((v2 > 8).mean(), 3))
    # même mesure sur la grille du modèle décrit (z0) : part due à la description
    z0 = np.load(ctx.dbase / "nivellement_grille.npz")["z0"].astype(np.float64)
    okm = np.isfinite(gx2) & np.isfinite(gy2)
    gxd = (K.decaler(z0, -10, 0, np.nan) - K.decaler(z0, 10, 0, np.nan)) / 2.0
    gyd = (K.decaler(z0, 0, -10, np.nan) - K.decaler(z0, 0, 10, np.nan)) / 2.0
    vd = (np.hypot(gxd, gyd) * 100)[ped & okm]
    vd = vd[np.isfinite(vd)]
    R.mesure("modele_decrit_pente_2m_pct", stats(vd, (50, 95, 99)))
    R.mesure("modele_decrit_part_2m_sup_8pct", r4((vd > 8).mean(), 3) if len(vd) else None)
    m8 = ped & (s2 > 8)
    m12 = ped & (s05 > 12)
    sid = G["R"]
    a8 = collections.Counter(sid[m8].tolist())
    a12 = collections.Counter(sid[m12].tolist())
    a5 = collections.Counter(sid[ped & (s2 > 5)].tolist())
    for k, s in enumerate(G["ids"]):
        if ctx.surfaces[s]["p"]["classe"] not in K.PIETON:
            continue
        n8, n12 = a8.get(k, 0) * PAS * PAS, a12.get(k, 0) * PAS * PAS
        ok = n8 <= 0.25 and n12 <= 0.10
        if ok:
            R.tester(True)
            continue
        jj, ii = np.nonzero((sid == k) & (m8 | m12))
        vals = np.fmax(np.nan_to_num(s2[jj, ii], nan=-1), np.nan_to_num(s05[jj, ii], nan=-1) * 8 / 12)
        kk = int(np.argmax(vals))
        vals = np.where(vals < 0, np.nan, vals)
        R.tester(False, entite=s, xy=(G["g"][ii[kk]], G["g"][jj[kk]]), valeur=r4(np.nanmax(vals), 1),
                 seuil="≤ 8 % sur 2 m (≤ 0,25 m²), ≤ 12 % sur 0,5 m (≤ 0,10 m²)",
                 detail=f"{n8:.2f} m² > 8 % sur 2 m, {n12:.2f} m² > 12 % sur 0,5 m, {a5.get(k, 0) * PAS * PAS:.1f} m² "
                        f"> 5 % ; {ctx.surfaces[s]['p'].get('sous_classe') or ctx.surfaces[s]['p']['classe']}",
                 ecart=max(n8 / 0.25, n12 / 0.1, np.nanmax(vals) / 8.0))


# =========================================================================== GA-TRO-005
@regle("GA-TRO-005", "les_deux", "mineur",
       "Rampes (surfaces à sous-classe rampe_*) de pente > 4 % : un palier horizontal (≤ 2 %) d'au moins 1,20 × 1,40 m "
       "(1,68 m²) doit exister sur le sol fabriqué dans la bande de 1,5 m au-delà du haut de la rampe. Unité : rampe de "
       "pente décrite ou mesurée > 4 %.", "partiel", "palier bas (zone abaissée) et paliers intermédiaires tous les 10 m "
       "non contrôlés")
def ga_tro_005(ctx, R):
    G = grille(ctx)
    g = G["g"]
    gx, gy = pentes(ctx, 5)
    pen = np.hypot(gx, gy) * 100
    for sid in sorted(ctx.surfaces):
        s = ctx.surfaces[sid]
        rp = s["p"].get("rampe")
        if not rp:
            continue
        k = G["ids"].index(sid)
        m = G["R"] == k
        vals = pen[m & np.isfinite(pen)]
        mes = float(np.median(vals)) if len(vals) else 0.0
        if max(rp.get("pente_pct", 0.0), mes) <= 4.0:
            continue
        zr = G["Z"][m]
        if not np.isfinite(zr).any():
            continue
        zhaut = np.nanmax(zr)
        jj, ii = np.nonzero(m)
        j0, j1 = max(0, jj.min() - 20), min(K.N_GRILLE, jj.max() + 21)
        i0, i1 = max(0, ii.min() - 20), min(K.N_GRILLE, ii.max() + 21)
        ml = m[j0:j1, i0:i1]
        anneau = K.dilater(ml, 15) & ~ml & G["ped"][j0:j1, i0:i1] & (np.abs(G["Z"][j0:j1, i0:i1] - zhaut) < 0.03)
        plat = anneau & (pen[j0:j1, i0:i1] <= 2.0)
        a = plat.sum() * PAS * PAS
        c = (g[ii].mean(), g[jj].mean())
        R.tester(a >= 1.68, entite=sid, xy=c, valeur=r4(a, 2), seuil="palier ≥ 1,68 m² (1,20 × 1,40) à ≤ 2 %",
                 detail=f"rampe {rp.get('id')} : pente décrite {rp.get('pente_pct')} %, mesurée {mes:.1f} % ; palier haut "
                        f"plat trouvé : {a:.2f} m²", ecart=1.68 / max(a, 0.1))


# =========================================================================== GA-TRO-001
def obstacles(ctx):
    """Obstacles ponctuels du mobilier et troncs d'arbres : (id, xy, rayon)."""
    rayons = {"potelet": 0.06, "panneau": 0.05, "lampadaire": 0.10, "support_feux": 0.10, "poteau_reseau": 0.12,
              "poteau_arret": 0.05, "corbeille": 0.25, "banc": 0.35, "armoire": 0.40, "distributeur": 0.40,
              "panneau_information": 0.30, "mobilier_publicitaire": 0.70, "poteau_incendie": 0.12,
              "balise_J11": 0.08, "stationnement_velos": 0.40, "mat_camera": 0.12, "totem_PR": 0.30,
              "boite_aux_lettres": 0.25, "conteneur_verre": 0.70, "fontaine": 0.40}
    out = []
    for f in ctx.mobilier:
        p = f["properties"]
        if f["geometry"]["type"] != "Point" or p.get("x_local") is None:
            continue
        if "absent" in str(p.get("statut_2026", "")):
            continue
        r = rayons.get(p["type"])
        if r:
            out.append((p["id"], np.array([p["x_local"], p["y_local"]]), r, p["type"]))
        if p["type"] == "abri_bus":
            out.append((p["id"], np.array([p["x_local"], p["y_local"]]), 0.75, p["type"]))
    for f in ctx.arbres:
        p = f["properties"]
        if "absent" in str(p.get("statut_2026", "")) or p.get("x_local") is None:
            continue
        out.append((p["id"], np.array([p["x_local"], p["y_local"]]), 0.20, "arbre"))
    return out


@regle("GA-TRO-001", "description", "majeur",
       "Largeur libre des cheminements ≥ 1,40 m : masque piéton (trottoirs, quais, rampes) à 0,10 m, ouverture "
       "morphologique par un disque de 0,70 m de rayon ; parties géométriquement plus étroites que 1,40 m (> 1 m²) ; "
       "les obstacles (mobilier, arbres) sont contrôlés par GA-OBS-001. Unité : surface piétonne.", "implemente")
def ga_tro_001(ctx, R):
    G = grille(ctx)
    g = G["g"]
    ped = np.isin(G["cl"], K.PIETON)
    ouvert = ctx._m("sol:ouvert140", lambda: K.dilater(K.eroder(ped, 7), 7))
    etroit = ped & ~ouvert
    etroit = etroit & ~K.dilater(~ped & ~np.isin(G["cl"], ("emprise_bordure",)), 0)
    gr = grappes_noeuds(ctx, etroit, 0.25)
    par = collections.defaultdict(list)
    for c, a, n, surf, _ in gr:
        if a >= 1.0:
            par[surf[0] if surf else "?"].append((c, a))
    R.mesure("A_parties_etroites_m2", r4(sum(a for v in par.values() for _, a in v), 1))
    for sid in sorted(s for s in ctx.surfaces if ctx.surfaces[s]["p"]["classe"] in K.PIETON):
        cas = par.get(sid, [])
        if not cas:
            R.tester(True)
            continue
        c, a = max(cas, key=lambda x: x[1])
        R.tester(False, entite=sid, xy=c, valeur=r4(a, 2), seuil="largeur ≥ 1,40 m",
                 detail=f"{len(cas)} partie(s) plus étroite(s) que 1,40 m, la plus grande {a:.1f} m²",
                 ecart=a / 1.0)


@regle("GA-OBS-001", "description", "majeur",
       "Mobilier et arbres hors du cheminement de 1,40 m : pour chaque obstacle posé sur un trottoir ou un quai (rayon "
       "forfaitaire par type, tronc 0,20 m : une grille d'arbre conforme compte dans le cheminement), le masque "
       "piéton privé de l'obstacle doit garder une partie ouverte à 1,40 m (disque de 0,70 m) à moins de 1,6 m de "
       "lui ; sinon l'aire perdue est rapportée. Unité : obstacle sur cheminement.", "implemente")
def ga_obs_001(ctx, R):
    G = grille(ctx)
    ped = np.isin(G["cl"], K.PIETON)
    ouvert = ctx._m("sol:ouvert140", lambda: K.dilater(K.eroder(ped, 7), 7))
    for oid, xy, r, typ in sorted(obstacles(ctx), key=lambda t: t[0]):
        j, i = int(round((xy[1] - K.Y0) / PAS)), int(round((xy[0] - K.X0) / PAS))
        if not (0 <= j < K.N_GRILLE and 0 <= i < K.N_GRILLE) or not ped[j, i]:
            continue
        rp = int(math.ceil(r / PAS))
        j0, j1, i0, i1 = max(0, j - 30), min(K.N_GRILLE, j + 31), max(0, i - 30), min(K.N_GRILLE, i + 31)
        loc = ped[j0:j1, i0:i1].copy()
        yy, xx = np.mgrid[j0:j1, i0:i1]
        loc &= (np.hypot(xx - i, yy - j) * PAS > r)
        av = ouvert[j0:j1, i0:i1]
        ap = K.dilater(K.eroder(loc, 7), 7)
        perdu = av & ~ap & loc
        # libre si le passage reste possible d'un côté (composante ouverte voisine de l'obstacle)
        voisin = np.hypot(xx - i, yy - j) * PAS <= r + 1.6
        libre = bool((ap & voisin).any())
        a = perdu.sum() * PAS * PAS
        ok = libre or a < 0.3
        R.tester(ok, entite=f"{oid} ({typ})", xy=xy, valeur=r4(a, 2), seuil="1,40 m libres",
                 detail=f"cheminement réduit sous 1,40 m sur {a:.1f} m² par l'obstacle (rayon {r:.2f} m)",
                 ecart=1 + a)


# =========================================================================== GA-TRO-006
@regle("GA-TRO-006", "description", "majeur",
       "Rupture de niveau > 0,40 m bordant un cheminement (bordures de vue > 0,40 m dont un côté est piéton) : un "
       "garde-corps ou une clôture du mobilier doit longer la bordure (à ≤ 1,0 m sur ≥ 80 % de la longueur). Unité : "
       "bordure concernée.", "implemente")
def ga_tro_006(ctx, R):
    clot = [K.ligne_local(f["geometry"])[0] for f in ctx.mobilier
            if f["geometry"]["type"] == "LineString" and f["properties"]["type"] in ("cloture", "garde_corps", "barriere")]
    A = np.vstack([c[:-1] for c in clot]) if clot else np.zeros((0, 2))
    B = np.vstack([c[1:] for c in clot]) if clot else np.zeros((0, 2))
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        p = b["p"]
        vmax = max(max(it["vue_m"], it.get("vue_m_fin", 0)) for it in p["intervalles"])
        if vmax <= 0.40:
            continue
        s, xy, nrm, _ = echantillons(ctx, bid, 0.5)
        cb, ch = classes_cotes(ctx, bid, xy, nrm, s)
        bas, haut = set(cb.tolist()), set(ch.tolist())
        v = vue_a(p, s)
        m = (v > 0.40) & (np.isin(cb, K.PIETON) | np.isin(ch, K.PIETON))
        if not m.any():
            continue
        d, _, _ = K.C.distance_segments(xy[m], A, B) if len(A) else (np.full(m.sum(), np.inf), None, None)
        part = float((d <= 1.0).mean()) if m.any() else 1.0
        R.tester(part >= 0.8, entite=bid, xy=xy[m][0] if m.any() else xy[0], valeur=r4(vmax, 3),
                 seuil="garde-corps le long de la rupture > 0,40 m",
                 detail=f"vue jusqu'à {vmax:.2f} m ({p['intervalles'][0]['profil']}), longée par une clôture sur "
                        f"{part * 100:.0f} % ; côtés {sorted(bas)} / {sorted(haut)}", ecart=vmax / 0.40)


# =========================================================================== GA-TRO-007
@regle("GA-TRO-007", "les_deux", "majeur",
       "Aucun revêtement meuble (gravillons, BRF, galets, paillage) sur un trottoir ou un quai : matériau décrit des "
       "surfaces piétonnes et matériau des triangles du sol fabriqué sous les nœuds piétons. Unité : surface piétonne.",
       "implemente")
def ga_tro_007(ctx, R):
    G = grille(ctx)
    sol = ctx.fab_couche("sol")
    mats = sol["mats"]
    jj, ii = np.nonzero(G["ped"])
    Q = np.c_[G["g"][ii], G["g"][jj]][::4]
    sid = G["R"][jj, ii][::4]
    _, ti, _ = ctx.requete("sol", 0.5).requete(Q)
    mm = np.where(ti >= 0, mats[sol["mat"][np.maximum(ti, 0)]], "")
    meuble = np.isin(mm, list(MEUBLES))
    par = collections.Counter(sid[meuble].tolist())
    for k, s in enumerate(G["ids"]):
        p = ctx.surfaces[s]["p"]
        if p["classe"] not in K.PIETON:
            continue
        md = p["revetement"]["materiau_id"] in MEUBLES
        nf = par.get(k, 0)
        R.tester(not md and nf == 0, entite=s, xy=ctx.surfaces[s]["poly"][0][0].mean(0), valeur=nf,
                 seuil="aucun matériau meuble", detail=f"décrit {p['revetement']['materiau_id']} ; "
                                                     f"{nf * 0.04:.2f} m² de sol fabriqué meuble", ecart=1 + nf * 0.04)


# =========================================================================== GA-RES-001 / GA-RES-002
@regle("GA-RES-001", "les_deux", "majeur",
       "Ressauts sur cheminement : (a) bordures dont les deux côtés sont piétons (trottoir / quai, classes lues à 0,30 m "
       "de part et d'autre, au moins 1 m) avec une vue > 2 cm hors abaissés (4 cm tolérés avec chanfrein 1/3, non décrit) ; (b) marches > 2 cm entre nœuds voisins du sol "
       "fabriqué à l'intérieur d'une même surface piétonne. Unités : bordure piéton/piéton, surface piétonne.",
       "implemente")
def ga_res_001(ctx, R):
    for bid in sorted(ctx.bordures):
        p = ctx.bordures[bid]["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 0.25)
        cb, ch = classes_cotes(ctx, bid, xy, nrm, s)
        conf = np.isin(ch, K.PIETON) & np.isin(cb, K.PIETON)
        if conf.sum() * 0.25 < 1.0:
            continue
        v = np.where(dans_abaisse(p, s) | ~conf, np.nan, vue_a(p, s))
        vm = float(np.nanmax(v)) if np.isfinite(v).any() else 0.0
        k = int(np.nanargmax(v)) if np.isfinite(v).any() else 0
        R.tester(vm <= 0.02 + 1e-6, entite=bid, xy=xy[k], valeur=r4(vm, 3), seuil="≤ 0,02 m",
                 detail=f"(a) bordure entre deux cheminements sur {conf.sum() * 0.25:.1f} m, vue {vm:.3f} m",
                 ecart=vm / 0.02)
    G = grille(ctx)
    Z = G["Z"]
    Rr = G["R"]
    m = np.zeros(Z.shape, bool)
    for di, dj in ((1, 0), (0, 1)):
        z2 = K.decaler(Z, -di, -dj, np.nan)
        r2 = K.decaler(Rr, -di, -dj, -9)
        m |= G["ped"] & (r2 == Rr) & (np.abs(Z - z2) > 0.02)
    par = collections.defaultdict(list)
    for c, a, n, surf, _ in grappes_noeuds(ctx, m, 0.25):
        par[surf[0] if surf else "?"].append((c, n))
    for k, s in enumerate(G["ids"]):
        if ctx.surfaces[s]["p"]["classe"] not in K.PIETON:
            continue
        cas = par.get(s, [])
        if not cas:
            R.tester(True)
            continue
        c, n = max(cas, key=lambda x: x[1])
        R.tester(False, entite=s, xy=c, valeur=n, seuil="aucune marche > 0,02 m dans la surface",
                 detail=f"(b) {len(cas)} marche(s) > 2 cm dans la surface (la plus longue : {n} nœuds)", ecart=1 + n / 10)


@regle("GA-RES-002", "fabrication", "mineur",
       "Fentes des cheminements < 2 cm : largeur des joints de bordure posés (points/bordures.json, longueur des "
       "bouchons de joint) ; aucune grille ni caniveau à fente n'est décrit. Unité : joint.", "partiel",
       "grilles d'avaloir et d'arbre absentes de la description")
def ga_res_002(ctx, R):
    for p in ctx.points("bordures")["points"]:
        if p["x"].get("type") != "joint":
            continue
        w = float(p["x"]["longueur_m"])
        R.tester(w < 0.02, entite=p["id"], xy=p["p"], valeur=r4(w, 4), seuil="< 0,02 m", ecart=w / 0.02)


# =========================================================================== GA-ABA-004
CH = re.compile(r"chartiere_([A-Z0-9]+?)(\d{3})_([A-Z0-9]+?)(\d{3})_L(\d+)")


@regle("GA-ABA-004", "les_deux", "majeur",
       "Rampants latéraux des abaissés : pente = Δvue / longueur de chaque raccord décrit (≤ 8 % ; 12 % toléré sur "
       "≤ 0,50 m) et de chaque chartière posée (asset chartiere_<profil><vue mm>_<profil><vue mm>_L<mm> de "
       "points/bordures.json). Les chartières levées au GAM sont signalées en mineur. Unités : raccord décrit, "
       "chartière posée.", "implemente")
def ga_aba_004(ctx, R):
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        for a in b["p"]["abaisses"]:
            obs = (a.get("rampe") or {}).get("chartiere_observee")
            for r in a.get("raccords", []):
                L = r["s1"] - r["s0"]
                if L <= 1e-6:
                    continue
                pente = abs(r["vue_m"] - r["vue_m_fin"]) / L * 100
                lim = 12.0 if L <= 0.5 + 1e-6 else 8.0
                xy = K.point(b["P"][:, :2], (r["s0"] + r["s1"]) / 2)
                R.tester(pente <= lim + 1e-6, entite=f"{a['id']} ({r['cote']})", xy=xy, valeur=r4(pente, 2),
                         seuil=f"≤ {lim:.0f} %", detail=f"raccord décrit {r['vue_m']:.3f} -> {r['vue_m_fin']:.3f} m sur "
                                                        f"{L:.2f} m" + (" (chartière levée GAM)" if obs else ""),
                         ecart=pente / lim, severite="mineur" if obs else None)
    for p in ctx.points("bordures")["points"]:
        m = CH.match(p["asset"])
        if not m:
            continue
        v0, v1, L = int(m.group(2)) / 1000, int(m.group(4)) / 1000, int(m.group(5)) / 1000 * p["s"][0]
        pente = abs(v0 - v1) / max(L, 1e-6) * 100
        lim = 12.0 if L <= 0.5 + 1e-6 else 8.0
        R.tester(pente <= lim + 1e-6, entite=p["id"], xy=p["p"], valeur=r4(pente, 2), seuil=f"≤ {lim:.0f} %",
                 detail=f"chartière posée {v0:.3f} -> {v1:.3f} m sur {L:.3f} m ({p['asset']})", ecart=pente / lim)


# =========================================================================== GA-BEV-002 / GA-BEV-005 / GA-BEV-006
@regle("GA-BEV-002", "les_deux", "mineur",
       "Pas de freinage : distance de l'arête avant (nez) de la bordure d'ancrage à la première rangée de la BEV = "
       "0,50 ± 0,02 m, sur le polygone décrit et sur le maillage fabriqué (BEV_xxxx de sol.usdc : 2e centile des "
       "distances de ses sommets au nez). Unité : BEV × (description, fabrication).", "implemente")
def ga_bev_002(ctx, R):
    sol = ctx.fab_couche("sol")
    ents = ctx.fab_entites("sol")
    for bid in sorted(ctx.ponctuels):
        v = ctx.ponctuels[bid]
        a = v["p"].get("ancrage") or {}
        if v["p"].get("type") != "bev" or a.get("bordure") not in ctx.bordures:
            continue
        P = ctx.bordures[a["bordure"]]["P"][:, :2]
        Pz = K.C.sous_polyligne(P, a["s0"] - 0.5, a["s1"] + 0.5) if hasattr(K.C, "sous_polyligne") else P
        poly = v["poly"][0][0]
        d = K.dist_polyligne(poly, Pz)
        dm = float(d.min())
        R.tester(abs(dm - 0.5) <= 0.02 + 1e-6, entite=bid + " (description)", xy=poly.mean(0), valeur=r4(dm, 3),
                 seuil="0,50 ± 0,02 m", detail=f"nez {a['bordure']} -> BEV décrite {dm:.3f} m", ecart=abs(dm - 0.5) / 0.02)
        e = bid.replace("-", "_")
        if e in ents:
            TB = sol["T"][ents[e]].reshape(-1, 3).astype(np.float64)
            df = float(np.percentile(K.dist_polyligne(TB[:, :2], Pz), 2))
            R.tester(abs(df - 0.5) <= 0.02 + 1e-6, entite=bid + " (fabriquée)", xy=poly.mean(0), valeur=r4(df, 3),
                     seuil="0,50 ± 0,02 m", detail=f"nez {a['bordure']} -> maillage BEV {df:.3f} m",
                     ecart=abs(df - 0.5) / 0.02)


def luminance(rgb):
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


@regle("GA-BEV-005", "description", "mineur",
       "Contraste de luminance BEV / support ≥ 0,70 : (Lmax − Lmin) / Lmax avec les albédos linéaires cibles de "
       "materiaux_sol.json (bev_podotactile contre le revêtement de la surface piétonne sous la BEV). Unité : BEV.",
       "implemente")
def ga_bev_005(ctx, R):
    mats = ctx.spec("materiaux_sol")["materiaux"]
    Lb = luminance(mats["bev_podotactile"]["albedo_cible_lineaire"])
    G = grille(ctx)
    for bid in sorted(ctx.ponctuels):
        v = ctx.ponctuels[bid]
        if v["p"].get("type") != "bev":
            continue
        poly = v["poly"][0][0]
        a = v["p"]["ancrage"]
        P = ctx.bordures[a["bordure"]]["P"][:, :2]
        c = poly.mean(0)
        _, d_, side = K.C.projeter(P, c[None])
        s_, xy, nrm, _ = echantillons(ctx, a["bordure"], 0.5)
        # point du trottoir à 1,2 m derrière le nez, au milieu de la BEV
        k = int(np.argmin(np.hypot(*(xy - c).T)))
        q = xy[k] + 1.2 * nrm[k]
        j, i = int(round((q[1] - K.Y0) / PAS)), int(round((q[0] - K.X0) / PAS))
        sid = G["ids"][G["R"][j, i]] if G["R"][j, i] >= 0 else None
        mat = ctx.surfaces[sid]["p"]["revetement"]["materiau_id"] if sid else None
        if mat not in mats:
            R.tester(False, entite=bid, xy=c, detail=f"support inconnu ({sid}, {mat})", seuil="support décrit")
            continue
        Ls = luminance(mats[mat]["albedo_cible_lineaire"])
        ct = (max(Lb, Ls) - min(Lb, Ls)) / max(Lb, Ls)
        R.tester(ct >= 0.70, entite=bid, xy=c, valeur=r4(ct, 3), seuil="≥ 0,70",
                 detail=f"BEV L = {Lb:.3f} sur {mat} ({sid}) L = {Ls:.3f}", ecart=0.70 / max(ct, 0.01))


@regle("GA-BEV-006", "description", "mineur",
       "Les supports de feux portant une tête piétonne R12 (mobilier support_feux) ne sont pas posés sur une BEV "
       "(distance au polygone de BEV > 0,05 m). Unité : support portant un R12.", "partiel",
       "position « dans le prolongement du marquage » non contrôlée")
def ga_bev_006(ctx, R):
    bevs = [v["poly"][0] for v in ctx.ponctuels.values() if v["p"].get("type") == "bev"]
    for f in sorted(ctx.mobilier, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p["type"] != "support_feux" or not p.get("nb_tetes_R12"):
            continue
        xy = np.array([p["x_local"], p["y_local"]])
        dedans = bool(K.dans_liste(xy[None], [[b[0]] for b in bevs])[0]) if bevs else False
        d = float(K.dist_polys(xy[None], [[b[0]] for b in bevs])[0]) if bevs else np.inf
        R.tester(not dedans and d > 0.05, entite=p["id"], xy=xy, valeur=r4(d, 2), seuil="hors BEV",
                 detail=f"support R12 à {d:.2f} m d'une BEV" + (" (dedans)" if dedans else ""))


# =========================================================================== GA-BOR-001
@regle("GA-BOR-001", "description", "majeur",
       "Hors abaissés, une bordure entre un espace piéton (côté haut : trottoir / quai à largeur + 0,30 m derrière la "
       "face) et un espace circulé (côté bas : chaussée, parking, piste, accès à 0,30 m devant) a une vue ≥ 0,05 m "
       "(détectable à la canne). Classes lues sur la partition, échantillons tous les 0,10 m. Unité : bordure ayant au "
       "moins 1 m dans cette configuration ; longueur non conforme rapportée.", "implemente")
def ga_bor_001(ctx, R):
    for bid in sorted(ctx.bordures):
        p = ctx.bordures[bid]["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 0.1)
        cb, ch = classes_cotes(ctx, bid, xy, nrm, s)
        conf = np.isin(ch, K.PIETON) & np.isin(cb, K.CIRCULE)
        if conf.sum() * 0.1 < 1.0:
            continue
        v = vue_a(p, s)
        m = conf & (v < 0.05 - 1e-6) & ~dans_abaisse(p, s, 0.05)
        L = m.sum() * 0.1
        k = int(np.argmin(np.where(m, v, 9))) if m.any() else 0
        R.tester(L <= 0.3, entite=bid, xy=xy[k], valeur=r4(L, 1), seuil="vue ≥ 0,05 m hors abaissés",
                 detail=f"{L:.1f} m sur {conf.sum() * 0.1:.1f} m piéton/circulé sous 0,05 m (vue min "
                        f"{np.nanmin(np.where(m, v, np.nan)) if m.any() else 0:.3f} m)", ecart=1 + L / 2)


# =========================================================================== GA-BOR-005
def contacts(ctx):
    """Contacts entre bordures : bout d'une bordure à < 0,20 m d'une autre (bout ou intérieur)."""
    def f():
        out = []
        ids = sorted(ctx.bordures)
        segs = {b: (ctx.bordures[b]["P"][:-1, :2], ctx.bordures[b]["P"][1:, :2]) for b in ids}
        for a in ids:
            P = ctx.bordures[a]["P"][:, :2]
            for bout, q, sa in (("debut", P[0], 0.0), ("fin", P[-1], float(ctx.bordures[a]["s"][-1]))):
                for b in ids:
                    if b == a:
                        continue
                    A, B = segs[b]
                    lo = np.minimum(A, B).min(0) - 0.25
                    hi = np.maximum(A, B).max(0) + 0.25
                    if not (lo[0] <= q[0] <= hi[0] and lo[1] <= q[1] <= hi[1]):
                        continue
                    sb, d, _ = K.C.projeter(ctx.bordures[b]["P"][:, :2], q[None])
                    if d[0] <= 0.20:
                        out.append((a, bout, sa, b, float(sb[0]), float(d[0]), q))
        return out
    return ctx._m("sol:contacts", f)


@regle("GA-BOR-005", "les_deux", "majeur",
       "Contacts entre bordures (bout d'une bordure à moins de 0,20 m d'une autre). Bout à bout (à moins de 0,20 m du "
       "bout de l'autre) : écart de tête ≤ 0,02 m et de pied ≤ 0,01 m (nivellement.json) et écart de dessus des "
       "maillages fabriqués ≤ 0,02 m. En T contre la face (côté bas de l'autre) : pieds ≤ 0,01 m et tête ≤ tête de "
       "l'autre + 0,02 m ; en T contre le dos (côté haut) : pied ≤ 0,01 m de l'arête arrière de l'autre. Dessus "
       "fabriqué : maximum sur la largeur de l'élément près du point de contact. Unité : contact.", "implemente")
def ga_bor_005(ctx, R):
    vus = set()
    compte = collections.Counter()
    for a, bout, sa, b, sb, d, q in contacts(ctx):
        cle = tuple(sorted((a, b))) + (round(q[0], 1), round(q[1], 1))
        if cle in vus:
            continue
        vus.add(cle)
        Lb = float(ctx.bordures[b]["s"][-1])
        bout_a_bout = sb <= 0.20 or sb >= Lb - 0.20
        pa, ta, ra = ctx.niv.z_bordure(a, [sa])
        pb, tb, rb = ctx.niv.z_bordure(b, [sb])
        pa, ta, pb, tb, rb = float(pa[0]), float(ta[0]), float(pb[0]), float(tb[0]), float(rb[0])
        # dessus fabriqués près du contact (côté de chaque bordure)
        sA = np.array([max(0.05, min(sa, ctx.bordures[a]["s"][-1] - 0.05))])
        sB = np.array([max(0.05, min(sb, Lb - 0.05))])
        _, xa, na, tga = echantillons_a(ctx, a, sA)
        _, xb, nb_, tgb = echantillons_a(ctx, b, sB)
        fa = dessus_bordure(ctx, a, xa, na, tga, largeur_base(ctx.bordures[a]["p"], sA))[0]
        fb = dessus_bordure(ctx, b, xb, nb_, tgb, largeur_base(ctx.bordures[b]["p"], sB))[0]
        cote_b = float((q - xb[0]) @ nb_[0])
        if bout_a_bout:
            genre = "bout à bout"
            dt, dp = abs(ta - tb), abs(pa - pb)
            df = abs(fa - fb) if np.isfinite(fa) and np.isfinite(fb) else 0.0
        elif cote_b < 0:
            genre = "en T contre la face"
            dt, dp = max(0.0, ta - tb), abs(pa - pb)
            df = max(0.0, fa - fb) if np.isfinite(fa) and np.isfinite(fb) else 0.0
        else:
            genre = "en T contre le dos"
            dt, dp, df = 0.0, abs(pa - rb), 0.0
        ok = dt <= 0.02 + 1e-6 and dp <= 0.01 + 1e-6 and df <= 0.02 + 1e-6
        compte[genre] += 1
        compte["tete_sup_2cm"] += dt > 0.02 + 1e-6
        compte["pied_sup_1cm"] += dp > 0.01 + 1e-6
        compte["dessus_fabrique_sup_2cm"] += df > 0.02 + 1e-6
        R.tester(ok, entite=f"{a} ({bout}) / {b}", xy=q, valeur=r4(max(dt, df), 4),
                 seuil="tête ≤ 0,02, pied ≤ 0,01 (fabriqué ≤ 0,02)",
                 detail=f"{genre} : écart de tête décrit {dt * 100:.1f} cm, de pied {dp * 100:.1f} cm, de dessus "
                        f"fabriqué {df * 100:.1f} cm", ecart=max(dt / 0.02, dp / 0.01, df / 0.02))
    R.mesure("contacts", len(vus))
    R.mesure("ecarts", dict(sorted((k, int(v)) for k, v in compte.items())))


def echantillons_a(ctx, bid, s):
    """Comme echantillons, à des abscisses données."""
    b = ctx.bordures[bid]
    P, S = b["P"][:, :2], b["s"]
    s = np.asarray(s, float)
    k = np.clip(np.searchsorted(S, s, side="right") - 1, 0, len(S) - 2)
    t = (s - S[k]) / np.maximum(S[k + 1] - S[k], 1e-12)
    xy = P[k] + (P[k + 1] - P[k]) * t[:, None]
    tg = P[k + 1] - P[k]
    tg /= np.maximum(np.hypot(*tg.T), 1e-12)[:, None]
    return s, xy, np.c_[-tg[:, 1], tg[:, 0]], tg


# =========================================================================== VAL-KRB-005
@regle("VAL-KRB-005", "les_deux", "majeur",
       "Bordures finales : (a) écart plan des sommets décrits (tous les 0,5 m) à la ligne GAM 2026 la plus proche, p95 "
       "≤ 0,05 m (bordures de source GAM) ; (b) vue décrite à ±0,02 m de la marche LiDAR des tronçons « mesuree » "
       "(bordures_hauteurs, hors zone de travaux 2025 et hors abaissés) ; (c) abaissés de traversée à 0,02 ± 0,005 m "
       "et ≥ 1,20 m ; (d) vue posée (dessus du maillage fabriqué, maximum sur la largeur de l'élément et sur ±2 cm le "
       "long de la bordure − sol fabriqué à 3 cm devant la face) à ±0,005 m "
       "sur les bateaux de traversée et ±0,02 m ailleurs. Unités : bordure (a, d), tronçon LiDAR (b), abaissé (c).",
       "implemente")
def val_krb_005(ctx, R):
    gam = [K.ligne_local(f["geometry"])[0] for f in ctx.gam("bordure_lin")]
    A = np.vstack([g[:-1] for g in gam])
    B = np.vstack([g[1:] for g in gam])
    ecarts = []
    for bid in sorted(ctx.bordures):
        p = ctx.bordures[bid]["p"]
        if (p["prov"].get("geometrie") or {}).get("src") != "gam":
            continue
        s, xy, _, _ = echantillons(ctx, bid, 0.5)
        d, _, _ = K.C.distance_segments(xy, A, B)
        ecarts.append(d)
        p95 = float(np.percentile(d, 95))
        k = int(np.argmax(d))
        R.tester(p95 <= 0.05, entite=bid, xy=xy[k], valeur=r4(p95, 3), seuil="p95 ≤ 0,05 m",
                 detail=f"(a) écart au levé GAM p95 {p95 * 100:.1f} cm, max {d.max() * 100:.1f} cm", ecart=p95 / 0.05)
    if ecarts:
        R.mesure("a_ecart_plan_gam_m", stats(np.concatenate(ecarts), (50, 95, 99)))
    # (b) vues LiDAR
    ids = sorted(ctx.bordures)
    segsA = np.vstack([ctx.bordures[b]["P"][:-1, :2] for b in ids])
    segsB = np.vstack([ctx.bordures[b]["P"][1:, :2] for b in ids])
    own = np.concatenate([np.full(len(ctx.bordures[b]["P"]) - 1, k) for k, b in enumerate(ids)])
    bh = [f for f in ctx.bordures_hauteurs if f["properties"].get("statut") == "mesuree"
          and not f["properties"].get("zone_travaux_2025")]
    mil = np.array([K.ligne_local(f["geometry"])[0].mean(0) for f in bh])
    d, js, _ = K.C.distance_segments(mil, segsA, segsB)
    dv_all = []
    for f, q, dd, j in zip(bh, mil, d, js):
        if dd > 0.30:
            continue
        bid = ids[own[j]]
        p = ctx.bordures[bid]["p"]
        sb, _, _ = K.C.projeter(ctx.bordures[bid]["P"][:, :2], q[None])
        if dans_abaisse(p, sb, 0.3)[0]:
            continue
        v = float(vue_a(p, sb)[0])
        h = float(f["properties"]["h_vue_m"])
        dv = v - h
        dv_all.append(dv)
        R.tester(abs(dv) <= 0.02 + 1e-6, entite=f"{f['properties']['id']} -> {bid}", xy=q, valeur=r4(dv, 3),
                 seuil="±0,02 m", detail=f"(b) vue décrite {v:.3f} m, marche LiDAR {h:.3f} m", ecart=abs(dv) / 0.02,
                 severite="mineur")
    R.mesure("b_vue_moins_lidar_m", stats(np.abs(dv_all), (50, 95)))
    # (c) abaissés
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        for a in b["p"]["abaisses"]:
            if a["type"] != "traversee":
                continue
            L = a["s1"] - a["s0"]
            ok = abs(a["vue_m"] - 0.02) <= 0.005 + 1e-6 and L >= 1.20 - 1e-3
            R.tester(ok, entite=a["id"], xy=K.point(b["P"][:, :2], (a["s0"] + a["s1"]) / 2), valeur=r4(a["vue_m"], 3),
                     seuil="vue 0,02 ± 0,005, ≥ 1,20 m", detail=f"(c) vue {a['vue_m']:.3f} m sur {L:.2f} m",
                     ecart=max(abs(a["vue_m"] - 0.02) / 0.005, 1.2 / max(L, 0.1)))
    # (d) vue posée
    bor = ctx.fab_couche("bordures")
    ents = ctx.fab_entites("bordures")
    dvp = []
    for bid in sorted(ctx.bordures):
        e = bid.replace("-", "_")
        if e not in ents:
            R.tester(False, entite=bid, detail="(d) bordure absente de bordures.usdc", seuil="présente")
            continue
        p = ctx.bordures[bid]["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 1.0, 0.25)
        _, _, _, tg = echantillons(ctx, bid, 1.0, 0.25)
        zt = dessus_bordure(ctx, bid, xy, nrm, tg, largeur_base(p, s))
        zs = requete_sol(ctx, xy - 0.03 * nrm)
        vp = zt - zs
        v = vue_a(p, s)
        bateau = np.zeros(len(s), bool)
        for a in p["abaisses"]:
            if a["type"] == "traversee":
                bateau |= (s >= a["s0"] + 0.2) & (s <= a["s1"] - 0.2)
        tol = np.where(bateau, 0.005, 0.02)
        d_ = vp - v
        ok = np.isfinite(d_)
        if not ok.any():
            continue
        dvp.append(d_[ok])
        r_ = np.abs(d_) / tol
        k = int(np.nanargmax(np.where(ok, r_, -1)))
        R.tester(r_[k] <= 1.0 + 1e-6, entite=bid, xy=xy[k], valeur=r4(d_[k], 4),
                 seuil="±0,005 (bateau de traversée), ±0,02 m", detail=f"(d) vue posée {vp[k]:.3f} m pour {v[k]:.3f} m "
                                                                         f"décrite (s = {s[k]:.1f} m)", ecart=r_[k])
    if dvp:
        R.mesure("d_vue_posee_moins_decrite_m", stats(np.concatenate(dvp), (5, 50, 95)))


# =========================================================================== TQ-BOR-007 / TQ-BOR-005 / TQ-BOR-002
@regle("TQ-BOR-007", "fabrication", "majeur",
       "Interfaces sol / bordure / caniveau : le sol fabriqué existe sous chaque élément à 12 mm et 30 mm derrière la "
       "face (recouvrement ≥ flèche + 1,5 mm) au niveau du pied (±5 mm) ; côté caniveau, le sol à 2 cm devant le bord "
       "du caniveau (0,25 m devant la face) a le Z du bord du caniveau fabriqué à ±3 mm. Unité : bordure.",
       "implemente")
def tq_bor_007(ctx, R):
    can = ctx.requete("caniveaux", 0.25)
    for bid in sorted(ctx.bordures):
        p = ctx.bordures[bid]["p"]
        s, xy, nrm, _ = echantillons(ctx, bid, 0.5, 0.15)
        pied, _, _ = ctx.niv.z_bordure(bid, s)
        z12 = requete_sol(ctx, xy + 0.012 * nrm)
        z30 = requete_sol(ctx, xy + 0.030 * nrm)
        manque = ~np.isfinite(z12) | ~np.isfinite(z30)
        ec = np.nanmax(np.abs(np.r_[z12 - pied, z30 - pied])) if np.isfinite(np.r_[z12, z30]).any() else 0.0
        det, ecart = None, 1.0
        if manque.any():
            k = int(np.nonzero(manque)[0][0])
            det, ecart, pt = f"pas de sol sous l'élément à s = {s[k]:.1f} m ({manque.sum()} sondes)", 2 + manque.sum(), xy[k]
        elif ec > 0.005:
            d_ = np.abs(np.r_[z12 - pied, z30 - pied])
            k = int(np.nanargmax(d_)) % len(s)
            det, ecart, pt = f"sol sous l'élément à {ec * 1000:.0f} mm du pied (s = {s[k]:.1f} m)", ec / 0.005, xy[k]
        cv = p.get("caniveau")
        if det is None and cv:
            q_bord = xy - 0.25 * nrm
            zc, _, _ = can.requete(q_bord + 0.01 * nrm)
            zs = requete_sol(ctx, q_bord - 0.02 * nrm)
            d_ = zs - zc
            if np.isfinite(d_).any() and np.nanmax(np.abs(d_)) > 0.003:
                k = int(np.nanargmax(np.abs(d_)))
                det, ecart, pt = f"enrobé − bord du caniveau {d_[k] * 1000:+.0f} mm (s = {s[k]:.1f} m)", \
                    abs(d_[k]) / 0.003, q_bord[k]
            elif not np.isfinite(zc).any():
                det, ecart, pt = "caniveau décrit absent de caniveaux.usda", 2.0, xy[0]
        if det is None:
            R.tester(True)
        else:
            R.tester(False, entite=bid, xy=pt, valeur=r4(ec, 4), seuil="sol sous l'élément au pied ±5 mm ; caniveau ±3 mm",
                     detail=det, ecart=ecart)


@regle("TQ-BOR-005", "fabrication", "mineur",
       "Non-transparence des joints (sans lancer de rayons) : chaque joint posé a une largeur de 3,5 à 9,5 mm, un "
       "bouchon de mortier (point « joint » de points/bordures.json, mortier présent dans bordures.usdc) et du sol "
       "sous la bordure à 0,10 m derrière la face. Unité : joint.", "partiel", "lancer de rayons depuis 1,2-1,6 m non fait")
def tq_bor_005(ctx, R):
    mats = set(map(str, ctx.fab_couche("bordures")["mats"]))
    mortier = bool(mats & {"mortier_joint", "mortier_clair"})
    pts = [p for p in ctx.points("bordures")["points"] if p["x"].get("type") == "joint"]
    Q = []
    for p in pts:
        qx, qy, qz, qw = p["q"]
        # axe +Y du prototype (vers l'arrière) en local
        y_ax = np.array([2 * (qx * qy - qw * qz), 1 - 2 * (qx * qx + qz * qz)])
        Q.append(np.array(p["p"][:2]) + 0.10 * y_ax / max(np.hypot(*y_ax), 1e-9))
    z = requete_sol(ctx, np.array(Q)) if Q else np.zeros(0)
    for p, zz in zip(pts, z):
        w = float(p["x"]["longueur_m"])
        ok = 0.0035 - 1e-6 <= w <= 0.0095 + 1e-6 and mortier and np.isfinite(zz)
        R.tester(ok, entite=p["id"], xy=p["p"], valeur=r4(w * 1000, 2), seuil="3,5-9,5 mm, mortier, sol derrière",
                 detail=f"joint {w * 1000:.1f} mm" + ("" if np.isfinite(zz) else ", pas de sol derrière"),
                 ecart=max(w / 0.0095, 0.0035 / max(w, 1e-4)))


@regle("TQ-BOR-002", "fabrication", "mineur",
       "Éléments de bordure et de caniveau posés en instances rigides (points/bordures.json, caniveaux.json) : échelles "
       "Y et Z = 1, échelle X des éléments dans [0,2 ; 1,05] (coupes, pente 1/cos), aucune déformation de type spline. "
       "Unité : élément.", "implemente")
def tq_bor_002(ctx, R):
    for fam in ("bordures", "caniveaux"):
        for p in ctx.points(fam)["points"]:
            if p["x"].get("type") == "joint":
                continue
            sx, sy, sz = p["s"]
            ok = abs(sy - 1) < 1e-6 and abs(sz - 1) < 1e-6 and 0.2 <= sx <= 1.05
            R.tester(ok, entite=p["id"], xy=p["p"], valeur=r4(sx, 4), seuil="sy = sz = 1, sx dans [0,2 ; 1,05]",
                     detail=f"s = {p['s']}", ecart=2.0)


# =========================================================================== TQ-PCG-001
def quat_rpy(q):
    x, y, z, w = q
    R_ = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                   [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                   [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return R_


def rpy_mat(r, p, y):
    r, p, y = map(math.radians, (r, p, y))
    Rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
    Ry = np.array([[math.cos(p), 0, math.sin(p)], [0, 1, 0], [-math.sin(p), 0, math.cos(p)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(r), -math.sin(r)], [0, math.sin(r), math.cos(r)]])
    return Rz @ Ry @ Rx


@regle("TQ-PCG-001", "fabrication", "majeur",
       "Transport canonique des instances (pj_points/0.1) : schéma, q unitaire [x, y, z, w], concordance q / rpy_deg à "
       "0,05° (sinon charger_points refuse le fichier), échelle positive, et pour les éclats d'îlot échelle = taille "
       "décrite (x.taille_m). Unité : point de bordures, caniveaux, îlots, symboles.", "implemente")
def tq_pcg_001(ctx, R):
    for fam in ("bordures", "caniveaux", "ilots", "symboles"):
        doc = ctx.points(fam)
        sch = doc.get("schema") == "pj_points/0.1"
        for p in doc["points"]:
            q = np.array(p["q"], float)
            nq = float(np.linalg.norm(q))
            ang = 0.0
            if p.get("rpy_deg") is not None:
                Ra = quat_rpy(q / max(nq, 1e-12))
                Rb = rpy_mat(*p["rpy_deg"])
                c = (np.trace(Ra.T @ Rb) - 1) / 2
                ang = math.degrees(math.acos(max(-1.0, min(1.0, c))))
            ech = all(v > 0 for v in p["s"])
            taille = (p.get("x") or {}).get("taille_m")
            ok_t = True
            if taille is not None:
                ok_t = abs(max(p["s"]) - float(taille)) <= 0.25 * float(taille) + 1e-4
            ok = sch and abs(nq - 1) < 1e-3 and ang <= 0.05 and ech and ok_t
            det = []
            if abs(nq - 1) >= 1e-3:
                det.append(f"|q| = {nq:.4f}")
            if ang > 0.05:
                det.append(f"q / rpy écart {ang:.3f}°")
            if not ok_t:
                det.append(f"échelle {max(p['s']):.4f} pour taille {float(taille):.4f} m")
            R.tester(ok, entite=p["id"], xy=p["p"], valeur=r4(ang, 3), seuil="q unitaire, q/rpy ≤ 0,05°",
                     detail=f"{fam} : " + ", ".join(det), ecart=max(ang / 0.05, 1.0 if ok_t else 3.0))


# =========================================================================== GA-OBS-002 / GA-OBS-003 / GA-ARB-005
@regle("GA-OBS-002", "description", "mineur",
       "Potelets et bornes sur cheminement (mobilier potelet, balise_J11) : hauteur ≥ 0,50 m ; entraxe de deux potelets "
       "voisins (< 3 m) dans [1,30 ; 1,60] m (1,30 minimum absolu). Unité : potelet.", "partiel",
       "diamètre à 0,50 m (abaque) et bande contrastée non décrits")
def ga_obs_002(ctx, R):
    pts = [(f["properties"]["id"], np.array([f["properties"]["x_local"], f["properties"]["y_local"]]),
            f["properties"].get("hauteur_m")) for f in ctx.mobilier
           if f["properties"]["type"] in ("potelet", "balise_J11") and f["geometry"]["type"] == "Point"]
    for k, (pid, xy, h) in enumerate(sorted(pts, key=lambda t: t[0])):
        autres = [np.hypot(*(xy - q)) for j, (_, q, _) in enumerate(sorted(pts, key=lambda t: t[0])) if j != k]
        dmin = min([d for d in autres if d < 3.0], default=None)
        ok_h = h is None or h >= 0.5
        ok_e = dmin is None or dmin >= 1.30
        R.tester(ok_h and ok_e, entite=pid, xy=xy, valeur=r4(dmin if dmin is not None else h, 2),
                 seuil="h ≥ 0,50 m, entraxe ≥ 1,30 m", detail=f"hauteur {h}, entraxe au plus proche {dmin}",
                 ecart=max(0.5 / max(h or 0.5, 0.05), 1.3 / max(dmin or 1.3, 0.05)))


@regle("GA-OBS-003", "description", "mineur",
       "Barrières et clôtures (mobilier LineString) à moins de 3 m d'une bordure de chaussée : recul ≥ 0,30 m depuis "
       "l'arête avant (nez) de la bordure. Unité : barrière proche d'une chaussée.", "implemente")
def ga_obs_003(ctx, R):
    A, B = kerbs_chaussee_index(ctx)
    for f in sorted(ctx.mobilier, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if f["geometry"]["type"] != "LineString" or p["type"] not in ("cloture", "barriere", "garde_corps"):
            continue
        L = K.densifier(K.ligne_local(f["geometry"])[0], 0.25)
        d, _, _ = K.C.distance_segments(L, A, B)
        if d.min() > 3.0:
            continue
        k = int(np.argmin(d))
        R.tester(d.min() >= 0.30, entite=p["id"], xy=L[k], valeur=r4(d.min(), 2), seuil="≥ 0,30 m du nez",
                 detail=f"{p['type']} à {d.min():.2f} m d'une bordure de chaussée", ecart=0.30 / max(d.min(), 0.01))


@regle("GA-ARB-005", "description", "mineur",
       "Arbres plantés en 2025 ou déduits (statut « planté 2025 », « à vérifier ») : tronc à ≥ 1,00 m (moyen "
       "développement) du nez d'une bordure de chaussée, 1,50 m si la hauteur dépasse 15 m. Unité : arbre concerné.",
       "partiel", "limites de propriété privée inconnues")
def ga_arb_005(ctx, R):
    A, B = kerbs_chaussee_index(ctx)
    for f in sorted(ctx.arbres, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        st = str(p.get("statut_2026", ""))
        if not ("plant" in st or "rifier" in st):
            continue
        xy = np.array([p["x_local"], p["y_local"]])
        d, _, _ = K.C.distance_segments(xy[None], A, B)
        lim = 1.5 if (p.get("hauteur_m") or 0) > 15 else 1.0
        R.tester(d[0] >= lim, entite=p["id"], xy=xy, valeur=r4(d[0], 2), seuil=f"≥ {lim:.2f} m",
                 detail=f"{st} : tronc à {d[0]:.2f} m d'une bordure de chaussée", ecart=lim / max(d[0], 0.05))


# =========================================================================== GA-ABA-008
@regle("GA-ABA-008", "description", "mineur",
       "Abaissés de traversée sur un point bas du fil d'eau (pied décrit plus bas au milieu de l'abaissé qu'aux deux "
       "bouts de plus de 5 mm) : vue ≥ 0,02 m et avaloir en amont (ponctuels_sol). Unité : abaissé de traversée.",
       "implemente")
def ga_aba_008(ctx, R):
    avaloirs = [v for v in ctx.ponctuels.values() if v["p"].get("type") in ("avaloir", "grille")]
    for bid in sorted(ctx.bordures):
        b = ctx.bordures[bid]
        for a in b["p"]["abaisses"]:
            if a["type"] != "traversee":
                continue
            s = np.linspace(a["s0"] - 1.0, a["s1"] + 1.0, 21)
            s = np.clip(s, 0, b["s"][-1])
            pied, _, _ = ctx.niv.z_bordure(bid, s)
            bas = pied[5:16].min() < min(pied[0], pied[-1]) - 0.005
            ok = (a["vue_m"] >= 0.02 - 1e-6) and (not bas or bool(avaloirs))
            R.tester(ok, entite=a["id"], xy=K.point(b["P"][:, :2], (a["s0"] + a["s1"]) / 2), valeur=r4(a["vue_m"], 3),
                     seuil="vue ≥ 0,02 ; avaloir si point bas",
                     detail=("point bas du fil d'eau sans avaloir" if bas else "") + (
                         f" vue {a['vue_m']:.3f}" if a["vue_m"] < 0.02 else ""), ecart=1.5)
