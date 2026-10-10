"""Reprises de la description des marquages (revue du 10/10, deuxième tour) : passes appliquées après la construction des
entités (marquages.construire), dans cet ordre :

1. flèches hors des voies du réseau 2026 (fleches_hors_voie) : une flèche d'un état 2022 dont l'origine tombe dans une voie
   non roulable du .xodr 2026 (trottoir, bordure, accotement) n'existe plus en 2026 -> retirée (devenir « retire »),
   avec le gabarit lu sur l'ortho 2022 (classement étendu au gabarit TD_TAG_TAD, flèche à trois directions = TD_TAD ∪
   miroir) ;
2. recouvrements entre entités (recouvrements / resoudre) : empreintes peintes rastérisées (2 cm) ; recouvrement de plus
   de 0,01 m² hors surface colorée et fantômes (sous les marques) -> le symbole posé (figurine, PMR, texte, puis flèche)
   est déplacé le long de son cap jusqu'à 0,10 m de toute autre marque (≤ 2 m) ; deux passages : le moins prioritaire
   reçoit une découpe (empreinte de l'autre élargie de 0,10 m) ;
3. dégagement des bordures et sol (marquages_bordures.degager).
"""
import math

import numpy as np

import marquages_bordures as MB
import marquages_commun as M
import marquages_glyphes as GL
from commun import abscisses, point_a, sous_polyligne

RES = 0.02
SEUIL_M2 = 0.01
SEUIL_GABARIT_M2 = 3e-4          # gabarit (flèche, figurine, glyphe) : aucun recouvrement (une cellule de 2 cm près)
DEGAGEMENT = 0.10
DEPLACEMENT_MAX = 2.5


# --------------------------------------------------------------------------- empreintes
def _pieces_ligne(e):
    from marquages_controles import _pieces
    q = dict(e, type="discontinue") if e["classe"] == "transversale" else e
    return _pieces(q, e["geom"][1])


def empreinte(e):
    """Polygones peints (local) d'une entité interne."""
    cl, ty = e["classe"], e["type"]
    if cl in ("ligne", "transversale"):
        P = e["geom"][1]
        out = []
        for a, b in _pieces_ligne(e):
            Q = sous_polyligne(P, a, b)
            if len(Q) >= 2 and abscisses(Q)[-1] > 1e-3:
                out.append([GL.trait(Q, e["largeur_m"])])
        return out
    if cl == "zone" and ty == "zigzag":
        A, B = e["geom"][1][:2]
        L = float(np.hypot(*(B - A)))
        u = (B - A) / L
        n = np.array([-u[1], u[0]]) * (1 if int(e["cote"]) > 0 else -1)
        npr = max(1, int(round(L / float(e["periode_m"]))))
        Pp = L / npr
        pts = [A]
        for k in range(npr + 1):
            pts.append(A + u * (k * Pp) + n * e["amplitude_m"])
            if k < npr:
                pts.append(A + u * ((k + 0.5) * Pp))
        pts.append(B)
        return [[GL.trait(np.array(pts), e["trait_m"])]]
    return MB.polygones_entite(e)


def _bbox(polys, marge=0.0):
    P = np.vstack([r for poly in polys for r in poly])
    return (*(P.min(axis=0) - marge), *(P.max(axis=0) + marge))


def _decoupes(e):
    return [[np.asarray(d["polygone_local"], float)] for d in e.get("decoupes", [])]


def _aire_commune(pa, pb, dil=0.0, ca=(), cb=()):
    """Aire commune (m²) des empreintes pa et pb (pb élargie de dil), découpes ca / cb retirées."""
    a, b = _bbox(pa, dil), _bbox(pb, dil)
    x0, y0, x1, y1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    nx, ny = int(math.ceil((x1 - x0) / RES)) + 1, int(math.ceil((y1 - y0) / RES)) + 1
    ma = M.raster_masque(pa, x0, y0, nx, ny, RES)
    mb = M.raster_masque(pb, x0, y0, nx, ny, RES)
    if ca:
        ma &= ~M.raster_masque(list(ca), x0, y0, nx, ny, RES)
    if cb:
        mb &= ~M.raster_masque(list(cb), x0, y0, nx, ny, RES)
    if dil > 0:
        k = int(round(dil / RES))
        from PIL import Image, ImageFilter
        mb = np.asarray(Image.fromarray((mb * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(2 * k + 1))) > 0
    return float((ma & mb).sum()) * RES * RES


def permis(ea, eb):
    """Paires dont le recouvrement est permis : surface colorée (fond), fantômes (sous les marques), deux lignes (contrôle
    dédié des parties peintes), une ligne et un passage (interruption de 0,50 m déjà décrite)."""
    ca, cb = {ea["classe"], eb["classe"]}, {ea["type"], eb["type"]}
    if "surface_coloree" in cb or "fantome" in ca:
        return True
    if ca <= {"ligne"}:
        return True
    if "ligne" in ca and "hachures" in cb:
        return True                  # lignes de bord des zones hachurées (la zone est son contour, les bandes sont dedans)
    return False


def _gabarit(e):
    return e["classe"] == "fleche" or e.get("type") in ("velo", "pmr", "texte", "t_stationnement")


def _cede(ea, eb):
    """Paire zone cédante (bande isolée, forme diverse) / ligne : aucun recouvrement toléré (la zone est découpée)."""
    return any(z["classe"] == "zone" and z["type"] in CEDANTES and l["classe"] == "ligne" for z, l in ((ea, eb), (eb, ea)))


def recouvrements(entites, seuil=SEUIL_M2):
    """[(id a, id b, aire m²)] des paires non permises qui se recouvrent de plus de `seuil`."""
    emp = {e["id"]: empreinte(e) for e in entites}
    emp = {k: v for k, v in emp.items() if v}
    par = {e["id"]: e for e in entites}
    ids = sorted(emp)
    bb = {i: _bbox(emp[i]) for i in ids}
    out = []
    for x in range(len(ids)):
        a = ids[x]
        A = bb[a]
        for y in range(x + 1, len(ids)):
            b = ids[y]
            B = bb[b]
            if A[2] < B[0] or B[2] < A[0] or A[3] < B[1] or B[3] < A[1]:
                continue
            if permis(par[a], par[b]):
                continue
            s = _aire_commune(emp[a], emp[b], 0.0, _decoupes(par[a]), _decoupes(par[b]))
            sl = min(seuil, SEUIL_GABARIT_M2) if (_gabarit(par[a]) or _gabarit(par[b]) or _cede(par[a], par[b])) else seuil
            if s > sl:
                out.append((a, b, round(s, 4)))
    return out


# --------------------------------------------------------------------------- résolution
RANG_MOBILE = {"velo": 0, "pmr": 1, "texte": 1, "point": 2, "barre": 3, "chevron": 3, "dent_requin": 3}


def _mobile(e):
    if e["classe"] == "symbole" and e["type"] in RANG_MOBILE:
        return RANG_MOBILE[e["type"]]
    if e["classe"] == "fleche":
        return 5
    return None


def _translater(e, v):
    if "pose" in e:
        e["pose"]["origine_local"] = np.asarray(e["pose"]["origine_local"], float) + v
    t, g = e["geom"]
    if t in ("Polygon", "MultiPolygon"):
        e["geom"] = (t, [[np.asarray(r, float) + v for r in poly] for poly in g])
    a = e.get("ancrage") or {}
    if a.get("type") == "xodr" and "s" in a:
        cap = math.radians(e["pose"]["cap_deg"])
        d = float(v @ np.array([math.cos(cap), math.sin(cap)]))
        a["s"] = round(a["s"] + (d if a.get("voie", -1) < 0 else -d), 3)


def resoudre(entites, devenir=None):
    """Déplace les symboles posés / ajoute des découpes aux passages pour supprimer les recouvrements -> journal."""
    par = {e["id"]: e for e in entites}
    journal = {"deplacements": {}, "decoupes": {}, "non_resolus": []}
    for _ in range(3):
        rec = recouvrements(entites)
        if not rec:
            break
        traites = set()
        for a, b, s in rec:
            ea, eb = par[a], par[b]
            ma, mb = _mobile(ea), _mobile(eb)
            if ma is None and mb is None:
                zl = [(z, l) for z, l in ((ea, eb), (eb, ea)) if z["classe"] == "zone" and z["type"] in CEDANTES and l["classe"] == "ligne"]
                if zl:
                    z, l = zl[0]
                    cut = [{"motif": f"ligne {l['id']}", "obstacle": l["id"], "degagement_m": 0.05, "polygone_local": r}
                           for r in _ruban_local(l, _bbox(empreinte(z), 1.0), 0.05)]
                    z["decoupes"] = z.get("decoupes", []) + cut
                    journal["decoupes"].setdefault(z["id"], []).append(l["id"])
                    continue
                if ea["classe"] == "passage" and eb["classe"] == "passage":
                    # le passage de plus grand id (le moins prioritaire à la fabrication) est découpé par l'autre
                    bas, haut = (ea, eb) if ea["id"] > eb["id"] else (eb, ea)
                    cut = [{"motif": f"passage {haut['id']}", "obstacle": haut["id"], "degagement_m": DEGAGEMENT,
                            "polygone_local": r} for r in _rectangles_dilates(empreinte(haut), DEGAGEMENT)]
                    bas["decoupes"] = bas.get("decoupes", []) + cut
                    journal["decoupes"].setdefault(bas["id"], []).append(haut["id"])
                else:
                    journal["non_resolus"].append([a, b, s])
                continue
            mob, fixe = (ea, eb) if (mb is None or (ma is not None and ma < mb) or (ma == mb and ea["id"] > eb["id"])) else (eb, ea)
            if mob["id"] in traites:
                continue
            dd = _deplacement(mob, entites, fixe["id"])
            if dd is None and fixe["classe"] == "zone" and fixe["type"] in ("zigzag", "aplat", "hachures"):
                # aucune position libre (zigzag d'arrêt de bus sur toute la longueur de la voie) : la zone cède la place au
                # symbole (découpe par sa boîte élargie de DEGAGEMENT)
                cut = [{"motif": f"{mob['classe']} {mob['id']}", "obstacle": mob["id"], "degagement_m": DEGAGEMENT,
                        "polygone_local": r} for r in _rectangles_dilates(empreinte(mob), DEGAGEMENT)]
                fixe["decoupes"] = fixe.get("decoupes", []) + cut
                journal["decoupes"].setdefault(fixe["id"], []).append(mob["id"])
                continue
            if dd is None:
                journal["non_resolus"].append([a, b, s])
                continue
            dl, dt = dd
            cap = math.radians(mob["pose"]["cap_deg"])
            dcap, ncap = np.array([math.cos(cap), math.sin(cap)]), np.array([-math.sin(cap), math.cos(cap)])
            _translater(mob, dl * dcap + dt * ncap)
            mob["deplacement_recouvrement_m"] = [round(dl, 3), round(dt, 3)]
            mob.setdefault("prov", {})["pose"] = dict(mob["prov"].get("pose", {"src": "regle:marquages_reprises", "conf": "moyenne"}),
                                                      ref=mob["prov"].get("pose", {}).get("ref", "") + f" ; déplacée de {dl:+.2f} m le long du cap et de "
                                                      f"{dt:+.2f} m en travers (recouvrait {fixe['id']} sur {s:.3f} m²)")
            journal["deplacements"][mob["id"]] = [round(dl, 3), round(dt, 3), fixe["id"], s]
            traites.add(mob["id"])
    return journal


def _ruban_local(e, bb, d):
    """Ruban de la ligne e (largeur + 2d) sur la partie de son axe dans la boîte bb, morceaux peints compris : [polygone]."""
    P = e["geom"][1]
    from commun import projeter
    S = abscisses(P)
    m = (P[:, 0] >= bb[0]) & (P[:, 0] <= bb[2]) & (P[:, 1] >= bb[1]) & (P[:, 1] <= bb[3])
    Q = np.array([[bb[0], bb[1]], [bb[2], bb[1]], [bb[2], bb[3]], [bb[0], bb[3]]])
    s, _, _ = projeter(P, Q)
    a, b = max(0.0, float(s.min()) - 0.5), min(float(S[-1]), float(s.max()) + 0.5)
    out = []
    for x, y in _pieces_ligne(e):
        x, y = max(x, a), min(y, b)
        if y - x > 1e-3:
            R = sous_polyligne(P, max(0.0, x - d), min(float(S[-1]), y + d))
            if len(R) >= 2:
                out.append(GL.trait(R, e["largeur_m"] + 2 * d))
    return out


def _rectangles_dilates(polys, d):
    """Rectangles orientés minimaux de chaque polygone, élargis de d."""
    out = []
    for poly in polys:
        o = M.rect_min(np.asarray(poly[0], float))
        L, W = o["L"] + 2 * d, o["W"] + 2 * d
        out.append(np.array([o["c"] + o["u"] * a * L / 2 + o["v"] * b * W / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))
    return out


def candidats(cap_deg, long_max, trav_max, pas=0.05):
    """Déplacements candidats (vecteurs locaux), du plus petit au plus grand : le long du cap (≤ long_max), puis en
    travers (≤ trav_max), puis combinés ; ordre déterministe."""
    cap = math.radians(cap_deg)
    d = np.array([math.cos(cap), math.sin(cap)])
    n = np.array([-d[1], d[0]])
    out = []
    for i in range(-int(round(long_max / pas)), int(round(long_max / pas)) + 1):
        for j in range(-int(round(trav_max / pas)), int(round(trav_max / pas)) + 1):
            if i == 0 and j == 0:
                continue
            a, b = i * pas, j * pas
            out.append((round(math.hypot(a, 2.0 * b), 4), abs(j), abs(i), -i, -j, a, b))
    out.sort()
    return [(x[5], x[6], d * x[5] + n * x[6]) for x in out]


def _deplacement(e, entites, conflit=None):
    """Plus petit déplacement (le long du cap ≤ DEPLACEMENT_MAX, en travers ≤ 0,5 m, le travers compté double) qui laisse
    DEGAGEMENT avec la marque en conflit, ne recouvre aucune autre marque non permise et ne rapproche pas la marque d'une
    bordure en deçà de 2u -> (le long, travers) en m ou None."""
    p0 = empreinte(e)
    g2u = MB.DEGAGEMENT_U * MB._u(e)
    Qb = MB._bord_polys(p0, 0.05)
    sd0 = float(np.min(MB.distance_signee(Qb)[0]))
    bb = _bbox(p0, DEPLACEMENT_MAX + 0.5)
    autres = []
    for o in entites:
        if o["id"] == e["id"] or permis(e, o):
            continue
        po = empreinte(o)
        if not po:
            continue
        B = _bbox(po)
        if B[2] < bb[0] or bb[2] < B[0] or B[3] < bb[1] or bb[3] < B[1]:
            continue
        autres.append((po, DEGAGEMENT if o["id"] == conflit else RES, _decoupes(o)))
    for a, b, v in candidats(e["pose"]["cap_deg"], DEPLACEMENT_MAX, 0.5):
        pk = [[np.asarray(r) + v for r in poly] for poly in p0]
        if not all(_aire_commune(pk, po, dil, (), cb) <= 1e-4 for po, dil, cb in autres):
            continue
        if float(np.min(MB.distance_signee(Qb + v)[0])) < min(g2u, sd0) - 1e-4:
            continue
        return a, b
    return None


# --------------------------------------------------------------------------- flèches pleine taille sur piste
def fleches_levees_pleine_taille(entites):
    """Flèches du parking (voie partagée avec les cycles) levées au GAM à pleine taille (contour levé, IoU ≥ 0,85 avec le
    gabarit IISR 4 m) : la mesure prime sur l'homothétie 1/2 des flèches vélo (spec cycles.fleches_velo) ; écart noté."""
    j = []
    for e in entites:
        if e["classe"] == "fleche" and e.get("echelle") == 1.0 and e.get("groupe") == "fleches_parking" and e.get("iou_v1", 0) >= 0.85:
            e.setdefault("ecarts_iisr", []).append(
                f"flèche {e['gabarit']} de 4 m levée au GAM (contour, IoU {e['iou_v1']:.2f}) sur la voie du parking empruntée par les "
                "cycles : taille mesurée gardée (spec cycles.fleches_velo : homothétie 1/2) ; figurines voisines déplacées")
            j.append(e["id"])
    return j


# --------------------------------------------------------------------------- sol non fabricable, lignes sans peinture
# marques du plan 2025 dont le sol v1 (paquet) n'est pas fabricable sous elles : pente > 30 % (raccord ou talus du modèle v1,
# piste Chronovélo 2025 non modélisée) ou marche sur toute leur emprise (constat de la fabrication du 10/10 : aucun triangle)
SOL_NON_FABRICABLE = {
    "MS-0819": "point d'axe Chronovélo (plan 2025) sur le talus du sol v1 (trottoir_2025, pente > 30 % sur toute l'emprise)",
    "MS-0822": "point d'axe Chronovélo (plan 2025) sur le talus du sol v1 (trottoir_2025, pente > 30 % sur toute l'emprise)",
    "MS-0846": "point d'axe Chronovélo (plan 2025) à cheval sur une marche du sol v1 (espace_vert_2025 / trottoir_2025)",
    "MS-0895": "point d'axe Chronovélo (plan 2025) sur le talus du sol v1 (trottoir_2025, pente > 30 % sur toute l'emprise)",
}


def sol_non_fabricable(entites, devenir):
    """Marques gardées mais non fabriquées (SOL_NON_FABRICABLE) : fabrication.statut non_fabrique, devenir
    garde_non_fabrique -> journal."""
    j = {}
    for e in entites:
        r = SOL_NON_FABRICABLE.get(e["id"])
        if r:
            e["fabrication"] = {"statut": "non_fabrique", "raison": r + " : sol absent du paquet, marque gardée non fabriquée"}
            for mq in e["lien_v1"]:
                devenir[mq] = ("garde_non_fabrique", e["id"], e["fabrication"]["raison"])
            j[e["id"]] = r
    return j


def sans_peinture(entites, devenir):
    """Lignes dont toute la longueur est interrompue (marques voisines, bordures) : retirées -> (entités, journal)."""
    out, j = [], {}
    for e in entites:
        if e["classe"] in ("ligne", "transversale") and not _pieces_ligne(e):
            r = ("ligne interrompue sur toute sa longueur par " + ", ".join(e.get("interruptions_marques", []) + e.get("interruptions_zebras", []))
                 + (" et le dégagement des bordures" if e.get("interruptions_bordures") else "")).replace("par  et", "par le dégagement des bordures et")
            j[e["id"]] = r
            for mq in e["lien_v1"]:
                devenir[mq] = ("retire", None, r)
            continue
        out.append(e)
    return out, j


# --------------------------------------------------------------------------- suivi du levé GAM
def suivre_gam(entites, reseau):
    """Lignes ancrées sur un bord xodr : écart latéral aux axes levés GAM de tous leurs MQ (y compris ceux des doublons
    absorbés), lignes d'une autre marque exclues ; p95 > marquages_lignes.PROFIL_SEUIL -> profil t(s) (nœuds de 4 m,
    moindres carrés lissés) ajouté au profil existant, géométrie recalculée -> journal {ligne: nœuds}."""
    import marquages_lignes as LG
    chaines = {}
    for ch in LG.chaines_reseau(reseau):
        for b in ch.bords:
            chaines[(ch.route, round(b.section_s, 3), b.voie)] = ch
    V = {m["id"]: m for m in M.v1()}
    journal = {}
    for e in sorted(entites, key=lambda e: e["id"]):
        a = e.get("ancrage") or {}
        if e["classe"] != "ligne" or a.get("type") != "xodr" or not a.get("bords"):
            continue
        refs = sorted({k for mq in e["lien_v1"] for k in M.gam_refs(V[mq]["p"])} | set((e.get("ajout") or {}).get("gam", [])))
        if not refs:
            continue
        b0 = a["bords"][0]
        ch = chaines[(a["route"], round(float(b0["section_s"]), 3), int(b0["voie"]))]
        ancien = a.get("t_off_profil")
        P, ss = ch.axe(a["t_off_m"], a["s0"], a["s1"], avec_s=True, profil=ancien)
        refs = [k for k in refs if k not in set(LG.refs_etrangeres(P, refs)) | set(e.get("gam_refs_exclues", []))]
        prof = LG.profil_refs(refs, P, ss)
        if not prof:
            continue
        if ancien:
            prof = [[x, round(v + float(np.interp(x, [q[0] for q in ancien], [q[1] for q in ancien])), 4)] for x, v in prof]
            ks = sorted({q[0] for q in ancien} | {q[0] for q in prof})
            prof = [[x, round(float(np.interp(x, [q[0] for q in prof], [q[1] for q in prof])), 4)] for x in ks]
        a["t_off_profil"] = prof
        L0 = e["longueur_m"]
        Pn = ch.axe(a["t_off_m"], a["s0"], a["s1"], profil=prof)
        e["geom"] = ("LineString", M.douglas_peucker(Pn, 0.001))
        L = float(abscisses(e["geom"][1])[-1])
        k = L / max(L0, 1e-9)
        if abs(k - 1) > 1e-6:
            e["interruptions"] = [[round(x * k, 3), round(y * k, 3)] for x, y in e.get("interruptions", [])]
        e["longueur_m"] = round(L, 3)
        e["prov"]["geometrie"] = dict(e["prov"]["geometrie"], ref=e["prov"]["geometrie"]["ref"]
                                      + f" ; profil t(s) sur les lignes GAM {','.join(map(str, refs))} ({len(prof)} nœuds)")
        journal[e["id"]] = prof
    return journal


# --------------------------------------------------------------------------- lignes interrompues
BLOQUANTS = {("zone", "zigzag"), ("zone", "aplat"), ("transversale", "effet_feux")}
CEDANTES = ("bande_isolee", "divers")     # zones qui cèdent la place à une ligne qui les traverse (découpe de la zone)


def interrompre_lignes(entites):
    """Lignes longitudinales interrompues là où elles recouvrent un zigzag, un aplat ou une ligne d'effet des feux (bord
    peint à moins de 0,05 m de la marque) -> journal {ligne: [[σ0, σ1, entité], ...]} ; une bande isolée (reste de zébra) ou
    une forme diverse traversée par une ligne cède la place (resoudre : découpe le long de la ligne)."""
    from commun import dans_polygones, distance_segments
    import marquages_bordures as MB_
    bloc = [(e["id"], empreinte(e)) for e in entites if (e["classe"], e["type"]) in BLOQUANTS]
    bloc = [(i, p, _bbox(p, 0.6)) for i, p in bloc if p]
    journal = {}
    for e in entites:
        if e["classe"] != "ligne":
            continue
        P = e["geom"][1]
        s, Q, T = MB_._echantillons(e, P, 0.02)
        if not len(s):
            continue
        w = float(e["largeur_m"])
        lo, hi = Q.min(axis=0), Q.max(axis=0)
        inter = []
        for bid, polys, bb in bloc:
            if bb[2] < lo[0] or bb[0] > hi[0] or bb[3] < lo[1] or bb[1] > hi[1]:
                continue
            A = np.vstack([r for poly in polys for r in poly])
            B = np.vstack([np.roll(r, -1, axis=0) for poly in polys for r in poly])
            d, _, _ = distance_segments(Q, A, B)
            dedans = dans_polygones(Q, polys) | (d < w / 2 + 0.05)
            if not dedans.any():
                continue
            ks = np.where(dedans)[0]
            coupes = np.where(np.diff(ks) > 1)[0]
            for i0, i1 in zip(np.r_[ks[0], ks[coupes + 1]], np.r_[ks[coupes], ks[-1]]):
                inter.append([round(max(0.0, float(s[i0]) - 0.02), 3), round(min(e["longueur_m"], float(s[i1]) + 0.02), 3), bid])
        if inter:
            e["interruptions"] = MB_._fusion(e.get("interruptions", []) + [x[:2] for x in inter])
            e["interruptions_marques"] = sorted({x[2] for x in inter})
            journal[e["id"]] = inter
    return journal


# --------------------------------------------------------------------------- flèches hors voie
def _points_dans(polys, pas):
    """Points d'une grille de `pas` m à l'intérieur des polygones (local)."""
    from commun import dans_polygones
    P = np.vstack([r for poly in polys for r in poly])
    xs = np.arange(P[:, 0].min(), P[:, 0].max() + 1e-9, pas)
    ys = np.arange(P[:, 1].min(), P[:, 1].max() + 1e-9, pas)
    X, Y = np.meshgrid(xs, ys)
    G = np.c_[X.ravel(), Y.ravel()]
    return G[dans_polygones(G, polys)]


def gabarit_trois_directions():
    """TD_TAG_TAD (écart du site, hors IISR) : réunion de TD_TAD et de son miroir (TD_TAG symétrique), même origine."""
    td_tad = M.gabarit("TD_TAD")
    miroir = [[np.c_[-np.asarray(r)[:, 0], np.asarray(r)[:, 1]][::-1] for r in poly] for poly in td_tad]
    return td_tad + miroir


def fleches_hors_voie(entites, reseau, devenir):
    """Flèches d'un état 2022 posées dans une voie non roulable du .xodr 2026 -> retirées ; classement sur l'ortho 2022
    (corrélation au gabarit décrit et au gabarit à trois directions) dans la justification -> (entités, journal)."""
    import marquages_ortho as MO
    import marquages_symboles as SY
    loc = SY.Localisateur(reseau)
    out, journal = [], {}
    for e in entites:
        if e["classe"] != "fleche" or e["etat"] not in MO.ETATS_2022 or e.get("echelle", 1.0) != 1.0:
            out.append(e)
            continue
        o = np.asarray(e["pose"]["origine_local"], float)
        cap = e["pose"]["cap_deg"]
        pts = _points_dans(e["geom"][1], 0.15)
        roul = np.array([bool(loc.voies(q, types=("driving", "bus", "biking"))) for q in pts])
        hors = [loc.voies(q, types=("sidewalk", "curb", "border", "shoulder", "median", "none", "restricted")) for q in pts]
        if roul.mean() >= 0.5 or not any(hors):
            out.append(e)
            continue
        v = next(h[0] for h in hors if h)
        r1 = MO.recaler(M.gabarit(e["gabarit"]), o, cap, echelle=(1.0, 1.0))
        r3 = MO.recaler(gabarit_trois_directions(), o, cap, echelle=(1.0, 1.0))
        lu = "TD_TAG_TAD (trois directions)" if r3 and r1 and r3["corr_max"] > r1["corr_max"] + 0.05 else e["gabarit"]
        raison = (f"flèche de 2022 hors des voies roulables du réseau 2026 ({1 - roul.mean():.0%} de l'empreinte hors voie, dans la voie "
                  f"{v['route']}/{v['voie']} "
                  f"({v['type']}) du .xodr (voie roulable voisine en biseau) ; plan projet 2025 : emprise réaménagée (piste, "
                  f"espace vert) ; ortho 2022 : {lu} (corrélation {e['gabarit']} {r1['corr_max'] if r1 else float('nan'):.2f}, "
                  f"TD_TAG_TAD {r3['corr_max'] if r3 else float('nan'):.2f}) ; zone resurfacée en 2025 : pas d'empreinte")
        journal[e["id"]] = raison
        for mq in e["lien_v1"]:
            devenir[mq] = ("retire", None, raison)
    return out, journal
