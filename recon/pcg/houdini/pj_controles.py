"""pj_controles : contrôles de conformité mesurés sur la géométrie POSÉE (revue conformité r2 : les critères
de la phase 1 doivent porter sur la mesure brute avec leur seuil d'origine, sans reformulation).

Chaque fonction renvoie un dict de statistiques et de cas ; fabriquer._phase1 en tire les critères :
- fidelite : fil d'eau posé − z décrit par élément (≤ 1 cm) ; écart en plan de la face posée au tracé
  levé (p95 ≤ 2 cm, max ≤ 5 cm, nez arrondis exclus) ; écart de lissage par bordure ;
- interstices_denses : sondes tous les 2 cm à 3 mm devant et derrière chaque face (trou dans le sol) ;
- rampes_marchables : profils perpendiculaires de 2 m derrière les bateaux de traversée, sur revêtement
  marchable seulement, pente sur 0,25 m glissants (p95 ≤ 5 %) ;
- faces_arriere : hauteur de face arrière à nu 5 cm derrière les bordures (≤ 3 cm) ;
- remplissages : retrait sous la tête locale à 3, 6 et 10 cm derrière la ceinture, classe de remplissage
  seulement (3 à 5 cm) ;
- vues_traversees : vue réelle (tête − sol 5 cm devant) de chaque élément de bateau de traversée.
"""
import math

import numpy as np

import pj_bordure_pose as PO
import pj_commun as K
import pj_sol as SO

C = K.C
MARCHABLES = set(SO.MARCHABLES)


def _stat(a, nd=4):
    a = np.asarray(a, dtype=float)
    if len(a) == 0:
        return None
    return {"n": int(len(a)), "min": round(float(a.min()), nd), "p5": round(float(np.percentile(a, 5)), nd),
            "mediane": round(float(np.median(a)), nd), "p95": round(float(np.percentile(a, 95)), nd),
            "max": round(float(a.max()), nd)}


def face_locale(e, specs, desc, pas=0.02):
    """Points de la face vue (u = 0) d'un élément posé dans son repère, tous les `pas` m, et normale
    gauche locale à chaque point (vers l'arrière)."""
    sx = e["s"][0]
    if PO.sur_mesure(e):
        ch = PO.chemin_courbe(desc.par_id[e["bordure"]], e, pas) * [sx, 1.0]
        return ch, K.normales_gauches(ch)
    L = e["longueur"] / max(sx, 1e-6) * sx
    xs = np.linspace(-0.5 * L * 0.995, 0.5 * L * 0.995, max(3, int(L / pas) + 1))
    return np.c_[xs, np.zeros(len(xs))], np.tile([0.0, 1.0], (len(xs), 1))


def vers_monde(e, loc_xy, z=0.0):
    R = K.rotation_rpy(e["rpy"])
    loc = np.c_[loc_xy, np.full(len(loc_xy), z) if np.isscalar(z) else z]
    return np.asarray(e["p"]) + (R @ loc.T).T


def fidelite(desc, specs, elements):
    """Fil d'eau posé − z décrit (au milieu de chaque élément) et écart en plan face posée - tracé levé."""
    dz, details_z = [], []
    plan, details_p = [], []
    for e in elements:
        B = desc.par_id[e["bordure"]]
        a = B.a_leve
        base, H = specs.dims(e["profil"])
        # fil d'eau posé au milieu de la corde : pivot + z_pied
        fe = float(e["p"][2]) + float(e["z_pied"])
        d, j, proj = C.distance_segments(np.asarray(e["p"][:2])[None], a[:-1, :2], a[1:, :2])
        j = int(j[0])
        t = float(np.clip(np.hypot(*(proj[0] - a[j, :2])) / max(np.hypot(*(a[j + 1, :2] - a[j, :2])), 1e-9), 0, 1))
        zd = a[j, 2] + t * (a[j + 1, 2] - a[j, 2])
        dz.append(fe - zd)
        if abs(fe - zd) > 0.01:
            details_z.append([e["id"], round((fe - zd) * 1000, 1)])
        # plan : face posée (pied, u = 0) aux points hors nez arrondis
        loc, _ = face_locale(e, specs, desc, 0.05)
        W = vers_monde(e, loc, 0.0)[:, :2]
        s, _, _ = C.projeter(B.P, W)
        hors = np.ones(len(W), dtype=bool)
        for s0, s1 in B.arcs_fab:
            hors &= ~((s >= s0 - 0.3) & (s <= s1 + 0.3))
        if hors.any():
            dd, _, _ = C.distance_segments(W[hors], a[:-1, :2], a[1:, :2])
            plan.append(float(dd.max()))
            if dd.max() > 0.05:
                details_p.append([e["id"], round(float(dd.max()) * 1000, 1)])
    lis = {B.id: {"hors_nez_m": round(B.ecart_lissage_m, 4), "nez_m": round(B.ecart_nez_m, 4)} for B in desc.bordures}
    plan = np.array(plan)
    return {"methode": "fil d'eau = pivot + z_pied au milieu de la corde, z décrit interpolé sur le tracé levé au droit du "
                       "pivot ; plan : pied de face posé tous les 5 cm (hors nez arrondis ± 0,3 m) à la polyligne levée",
            "fil_eau_pose_moins_decrit_m": _stat(dz), "n_ecart_z_sup_1cm": len(details_z), "ecarts_z_sup_1cm": details_z[:30],
            "ecart_plan_m": _stat(plan), "n_ecart_plan_sup_5cm": len(details_p), "ecarts_plan_sup_5cm": details_p[:30],
            "ecart_lissage_par_bordure": lis}


def interstices_denses(desc, specs, sol, elements, caniveaux, loc):
    """Sondes tous les 2 cm à 3 mm devant et derrière la face de chaque élément : aucun triangle de sol
    (trou) = interstice ; devant un caniveau, le caniveau couvre ; derrière, une bordure dos à dos couvre ;
    hors de l'emprise, non compté."""
    x0, y0, x1, y1 = desc.zone
    can = {}
    for c in caniveaux:
        can.setdefault(c["bordure"], []).append((c["s0"] - 0.01, c["s1"] + 0.01))
    trous = {"avant": [], "arriere": []}
    n = {"avant": 0, "arriere": 0}
    for e in elements:
        B = desc.par_id[e["bordure"]]
        base, H = specs.dims(e.get("profil_bas", e["profil"]) if e["type"] == "chartiere" else e["profil"])
        base = min(base, specs.dims(e["profil"])[0])
        loc_xy, nl = face_locale(e, specs, desc, 0.02)
        ur = SO.u_route(specs, e["profil"], max(e["vue"], e.get("vue_fin", e["vue"])))
        for cote, u in (("avant", min(ur, 0.0) - 0.003), ("arriere", base + 0.003)):
            W = vers_monde(e, loc_xy + nl * u, 0.0)[:, :2]
            dedans = (W[:, 0] > x0 + 0.05) & (W[:, 0] < x1 - 0.05) & (W[:, 1] > y0 + 0.05) & (W[:, 1] < y1 - 0.05)
            W = W[dedans]
            if len(W) == 0:
                continue
            tri, _ = loc.trouver(W)
            vide = tri < 0
            if cote == "avant" and e["bordure"] in can:
                s, _, _ = C.projeter(B.P, W)
                vide &= ~np.array([any(a <= x <= b for a, b in can[e["bordure"]]) for x in s], dtype=bool)
            if vide.any():                         # une autre bordure couvre (dos à dos, nez, raccord)
                iv = np.where(vide)[0]
                for bid2, m2, s2, dl2, d2, ex2 in sol.projections(W[iv], rayon=0.3):
                    if bid2 == e["bordure"] and cote == "avant":
                        continue
                    b2 = sol.bandes[bid2]
                    couvert = (ex2 <= 0.01) & (dl2 > b2.interp(b2.uf, s2) - 0.015) & (dl2 < b2.interp(b2.base, s2) + 0.015)
                    vide[iv[m2[couvert]]] = False
            n[cote] += int(len(W))
            if vide.any():
                trous[cote].append([e["id"], int(vide.sum()), round(0.02 * int(vide.sum()), 2)])
    return {"methode": "sondes tous les 2 cm à 3 mm de la face vue (avant) et du dos (arrière) ; trou = aucun triangle de "
                       "sol.usda, hors caniveau devant et hors bande d'une autre bordure",
            "sondes": n, "elements_avec_trou_avant": trous["avant"][:30], "elements_avec_trou_arriere": trous["arriere"][:30],
            "points_trou_avant": int(sum(t[1] for t in trous["avant"])),
            "points_trou_arriere": int(sum(t[1] for t in trous["arriere"]))}


def rampes_marchables(desc, specs, sol, elements, loc):
    """Profils perpendiculaires de 2 m derrière chaque élément de bateau de traversée (5 profils par élément),
    arrêtés au premier revêtement non marchable ou à la bande d'une autre bordure ; pente |Δz| / 0,25 m."""
    out = {}
    abaisses = {}
    for B in desc.bordures:
        for a in B.p.get("abaisses", []):
            if a.get("type") == "traversee":
                abaisses[(B.id, a["id"])] = (float(B.s_nouveau(a["s0"])), float(B.s_nouveau(a["s1"])))
    for (bid, aid), (s0, s1) in sorted(abaisses.items()):
        els = [e for e in elements if e["bordure"] == bid and e["type"] == "bateau" and s0 - 0.05 <= 0.5 * (e["s0"] + e["s1"]) <= s1 + 0.05]
        pentes, ressauts, longueurs = [], [], []
        for e in els:
            base, H = specs.dims(e["profil"])
            loc_xy, nl = face_locale(e, specs, desc, 0.02)
            k = np.linspace(0.1, 0.9, 5) * (len(loc_xy) - 1)
            for i in k.astype(int):
                us = np.arange(base + 0.03, base + 2.03, 0.05)
                W = vers_monde(e, loc_xy[i] + np.outer(us, nl[i]), 0.0)[:, :2]
                tri, z = loc.trouver(W)
                cls = np.where(tri >= 0, sol.cl[np.maximum(tri, 0)], "")
                n = len(W)
                for j in range(len(W)):
                    if tri[j] < 0 or cls[j] not in MARCHABLES:
                        n = j
                        break
                if n > 0:                          # à 0,3 m d'une autre bordure (son fil d'eau n'est pas le cheminement)
                    for bid2, m2, s2, dl2, d2, ex2 in sol.projections(W[:n], rayon=0.5):
                        if bid2 == bid:
                            continue
                        b2 = sol.bandes[bid2]
                        dans = (ex2 <= 0.05) & (dl2 > b2.interp(b2.uf, s2) - 0.30) & (dl2 < b2.interp(b2.base, s2) + 0.30)
                        if dans.any():
                            n = min(n, int(m2[dans].min()))
                longueurs.append(0.05 * n)
                zz = z[:n]
                if n > 5:
                    pentes += list(np.abs(zz[5:] - zz[:-5]) / 0.25)
                if n > 1:
                    ressauts.append(float(np.max(np.abs(np.diff(zz)))))
        p = np.array(pentes)
        out[aid] = {"bordure": bid, "elements": len(els), "longueur_marchable_mediane_m": round(float(np.median(longueurs)), 2) if longueurs else 0.0,
                    "pente_p50_pct": round(100 * float(np.median(p)), 2) if len(p) else None,
                    "pente_p95_pct": round(100 * float(np.percentile(p, 95)), 2) if len(p) else None,
                    "pente_max_pct": round(100 * float(p.max()), 2) if len(p) else None,
                    "part_sup_5pct": round(float(np.mean(p > 0.05)), 3) if len(p) else None,
                    "ressaut_max_m": round(max(ressauts), 4) if ressauts else None}
    return {"methode": "5 profils par élément de bateau de traversée, de base + 3 cm à base + 2,03 m, revêtements marchables "
                       "seulement (arrêt au premier non marchable ou à 0,30 m d'une autre bordure : son fil d'eau n'est pas le "
                       "cheminement), pente sur 0,25 m",
            "abaisses": out}


RETRAITS = dict(SO.DECAISSE)
RETRAITS_ILOT = {}


def faces_arriere(desc, specs, sol, elements, loc):
    """Hauteur de face arrière à nu : tête − sol 5 cm derrière le dos, 3 points par élément (> 3 cm signalé),
    hors bordures dont le côté haut est une chaussée ou un autre élément."""
    h, cas = [], []
    for il in desc.ilots:
        RETRAITS_ILOT[il["id"]] = float(il["p"]["remplissage"].get("retrait_sous_bordure_m", 0.0)) + 0.01
    for e in elements:
        if e["type"] == "caniveau":
            continue
        base, H = specs.dims(e["profil"])
        loc_xy, nl = face_locale(e, specs, desc, 0.02)
        idx = np.linspace(0.15, 0.85, 3) * (len(loc_xy) - 1)
        P = np.array([loc_xy[int(i)] + nl[int(i)] * (base + 0.05) for i in idx])
        W = vers_monde(e, P, 0.0)
        top = vers_monde(e, np.array([loc_xy[int(i)] + nl[int(i)] * (base - 0.02) for i in idx]), H)[:, 2]
        if e["type"] == "chartiere":
            B = desc.par_id[e["bordure"]]
            s, _, _ = C.projeter(B.P, W[:, :2])
            top = B.z_fe(s) + B.vue(s)
        tri, z = loc.trouver(W[:, :2])
        ok = tri >= 0
        if not ok.any():
            continue
        # une autre bordure derrière (dos à dos, pointe d'îlot : la sonde passe devant l'autre face) et bouts de
        # file (about libre) : non comptés
        io = np.where(ok)[0]
        for bid2, m2, s2, dl2, d2, ex2 in sol.projections(W[io, :2], rayon=0.5):
            b2 = sol.bandes[bid2]
            if bid2 == e["bordure"]:
                bout = (s2 < 0.3) | (s2 > b2.B.L - 0.3) | (ex2 > 0)
                # pointe d'îlot : la sonde passe devant l'autre côté de la même bordure
                pointe = dl2 < 0.0
                ok[io[m2[bout | pointe]]] = False
                continue
            dans = (ex2 <= 0.05) & (d2 < 0.5) & (dl2 < b2.interp(b2.base, s2) + 0.03)
            ok[io[m2[dans]]] = False
        d = top[ok] - z[ok]
        # massif ou remplissage décaissé derrière (BRF, gravier : 3-5 cm voulus) : face visible admise = retrait + 3 cm
        cls = sol.cl[tri[ok]]
        ilo = sol.ilot_tri[tri[ok]]
        admis = 0.03 + np.array([RETRAITS.get(c, 0.0) if not i else RETRAITS_ILOT.get(i, 0.0) for c, i in zip(cls, ilo)])
        h += list(d)
        if len(d) and (d - admis).max() > 0:
            k = int(np.argmax(d - admis))
            cas.append([e["id"], round(float(d[k]) * 1000, 1), str(cls[k])])
    return {"methode": "tête − sol 5 cm derrière le dos, 3 points par élément (dos à dos exclus) ; admis : 3 cm, + le retrait "
                       "voulu d'un massif ou d'un remplissage (BRF 4 cm, gravier 3-4 cm, + 1 cm de bombement)",
            "face_arriere_a_nu_m": _stat(h), "n_sup_3cm": len(cas), "cas_sup_3cm": sorted(cas, key=lambda c: -c[1])[:30]}


def remplissages(desc, specs, sol, elements, loc):
    """Retrait du remplissage sous la tête LOCALE de la ceinture, sondé à 3, 6 et 10 cm du dos des
    éléments de ceinture, sur la seule classe de remplissage de l'îlot."""
    out = {}
    for il in desc.ilots:
        rem = il["p"]["remplissage"]
        if float(rem.get("retrait_sous_bordure_m", 0.0)) <= 0:
            continue
        mid = rem["materiau_id"]
        rr, hors = [], []
        for e in elements:
            if e["bordure"] not in il["p"].get("ceinture", []):
                continue
            base, H = specs.dims(e["profil"])
            loc_xy, nl = face_locale(e, specs, desc, 0.05)
            for k in range(0, len(loc_xy), 2):
                for off in (0.03, 0.06, 0.10):
                    W = vers_monde(e, (loc_xy[k] + nl[k] * (base + off))[None], 0.0)
                    tri, z = loc.trouver(W[:, :2])
                    if tri[0] < 0 or sol.cl[tri[0]] != mid or sol.ilot_tri[tri[0]] != il["id"]:
                        continue
                    top = float(vers_monde(e, (loc_xy[k] + nl[k] * (base - 0.03))[None], H)[0, 2])
                    if e["type"] == "chartiere":       # tête variable le long d'une chartière
                        B = desc.par_id[e["bordure"]]
                        sp, _, _ = C.projeter(B.P, W[:, :2])
                        top = float(B.z_fe(sp[0]) + B.vue(sp[0])[0])
                    r = top - float(z[0])
                    rr.append(r)
                    if not (0.03 - 0.002 <= r <= 0.05 + 0.002):
                        hors.append([e["id"], off, round(r * 100, 1)])
        out[il["id"]] = {"materiau_id": mid, "retrait_decrit_m": rem.get("retrait_sous_bordure_m"), "retrait_m": _stat(rr),
                         "n_sondes": len(rr), "n_hors_3_5cm": len(hors), "hors_3_5cm": hors[:15]}
    return out


def vues_traversees(desc, specs, elements, loc):
    """Vue réelle (tête de l'élément − sol 5 cm devant la face) des éléments de bateau de traversée."""
    out = []
    trav = set()
    for B in desc.bordures:
        for a in B.p.get("abaisses", []):
            if a.get("type") == "traversee":
                trav.add((B.id, round(float(B.s_nouveau(a["s0"])), 2), round(float(B.s_nouveau(a["s1"])), 2)))
    for e in elements:
        if e["type"] != "bateau":
            continue
        sm = 0.5 * (e["s0"] + e["s1"])
        if not any(b == e["bordure"] and s0 - 0.05 <= sm <= s1 + 0.05 for b, s0, s1 in trav):
            continue
        base, H = specs.dims(e["profil"])
        loc_xy, nl = face_locale(e, specs, desc, 0.05)
        i = len(loc_xy) // 2
        tete = float(vers_monde(e, (loc_xy[i] + nl[i] * 0.06)[None], H)[0, 2])
        W = vers_monde(e, (loc_xy[i] - nl[i] * 0.05)[None], 0.0)
        tri, z = loc.trouver(W[:, :2])
        if tri[0] >= 0:
            out.append([e["id"], round(float(e["vue"]), 3), round(tete - float(z[0]), 4)])
    v = np.array([o[2] for o in out]) if out else np.zeros(0)
    hors = [o for o in out if not (0.015 <= o[2] <= 0.025)]
    return {"methode": "tête de l'élément (6 cm derrière la face) − sol 5 cm devant, au milieu de chaque élément de bateau de traversée",
            "vue_reelle_m": _stat(v), "hors_0_02_pm_0_005": hors, "ecart_a_la_vue_decrite_m": _stat([o[2] - o[1] for o in out])}
