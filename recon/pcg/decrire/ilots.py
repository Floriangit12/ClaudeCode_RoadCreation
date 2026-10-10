"""Famille `ilots` de la description v2 : îlots, terre-pleins et massifs bordés de la zone pilote,
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

import contexte as ctx
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
        # lacune comblée par une autre bordure : au moins la moitié de la corde longée (≤ 0,3 m) par
        # elle (une bordure qui ne fait qu'aboutir près de la corde, ex. le bateau K-0389 contre
        # I-0629, ne ferme pas l'anneau)
        comblee = False
        if gap > 0.3:
            corde = np.linspace(P[-1], P[0], 9)
            for k2, P2 in ext.items():
                if k2 == kid:
                    continue
                d, _, _ = distance_segments(corde, P2[:-1], P2[1:])
                if (d <= 0.3).mean() >= 0.5:
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


def largeur_profil(spec, profil):
    p = spec["profils"].get(profil, {})
    return float(p.get("base") or p.get("largeur") or 0.15)


def construire(mnt, bordures, surfaces):
    """(îlots, bordures de raccord ajoutées, rapport)."""
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
    for s in surfaces:
        surf_par_v1[s["properties"]["lien_v1"]].append(s)
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
        ceint = ceinture(poly, bordures)
        recale = None
        if not c["kid"] and ceint:
            poly, n_rec, n_tot = recaler_sur_bordures(poly, [par_id[k] for k in ceint])
            recale = f"{n_rec}/{n_tot} sommets du contour v1 recalés sur l'arête avant de {', '.join(ceint)} (≤ {RECALAGE_MAX} m)"
        if c["gap"] > 0.3 and c["kid"]:
            rac = bordure_raccord(c["kid"], poly[0], par_id[c["kid"]], mnt)
            raccords.append(rac)
            par_id[rac["properties"]["id"]] = rac
            ceint = sorted(set(ceint) | {rac["properties"]["id"]})
        if not c["kid"] and ceint:
            # limite de massif sans bordure levée : bordurette P1 (bordures.json usage_site)
            massif = mid in ("brf_bois_concasse", "gravier_concasse_6_10", "gazon_tondu")
            for j, P in enumerate(lacunes_ceinture(poly[0], [par_id[k] for k in ceint])):
                P = sans_repli(P)
                nid = f"K-9{iid[3:6]}" + "abcdefghij"[j]
                syn = bordure_synthetique(
                    nid, P, "P1" if massif else "T2", 0.02 if massif else 0.14, par_id[ceint[0]],
                    {"src": "a_priori:limite_ilot_sans_bordure_levee",
                     "ref": f"contour de {iid} à plus de 0,30 m des bordures levées sur {abscisses(P)[-1]:.1f} m", "conf": "faible"},
                    {"src": "a_priori:limite_massif_p1" if massif else "a_priori:profil_voisin",
                     "ref": "bordures.json usage_site : limites d'espaces verts en P1 (0-0,05)", "conf": "faible"}, mnt)
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
