"""Entités paramétriques tirées du levé GAM 2026 (source de rang 1, FUS-SRC-001), après classement
(marquages_gam_classer). La forme posée est toujours normative (FUS-SNP-004) ; la pose et le type viennent du levé.

- zébras (MP-5kkk) : bandes rectangulaires levées côte à côte (parallèles à ± 6°, pas 0,8-1,7 m) -> axe [A, B],
  bande 0,50 m, intervalle mesuré borné à [0,50 ; 0,80] (MQ-PP-004), longueur médiane des bandes entières, coupures
  aux emplacements vides ; bande tronquée par une bordure ou un îlot : polygone levé gardé (zone bande_isolee,
  simplifié à 1 cm) ;
- hachures (MZ-5kkk) : bandes obliques (parallélogrammes de 0,5 m) hors zébras et bords voisins -> contour convexe,
  cap et pas mesurés (pas ramené à 1,85 m si l'écart est ≤ 10 %, regle:marquages_geometrie.hachures) ;
- flèches (MF-5kkk contour, MF-55ii bloc) : gabarit IISR ajusté (IoU ≥ 0,55) ou bloc SYMBOLE_FLECHE ; type
  rapproché des manœuvres 2026 plus loin (FUS-CON-005) ;
- figurines vélo (MS-55ii bloc, MS-5kkk pictogramme dessiné), PMR (MS-55ii), chevrons des traversées cyclables
  (MS-5kkk, trait 0,12, MQ-CYC-008), dents de plateau (MS-5kkk, triangles isocèles normatifs, MQ-RAL-001),
  barres et carrés (MS-5kkk) ;
- zigzags d'arrêt de bus (MZ-5kkk, jaunes 2u, MQ-BUS-005) ;
- lignes (ML-5kkk) : axes levés (paires de bords -> médiane + largeur levée ramenée à {0,10 ; 0,12 ; 0,15 ;
  0,18 ; 0,25 ; 0,30} à ± 2 cm), tirets levés alignés -> ligne discontinue (motif IISR, detection_lignes.modeliser) ;
  ancrage OpenDRIVE (bord de voie + t_off) si le levé suit le bord à 4 cm près (p95), sinon axe levé adouci ;
- pictogrammes hors bibliothèque (piéton dessiné, flèches de guidage coudées du carrefour) : polygones levés
  simplifiés à 1 cm, drapeau atypique, confiance faible (FUS-SNP-004).
Identifiants : 5000 + plus petit indice de polyligne GAM ; 5500 + indice du bloc.
"""
import collections
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_lignes as DL  # noqa: E402
import marquages_commun as M  # noqa: E402
import marquages_gam_classer as GC  # noqa: E402
import marquages_glyphes as GL  # noqa: E402
import marquages_lignes as LG  # noqa: E402
import marquages_sources as S  # noqa: E402
from commun import abscisses, densifier, point_a, projeter  # noqa: E402

LARGEURS = (0.10, 0.12, 0.15, 0.18, 0.25, 0.30)          # FUS-SNP-004
BRANCHE_ROUTE = {"1": "verdun_sw", "2": "verdun_sw", "3": "verdun_ne", "4": "verdun_ne", "5": "reviree", "6": "vercors"}


def ident(prefixe, n):
    return f"{prefixe}-{int(n):04d}"


def etat_entite(Q):
    e = S.etat_majoritaire(np.atleast_2d(Q))
    return e


def aspect(etat):
    """(usure, couverture) a priori selon l'état de zone (marques 2025 neuves : usure 0, regle neuf_2025_u0)."""
    if etat in ("neuf_2025", "construit_2023_2024"):
        return "0", 0.97
    if etat == "refait_2025_identique":
        return "0", 0.97
    return "1", 0.88


def branche(loc, xy):
    vs = loc.voies(np.asarray(xy, float), types=("driving", "biking", "bus", "parking", "median", "border", "curb",
                                                   "sidewalk", "none"))
    if not vs:
        return "hors_reseau"
    r = vs[0]["route"]
    return BRANCHE_ROUTE.get(r, "centre")


def base(eid, classe, type_, Q, gam, ref, loc, couleur="blanc"):
    etat = etat_entite(Q)
    us, cv = aspect(etat)
    return {"id": eid, "classe": classe, "type": type_, "couleur": couleur, "usure": us, "couverture": cv,
            "etat": "neuf_2025" if etat == "construit_2023_2024" else etat, "etat_zone": etat,
            "groupe": f"gam_{classe}", "branche": branche(loc, np.atleast_2d(Q).mean(axis=0)), "lien_v1": [],
            "src": "gam", "gam": sorted(int(k) for k in gam),
            "sources": [{"src": "gam", "ref": ref, "S": round(S.score("gam", 1.0, etat), 3)}],
            "prov": {"geometrie": {"src": "gam", "ref": ref, "conf": "haute"}}}


# --------------------------------------------------------------------------- zébras et hachures
def _bandes(C):
    return [a for a in C["anneaux"] if a["nature"] in ("bande", "bande_oblique")]


def grouper_bandes(bandes):
    """Bandes côte à côte (parallèles à ± 6°, voisines à 0,7-1,8 m le long de la normale, chevauchement en long) ->
    groupes (listes d'indices)."""
    n = len(bandes)
    par = list(range(n))

    def r(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(n):
        oi = bandes[i]["obb"]
        for j in range(i + 1, n):
            oj = bandes[j]["obb"]
            if abs(float(oi["u"] @ oj["u"])) < math.cos(math.radians(6.0)):
                continue
            d = oj["c"] - oi["c"]
            nn = np.array([-oi["u"][1], oi["u"][0]])
            if 0.7 <= abs(float(d @ nn)) <= 1.8 and abs(float(d @ oi["u"])) <= 0.6 * max(oi["L"], oj["L"]):
                par[r(j)] = r(i)
    g = collections.defaultdict(list)
    for i in range(n):
        g[r(i)].append(i)
    return sorted(g.values(), key=lambda x: min(bandes[i]["gam"][0] for i in x))


def zebras_hachures(C, loc):
    bandes = _bandes(C)
    out, utilises = [], set()
    for grp in grouper_bandes(bandes):
        bs = [bandes[i] for i in grp]
        rect = [b for b in bs if b["nature"] == "bande"]
        gam = sorted(k for b in bs for k in b["gam"])
        if len(rect) >= 2:
            out += _zebra(bs, rect, gam, loc)
            utilises |= set(gam)
    return out, utilises


def _zebra(bs, rect, gam, loc):
    u = rect[0]["obb"]["u"]
    u = np.mean([b["obb"]["u"] * (1 if float(b["obb"]["u"] @ u) >= 0 else -1) for b in rect], axis=0)
    u /= np.hypot(*u)
    if u[0] < 0 or (abs(u[0]) < 1e-9 and u[1] < 0):
        u = -u
    nrm = np.array([-u[1], u[0]])
    Lmed = float(np.median([b["obb"]["L"] for b in rect]))
    pos = np.array([float(b["obb"]["c"] @ nrm) for b in bs])
    ordre = np.argsort(pos, kind="stable")
    bs = [bs[i] for i in ordre]
    pos = pos[ordre]
    d = np.diff(pos)
    pas_mes = float(np.median(d[d < 1.6])) if (d < 1.6).any() else float(np.median(d))
    vide = min(0.80, max(0.50, pas_mes - 0.50))                  # FUS-SNP-004 / MQ-PP-004
    pas = 0.50 + vide
    k = np.round((pos - pos[0]) / pas_mes).astype(int)
    entiers = [b for b in bs if b["nature"] == "bande" and b["obb"]["L"] >= 0.85 * Lmed]
    lon = float(np.median([float(b["obb"]["c"] @ u) for b in entiers])) if entiers else float(np.median([float(b["obb"]["c"] @ u) for b in bs]))
    # positions des emplacements sur l'axe (normale), recalées au moindre carré sur les bandes entières
    p0 = float(np.median([pos[i] - k[i] * pas for i in range(len(bs)) if bs[i] in entiers])) if entiers else float(pos[0])
    A = u * lon + nrm * p0
    nb_empl = int(k.max()) + 1
    B = A + nrm * pas * (nb_empl - 1)
    presents = {int(k[i]) for i in range(len(bs)) if bs[i] in entiers}
    coupures = [i for i in range(nb_empl) if i not in presents]
    res = [abs(pos[i] - (p0 + k[i] * pas)) for i in range(len(bs)) if bs[i] in entiers]
    eid = ident("MP", 5000 + gam[0])
    e = base(eid, "passage", "zebra", np.vstack([A, B]), gam, f"bandes levées GAM {','.join(map(str, gam))} : "
             f"{len(entiers)} bandes entières, pas mesuré {pas_mes:.3f} m", loc)
    e.update({"geom": ("LineString", np.vstack([A, B])), "largeur_bande_m": 0.5, "intervalle_m": round(vide, 3),
              "pas_axe_m": round(pas, 3), "longueur_bande_m": round(Lmed, 3), "cap_bandes_deg": round(M.cap_de(u), 3),
              "nb_bandes": len(presents), "nb_emplacements": nb_empl, "coupures": coupures,
              "mesures": {"pas_leve_m": round(pas_mes, 3), "residu_bandes_max_m": round(max(res), 3) if res else None,
                          "n_bandes_levees": len(bs)}})
    e["prov"]["parametres"] = {"src": "regle:regles_conception.MQ-PP-004", "ref": "bande 0,50 ; intervalle mesuré borné à "
                               "[0,50 ; 0,80] (FUS-SNP-004)", "conf": "haute"}
    e["regles"] = ["FUS-SNP-004", "MQ-PP-004"]
    out = [e]
    # bandes tronquées (au droit d'une bordure ou d'un îlot) : polygone levé simplifié (vectoriel, sans marche)
    for b in bs:
        if b in entiers:
            continue
        r = M.douglas_peucker(np.vstack([b["anneau"], b["anneau"][:1]]), 0.01)[:-1]
        z = base(ident("MZ", 5000 + b["gam"][0]), "zone", "bande_isolee", r, b["gam"],
                 f"bande de zébra tronquée levée GAM {','.join(map(str, b['gam']))} ({b['obb']['L']:.2f} x {b['obb']['W']:.2f} m)", loc)
        z.update({"geom": ("Polygon", [[r]]), "passage": eid, "atypique": True, "regles": ["FUS-SNP-004"]})
        out.append(z)
    return out


def hachures(C, loc, utilises):
    """Groupes de bandes obliques hors zébras (+ chaînes voisines à moins de 1,5 m) -> zones hachurées."""
    bandes = [a for a in C["anneaux"] if a["nature"] in ("bande_oblique", "atypique") and not set(a["gam"]) & utilises
              and 0.35 <= a["obb"]["W"] <= 0.65 and a["obb"]["L"] >= 1.0]
    # bandes ouvertes en U (trois côtés levés) : chaîne de 4 sommets dans un rectangle de 0,4-0,6 m de large
    for c in C["chaines"]:
        if c["nature"] == "axe" and c["n_sommets"] == 4 and not set(c["gam"]) & utilises:
            o = M.rect_min(c["P"])
            if 0.4 <= o["W"] <= 0.62 and o["L"] >= 1.0:
                bandes.append({"gam": c["gam"], "anneau": c["P"], "obb": o, "nature": "bande_ouverte"})
    chaines = [c for c in C["chaines"] if c["nature"] in ("axe", "segment") and c["longueur_m"] < 26.0]
    out, pris = [], set()
    groupes = []
    for b in bandes:
        for g in groupes:
            if any(float(np.min(np.hypot(*(b["anneau"][:, None] - x["anneau"][None]).transpose(2, 0, 1)))) < 2.5 for x in g):
                g.append(b)
                break
        else:
            groupes.append([b])
    for g in groupes:
        if len(g) < 2:
            continue
        pts = [x["anneau"] for x in g]
        gam = sorted(k for x in g for k in x["gam"])
        for c in chaines:
            dmin = min(float(np.min(np.hypot(*(c["P"][:, None] - p[None]).transpose(2, 0, 1)))) for p in pts)
            if dmin < 1.5 and not set(c["gam"]) & pris and not set(c["gam"]) & set(gam):
                pts.append(c["P"])
                gam += c["gam"]
                pris |= set(c["gam"])
        gam = sorted(set(gam))
        H = M.enveloppe_convexe(np.vstack(pts))
        longues = [x for x in g if x["obb"]["L"] >= 2.5 * x["obb"]["W"]] or g
        u0 = longues[0]["obb"]["u"]
        U = np.array([x["obb"]["u"] * (1 if float(x["obb"]["u"] @ u0) >= 0 else -1) for x in longues])
        u = U.mean(axis=0)
        u /= np.hypot(*u)
        nrm = np.array([-u[1], u[0]])
        pos = np.sort([float(x["obb"]["c"] @ nrm) for x in longues])
        dd = np.diff(pos)
        dd = dd[dd > 0.6]
        pas_mes = float(np.median(dd)) if len(dd) else 1.85
        pas = 1.85 if (abs(pas_mes - 1.85) <= 0.185 or not 0.8 <= pas_mes <= 4.0) else round(pas_mes, 3)
        e = base(ident("MZ", 5000 + gam[0]), "zone", "hachures", H, gam,
                 f"bandes obliques levées GAM {','.join(map(str, gam))} : pas mesuré {pas_mes:.2f} m", loc)
        e.update({"geom": ("Polygon", [[H]]), "bande_m": 0.5, "pas_m": pas, "cap_bandes_deg": round(M.cap_de(u), 3),
                  "origine_bandes_local": longues[0]["obb"]["c"], "contour_peint": False,
                  "mesures": {"pas_leve_m": round(pas_mes, 3), "n_bandes_levees": len(g)}, "regles": ["FUS-SNP-004"]})
        e["prov"]["pas_m"] = {"src": "regle:marquages_geometrie.hachures", "ref": "pas perpendiculaire 1,85 m (± 10 %) sinon mesuré",
                              "conf": "moyenne"}
        out.append(e)
        utilises |= set(gam)
    return out


# --------------------------------------------------------------------------- flèches, symboles
def fleches(C, loc):
    out = []
    for a in C["anneaux"]:
        if a["nature"] != "fleche":
            continue
        f = a["fleche"]
        eid = ident("MF", 5000 + a["gam"][0])
        e = base(eid, "fleche", "rabattement" if f["gabarit"].startswith("RAB") else "directionnelle", f["origine"],
                 a["gam"], f"contour levé GAM {','.join(map(str, a['gam']))} ajusté au gabarit IISR {f['gabarit']} "
                 f"(IoU {f['iou']:.2f}, second {f.get('second')})", loc)
        e.update({"gabarit": f["gabarit"], "echelle": f["echelle"],
                  "pose": {"origine_local": f["origine"], "cap_deg": round(f["cap_deg"], 3), "cap_source": "gam"},
                  "iou_reference": round(f["iou"], 3), "regles": ["FUS-SNP-004"]})
        if f["iou"] < 0.7:
            e["note_gabarit"] = ("IoU < 0,70 : gabarit GAM plus étroit que l'IISR ; gabarit IISR posé (décision utilisateur "
                                 "n° 10 : flèches IISR sauf preuve photo contraire)")
            e["prov"]["geometrie"]["conf"] = "moyenne"
        out.append(e)
    blocs = [b for b in C["blocs"] if b.get("nature") == "fleche"]
    vus = {}
    for b in blocs:
        cle = (round(float(b["xy"][0]), 2), round(float(b["xy"][1]), 2))
        vus.setdefault(cle, []).append(b)
    for cle in sorted(vus):
        bs = vus[cle]
        vs = loc.voies(bs[0]["xy"])
        cap_v = math.degrees(vs[0]["cap"]) % 360.0 if vs else None
        b = min(bs, key=lambda x: (S.angle_diff(x["cap_deg"], cap_v) if cap_v is not None else 0.0, x["gam_pct"]))
        e = base(ident("MF", 5500 + b["gam_pct"]), "fleche", "directionnelle", b["xy"], [], f"bloc GAM {b['bloc']} "
                 f"(n° {b['gam_pct']}, rotation {b['rotation']:.2f}°)", loc)
        e["gam_pct"] = sorted(x["gam_pct"] for x in bs)
        e.update({"gabarit": b["gabarit"], "echelle": 1.0,
                  "pose": {"origine_local": b["xy"], "cap_deg": round(b["cap_deg"], 3), "cap_source": "gam"},
                  "regles": ["FUS-SNP-004"]})
        if len(bs) > 1:
            # insertion double au même point : le bloc et son symétrique (le levé n'a pas de bloc DROIT_DROITE) -> gabarit
            # symétrique (TD_TAG <-> TD_TAD, TAG <-> TAD) ; rapproché des manœuvres 2026 plus loin (FUS-CON-005)
            rots = ", ".join("%.1f" % x["rotation"] for x in bs)
            sym = {"TD_TAG": "TD_TAD", "TD_TAD": "TD_TAG", "TAG": "TAD", "TAD": "TAG"}.get(e["gabarit"], e["gabarit"])
            e["note_gabarit"] = (f"{len(bs)} insertions du bloc au même point (rotations {rots}°) : bloc symétrique, gabarit "
                                 f"{e['gabarit']} -> {sym} ; cap le plus proche de la voie retenu")
            e["gabarit"] = sym
            e["prov"]["gabarit"] = {"src": "gam", "ref": "bloc inséré deux fois (symétrique)", "conf": "moyenne"}
        out.append(e)
    return out


def _sens_voie(loc, xy, cap, types=("biking", "driving", "bus")):
    vs = loc.voies(np.asarray(xy, float), types=types)
    if not vs:
        return cap, "gam"
    cv = math.degrees(vs[0]["cap"]) % 360.0
    return (cap if S.angle_diff(cap, cv) <= 90.0 else (cap + 180.0) % 360.0), "voie"


def symboles(C, loc, utilises=frozenset()):
    out = []
    for b in C["blocs"]:
        nat = b.get("nature")
        if nat == "velo":
            e_ = float(b.get("echelle", 1.0))
            ex, ey = M.axes_cap(b["cap_deg"])
            o = b["xy"] - ey * 0.64 * e_
            e = base(ident("MS", 5500 + b["gam_pct"]), "symbole", "velo", b["xy"], [], f"bloc GAM SYMBOLE_VELO "
                     f"(n° {b['gam_pct']}, rotation {b['rotation']:.2f}° ; point = centre de la figurine)", loc)
            e.update({"gabarit": "VELO", "echelle": 1.0 if e_ > 0.75 else 0.5,
                      "pose": {"origine_local": o, "cap_deg": round(b["cap_deg"], 3), "cap_source": "gam"}, "regles": ["FUS-SNP-004"]})
            out.append(e)
        elif nat == "pmr":
            e_ = float(b.get("echelle", 1.0))
            prm = {"nom": "pmr", "hauteur_m": round(GC.PMR_HAUTEUR_ECHELLE_1 * e_, 3), "miroir": False}
            e = base(ident("MS", 5500 + b["gam_pct"]), "symbole", "pmr", b["xy"], [], f"bloc GAM SYMBOLE_PMR "
                     f"(n° {b['gam_pct']}, échelle {e_})", loc)
            e.update({"gabarit": "PMR", "glyphe": prm,
                      "pose": {"origine_local": b["xy"], "cap_deg": round(b["cap_deg"], 3), "cap_source": "gam"}, "regles": ["FUS-SNP-004"]})
            out.append(e)
    for p in C["pictos"]:
        o_ = p["obb"]
        if p["nature"] == "velo":
            cap, srcc = _sens_voie(loc, o_["c"], M.cap_de(p["axe_u"]))
            ex, ey = M.axes_cap(cap)
            e = base(ident("MS", 5000 + p["gam"][0]), "symbole", "velo", o_["c"], p["gam"],
                     f"pictogramme vélo dessiné GAM ({len(p['gam'])} polylignes, {o_['L']:.2f} m) : figurine IISR D1 posée", loc)
            e.update({"gabarit": "VELO", "echelle": 1.0,
                      "pose": {"origine_local": o_["c"] - ey * 0.64, "cap_deg": round(cap, 3), "cap_source": srcc},
                      "regles": ["FUS-SNP-004"]})
            out.append(e)
        else:
            polys = [[M.douglas_peucker(np.vstack([r, r[:1]]), 0.01)[:-1]] for r in p["anneaux"] if len(r) >= 3]
            if not polys:
                continue
            e = base(ident("MZ", 5000 + p["gam"][0]), "zone", "divers", o_["c"], p["gam"],
                     f"pictogramme {p['nature']} dessiné GAM (hors bibliothèque IISR) : polygones levés simplifiés à 1 cm", loc)
            e.update({"geom": ("MultiPolygon", polys), "pictogramme": p["nature"], "atypique": True, "regles": ["FUS-SNP-004"]})
            e["prov"]["geometrie"]["conf"] = "faible"
            out.append(e)
    for c in C["chaines"]:
        if c["nature"] != "chevron":
            continue
        ouv = math.radians(c["ouverture_deg"])
        d = np.array([math.cos(math.radians(c["cap_deg"])), math.sin(math.radians(c["cap_deg"]))])
        tr = 0.12                                                     # MQ-CYC-008
        o = c["pointe"] + d * (0.5 * tr / math.sin(ouv / 2))         # pointe extérieure (levé = axe du trait)
        e = base(ident("MS", 5000 + c["gam"][0]), "symbole", "chevron", o, c["gam"],
                 f"chevron levé GAM {c['gam'][0]} (branches {c['branche_m']:.2f} m, ouverture {c['ouverture_deg']:.0f}°)", loc)
        e.update({"chevron": {"branche_m": round(c["branche_m"] + 0.5 * tr / math.tan(ouv / 2), 3),
                              "ouverture_deg": round(c["ouverture_deg"], 2), "trait_m": tr},
                  "pose": {"origine_local": o, "cap_deg": round(c["cap_deg"], 3), "cap_source": "gam"},
                  "regles": ["MQ-CYC-008", "FUS-SNP-004"]})
        e["prov"]["trait_m"] = {"src": "regle:regles_conception.MQ-CYC-008", "ref": "double chevron : trait 0,12 m", "conf": "moyenne"}
        out.append(e)
    for t in C["triangles"]:
        A, B = t["base"]
        mb = 0.5 * (A + B)
        h = float(np.hypot(*(t["sommet"] - mb)))
        cap = M.cap_de(t["sommet"] - mb)
        e = base(ident("MS", 5000 + min(t["gam"])), "symbole", "dent_requin", mb, t["gam"],
                 f"triangle de plateau levé GAM {t['gam']} (base {np.hypot(*(A - B)):.2f} m, hauteur {h:.2f} m ; "
                 "dessiné rectangle, posé isocèle)", loc)
        e.update({"triangle": {"base_m": round(float(np.hypot(*(A - B))), 3), "hauteur_m": round(h, 3)},
                  "pose": {"origine_local": mb, "cap_deg": round(cap, 3), "cap_source": "gam"}, "regles": ["MQ-RAL-001", "FUS-SNP-004"]})
        out.append(e)
    for a in C["anneaux"]:
        if a["nature"] == "triangle":
            r = M.douglas_peucker(np.vstack([a["anneau"], a["anneau"][:1]]), 0.02)[:-1]
            Ls = [float(np.hypot(*(r[(k + 1) % 3] - r[k]))) for k in range(3)]
            k = int(np.argmin(Ls))
            A, B, P = r[k], r[(k + 1) % 3], r[(k + 2) % 3]
            mb = 0.5 * (A + B)
            e = base(ident("MS", 5000 + a["gam"][0]), "symbole", "dent_requin", mb, a["gam"], f"triangle levé GAM {a['gam']}", loc)
            e.update({"triangle": {"base_m": round(Ls[k], 3), "hauteur_m": round(float(np.hypot(*(P - mb))), 3)},
                      "pose": {"origine_local": mb, "cap_deg": round(M.cap_de(P - mb), 3), "cap_source": "gam"}, "regles": ["FUS-SNP-004"]})
            out.append(e)
        elif a["nature"] in ("carre", "tiret") or (a["nature"] in ("bande", "bande_oblique") and not set(a["gam"]) & utilises):
            o = a["obb"]
            e = base(ident("MS", 5000 + a["gam"][0]), "symbole", "barre", o["c"], a["gam"],
                     f"{a['nature']} levé GAM {a['gam']} ({o['L']:.2f} x {o['W']:.2f} m)", loc)
            e.update({"rectangle": {"longueur_m": round(o["L"], 3), "largeur_m": round(o["W"], 3)},
                      "pose": {"origine_local": o["c"], "cap_deg": round(M.cap_de(o["u"]), 3), "cap_source": "gam"}})
            out.append(e)
        elif a["nature"] == "atypique" and not set(a["gam"]) & utilises:
            o = a["obb"]
            if o["L"] > 4.5 and o["W"] > 1.5:
                continue                     # contour de zone sans remplissage connu : non décrit (rapport)
            r = M.douglas_peucker(np.vstack([a["anneau"], a["anneau"][:1]]), 0.01)[:-1]
            e = base(ident("MZ", 5000 + a["gam"][0]), "zone", "divers", o["c"], a["gam"],
                     f"contour levé GAM {a['gam']} hors gabarits IISR (meilleure IoU < 0,55) : polygone levé simplifié à 1 cm", loc)
            e.update({"geom": ("Polygon", [[r]]), "atypique": True, "regles": ["FUS-SNP-004"]})
            e["prov"]["geometrie"]["conf"] = "faible"
            out.append(e)
    return out


def zigzags(C, loc):
    out = []
    for c in C["chaines"]:
        if c["nature"] != "zigzag":
            continue
        s = M.douglas_peucker(c["P"], 0.03)
        # sommets alternés : côté base (le plus proche de la droite des extrémités) et côté sommet
        A, B = s[0], s[-1]
        u = (B - A) / np.hypot(*(B - A))
        n = np.array([-u[1], u[0]])
        h = (s - A) @ n
        cote = 1 if np.median(h[1:-1]) > 0 else -1
        bas = s[(h * cote) < 0.5 * np.max(h * cote)]
        haut = s[(h * cote) >= 0.5 * np.max(h * cote)]
        # droite de base : moindres carrés sur les sommets bas
        if len(bas) >= 2:
            c0 = bas.mean(axis=0)
            _, _, vt = np.linalg.svd(bas - c0)
            ub = vt[0] if float(vt[0] @ u) > 0 else -vt[0]
        else:
            c0, ub = A, u
        nb = np.array([-ub[1], ub[0]]) * cote
        amp = float(np.median((haut - c0) @ nb))
        proj = np.sort(np.r_[(haut - c0) @ ub])
        periode = float(np.median(np.diff(proj))) if len(proj) >= 2 else 5.0
        t0, t1 = float(proj.min()), float(proj.max())
        A2, B2 = c0 + ub * t0, c0 + ub * t1
        e = base(ident("MZ", 5000 + c["gam"][0]), "zone", "zigzag", np.vstack([A2, B2]), c["gam"],
                 f"zigzag levé GAM {c['gam']} : période mesurée {periode:.2f} m, amplitude {amp:.2f} m", loc, couleur="jaune")
        pe = 5.0 if abs(periode - 5.0) <= 0.5 else round(periode, 3)
        ap = 2.5 if abs(amp - 2.5) <= 0.25 else round(amp, 3)
        e.update({"geom": ("LineString", np.vstack([A2, B2])), "cote": cote, "amplitude_m": ap, "periode_m": pe,
                  "trait_m": 0.12, "regles": ["MQ-BUS-005", "FUS-SNP-004"],
                  "mesures": {"periode_levee_m": round(periode, 3), "amplitude_levee_m": round(amp, 3)}})
        e["prov"]["couleur"] = {"src": "regle:regles_conception.MQ-BUS-005", "ref": "zigzag d'arrêt de bus jaune 2u", "conf": "haute"}
        out.append(e)
    return out


# --------------------------------------------------------------------------- lignes
def _largeur(mes, role, br, piste):
    u = LG.u_itineraire(br, piste)
    if mes is not None:
        w = min(LARGEURS, key=lambda x: abs(x - mes))
        if abs(w - mes) <= 0.02:
            return w, {"src": "gam", "ref": f"bords levés écartés de {mes:.3f} m -> {w} (FUS-SNP-004)", "conf": "haute"}
        return round(mes, 3), {"src": "gam", "ref": f"bords levés écartés de {mes:.3f} m (hors table) : largeur levée gardée", "conf": "haute"}
    n = LG.ROLES_U.get(role, 2)
    return round(n * u, 3), {"src": "regle:marquages_geometrie.largeurs_par_ligne", "ref": f"{role} {n}u, u = {u} ({br})",
                             "conf": "moyenne"}


def _ancrer(chaines, P):
    """Ancrage OpenDRIVE d'un axe levé : (ancrage, axe, mesures) si le bord + t_off suit le levé à 4 cm (p95)."""
    u = P[-1] - P[0]
    if np.hypot(*u) < 1e-6:
        return None
    u = u / np.hypot(*u)
    anc = LG.ancrer(chaines, P, u)
    if anc is None:
        return None
    ch, t_off, frac = anc
    sig, _, _ = projeter(ch.xy, P)
    s0, s1 = float(ch.s_de_sig(sig.min())), float(ch.s_de_sig(sig.max()))
    if s1 - s0 < 0.3:
        return None
    Q = ch.axe(t_off, s0, s1)
    _, d, _ = projeter(Q, densifier(P, 0.10)[0])
    if float(np.percentile(d, 95)) > LG.TOL_LAT_GAM:
        return None
    return ({"type": "xodr", "route": ch.route, "bords": ch.troncons(s0, s1), "s0": round(s0, 3), "s1": round(s1, 3),
             "t_off_m": round(t_off, 4)}, Q, {"lateral_gam_p95_m": round(float(np.percentile(d, 95)), 4)}, ch)


def lignes(C, loc, chaines, utilises):
    out = []
    ch_ = [c for c in C["chaines"] if c["nature"] in ("axe", "segment") and not set(c["gam"]) & utilises]
    idx = {id(c): i for i, c in enumerate(C["chaines"])}
    faits = set()
    pistes = set()
    # axes (paires fusionnées)
    axes = []
    for c in ch_:
        i = idx[id(c)]
        if i in faits:
            continue
        if "paire" in c:
            j, ecart, _ = c["paire"]
            cj = C["chaines"][j]
            faits |= {i, j}
            a, b = (c, cj) if c["longueur_m"] >= cj["longueur_m"] else (cj, c)
            P = GC.mediane(a["P"], b["P"])
            if len(P) < 2:
                continue
            axes.append((P, ecart, sorted(set(c["gam"]) | set(cj["gam"]))))
        else:
            faits.add(i)
            axes.append((c["P"], None, c["gam"]))
    est_long = [float(abscisses(x[0])[-1]) >= 6.5 or M.rect_min(x[0])["W"] > 0.05 for x in axes]
    longs = [x for x, l_ in zip(axes, est_long) if l_]
    courts = [x for x, l_ in zip(axes, est_long) if not l_ and float(abscisses(x[0])[-1]) >= 0.3]
    # rangées de tirets alignés
    rangs = _rangees(courts)
    for P, ecart, gam in longs:
        out.append(_ligne(P, ecart, gam, "continue", None, loc, chaines))
    for r in rangs:
        if len(r) == 1:
            P, ecart, gam = r[0]
            if float(abscisses(P)[-1]) >= 1.0:
                out.append(_ligne(P, ecart, gam, "segment", None, loc, chaines))
            continue
        # axe de la rangée : droite ajustée sur les tirets
        pts = np.vstack([x[0] for x in r])
        c0 = pts.mean(axis=0)
        _, _, vt = np.linalg.svd(pts - c0)
        u = vt[0] if vt[0][0] >= 0 else -vt[0]
        pr = [((x[0] - c0) @ u) for x in r]
        a, b = min(p.min() for p in pr), max(p.max() for p in pr)
        axe = np.vstack([c0 + u * a, c0 + u * b])
        plages = sorted((float(p.min() - a), float(p.max() - a), 0.0, 1.0) for p in pr)
        mods = DL.modeliser(plages, b - a)
        gam = sorted(k for x in r for k in x[2])
        ec = [x[1] for x in r if x[1] is not None]
        for m in mods:
            P = np.vstack([axe[0] + u * m["sigma0"], axe[0] + u * m["sigma1"]])
            e = _ligne(P, float(np.median(ec)) if ec else None, gam, m["type"], m, loc, chaines)
            out.append(e)
    # identifiants uniques (une rangée peut donner plusieurs morceaux)
    vus, extra = set(), 0
    for e in sorted(out, key=lambda e: (e["gam"][0], float(e["geom"][1][0][0]), float(e["geom"][1][0][1]))):
        k = e["gam"][0]
        if k not in vus:
            vus.add(k)
            e["id"] = ident("ML", 5000 + k)
        else:                                   # morceau supplémentaire d'une même rangée levée
            e["id"] = ident("ML", 5450 + extra)
            extra += 1
    return out


def _rangees(courts):
    """Tirets levés alignés (parallèles à ± 4°, écart latéral ≤ 0,08 m, trou ≤ 14 m) -> rangées (listes)."""
    n = len(courts)
    par = list(range(n))

    def r(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    info = []
    for P, _, _ in courts:
        u = P[-1] - P[0]
        u = u / max(np.hypot(*u), 1e-9)
        info.append((u, 0.5 * (P[0] + P[-1]), P))
    for i in range(n):
        ui, mi, Pi = info[i]
        ni = np.array([-ui[1], ui[0]])
        for j in range(i + 1, n):
            uj, mj, Pj = info[j]
            if abs(float(ui @ uj)) < math.cos(math.radians(4.0)):
                continue
            if abs(float((mj - mi) @ ni)) > 0.08:
                continue
            gap = min(float(np.hypot(*(a - b))) for a in (Pi[0], Pi[-1]) for b in (Pj[0], Pj[-1]))
            if gap <= 14.0:
                par[r(j)] = r(i)
    g = collections.defaultdict(list)
    for i in range(n):
        g[r(i)].append(courts[i])
    return sorted(g.values(), key=lambda x: min(min(y[2]) for y in x))


def _ligne(P, ecart, gam, type_, mod, loc, chaines):
    P = M.dedoublonner(P)
    c = P[len(P) // 2]
    br = branche(loc, c)
    vs = loc.voies(c, types=("biking",))
    piste = bool(vs and vs[0]["ecart_centre"] < 1.5)
    anc = _ancrer(chaines, P)
    e = base("ML-0000", "ligne", type_, P, gam, f"axe levé GAM {','.join(map(str, gam))}"
             + (f" (paire de bords écartés de {ecart:.3f} m)" if ecart else ""), loc)
    role = ("axe", "défaut")
    if anc:
        ancrage, Q, mes, ch = anc
        e["ancrage"] = ancrage
        e["geom"] = ("LineString", M.douglas_peucker(Q, 0.001))
        e["mesures"] = mes
        e["prov"]["ancrage"] = {"src": "xodr", "ref": f"bord {ch.cle} + t_off médian du levé (p95 {mes['lateral_gam_p95_m']} m)", "conf": "haute"}
        role = LG.role_xodr(ch, 0.5 * (ancrage["s0"] + ancrage["s1"])) or role
    else:
        e["ancrage"] = {"type": "axe", "source": "gam"}
        e["geom"] = ("LineString", M.douglas_peucker(GL.adoucir(P), 0.001))
        e["mesures"] = {}
    if piste:
        role = ("rive_piste" if ecart is None else role[0], "piste cyclable")
    w, pw = _largeur(ecart, role[0], br, piste)
    e["largeur_m"], e["role"] = w, role[0] if role[0] in LG.ROLES_U else "axe"
    e["prov"]["largeur_m"] = pw
    L = float(abscisses(e["geom"][1])[-1])
    e["longueur_m"] = round(L, 3)
    e["interruptions"] = []
    if type_ == "discontinue":
        e.update({"modulation": mod["code"], "trait_m": mod["trait_m"], "vide_m": mod["vide_m"], "phase_m": 0.0,
                  "modulation_source": "IISR", "n_tirets": mod["n_tirets"]})
        e["prov"]["modulation"] = {"src": "gam", "ref": f"{mod['n_vus']} tirets levés suivant le motif IISR {mod['code']} "
                                   f"(DET-LIG-011) ; tirets manquants reconstruits (TQ-DED-002)", "conf": "haute"}
        e["prov"]["phase_m"] = {"src": "gam", "ref": "début du premier tiret levé", "conf": "haute"}
        e["regles"] = ["DET-LIG-011", "TQ-DED-002", "FUS-SNP-004"]
    else:
        e["modulation"] = "continue"
        e["regles"] = ["FUS-SNP-004"]
    return e


# --------------------------------------------------------------------------- géométrie posée des gabarits
def _rect(c, d, L, W):
    n = np.array([-d[1], d[0]])
    return np.array([c - d * L / 2 - n * W / 2, c + d * L / 2 - n * W / 2, c + d * L / 2 + n * W / 2, c - d * L / 2 + n * W / 2])


def geom_posee(e):
    """Polygones posés (local) d'une flèche ou d'un symbole décrit par ses paramètres (mêmes constructions que
    houdini/pj_marquages) -> ("MultiPolygon", [[anneau]]) ou None."""
    import marquages_symboles as SY_
    if "pose" not in e:
        return None
    o = np.asarray(e["pose"]["origine_local"], float)
    cap = float(e["pose"]["cap_deg"])
    d = np.array([math.cos(math.radians(cap)), math.sin(math.radians(cap))])
    ex = np.array([d[1], -d[0]])
    cl, ty = e["classe"], e["type"]
    if cl == "fleche" or (cl == "symbole" and ty == "velo"):
        nom = e.get("gabarit") or "VELO"
        ech = float(e.get("echelle", 1.0))
        return ("MultiPolygon", [[M.poser(r, o, cap, ech) for r in poly] for poly in M.gabarit(nom)])
    if cl == "symbole" and ty in ("pmr", "texte"):
        return ("MultiPolygon", [[M.poser(r, o, cap) for r in poly] for poly in SY_.construire_glyphe(e["glyphe"])])
    if ty == "dent_requin":
        b, h = float(e["triangle"]["base_m"]), float(e["triangle"]["hauteur_m"])
        return ("MultiPolygon", [[np.array([o - ex * b / 2, o + ex * b / 2, o + d * h])]])
    if ty == "chevron":
        c = e["chevron"]
        lb, ouv, tr = float(c["branche_m"]), math.radians(float(c["ouverture_deg"])), float(c["trait_m"])
        u1 = M.poser(np.array([[math.sin(ouv / 2), -math.cos(ouv / 2)]]), np.zeros(2), cap)[0]
        u2 = M.poser(np.array([[-math.sin(ouv / 2), -math.cos(ouv / 2)]]), np.zeros(2), cap)[0]
        n1 = M.poser(np.array([[-math.cos(ouv / 2), -math.sin(ouv / 2)]]), np.zeros(2), cap)[0]
        n2 = M.poser(np.array([[math.cos(ouv / 2), -math.sin(ouv / 2)]]), np.zeros(2), cap)[0]
        e1, e2 = o + u1 * lb, o + u2 * lb
        ic = o - d * (tr / math.sin(ouv / 2))
        return ("MultiPolygon", [[np.array([o, e2, e2 + n2 * tr, ic, e1 + n1 * tr, e1])]])
    if ty == "barre":
        return ("MultiPolygon", [[_rect(o, d, float(e["rectangle"]["longueur_m"]), float(e["rectangle"]["largeur_m"]))]])
    if ty == "point":
        dm = float(e["disque"]["diametre_m"])
        a = np.linspace(0, 2 * math.pi, 48, endpoint=False)
        return ("MultiPolygon", [[o + 0.5 * dm * np.c_[np.cos(a), np.sin(a)]]])
    return None


def completer_ancrage(entites, loc):
    """Ancrage des flèches qui n'en ont pas (levé, détection) : voie OpenDRIVE sous le milieu de la flèche (route, voie,
    section_s, s, t de l'origine), sinon pose seule."""
    for e in entites:
        if e["classe"] != "fleche" or e.get("ancrage"):
            continue
        o = np.asarray(e["pose"]["origine_local"], float)
        ey = M.axes_cap(e["pose"]["cap_deg"])[1]
        vs = loc.voies(o + 2.0 * ey * float(e.get("echelle", 1.0)))
        if vs:
            v = vs[0]
            e["ancrage"] = {"type": "xodr", "route": v["route"], "voie": int(v["voie"]), "section_s": round(float(v["section_s"]), 3),
                            "s": round(float(v["s"]), 3), "t": round(float(v["t"]), 3)}
        else:
            e["ancrage"] = {"type": "pose"}
    return entites


def completer_geom(entites):
    for e in entites:
        if "pose" in e and e["classe"] in ("fleche", "symbole"):
            g = geom_posee(e)
            if g is not None:
                e["geom"] = g
    return entites


def entites(reseau, loc):
    """Toutes les entités GAM (repère local) et le journal des morceaux non décrits."""
    C = GC.classer()
    chaines = LG.chaines_reseau(reseau)
    LG.RESEAU[:] = [reseau]
    zh, utilises = zebras_hachures(C, loc)
    ha = hachures(C, loc, utilises)
    out = zh + ha + fleches(C, loc) + symboles(C, loc, utilises) + zigzags(C, loc) + lignes(C, loc, chaines, utilises)
    completer_geom(out)
    utilises_tous = {k for e in out for k in e["gam"]}
    G = M.gam_lin()
    non_decrits = [k for k in range(len(G)) if k not in utilises_tous]
    return out, {"non_decrits": non_decrits, "classement": GC.resume()}
