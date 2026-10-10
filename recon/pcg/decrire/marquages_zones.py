"""Zones (hachures, zigzag d'arrêt de bus, aplats, surfaces colorées), fantômes et polygones gardés :
paramètres quand la forme est normée, sinon polygone simplifié sans marche d'escalier.

Hachures (classe zone, type hachures) : polygone (contour de la zone) + bandes parallèles de
    largeur bande_m, de direction cap_bandes_deg, d'axes passant par origine + k·pas_m·n (n normale
    gauche de la direction), découpées par le polygone ; contour_peint : ligne continue 3u le long du
    contour (sinon portée par les lignes voisines).
Zigzag (classe zone, type zigzag) : axe = ligne de base côté bordure [A, B], amplitude_m (à l'axe du
    trait), periode_m, trait_m, cote (+1 : sommets à gauche de A->B), n_periodes ; sommets sur la
    ligne d'amplitude aux demi-périodes impaires.
Polygones v1 hors gabarit (aplat, surface_coloree, divers, bande isolée, fantôme) : primitive ajustée quand elle
    explique le polygone v1 (IoU) : rectangle orienté (remplissage de la boîte ≥ 0,80 ; IoU ≥ 0,75), ruban à
    largeur constante sur un axe ajusté (largeur ≤ 0,40 m, élancement ≥ 4 ; IoU ≥ 0,70), gabarit de flèche IISR
    (fantômes de 3 à 4,6 m ; IoU ≥ 0,55), T de stationnement ; fantômes : rectangle orienté ou réunion de 2 à 3 rectangles
    adjacents dès IoU ≥ 0,5 (empreinte à bords droits) ; sinon contour redressé (droites ajustées,
    marquages_glyphes.redresser : lissage 5 cm, Douglas-Peucker 2,5 cm, coins vifs ; aucune marche d'escalier) ;
    levés vectoriels GAM / plan sans marche : Douglas-Peucker 1 cm. Fantômes qui se recouvrent : une seule entité
    (réunion à la fabrication, une seule empreinte).
"""
import collections
import math

import numpy as np

import marquages_commun as M
import marquages_glyphes as GL
from commun import abscisses, aire_signee, projeter


def _iou(m, polys):
    return M.iou(m["polys"], polys, res=0.01)


def rectangles_unis(m, k):
    """k rectangles adjacents le long de l'axe de la boîte orientée, chacun ajusté (boîte dans le repère de l'axe) sur les
    cellules (2 cm) du polygone v1 de sa tranche : forme d'empreinte sans marche, -> polygones."""
    o = M.rect_min(np.vstack([pp[0] for pp in m["polys"]]))
    P = np.vstack([pp[0] for pp in m["polys"]])
    x0, y0 = P.min(axis=0) - 0.04
    nx, ny = int((P[:, 0].max() - x0) / 0.02) + 4, int((P[:, 1].max() - y0) / 0.02) + 4
    msk = M.raster_masque(m["polys"], x0, y0, nx, ny, 0.02)
    r, c = np.nonzero(msk)
    if len(r) < 4 * k:
        return None
    G = np.c_[x0 + (c + 0.5) * 0.02, y0 + ny * 0.02 - (r + 0.5) * 0.02]
    a, b = (G - o["c"]) @ o["u"], (G - o["c"]) @ o["v"]
    bornes = np.quantile(a, np.linspace(0, 1, k + 1))
    bornes[0], bornes[-1] = a.min() - 0.01, a.max() + 0.01
    out = []
    for i in range(k):
        sel = (a >= bornes[i]) & (a <= bornes[i + 1])
        if sel.sum() < 4:
            return None
        v0, v1 = float(np.percentile(b[sel], 2)) - 0.01, float(np.percentile(b[sel], 98)) + 0.01
        u0, u1 = float(bornes[i]), float(bornes[i + 1])
        out.append([GL.trigo(np.array([o["c"] + o["u"] * uu + o["v"] * vv for uu, vv in ((u0, v0), (u1, v0), (u1, v1), (u0, v1))]))])
    return out


def primitive(m, fleches=False, fantome=False):
    """Primitive ajustée sur une marque v1 : (polygones, description, méthode, IoU). Fantômes (fantome=True) : rectangle
    orienté ou réunion de 2 à 3 rectangles adjacents dès IoU ≥ 0,5 (empreinte à bords droits) avant le contour redressé."""
    o = M.rect_min(np.vstack([pp[0] for pp in m["polys"]]))
    aire = m["aire"]
    rempl = aire / max(o["L"] * o["W"], 1e-9)
    cands = []
    if fantome and o["W"] >= 0.04:
        L, W = round(o["L"], 2), round(o["W"], 2)
        polys = [[GL.trigo(np.array([o["c"] + o["u"] * a * L / 2 + o["v"] * b * W / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))]]
        cands.append((0.50, polys, {"type": "rectangle", "centre_local": o["c"], "cap_deg": round(M.cap_de(o["u"]), 3),
                                    "longueur_m": L, "largeur_m": W}, "rectangle"))
        for k in (2, 3):
            ru = rectangles_unis(m, k)
            if ru:
                cands.append((0.50 + 0.03 * (k - 1), ru, {"type": "rectangles", "n": k, "cap_deg": round(M.cap_de(o["u"]), 3)},
                              f"{k} rectangles"))
    if rempl >= 0.80 and o["W"] >= 0.04:
        L, W = round(o["L"], 2), round(o["W"], 2)
        polys = [[GL.trigo(np.array([o["c"] + o["u"] * a * L / 2 + o["v"] * b * W / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))]]
        cands.append((0.75, polys, {"type": "rectangle", "centre_local": o["c"], "cap_deg": round(M.cap_de(o["u"]), 3),
                                    "longueur_m": L, "largeur_m": W}, "rectangle"))
    if o["W"] <= 0.40 and o["L"] >= 4 * o["W"] and rempl >= 0.5:
        import marquages_lignes as LG
        axe = LG._axe_ajuste([dict(m, _axe=np.vstack([o["c"] - o["u"] * o["L"] / 2, o["c"] + o["u"] * o["L"] / 2]))])
        sg, d, _ = projeter(axe, np.vstack([pp[0] for pp in m["polys"]]))
        axe = M.dedoublonner(LG._sous(axe, max(0.0, float(sg.min())), float(sg.max())))
        Lx = float(abscisses(axe)[-1])
        w = round(aire / max(Lx, 1e-6), 2)
        if len(axe) >= 2 and w >= 0.04:
            cands.append((0.70, [[GL.trait(axe, w)]], {"type": "ruban", "axe_local": axe, "largeur_m": w}, "ruban"))
    if fleches and 3.0 <= o["L"] <= 4.6 and 0.45 <= o["W"] <= 1.5:
        import marquages_symboles as SY
        cu = M.cap_de(o["u"])
        best = None
        for cap in (cu, cu + 180.0):
            for nom in ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG"):
                org, i = SY.ajuster_gabarit(m, nom, cap, 1.0, fenetre=(0.30, 0.60))
                if best is None or i > best[0] + 1e-9:
                    best = (i, nom, cap % 360.0, org)
        i, nom, cap, org = best
        polys = [[M.poser(rr, org, cap) for rr in poly] for poly in M.gabarit(nom)]
        cands.append((0.55, polys, {"type": "gabarit", "gabarit": nom, "origine_local": org, "cap_deg": round(cap, 3)}, f"gabarit {nom}"))
    best = None
    for seuil, polys, desc, meth in cands:
        i = _iou(m, polys)
        # une primitive plus composée (k rectangles) doit gagner au moins 0,03 d'IoU par rectangle ajouté
        bonus = 0.03 * (desc.get("n", 1) - 1)
        if i >= seuil and (best is None or i - bonus > best[3] - 0.03 * (best[1].get("n", 1) - 1) + 1e-9):
            best = (polys, desc, meth, i)
    if best:
        return best
    if m["raster"]:
        # redressement de plus en plus fort jusqu'à ce qu'aucune marche ne subsiste (détecteur élargi)
        for prm in (dict(tol=0.025, lmin=0.06, lisse=0.05), dict(tol=0.03, lmin=0.10, lisse=0.06),
                    dict(tol=0.03, lmin=0.15, lisse=0.08), dict(tol=0.04, lmin=0.20, lisse=0.10)):
            polys = [[GL.redresser(pp[0], **prm)] for pp in m["polys"]]
            if not any(M.escalier(pp[0]) for pp in polys):
                break
        return polys, {"type": "contour_redresse", "lissage_m": prm["lisse"], "tolerance_m": prm["tol"], "arete_min_m": prm["lmin"]},             "redressé", _iou(m, polys)
    polys = [[M.douglas_peucker(rr, 0.01, ferme=True) if len(rr) > 4 else rr for rr in poly] for poly in m["polys"]]
    return polys, {"type": "contour_leve"}, "dp", _iou(m, polys)


def t_stationnement(m):
    """T de stationnement ajusté (4 orientations, IoU) : barre = côté de la boîte, jambe = l'autre, trait 2u."""
    import marquages_lignes as LG
    import marquages_symboles as SY
    o = m["obb"]
    w = round(2 * LG.u_itineraire(m["p"]["branche"]), 3)
    best = None
    for k in range(4):
        cap = (M.cap_de(o["u"]) + 90.0 * k) % 360.0
        barre, jambe = (o["L"], o["W"]) if k % 2 else (o["W"], o["L"])
        prm = {"nom": "t_stationnement", "barre_m": round(barre, 3), "jambe_m": round(jambe, 3), "trait_m": w}
        org = M.poser(np.array([[0.0, jambe / 2]]), o["c"], cap)[0]
        polys = [[M.poser(r, org, cap) for r in poly] for poly in SY.construire_glyphe(prm)]
        i = _iou(m, polys)
        if best is None or i > best[0] + 1e-9:
            best = (i, prm, org, cap, polys)
    return best


def _base(m):
    p = m["p"]
    return {"couleur": p["couleur"], "usure": p["usure"], "couverture": p["couverture"], "etat": p["etat"],
            "groupe": p["groupe"], "branche": p["branche"], "lien_v1": [m["id"]]}


def _src(m):
    s = m["p"]["source"]
    return "gam" if s.startswith("GAM") else ("plan2025" if s.startswith("plan") else "ortho2022")


def hachures():
    V = {m["id"]: m for m in M.v1()}
    groupes = {}
    for m in M.v1():
        if m["p"]["type"] == "hachures" and m["p"]["groupe"] == "hachures":
            groupes.setdefault(m["p"]["branche"], []).append(m)
    entites, devenir = [], {}
    for branche, ms in sorted(groupes.items()):
        us, cs = [], []
        for m in ms:
            r = m["r"]
            e = np.diff(np.vstack([r, r[:1]]), axis=0)
            L = np.hypot(*e.T)
            k = int(np.argmax(L))
            u = e[k] / L[k]
            us.append(u if not us or u @ us[0] >= 0 else -u)
            cs.append(r.mean(axis=0))
        u = np.mean(us, axis=0)
        u /= np.hypot(*u)
        if u[0] < 0:
            u = -u
        n = np.array([-u[1], u[0]])
        cs = np.array(cs)
        sn = cs @ n
        o = np.argsort(sn)
        pas = float(np.median(np.diff(sn[o])))
        k = np.round((sn - sn[o[0]]) / pas)
        (s0, pas), *_ = np.linalg.lstsq(np.c_[np.ones(len(k)), k], sn, rcond=None)
        origine = cs[o[0]] + n * (s0 - sn[o[0]])
        contour = [m for m in M.v1() if m["p"]["type"] == "ligne_continue" and m["p"]["groupe"] == "hachures"
                   and m["p"]["branche"] == branche]
        pts = np.vstack([m["r"] for m in ms + contour])
        poly = M.enveloppe_convexe(pts)
        poly = M.douglas_peucker(poly, 0.01, ferme=True)
        c, w, V_ = pts.mean(axis=0), *np.linalg.eigh(np.cov((pts - pts.mean(axis=0)).T))
        axe = V_[:, int(np.argmax(w))]
        angle = math.degrees(math.acos(min(1.0, abs(float(axe @ u)))))
        ids = sorted(m["id"] for m in ms + contour)
        eid = M.ident("MZ", ids)
        e = {"id": eid, "classe": "zone", "type": "hachures", "couleur": "blanc",
             "geom": ("Polygon", [[poly]]), "bande_m": 0.5, "pas_m": round(pas, 3),
             "cap_bandes_deg": round(M.cap_de(u), 3), "origine_bandes_local": origine,
             "angle_axe_zone_deg": round(angle, 2), "contour_peint": bool(contour),
             "contour_largeur_m": 0.15 if contour else None, "nb_bandes_v1": len(ms),
             "usure": ms[0]["p"]["usure"], "couverture": M.mediane_ou([m["p"]["couverture"] for m in ms]),
             "etat": ms[0]["p"]["etat"], "groupe": "hachures", "branche": branche, "lien_v1": ids,
             "prov": {"geometrie": {"src": "gam", "ref": "enveloppe des bandes levées" + (" et du contour levé" if contour else ""), "conf": "moyenne"},
                      "pas_m": {"src": "gam", "ref": f"pas perpendiculaire mesuré sur {len(ms)} bandes (IISR : 1,85)", "conf": "haute"},
                      "bande_m": {"src": "norme:IISR_7_art117-2", "ref": "bande 0,50", "conf": "haute"}}}
        entites.append(e)
        for i in ids:
            devenir[i] = ("genere", eid, "zone hachurée paramétrique (bande, pas, cap)")
    return entites, devenir


def zigzags():
    """Zigzags d'arrêt de bus : axe levé GAM (sommets alternés base / amplitude, traits d'extrémité)."""
    entites, devenir = [], {}
    for m in M.v1():
        if m["p"]["type"] != "zigzag_arret_bus" or not M.gam_refs(m["p"]):
            continue
        P = M.gam_lin()[M.gam_refs(m["p"])[0]]
        c = P[1:-1].mean(axis=0)
        w, V = np.linalg.eigh(np.cov((P[1:-1] - c).T))
        u = V[:, int(np.argmax(w))]
        if (P[-1] - P[0]) @ u < 0:
            u = -u
        n = np.array([-u[1], u[0]])
        t = (P - c) @ n
        s = (P - c) @ u
        base = np.arange(len(P)) % 2 == 0          # P0, P2, ... sur la bordure (traits d'extrémité depuis la base)
        tb, ta = float(np.median(t[base])), float(np.median(t[~base]))
        amp = abs(ta - tb)
        cote = 1 if ta > tb else -1
        som = np.sort(s[1:-1][~base[1:-1]])
        periode = float(np.median(np.diff(som))) if len(som) > 1 else 5.0
        A = c + u * s[0] + n * tb
        B = c + u * s[-1] + n * tb
        L = float(s[-1] - s[0])
        eid = M.ident("MZ", [m["id"]])
        e = dict(_base(m), id=eid, classe="zone", type="zigzag",
                 geom=("LineString", np.vstack([A, B])), amplitude_m=round(amp, 3), periode_m=round(periode, 3),
                 trait_m=0.12, cote=cote, longueur_m=round(L, 3), n_periodes=round(L / periode, 2),
                 prov={"geometrie": {"src": "gam", "ref": f"axe levé GAM {M.gam_refs(m['p'])[0]} : base (côté bordure), amplitude et période ajustées", "conf": "haute"},
                       "trait_m": {"src": "regle:marquages_geometrie.zigzag_bus", "ref": "2u, u = 0,06 (Verdun)", "conf": "moyenne"}})
        entites.append(e)
        devenir[m["id"]] = ("genere", eid, f"zigzag paramétrique (amplitude {amp:.2f}, période {periode:.2f})")
    return entites, devenir


def polygones_gardes(ms, classe, type_, prefixe, note, fleches=False, fantome=False):
    entites, devenir = [], {}
    for m in ms:
        if "marque en T" in (m["p"]["note"] or ""):
            i, prm, org, cap, polys = t_stationnement(m)
            eid = M.ident(prefixe, [m["id"]])
            e = dict(_base(m), id=eid, classe=classe, type="t_stationnement", glyphe=prm,
                     pose={"origine_local": org, "cap_deg": round(cap, 3)}, iou_v1=round(i, 3),
                     geom=("MultiPolygon", polys), contour_raster_v1=m["raster"],
                     prov={"geometrie": {"src": "regle:marquages_glyphes.t_stationnement",
                                         "ref": f"T de stationnement (traits 2u) ajusté sur la boîte v1, IoU {i:.2f}", "conf": "moyenne"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", eid, f"T de stationnement paramétrique (IoU {i:.2f})")
            continue
        polys, desc, methode, i = primitive(m, fleches, fantome)
        eid = M.ident(prefixe, [m["id"]])
        e = dict(_base(m), id=eid, classe=classe, type=type_,
                 geom=("Polygon" if len(polys) == 1 else "MultiPolygon", polys),
                 simplification=methode, primitive=desc, iou_v1=round(i, 3), contour_raster_v1=m["raster"],
                 prov={"geometrie": {"src": _src(m), "ref": f"{methode} ajusté sur le polygone v1 (IoU {i:.2f})",
                                     "conf": "faible" if desc["type"] == "contour_redresse" else "moyenne"}})
        if m["p"]["note"]:
            e["note_v1"] = m["p"]["note"][:160]
        entites.append(e)
        fate = "genere" if desc["type"] in ("rectangle", "rectangles", "ruban", "gabarit") else "garde_simplifie"
        devenir[m["id"]] = (fate, eid, note + f" ({methode}, IoU {i:.2f})")
    return entites, devenir


def _reunir(entites, devenir):
    """Fantômes dont les primitives se recouvrent : une entité (plus petit MQ), géométrie = toutes les primitives."""
    n = len(entites)
    par = list(range(n))

    def rac(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    bb = []
    for e in entites:
        P = np.vstack([r for poly in e["geom"][1] for r in poly])
        bb.append((*P.min(axis=0), *P.max(axis=0)))
    for i in range(n):
        for j in range(i + 1, n):
            A, B = bb[i], bb[j]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            pa, pb = entites[i]["geom"][1], entites[j]["geom"][1]
            P = np.vstack([r for poly in pa + pb for r in poly])
            x0, y0 = P.min(axis=0) - 0.02
            nx, ny = int((P[:, 0].max() - x0) / 0.02) + 3, int((P[:, 1].max() - y0) / 0.02) + 3
            if (M.raster_masque(pa, x0, y0, nx, ny, 0.02) & M.raster_masque(pb, x0, y0, nx, ny, 0.02)).sum() * 4e-4 > 0.005:
                par[rac(j)] = rac(i)
    groupes = collections.defaultdict(list)
    for i in range(n):
        groupes[rac(i)].append(entites[i])
    out = []
    for g in sorted(groupes.values(), key=lambda g: g[0]["id"]):
        if len(g) == 1:
            out.append(g[0])
            continue
        g = sorted(g, key=lambda e: e["id"])
        e = dict(g[0])
        e["lien_v1"] = sorted(i for x in g for i in x["lien_v1"])
        e["id"] = M.ident("MG", e["lien_v1"])
        e["geom"] = ("MultiPolygon", [poly for x in g for poly in x["geom"][1]])
        e["primitives"] = [dict(x["primitive"], mq=x["lien_v1"][0], simplification=x["simplification"]) for x in g]
        e.pop("primitive", None)
        e["simplification"] = "+".join(sorted({x["simplification"] for x in g}))
        e["couverture"] = M.mediane_ou([x["couverture"] for x in g])
        e["contour_raster_v1"] = any(x["contour_raster_v1"] for x in g)
        e["iou_v1"] = round(float(np.mean([x["iou_v1"] for x in g])), 3)
        e["prov"] = {"geometrie": {"src": g[0]["prov"]["geometrie"]["src"],
                                   "ref": f"{len(g)} empreintes v1 qui se recouvrent, réunies (une seule empreinte à la fabrication) : "
                                          + ", ".join(f"{x['lien_v1'][0]} {x['simplification']}" for x in g), "conf": "moyenne"}}
        for mq in e["lien_v1"]:
            fate, _, note = devenir[mq]
            devenir[mq] = (fate, e["id"], note + f" ; réunie dans {e['id']}")
        out.append(e)
    return out


def fantomes():
    ms = [m for m in M.v1() if m["p"]["type"] == "fantome"]
    e, d = polygones_gardes(ms, "fantome", "fantome", "MG", "empreinte effacée (fantôme)", fleches=True, fantome=True)
    return _reunir(e, d), d
