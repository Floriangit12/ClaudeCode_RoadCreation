"""Flèches et symboles : gabarits IISR posés (origine, cap), classés par IoU rastérisé contre les
polygones v1 ; triangles (dents de requin), chevrons, barres et points paramétriques ; symboles non
encore vectorisés (PMR, « 30 », « 50 ») en boîtes « a_vectoriser ».

Flèche (classe fleche) : gabarit ∈ {TD, TAD, TAG, TD_TAD, TD_TAG, RAB_D, RAB_G}, echelle (1 ; 0,5 pour
    les pistes cyclables, art. 118-1), pose {x, y (L93), cap_deg} (origine du gabarit : milieu du pied
    de la tige ; cap = sens de circulation de la voie), ancrage {route, voie, s, t} (point d'origine),
    iou_v1 et table de classement {gabarit: IoU}. Le cap suit la tangente de la voie (pas d'ajustement
    angulaire) ; la position (s, t) est ajustée par corrélation (FFT) des masques au cm.
"""
import collections
import math

import numpy as np

import marquages_commun as M
import marquages_glyphes as GL
import marquages_ortho as MO
from commun import projeter

FLECHES = ("TD", "TAD", "TAG", "TD_TAD", "TD_TAG", "RAB_D", "RAB_G")
DIR_V1 = {"tout_droit": "TD", "tout_droit_droite": "TD_TAD", "tout_droit_gauche": "TD_TAG", "gauche": "TAG",
          "droite": "TAD"}
XODR_SOUS_TYPE = {"tout_droit": "TD", "tout_droit_droite": "TD_TAD", "tout_droit_gauche": "TD_TAG", "gauche": "TAG",
                  "droite": "TAD"}
RES = 0.01


# --------------------------------------------------------------------------- localisation sur le réseau
class Localisateur:
    """Projection d'un point sur les voies du réseau (routes hors jonction d'abord)."""

    def __init__(self, reseau):
        import xodr_echantillonne as X
        self.X = X
        self.reseau = reseau
        self.refs = {}
        for rid, r in reseau.items():
            s = X.abscisses_section(0.0, r.longueur, 0.10)
            x, y, h = r.reference(s)
            self.refs[rid] = (s, np.c_[x, y], h)

    def voies(self, xy, types=("driving", "biking", "bus")):
        out = []
        for rid in sorted(self.reseau, key=int):
            s_, P, h_ = self.refs[rid]
            sig, d, cote = projeter(P, xy[None])
            s = float(np.interp(sig[0], np.r_[0.0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))], s_))
            if s <= 0.05 or s >= self.reseau[rid].longueur - 0.05:
                continue
            r = self.reseau[rid]
            x0, y0, h = r.reference(np.array([s]))
            n = np.array([-math.sin(h[0]), math.cos(h[0])])
            t = float((xy - np.array([x0[0], y0[0]])) @ n)
            sec = r.section(s)
            tb = r.t_bords(np.array([s]), sec)
            for v, t_ext in tb.items():
                if v == 0:
                    continue
                t_int = tb[v - 1 if v > 0 else v + 1][0]
                lo, hi = sorted((t_int, t_ext[0]))
                if lo - 1e-6 <= t <= hi + 1e-6 and sec.voies[v].type in types:
                    cap = h[0] if v < 0 else h[0] + math.pi
                    jonction = r.jonction != "-1"
                    out.append({"route": rid, "voie": v, "section_s": sec.s, "s": s, "t": t, "cap": cap,
                                "type": sec.voies[v].type, "jonction": jonction,
                                "ecart_centre": abs(t - 0.5 * (lo + hi))})
        out.sort(key=lambda o: (o["jonction"], o["ecart_centre"]))
        return out


# --------------------------------------------------------------------------- ajustement de gabarit
def _raster(polys, x0, y0, nx, ny):
    return M.raster_masque(polys, x0, y0, nx, ny, RES).astype(np.float64)


def ajuster_gabarit(m, nom, cap_deg, echelle=1.0, fenetre=(0.30, 0.60), echelle_x=1.0):
    """Meilleure position du gabarit `nom` au cap donné sur le polygone v1 : (origine locale, IoU)."""
    c = m["obb"]["c"]
    q = [[M.dans_repere(r, c, cap_deg) for r in poly] for poly in m["polys"]]
    g = [[r * echelle for r in poly] for poly in M.gabarit(nom, echelle_x)]
    gp = np.vstack([r for poly in g for r in poly])
    b0 = 0.5 * (gp.min(axis=0) + gp.max(axis=0))
    g = [[r - b0 for r in poly] for poly in g]
    allp = np.vstack([r for poly in q + g for r in poly])
    demi = np.abs(allp).max(axis=0) + np.array(fenetre) + 0.05
    nx, ny = int(2 ** math.ceil(math.log2(2 * demi[0] / RES))), int(2 ** math.ceil(math.log2(2 * demi[1] / RES)))
    x0, y0 = -nx * RES / 2, -ny * RES / 2
    A = _raster(q, x0, y0, nx, ny)
    B = _raster(g, x0, y0, nx, ny)
    C = np.fft.irfft2(np.fft.rfft2(A) * np.conj(np.fft.rfft2(B)), s=A.shape)
    wx, wy = int(fenetre[0] / RES), int(fenetre[1] / RES)
    rows = np.r_[np.arange(0, wy + 1), np.arange(ny - wy, ny)]
    cols = np.r_[np.arange(0, wx + 1), np.arange(nx - wx, nx)]
    sub = C[np.ix_(rows, cols)]
    iou_ = sub / (A.sum() + B.sum() - sub)
    i, j = np.unravel_index(int(np.argmax(iou_)), iou_.shape)
    dr, dc = rows[i], cols[j]
    dr = dr - ny if dr > ny // 2 else dr
    dc = dc - nx if dc > nx // 2 else dc
    d = np.array([dc * RES, -dr * RES])          # rangées vers le bas = y décroissant
    origine = M.poser((-b0 + d)[None], c, cap_deg)[0]
    return origine, float(iou_.max())


def iou_pose(m, nom, origine, cap_deg, echelle=1.0, echelle_x=1.0):
    placed = [[M.poser(r, origine, cap_deg, echelle) for r in poly] for poly in M.gabarit(nom, echelle_x)]
    return M.iou(m["polys"], placed, res=RES), placed


# --------------------------------------------------------------------------- flèches
def _meilleur(m, noms, caps, ech):
    """Meilleur (IoU, gabarit, cap, origine) sur une liste de gabarits et de caps."""
    best = None
    for cap in caps:
        for nom in noms:
            o, s_ = ajuster_gabarit(m, nom, cap, ech, fenetre=(0.30, 0.80))
            cle = (round(s_, 4), nom)
            if best is None or cle > best[0]:
                best = (cle, nom, cap % 360.0, o)
    return best[0][0], best[1], best[2], best[3]


def fleches(reseau, objets_xodr):
    loc = Localisateur(reseau)
    arrows = [m for m in M.v1() if m["p"]["type"] == "fleche"]
    xo = [o for o in objets_xodr if o["type"] == "roadMark" and o["sous_type"] not in ("stopLine",)]
    entites, devenir, table = [], {}, []
    balayage = np.arange(-15.0, 15.01, 1.5)
    for m in arrows:
        velo = m["p"]["groupe"] == "piste_chronovelo_fleches"
        ech = 0.5 if velo else 1.0
        types = ("biking",) if velo else ("driving", "bus")
        c = m["obb"]["c"]
        vs = [v for v in loc.voies(c, types=types) if not v["jonction"]]
        ox = min(xo, key=lambda o: float(np.hypot(*(o["xy"] - c)))) if xo else None
        lien_x = ox if ox is not None and float(np.hypot(*(ox["xy"] - c))) < 4.0 else None
        if vs:
            cap0, src_cap = math.degrees(vs[0]["cap"]) % 360.0, "voie"
        elif lien_x is not None:
            cap0, src_cap = math.degrees(lien_x["cap"]) % 360.0, "xodr_objet"
        else:
            cap0, src_cap = None, "axe_v1"
        # recherche à cap libre : diagnostic sur voie, pose ailleurs
        if cap0 is None:
            cu = M.cap_de(m["obb"]["u"])
            caps_libres = [cu + d for d in balayage] + [cu + 180.0 + d for d in balayage]
        else:
            caps_libres = [cap0 + d for d in balayage] + ([cap0 + 180.0 + d for d in balayage] if src_cap == "xodr_objet" else [])
        iou_l, nom_l, cap_l, o_l = _meilleur(m, FLECHES, caps_libres, ech)
        cap_ref = cap0 if src_cap == "voie" else cap_l
        scores = {}
        for nom in FLECHES:
            o, s_ = ajuster_gabarit(m, nom, cap_ref, ech, fenetre=(0.30, 0.80))
            scores[nom] = (s_, o, cap_ref)
        nom = max(scores, key=lambda k: (round(scores[k][0], 4), k))
        attendu = DIR_V1.get(m["p"]["direction"])
        if attendu and attendu != nom and scores[nom][0] - scores[attendu][0] < 0.03:
            nom = attendu
        s_best, o_best, cap = scores[nom]
        ex_ = 1.0
        # flèche visible en 2022 (conservée ou refaite à l'identique) : position recalée sur l'ortho PCRS (cap gardé)
        recal = None
        if m["p"]["etat"] in MO.ETATS_2022:
            r = MO.recaler(M.gabarit(nom, ex_), o_best, cap, echelle=(ech, ech))
            if r is not None and r["corr_max"] >= 0.5 and r["corr_max"] - r["corr_v2"] >= 0.02 and max(abs(r["dx"]), abs(r["dy"])) > 0.02:
                ax, ay = M.axes_cap(cap)
                o_best = o_best + r["dx"] * ax + r["dy"] * ay
                recal = r
            elif r is not None:
                recal = dict(r, applique=False)
        iou_exact, placed = iou_pose(m, nom, o_best, cap, ech, ex_)
        anc = None
        v0 = loc.voies(o_best, types=types)
        if v0:
            v = v0[0]
            anc = {"type": "xodr", "route": v["route"], "voie": v["voie"], "section_s": round(v["section_s"], 3),
                   "s": round(v["s"], 3), "t": round(v["t"], 3)}
        ids = [m["id"]]
        eid = M.ident("MF", ids)
        ref_pose = {"voie": "cap = tangente de la voie ; position ajustée (corrélation des masques au cm)",
                    "xodr_objet": "jonction : cap balayé (± 15°) autour de l'objet flèche du .xodr ; position ajustée",
                    "axe_v1": "hors voie : cap balayé (± 15°) autour de l'axe du polygone v1 ; position ajustée"}[src_cap]
        e = {"id": eid, "classe": "fleche", "type": "directionnelle" if nom.startswith("T") else "rabattement",
             "couleur": m["p"]["couleur"], "gabarit": nom, "echelle": ech,
             "pose": {"origine_local": o_best, "cap_deg": round(cap % 360.0, 3), "cap_source": src_cap},
             "geom": ("MultiPolygon" if len(placed) > 1 else "Polygon", placed),
             "ancrage": anc or {"type": "pose"}, "iou_v1": round(iou_exact, 3),
             "classement": {k: round(v[0], 3) for k, v in sorted(scores.items())},
             "diagnostic_cap_libre": {"gabarit": nom_l, "iou": round(iou_l, 3), "ecart_cap_deg": round(M.ecart_cap(cap_l, cap), 2)},
             "direction_v1": m["p"]["direction"], "usure": m["p"]["usure"], "couverture": m["p"]["couverture"],
             "etat": m["p"]["etat"], "groupe": m["p"]["groupe"], "branche": m["p"]["branche"], "lien_v1": ids,
             "prov": {"geometrie": {"src": "regle:marquages_geometrie.gabarits." + nom, "ref": "gabarit IISR posé (origine, cap) : géométrie dérivée", "conf": "haute"},
                      "gabarit": {"src": "regle:marquages_geometrie.gabarits." + nom,
                                  "ref": f"IoU {iou_exact:.2f} contre le polygone v1 ({m['p']['source'][:60]})",
                                  "conf": "haute" if iou_exact >= 0.75 else ("moyenne" if iou_exact >= 0.55 else "faible")},
                      "pose": {"src": "xodr" if src_cap != "axe_v1" else _src(m), "ref": ref_pose,
                               "conf": "haute" if src_cap == "voie" else "moyenne"}}}
        if recal is not None:
            e["recalage_ortho"] = {k: recal[k] for k in ("dx", "dy", "corr_v2", "corr_max")}
            if recal.get("applique", True):
                e["prov"]["pose"] = {"src": "ortho2022", "ref": f"{ref_pose} ; recalée sur l'ortho PCRS 5 cm 2022 (corrélation {recal['corr_v2']:.2f} -> "
                                                               f"{recal['corr_max']:.2f}, latéral {recal['dx']:+.2f} m, longitudinal {recal['dy']:+.2f} m)",
                                     "conf": "haute"}
        if lien_x is not None:
            e["xodr_objet"] = lien_x["id"]
            e["xodr_sous_type"] = lien_x["sous_type"]
        entites.append(e)
        devenir[m["id"]] = ("genere", eid, f"gabarit {nom} (IoU {iou_exact:.2f})")
        table.append({"mq": m["id"], "groupe": m["p"]["groupe"], "direction_v1": m["p"]["direction"], "raster": m["raster"],
                      "gabarit": nom, "iou": round(iou_exact, 3), "cap_source": src_cap,
                      "scores": {k: round(v[0], 3) for k, v in sorted(scores.items())},
                      "cap_libre": [nom_l, round(iou_l, 3), round(M.ecart_cap(cap_l, cap), 2)],
                      "xodr": [lien_x["id"], lien_x["sous_type"], XODR_SOUS_TYPE.get(lien_x["sous_type"])] if lien_x is not None else None,
                      "voie": [anc["route"], anc["voie"]] if anc else None})
    lies = {e.get("xodr_objet") for e in entites}
    orphelins = [o["id"] for o in xo if o["id"] not in lies]
    return entites, devenir, table, orphelins


def controle_trois_par_voie(entites):
    """Contrôle seulement (pas de génération) : nombre de flèches directionnelles par (route, voie)."""
    c = collections.Counter()
    for e in entites:
        a = e["ancrage"]
        if a.get("type") == "xodr" and e["type"] == "directionnelle" and e["echelle"] == 1.0:
            c[(a["route"], a["voie"])] += 1
    return {f"{r}/{v}": n for (r, v), n in sorted(c.items(), key=lambda kv: (int(kv[0][0]), kv[0][1]))}


def _src(m):
    s = m["p"]["source"]
    return "gam" if s.startswith("GAM") else ("plan2025" if s.startswith("plan") else "ortho2022")


# --------------------------------------------------------------------------- symboles
def _velo(m, loc=None):
    """Gabarit VELO (IISR D1 : figure debout, +y = sens de circulation) centré sur le pictogramme v1 ;
    cap : bloc GAM SYMBOLE_VELO (rotation + 90° : +y du bloc le long du cadre) à moins de 1 m, sinon voie
    cyclable, sinon axe du pictogramme orienté par IoU. Le pictogramme du site (vélo couché le long de
    la voie, roues rondes) diffère du D1 : l'IoU reste bas par construction."""
    c = m["obb"]["c"]
    bloc = [b for b in M.gam_pct() if b["bloc"] == "SYMBOLE_VELO" and float(np.hypot(*(b["xy"] - c))) < 1.0]
    src = None
    if bloc:
        cap, src = (float(bloc[0]["rotation"]) + 90.0) % 360.0, "gam"      # +y du bloc = cadre du vélo
    elif loc is not None:
        vs = loc.voies(c, types=("biking",))
        if vs:
            cap, src = math.degrees(vs[0]["cap"]) % 360.0, "xodr"
    if src is None:
        caps = [M.cap_de(m["obb"]["u"]), (M.cap_de(m["obb"]["u"]) + 180.0) % 360.0]
        cap = max(caps, key=lambda k: ajuster_gabarit(m, "VELO", k, 1.0, fenetre=(0.10, 0.10))[1])
        src = "axe_v1"
    g = M.spec()["gabarits"]["VELO"]["boite"]
    centre = np.array([0.5 * (g["x"][0] + g["x"][1]), 0.5 * (g["y"][0] + g["y"][1])])
    o = M.poser((-centre)[None], c, cap)[0]
    i, placed = iou_pose(m, "VELO", o, cap)
    return o, cap, i, placed, src


def _triangle(r):
    """Triangle isocèle : (base_m, hauteur_m, milieu de base, cap base -> pointe)."""
    L = [float(np.hypot(*(r[(k + 1) % 3] - r[k]))) for k in range(3)]
    k = int(np.argmin(L))
    a, b, p = r[k], r[(k + 1) % 3], r[(k + 2) % 3]
    mb = 0.5 * (a + b)
    return L[k], float(np.hypot(*(p - mb))), mb, M.cap_de(p - mb)


def _chevron(r):
    """Chevron (V à trait d'épaisseur constante, 6 sommets) : pointe extérieure, cap (de l'intérieur
    vers la pointe), longueur des branches, ouverture, largeur du trait."""
    n = len(r)
    L = np.hypot(*np.diff(np.vstack([r, r[:1]]), axis=0).T)
    somme = np.array([L[k - 1] + L[k] for k in range(n)])
    k = int(np.argmax(somme))
    pa, pb, pc = r[k - 1], r[k], r[(k + 1) % n]
    d1, d2 = pa - pb, pc - pb
    l1, l2 = float(np.hypot(*d1)), float(np.hypot(*d2))
    u1, u2 = d1 / l1, d2 / l2
    ouv = math.degrees(math.acos(max(-1.0, min(1.0, float(u1 @ u2)))))
    bis = u1 + u2
    cap = M.cap_de(-bis)
    courts = sorted(L)[:2]
    return {"pointe": pb, "cap_deg": cap, "branche_m": 0.5 * (l1 + l2), "ouverture_deg": ouv, "trait_m": float(np.mean(courts))}


def _glyphe(m, base, loc):
    """PMR (ISO 7001 stylisé) ou rappel de vitesse « 30 » / « 50 » dans une ellipse, construits par primitives
    (marquages_glyphes) ; orientation : voie roulable (texte) puis IoU contre le polygone v1."""
    p = m["p"]
    o = m["obb"]
    cu = M.cap_de(o["u"])
    if p["type"] == "texte":
        texte = str(p["sous_type"])
        params = {"nom": "texte_ellipse", "texte": texte, "longueur_m": round(o["L"], 3), "largeur_m": round(o["W"], 3), "anneau_m": 0.10}
        caps = [cu, (cu + 180.0) % 360.0]
        vs = loc.voies(o["c"]) if loc else []
        if vs:
            cv = math.degrees(vs[0]["cap"]) % 360.0
            caps.sort(key=lambda k: M.ecart_cap(k, cv))
            caps = caps[:1]
            src_cap = "voie"
        else:
            src_cap = "axe_v1"
        variantes = [(k, params) for k in caps]
        nom, typ = f"TEXTE_{texte}", "texte"
    else:
        variantes = []
        for k in (cu, cu + 90.0, cu + 180.0, cu + 270.0):
            le_long_y = abs(math.cos(math.radians(k - cu))) > 0.5        # +y du pictogramme le long de u
            dy, dx = (o["L"], o["W"]) if le_long_y else (o["W"], o["L"])
            h = round(min(dy, dx * GL.PMR_BOITE[1] / GL.PMR_BOITE[0]), 3)
            for mir in (False, True):
                variantes.append((k % 360.0, {"nom": "pmr", "hauteur_m": h, "miroir": mir}))
        src_cap, nom, typ = "axe_v1", "PMR", "pmr"
    best = None
    for k, prm in variantes:
        placed = [[M.poser(r, o["c"], k) for r in poly] for poly in construire_glyphe(prm)]
        i = M.iou(m["polys"], placed, res=0.01)
        if best is None or i > best[0] + 1e-9:
            best = (i, k, prm, placed)
    i, cap, prm, placed = best
    e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type=typ, gabarit=nom, glyphe=prm,
             pose={"origine_local": o["c"], "cap_deg": round(cap % 360.0, 3), "cap_source": src_cap}, iou_v1=round(i, 3),
             geom=("MultiPolygon", placed),
             prov={"geometrie": {"src": "regle:marquages_glyphes." + prm["nom"], "ref": ("pictogramme ISO 7001 stylisé construit par primitives (disque, traits à bouts ronds, anneau ouvert)"
                                                                               if typ == "pmr" else f"« {prm['texte']} » : chiffres en traits et arcs d'ellipse dans un anneau elliptique, anamorphosés le long de la lecture")
                                 + " ; posé (origine, cap)", "conf": "moyenne"},
                   "pose": {"src": _src(m), "ref": f"centre de la boîte v1 ; cap : {src_cap}, puis meilleure IoU ({i:.2f}) contre le polygone v1", "conf": "moyenne"}})
    return e, f"{nom} construit par primitives (IoU {i:.2f})"


def construire_glyphe(prm):
    """Polygones (repère du gabarit, origine au centre) d'un glyphe décrit par ses paramètres."""
    if prm["nom"] == "pmr":
        return GL.pmr(prm["hauteur_m"], prm.get("miroir", False))
    if prm["nom"] == "texte_ellipse":
        return GL.texte_ellipse(prm["texte"], prm["longueur_m"], prm["largeur_m"], prm.get("anneau_m", 0.10))
    if prm["nom"] == "t_stationnement":
        return GL.t_stationnement(prm["barre_m"], prm["jambe_m"], prm["trait_m"])
    raise ValueError(prm["nom"])


def symboles(reseau=None):
    tous = M.v1()
    loc = Localisateur(reseau) if reseau else None
    entites, devenir = [], {}
    pct = M.gam_pct()
    for m in tous:
        p = m["p"]
        t, g = p["type"], p["groupe"]
        base = {"couleur": p["couleur"], "usure": p["usure"], "couverture": p["couverture"], "etat": p["etat"],
                "groupe": g, "branche": p["branche"], "lien_v1": [m["id"]]}
        if t == "symbole_velo":
            o, cap, i, placed, src_cap = _velo(m, loc)
            e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type="velo", gabarit="VELO", echelle=1.0,
                     pose={"origine_local": o, "cap_deg": round(cap, 3)}, iou_v1=round(i, 3),
                     geom=("MultiPolygon", placed),
                     prov={"geometrie": {"src": "regle:marquages_geometrie.gabarits.VELO", "ref": "figurine D1 posée (origine, cap) : géométrie dérivée", "conf": "haute"},
                           "gabarit": {"src": "regle:marquages_geometrie.gabarits.VELO", "ref": f"IoU {i:.2f} contre le pictogramme v1 (1,32 x 0,69 du site)", "conf": "moyenne"},
                           "pose": {"src": {"gam": "gam", "xodr": "xodr"}.get(src_cap, _src(m)),
                                    "ref": f"centre du pictogramme v1 ; cap : {src_cap} (bloc SYMBOLE_VELO, voie cyclable ou axe v1)", "conf": "moyenne"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], f"gabarit VELO (IoU {i:.2f})")
        elif t == "symbole" and g in ("plateau_piste_dents_de_requin", "saules_blancs_dents_de_requin"):
            b, h, mb, cap = _triangle(m["r"])
            e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type="dent_requin",
                     triangle={"base_m": round(b, 3), "hauteur_m": round(h, 3)},
                     pose={"origine_local": mb, "cap_deg": round(cap, 3)},
                     geom=("Polygon", [[m["r"]]]),
                     prov={"geometrie": {"src": _src(m), "ref": "triangle isocèle ajusté sur les 3 sommets v1 (origine = milieu de la base, cap vers la pointe)", "conf": "moyenne"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], "triangle paramétrique")
        elif t == "chevrons":
            c = _chevron(m["r"])
            e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type="chevron",
                     chevron={"branche_m": round(c["branche_m"], 3), "ouverture_deg": round(c["ouverture_deg"], 2), "trait_m": round(c["trait_m"], 3)},
                     pose={"origine_local": c["pointe"], "cap_deg": round(c["cap_deg"], 3)}, direction_v1=p["direction"],
                     geom=("Polygon", [[m["r"]]]),
                     prov={"geometrie": {"src": "gam", "ref": "V ajusté sur les 6 sommets du levé (pointe extérieure, branches, trait)", "conf": "haute"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], "chevron paramétrique")
        elif t == "symbole" and g == "piste_chronovelo_barres":
            o = m["obb"]
            e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type="barre",
                     rectangle={"longueur_m": round(o["L"], 3), "largeur_m": round(max(o["W"], 0.10), 3)},
                     pose={"origine_local": o["c"], "cap_deg": round(M.cap_de(o["u"]), 3)},
                     geom=("Polygon", [[o["coins"]]]),
                     prov={"geometrie": {"src": "plan2025", "ref": "rectangle orienté minimal de la barre du plan (largeur ≥ 0,10)", "conf": "moyenne"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], "barre rectangulaire")
        elif t == "ligne_discontinue" and g == "piste_chronovelo_axe":
            o = m["obb"]
            e = dict(base, id=M.ident("MS", [m["id"]]), classe="symbole", type="point",
                     disque={"diametre_m": round(0.5 * (o["L"] + o["W"]), 3)},
                     pose={"origine_local": o["c"], "cap_deg": 0.0},
                     geom=("Polygon", [[o["c"] + 0.5 * 0.5 * (o["L"] + o["W"]) * np.c_[np.cos(np.linspace(0, 2 * np.pi, 32, endpoint=False)), np.sin(np.linspace(0, 2 * np.pi, 32, endpoint=False))]]]),
                     prov={"geometrie": {"src": "plan2025", "ref": "disque de l'axe de piste (centre et diamètre du point du plan)", "conf": "moyenne"}})
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], "point d'axe (disque)")
        elif (t == "symbole" and g == "stationnement_PMR") or t == "texte" or (t == "symbole" and "PMR" in (p["note"] or "")):
            e, note = _glyphe(m, base, loc)
            entites.append(e)
            devenir[m["id"]] = ("genere", e["id"], note)
    return entites, devenir
