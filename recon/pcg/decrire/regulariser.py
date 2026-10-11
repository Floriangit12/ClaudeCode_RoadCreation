"""Régularisation géométrique professionnelle de la description v2 (schéma 0.3, site complet) : les
bordures, contours d'îlots, limites de surfaces et axes de marquage deviennent un dessin de VRD (droites et
arcs tangents, coins voulus seulement, topologie exacte), dans la tolérance de leur source.

Règles : assets/specs/regles_qualite_geometrique.json (GQ-*), citées dans le code, les entités et le rapport.

Crochets (une ligne chacun, fichiers partagés) :
- sol_composer.familles_sol, après bordures.construire : `regulariser.bordures(K, bev_cand, mnt)`
  1. orientation (GQ-ORI-001 voies driving/bus du côté bas ; GQ-ORI-002 classes raster si MNT non décisif) ;
  2. nœuds et contacts (GQ-TOP-001 nœud exact et cap commun si les bordures se prolongent, GQ-TOP-002 contact
     en T posé sur la courbe régularisée, GQ-TOP-003 anneaux refermés) ;
  3. ajustement droites / arcs G1 (regulariser_geometrie : GQ-PRI-001, GQ-CON-001/002, GQ-TOL-001/003,
     GQ-SEG-001/002, GQ-RAY-001/003, GQ-SYM-003 quais en alignement droit) ;
  4. géométrie dépendante (GQ-TOP-005) : intervalles, abaissés, chartières, caniveau, Z remappés par
     projection ; courbes de pose recalculées sur les arcs (GQ-RAY-001) ; candidats BEV mis à jour.
- surfaces.construire_partition : `regulariser.lignes_partition(lignes)` (limites GAM, OSM, fermetures
  d'origine raster ; GQ-LAR-001 : limite parallèle à une bordure rendue à largeur constante) ; la partition
  (et donc les surfaces, les îlots et le nivellement) est construite sur les limites régularisées (GQ-TOP-004).
- composer.py, après marquages.construire : `regulariser.marquages(feats_m)` (axes des lignes, GQ-PRI-002).
- composer.py : `regulariser.ecrire_sources(dossier)` archive les géométries sources (GQ-PRO-001) et le
  rapport (statistiques.regularisation du manifeste).
Déterministe : entités traitées par identifiant trié, aucun aléa, arrondis fixes.
"""
import collections
import functools
import math
import re

import numpy as np

import regulariser_geometrie as RG
import sol_site as ctx
from commun import (SPECS, abscisses, arrondi, coords_geojson, distance_segments, ecrire_geojson, lire_json,
                    normale_gauche, point_a, projeter, repere)

FICHIER_REGLES = SPECS / "regles_qualite_geometrique.json"
LMIN = {"bordure": 0.5, "limite": 0.3, "marquage": 0.5}          # GQ-SEG-001
RMIN = {"bordure": 0.25, "limite": 0.2, "marquage": 0.2}         # GQ-RAY-001
PAS_MAX = {"bordure": 0.5, "limite": 1.0, "marquage": None}      # GQ-DEN-001
SRC_LIMITES = {"limite_revetement": "gam", "vegetation": "gam", "talus_haut": "gam", "talus_bas": "gam",
               "osm_parking": "osm", "fermeture": "fermeture_raster"}

_ETAT = {"sources": [], "rapport": {}}                          # archive des sources et rapport (une exécution)


@functools.lru_cache(maxsize=None)
def regles():
    return {r["id"]: r for r in lire_json(FICHIER_REGLES)["regles"]}


def param(rid, cle):
    return regles()[rid]["parametres"][cle]


def tolerance(src):
    """GQ-TOL-001 : tolérance T (m) de la source."""
    T = param("GQ-TOL-001", "T_m")
    s = (src or "").split(":")[0]
    if s in T:
        return float(T[s])
    if src and src.startswith("a_priori"):
        return float(T["a_priori"])
    if src and src.startswith("regle"):
        return float(T["regle"])
    if src and src.startswith("osm"):
        return float(T["osm"])
    return float(T["v1"])


def reinitialiser():
    _ETAT["sources"] = []
    _ETAT["rapport"] = {}
    _ETAT["regularisees"] = set()
    _ETAT["limites_apres"] = []
    _ETAT.pop("protegees", None)
    _ETAT.pop("bordures_reg", None)


def vers_l93(P):
    return repere(np.asarray(P, dtype=np.float64), "l93")


# --------------------------------------------------------------------------- orientation (GQ-ORI-001/002)
@functools.lru_cache(maxsize=None)
def _carte_circulee():
    """Carte d'indices : 1 sous une voie driving / bus de lanes_2026 (GQ-ORI-001), 0 ailleurs."""
    types = set(param("GQ-ORI-001", "types_voie"))
    return ctx.rasteriser([(1 if t in types else 0, polys) for r, v, t, s, j, polys in ctx.voies_xodr()], defaut=0)


def _portees(Q, N, A, B, dmax):
    """Distance le long de chaque rayon Q + t·N (t ∈ ]0,02 ; dmax]) au premier segment [A, B] (dmax sinon)."""
    out = np.full(len(Q), dmax)
    if len(A) == 0:
        return out
    S = B - A
    for k0 in range(0, len(Q), 512):
        q, n = Q[k0:k0 + 512], N[k0:k0 + 512]
        den = n[:, None, 0] * S[None, :, 1] - n[:, None, 1] * S[None, :, 0]
        ap = A[None] - q[:, None]
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (ap[..., 0] * S[None, :, 1] - ap[..., 1] * S[None, :, 0]) / den
            w = (ap[..., 0] * n[:, None, 1] - ap[..., 1] * n[:, None, 0]) / den
        ok = (np.abs(den) > 1e-12) & (t > 0.02) & (t <= dmax) & (w >= 0) & (w <= 1)
        t = np.where(ok, t, dmax)
        out[k0:k0 + 512] = t.min(axis=1)
    return out


def diagnostic_cotes(P, autres_A, autres_B):
    """Parts de voie circulée (GQ-ORI-001) et de classes raster (GQ-ORI-002) du côté haut (gauche) et du
    côté bas (droite) d'une polyligne locale ; rayons arrêtés à la première autre bordure."""
    S = abscisses(P)
    L = float(S[-1])
    s = np.linspace(0.0, L, max(3, int(L / 0.5) + 1))
    q, tg = point_a(P, s)
    n = normale_gauche(tg)
    dec = param("GQ-ORI-001", "decalages_m")
    carte = _carte_circulee()
    # segments des autres bordures à portée
    bb = (P[:, 0].min() - 2, P[:, 1].min() - 2, P[:, 0].max() + 2, P[:, 1].max() + 2)
    m = ((np.maximum(autres_A[:, 0], autres_B[:, 0]) >= bb[0]) & (np.minimum(autres_A[:, 0], autres_B[:, 0]) <= bb[2])
         & (np.maximum(autres_A[:, 1], autres_B[:, 1]) >= bb[1]) & (np.minimum(autres_A[:, 1], autres_B[:, 1]) <= bb[3]))
    A, B = autres_A[m], autres_B[m]
    res = {}
    basses = set(param("GQ-ORI-002", "classes_basses"))
    hautes = set(param("GQ-ORI-002", "classes_hautes"))
    for cote, sg in (("haut", 1.0), ("bas", -1.0)):
        portee = _portees(q, sg * n, A, B, max(dec) + 0.1)
        circ, tot = 0, 0
        for o in dec:
            pts = q + sg * n * o
            vu = o < portee - 0.02
            circ += int(np.sum((ctx.echantillonner(carte, pts, 0) == 1) & vu))
            tot += len(pts)
        pts = q + sg * n * 0.6
        vu = 0.6 < portee - 0.02
        cl = ctx.classe_surface(pts)
        nv = max(int(vu.sum()), 1)
        res[cote] = {"circulee": circ / max(tot, 1),
                     "classe_basse": float(np.sum(np.isin(cl, list(basses)) & vu)) / nv,
                     "classe_haute": float(np.sum(np.isin(cl, list(hautes)) & vu)) / nv,
                     "n_vus": int(vu.sum())}
    return res


def _critere(p):
    ref = p["prov"].get("face_vue", {}).get("ref", "")
    return ref.split(" ")[0] if ref else "inconnu"


def orienter(K):
    """GQ-ORI-001 / GQ-ORI-002 : retourne les bordures dont le côté haut porte une voie circulée (ou, sans
    voie et MNT non décisif, la classe chaussée face à une classe piétonne / verte). Renvoie le journal."""
    P = {f["properties"]["id"]: repere(np.asarray(f["geometry"]["coordinates"])[:, :2]) for f in K}
    ids = sorted(P)
    A = np.vstack([P[k][:-1] for k in ids])
    B = np.vstack([P[k][1:] for k in ids])
    own = np.concatenate([np.full(len(P[k]) - 1, i) for i, k in enumerate(ids)])
    pmin, marge = param("GQ-ORI-001", "part_min_ratio"), param("GQ-ORI-001", "marge_ratio")
    cmin = param("GQ-ORI-002", "part_classe_min_ratio")
    faibles = {"cote_haut_relief", "surfaces_v1", "defaut"}
    journal = []
    par_id = {f["properties"]["id"]: f for f in K}
    for i, kid in enumerate(ids):
        f = par_id[kid]
        p = f["properties"]
        sel = own != i
        d = diagnostic_cotes(P[kid], A[sel], B[sel])
        h, b = d["haut"], d["bas"]
        crit = _critere(p)
        decision, regle = "garde", None
        if h["circulee"] >= pmin and h["circulee"] >= b["circulee"] + marge:
            decision, regle = "retournee", "GQ-ORI-001"
        elif h["circulee"] < 0.1 and b["circulee"] < 0.1 and crit in faibles:
            if h["classe_basse"] >= cmin and b["classe_haute"] >= cmin:
                decision, regle = "retournee", "GQ-ORI-002"
        e = {"bordure": kid, "longueur_m": round(float(abscisses(P[kid])[-1]), 2), "critere_origine": crit,
             "circulee_haut": round(h["circulee"], 2), "circulee_bas": round(b["circulee"], 2),
             "classe_chaussee_haut": round(h["classe_basse"], 2), "classe_pietonne_bas": round(b["classe_haute"], 2),
             "classe_chaussee_bas": round(b["classe_basse"], 2), "classe_pietonne_haut": round(h["classe_haute"], 2),
             "decision": decision, "regle": regle}
        # conflits journalisés (CF-GQ-03) : critère d'origine fort contredit, ou classe raster contraire
        if decision == "retournee" and crit in ("mnt_2026", "xodr_2026"):
            e["conflit"] = f"CF-GQ-03 : retournée contre le critère d'origine {crit} ({p['prov']['face_vue']['ref']})"
        if decision == "garde" and h["classe_basse"] >= cmin and b["classe_haute"] >= cmin:
            e["conflit"] = "classe raster contraire (chaussée côté haut, piétonne côté bas) : gardée (voie ou MNT décisif)"
        if decision == "retournee":
            retourner(f, e)
        journal.append(e)
    return journal


def _inv_intervalle(it, L):
    out = dict(it)
    out["s0"], out["s1"] = L - it["s1"], L - it["s0"]
    if "vue_m_fin" in it:
        out["vue_m"], out["vue_m_fin"] = it["vue_m_fin"], it["vue_m"]
    return out


def retourner(f, e):
    """Inverse le sens d'une bordure (côté haut à gauche) : géométrie, intervalles, abaissés, chartières,
    caniveau, bouts, source, provenance de face_vue (GQ-ORI-001 / GQ-ORI-002)."""
    p = f["properties"]
    C = np.asarray(f["geometry"]["coordinates"], dtype=np.float64)[::-1]
    f["geometry"]["coordinates"] = coords_geojson(C)
    L = float(abscisses(C[:, :2])[-1])
    p["intervalles"] = [_inv_intervalle(it, L) for it in reversed(p["intervalles"])]
    abs_ = []
    for a in reversed(p["abaisses"]):
        a = dict(a)
        a["s0"], a["s1"] = L - a["s1"], L - a["s0"]
        rs = []
        for r in reversed(a.get("raccords", [])):
            r2 = _inv_intervalle(r, L)
            r2["cote"] = {"debut": "fin", "fin": "debut"}.get(r.get("cote"), r.get("cote"))
            rs.append(r2)
        a["raccords"] = rs
        abs_.append(a)
    p["abaisses"] = abs_
    p["courbes"] = [dict(c, s0=L - c["s1"], s1=L - c["s0"]) for c in reversed(p.get("courbes", []))]
    p["chartieres_gam"] = [dict(c, s=L - c["s"]) for c in reversed(p.get("chartieres_gam", []))]
    if p.get("caniveau") and p["caniveau"].get("intervalles"):
        p["caniveau"]["intervalles"] = [[L - b, L - a] for a, b in reversed(p["caniveau"]["intervalles"])]
    cz = p.get("coupe_zone", {})
    p["coupe_zone"] = {"debut": cz.get("fin", False), "fin": cz.get("debut", False)}
    src = p.get("source", {})
    if src.get("sens") in ("direct", "inverse"):
        src["sens"] = "inverse" if src["sens"] == "direct" else "direct"
    if isinstance(src.get("s_src_m"), list) and len(src["s_src_m"]) == 2:
        src["s_src_m"] = src["s_src_m"][::-1]
    if e["regle"] == "GQ-ORI-001":
        ref = (f"voie driving/bus (lanes_2026) du côté haut : part {e['circulee_haut']:.2f} contre {e['circulee_bas']:.2f} "
               f"côté bas ; bordure retournée (critère d'origine {e['critere_origine']})")
    else:
        ref = (f"sans voie adjacente, MNT non décisif : classe chaussée côté haut {e['classe_chaussee_haut']:.2f}, "
               f"classe piétonne côté bas {e['classe_pietonne_bas']:.2f} ; bordure retournée (critère d'origine {e['critere_origine']})")
    p["prov"]["face_vue"] = {"src": f"regle:regles_qualite_geometrique.{e['regle']}", "ref": ref,
                             "conf": "haute" if e["regle"] == "GQ-ORI-001" else "moyenne"}
    if p["abaisses"]:
        e["note"] = "abaissés retournés : configuration et largeur de trottoir à revoir (calculées côté opposé)"


# --------------------------------------------------------------------------- nœuds (GQ-TOP-001/002/003)
def _tangente_bout(P, bout, long=1.5):
    """Direction de parcours au bout (0 début, -1 fin), droite ajustée sur ≤ long m."""
    S = abscisses(P)
    if bout == 0:
        Q = P[S <= min(long, S[-1])]
    else:
        Q = P[S >= max(S[-1] - long, 0.0)]
    if len(Q) < 2:
        Q = P[:2] if bout == 0 else P[-2:]
    _, d, _ = RG.droite_tls(Q)
    if d @ (Q[-1] - Q[0]) < 0:
        d = -d
    return math.atan2(d[1], d[0])


def _tangente_commune(Pa, Pb, c, sens, T, rayon=1.5):
    """Cap (rad) au nœud c de la courbe ajustée sur les points des deux bordures à moins de `rayon` m :
    cercle s'il tient dans T, sinon droite ; orienté comme `sens`."""
    Q = []
    for P in (Pa, Pb):
        D, _ = RG.reechantillonner(RG.nettoyer(P), 0.1)
        Q.append(D[np.hypot(*(D - c).T) <= rayon])
    Q = np.vstack(Q)
    if len(Q) < 3:
        return sens
    t = None
    ci = RG.cercle(Q)
    if ci is not None and ci[2] <= T and ci[1] < 1e4:
        v = c - ci[0]
        t = np.array([-v[1], v[0]])
    if t is None:
        _, t, _ = RG.droite_tls(Q)
    h = math.atan2(t[1], t[0])
    return h if abs(float(RG.wrap(h - sens))) <= math.pi / 2 else h + math.pi


def noeuds(P, tol, anneaux):
    """Nœuds de bouts (GQ-TOP-001) et contacts en T (GQ-TOP-002) entre bordures ouvertes.
    P : {id: polyligne locale} ; tol : {id: T} ; anneaux : ids refermés. Renvoie (contraintes, journal)."""
    ids = [k for k in sorted(P) if k not in anneaux]
    bouts = [(k, b) for k in ids for b in (0, -1)]
    X = np.array([P[k][b] for k, b in bouts])
    acc_r, acc_max = param("GQ-TOP-001", "accrochage_ratio_T"), param("GQ-TOP-001", "accrochage_max_m")
    parent = list(range(len(bouts)))

    def racine(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(bouts)):
        d = np.hypot(*(X - X[i]).T)
        for j in np.nonzero(d <= acc_max)[0]:
            if j <= i or bouts[j][0] == bouts[i][0]:
                continue
            seuil = min(acc_max, acc_r * max(tol[bouts[i][0]], tol[bouts[j][0]]))
            if d[j] <= seuil:
                a, b = racine(i), racine(j)
                if a != b:
                    parent[max(a, b)] = min(a, b)
    groupes = collections.defaultdict(list)
    for i in range(len(bouts)):
        groupes[racine(i)].append(i)
    cons = collections.defaultdict(dict)            # cons[id] = {"debut": {...}, "fin": {...}}
    journal = {"noeuds": 0, "noeuds_g1": 0, "bouts_accroches": 0, "deplacement_max_m": 0.0, "contacts_t": 0,
               "sens_opposes": []}
    prol = math.radians(param("GQ-TOP-001", "prolongement_max_deg"))
    for g in sorted(groupes.values(), key=lambda g: min(g)):
        if len(g) < 2:
            continue
        pts = X[g]
        c = pts.mean(axis=0)
        if np.hypot(*(pts - pts[0]).T).max() < 1e-3:
            c = pts[0].copy()
        journal["noeuds"] += 1
        journal["bouts_accroches"] += len(g)
        journal["deplacement_max_m"] = max(journal["deplacement_max_m"], float(np.hypot(*(pts - c).T).max()))
        cap = None
        if len(g) == 2:
            (ka, ba), (kb, bb) = bouts[g[0]], bouts[g[1]]
            ha, hb = _tangente_bout(P[ka], ba), _tangente_bout(P[kb], bb)
            # direction « sortant du nœud » de chaque bordure
            sa = ha if ba == 0 else ha + math.pi
            sb = hb if bb == 0 else hb + math.pi
            if abs(float(RG.wrap(sa - (sb + math.pi)))) <= prol:
                # prolongement : cap commun = tangente au nœud du cercle (ou de la droite) ajusté sur les deux
                # bordures à moins de 1,5 m du nœud, orientée selon « sa » (sortant du nœud le long de ka)
                moy = _tangente_commune(P[ka], P[kb], c, sa, max(tol[ka], tol[kb]))
                cap = {(ka, ba): moy if ba == 0 else moy + math.pi, (kb, bb): moy + math.pi if bb == 0 else moy}
                journal["noeuds_g1"] += 1
                if ba == bb:                                   # GQ-ORI-003 : début contre début ou fin contre fin
                    journal["sens_opposes"].append(sorted([ka, kb]))
        for i in g:
            k, b = bouts[i]
            e = {"point": c, "type": "noeud", "avec": sorted({bouts[j][0] for j in g if j != i})}
            if cap is not None:
                e["cap"] = float(RG.wrap(cap[(k, b)]))
                e["g1"] = True
            cons[k]["debut" if b == 0 else "fin"] = e
    # contacts en T : bout libre près de l'intérieur d'une autre bordure (posé après coup sur la courbe régularisée)
    libres = [(k, b) for k, b in bouts if ("debut" if b == 0 else "fin") not in cons[k]]
    tous = sorted(P)
    A = np.vstack([P[k][:-1] for k in tous])
    B = np.vstack([P[k][1:] for k in tous])
    own = np.concatenate([np.full(len(P[k]) - 1, i) for i, k in enumerate(tous)])
    for k, b in libres:
        q = P[k][b]
        sel = own != tous.index(k)
        d, j, pr = distance_segments(q[None], A[sel], B[sel])
        if not np.isfinite(d[0]):
            continue
        o = tous[own[sel][j[0]]]
        seuil = min(acc_max, acc_r * max(tol[k], tol[o]))
        if d[0] <= seuil:
            cons[k]["debut" if b == 0 else "fin"] = {"point": pr[0], "type": "t", "avec": [o]}
            journal["contacts_t"] += 1
    journal["deplacement_max_m"] = round(journal["deplacement_max_m"], 4)
    return cons, journal


# --------------------------------------------------------------------------- ajustement d'une polyligne
def ajuster(P, tol, famille, debut=None, fin=None, cap_debut=None, cap_fin=None, ferme=False, droite_seule=False):
    """Ajustement GQ d'une polyligne locale ; renvoie le résultat de regulariser_geometrie.ajuster_polyligne."""
    if droite_seule:
        a = np.asarray(debut if debut is not None else P[0], float)
        b = np.asarray(fin if fin is not None else P[-1], float)
        h = math.atan2(b[1] - a[1], b[0] - a[0])
        ch = RG.Chaine(a[0], a[1], h, [[float(np.hypot(*(b - a))), 0.0, 0.0]])
        Pn = RG.nettoyer(P)
        D, _ = RG.reechantillonner(Pn, 0.05)
        d1, d2 = RG.ecarts(ch, D, Pn)
        poly, u = RG.densifier([ch], pas_max=PAS_MAX[famille])
        return {"chaines": [ch], "coins": [], "polyligne": poly, "u": u, "d1": d1, "d2": d2,
                "ok": RG.accepte(d1, d2, tol), "ecart_max": float(max(d1.max(), d2.max())),
                "ecart_p99": float(np.percentile(np.r_[d1, d2], 99)), "source": Pn, "ferme": False,
                "statut": "regularise", "coins_ajoutes": 0, "tours": 0}
    r = RG.ajuster_polyligne(P, tol, debut=debut, fin=fin, cap_debut=cap_debut, cap_fin=cap_fin, ferme=ferme,
                             lmin=LMIN[famille], rmin=RMIN[famille])
    if r is None:
        return None
    if PAS_MAX[famille] != 0.5 and r["statut"] != "source_gardee":
        poly, u = RG.densifier(r["chaines"], pas_max=PAS_MAX[famille])
        if ferme:
            poly[-1] = poly[0]
        r["polyligne"], r["u"] = poly, u
    return r


def _chaines_tournees(chaines, u_star):
    """Anneau : chaînes réordonnées pour commencer à l'abscisse u_star (sans coin ajouté)."""
    base = 0.0
    for i, ch in enumerate(chaines):
        if base - 1e-9 <= u_star <= base + ch.L + 1e-9:
            t = u_star - base
            if t <= 1e-6:
                return chaines[i:] + chaines[:i], [True] * len(chaines)
            if ch.L - t <= 1e-6:
                return chaines[i + 1:] + chaines[:i + 1], [True] * len(chaines)
            a, b = _couper(ch, t)
            out = [b] + chaines[i + 1:] + chaines[:i] + [a]
            coins = [False] + [True] * (len(chaines) - 1) + [True]
            return out, coins
        base += ch.L
    return chaines, [True] * len(chaines)


def _couper(ch, t):
    """Coupe une chaîne à l'abscisse t : (avant, après)."""
    av, ap = [], []
    for j, (L, k0, k1) in enumerate(ch.pieces):
        a, b = ch.bornes[j], ch.bornes[j + 1]
        if b <= t + 1e-12:
            av.append([L, k0, k1])
        elif a >= t - 1e-12:
            ap.append([L, k0, k1])
        else:
            km = k0 + (k1 - k0) * (t - a) / max(L, 1e-12)
            av.append([t - a, k0, km])
            ap.append([b - t, km, k1])
    C, h, _ = ch.evaluer(np.array([t]))
    return RG.Chaine(ch.x0, ch.y0, ch.h0, av), RG.Chaine(C[0, 0], C[0, 1], h[0], ap)


def description(r, famille, src, tol, extra=None, coins_chaines=None):
    """Champ geometrie_reguliere (GQ-PRI-003) d'un résultat d'ajustement."""
    prims = RG.description_primitives(r["chaines"], vers_l93)
    if coins_chaines is not None:
        for e in prims:
            e.pop("coin", None)
        base = 0
        for ci, ch in enumerate(r["chaines"]):
            if ci > 0 and coins_chaines[ci]:
                prims[base]["coin"] = True
            base += len(ch.pieces)
    n = collections.Counter(e["type"] for e in prims)
    d = np.r_[r["d1"], r["d2"]]
    out = {"statut": r["statut"], "famille": famille, "source": src, "tolerance_m": round(tol, 3),
           "ecart_max_m": round(float(d.max()), 4), "ecart_p99_m": round(float(np.percentile(d, 99)), 4),
           "ecart_moyen_m": round(float(r["d1"].mean()), 4),
           "n_primitives": {k: int(v) for k, v in sorted(n.items())},
           "coins": [round(e["s0"], 3) for e in prims if e.get("coin")],
           "ferme": bool(r.get("ferme")), "primitives": prims,
           "regles": ["GQ-PRI-001" if famille != "marquage" else "GQ-PRI-002", "GQ-CON-001", "GQ-CON-002",
                      "GQ-TOL-001", "GQ-TOL-003", "GQ-SEG-001", "GQ-SEG-002", "GQ-RAY-003", "GQ-DEN-001"]}
    if extra:
        out.update(extra)
    return out


# --------------------------------------------------------------------------- remappage (GQ-TOP-005)
def remapper_s(P_old, P_new, s_old, ferme=False):
    """Abscisses sur P_new des points d'abscisse s_old sur P_old (projection ; ordre conservé)."""
    s_old = np.asarray(s_old, dtype=np.float64)
    if len(s_old) == 0:
        return s_old
    L_old = float(abscisses(P_old)[-1])
    L_new = float(abscisses(P_new)[-1])
    q, _ = point_a(P_old, np.clip(s_old, 0, L_old))
    s_new, _, _ = projeter(P_new, q)
    if ferme:                                          # couture de l'anneau
        s_new = np.where((s_old > 0.75 * L_old) & (s_new < 0.25 * L_new), s_new + L_new, s_new)
        s_new = np.where((s_old < 0.25 * L_old) & (s_new > 0.75 * L_new), s_new - L_new, s_new)
    s_new = np.where(s_old <= 1e-9, 0.0, s_new)
    s_new = np.where(s_old >= L_old - 1e-9, L_new, s_new)
    o = np.argsort(s_old, kind="stable")
    s_new[o] = np.maximum.accumulate(s_new[o])         # monotonie (projections de points très voisins)
    return np.clip(s_new, 0.0, L_new)


def _courbes(r, L):
    """Courbes de pose relues sur les arcs (GQ-RAY-001, regle_pas_rayon) : piece_courbe si R < 3 m,
    element_0_50 si 3 ≤ R < 12 m ; mêmes champs que bordures.py."""
    out = []
    base = 0.0
    for ch in r["chaines"]:
        for j, (Lp, k0, k1) in enumerate(ch.pieces):
            k = max(abs(k0), abs(k1))
            if k > 1.0 / 12.0:
                R = 1.0 / k
                pose = "piece_courbe" if R < 3.0 else "element_0_50"
                out.append({"s0": base + ch.bornes[j], "s1": base + ch.bornes[j + 1], "r_min_m": R, "pose": pose})
        base += ch.L
    fus = []
    for c in out:
        if fus and c["pose"] == fus[-1]["pose"] and c["s0"] - fus[-1]["s1"] <= 0.5:
            fus[-1]["s1"] = c["s1"]
            fus[-1]["r_min_m"] = min(fus[-1]["r_min_m"], c["r_min_m"])
        else:
            fus.append(dict(c))
    for c in fus:
        c["s0"], c["s1"] = max(0.0, c["s0"]), min(L, c["s1"])
    return fus


def appliquer_bordure(f, r, P_old, C_old, ferme, desc):
    """Écrit la géométrie régularisée d'une bordure et remappe tout ce qui dépend de s (GQ-TOP-005)."""
    p = f["properties"]
    Pn = r["polyligne"]
    S_old = abscisses(P_old)
    s_proj, _, _ = projeter(P_old, Pn)
    z = np.interp(s_proj, S_old, C_old[:, 2])
    f["geometry"]["coordinates"] = coords_geojson(np.c_[vers_l93(Pn), z])
    P_new = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
    L_new = float(abscisses(P_new)[-1])
    L_old = float(S_old[-1])
    # abaissés et chartières : longueurs normatives conservées (GA-ABA-001 ≥ 1,20 m, chartières de 1 m),
    # groupe translaté de la projection de son centre ; bornes d'intervalles confondues avec elles reprises
    corresp = {}
    fin_prec_old, fin_prec_new = None, None
    for a in sorted(p["abaisses"], key=lambda x: x["s0"]):
        grp = [a] + list(a.get("raccords", []))
        lo = min(g["s0"] for g in grp)
        hi = max(g["s1"] for g in grp)
        if lo < 1e-6 and hi > L_old - 1e-6:             # groupe sur toute la bordure : homothétie
            fct = L_new / max(L_old, 1e-9)
            nouv = {id(g): (g["s0"] * fct, g["s1"] * fct) for g in grp}
        else:
            c_old = (a["s0"] + a["s1"]) / 2.0
            dec = float(remapper_s(P_old, P_new, [c_old], ferme)[0]) - c_old
            if lo < 1e-6:
                dec = 0.0                               # groupe ancré au début de la bordure
            elif hi > L_old - 1e-6:
                dec = L_new - L_old                     # groupe ancré à la fin
            if fin_prec_old is not None:                # ordre et écart au groupe précédent conservés (GA-ABA-007)
                dec = max(dec, fin_prec_new + max(lo - fin_prec_old, 0.0) - lo)
            dec = min(max(dec, -lo), L_new - hi)        # le groupe reste dans [0, L_new]
            nouv = {id(g): (g["s0"] + dec, g["s1"] + dec) for g in grp}
        for g in grp:
            n0, n1 = nouv[id(g)]
            corresp[round(g["s0"], 6)] = n0
            corresp[round(g["s1"], 6)] = n1
            g["s0"], g["s1"] = float(max(0.0, n0)), float(min(L_new, n1))
        fin_prec_old, fin_prec_new = hi, max(g["s1"] for g in grp)
    # intervalles : partition exacte de [0, L_new]
    its = p["intervalles"]
    bornes = [it["s0"] for it in its] + [its[-1]["s1"]]
    nb = remapper_s(P_old, P_new, bornes, ferme)
    for i, b0 in enumerate(bornes):
        proche = [v for k_, v in corresp.items() if abs(k_ - b0) < 1e-3]
        if proche:
            nb[i] = proche[0]
    nb[0], nb[-1] = 0.0, L_new
    nb = np.maximum.accumulate(np.clip(nb, 0.0, L_new))
    for it, a, b in zip(its, nb[:-1], nb[1:]):
        it["s0"], it["s1"] = float(a), float(b)
    for c in p.get("chartieres_gam", []):
        c["s"] = float(remapper_s(P_old, P_new, [c["s"]], ferme)[0])
    if p.get("caniveau") and p["caniveau"].get("intervalles"):
        p["caniveau"]["intervalles"] = [[float(x) for x in remapper_s(P_old, P_new, iv, ferme)]
                                        for iv in p["caniveau"]["intervalles"]]
    p["courbes"] = _courbes(r, L_new)
    p["longueur_m"] = L_new
    p["geometrie_reguliere"] = desc
    d = desc
    p["prov"]["regularisation"] = {
        "src": "regle:regles_qualite_geometrique.GQ-TOL-001",
        "ref": (f"droites et arcs tangents (GQ-PRI-001, GQ-CON-001) : {d['n_primitives']} ; écart max {d['ecart_max_m']:.3f} m, "
                f"p99 {d['ecart_p99_m']:.3f} m à la source {d['source']} (T {d['tolerance_m']:.2f} m) ; longueur {L_old:.3f} -> {L_new:.3f} m"),
        "conf": "haute" if d["statut"] == "regularise" else "faible"}
    return P_new


def bordures(K, bev_cand, mnt=None):
    """Crochet de sol_composer.familles_sol : orientation, nœuds, ajustement et dépendances des bordures."""
    reinitialiser()
    rap = {"orientation": orienter(K)}
    par_id = {f["properties"]["id"]: f for f in K}
    ids = sorted(par_id)
    P = {k: repere(np.asarray(par_id[k]["geometry"]["coordinates"])[:, :2]) for k in ids}
    C3 = {k: np.c_[P[k], np.asarray(par_id[k]["geometry"]["coordinates"])[:, 2]] for k in ids}
    src = {k: par_id[k]["properties"]["prov"]["geometrie"]["src"] for k in ids}
    tol = {k: tolerance(src[k]) for k in ids}
    r_ferm = param("GQ-TOP-003", "fermeture_max_ratio_T")
    anneaux = {k for k in ids if float(abscisses(P[k])[-1]) > param("GQ-TOP-003", "longueur_min_anneau_m")
               and float(np.hypot(*(P[k][0] - P[k][-1]))) <= r_ferm * tol[k]}
    cons, jn = noeuds(P, tol, anneaux)
    rap["noeuds"] = jn
    for k in ids:                                    # archive des sources (GQ-PRO-001)
        _ETAT["sources"].append(("bordures", k, src[k], tol[k], C3[k][:, :2]))
    resultats = {}

    def un(k, fin_t=None, debut_t=None):
        c = cons.get(k, {})
        de = c.get("debut", {})
        fi = c.get("fin", {})
        dpt = debut_t if debut_t is not None else (de.get("point") if de.get("type") == "noeud" else None)
        fpt = fin_t if fin_t is not None else (fi.get("point") if fi.get("type") == "noeud" else None)
        quai = _part_quai(par_id[k]["properties"])
        r = None
        if quai >= 0.7 and k not in anneaux:          # GQ-SYM-003 : quai en alignement droit
            r = ajuster(P[k], tol[k], "bordure", debut=dpt, fin=fpt, droite_seule=True)
            if not r["ok"]:
                r = None
        if r is None:
            r = ajuster(P[k], tol[k], "bordure", debut=dpt, fin=fpt, cap_debut=de.get("cap"), cap_fin=fi.get("cap"),
                        ferme=k in anneaux)
        r["quai_droit"] = bool(quai >= 0.7 and len(r["chaines"]) == 1 and all(p_[1] == 0 for p_ in r["chaines"][0].pieces))
        return r

    for k in ids:
        resultats[k] = un(k)
    # contacts en T : bout posé sur la courbe régularisée de la bordure traversante (GQ-TOP-002)
    for k in ids:
        c = cons.get(k, {})
        de, fi = c.get("debut", {}), c.get("fin", {})
        if de.get("type") != "t" and fi.get("type") != "t":
            continue
        dpt = fpt = None
        for e, nom in ((de, "debut"), (fi, "fin")):
            if e.get("type") == "t":
                o = e["avec"][0]
                Po = resultats[o]["polyligne"]
                q = P[k][0] if nom == "debut" else P[k][-1]
                s_, _, _ = projeter(Po, q[None])
                pt, _ = point_a(Po, s_)
                if nom == "debut":
                    dpt = pt[0]
                else:
                    fpt = pt[0]
        resultats[k] = un(k, fin_t=fpt, debut_t=dpt)
    # écriture
    stats = collections.Counter()
    for k in ids:
        r = resultats[k]
        f = par_id[k]
        ferme = k in anneaux
        coins_ch = None
        if ferme and r["statut"] != "source_gardee":
            # l'anneau garde son origine (abscisses des intervalles) : rotation au point le plus proche du départ
            s0, _, _ = projeter(r["polyligne"], P[k][:1])
            r["chaines"], coins_ch = _chaines_tournees(r["chaines"], float(s0[0]))
            poly, u = RG.densifier(r["chaines"], pas_max=PAS_MAX["bordure"])
            poly[-1] = poly[0]
            r["polyligne"], r["u"] = poly, u
        c = cons.get(k, {})
        bouts = {}
        for nom in ("debut", "fin"):
            e = c.get(nom)
            if e:
                bouts[nom] = {"type": e["type"], "avec": e["avec"], "g1": bool(e.get("g1", False))}
            else:
                bouts[nom] = {"type": "anneau" if ferme else "libre", "avec": [], "g1": ferme}
        extra = {"noeuds": bouts, "quai_alignement_droit": r.get("quai_droit", False)}
        desc = description(r, "bordure", src[k], tol[k], extra, coins_ch)
        desc["regles"] += ["GQ-TOP-001", "GQ-TOP-002", "GQ-TOP-003", "GQ-TOP-005", "GQ-RAY-001", "GQ-PRO-001"]
        if r.get("quai_droit"):
            desc["regles"].append("GQ-SYM-003")
        if any(e["regle"] for e in rap["orientation"] if e["bordure"] == k):
            desc["regles"].append(next(e["regle"] for e in rap["orientation"] if e["bordure"] == k))
        _ETAT.setdefault("bordures_reg", {})[k] = appliquer_bordure(f, r, P[k], C3[k], ferme, desc)
        _ETAT.setdefault("regularisees", set()).add(k)
        stats[r["statut"]] += 1
    # candidats BEV : polyligne et abaissés à jour
    nouv = []
    for kid, _, a in bev_cand:
        f = par_id[kid]
        Pn = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        a2 = next((x for x in f["properties"]["abaisses"] if x["id"] == a["id"]), a)
        nouv.append((kid, Pn, a2))
    rap["statuts"] = dict(sorted(stats.items()))
    _ETAT["rapport"]["bordures"] = rap
    return K, nouv, rap


def decrire_ajouts(K):
    """Bordures ajoutées après la régularisation (ponts K-95nn, ceintures d'îlot « z ») : déjà droites ou
    construites sur des bouts régularisés, elles ne bougent plus (la partition est faite) ; leur suite de
    primitives est relue sur la polyligne (écart ≤ 2 mm) ou, à défaut, une droite par segment (GQ-PRI-003)."""
    n = collections.Counter()
    faites = _ETAT.get("regularisees", set())
    for f in sorted(K, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p["id"] in faites:
            continue
        p.pop("geometrie_reguliere", None)              # champ hérité d'une voisine (copie des propriétés)
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        src = p["prov"]["geometrie"]["src"]
        Pn = RG.nettoyer(P, 1e-4)
        r = None
        if len(Pn) > 2:
            r = RG.ajuster_polyligne(Pn, 0.002, lmin=0.05, rmin=RMIN["bordure"])
            if r is None or r["statut"] != "regularise" or r["ecart_max"] > 0.002:
                r = None
        if r is None:
            ch = []
            for q0, q1 in zip(Pn[:-1], Pn[1:]):
                h = math.atan2(q1[1] - q0[1], q1[0] - q0[0])
                ch.append(RG.Chaine(q0[0], q0[1], h, [[float(np.hypot(*(q1 - q0))), 0.0, 0.0]]))
            r = {"chaines": ch, "d1": np.zeros(1), "d2": np.zeros(1), "statut": "regularise", "ferme": False}
        L = float(abscisses(P)[-1])
        desc = description(r, "bordure", src, tolerance(src),
                           {"noeuds": {"debut": {"type": "libre", "avec": [], "g1": False},
                                       "fin": {"type": "libre", "avec": [], "g1": False}},
                            "quai_alignement_droit": False})
        # abscisses des primitives ramenées exactement à la polyligne (géométrie inchangée)
        fac = L / max(desc["primitives"][-1]["s1"], 1e-9)
        for e in desc["primitives"]:
            e["s0"], e["s1"] = round(e["s0"] * fac, 6), round(e["s1"] * fac, 6)
        _ETAT["sources"].append(("bordures", p["id"], src, tolerance(src), P))     # GQ-PRO-001 (inchangée)
        desc["regles"] += ["GQ-PRI-003"]
        p["geometrie_reguliere"] = desc
        p["prov"]["regularisation"] = {"src": "regle:regles_qualite_geometrique.GQ-PRI-003",
                                       "ref": f"bordure ajoutée après régularisation ({src}) : primitives relues sans déplacement",
                                       "conf": "haute"}
        n[src] += 1
    _ETAT["rapport"].setdefault("bordures_ajoutees", dict(sorted(n.items())))
    return K


def _part_quai(p):
    L = max(p["longueur_m"], 1e-9)
    return sum(it["s1"] - it["s0"] for it in p["intervalles"] if it["profil"] == "QUAI_BUS") / L


# --------------------------------------------------------------------------- limites de la partition
def lignes_partition(lignes):
    """Crochet de surfaces.construire_partition : limites levées (GAM), OSM et fermetures d'origine raster
    ajustées en droites / arcs (GQ-PRI-001, GQ-TOL-001) ; limite parallèle à une bordure rendue à largeur
    constante (GQ-LAR-001). Les lignes de bordure, bâtiments, rampes, bords OpenDRIVE et l'emprise ne
    changent pas (déjà régularisées ou analytiques)."""
    rap = _ETAT["rapport"].setdefault("limites", collections.Counter())
    avants = [(e.get("id"), P) for P, e in lignes if e.get("src") == "bordure_avant"]
    prot = [np.asarray(P, dtype=np.float64)[:, :2] for P, e in lignes
            if e.get("src") in ("bordure_avant", "bordure_arriere", "bordure_bout", "batiment", "rampe")]
    if prot:                                           # premier appel (toutes les lignes) : mémorisées
        _ETAT["protegees"] = (np.vstack([P[:-1] for P in prot]), np.vstack([P[1:] for P in prot]), avants)
    elif "protegees" in _ETAT:                         # appels suivants (fermetures seules)
        avants = _ETAT["protegees"][2]
    PA, PB = _ETAT.get("protegees", (np.zeros((0, 2)), np.zeros((0, 2)), []))[:2]
    out = []
    for P, e in lignes:
        s = e.get("src")
        if s not in SRC_LIMITES or len(P) < 2 or float(abscisses(P)[-1]) < 0.05:
            out.append((P, e))
            continue
        cle = SRC_LIMITES[s]
        tol = float(param("GQ-TOL-001", "T_m")[cle])
        P = np.asarray(P, dtype=np.float64)[:, :2]
        ferme = bool(np.hypot(*(P[0] - P[-1])) < 1e-6 and len(P) > 3)
        r = ajuster(P, tol, "limite", debut=None if ferme else P[0], fin=None if ferme else P[-1], ferme=ferme)
        if r is None:
            out.append((P, e))
            continue
        Pn = r["polyligne"]
        # GQ-TOP-004 : la limite régularisée ne doit pas couper davantage de lignes protégées (bordures,
        # bâtiments, rampes) que la source (sinon éclats) ; sinon tolérance réduite, puis source gardée
        n_src = _croisements(P, PA, PB)
        for essai in (1, 2):
            if _croisements(Pn, PA, PB) <= n_src:
                break
            rap["croisements_evites"] += 1
            if essai == 1:
                r2 = ajuster(P, tol / 4.0, "limite", debut=None if ferme else P[0], fin=None if ferme else P[-1], ferme=ferme)
                if r2 is not None:
                    r, Pn = r2, r2["polyligne"]
            else:
                Pn = RG.nettoyer(P)
                r = dict(r, statut="source_gardee", d1=np.zeros(1), d2=np.zeros(1))
        # GQ-TOP-004 : limite régularisée entièrement à moins d'1 cm des lignes protégées (bosse raster aplatie
        # contre une bordure) : elle ne sépare plus rien et ferait une face d'aire nulle -> retirée
        Qs = RG.reechantillonner(np.asarray(Pn, dtype=np.float64), 0.05)[0]
        A_, B_ = _segments_proches(Qs, PA, PB, 0.02)
        if len(A_):
            dd, _, _ = distance_segments(Qs, A_, B_)
            if float(dd.max()) <= 0.01:
                rap["limites_degenerees_retirees"] += 1
                continue
        lar = None
        if cle == "gam" and not ferme:
            Pn2, lar = largeur_constante(Pn, avants, tol)
            if lar is not None:
                Pn = Pn2
                rap["largeur_constante"] += 1
                rap["largeur_constante_m"] += float(abscisses(Pn)[-1])
        rap[r["statut"]] += 1
        rap[f"n_{s}"] += 1
        d = np.r_[r["d1"], r["d2"]]
        rap[f"ecart_max_{s}"] = max(rap[f"ecart_max_{s}"], float(d.max()))
        e2 = dict(e)
        e2["regularise"] = {"ecart_max_m": round(float(d.max()), 4), "tolerance_m": tol,
                            "n_primitives": sum(len(c.pieces) for c in r["chaines"]), "largeur_constante": lar}
        _ETAT["sources"].append(("limites", f"{s}/{e.get('id', '')}", cle, tol, P))
        _ETAT.setdefault("limites_apres", []).append((s, e.get("id"), Pn, r))
        out.append((Pn, e2))
    return out


def _segments_proches(P, A, B, marge):
    """Segments [A, B] dont la boîte touche la boîte de P élargie de marge."""
    if len(A) == 0:
        return A, B
    bb = (P[:, 0].min() - marge, P[:, 1].min() - marge, P[:, 0].max() + marge, P[:, 1].max() + marge)
    m = ((np.maximum(A[:, 0], B[:, 0]) >= bb[0]) & (np.minimum(A[:, 0], B[:, 0]) <= bb[2])
         & (np.maximum(A[:, 1], B[:, 1]) >= bb[1]) & (np.minimum(A[:, 1], B[:, 1]) <= bb[3]))
    return A[m], B[m]


def _croisements(P, A, B, marge=0.01):
    """Nombre de croisements de la polyligne P avec les segments [A, B] (hors bouts de P à moins de marge)."""
    P = np.asarray(P, dtype=np.float64)[:, :2]
    if len(A) == 0 or len(P) < 2:
        return 0
    bb = (P[:, 0].min() - 0.1, P[:, 1].min() - 0.1, P[:, 0].max() + 0.1, P[:, 1].max() + 0.1)
    m = ((np.maximum(A[:, 0], B[:, 0]) >= bb[0]) & (np.minimum(A[:, 0], B[:, 0]) <= bb[2])
         & (np.maximum(A[:, 1], B[:, 1]) >= bb[1]) & (np.minimum(A[:, 1], B[:, 1]) <= bb[3]))
    A, B = A[m], B[m]
    if len(A) == 0:
        return 0
    p, q = P[:-1], P[1:]
    r = q - p
    sg = B - A
    den = r[:, None, 0] * sg[None, :, 1] - r[:, None, 1] * sg[None, :, 0]
    ap = A[None] - p[:, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (ap[..., 0] * sg[None, :, 1] - ap[..., 1] * sg[None, :, 0]) / den
        u = (ap[..., 0] * r[:, None, 1] - ap[..., 1] * r[:, None, 0]) / den
    ok = (np.abs(den) > 1e-12) & (t > 0) & (t < 1) & (u >= 0) & (u <= 1)
    if not ok.any():
        return 0
    X = p[:, None] + t[..., None] * r[:, None]
    loin = (np.hypot(*(X - P[0]).transpose(2, 0, 1)) > marge) & (np.hypot(*(X - P[-1]).transpose(2, 0, 1)) > marge)
    return int((ok & loin).sum())


def largeur_constante(Pn, avants, tol, regle="GQ-LAR-001", garder_bouts=True):
    """GQ-LAR-001 : si la limite (régularisée, sans coin) longe une bordure à distance quasi constante
    (variation ≤ min(2T, 6 cm)) sur toute sa longueur (≥ 5 m), elle devient le décalé exact de la bordure.
    GQ-PAR-001 (regle) : même construction pour une ligne de marquage à moins de 1,5 m d'une bordure
    (bouts de la ligne projetés sur le décalé : garder_bouts=False)."""
    pr = dict(regles()["GQ-LAR-001"]["parametres"])
    if regle == "GQ-PAR-001":
        pp = regles()["GQ-PAR-001"]["parametres"]
        pr.update(distance_max_m=pp["distance_max_m"], longueur_min_m=2.0)
    L = float(abscisses(Pn)[-1])
    if L < pr["longueur_min_m"]:
        return Pn, None
    var_max = min(pr["variation_largeur_max_ratio_T"] * tol, pr["variation_largeur_max_m"])
    s = np.linspace(0.0, L, max(5, int(L / 0.5) + 1))
    q, _ = point_a(Pn, s)
    meilleur = None
    for kid, Pk in avants:
        if (q[:, 0].min() > Pk[:, 0].max() + pr["distance_max_m"] or q[:, 0].max() < Pk[:, 0].min() - pr["distance_max_m"]
                or q[:, 1].min() > Pk[:, 1].max() + pr["distance_max_m"] or q[:, 1].max() < Pk[:, 1].min() - pr["distance_max_m"]):
            continue
        sk, dk, cote = projeter(Pk, q)
        Lk = float(abscisses(Pk)[-1])
        if sk.min() < 0.2 or sk.max() > Lk - 0.2:
            continue                                   # la limite déborde de la bordure
        dd = dk * cote
        if np.ptp(dd) > var_max or np.abs(dd).max() > pr["distance_max_m"] or np.abs(dd).min() < 0.05:
            continue
        if not (np.all(np.sign(dd) == np.sign(dd[0]))):
            continue
        if meilleur is None or abs(np.median(dd)) < abs(meilleur[1]):
            meilleur = (kid, float(np.median(dd)), float(sk.min()), float(sk.max()), Pk, float(np.ptp(dd)))
    if meilleur is None:
        return Pn, None
    kid, dmed, a, b, Pk, var = meilleur
    from commun import sous_polyligne
    seg = sous_polyligne(Pk, a, b)
    seg = RG.nettoyer(seg, 0.002)
    # normale lissée aux sommets (polyligne densifiée d'arcs et de droites : décalé exact à la flèche près)
    seg_dir = np.diff(seg, axis=0)
    seg_dir /= np.maximum(np.hypot(*seg_dir.T), 1e-12)[:, None]
    nv = np.vstack([seg_dir[:1], seg_dir[:-1] + seg_dir[1:], seg_dir[-1:]])
    nv /= np.maximum(np.hypot(*nv.T), 1e-12)[:, None]
    n = normale_gauche(nv)
    off = seg + n * dmed
    # sens de la limite conservé
    if np.hypot(*(off[0] - Pn[0])) > np.hypot(*(off[-1] - Pn[0])):
        off = off[::-1]
    if garder_bouts:
        off[0], off[-1] = Pn[0], Pn[-1]                 # bouts de la limite (raccords à ≤ var)
    return off, {"bordure": kid, "distance_m": round(abs(dmed), 3), "variation_m": round(var, 3), "regle": regle}


# --------------------------------------------------------------------------- marquages
def marquages(feats):
    """Crochet de composer.py : axes des lignes de marquage ajustés (GQ-PRI-002) ; interruptions remappées."""
    rap = collections.Counter()
    ecarts = []
    for f in sorted(feats, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p.get("classe") not in ("ligne", "transversale") or f["geometry"]["type"] != "LineString":
            continue
        C = np.asarray(f["geometry"]["coordinates"], dtype=np.float64)
        P = repere(C[:, :2])
        src = p.get("src") or p.get("prov", {}).get("geometrie", {}).get("src", "v1")
        tol = tolerance(src)
        _ETAT["sources"].append(("marquages", p["id"], src, tol, P))
        if len(RG.nettoyer(P)) <= 2:
            r = ajuster(P, tol, "marquage", droite_seule=True)
        else:
            r = ajuster(P, tol, "marquage", debut=P[0], fin=P[-1])
        if r is None:
            continue
        Pn = r["polyligne"]
        par = None
        if p.get("classe") == "ligne" and not p.get("sur_bordure") and _ETAT.get("bordures_reg"):
            avants = sorted(_ETAT["bordures_reg"].items())
            Pn2, par = largeur_constante(Pn, avants, tol, regle="GQ-PAR-001", garder_bouts=False)
            if par is not None:
                Ds = RG.reechantillonner(RG.nettoyer(P), 0.05)[0]
                d1s = RG.distance_a_polyligne(Ds, Pn2)
                d2s = RG.distance_a_polyligne(RG.reechantillonner(Pn2, 0.05)[0], RG.nettoyer(P))
                if RG.accepte(d1s, d2s, tol) and abs(float(abscisses(Pn2)[-1]) - float(abscisses(Pn)[-1])) < 0.2:
                    Pn = Pn2
                    rap["paralleles_bordure"] += 1
                else:
                    par = None
        L_old = float(abscisses(P)[-1])
        for cle in ("interruptions", "interruptions_bordures", "interruptions_bouts"):     # intervalles [s0, s1]
            v = p.get(cle)
            if v and all(isinstance(iv, list) and len(iv) == 2 and all(isinstance(x, (int, float)) for x in iv) for iv in v):
                p[cle] = [[round(float(x), 3) for x in remapper_s(P, Pn, iv)] for iv in v]
        f["geometry"]["coordinates"] = coords_geojson(vers_l93(Pn) if C.shape[1] == 2 else
                                                      np.c_[vers_l93(Pn), np.interp(projeter(P, Pn)[0], abscisses(P), C[:, 2])])
        if "longueur_m" in p:
            p["longueur_m"] = round(float(abscisses(repere(np.asarray(f["geometry"]["coordinates"])[:, :2]))[-1]), 3)
        desc = description(r, "marquage", src, tol)
        desc["regles"] += ["GQ-TOP-005", "GQ-PRO-001"]
        if par is not None:                              # axe = décalé exact de la bordure (droites / arcs concentriques)
            rp = RG.ajuster_polyligne(Pn, 0.002, lmin=0.05, rmin=RMIN["marquage"])
            if rp is not None and rp["statut"] == "regularise":
                d1s = RG.distance_a_polyligne(RG.reechantillonner(RG.nettoyer(P), 0.05)[0], Pn)
                rp["d1"], rp["d2"] = d1s, RG.distance_a_polyligne(RG.reechantillonner(Pn, 0.05)[0], RG.nettoyer(P))
                rp["statut"] = "regularise"
                desc = description(rp, "marquage", src, tol, {"parallele_bordure": par})
                desc["regles"] += ["GQ-TOP-005", "GQ-PRO-001", "GQ-PAR-001"]
        p["geometrie_reguliere"] = desc
        p.setdefault("prov", {})["regularisation"] = {
            "src": "regle:regles_qualite_geometrique.GQ-TOL-001",
            "ref": f"axe {desc['n_primitives']} ; écart max {desc['ecart_max_m']:.3f} m (T {tol:.2f} m, source {src}) ; longueur {L_old:.3f} m",
            "conf": "haute" if desc["statut"] == "regularise" else "faible"}
        rap[r["statut"]] += 1
        rap[f"{p['classe']}_{'droite' if len(r['chaines']) == 1 and len(r['chaines'][0].pieces) == 1 else 'multi'}"] += 1
        ecarts.append((src, desc["ecart_max_m"]))
    _ETAT["rapport"]["marquages"] = {"statuts": dict(sorted(rap.items())),
                                     "ecart_max_par_source_m": {s: round(max(e for s2, e in ecarts if s2 == s), 4)
                                                                for s in sorted({s for s, _ in ecarts})}}
    return feats


# --------------------------------------------------------------------------- archive et rapport
def ecrire_sources(dossier_base):
    """GQ-PRO-001 : géométries sources (avant régularisation) dans base/regularisation_sources.geojson."""
    feats = []
    vus = set()
    for fam, eid, src, tol, P in _ETAT["sources"]:
        cle = (fam, eid)
        if cle in vus:
            continue
        vus.add(cle)
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(vers_l93(P))},
                      "properties": {"id": f"{fam}:{eid}", "famille": fam, "entite": eid, "src": src,
                                     "tolerance_m": tol, "role": "géométrie source avant régularisation (non fabriquée)"}})
    f = dossier_base / "regularisation_sources.geojson"
    ecrire_geojson(f, feats, "regularisation_sources",
                   {"schema": "description_scene_v2/0.3", "famille": "regularisation_sources",
                    "regles": "GQ-PRO-001 (regles_qualite_geometrique.json)",
                    "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98)"})
    return f, len(feats)


def rapport():
    """Rapport sérialisable de la dernière exécution (manifeste : statistiques.regularisation)."""
    r = _ETAT["rapport"]
    out = {}
    if "bordures" in r:
        b = r["bordures"]
        ori = b["orientation"]
        out["orientation"] = {
            "regles": ["GQ-ORI-001", "GQ-ORI-002"],
            "bordures_verifiees": len(ori),
            "retournees": [e for e in ori if e["decision"] == "retournee"],
            "conflits_journalises": [e for e in ori if e.get("conflit") and e["decision"] == "garde"],
        }
        out["noeuds"] = b["noeuds"]
        out["bordures_statuts"] = b["statuts"]
    if "bordures_ajoutees" in r:
        out["bordures_ajoutees_decrites"] = r["bordures_ajoutees"]
    if "limites" in r:
        out["limites"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in sorted(r["limites"].items())}
    if "marquages" in r:
        out["marquages"] = r["marquages"]
    return arrondi(out, 4)
