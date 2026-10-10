"""Passages : zébras (bandes v1 regroupées et paramétrées) et traversées cyclables (files de pavés
Chronovélo, de carrés 0,50 ou de pavés mesurés), en entités paramétriques.

Zébra (classe passage, type zebra) :
    axe [A, B] = centres de la première et de la dernière bande (LineString) ; bande k centrée en
    A + k·pas_axe_m·(B − A)/|B − A| ; bandes rectangulaires largeur_bande_m × longueur_bande_m, grand côté
    au cap cap_bandes_deg (parallèle à l'axe de la chaussée) ; intervalle_m = vide entre bandes mesuré
    perpendiculairement aux bandes (pas = largeur + intervalle ; pas_axe = pas / cos(obliquité)) ;
    coupures = indices de bandes absentes (refuge) ; nb_bandes = bandes peintes.
Traversée cyclable (classe passage, type traversee_cyclable) : files [{axe [A, B], gabarit ou
    dimensions, pas_m, nb, absents, cap_deg}] ; tuile k centrée en A + k·pas·dir.
"""
import collections
import math

import numpy as np

import marquages_commun as M

LB = 0.50                     # largeur de bande IISR (art. 118)
TOL_RESIDU = 0.15             # écart d'une bande à son emplacement au-delà duquel elle est écartée


# --------------------------------------------------------------------------- regroupement
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
    return sorted(g.values(), key=lambda ms: ms[0]["id"])


def _proche_bande(a, b):
    oa, ob = a["obb"], b["obb"]
    if abs(oa["u"] @ ob["u"]) < 0.95:
        return False
    d = ob["c"] - oa["c"]
    return abs(d @ oa["v"]) < 1.7 and abs(d @ oa["u"]) < 1.5


def _axe_groupe(ms):
    u = ms[0]["obb"]["u"]
    us = np.array([m["obb"]["u"] * (1 if m["obb"]["u"] @ u >= 0 else -1) for m in ms])
    u = us.mean(axis=0)
    u /= np.hypot(*u)
    n = np.array([-u[1], u[0]])
    c = np.array([m["obb"]["c"] for m in ms])
    return u, n, c


def _fusion_refuge(groupes):
    """Fusionne deux groupes de bandes alignés de part et d'autre d'un refuge (même cap de bandes,
    centres sur la même droite à 0,5 m près, longueurs voisines, écart < 8 m)."""
    fait = True
    while fait:
        fait = False
        for i in range(len(groupes)):
            for j in range(i + 1, len(groupes)):
                gi, gj = groupes[i], groupes[j]
                if len(gi) < 2 or len(gj) < 2:
                    continue
                ui, ni, ci = _axe_groupe(gi)
                uj, nj, cj = _axe_groupe(gj)
                if abs(ui @ uj) < 0.995:
                    continue
                if abs(np.median([m["obb"]["L"] for m in gi]) - np.median([m["obb"]["L"] for m in gj])) > 0.3:
                    continue
                d = (cj - ci.mean(axis=0)) @ ui
                if np.max(np.abs(d)) > 0.3:
                    continue
                ecart = min(abs(a - b) for a in ci @ ni for b in cj @ ni)
                if ecart >= 8.0:
                    continue
                essai, ec = _ajuster_zebra(gi + gj)
                if essai is None or ec or np.max(np.abs(essai["residus"])) > 0.05 or np.ptp(essai["L"]) > 0.1:
                    continue
                groupes[i] = sorted(gi + gj, key=lambda m: m["id"])
                del groupes[j]
                fait = True
                break
            if fait:
                break
    return groupes


# --------------------------------------------------------------------------- zébras
def _ajuster_zebra(ms):
    """Paramètres d'un zébra : pas, emplacements, axe, obliquité, longueur ; renvoie (params, écartées)."""
    u, n, c = _axe_groupe(ms)
    s = c @ n
    o = np.argsort(s)
    ms, c, s = [ms[i] for i in o], c[o], s[o]
    ds = np.diff(s)
    pas = float(np.median(ds[ds < 1.6])) if np.any(ds < 1.6) else 1.0
    k = np.round((s - s[0]) / pas).astype(int)
    # ajustement linéaire s = s0 + k·pas (moindres carrés)
    for _ in range(2):
        A = np.c_[np.ones(len(k)), k]
        (s0, pas), *_ = np.linalg.lstsq(A, s, rcond=None)
        k = np.round((s - s0) / pas).astype(int)
    res = s - (s0 + k * pas)
    garde = np.abs(res) <= TOL_RESIDU
    if garde.sum() < 2:
        return None, ms
    ecartees = [m for m, g in zip(ms, garde) if not g]
    ms, c, s, k = [m for m, g in zip(ms, garde) if g], c[garde], s[garde], k[garde]
    if ecartees:                                   # nouvel ajustement sans les bandes écartées
        (s0, pas), *_ = np.linalg.lstsq(np.c_[np.ones(len(k)), k], s, rcond=None)
    res = s - (s0 + k * pas)
    s0 += k.min() * pas
    k = k - k.min()
    t = c @ u
    # axe : droite des centres (obliquité si les centres glissent le long des bandes)
    if len(c) >= 3 and np.ptp(t) > 0.15:
        pente = np.polyfit(s - s.mean(), t, 1)[0]
    else:
        pente = 0.0
    if abs(math.degrees(math.atan(pente))) < 2.0:
        pente = 0.0
    t0 = float(np.mean(t - pente * (s - s.mean())))
    sA, sB = s0 + k.min() * pas, s0 + k.max() * pas
    pt = lambda sv: n * sv + u * (t0 + pente * (sv - s.mean()))
    A, B = pt(sA), pt(sB)
    occupes = sorted(set(k.tolist()))
    absents = [i for i in range(k.max() + 1) if i not in occupes]
    L = np.array([m["obb"]["L"] for m in ms])
    sources = collections.Counter(m["p"]["source"].split(" (")[0] for m in ms)
    # longueur : levé GAM / plan = exact ; ortho : médiane (bouts usés)
    longueur = float(np.median(L))
    return {"u": u, "n": n, "pas": float(pas), "A": A, "B": B, "k": k, "absents": absents, "pente": pente,
            "residus": res, "longueur": longueur, "L": L, "sources": sources, "ms": ms}, ecartees


def zebras(xo=None):
    """Passages piétons -> (features locales, devenir des MQ, mesures)."""
    bandes = [m for m in M.v1() if m["p"]["type"] == "passage_pieton_bande"]
    groupes = _fusion_refuge(_unions(bandes, _proche_bande))
    entites, devenir, isolees = [], {}, []
    for g in groupes:
        if len(g) < 2:
            isolees += g
            continue
        par, ec = _ajuster_zebra(g)
        isolees += ec
        if par is None:
            continue
        ms = par["ms"]
        ids = sorted(m["id"] for m in ms)
        eid = M.ident("MP", ids)
        obliq = math.atan(par["pente"])
        pas_axe = par["pas"] / math.cos(obliq)
        etat = collections.Counter(m["p"]["etat"] for m in ms).most_common(1)[0][0]
        usure = collections.Counter(m["p"]["usure"] for m in ms).most_common(1)[0][0]
        couv = M.mediane_ou([m["p"]["couverture"] for m in ms])
        src_geo = "gam" if par["sources"].most_common(1)[0][0].startswith("GAM") else (
            "plan2025" if par["sources"].most_common(1)[0][0].startswith("plan") else "ortho2022")
        cap_b = M.cap_de(par["u"])
        e = {
            "id": eid, "classe": "passage", "type": "zebra", "couleur": "blanc",
            "geom": ("LineString", np.vstack([par["A"], par["B"]])),
            "axe_m": float(np.hypot(*(par["B"] - par["A"]))),
            "largeur_bande_m": LB, "intervalle_m": round(par["pas"] - LB, 3),
            "pas_m": round(par["pas"], 3), "pas_axe_m": round(pas_axe, 3),
            "longueur_bande_m": round(par["longueur"], 3), "cap_bandes_deg": round(cap_b, 2),
            "obliquite_deg": round(math.degrees(obliq), 2),
            "nb_bandes": len(ms), "nb_emplacements": int(par["k"].max() + 1), "coupures": par["absents"],
            "usure": usure, "couverture": couv, "etat": etat,
            "groupe": ms[0]["p"]["groupe"], "branche": ms[0]["p"]["branche"], "lien_v1": ids,
            "mesures": {"residu_bandes_max_m": round(float(np.max(np.abs(par["residus"]))), 3),
                        "ecart_longueur_max_m": round(float(np.max(np.abs(par["L"] - par["longueur"]))), 3)},
            "prov": {"geometrie": {"src": src_geo, "ref": f"bandes v1 {ids[0]}..{ids[-1]} ({len(ids)}) : pas et axe ajustés (moindres carrés)",
                                   "conf": "haute" if src_geo == "gam" else "moyenne"},
                     "largeur_bande_m": {"src": "norme:IISR_7_art118", "ref": "bande 0,50 m", "conf": "haute"},
                     "intervalle_m": {"src": src_geo, "ref": "pas médian des bandes v1 - 0,50", "conf": "haute" if src_geo == "gam" else "moyenne"}},
        }
        if par["absents"]:
            e["prov"]["coupures"] = {"src": src_geo, "ref": "emplacements sans bande entre deux groupes alignés (refuge)", "conf": "moyenne"}
        lmin = M.spec()["passages_pietons"]["longueur_bande_m"]["ville_min"]
        if par["longueur"] < lmin - 0.005:
            e["ecarts_iisr"] = [f"longueur de bande {par['longueur']:.2f} m < {lmin:.2f} m (minimum IISR en ville) : mesurée sur le site, gardée"]
        entites.append(e)
        for m in ms:
            devenir[m["id"]] = ("genere", eid, "bande du zébra")
    return entites, devenir, isolees, groupes


# --------------------------------------------------------------------------- traversées cyclables
def _proche_tuile(a, b):
    if a["p"]["groupe"] != b["p"]["groupe"] or a["p"]["branche"] != b["p"]["branche"]:
        return False
    if a["p"]["modulation"] != b["p"]["modulation"]:
        return False
    oa, ob = a["obb"], b["obb"]
    if abs(oa["L"] - ob["L"]) > 0.15 or abs(oa["W"] - ob["W"]) > 0.15:
        return False
    return float(np.hypot(*(oa["c"] - ob["c"]))) < 1.3


def _gabarit_tuile(L, W, mod):
    g = M.spec()["gabarits"]
    for nom in ("PAVE_CHRONOVELO", "CARRE_TRAVERSEE_CYCLABLE", "DAMIER_BUS"):
        gl, gw = sorted((g[nom]["longueur_m"], g[nom]["largeur_m"]), reverse=True)
        if abs(L - gl) <= 0.04 and abs(W - gw) <= 0.04:
            return nom
    return None


def _droite_dominante(g):
    """Plus grande file alignée d'un amas de tuiles (paires voisines comme directions candidates,
    tuiles à moins de 0,08 m de la droite) : (tuiles de la file, autres)."""
    c = np.array([m["obb"]["c"] for m in g])
    meilleur = (1, 0.0, [0])
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            d = c[j] - c[i]
            L = float(np.hypot(*d))
            if not 0.3 <= L <= 1.3:
                continue
            d = d / L
            n = np.array([-d[1], d[0]])
            lat = (c - c[i]) @ n
            inl = np.where(np.abs(lat) < 0.08)[0]
            cle = (len(inl), -float(np.sqrt(np.mean(lat[inl] ** 2))))
            if cle > meilleur[:2]:
                meilleur = (*cle, inl.tolist())
    garde = set(meilleur[2])
    return [m for k, m in enumerate(g) if k in garde], [m for k, m in enumerate(g) if k not in garde]


def files_tuiles(tuiles):
    """Files (rangées) de tuiles alignées : [{tuiles triées, A, B, dir, pas, k, absents, res, lat}]."""
    out = []
    for g in _unions(tuiles, _proche_tuile):
        reste = g
        while reste:
            file, reste = _droite_dominante(reste)
            out.append(_file(file))
            if reste:
                reste = sorted(reste, key=lambda m: m["id"])
    return sorted(out, key=lambda f: f["tuiles"][0]["id"])


def _file(g):
    """Ajustement d'une file : direction (ACP des centres), pas et emplacements (moindres carrés)."""
    c = np.array([m["obb"]["c"] for m in g])
    if len(g) >= 2:
        cc = c - c.mean(axis=0)
        w, V = np.linalg.eigh(cc.T @ cc)
        d = V[:, int(np.argmax(w))]
    else:
        d = g[0]["obb"]["v"]
    if d[0] < 0 or (abs(d[0]) < 1e-9 and d[1] < 0):
        d = -d
    s = c @ d
    o = np.argsort(s)
    g, c, s = [g[i] for i in o], c[o], s[o]
    if len(g) >= 2:
        ds = np.diff(s)
        pas = float(np.median(ds))
        k = np.round((s - s[0]) / pas).astype(int)
        (s0, pas), *_ = np.linalg.lstsq(np.c_[np.ones(len(k)), k], s, rcond=None)
        k = np.round((s - s0) / pas).astype(int)
        s0 += k.min() * pas
        k -= k.min()
        res = s - (s0 + k * pas)
    else:
        pas, k, res, s0 = 0.0, np.array([0]), np.array([0.0]), s[0]
    n = np.array([-d[1], d[0]])
    t0 = float(np.mean(c @ n))
    A = d * s0 + n * t0
    B = A + d * pas * k.max()
    return {"tuiles": g, "A": A, "B": B, "dir": d, "pas": float(pas), "k": k, "lat": c @ n - t0,
            "absents": [i for i in range(int(k.max()) + 1) if i not in set(k.tolist())], "res": res}


def traversees_cyclables():
    tuiles = [m for m in M.v1() if m["p"]["type"] == "damier"]
    files = files_tuiles(tuiles)
    # regroupement des files d'un même (groupe, branche) en une traversée
    par_trav = collections.defaultdict(list)
    for f in files:
        p = f["tuiles"][0]["p"]
        par_trav[(p["groupe"], p["branche"])].append(f)
    entites, devenir = [], {}
    for (groupe, branche), fs in sorted(par_trav.items()):
        ids = sorted(m["id"] for f in fs for m in f["tuiles"])
        eid = M.ident("MP", ids)
        lst = []
        for f in sorted(fs, key=lambda f: min(m["id"] for m in f["tuiles"])):
            ms = f["tuiles"]
            L = float(np.median([m["obb"]["L"] for m in ms]))
            W = float(np.median([m["obb"]["W"] for m in ms]))
            gab = _gabarit_tuile(L, W, ms[0]["p"]["modulation"])
            # cap de la tuile : +y du gabarit le long de la file ; pour un rectangle mesuré, grand côté
            # perpendiculaire à la file s'il l'est sur le relevé
            u0 = ms[0]["obb"]["u"]
            grand_cote_perp = abs(u0 @ f["dir"]) < 0.5
            item = {"axe": [f["A"], f["B"]], "nb": len(ms), "pas_m": round(f["pas"], 3), "absents": f["absents"],
                    "cap_deg": round(M.cap_de(f["dir"]), 2), "couleur": ms[0]["p"]["couleur"],
                    "lien_v1": sorted(m["id"] for m in ms),
                    "residu_max_m": round(float(np.max(np.abs(f["res"]))), 3)}
            if gab:
                item["gabarit"] = gab
            else:
                item["tuile_m"] = {"perp_file": round(L if grand_cote_perp else W, 2),
                                   "le_long_file": round(W if grand_cote_perp else L, 2)}
            lst.append(item)
        couleur = collections.Counter(m["p"]["couleur"] for f in fs for m in f["tuiles"]).most_common(1)[0][0]
        allms = [m for f in fs for m in f["tuiles"]]
        srcs = collections.Counter(m["p"]["source"].split(" (")[0] for m in allms)
        s0 = srcs.most_common(1)[0][0]
        src_geo = "gam" if s0.startswith("GAM") else ("plan2025" if s0.startswith("plan") else "ortho2022")
        e = {"id": eid, "classe": "passage", "type": "traversee_cyclable", "couleur": couleur,
             "geom": ("MultiLineString", [np.vstack(it["axe"]) if it["nb"] > 1 else np.vstack([it["axe"][0], it["axe"][0] + 0.001 * np.array([math.cos(math.radians(it["cap_deg"])), math.sin(math.radians(it["cap_deg"]))])]) for it in lst]),
             "files": lst, "nb_tuiles": len(allms),
             "usure": collections.Counter(m["p"]["usure"] for m in allms).most_common(1)[0][0],
             "couverture": M.mediane_ou([m["p"]["couverture"] for m in allms]),
             "etat": collections.Counter(m["p"]["etat"] for m in allms).most_common(1)[0][0],
             "groupe": groupe, "branche": branche, "lien_v1": ids,
             "prov": {"geometrie": {"src": src_geo, "ref": f"tuiles v1 {ids[0]}..{ids[-1]} ({len(ids)}) : files, pas et axes ajustés", "conf": "moyenne"},
                      "gabarit": {"src": "regle:marquages_geometrie.gabarits", "ref": "PAVE_CHRONOVELO / CARRE_TRAVERSEE_CYCLABLE (pratique du site, non IISR) ; sinon tuile mesurée", "conf": "moyenne"}}}
        entites.append(e)
        for m in allms:
            devenir[m["id"]] = ("genere", eid, "tuile de traversée cyclable")
    return entites, devenir


def emprises_zebras(entites, marge=0.5):
    """Rectangles (local) des zébras élargis de `marge` : zone où les lignes s'interrompent (art. 118)."""
    out = []
    for e in entites:
        if e.get("type") != "zebra":
            continue
        A, B = e["geom"][1]
        h = math.radians(e["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        n = np.array([-u[1], u[0]])
        pts = []
        for P in (A, B):
            for a in (-1, 1):
                for b in (-1, 1):
                    pts.append(P + u * a * (e["longueur_bande_m"] / 2 + marge) + n * b * (LB / 2 + marge))
        out.append((e["id"], M.enveloppe_convexe(np.array(pts))))
    return out
