"""Famille `ilots` de la description v2 (site complet, schéma 0.3) : îlots, terre-pleins et massifs bordés,
avec remplissage (matériau, épaisseur, retrait sous le dessus de bordure), ceinture de bordures,
nez, objets portés et plantations.

Géométrie : anneau fermé (ou presque) d'une bordure dédoublonnée, sinon polygone v1. L'anneau est
l'arête avant de la ceinture ; le remplissage commence à `retrait_bordure_m` (largeur du profil)
à l'intérieur et affleure `retrait_sous_bordure_m` sous le dessus de bordure.
Une lacune de ceinture sans autre bordure (ex. TPC NE, 3,3 m non levés au GAM) est fermée par une
bordure de raccord synthétique (suffixe « z », a_priori:fermeture_ceinture_ilot).
"""
import collections

import numpy as np

import sol_site as ctx
from surfaces import CORRECTIONS
from commun import (abscisses, aire_signee, arrondi, coords_geojson, couper_polygone, dans_polygone,
                    densifier, distance_segments, echantillons_interieurs, geom_polygones,
                    lire_json, normale_gauche, point_a, rayon_courbure, repere, SPECS)

FERMETURE_MAX = 4.0        # lacune d'anneau acceptée (m)
RECALAGE_MAX = 0.8         # recalage d'un contour v1 sur l'arête avant des bordures (m)
REMPLISSAGES = {
    "brf_bois_concasse": {"epaisseur_m": 0.08, "retrait_sous_bordure_m": 0.04, "granulometrie_mm": [20, 50],
                          "bombement_m": 0.02, "debordement": {"largeur_m": 0.30, "densite": 0.15},
                          "teinte": "brun_roux_grisaillant"},
    # îlots du Vercors : pierres concassées sombres et grossières entre bordures claires (Panoramax
    # 2025-01-12 a1ff r01_c00, constat p2025_01_vercors-26 ; revue réalisme r2) ; retrait au milieu de la
    # plage 3-5 cm (revue conformité r2)
    "gravier_concasse_6_10": {"epaisseur_m": 0.06, "retrait_sous_bordure_m": 0.04, "granulometrie_mm": [10, 20],
                              "bombement_m": 0.01, "debordement": {"largeur_m": 0.20, "densite": 0.10},
                              "teinte": "gris_fonce"},
    "beton_balaye": {"epaisseur_m": 0.12, "retrait_sous_bordure_m": 0.0, "bombement_m": 0.0, "debordement": None},
    "enrobe_trottoir": {"epaisseur_m": 0.04, "retrait_sous_bordure_m": 0.0, "bombement_m": 0.0, "debordement": None},
    "gazon_tondu": {"epaisseur_m": 0.10, "retrait_sous_bordure_m": 0.03, "bombement_m": 0.02, "debordement": None},
}
# Remplissages imposés : constat (îlots du Vercors gravillonnés) ou choix a priori de la zone pilote
CHOIX = [
    # (v1 lié, ou anneau K-…, materiau_id, src, ref, conf, rôle)
    ("K-0390", "gravier_concasse_6_10", "constat:coeur-31",
     "petit îlot du Vercors gravillonné, bordures béton claires, feu à la pointe (ortho 2022 ; p2025_01_vercors-26 le 12/01/2025) ; îlot refait en 2025, remplissage reconduit ; concassé sombre 10/20 (panoramax:2025-01-12 a1ff r01_c00)",
     "faible", "ilot_separateur"),
    ("K-0629", "gravier_concasse_6_10", "constat:p2025_01_vercors-26",
     "îlot effilé du Vercors gravillonné d'un seul tenant (12/01/2025, a1ff r01_c00 ; coeur-31) ; îlot refait en 2025 (plan projet), remplissage reconduit ; concassé sombre 10/20 (panoramax:2025-01-12 a1ff r01_c00)",
     "faible", "ilot_separateur"),
    ("surf_0297", "brf_bois_concasse", "photo_utilisateur",
     "massif planté de 2025 (goutte NE, terre et herbe avant travaux : coeur-31) ; paillage bois BRF d'après la photo de référence de l'utilisateur (images/2.png) : choix a priori, pas une observation du site",
     "faible", "massif_goutte"),
    ("K-0386", "enrobe_trottoir", "constat:p2025_05_360-06",
     "TPC NE : bordures béton, dessus en enrobé sombre avec des herbes, mât de feu au SO, balise J5 au nez (18/05/2025, 9834 r01_c01-c02, revu sur la tuile r01_c01) ; bordure 386 déjà mesurée au LiDAR 2021, conservée",
     "moyenne", "terre_plein_central"),
]


def anneaux_bordures(bordures):
    """Bordures dont les extrémités se rejoignent (≤ FERMETURE_MAX) : [(kid, anneau local, lacune)]."""
    ext = {}
    for f in bordures:
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        ext[f["properties"]["id"]] = P
    out = []
    coupees = {f["properties"]["id"] for f in bordures
               if f["properties"]["coupe_zone"]["debut"] or f["properties"]["coupe_zone"]["fin"]}
    for kid, P in ext.items():
        if kid in coupees:
            continue                                    # anneau tronqué par la zone pilote
        L = abscisses(P)[-1]
        gap = float(np.hypot(*(P[-1] - P[0])))
        if L < 4.0 or gap > FERMETURE_MAX or aire_signee(P) <= 1.0:
            continue
        # lacune comblée par une autre bordure : au moins la moitié de la corde longée (≤ 0,6 m ; 0,3 m avant la
        # revue du 11/10/2026 : K-0628z doublait K-0400 à 0,35 m, GA-ILO-003 / GQ-TOP-004) par elle (une bordure qui ne
        # fait qu'aboutir près de la corde, ex. le bateau K-0389 contre I-0629, ne ferme pas l'anneau)
        comblee = False
        if gap > 0.3:
            corde = np.linspace(P[-1], P[0], 9)
            for k2, P2 in ext.items():
                if k2 == kid:
                    continue
                d, jj, _ = distance_segments(corde, P2[:-1], P2[1:])
                if (d <= 0.3).mean() >= 0.5:
                    comblee = True
                elif (d <= 0.6).mean() >= 0.5:                   # 0,3-0,6 m : seulement une bordure PARALLÈLE à la corde
                    u = (P[0] - P[-1]) / max(float(np.hypot(*(P[0] - P[-1]))), 1e-9)
                    sg = P2[1:] - P2[:-1]
                    sg = sg / np.maximum(np.hypot(*sg.T), 1e-9)[:, None]
                    if float(np.mean(np.abs(sg[jj[d <= 0.6]] @ u))) >= 0.9:
                        comblee = True
        out.append((kid, P[:-1] if gap < 1e-6 else P, 0.0 if gap < 0.3 or comblee else gap))
    return out


def lien_v1(poly):
    Q = echantillons_interieurs(poly, 0.5)
    cpt = collections.Counter()
    for sid, p, polys in ctx.surfaces_v1():
        for pp in polys:
            cpt[(sid, p["classe"], p["materiau"], p["etat"])] += int(dans_polygone(Q, pp).sum())
    cpt = {k: v for k, v in cpt.items() if v > 0}
    if not cpt:
        return None
    return max(cpt.items(), key=lambda kv: (kv[1], kv[0][0]))[0]


def nez(poly):
    """Rayon du nez : plus petit rayon de courbure aux sommets convexes de l'anneau (≥ R 0,25)."""
    r = np.vstack([poly, poly[:1]])
    L = abscisses(r)[-1]
    s = np.arange(0.0, L, 0.25)
    R = rayon_courbure(r, s, h=0.5)
    q, tg = point_a(r, s)
    q2, tg2 = point_a(r, np.clip(s + 0.3, 0, L))
    convexe = (tg[:, 0] * tg2[:, 1] - tg[:, 1] * tg2[:, 0]) > 0
    if not convexe.any():
        return None
    i = int(np.argmin(np.where(convexe, R, np.inf)))
    return {"rayon_m": float(max(0.25, R[i])), "position": coords_geojson(repere(q[i:i + 1], "l93"))[0],
            "peint": False}


def ceinture(poly, bordures):
    out = []
    for f in bordures:
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        L = abscisses(P)[-1]
        s = np.arange(0.25, L, 0.5) if L > 0.5 else np.array([L / 2])
        q, tg = point_a(P, s)
        m = dans_polygone(q + normale_gauche(tg) * 0.3, poly)
        if m.sum() * (L / len(s)) >= 0.5:
            out.append(f["properties"]["id"])
    return sorted(out)


def bordure_synthetique(nid, P, profil, vue, ref_feat, prov_geo, prov_int, mnt, z_bouts=None):
    """Bordure ajoutée par la description (lacune du levé) : polyligne locale P, côté haut à gauche,
    Z = MNT 2026 à 0,30 m devant la face, régularisé comme les bordures levées (regle:fil_eau_regulier ;
    revue conformité r2 : K-9297a avait des pointes de 9 cm, marches de tête de 4 à 7 cm) ; matériau,
    aspect et pose repris de la bordure voisine. `z_bouts` (corde de fermeture d'une ceinture) : fil d'eau
    interpolé entre les extrémités de la bordure qu'elle referme (revue conformité r2 : K-0629z tirée du MNT,
    6 à 9 cm plus haute que K-0629, remplissage de I-0629 hors 3-5 cm)."""
    from bordures import regulariser_fil_eau
    pts, sv = densifier(P, 1.0)
    _, tg = point_a(P, sv)
    nl = normale_gauche(tg)
    if z_bouts is not None:
        z = z_bouts[0] + (z_bouts[1] - z_bouts[0]) * sv / max(float(sv[-1]), 1e-9)
    else:
        z_av = mnt(*(repere(pts - nl * 0.30, "l93").T))
        z_ar = mnt(*(repere(pts + nl * (largeur_profil(lire_json(SPECS / "bordures.json"), profil) + 0.30), "l93").T)) - vue
        z, _ = regulariser_fil_eau(sv, z_av, z_ar)
    L = float(abscisses(P)[-1])
    rp = ref_feat["properties"]
    props = dict(rp)
    props.update({
        "id": nid, "longueur_m": L,
        "intervalles": [{"s0": 0.0, "s1": L, "profil": profil, "vue_m": vue, "role": "courant"}],
        "abaisses": [], "courbes": [], "chartieres_gam": [], "zone_travaux_2025": rp["zone_travaux_2025"],
        "coupe_zone": {"debut": False, "fin": False},
        "source": {"ligne": None, "gam_index": None, "s_src_m": None, "sens": "direct", "doublons_supprimes": [],
                   "statut_hauteur": "synthetique", "ecart_fil_eau_2021_mnt_m": None, "voisine": rp["id"]},
        "prov": {"geometrie": prov_geo, "face_vue": {"src": "a_priori:interieur_ilot_a_gauche",
                                                     "ref": "anneau d'îlot anti-horaire", "conf": "haute"},
                 "intervalles": prov_int, "materiau": rp["prov"]["materiau"], "aspect": rp["prov"]["aspect"],
                 "element_m": rp["prov"]["element_m"], "z": rp["prov"]["z"]},
    })
    return {"type": "Feature", "geometry": {"type": "LineString",
                                            "coordinates": coords_geojson(np.c_[repere(pts, "l93"), z])},
            "properties": arrondi(props)}


def bordure_raccord(kid, P_ring, ref_feat, mnt):
    """Corde fermant la lacune d'une ceinture en anneau (ex. TPC NE), profil courant de la voisine."""
    P = np.vstack([P_ring[-1], P_ring[0]])
    voisins = [it for it in ref_feat["properties"]["intervalles"] if it["role"] == "courant"]
    it0 = voisins[-1] if voisins else {"profil": "T2", "vue_m": 0.14}
    L = float(np.hypot(*(P[1] - P[0])))
    nid = (kid[:-1] if kid[-1].isalpha() else kid) + "z"
    # fil d'eau aux extrémités : celui de la bordure refermée, à l'extrémité la plus proche de chaque bout
    C3 = np.asarray(ref_feat["geometry"]["coordinates"], dtype=np.float64)
    E = repere(C3[[0, -1], :2])
    zb = [float(C3[[0, -1]][int(np.argmin(np.hypot(*(E - q).T))), 2]) for q in P]
    syn = bordure_synthetique(
        nid, P, it0["profil"], it0["vue_m"], ref_feat,
        {"src": "a_priori:fermeture_ceinture_ilot",
         "ref": f"corde de {L:.2f} m entre les extrémités de {kid} (lacune du levé GAM)", "conf": "faible"},
        {"src": "a_priori:profil_voisin", "ref": f"profil courant de {kid}", "conf": "faible"}, mnt, z_bouts=zb)
    syn["properties"]["prov"]["z"] = {"src": "a_priori:fil_eau_bordure_refermee",
                                      "ref": f"fil d'eau interpolé entre les extrémités de {kid}", "conf": "moyenne"}
    return syn


def lacunes_ceinture(ring, ceint_feats, seuil=0.3, lmin=1.0):
    """Portions du contour (anneau anti-horaire) à plus de `seuil` m de toute bordure de la ceinture
    sur au moins `lmin` m : [polyligne locale]."""
    r = np.vstack([ring, ring[:1]])
    pts, s = densifier(r, 0.25)
    if not ceint_feats:
        return []
    A = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[:-1, :2]) for f in ceint_feats])
    B = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[1:, :2]) for f in ceint_feats])
    d, _, _ = distance_segments(pts, A, B)
    libre = d > seuil
    if not libre.any() or libre.all():
        return []
    k0 = int(np.argmin(libre))                      # départ sur un point couvert (gestion du bouclage)
    idx = np.r_[np.arange(k0, len(pts) - 1), np.arange(0, k0 + 1)]
    out, cur = [], []
    for i in idx:
        if libre[i]:
            cur.append(pts[i])
        elif cur:
            cur = [pts[prev]] + cur + [pts[i]]
            if abscisses(np.array(cur))[-1] >= lmin:
                out.append(np.array(cur))
            cur = []
        prev = i
    return out


def sans_repli(P, seuil_deg=150.0, dmax=0.25):
    """Polyligne sans aller-retour : à un tournant de plus de 150° dont l'aller longe le retour à moins de
    0,25 m, seule la partie la plus longue est gardée (K-9297a : 3,2 m d'aller replié sur le retour)."""
    P = np.asarray(P, dtype=np.float64)
    if len(P) < 3:
        return P
    d = np.diff(P, axis=0)
    a = np.arctan2(d[:, 1], d[:, 0])
    tour = np.degrees((a[1:] - a[:-1] + np.pi) % (2 * np.pi) - np.pi)
    for k in np.where(np.abs(tour) > seuil_deg)[0] + 1:
        A, B = P[:k + 1], P[k:]
        dA, _, _ = distance_segments(A, B[:-1], B[1:])
        dB, _, _ = distance_segments(B, A[:-1], A[1:])
        if min(np.max(dA), np.max(dB)) < dmax:
            return B if abscisses(B)[-1] >= abscisses(A)[-1] else A
    return P


def recaler_sur_bordures(poly, bordures, dmax=RECALAGE_MAX):
    """Recale l'anneau d'un polygone v1 sur l'arête avant des bordures voisines : contour
    rééchantillonné à 0,25 m, chaque sommet à moins de dmax d'une bordure est projeté dessus."""
    r = np.vstack([poly[0], poly[0][:1]])
    pts, _ = densifier(r, 0.25)
    pts = pts[:-1]
    A = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[:-1, :2]) for f in bordures])
    B = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[1:, :2]) for f in bordures])
    d, _, pr = distance_segments(pts, A, B)
    m = d <= dmax
    pts[m] = pr[m]
    out = [pts[0]]
    for q in pts[1:]:
        if np.hypot(*(q - out[-1])) > 0.02:
            out.append(q)
    ring = np.array(out)
    if aire_signee(ring) < 0:
        ring = ring[::-1]
    return [ring] + poly[1:], int(m.sum()), len(pts)


def _src_geo(f):
    return (f["properties"].get("prov") or {}).get("geometrie", {}).get("src", "")


def rogner_par_bordures_levees(poly, bordures, part_max=0.4):
    """GQ-TOP-004 : contour v1 d'îlot traversé de part en part par une bordure levée (GAM, PCRS, plan 2025) ; la petite
    partie au-delà de la bordure (≤ part_max de l'aire, ex. pointe de I-0333 au-delà du nez K-0399 dans le refuge de
    Verdun SO, revues du 11/10/2026) est retirée : coupe par la droite des points d'entrée et de sortie. Une bordure qui
    partage l'îlot en deux parts comparables (bordure intérieure, ex. K-0398) ne coupe rien. -> (poly, [coupes])."""
    from commun import _couper_demi_plan, couper_polyligne
    coupes = []
    for f in sorted(bordures, key=lambda f: f["properties"]["id"]):
        if _src_geo(f).startswith("a_priori"):
            continue
        P = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        lo, hi = poly[0].min(axis=0) - 0.5, poly[0].max(axis=0) + 0.5
        if (P.max(axis=0) < lo).any() or (P.min(axis=0) > hi).any():
            continue
        for s0, s1 in couper_polyligne(P, poly):
            if s1 - s0 < 0.5:
                continue
            a, _ = point_a(P, s0)
            b, _ = point_a(P, s1)
            a, b = np.asarray(a).ravel(), np.asarray(b).ravel()
            ra = np.vstack([poly[0], poly[0][:1]])
            da = distance_segments(np.vstack([a, b]), ra[:-1], ra[1:])[0]
            if (da > 0.05).any():
                continue                                    # la bordure ne traverse pas le contour de part en part
            d = b - a
            n = np.array([-d[1], d[0]]) / max(float(np.hypot(*d)), 1e-9)
            c = -float(n @ a)
            g = _couper_demi_plan(poly, n, c)
            dr = _couper_demi_plan(poly, -n, -c)
            ag = sum(abs(aire_signee(p[0])) for p in g)
            ad = sum(abs(aire_signee(p[0])) for p in dr)
            tot = ag + ad
            if tot <= 0 or min(ag, ad) > part_max * tot or min(ag, ad) < 0.05 or not g or not dr:
                continue
            garde = g if ag >= ad else dr
            poly = max(garde, key=lambda p: abs(aire_signee(p[0])))
            coupes.append(f"{f['properties']['id']} ({min(ag, ad):.2f} m² retirés)")
    return poly, coupes


def lacune_fermee(P, bordures, exclus, dmax=0.6, part=0.6):
    """GA-ILO-003 / GQ-TOP-004 : lacune de ceinture déjà fermée par une bordure levée hors ceinture (≥ part des
    échantillons à ≤ dmax m), ex. K-0400 (bout de I-0628) à 0,3 m du bout de I-0339 : aucune bordure synthétique."""
    pts, _ = densifier(np.asarray(P, float), 0.25)
    lev = [f for f in bordures if f["properties"]["id"] not in exclus and not _src_geo(f).startswith("a_priori")]
    if not lev:
        return None
    A = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[:-1, :2]) for f in lev])
    B = np.vstack([repere(np.asarray(f["geometry"]["coordinates"])[1:, :2]) for f in lev])
    own = np.concatenate([np.full(len(f["geometry"]["coordinates"]) - 1, k) for k, f in enumerate(lev)])
    d, j, _ = distance_segments(pts, A, B)
    if (d <= dmax).mean() >= part:
        ks = sorted({lev[int(own[x])]["properties"]["id"] for x in j[d <= dmax]})
        return ks
    return None


def rogner_synthetique(P, bordures, lmin=0.5):
    """GQ-TOP-004 : bordure synthétique coupée à ses croisements avec les bordures levées ; on garde le plus long
    morceau sans croisement (≥ lmin), sinon rien (K-9333a croisait deux fois K-0399)."""
    P = np.asarray(P, float)
    S = abscisses(P)
    coupes = [0.0, float(S[-1])]
    for f in bordures:
        if _src_geo(f).startswith("a_priori"):
            continue
        Q = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
        for i in range(len(P) - 1):
            p, r = P[i], P[i + 1] - P[i]
            A, D = Q[:-1], Q[1:] - Q[:-1]
            den = r[0] * D[:, 1] - r[1] * D[:, 0]
            ok = np.abs(den) > 1e-12
            ap = A - p
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (ap[:, 0] * D[:, 1] - ap[:, 1] * D[:, 0]) / den
                u = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den
            m = ok & (t > 1e-6) & (t < 1 - 1e-6) & (u >= 0) & (u <= 1)
            coupes += list(S[i] + t[m] * (S[i + 1] - S[i]))
    coupes = np.unique(np.round(coupes, 6))
    if len(coupes) <= 2:
        return P
    from commun import sous_polyligne
    k = int(np.argmax(np.diff(coupes)))
    a, b = float(coupes[k]), float(coupes[k + 1])
    marge = 0.05                                            # au contact de la bordure levée, sans la toucher
    a = a + marge if a > 0 else a
    b = b - marge if b < S[-1] else b
    if b - a < lmin:
        return None
    return sous_polyligne(P, a, b)


def vue_adjacente(P, ceint_feats, defaut):
    """Vue de la bordure synthétique : celle des bordures levées de la ceinture à ses deux bouts (intervalle le plus
    proche), au lieu du T2 0,14 par défaut (revue conformité du 11/10/2026 : K-9339a en T2 0,14 entre des bateaux)."""
    vues = []
    for q in (np.asarray(P[0], float), np.asarray(P[-1], float)):
        best = None
        for f in ceint_feats:
            if _src_geo(f).startswith("a_priori"):
                continue
            Q = repere(np.asarray(f["geometry"]["coordinates"])[:, :2])
            d, _, pr = distance_segments(q[None], Q[:-1], Q[1:])
            if best is None or d[0] < best[0]:
                S = abscisses(Q)
                k = int(np.argmin(np.hypot(*(Q - pr[0]).T)))
                s = float(S[k])
                it = f["properties"]["intervalles"][-1]
                for c in f["properties"]["intervalles"]:
                    if c["s0"] - 1e-6 <= s <= c["s1"] + 1e-6:
                        it = c
                        break
                v = it.get("vue_m_fin", it["vue_m"]) if s > 0.5 * (it["s0"] + it["s1"]) else it["vue_m"]
                best = (float(d[0]), float(v))
        if best is not None and best[0] <= 1.0:
            vues.append(best[1])
    return round(float(min(vues)), 3) if vues else defaut


def largeur_profil(spec, profil):
    p = spec["profils"].get(profil, {})
    return float(p.get("base") or p.get("largeur") or 0.15)


def lier_surfaces(ilots, surfaces):
    """Surfaces (faces de la partition) intérieures à chaque îlot : îlot.surface et surface.ilots."""
    from sol_partition import point_interieur
    polys = []
    for f in ilots:
        g = f["geometry"]
        rs = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        polys.append((f, [[repere(np.asarray(r, float)[:-1, :2]) for r in pp] for pp in rs]))
    for s in surfaces:
        if s["properties"]["classe"] == "emprise_bordure":
            continue
        g = s["geometry"]
        rs = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        pi = point_interieur([repere(np.asarray(r, float)[:-1, :2]) for r in rs[0]])
        for f, pp in polys:
            if any(dans_polygone(pi[None], q)[0] for q in pp):
                f["properties"]["surface"] = sorted(set(f["properties"]["surface"]) | {s["properties"]["id"]})
                s["properties"]["ilots"] = sorted(set(s["properties"]["ilots"]) | {f["properties"]["id"]})
                break


def construire(mnt, bordures, surfaces=()):
    """(îlots, bordures de raccord ajoutées, rapport). Site complet ; les surfaces (faces de la
    partition, calculée après les bordures de raccord) sont liées ensuite par lier_surfaces."""
    spec = lire_json(SPECS / "bordures.json")
    zone = ctx.zone_pilote()["anneau"]
    par_id = {f["properties"]["id"]: f for f in bordures}
    choix = {c[0]: c for c in CHOIX}
    candidats = []
    for kid, ring, gap in anneaux_bordures(bordures):
        candidats.append({"cle": kid, "poly": [ring], "gap": gap, "kid": kid})
    deja = {lien_v1(c["poly"])[0] for c in candidats if lien_v1(c["poly"])}
    for sid, p, polys in ctx.surfaces_v1():
        classe = CORRECTIONS.get(sid, {}).get("classe", p["classe"])
        if sid in deja or not (classe in ("ilot", "terre_plein_vegetal") or sid in choix):
            continue
        for poly in polys:
            for m in couper_polygone(poly, zone):
                if abs(aire_signee(m[0])) < 0.95 * abs(aire_signee(poly[0])):
                    continue                            # îlot tronqué par la zone pilote
                candidats.append({"cle": sid, "poly": m, "gap": 0.0, "kid": None})
    ilots, raccords, rapport = [], [], collections.Counter()
    surf_par_v1 = collections.defaultdict(list)
    for c in sorted(candidats, key=lambda c: c["cle"]):
        poly = c["poly"]
        if not dans_polygone(poly[0].mean(axis=0, keepdims=True), [zone])[0]:
            continue
        v1 = lien_v1(poly)
        sid = v1[0] if v1 else None
        ch = choix.get(c["cle"]) or choix.get(sid)
        if c["kid"] and v1 and v1[1] not in ("ilot", "terre_plein_vegetal", "espace_vert", "trottoir"):
            continue                                   # anneau qui n'entoure pas un îlot (ex. bordure de chaussée)
        if ch and ch[1]:
            mid, src, ref, conf, role = ch[1], ch[2], ch[3], ch[4], ch[5]
        else:
            mid = {"beton": "beton_balaye", "enrobe": "enrobe_trottoir", "herbe": "gazon_tondu",
                   "massif_plante": "brf_bois_concasse"}.get(v1[2] if v1 else "", "beton_balaye")
            src = "plan2025" if v1 and v1[3] == "modifie_2025" else "a_priori:correspondance_materiau_v1"
            ref = f"v1 {v1[0]} {v1[1]}/{v1[2]}/{v1[3]}" if v1 else "sans surface v1"
            conf, role = "faible", (ch[5] if ch else ("refuge" if aire_signee(poly[0]) < 8 else "ilot"))
        iid = "I-" + (c["cle"][2:] if c["kid"] else c["cle"][5:])
        if not c["kid"] and any(f["properties"]["id"] == iid for f in ilots):
            iid += "v"                                  # îlot v1 de même numéro qu'un anneau de bordure
        ceint = ceinture(poly, bordures)
        recale = None
        if not c["kid"] and ceint:
            poly, n_rec, n_tot = recaler_sur_bordures(poly, [par_id[k] for k in ceint])
            recale = f"{n_rec}/{n_tot} sommets du contour v1 recalés sur l'arête avant de {', '.join(ceint)} (≤ {RECALAGE_MAX} m)"
            # GQ-TOP-004 : pointe du contour v1 au-delà d'une bordure levée qui le traverse retirée
            poly, coupes_lev = rogner_par_bordures_levees(poly, bordures)
            if coupes_lev:
                recale += " ; rogné par " + ", ".join(coupes_lev) + " (GQ-TOP-004)"
                rapport["contour_v1_rogne_par_bordure_levee"] += 1
                ceint = ceinture(poly, bordures)
        if c["gap"] > 0.3 and c["kid"]:
            rac = bordure_raccord(c["kid"], poly[0], par_id[c["kid"]], mnt)
            raccords.append(rac)
            par_id[rac["properties"]["id"]] = rac
            ceint = sorted(set(ceint) | {rac["properties"]["id"]})
        if not c["kid"] and ceint:
            # limite de massif sans bordure levée : bordurette P1 (bordures.json usage_site), seulement pour
            # combler de courtes lacunes (≤ 8 m) d'une ceinture levée aux 3/5 au moins : une ceinture surtout
            # synthétique suivrait un contour v1 d'origine raster (l'îlot n'est alors pas décrit, la surface
            # reste dans la partition vectorielle)
            lac = lacunes_ceinture(poly[0], [par_id[k] for k in ceint])
            per = float(abscisses(np.vstack([poly[0], poly[0][:1]]))[-1])
            l_lac = sum(float(abscisses(P)[-1]) for P in lac)
            if l_lac > 0.4 * per or any(float(abscisses(P)[-1]) > 8.0 for P in lac):
                rapport["v1_sans_ceinture_levee"] += 1
                continue
            massif = mid in ("brf_bois_concasse", "gravier_concasse_6_10", "gazon_tondu")
            j = 0
            for P in lac:
                P = sans_repli(P)
                # GA-ILO-003 / GQ-TOP-004 (revues du 11/10/2026) : pas de bordure synthétique sur une lacune déjà fermée
                # par une bordure levée hors ceinture ; sinon coupée aux croisements des bordures levées
                fermee = lacune_fermee(P, list(par_id.values()), set(ceint))
                if fermee:
                    rapport["lacune_fermee_par_bordure_levee"] += 1
                    continue
                P = rogner_synthetique(P, list(par_id.values()))
                if P is None:
                    rapport["synthetique_trop_courte_apres_rognage"] += 1
                    continue
                nid = f"K-9{iid[3:6]}" + "abcdefghij"[j]
                j += 1
                vue_s = vue_adjacente(P, [par_id[k] for k in ceint], 0.02 if massif else 0.14)
                if massif:
                    vue_s = min(vue_s, 0.03)                     # limite de massif : bordurette P1 (VUE_PLAGE 0-0,03)
                from bordures import profil_de
                prof_s = profil_de(vue_s)                        # profil de la plage de vue (bordures.VUE_PLAGE)
                syn = bordure_synthetique(
                    nid, P, prof_s, vue_s, par_id[ceint[0]],
                    {"src": "a_priori:limite_ilot_sans_bordure_levee",
                     "ref": f"contour de {iid} à plus de 0,30 m des bordures levées sur {abscisses(P)[-1]:.1f} m (coupé aux "
                            "bordures levées, GQ-TOP-004)", "conf": "faible"},
                    {"src": "a_priori:limite_massif_p1" if massif else "a_priori:vue_bordure_levee_adjacente",
                     "ref": ("bordures.json usage_site : limites d'espaces verts en P1 (0-0,05)" if massif else
                             f"vue des bordures levées de la ceinture aux deux bouts ({vue_s:.3f} m)"), "conf": "faible"}, mnt)
                raccords.append(syn)
                par_id[nid] = syn
                ceint = sorted(set(ceint) | {nid})
        rempl = {"materiau_id": mid}
        rempl.update(REMPLISSAGES.get(mid, {"epaisseur_m": 0.05, "retrait_sous_bordure_m": 0.03}))
        profils = [it["profil"] for k in ceint if k in par_id for it in par_id[k]["properties"]["intervalles"]
                   if it["role"] == "courant"]
        prof_maj = collections.Counter(profils).most_common(1)[0][0] if profils else "T2"
        rempl["retrait_bordure_m"] = largeur_profil(spec, prof_maj)
        # dessus de bordure : fil d'eau + vue courante, médiane le long de la ceinture
        dessus = []
        for k in ceint:
            f = par_id.get(k)
            if f is None:
                continue
            zs = [c3[2] for c3 in f["geometry"]["coordinates"]]
            vs = [it["vue_m"] for it in f["properties"]["intervalles"] if it["role"] == "courant"]
            if vs:
                dessus.append(float(np.median(zs)) + float(np.median(vs)))
        z_dessus = float(np.median(dessus)) if dessus else None
        obj = sorted(i for i, cat, xy in ctx.mobilier()
                     if dans_polygone(xy[None], poly)[0])
        arb = sorted(i for i, _, xy in ctx.arbres() if dans_polygone(xy[None], poly)[0])
        surf_ids = sorted(s["properties"]["id"] for s in surf_par_v1.get(sid, []))
        props = {
            "id": iid, "famille": "ilots", "type": role, "surface": surf_ids, "lien_v1": sid,
            "remplissage": rempl,
            "niveau": {"z_dessus_bordure_ngf": z_dessus,
                       "z_remplissage_ngf": None if z_dessus is None else z_dessus - rempl["retrait_sous_bordure_m"]},
            "ceinture": ceint, "nez": nez(poly[0]), "objets_portes": obj, "plantation": arb,
            "franchissable": False, "aire_m2": abs(aire_signee(poly[0])),
            "prov": {"geometrie": ({"src": "gam", "ref": f"anneau de la bordure {c['kid']}", "conf": "haute"} if c["kid"]
                                   else {"src": "a_priori:polygone_v1_recale", "ref": f"{sid} ; {recale or 'sans bordure attenante'}", "conf": "moyenne"}),
                     "remplissage": {"src": src, "ref": ref[:300], "conf": conf},
                     "retrait": {"src": "a_priori:pratique_remplissage_ilot",
                                 "ref": "surface du remplissage 3 à 5 cm sous le dessus de bordure (pratique courante)", "conf": "moyenne"}},
        }
        ilots.append({"type": "Feature", "geometry": geom_polygones([[repere(r, "l93") for r in poly]]),
                      "properties": arrondi(props)})
        rapport[mid] += 1
        for s in surf_par_v1.get(sid, []):
            s["properties"]["ilots"] = sorted(set(s["properties"]["ilots"]) | {iid})
    return ilots, raccords, dict(rapport)
