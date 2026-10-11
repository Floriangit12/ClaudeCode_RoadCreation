"""Famille `surfaces` de la description v2 (schéma 0.3) : partition VECTORIELLE du site complet
(carré de 300 m), classe, revêtement (materiau_id), bords, rampes et paliers derrière les abaissés.

Géométrie (aucune limite tirée d'un raster, sauf résidu signalé) — sol_partition.arrangement de :
  1. bord du site (carré de 300 m) ;
  2. bordures v2 : arête avant (face vue), arête arrière (avant décalée de la largeur de base du profil,
     bordures.json) et bouts : l'emprise de chaque bordure est une face (classe `emprise_bordure`) ;
  3. emprises de bâtiments (batiments_local du paquet : trous de la partition) ;
  4. rampes et paliers derrière les abaissés en plan incliné (GA-ABA-003, GA-ABA-005, GA-CHR-002) ;
  5. OpenDRIVE (routes 1-6) : bords de chaussée et de piste là où aucune bordure ne les double à moins
     de 0,50 m, coupes de la jonction 100 (TQ-SOL-014) ;
  6. levé GAM 2026 : limites de revêtement, végétation, talus (haut et bas) ;
  7. fermetures : résidus signalés (`limite_raster`) — changements de classe de la carte d'indices sans
     aucune ligne vectorielle à moins de 0,30 m, chaînés, simplifiés (Douglas-Peucker 0,25 m, Chaikin),
     accrochés aux lignes vectorielles ; boucles isolées de moins de 20 m² supprimées (taches raster).
Les lignes de priorité inférieure qui doublent (à moins de 6 cm, parallèles) une ligne supérieure ou
entrent dans une emprise de bordure sont retirées (TQ-SOL-001).

Classe : vote sur la carte d'indices (0,10 m ; indices seulement) : classes v1 (surfaces_2026), masque de
chaussée 2026 de l'atelier relief, voies OpenDRIVE, côtés des bordures de chaussée (côté bas circulé,
côté haut piéton), bâtiments. Revêtement : correspondance v1 (a priori) ou défaut de la classe, corrigés
par les constats. Identifiants : `S-<surface v1 dominante>[a-z]{0,2}`, `S-9<nnn>` sans indice v1,
`S-B<bordure>[-n]` pour les emprises de bordure.
"""
import collections
import functools
import math

import numpy as np

import sol_site as ctx
import sol_partition as SP
import sol_geometrie as G
from commun import (abscisses, aire_signee, arrondi, couper_polyligne, dans_polygone, distance_segments,
                    geom_polygones, normale_gauche, point_a, repere, sous_polyligne)

# --------------------------------------------------------------------------- classes
CLASSES = ["", "chaussee", "parking", "acces_riverain", "piste_cyclable", "trottoir", "quai_bus", "ilot",
           "terre_plein_vegetal", "espace_vert", "autre", "batiment"]
CODE = {c: i for i, c in enumerate(CLASSES)}
GROUPE = {"chaussee": 1, "parking": 2, "acces_riverain": 2, "piste_cyclable": 3, "trottoir": 4, "quai_bus": 4,
          "ilot": 5, "terre_plein_vegetal": 6, "espace_vert": 6, "autre": 7, "batiment": 8}
VEHICULES = {"chaussee", "parking", "acces_riverain"}
PIETONS = {"trottoir", "quai_bus"}
PRIORITE = {"fermeture_bout": 8, "emprise": 0, "bordure_avant": 1, "bordure_arriere": 1, "bordure_bout": 1, "batiment": 2,
            "rampe": 3, "xodr_bord": 4, "xodr_jonction": 4, "limite_revetement": 5, "vegetation": 6,
            "talus_haut": 6, "talus_bas": 6, "osm_parking": 7, "fermeture": 9}
DISCONTINUES = {"bordure_arriere", "bordure_bout", "batiment", "emprise"}   # ruptures de niveau (nivellement)

NOUE_DZ, NOUE_AIRE = -0.30, 50.0   # massif 2025 en creux sous le fil d'eau voisin et assez grand : noue
# correspondance (classe, matériau v1, état v1) -> materiau_id ; None = toutes valeurs
CORRESPONDANCE = [
    (("trottoir", "enrobe", None), "enrobe_trottoir"),
    (("trottoir", "beton", None), "beton_balaye"),
    (("trottoir", "paves", None), "paves_beton"),
    (("trottoir", "stabilise", None), "stabilise_beige"),
    (("chaussee", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("chaussee", "enrobe", None), "enrobe_bbsg_ancien"),
    (("piste_cyclable", "enrobe", None), "enrobe_piste_cyclable"),
    (("parking", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("parking", "enrobe", None), "enrobe_bbsg_ancien"),
    (("acces_riverain", "enrobe", "modifie_2025"), "enrobe_bbsg_neuf_2025"),
    (("acces_riverain", "enrobe", None), "enrobe_bbsg_ancien"),
    (("ilot", "beton", None), "beton_balaye"),
    (("ilot", "enrobe", None), "enrobe_trottoir"),
    (("quai_bus", "beton", None), "beton_balaye"),
    ((None, "massif_plante", "modifie_2025"), "brf_bois_concasse"),
    ((None, "massif_plante", None), "terre_nue"),
    ((None, "herbe", None), "gazon_tondu"),
    ((None, "terre", None), "terre_nue"),
    ((None, "stabilise", None), "stabilise_beige"),
    ((None, "beton", None), "beton_balaye"),
    ((None, "paves", None), "paves_beton"),
    ((None, "enrobe", None), "enrobe_bbsg_ancien"),
]
DEFAUT_CLASSE = {"chaussee": "enrobe_bbsg_ancien", "parking": "enrobe_bbsg_ancien", "acces_riverain": "enrobe_bbsg_ancien",
                 "piste_cyclable": "enrobe_piste_cyclable", "trottoir": "enrobe_trottoir", "quai_bus": "beton_balaye",
                 "ilot": "beton_balaye", "terre_plein_vegetal": "gazon_tondu", "espace_vert": "gazon_tondu",
                 "autre": "stabilise_beige", "emprise_bordure": "beton_balaye"}
APPAREILLAGE = {
    "paves_beton": {"appareillage": "panneresse", "module_cm": [20, 10], "joint_mm": 5},
    "beton_balaye": {"appareillage": "dalle_coulee", "joints_scies_m": 3.5},
    "brf_bois_concasse": {"appareillage": "vrac", "granulometrie_mm": [20, 50], "epaisseur_m": 0.08},
}
AGE = {"inchange_2022": ("ancien", 0.5), "construit_2023_2024": ("recent", 0.3), "modifie_2025": ("neuf_2025", 0.15)}

# Constats qui corrigent la classe ou le revêtement v1 (id v1 -> correction)
CORRECTIONS = {
    "surf_0121": {"materiau_id": "herbe_haute", "constat": "p2025_05_360-32",
                  "note": "accotement enherbé non tondu de l'approche NE, l'herbe déborde sur la bordure"},
    "surf_0344": {"classe": "chaussee", "sous_classe": "terre_plein_peint", "materiau_id": "enrobe_bbsg_ancien",
                  "constat": "p2025_05_360-06",
                  "note": "au-delà du nez du TPC NE : terre-plein PEINT (deux lignes) ; aucune bordure GAM 2026 ; v1 le donnait en îlot surélevé de 0,16 m",
                  "arasement": "le MNT 2026 garde ici le relief LiDAR 2021 d'un ancien prolongement du TPC (+0,16 m) ; la photo du 18/05/2025 montre un terre-plein peint à niveau : araser au niveau de la chaussée adjacente",
                  "preuve_niveau": "panoramax:9834f494/r01_c01"},
}

FILTRE_XODR_M = 0.50       # un bord OpenDRIVE doublé par une bordure à moins de 0,50 m est retiré
COUVERT_M = 0.30           # une limite de classe à moins de 0,30 m d'une ligne vectorielle est couverte
DP_FERMETURE_M = 0.25
FERMETURE_MIN_M = 1.0
BOUCLE_MIN_M2 = 20.0
LACUNE_MAX_M = 10.0         # fermeture hors bord de chaussée : lacune courte seulement
SLIVER_M2 = 0.05


def materiau_v1(classe, p):
    for (cl, mat, et), mid in CORRESPONDANCE:
        if (cl is None or cl == classe) and mat == p["materiau"] and (et is None or et == p["etat"]):
            return mid
    return None


# --------------------------------------------------------------------------- lignes : bordures
def lignes_bordures(K):
    """[(polyligne, étiquette)], emprises {kid: anneau}, arêtes arrière {kid: Q} (repère local)."""
    lignes, emprises, arrieres = [], {}, {}
    for f in K:
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        Q = G.arete_arriere(P, p["intervalles"])
        arrieres[p["id"]] = Q
        emprises[p["id"]] = G.emprise(P, Q)
        g = p["id"]
        if len(P) > 3 and 1e-3 < float(np.hypot(*(P[0] - P[-1]))) < 1.0 and float(abscisses(P)[-1]) > 4.0:
            # anneau presque fermé (îlot) : arêtes avant et arrière refermées, sans bouts
            lignes.append((np.vstack([P, P[:1]]), {"src": "bordure_avant", "id": g, "groupe": g}))
            lignes.append((np.vstack([Q, Q[:1]]), {"src": "bordure_arriere", "id": g, "groupe": g, "fixe": True}))
            continue
        lignes.append((P, {"src": "bordure_avant", "id": g, "groupe": g}))
        lignes.append((Q, {"src": "bordure_arriere", "id": g, "groupe": g, "fixe": True}))
        lignes.append((np.vstack([P[0], Q[0]]), {"src": "bordure_bout", "id": g, "groupe": g, "fixe": True}))
        lignes.append((np.vstack([P[-1], Q[-1]]), {"src": "bordure_bout", "id": g, "groupe": g, "fixe": True}))
    return lignes, emprises, arrieres


# --------------------------------------------------------------------------- lignes : rampes
def rampes(K, arrieres):
    """Rampes et paliers derrière les abaissés en plan incliné (configuration de bordures.py) :
    [{id, bordure, abaisse, s0, s1, profondeur_m, anneau, contour (U), ...}].
    GA-ABA-003 : plan incliné perpendiculaire de profondeur D = dh / pente (4 % visé, GA-ABA-005 ; 5 %
    au plus, GA-TRO-004) entre les bouts des chartières, passage horizontal ≥ 0,80 m conservé derrière ;
    GA-CHR-002 : charretière, abaissement limité à 1,10 m. Le contour en U (côtés + arête lointaine)
    est inséré dans la partition ; l'arête proche est l'arête arrière de la bordure."""
    out = []
    for f in K:
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        L = float(abscisses(P)[-1])
        for a in p["abaisses"]:
            if a.get("configuration") != "plan_incline" or a["rampe"]["profondeur_m"] < 0.3:
                continue
            s0 = min([a["s0"]] + [r["s0"] for r in a["raccords"]])
            s1 = max([a["s1"]] + [r["s1"] for r in a["raccords"]])
            s0, s1 = max(0.0, s0), min(L, s1)
            if s1 - s0 < 0.5:
                continue
            D = float(a["rampe"]["profondeur_m"])
            seg = sous_polyligne(P, s0, s1)
            S = abscisses(seg) + s0
            wf = lambda s, it=p["intervalles"]: G.largeur_le_long(it, np.asarray(s) + 0.0)
            proche, sp = G.decaler_variable(seg, lambda s: wf(s + s0))
            loin, sl = G.decaler_variable(seg, lambda s: wf(s + s0) + D)
            contour = np.vstack([proche[:1], loin, proche[-1:]])
            anneau = np.vstack([proche, loin[::-1]])
            if aire_signee(anneau) < 0:
                anneau = anneau[::-1]
            out.append({"id": f"R-{a['id'][2:]}", "bordure": p["id"], "abaisse": a["id"], "type": a["type"],
                        "s0": s0, "s1": s1, "s_bateau": [a["s0"], a["s1"]], "profondeur_m": D,
                        "pente_pct": a["rampe"]["pente_pct"], "denivele_m": a["rampe"]["denivele_m"],
                        "contour": contour, "anneau": anneau,
                        "regles": ["GA-ABA-003", "GA-ABA-005", "GA-TRO-004"] if a["type"] != "charretiere"
                        else ["GA-CHR-002", "GA-TRO-004"]})
    return out


# --------------------------------------------------------------------------- lignes : OpenDRIVE
GROUPE_VOIE = {"driving": "chaussee", "bus": "chaussee", "stop": "chaussee", "parking": "chaussee",
               "entry": "chaussee", "exit": "chaussee", "onRamp": "chaussee", "offRamp": "chaussee",
               "curb": "bordure", "sidewalk": "trottoir", "border": "accotement", "median": "tpc"}


@functools.lru_cache(maxsize=None)
def reseau_xodr():
    import xodr_echantillonne as X
    return X.lire_xodr()


def lignes_xodr(pas=0.5):
    """Bords de chaussée et de piste des routes hors jonction (changement de groupe de voie, du centre
    vers l'extérieur ; piste = voie biking non contiguë à la chaussée) et coupes de la jonction 100 aux
    extrémités des routes qui y aboutissent. Repère local (le .xodr est déjà en local)."""
    import xodr_echantillonne as X
    res = reseau_xodr()
    lignes = []
    for rid in sorted(res, key=int):
        r = res[rid]
        if r.jonction != "-1":
            continue
        for sec in r.sections:
            n = max(2, int(math.ceil((sec.s1 - sec.s) / pas)) + 1)
            s = np.linspace(sec.s, sec.s1, n)
            tb = r.t_bords(s, sec)
            for signe in (1, -1):
                ids = []
                k = signe
                while k in sec.voies:
                    ids.append(k)
                    k += signe
                groupes = []
                for i, lid in enumerate(ids):
                    t = sec.voies[lid].type
                    g = GROUPE_VOIE.get(t, "autre")
                    if t == "biking":
                        g = "chaussee" if (i > 0 and groupes[-1] == "chaussee") or (i == 0) else "piste"
                    groupes.append(g)
                for i in range(len(ids) - 1):
                    if groupes[i] != groupes[i + 1] and ("chaussee" in (groupes[i], groupes[i + 1])
                                                         or "piste" in (groupes[i], groupes[i + 1])):
                        x, y, _ = X.point_st(r, s, tb[ids[i]])
                        lignes.append((np.c_[x, y], {"src": "xodr_bord", "id": f"{rid}/{sec.s:g}/{ids[i]}"}))
        # coupe de jonction (TQ-SOL-014) : extrémité reliée à la jonction
        lk = r.xml.find("link")
        for el in (lk if lk is not None else []):
            if el.get("elementType") != "junction":
                continue
            s_j = r.longueur if el.tag == "successor" else 0.0
            sec = r.section(min(max(s_j, 0.0), r.longueur - 1e-6))
            tb = r.t_bords(np.array([s_j]), sec)
            ivs = []
            for lid, v in sec.voies.items():
                if lid == 0 or not (GROUPE_VOIE.get(v.type) == "chaussee" or v.type == "biking"):
                    continue
                inner = tb[lid - 1 if lid > 0 else lid + 1][0] if abs(lid) > 1 else tb[0][0]
                ivs.append(sorted((float(tb[lid][0]), float(inner))))
            ivs.sort()
            fus = []
            for iv in ivs:                               # intervalles de chaussée contigus (pas à travers un TPC)
                if fus and iv[0] <= fus[-1][1] + 0.05:
                    fus[-1][1] = max(fus[-1][1], iv[1])
                else:
                    fus.append(list(iv))
            for k_, (t0, t1) in enumerate(fus):
                tt = np.linspace(t0, t1, max(2, int((t1 - t0) / 0.5) + 1))
                x, y, _ = X.point_st(r, np.full(len(tt), s_j), tt)
                lignes.append((np.c_[x, y], {"src": "xodr_jonction", "id": f"{rid}@{s_j:g}/{k_}"}))
    return lignes


# --------------------------------------------------------------------------- carte d'indices
def carte_indices(K, emprises, arrieres, rampes_):
    """Carte des classes (codes CLASSES, 0,10 m) : indices sémantiques seulement."""
    sv = ctx.surfaces_v1()
    idx = ctx.carte_v1()
    codes_v1 = np.array([CODE.get(CORRECTIONS.get(i, {}).get("classe", p["classe"]), 0) for i, p, _ in sv] + [0],
                        dtype=np.int8)
    carte = codes_v1[np.where(idx >= 0, idx, len(sv))]
    proteges = np.isin(carte, [CODE["ilot"], CODE["terre_plein_vegetal"], CODE["batiment"]])
    # masque de chaussée 2026 (atelier relief) et voies OpenDRIVE circulées (état 2026)
    # le masque de l'atelier relief ne remplace que des classes circulées ou indéterminées (il déborde sur
    # des pistes et des trottoirs) ; les emprises 2026 des routes 1-6 viennent d'OpenDRIVE ci-dessous
    faible = np.isin(carte, [0, CODE["chaussee"], CODE["parking"], CODE["acces_riverain"], CODE["autre"]])
    carte[(ctx.carte_chaussee_2026() == 1) & ~proteges & faible] = CODE["chaussee"]
    route, typ = ctx.carte_xodr()
    carte[(typ == 1) & ~proteges] = CODE["chaussee"]
    jct = ctx.rasteriser([(1, polys) for r, v, t, s, j, polys in ctx.voies_xodr() if j and t in ctx.TYPES_CHAUSSEE], 0)
    carte[(jct == 1) & ~proteges] = CODE["chaussee"]
    # côtés des bordures de chaussée : côté bas circulé, côté haut piéton (bandes de 0,6 m)
    from commun import decaler
    bas, haut = [], []
    for f in K:
        p = f["properties"]
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        L = float(abscisses(P)[-1])
        s = np.arange(0.25, L, 0.5) if L > 0.5 else np.array([L / 2])
        q, tg = point_a(P, s)
        nrm = normale_gauche(tg)
        avant = ctx.echantillonner(carte, q - nrm * 0.5)
        if np.mean(np.isin(avant, [CODE["chaussee"]])) < 0.5:
            continue
        w = 0.6
        bas.append((1, [[np.vstack([P, decaler(P, -w)[::-1]])]]))
        Q = arrieres[p["id"]]
        haut.append((1, [[np.vstack([Q, decaler(Q, w)[::-1]])]]))
    mb = ctx.rasteriser(bas, 0) == 1
    mh = ctx.rasteriser(haut, 0) == 1
    carte[mb & ~np.isin(carte, [CODE[c] for c in VEHICULES | {"piste_cyclable"}]) & ~proteges] = CODE["chaussee"]
    carte[mh & np.isin(carte, [CODE[c] for c in VEHICULES])] = CODE["trottoir"]
    carte[ctx.rasteriser([(1, polys) for _, _, polys in ctx.batiments()], 0) == 1] = CODE["batiment"]
    if rampes_:
        carte[ctx.rasteriser([(1, [[r["anneau"]]]) for r in rampes_], 0) == 1] = CODE["trottoir"]
    # emprises de bordure : sans classe (couvertes par les lignes)
    carte[ctx.rasteriser([(1, [[e]]) for e in emprises.values()], 0) == 1] = 0
    return carte


# --------------------------------------------------------------------------- fermetures (résidus)
def _douglas(P, tol):
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    n = math.hypot(*ab)
    if n < 1e-12:
        d = np.hypot(*(P - a).T)
    else:
        d = np.abs((P[:, 0] - a[0]) * ab[1] - (P[:, 1] - a[1]) * ab[0]) / n
    i = int(np.argmax(d))
    if d[i] <= tol:
        return np.vstack([a, b])
    return np.vstack([_douglas(P[:i + 1], tol)[:-1], _douglas(P[i:], tol)])


def _chaikin(P, n=2):
    P = np.asarray(P, dtype=np.float64)
    for _ in range(n):
        if len(P) < 3:
            return P
        Q = [P[0]]
        for a, b in zip(P[:-1], P[1:]):
            Q += [0.75 * a + 0.25 * b, 0.25 * a + 0.75 * b]
        Q.append(P[-1])
        P = np.array(Q)
    return P


def _eroder(m, n):
    for _ in range(n):
        e = m.copy()
        e[1:, :] &= m[:-1, :]
        e[:-1, :] &= m[1:, :]
        e[:, 1:] &= m[:, :-1]
        e[:, :-1] &= m[:, 1:]
        m = e
    return m


def _dilater(m, n):
    for _ in range(n):
        e = m.copy()
        e[1:, :] |= m[:-1, :]
        e[:-1, :] |= m[1:, :]
        e[:, 1:] |= m[:, :-1]
        e[:, :-1] |= m[:, 1:]
        m = e
    return m


def fermetures(carte, lignes_vect, aretes_actives=None, elaguees=None):
    """Bords de la chaussée (masque binaire nettoyé de la carte d'indices) sans arête de partition à moins
    de COUVERT_M : polylignes simplifiées et accrochées (résidus signalés). Seul le bord de chaussée est
    fermé : il sépare deux niveaux (chaussée / trottoir, terre-plein, espace vert) ; les autres limites de
    classe sans ligne levée (limites raster v1, taches d'herbe) ne sont pas reprises (classe au vote,
    mélange signalé). La couverture
    est mesurée sur les arêtes ACTIVES d'une première partition (`aretes_actives`, segments (A, B)) :
    une ligne levée pendante (élaguée) ne ferme rien et ne couvre donc rien."""
    from PIL import Image, ImageDraw
    n, x0, y1 = ctx._grille()
    res = ctx.RES_CARTE
    # masque binaire de la chaussée (indices : OpenDRIVE, masque de chaussée 2026, côtés de bordure),
    # nettoyé par ouverture puis fermeture morphologiques (2 cellules) : groupe 1 = chaussée, 2 = reste
    m = carte == CODE["chaussee"]
    m = _dilater(_eroder(m, 2), 2)
    m = _eroder(_dilater(m, 2), 2)
    gm = np.where(m, 1, 2).astype(np.int8)
    gm[carte == 0] = 0
    # couverture des lignes vectorielles (tampon de COUVERT_M)
    img = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(img)
    lw = int(round(2 * COUVERT_M / res)) + 1
    couvrantes = ([np.vstack([a, b]) for a, b in zip(*aretes_actives)] if aretes_actives is not None
                  else [P for P, _ in lignes_vect])
    for P in couvrantes:
        pts = [((x - x0) / res - 0.5, (y1 - y) / res - 0.5) for x, y in P]
        if len(pts) >= 2:
            d.line(pts, fill=1, width=lw)
    couv = np.array(img, dtype=bool)
    # arêtes de pixels entre groupes différents (0 = sans indice : ignoré)
    aretes = {}
    paire = {}                                        # arête de pixels -> 1 si elle borde la chaussée
    h = (gm[:, :-1] != gm[:, 1:]) & (gm[:, :-1] > 0) & (gm[:, 1:] > 0) & ~(couv[:, :-1] | couv[:, 1:])
    r, c = np.nonzero(h)
    ch = ((gm[:, :-1] == 1) | (gm[:, 1:] == 1))[r, c]
    for rr, cc, cz in zip(r.tolist(), c.tolist(), ch.tolist()):
        a, b = (rr, cc + 1), (rr + 1, cc + 1)
        aretes.setdefault(a, []).append(b)
        aretes.setdefault(b, []).append(a)
        paire[(a, b)] = cz
    v = (gm[:-1, :] != gm[1:, :]) & (gm[:-1, :] > 0) & (gm[1:, :] > 0) & ~(couv[:-1, :] | couv[1:, :])
    r, c = np.nonzero(v)
    ch = ((gm[:-1, :] == 1) | (gm[1:, :] == 1))[r, c]
    for rr, cc, cz in zip(r.tolist(), c.tolist(), ch.tolist()):
        a, b = (rr + 1, cc), (rr + 1, cc + 1)
        aretes.setdefault(a, []).append(b)
        aretes.setdefault(b, []).append(a)
        paire[(a, b)] = cz
    # chaînage (coupure aux nœuds de degré ≠ 2)
    vu = set()
    chaines = []
    for depart in sorted(aretes):
        if len(aretes[depart]) == 2:
            continue
        for nxt in sorted(aretes[depart]):
            e = (min(depart, nxt), max(depart, nxt))
            if e in vu:
                continue
            ch = [depart]
            prev, cur = depart, nxt
            vu.add(e)
            while True:
                ch.append(cur)
                if len(aretes[cur]) != 2:
                    break
                a, b = aretes[cur]
                nn = b if a == prev else a
                e = (min(cur, nn), max(cur, nn))
                if e in vu:
                    break
                vu.add(e)
                prev, cur = cur, nn
            chaines.append((ch, False))
    for depart in sorted(aretes):                     # boucles fermées (tous les nœuds de degré 2)
        for nxt in sorted(aretes[depart]):
            e = (min(depart, nxt), max(depart, nxt))
            if e in vu:
                continue
            ch = [depart]
            prev, cur = depart, nxt
            vu.add(e)
            while cur != depart:
                ch.append(cur)
                a, b = aretes[cur]
                nn = b if a == prev else a
                vu.add((min(cur, nn), max(cur, nn)))
                prev, cur = cur, nn
            ch.append(depart)
            chaines.append((ch, True))
    if aretes_actives is not None:                    # accrochage sur les seules arêtes actives
        A, B = aretes_actives
    else:
        A = np.vstack([P[:-1] for P, _ in lignes_vect])
        B = np.vstack([P[1:] for P, _ in lignes_vect])
    # morceaux : extrémités accrochées (≤ 0,6 m d'une ligne vectorielle) ou partagées avec un autre morceau
    morceaux = []
    for ch, boucle in chaines:
        P = np.array([[x0 + cc * res, y1 - rr * res] for rr, cc in ch], dtype=np.float64)
        if boucle and abs(aire_signee(P[:-1])) < BOUCLE_MIN_M2:
            continue                                  # tache isolée (raster) : supprimée
        morceaux.append({"P": P, "boucle": boucle, "bouts": (ch[0], ch[-1]), "chaussee": True})
    ext = np.array([m["P"][i] for m in morceaux for i in (0, -1)]) if morceaux else np.zeros((0, 2))
    dd, _, pr = distance_segments(ext, A, B) if len(ext) else (np.zeros(0), None, np.zeros((0, 2)))
    for k, m in enumerate(morceaux):
        m["accroche"] = [(dd[2 * k] <= 0.6, pr[2 * k]), (dd[2 * k + 1] <= 0.6, pr[2 * k + 1])]
    # élagage itératif des morceaux pendants (une extrémité ni accrochée ni partagée)
    vivant = [True] * len(morceaux)
    while True:
        deg = collections.Counter()
        for k, m in enumerate(morceaux):
            if vivant[k] and not m["boucle"]:
                deg[m["bouts"][0]] += 1
                deg[m["bouts"][1]] += 1
        change = False
        for k, m in enumerate(morceaux):
            if not vivant[k] or m["boucle"]:
                continue
            for i in (0, 1):
                if not m["accroche"][i][0] and deg[m["bouts"][i]] < 2:
                    vivant[k] = False
                    change = True
                    break
        if not change:
            break
    out = []
    for k, m in enumerate(morceaux):
        if not vivant[k]:
            if elaguees is not None:
                elaguees.append(m["P"])
            continue
        Q = _chaikin(_douglas(m["P"], DP_FERMETURE_M), 2)
        if not m["boucle"]:
            if m["accroche"][0][0]:
                Q = np.vstack([m["accroche"][0][1], Q])
            if m["accroche"][1][0]:
                Q = np.vstack([Q, m["accroche"][1][1]])
        out.append((Q, {"src": "fermeture", "id": f"F{len(out):04d}", "boucle": bool(m["boucle"]), "bord_chaussee": m["chaussee"],
                        "longueur_m": float(abscisses(Q)[-1]), "ferme": bool(m["boucle"])}))
    return out


# --------------------------------------------------------------------------- partition
def preparer_lignes(K, rampes_, lignes_b, emprises):
    """Toutes les lignes de la partition, filtrées par priorité (TQ-SOL-001) et coupées au carré."""
    carre = ctx.anneau_site()
    lignes = [(np.vstack([carre, carre[:1]]), {"src": "emprise", "prolonger": False, "ferme": True})]
    for P, e in lignes_b:
        for c0, c1 in couper_polyligne(P, [carre]):
            lignes.append((sous_polyligne(P, c0, c1), e))
    for bid, _, polys in ctx.batiments():
        for p in polys:
            r = np.vstack([p[0], p[0][:1]])
            for c0, c1 in couper_polyligne(r, [carre]):
                lignes.append((sous_polyligne(r, c0, c1), {"src": "batiment", "id": bid}))
    zones = list(emprises.values())
    haut = lambda: (np.vstack([P[:-1] for P, _ in lignes]), np.vstack([P[1:] for P, _ in lignes]))
    for r in rampes_:
        for m in SP.filtrer_paralleles(r["contour"], haut(), dmax=0.03, zones=[]):
            lignes.append((m, {"src": "rampe", "id": r["id"]}))
    ref = haut()
    for P, e in lignes_xodr():
        for c0, c1 in couper_polyligne(P, [carre]):
            for m in SP.filtrer_paralleles(sous_polyligne(P, c0, c1), ref,
                                           dmax=FILTRE_XODR_M if e["src"] == "xodr_bord" else 0.05,
                                           zones=zones, lmin=0.5):
                lignes.append((m, e))
    for calque in ("limite_revetement", "vegetation", "talus_haut", "talus_bas"):
        ref = haut()
        for i, P in ctx.gam_lignes(calque):
            for c0, c1 in couper_polyligne(P, [carre]):
                for m in SP.filtrer_paralleles(sous_polyligne(P, c0, c1), ref, zones=zones):
                    lignes.append((m, {"src": calque, "id": int(i)}))
    # aires de stationnement OSM : limites parking / espace vert des grands îlots privés sans levé GAM
    # (moins précises : retirées à moins de 0,6 m d'une limite déjà présente, TQ-SOL-001)
    ref = haut()
    for oid, P in ctx.parkings_osm():
        r = np.vstack([P, P[:1]])
        for c0, c1 in couper_polyligne(r, [carre]):
            for m in SP.filtrer_paralleles(sous_polyligne(r, c0, c1), ref, dmax=0.6, cos_min=0.9, zones=zones, lmin=0.5):
                lignes.append((m, {"src": "osm_parking", "id": oid}))
    return lignes


def _chainer(aretes):
    """Arêtes de pixels {nœud: [voisins]} -> [(liste de nœuds, boucle)] coupées aux nœuds de degré ≠ 2."""
    vu = set()
    chaines = []
    for depart in sorted(aretes):
        if len(aretes[depart]) == 2:
            continue
        for nxt in sorted(aretes[depart]):
            e = (min(depart, nxt), max(depart, nxt))
            if e in vu:
                continue
            ch = [depart]
            prev, cur = depart, nxt
            vu.add(e)
            while True:
                ch.append(cur)
                if len(aretes[cur]) != 2:
                    break
                a, b = aretes[cur]
                nn = b if a == prev else a
                e = (min(cur, nn), max(cur, nn))
                if e in vu:
                    break
                vu.add(e)
                prev, cur = cur, nn
            chaines.append((ch, False))
    for depart in sorted(aretes):
        for nxt in sorted(aretes[depart]):
            e = (min(depart, nxt), max(depart, nxt))
            if e in vu:
                continue
            ch = [depart]
            prev, cur = depart, nxt
            vu.add(e)
            while cur != depart:
                ch.append(cur)
                a, b = aretes[cur]
                nn = b if a == prev else a
                vu.add((min(cur, nn), max(cur, nn)))
                prev, cur = cur, nn
            ch.append(depart)
            chaines.append((ch, True))
    return chaines


def _masque_classes(carte, classes):
    m = np.isin(carte, [CODE[c] for c in classes])
    m = _dilater(_eroder(m, 2), 2)
    return _eroder(_dilater(m, 2), 2)


def fermetures_faces(arr, carte, n0=0, seuil_aire=20.0, part_min=0.03, classes=("chaussee",), dp=None, nature="chaussee"):
    """Bords de chaussée DANS une face qui mêle chaussée et autre chose (masque exact de la face) :
    la limite de chaussée de la carte d'indices (masque binaire nettoyé) est chaînée, simplifiée
    (Douglas-Peucker 0,25 m, Chaikin) et accrochée au bord de la face (≤ 0,6 m) ; morceaux pendants
    élagués. Résidus signalés (`fermeture`) : aucune autre source ne sépare ces niveaux."""
    res = ctx.RES_CARTE
    m = _masque_classes(carte, classes)
    gm = np.where(m, 1, 2).astype(np.int8)
    gm[(carte == 0) | (carte == CODE["batiment"])] = 0
    dp = DP_FERMETURE_M if dp is None else dp
    out = []
    for k, f in enumerate(arr["faces"]):
        if f["aire"] < seuil_aire:
            continue
        ext = f["anneaux"][0]
        x0f, y0f = ext.min(axis=0)
        x1f, y1f = ext.max(axis=0)
        c0 = max(0, int(math.floor((x0f + ctx.DEMI) / res)) - 1)
        c1 = min(gm.shape[1], int(math.ceil((x1f + ctx.DEMI) / res)) + 1)
        r0 = max(0, int(math.floor((ctx.DEMI - y1f) / res)) - 1)
        r1 = min(gm.shape[0], int(math.ceil((ctx.DEMI - y0f) / res)) + 1)
        sx0, sy1 = -ctx.DEMI + c0 * res, ctx.DEMI - r0 * res
        mk = SP.masque_face(f["anneaux"], sx0, sy1, res, c1 - c0, r1 - r0)
        g = gm[r0:r1, c0:c1]
        val = g[mk & (g > 0)]
        if len(val) == 0:
            continue
        part = float(np.mean(val == 1))
        if part < part_min or part > 1.0 - part_min:
            continue
        A = np.vstack(f["anneaux"])
        B = np.vstack([np.roll(r, -1, axis=0) for r in f["anneaux"]])
        aretes = {}
        h = (g[:, :-1] != g[:, 1:]) & (g[:, :-1] > 0) & (g[:, 1:] > 0) & mk[:, :-1] & mk[:, 1:]
        v = (g[:-1, :] != g[1:, :]) & (g[:-1, :] > 0) & (g[1:, :] > 0) & mk[:-1, :] & mk[1:, :]
        cand = []
        r_, c_ = np.nonzero(h)
        cand += [((rr, cc + 1), (rr + 1, cc + 1)) for rr, cc in zip(r_.tolist(), c_.tolist())]
        r_, c_ = np.nonzero(v)
        cand += [((rr + 1, cc), (rr + 1, cc + 1)) for rr, cc in zip(r_.tolist(), c_.tolist())]
        if not cand:
            continue
        mil = np.array([[sx0 + 0.5 * (a_[1] + b_[1]) * res, sy1 - 0.5 * (a_[0] + b_[0]) * res] for a_, b_ in cand])
        dd, _, _ = distance_segments(mil, A, B)
        for (a_, b_), d_ in zip(cand, dd):
            if d_ <= 0.12:
                continue                              # limite déjà portée par le bord de la face
            aretes.setdefault(a_, []).append(b_)
            aretes.setdefault(b_, []).append(a_)
        morceaux = []
        for ch, boucle in _chainer(aretes):
            P = np.array([[sx0 + cc * res, sy1 - rr * res] for rr, cc in ch], dtype=np.float64)
            if boucle and abs(aire_signee(P[:-1])) < BOUCLE_MIN_M2:
                continue
            morceaux.append({"P": P, "boucle": boucle, "bouts": (ch[0], ch[-1])})
        if not morceaux:
            continue
        ext_pts = np.array([mm["P"][i] for mm in morceaux for i in (0, -1)])
        de, _, pr = distance_segments(ext_pts, A, B)
        for i, mm in enumerate(morceaux):
            mm["accroche"] = [(de[2 * i] <= 0.6, pr[2 * i]), (de[2 * i + 1] <= 0.6, pr[2 * i + 1])]
        vivant = [True] * len(morceaux)
        while True:
            deg = collections.Counter()
            for i, mm in enumerate(morceaux):
                if vivant[i] and not mm["boucle"]:
                    deg[mm["bouts"][0]] += 1
                    deg[mm["bouts"][1]] += 1
            change = False
            for i, mm in enumerate(morceaux):
                if not vivant[i] or mm["boucle"]:
                    continue
                for j in (0, 1):
                    if not mm["accroche"][j][0] and deg[mm["bouts"][j]] < 2:
                        vivant[i] = False
                        change = True
                        break
            if not change:
                break
        for i, mm in enumerate(morceaux):
            if not vivant[i]:
                continue
            Q = _chaikin(_douglas(mm["P"], dp), 2)
            if not mm["boucle"]:
                if mm["accroche"][0][0]:
                    Q = np.vstack([mm["accroche"][0][1], Q])
                if mm["accroche"][1][0]:
                    Q = np.vstack([Q, mm["accroche"][1][1]])
            out.append((Q, {"src": "fermeture", "id": f"F{n0 + len(out):04d}", "boucle": bool(mm["boucle"]),
                            "longueur_m": float(abscisses(Q)[-1]), "ferme": bool(mm["boucle"]), "face": k,
                            "nature": nature}))
    return out


def _actives(arr, lignes):
    """Segments actifs (A, B) d'un arrangement et groupes de lignes de chaque arête."""
    N = arr["noeuds"]
    cles = sorted(arr["aretes"])
    A = N[[a for a, _ in cles]]
    B = N[[b for _, b in cles]]
    groupes = [{lignes[l][1].get("groupe") for l in arr["aretes"][c]} - {None} for c in cles]
    return (A, B), groupes


def construire_partition(K, mnt):
    """Partition complète : (arrangement, lignes, emprises, arrières, rampes, carte, fermetures,
    bordures synthétiques des ponts). Passes : 1) lignes vectorielles ; 2) ponts entre bouts de
    bordure alignés (sol_lacunes) et fermetures des bouts libres ; 3) bords de chaussée sans ligne
    (résidus signalés) ; partition finale."""
    import sol_lacunes as LA
    import regulariser as RGQ                          # GQ-* : limites régularisées (regles_qualite_geometrique)
    lignes_b, emprises, arrieres = lignes_bordures(K)
    rampes_ = rampes(K, arrieres)
    lignes = RGQ.lignes_partition(preparer_lignes(K, rampes_, lignes_b, emprises))
    arr1 = SP.arrangement(lignes)
    libres = LA.bouts_libres(arr1, lignes)
    act, grp = _actives(arr1, lignes)
    paires = LA.ponts(libres, K, act)
    ajouts = []
    for k, (amont, aval, P) in enumerate(sorted(paires, key=lambda x: (x[0][0], x[1][0]))):
        ajouts.append(LA.bordure_pont(f"K-95{k:02d}" if k < 100 else f"K-9{500 + k}", P, amont, aval, K, mnt))
    if ajouts:
        lb2, em2, ar2 = lignes_bordures(ajouts)
        emprises.update(em2)
        arrieres.update(ar2)
        lignes += lb2
    relies = {(a[0], a[1]) for a, b, _ in paires} | {(b[0], b[1]) for a, b, _ in paires}
    restants = [x for x in libres if (x[0], x[1]) not in relies]
    lignes += LA.fermetures_bouts(restants, act, grp)
    carte = carte_indices(K + ajouts, emprises, arrieres, rampes_)
    ferm = []
    arr = SP.arrangement(lignes)
    for _ in range(2):                                # bords de chaussée dans les faces mêlées
        f2 = RGQ.lignes_partition(fermetures_faces(arr, carte, n0=len(ferm)))
        if not f2:
            break
        ferm += f2
        lignes += f2
        arr = SP.arrangement(lignes)
    # Les limites espace vert / revêtu sans ligne levée ne sont PAS reprises de la carte d'indices : elles
    # suivaient les classes raster v1 (ombres d'arbres, chantier 2022) ; la face garde la classe majoritaire
    # et son mélange est signalé (`melange`, `purete_classe`).
    return arr, lignes, emprises, arrieres, rampes_, carte, ferm, ajouts, restants


# --------------------------------------------------------------------------- faces
def aretes_faces(arr):
    """{arête (u, v): [faces]} et, par face, la longueur de bord par source."""
    par = collections.defaultdict(list)
    for k, f in enumerate(arr["faces"]):
        for cyc in f["aretes"]:
            for u, v in cyc:
                par[(min(u, v), max(u, v))].append(k)
    return par


@functools.lru_cache(maxsize=1)
def _signalisation_gam():
    """Levé GAM 2026 de la signalisation horizontale (polylignes : contours de lignes, bandes, flèches) en segments
    locaux, et blocs SYMBOLE_VELO : preuve forte de revêtement (revues du 11/10/2026 : lignes GAM posées sur des faces
    classées espace vert)."""
    from commun import VECTEURS, lire_geojson, repere as rp
    A, B = [], []
    for f in lire_geojson(VECTEURS / "etat_2026/signalisation_horizontale_lin_L93.geojson"):
        g = f["geometry"]
        cs = [g["coordinates"]] if g["type"] == "LineString" else (g["coordinates"] if g["type"] == "MultiLineString" else [])
        for c in cs:
            P = rp(np.asarray(c, float)[:, :2])
            if len(P) >= 2:
                A.append(P[:-1])
                B.append(P[1:])
    velos = []
    for f in lire_geojson(VECTEURS / "etat_2026/signalisation_horizontale_pct_L93.geojson"):
        g = f["geometry"]
        if "VELO" in str(f["properties"].get("bloc") or "").upper() and g["type"] in ("Point", "MultiPoint"):
            c = np.atleast_2d(np.asarray(g["coordinates"], float))[:, :2]
            velos += list(rp(c))
    return (np.vstack(A) if A else np.zeros((0, 2)), np.vstack(B) if B else np.zeros((0, 2)),
            np.array(velos) if velos else np.zeros((0, 2)))


def part_signalisation_gam(Q, dmax=2.0):
    """Part des échantillons Q d'une face à ≤ dmax m d'une marque levée GAM 2026, et présence d'un vélo GAM (≤ 3 m)."""
    A, B, V = _signalisation_gam()
    if not len(Q) or not len(A):
        return 0.0, False
    lo, hi = Q.min(axis=0) - dmax, Q.max(axis=0) + dmax
    m = ((A >= lo) & (A <= hi)).all(axis=1) | ((B >= lo) & (B <= hi)).all(axis=1)
    if not m.any():
        return 0.0, False
    d, _, _ = distance_segments(Q, A[m], B[m])
    velo = bool(len(V)) and bool(((V[:, 0] >= lo[0] - 1) & (V[:, 0] <= hi[0] + 1) & (V[:, 1] >= lo[1] - 1)
                                  & (V[:, 1] <= hi[1] + 1)).any())
    return float((d <= dmax).mean()), velo


def construire(mnt, K):
    """Surfaces du site complet : (features, partition pour le nivellement, rapport)."""
    arr, lignes, emprises, arrieres, rampes_, carte, ferm, ajouts, ouverts = construire_partition(K, mnt)
    K = K + ajouts
    N = arr["noeuds"]
    voisins = aretes_faces(arr)
    src_ligne = [e["src"] for _, e in lignes]
    id_ligne = [e.get("id") for _, e in lignes]
    sv = ctx.surfaces_v1()
    bats = ctx.batiments()
    faces = arr["faces"]
    ids_emp = sorted(emprises)
    bb_emp = np.array([[emprises[k][:, 0].min() - 0.01, emprises[k][:, 1].min() - 0.01,
                        emprises[k][:, 0].max() + 0.01, emprises[k][:, 1].max() + 0.01] for k in ids_emp])
    info = []
    for k, f in enumerate(faces):
        pi = SP.point_interieur(f["anneaux"])
        # bâtiment ?
        bat = next((bid for bid, _, polys in bats if any(dans_polygone(pi[None], p)[0] for p in polys)), None)
        # emprise de bordure ?
        kid = None
        cand = np.nonzero((bb_emp[:, 0] <= pi[0]) & (pi[0] <= bb_emp[:, 2]) & (bb_emp[:, 1] <= pi[1]) & (pi[1] <= bb_emp[:, 3]))[0]
        for c_ in cand:
            if dans_polygone(pi[None], [emprises[ids_emp[c_]]])[0]:
                kid = ids_emp[c_]
                break
        ramp = next((r for r in rampes_ if dans_polygone(pi[None], [r["anneau"]])[0]), None)
        Q = SP.echantillons(f["anneaux"], 0.25, 3000)
        cl = ctx.echantillonner(carte, Q, 0)
        cnt = collections.Counter(int(c) for c in cl if c > 0)
        iv1 = ctx.v1_sous(Q)
        cnt_v1 = collections.Counter(int(i) for i in iv1 if i >= 0)
        # longueur de bord par source et bords de bordure
        bords_src = collections.Counter()
        bords_k = collections.Counter()
        for cyc in f["aretes"]:
            for u, v in cyc:
                ls = arr["aretes"].get((min(u, v), max(u, v)), set())
                if not ls:
                    continue
                lg = float(np.hypot(*(N[u] - N[v])))
                l0 = min(ls, key=lambda l: (PRIORITE.get(src_ligne[l], 9), l))
                bords_src[src_ligne[l0]] += lg
                for l in ls:
                    if src_ligne[l] in ("bordure_avant", "bordure_arriere"):
                        bords_k[(id_ligne[l], "avant" if src_ligne[l] == "bordure_avant" else "arriere")] += lg
        frac_gam, velo_gam = part_signalisation_gam(Q)
        info.append({"k": k, "pi": pi, "bat": bat, "kid": kid, "rampe": ramp, "cnt": cnt, "cnt_v1": cnt_v1,
                     "bords_src": bords_src, "bords_k": bords_k, "n_ech": len(Q), "frac_gam": frac_gam, "velo_gam": velo_gam})
    feats, rapport = [], collections.Counter()
    noms = collections.defaultdict(list)
    for it in info:
        f = faces[it["k"]]
        if it["bat"] is not None:
            rapport["batiment_trou"] += 1
            continue
        if f["aire"] < 1e-4:
            continue
        if it["kid"]:
            classe = "emprise_bordure"
        elif it["rampe"] is not None:
            classe = "trottoir"
        elif it["cnt"]:
            classe = CLASSES[max(it["cnt"].items(), key=lambda kv: (kv[1], -kv[0]))[0]]
            if classe == "batiment":
                classe = "autre"
        else:
            classe = "autre"
        tot = sum(it["cnt"].values()) or 1
        purete = (it["cnt"].get(CODE.get(classe, -1), 0) / tot) if classe in CODE else 1.0
        iv = max(it["cnt_v1"].items(), key=lambda kv: (kv[1], -kv[0]))[0] if it["cnt_v1"] else None
        it.update(classe=classe, purete=purete, iv=iv)
        cle = ("B", it["kid"]) if it["kid"] else ("V", sv[iv][0] if iv is not None else None)
        noms[cle].append(it)
    # identifiants stables
    n9 = 0
    for cle in sorted(noms, key=lambda c: (c[0], c[1] or "")):
        its = sorted(noms[cle], key=lambda i: (-round(faces[i["k"]]["aire"], 3), round(float(i["pi"][0]), 3), round(float(i["pi"][1]), 3)))
        for j, it in enumerate(its):
            if cle[0] == "B":
                it["id"] = f"S-B{cle[1][2:]}" + ("" if j == 0 else f"-{j + 1}")
            elif cle[1] is None:
                it["id"] = None
            else:
                suf = "" if len(its) == 1 else _suffixe(j)
                it["id"] = f"S-{cle[1][5:]}{suf}"
    sans = sorted([it for it in info if "classe" in it and it.get("id") is None],
                  key=lambda i: (round(float(i["pi"][0]), 2), round(float(i["pi"][1]), 2)))
    for j, it in enumerate(sans):
        it["id"] = f"S-9{j:03d}"
    fil = {f["properties"]["id"]: float(np.median([c[2] for c in f["geometry"]["coordinates"]])) for f in K}
    for it in info:
        if "classe" not in it:
            continue
        f = faces[it["k"]]
        classe = it["classe"]
        p_v1 = sv[it["iv"]][1] if it["iv"] is not None else None
        sid_v1 = sv[it["iv"]][0] if it["iv"] is not None else ""
        corr = CORRECTIONS.get(sid_v1, {}) if classe != "emprise_bordure" else {}
        classe = corr.get("classe", classe)
        preuve_gam = None
        # MQ-DET-010 / TQ-SOL-001 (revues du 11/10/2026) : une face plantée dont la moitié au moins de l'aire est à
        # ≤ 2 m d'une marque levée GAM 2026 est revêtue (les marques ne se peignent pas sur le gazon) : piste cyclable
        # si un vélo GAM y est levé, sinon chaussée
        if classe in ("espace_vert", "terre_plein_vegetal") and "classe" not in corr and it.get("frac_gam", 0.0) >= 0.5:
            preuve_gam = (classe, round(it["frac_gam"], 3))
            classe = "piste_cyclable" if it.get("velo_gam") else "chaussee"
            rapport["reclassee_par_marques_gam"] += 1
        mid = None
        if corr.get("materiau_id"):
            mid = corr["materiau_id"]
            prov_rev = {"src": f"constat:{corr['constat']}", "ref": corr["note"][:160], "conf": "moyenne"}
        elif p_v1 is not None and classe == p_v1["classe"]:
            mid = materiau_v1(classe, p_v1)
            prov_rev = {"src": "a_priori:correspondance_materiau_v1",
                        "ref": f"v1 {sid_v1} {p_v1['classe']}/{p_v1['materiau']}/{p_v1['etat']} -> {mid}", "conf": "faible"}
        if mid is None:
            mid = DEFAUT_CLASSE.get(classe, "stabilise_beige")
            if classe in ("chaussee", "parking", "acces_riverain") and p_v1 is not None and p_v1["etat"] == "modifie_2025":
                mid = "enrobe_bbsg_neuf_2025"
            prov_rev = {"src": "a_priori:revetement_par_defaut_classe",
                        "ref": f"classe {classe} (indice v1 {sid_v1 or 'absent'} {p_v1['classe'] + '/' + p_v1['materiau'] if p_v1 else ''}) -> {mid}",
                        "conf": "faible"}
        if classe == "emprise_bordure":
            prov_rev = {"src": "regle:bordures.profils", "ref": f"sol sous la bordure {it['kid']} (caché par l'élément)", "conf": "haute"}
        ring0 = f["anneaux"]
        if mid in ("brf_bois_concasse", "gazon_tondu", "herbe_haute", "terre_nue") and "materiau_id" not in corr                 and classe in ("espace_vert", "terre_plein_vegetal"):
            bk = [kk for (kk, cote) in it["bords_k"] if kk in fil]
            if bk:
                zmed = float(np.median(mnt(*(repere(SP.echantillons(ring0, 0.5, 400), "l93").T))))
                dzf = zmed - float(np.median([fil[kk] for kk in bk]))
                if dzf < NOUE_DZ and f["aire"] >= NOUE_AIRE:
                    mid = "noue_plantee"
                    prov_rev = {"src": "a_priori:massif_2025_en_creux_noue",
                                "ref": f"espace planté à {dzf:+.2f} m sous le fil d'eau des bordures voisines : noue (constat hist-16 : noue SE de 152 m²) ; talus à 1/3 (GA-ASS-005)",
                                "conf": "faible"}
        age, sal = AGE.get(p_v1["etat"], ("inconnu", 0.4)) if p_v1 else ("inconnu", 0.4)
        rev = {"materiau_id": mid, "age": age, "salissure": sal}
        rev.update(APPAREILLAGE.get(mid, {}))
        lim = {k: round(v, 3) for k, v in sorted(it["bords_src"].items())}
        ferm_m = float(it["bords_src"].get("fermeture", 0.0))
        tot = sum(it["cnt"].values()) or 1
        melange = {CLASSES[c]: round(n / tot, 3) for c, n in sorted(it["cnt"].items())} if it["purete"] < 0.9 else None
        src_geo = "gam" if lim.get("bordure_avant", 0) + lim.get("bordure_arriere", 0) + lim.get("limite_revetement", 0) > 0.5 * sum(lim.values()) else "a_priori:partition_vectorielle_site"
        prov = {
            "geometrie": {"src": src_geo,
                          "ref": "partition vectorielle : " + ", ".join(f"{k} {v:.1f} m" for k, v in lim.items())[:280],
                          "conf": "haute" if ferm_m < 0.5 and src_geo == "gam" else ("moyenne" if ferm_m < 5 else "faible")},
            "classe": ({"src": "gam", "ref": f"marques levées GAM 2026 sur {preuve_gam[1]:.0%} de la face (classe votée "
                                             f"{preuve_gam[0]}) : surface revêtue (MQ-DET-010, TQ-SOL-001)", "conf": "moyenne"}
                       if preuve_gam else
                       {"src": f"constat:{corr['constat']}", "ref": corr.get("note", "")[:160], "conf": "moyenne"} if "classe" in corr else
                       {"src": "regle:bordures.profils" if classe == "emprise_bordure" else "a_priori:vote_indices_classe",
                        "ref": (f"emprise de {it['kid']}" if classe == "emprise_bordure" else
                                f"vote sur {it['n_ech']} points (v1, chaussée 2026, OpenDRIVE, côtés de bordure) : pureté {it['purete']:.2f}"),
                        "conf": "haute" if classe == "emprise_bordure" else ("moyenne" if it["purete"] >= 0.8 else "faible")}),
            "revetement": prov_rev,
            "niveau": {"src": "regle:regles_conception.TQ-SOL-013", "ref": "modèle de nivellement unique (nivellement.json)", "conf": "moyenne"},
        }
        props = {
            "id": it["id"], "famille": "surfaces", "classe": classe, "sous_classe": corr.get("sous_classe"),
            "revetement": rev,
            "niveau": {"ref": "nivellement_2026", "z_med_ngf": 216.3},
            "bords": [{"bordure": kk, "cote": cote, "longueur_m": round(lg, 3)}
                      for (kk, cote), lg in sorted(it["bords_k"].items()) if lg >= 0.25],
            "ilots": [], "limite_raster": ferm_m >= 0.25, "aire_m2": f["aire"], "lien_v1": sid_v1,
            "etat_v1": p_v1["etat"] if p_v1 else None,
            "limites_m": lim, "fermetures_m": round(ferm_m, 3), "purete_classe": round(it["purete"], 3),
            "prov": prov,
        }
        if melange:
            props["melange"] = melange
        if it["kid"]:
            props["bordure"] = it["kid"]
        if it["rampe"] is not None:
            r = it["rampe"]
            props["sous_classe"] = "rampe_charretiere" if r["type"] == "charretiere" else "rampe_abaisse"
            props["rampe"] = {"id": r["id"], "bordure": r["bordure"], "abaisse": r["abaisse"], "s0": r["s0"], "s1": r["s1"],
                              "profondeur_m": r["profondeur_m"], "pente_pct": r["pente_pct"], "denivele_m": r["denivele_m"],
                              "regles": r["regles"]}
            prov["geometrie"] = {"src": f"regle:regles_conception.{r['regles'][0]}",
                                 "ref": f"plan incliné derrière {r['abaisse']} : profondeur {r['profondeur_m']:.2f} m, pente {r['pente_pct']:.1f} %",
                                 "conf": "moyenne"}
        if corr.get("arasement"):
            props["niveau"]["arasement"] = {"motif": corr["arasement"], "preuve": corr["preuve_niveau"]}
        feats.append({"type": "Feature", "geometry": geom_polygones([[repere(r, "l93") for r in f["anneaux"]]]),
                      "properties": arrondi(props), "_k": it["k"]})
        rapport[classe] += 1
    feats.sort(key=lambda f: f["properties"]["id"])
    partition = {"arrangement": arr, "lignes": lignes, "emprises": emprises, "arrieres": arrieres,
                 "rampes": rampes_, "carte": carte, "fermetures": ferm, "bordures_ajoutees": ajouts,
                 "bouts_ouverts": sorted({(k, b) for k, b, _ in ouverts}),
                 "face_id": {f["_k"]: f["properties"]["id"] for f in feats}}
    for f in feats:
        del f["_k"]
    st = dict(arr["stats"])
    st["fermetures"] = len(ferm)
    st["fermetures_m"] = round(sum(e["longueur_m"] for _, e in ferm), 1)
    st["rampes"] = len(rampes_)
    st["ponts_bordure"] = len(ajouts)
    st["fermetures_bouts"] = sum(1 for _, e in lignes if e["src"] == "fermeture_bout")
    return feats, partition, {"classes": dict(sorted(rapport.items())), "partition": st}


def _suffixe(j):
    a = "abcdefghijklmnopqrstuvwxyz"
    return a[j] if j < 26 else a[j // 26 - 1] + a[j % 26]


def completer_bords(feats, bordures_feats):
    """Compatibilité 0.2 : bords déjà calculés par la partition (rien à faire)."""
    return None
