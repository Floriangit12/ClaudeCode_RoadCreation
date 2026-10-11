"""Contrôle des marquages par le solveur de cohérence v2 : flèches centrées dans leur voie, marques dans la
chaussée, propositions de recalage avec preuve. Lecture seule de base/marquages.geojson (jamais modifié).

1. Flèches directionnelles MF-* (MQ-FLE-006, IISR 7e partie / CETE 2010) : la pose est retrouvée sur le
   polygone posé lui-même (ajustement rigide du gabarit de marquages_geometrie.json, sommet à sommet), la
   voie par une coupe perpendiculaire au cap passant par le centre de la boîte du gabarit :
   - bords de voie = axes des lignes longitudinales peintes (continues, discontinues, segments) de part et
     d'autre, sinon arête avant de bordure, sinon bords du polygone de voie OpenDRIVE (lanes_2026) ;
   - décalage attendu de l'origine (pied de tige) par rapport à l'axe de voie : TD 0 ; TAD −0,425 m ; TAG
     +0,425 m ; TD_TAD −0,275 m ; TD_TAG +0,275 m (x positif à droite du sens de circulation) ;
   - écart = décalage observé − attendu ; |écart| ≤ 0,15 m : conforme ; sinon proposition de recalage
     latéral (−écart) si la flèche n'est pas levée (GAM σ 0,05 m : alors c'est la voie décrite qui est à
     revoir) ; la boîte doit rester dans la voie (MQ-DET-010).
   Preuve image : pour une flèche « conservée » (2022 = 2026), contraste de peinture du gabarit à la pose
   actuelle et à la pose recalée sur le PCRS 5 cm 2022 ; le recalage n'est proposé « avec preuve » que si
   l'ortho ne le contredit pas (contraste recalé ≥ contraste actuel − 0,01).
2. Toutes les marques (MQ-DET-010, TQ-MQG-014) : échantillons tous les 0,25 m (lignes) ou sommets et
   intérieur (polygones) ; un échantillon est hors chaussée s'il est du côté haut d'une bordure à moins de
   1 m (orientation v2), ou sur une classe non roulable loin de toute bordure. Exceptions : lignes jaunes
   (sur bordure admises), figurines vélo / PMR sur piste ou parking, passages coupant un refuge à niveau.
   Un débord ≤ 0,5 m d'une marque non levée donne une proposition de translation vers la chaussée
   (débord + 0,05 m) ; au-delà, ou pour une marque levée, un signalement.
3. Q3 (revue adverse v2) : les marquages que la fusion déclare « retirer » ou « absent_2026 » sont hors contrôle
   (et ne bornent plus les voies) ; « absent_2026_a_verifier » est signalé ; un retrait contredit par un levé
   GAM 2026 est journalisé (conflits_fusion.json).
4. Q5 (revue adverse v2) : (a) la preuve image mesure le contraste de la TÊTE seule (tige et anneau de la tige
   exclus) ; (b) flèche douteuse si la tige est à moins de 0,10 m de l'axe d'une ligne longitudinale parallèle
   ou si son pied est à moins de 0,5 m d'une limite de voie OpenDRIVE ; (c) toute limite (ligne, arête de
   bordure) qui coupe la boîte donne « voie_coupee », jamais un recalage ; (d) aucun recalage dont le résultat
   n'est pas entièrement roulable (« conflit_surface_marquage ») ; (e) une répétition INF-FLE-004 glisse en s
   jusqu'à une voie ≥ boîte + 2 × 0,3 m entièrement roulable (|Δs| ≤ 12 m), sinon sa suppression est proposée.
Sorties : coherence/marquages_controle.json, coherence/corrections_marquages.geojson.
"""
import math

import numpy as np

from coherence_carte import BASE_V2, CARTE, COHERENCE, _polys_locaux
from commun import RACINE, SPECS, arrondi, coords_geojson, dans_polygone, distance_segments, ecrire_geojson, \
    ecrire_json, lire_geojson, lire_json, repere

DECALAGE = {"TD": 0.0, "TAD": -0.425, "TAG": 0.425, "TD_TAD": -0.275, "TD_TAG": 0.275}
TOL_FLECHE = 0.15
Y_TETE = 2.0                 # Q5 : la tige occupe y < 2 m (|x| ≤ 0,075 m) dans tous les gabarits
MARGE_FLECHE = 0.30          # Q5 : voie ≥ boîte + 2 × 0,3 m pour une répétition INF-FLE-004
ROULABLES = {"chaussee", "parking", "acces_riverain", "piste_cyclable", "quai_bus"}
NON_ROULABLES = {"trottoir", "ilot", "espace_vert", "terre_plein_vegetal", "batiment"}
SORTIE = COHERENCE / "marquages_controle.json"
CORR = COHERENCE / "corrections_marquages.geojson"


def _gabarits():
    return lire_json(SPECS / "marquages_geometrie.json")["gabarits"]


def _rigide(T, Q):
    """Transformation rigide (R, t) qui envoie le gabarit T (N, 2) sur Q (N, 2) (Procrustes) ; résidu RMS."""
    ct, cq = T.mean(0), Q.mean(0)
    H = (T - ct).T @ (Q - cq)
    U, _, Vt = np.linalg.svd(H)
    D = np.eye(2)
    D[1, 1] = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ D @ U.T
    t = cq - R @ ct
    res = float(np.sqrt(np.mean(np.sum((T @ R.T + t - Q) ** 2, axis=1))))
    return R, t, res


def pose_fleche(f, gab):
    """(origine (2,), u direction de circulation (2,), r droite (2,), résidu) depuis le polygone posé."""
    Q = repere(np.asarray(f["geometry"]["coordinates"][0], float)[:, :2])
    if len(Q) > 1 and np.allclose(Q[0], Q[-1]):
        Q = Q[:-1]
    T = np.asarray(gab["polygone"], float)
    if len(T) != len(Q):
        return None
    best = None
    for k in range(len(Q)):                 # sommet de départ inconnu : toutes les rotations cycliques
        for sens in (1, -1):
            Qk = np.roll(Q[::sens], -k, axis=0)
            R, t, res = _rigide(T, Qk)
            if best is None or res < best[3]:
                best = (R, t, k, res)
    R, t, _, res = best
    o = t                                   # image de l'origine du gabarit
    u = R @ np.array([0.0, 1.0])
    r = R @ np.array([1.0, 0.0])
    return o, u, r, res


def _lignes(feats):
    out = []
    for f in feats:
        p = f["properties"]
        if p["classe"] != "ligne" or p["type"] not in ("continue", "discontinue", "segment"):
            continue
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for c in parts:
            P = repere(np.asarray(c, float)[:, :2])
            if len(P) >= 2:
                out.append((p["id"], P, p.get("couleur")))
    return out


def _coupe(c, r, lignes, carte, portee=4.6):
    """Bords de voie de part et d'autre du point c le long de r : (gauche (dist<0), droite (dist>0)) avec
    leur source ; candidats = lignes peintes, bordures (arête avant), sinon None."""
    A = c - r * portee
    B = c + r * portee
    cands = {-1: [], 1: []}
    for lid, P, _ in lignes:
        for a, b in zip(P[:-1], P[1:]):
            d = b - a
            den = r[0] * (-d[1]) - r[1] * (-d[0])
            if abs(den) < 1e-9:
                continue
            w = a - A
            tt = (w[0] * (-d[1]) - w[1] * (-d[0])) / den
            uu = (r[0] * w[1] - r[1] * w[0]) / den
            if 0 <= uu <= 1 and 0 <= tt <= 2 * portee:
                x = tt - portee
                if abs(x) > 0.3:
                    cands[int(np.sign(x))].append((abs(x), x, "ligne", lid))
    for k, kb in enumerate(carte.bordures):
        P = kb["P"]
        if np.min(np.hypot(*(P - c).T)) > portee + 2:
            continue
        for a, b in zip(P[:-1], P[1:]):
            d = b - a
            den = r[0] * (-d[1]) - r[1] * (-d[0])
            if abs(den) < 1e-9:
                continue
            w = a - A
            tt = (w[0] * (-d[1]) - w[1] * (-d[0])) / den
            uu = (r[0] * w[1] - r[1] * w[0]) / den
            if 0 <= uu <= 1 and 0 <= tt <= 2 * portee:
                x = tt - portee
                if abs(x) > 0.3:
                    cands[int(np.sign(x))].append((abs(x), x, "bordure", kb["id"]))
    g = sorted(cands[-1])[0] if cands[-1] else None
    d = sorted(cands[1])[0] if cands[1] else None
    return g, d


def _coupe_voie_xodr(c, r, carte):
    """Bords de la voie OpenDRIVE (lanes_2026) qui contient c, le long de r : (gauche, droite, source) ou None."""
    from commun import aretes
    for l in carte.lanes:
        if l["type"] != "driving" or np.any(c < l["bmin"]) or np.any(c > l["bmax"]):
            continue
        if not dans_polygone(c[None], l["poly"])[0]:
            continue
        A, B = aretes(l["poly"])
        xs = []
        for a, b in zip(A, B):
            d = b - a
            den = r[0] * (-d[1]) - r[1] * (-d[0])
            if abs(den) < 1e-9:
                continue
            w = a - c
            tt = (w[0] * (-d[1]) - w[1] * (-d[0])) / den
            uu = (r[0] * w[1] - r[1] * w[0]) / den
            if 0 <= uu <= 1:
                xs.append(tt)
        g = [x for x in xs if x < 0]
        dd = [x for x in xs if x > 0]
        if g and dd and 2.2 <= min(dd) - max(g) <= 4.6:
            return max(g), min(dd), f"voie OpenDRIVE {l['route']}/{l['voie']}"
    return None


def _contraste(pts_in, pts_out):
    import coherence_ombres as CO
    a = CO.echantillonner("pcrs2022", pts_in)
    b = CO.echantillonner("pcrs2022", pts_out)
    return float(np.nanmean(a) - np.nanmean(b))


def _echantillons_gabarit(gab, o, u, r, pas=0.05, tete=False):
    """Échantillons dans le gabarit et dans un anneau à 0,12-0,25 m autour. `tete` (Q5) : la tige (|x| ≤ 0,12 m,
    y < 2 m) et l'anneau qui la borde (|x| ≤ 0,35 m, y < 2 m) sont exclus : le contraste mesure la tête seule
    (une ligne longitudinale sous la tige ne peut plus « confirmer » une flèche)."""
    T = np.asarray(gab["polygone"], float)
    xs = np.arange(T[:, 0].min(), T[:, 0].max() + 1e-9, pas)
    ys = np.arange(0.0, 4.0 + 1e-9, pas)
    X, Y = np.meshgrid(xs, ys)
    L = np.c_[X.ravel(), Y.ravel()]
    m = dans_polygone(L, [T])
    if tete:
        m &= ~((np.abs(L[:, 0]) <= 0.12) & (L[:, 1] < Y_TETE))
    dedans = L[m]
    xs2 = np.arange(T[:, 0].min() - 0.3, T[:, 0].max() + 0.3 + 1e-9, pas)
    ys2 = np.arange(-0.3, 4.3 + 1e-9, pas)
    X2, Y2 = np.meshgrid(xs2, ys2)
    L2 = np.c_[X2.ravel(), Y2.ravel()]
    m2 = ~dans_polygone(L2, [T])
    A, B = np.vstack([T, T[:1]])[:-1], np.vstack([T, T[:1]])[1:]
    dd, _, _ = distance_segments(L2, A, B)
    m2 &= (dd >= 0.12) & (dd <= 0.25)
    if tete:
        m2 &= ~((np.abs(L2[:, 0]) <= 0.35) & (L2[:, 1] < Y_TETE))
    dehors = L2[m2]
    to = lambda Lp: o + Lp[:, :1] * r + Lp[:, 1:2] * u
    return to(dedans), to(dehors)


def _boite(gab, o, u, r, ds=0.0):
    bx = gab["boite"]["x"]
    o2 = o + u * ds
    return o2, bx


def _coupe_boite(o, u, r, bx, lignes, carte, marge=0.02):
    """Q5 : limites (lignes longitudinales, arêtes de bordure) qui coupent la boîte de la flèche [bx0, bx1] x [0, 4]
    (repère de la flèche, rétrécie de `marge`) : [(type, id, x moyen)]."""
    x0, x1, y0, y1 = bx[0] + marge, bx[1] - marge, marge, 4.0 - marge
    out = []

    def coupe(P):
        Q = P - o
        X, Y = Q @ r, Q @ u
        for (xa, ya), (xb, yb) in zip(np.c_[X, Y][:-1], np.c_[X, Y][1:]):
            t0, t1 = 0.0, 1.0
            dx, dy = xb - xa, yb - ya
            ok = True
            for p_, q_ in ((-dx, xa - x0), (dx, x1 - xa), (-dy, ya - y0), (dy, y1 - ya)):
                if abs(p_) < 1e-12:
                    if q_ < 0:
                        ok = False
                        break
                    continue
                t = q_ / p_
                if p_ < 0:
                    t0 = max(t0, t)
                else:
                    t1 = min(t1, t)
                if t0 > t1:
                    ok = False
                    break
            if ok and t1 - t0 > 1e-9:
                return float(xa + dx * (t0 + t1) / 2)
        return None
    for lid, P, _ in lignes:
        if np.min(np.hypot(*(P - (o + u * 2.0)).T)) > 6.0:
            continue
        x = coupe(P)
        if x is not None:
            out.append(("ligne", lid, round(x, 3)))
    for kb in carte.bordures:
        P = kb["P"]
        if np.min(np.hypot(*(P - (o + u * 2.0)).T)) > 6.0:
            continue
        x = coupe(P)
        if x is not None:
            out.append(("bordure", kb["id"], round(x, 3)))
    return out


def _douteuse(o, u, r, lignes, carte):
    """Q5 : flèche douteuse si sa tige est à moins de 0,10 m de l'axe d'une ligne longitudinale parallèle (tiret
    d'axe pris pour une flèche), ou si son pied est à moins de 0,5 m d'une limite de voie OpenDRIVE."""
    from commun import aretes
    motifs = []
    S = o + np.outer(np.arange(0.0, Y_TETE + 1e-9, 0.5), u)
    for lid, P, _ in lignes:
        if np.min(np.hypot(*(P - S[2]).T)) > 3.0:
            continue
        A, B = P[:-1], P[1:]
        d, j, _ = distance_segments(S, A, B)
        seg = B[j] - A[j]
        cosv = np.abs(seg @ u) / np.maximum(np.hypot(*seg.T), 1e-9)
        if float(np.median(d)) < 0.10 and float(np.median(cosv)) > 0.95:
            motifs.append(f"tige à {float(np.median(d)):.2f} m de l'axe de la ligne {lid}")
    m = S[2]
    for l in carte.lanes:
        if l["type"] != "driving" or np.any(m < l["bmin"]) or np.any(m > l["bmax"]):
            continue
        if not dans_polygone(m[None], l["poly"])[0]:
            continue
        A, B = aretes(l["poly"])
        seg = B - A
        par = np.abs(seg @ u) / np.maximum(np.hypot(*seg.T), 1e-9) > 0.866
        if not par.any():
            continue
        d, _, _ = distance_segments(np.vstack([o, m]), A[par], B[par])
        if float(d.min()) < 0.5:
            motifs.append(f"pied à {float(d.min()):.2f} m d'une limite de la voie OpenDRIVE {l['route']}/{l['voie']}")
        break
    return motifs


def _roulable(carte, gab, o, u, r):
    i2, _ = _echantillons_gabarit(gab, o, u, r, pas=0.2)
    cl = carte.classe(i2)
    return bool(np.all(np.isin(cl, sorted(ROULABLES)))), round(float(np.mean(np.isin(cl, sorted(ROULABLES)))), 3)


def _mesure_voie(c, r, lignes, carte):
    g, d = _coupe(c, r, lignes, carte)
    src = None
    gauche = droite = None
    if g and d:
        gauche, droite = g[1], d[1]
        src = f"{g[2]} {g[3]} | {d[2]} {d[3]}"
    if src is None or droite - gauche > 4.6:
        v = _coupe_voie_xodr(c, r, carte)
        if v is not None:
            gauche, droite, src = v
    return gauche, droite, src


def _glisser(gab, o, u, r, lignes, carte, pas=0.5, portee=12.0):
    """Q5 (INF-FLE-004) : plus petit glissement en s (|Δs| ≤ 12 m) qui donne une voie ≥ boîte + 2 × 0,3 m, sans
    limite dans la boîte, boîte entièrement roulable. Renvoie (Δs, détail) ou (None, None)."""
    bx = gab["boite"]["x"]
    larg_min = (bx[1] - bx[0]) + 2 * MARGE_FLECHE
    cands = sorted([s for s in np.arange(-portee, portee + 1e-9, pas) if abs(s) > 1e-9], key=lambda s: (abs(s), -s))
    for ds in cands:
        o2 = o + u * ds
        if _coupe_boite(o2, u, r, bx, lignes, carte):
            continue
        c = o2 + r * ((bx[0] + bx[1]) / 2) + u * 2.0
        gauche, droite, src = _mesure_voie(c, r, lignes, carte)
        if src is None or droite - gauche < larg_min or droite - gauche > 4.6:
            continue
        x_o = float(-((bx[0] + bx[1]) / 2) - (gauche + droite) / 2)
        if (bx[0] + x_o) - (gauche - (gauche + droite) / 2) < MARGE_FLECHE - 1e-6 or \
                ((droite - (gauche + droite) / 2) - (bx[1] + x_o)) < MARGE_FLECHE - 1e-6:
            continue
        ok, _ = _roulable(carte, gab, o2, u, r)
        if not ok:
            continue
        return float(ds), dict(largeur_voie_m=round(float(droite - gauche), 3), bords=src,
                               origine_local=[round(float(v), 3) for v in o2])
    return None, None


def controler_fleches(carte, feats, lignes, existences=None, journal=None):
    gabs = _gabarits()
    existences = existences or {}
    out, corr = [], []
    for f in sorted(feats, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p["classe"] != "fleche" or p.get("gabarit") not in DECALAGE:
            continue
        ex = existences.get(p["id"])
        gab = gabs[p["gabarit"]]
        if ex and ex["existence"] in ("retirer", "absent_2026"):
            po = pose_fleche(f, gab)
            dout = _douteuse(po[0], po[1], po[2], lignes, carte) if po is not None else None
            out.append(dict(id=p["id"], gabarit=p.get("gabarit"), etat=p.get("etat"), source=p.get("src"),
                            statut="a_retirer" if ex["existence"] == "retirer" else "absent_2026",
                            q5_douteuse=dout or None,
                            note=f"verdict d'existence de la fusion ({ex['existence']}, {', '.join(ex['obs_preuve'])}) : "
                                 "hors contrôle des marquages (Q3)" + (" ; le test Q5 la juge aussi douteuse : " + " ; ".join(dout)
                                                                        if dout else "")))
            continue
        po = pose_fleche(f, gab)
        if po is None:
            out.append(dict(id=p["id"], statut="gabarit_non_apparie"))
            continue
        o, u, r, res = po
        pose_src = "polygone (ajustement rigide du gabarit)"
        if res > 0.05 and (p.get("pose") or {}).get("point_l93"):
            cap = math.radians(float(p["pose"]["cap_deg"]))
            u = np.array([math.cos(cap), math.sin(cap)])
            r = np.array([u[1], -u[0]])
            o = repere(np.asarray(p["pose"]["point_l93"], float)[None])[0]
            pose_src = f"champ pose (polygone non conforme au gabarit, résidu {res:.2f} m)"
        bx = gab["boite"]["x"]
        c = o + r * ((bx[0] + bx[1]) / 2) + u * 2.0
        rec = dict(id=p["id"], gabarit=p["gabarit"], etat=p.get("etat"), source=p.get("src"), branche=p.get("branche"),
                   residu_gabarit_m=round(res, 3), pose=pose_src, origine_local=[round(float(v), 3) for v in o],
                   cap_deg=round(math.degrees(math.atan2(u[0], u[1])) % 360, 2))
        if ex and ex["existence"] == "absent_2026_a_verifier":
            rec["drapeaux"] = ["absent_2026_a_verifier"]
        leve = p.get("src") == "gam"
        inf = str(p.get("src") or "").startswith("regle:INF-FLE-004")
        # Q5 (b) : flèche douteuse (tige sur une ligne, pied sur une limite de voie)
        dout = _douteuse(o, u, r, lignes, carte)
        # Q5 (c) : limites qui coupent la boîte
        coupees = _coupe_boite(o, u, r, bx, lignes, carte)
        if coupees:
            rec["limites_dans_boite"] = [f"{t} {i} (x {x:+.2f})" for t, i, x in coupees]
        if dout and not leve:
            rec.update(statut="fleche_douteuse", motifs=dout,
                       note="flèche douteuse (Q5) : " + " ; ".join(dout) + " ; aucun recalage, à vérifier (tiret de ligne ?)")
            if journal is not None and ex is None:
                journal.append(dict(entite=p["id"], nature="fleche_douteuse_solveur", fusion=None,
                                    coherence=dict(motifs=dout), decision="aucun recalage ; existence à vérifier par la fusion",
                                    renvoi="fusion_recensement"))
            out.append(rec)
            continue
        if coupees and not inf:
            rec.update(statut="voie_coupee", note="une limite de voie ou une bordure traverse la boîte de la flèche (Q5) : "
                                                  "jamais de recalage ; position ou bords de voie à vérifier")
            out.append(rec)
            continue
        gauche, droite, src = _mesure_voie(c, r, lignes, carte)
        larg_min = (bx[1] - bx[0]) + 2 * MARGE_FLECHE
        if inf and (coupees or src is None or droite - gauche < larg_min):
            ds, det = _glisser(gab, o, u, r, lignes, carte)
            motif = ("limite dans la boîte : " + ", ".join(rec.get("limites_dans_boite") or [])) if coupees else \
                (f"voie de {droite - gauche:.2f} m < boîte + 2 × 0,3 m ({larg_min:.2f} m)" if src else "voie non bornée")
            if ds is not None:
                o2 = np.asarray(det["origine_local"], float)
                rec.update(statut="glissement_s_propose", glissement_s_m=round(ds, 2), origine_proposee_local=det["origine_local"],
                           largeur_voie_apres_m=det["largeur_voie_m"], bords_apres=det["bords"],
                           note=f"répétition INF-FLE-004 ({motif}) : glissée de {ds:+.1f} m en s, voie de "
                                f"{det['largeur_voie_m']:.2f} m entièrement roulable (Q5)")
                corr.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(
                    repere(np.vstack([o, o2]), "l93"))}, "properties": dict(
                    id=p["id"], nature="glissement_s_fleche", gabarit=p["gabarit"], glissement_s_m=round(ds, 2),
                    regle="INF-FLE-004", statut=rec["statut"], source=p.get("src"), etat=p.get("etat"), conf="faible",
                    motif=motif)})
            else:
                rec.update(statut="suppression_proposee",
                           note=f"répétition INF-FLE-004 ({motif}) : aucune position à ±12 m en s n'offre une voie ≥ "
                                f"{larg_min:.2f} m entièrement roulable : flèche à supprimer (Q5)")
                corr.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": coords_geojson(
                    repere(o[None], "l93"))[0]}, "properties": dict(
                    id=p["id"], nature="suppression_fleche", gabarit=p["gabarit"], regle="INF-FLE-004", statut=rec["statut"],
                    source=p.get("src"), etat=p.get("etat"), conf="faible", motif=motif)})
            out.append(rec)
            continue
        if src is None or droite - gauche > 4.6:
            rec.update(statut="voie_non_bornee", note="pas de bords de voie de part et d'autre (lignes, bordures ou voie "
                                                      "OpenDRIVE de 2,2 à 4,6 m) : position latérale non contrôlable")
            out.append(rec)
            continue
        largeur = droite - gauche
        axe = (gauche + droite) / 2
        x_o = float(-((bx[0] + bx[1]) / 2) - axe)
        attendu = DECALAGE[p["gabarit"]]
        ecart = x_o - attendu
        marge_g = (bx[0] + x_o) - (gauche - axe)
        marge_d = (droite - axe) - (bx[1] + x_o)
        rec.update(bords=src, largeur_voie_m=round(float(largeur), 3), decalage_origine_m=round(x_o, 3), decalage_attendu_m=attendu,
                   ecart_m=round(ecart, 3), marge_gauche_m=round(float(marge_g), 3), marge_droite_m=round(float(marge_d), 3),
                   dans_voie=bool(marge_g >= -0.02 and marge_d >= -0.02))
        if abs(ecart) <= TOL_FLECHE and rec["dans_voie"]:
            rec["statut"] = "conforme"
        elif leve:
            rec["statut"] = "leve_ecart_garde"
            rec["note"] = (f"flèche levée GAM (σ 0,05 m, peinture réelle) à {ecart:+.2f} m de sa position normative dans la voie "
                           f"bornée par {src} : gardée (la réalité peut s'écarter de MQ-FLE-006) ; si l'écart dépasse 0,3 m, "
                           "les bords de voie décrits sont à vérifier")
        else:
            delta = -ecart * r
            o2 = o + delta
            rec.update(translation_m=[round(float(delta[0]), 3), round(float(delta[1]), 3)],
                       origine_proposee_local=[round(float(v), 3) for v in o2])
            ok_av, part_av = _roulable(carte, gab, o, u, r)
            ok_ap, part_ap = _roulable(carte, gab, o2, u, r)
            coupees2 = _coupe_boite(o2, u, r, bx, lignes, carte)
            rec.update(dans_chaussee_avant=ok_av, part_roulable_avant=part_av, dans_chaussee_apres=ok_ap,
                       part_roulable_apres=part_ap)
            if not ok_ap or coupees2:
                # Q5 (d) : aucun recalage dont le résultat n'est pas entièrement roulable
                rec["statut"] = "conflit_surface_marquage"
                rec["note"] = (f"recalage refusé : le résultat n'est pas entièrement roulable ({part_ap * 100:.0f} % roulable"
                               + (", limite dans la boîte : " + ", ".join(f"{t} {i}" for t, i, _ in coupees2) if coupees2 else "")
                               + f") ; position actuelle {part_av * 100:.0f} % roulable : conflit surface / marquage à arbitrer (Q5)")
            elif p.get("etat") in ("conserve",) and p.get("src") in ("ortho2022", "v1"):
                i1, e1 = _echantillons_gabarit(gab, o, u, r, tete=True)
                i2, e2 = _echantillons_gabarit(gab, o2, u, r, tete=True)
                c1, c2 = _contraste(i1, e1), _contraste(i2, e2)
                rec["preuve_image"] = dict(ortho="PCRS 5 cm 2022-05-10", mesure="tête seule (hors tige, Q5)",
                                           contraste_actuel=round(c1, 4), contraste_recale=round(c2, 4))
                rec["statut"] = "recalage_propose_avec_preuve" if c2 >= c1 - 0.01 else "garde_par_ortho"
                if rec["statut"] == "garde_par_ortho":
                    rec["note"] = (f"la tête de la flèche peinte en 2022 est à la position actuelle (contraste {c1:.3f}) et pas à "
                                   f"la position normative ({c2:.3f}) : flèche gardée, bords de voie décrits à vérifier")
            else:
                rec["statut"] = "recalage_propose"
                rec["preuve_image"] = None
                rec["note"] = ("flèche neuve 2025 (plan 2025 ou règle) : aucune image postérieure aux travaux ; recalage "
                               "par la règle MQ-FLE-006 sur les bords de voie décrits, résultat entièrement roulable")
            if rec["statut"] in ("recalage_propose", "recalage_propose_avec_preuve"):
                corr.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(
                    repere(np.vstack([o, o2]), "l93"))}, "properties": dict(
                    id=p["id"], nature="recalage_lateral_fleche", gabarit=p["gabarit"], ecart_m=round(ecart, 3),
                    translation_m=rec["translation_m"], regle="MQ-FLE-006", bords=src, statut=rec["statut"],
                    preuve=rec.get("preuve_image"), source=p.get("src"), etat=p.get("etat"),
                    conf="moyenne" if rec["statut"] == "recalage_propose_avec_preuve" else "faible")})
        out.append(rec)
    return out, corr


def _echantillons_marque(f, pas=0.25):
    g = f["geometry"]
    if g["type"] in ("LineString", "MultiLineString"):
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        out = []
        for c in parts:
            P = repere(np.asarray(c, float)[:, :2])
            for a, b in zip(P[:-1], P[1:]):
                L = float(np.hypot(*(b - a)))
                n = max(1, int(math.ceil(L / pas)))
                out.append(a + (b - a) * (np.arange(n + 1)[:, None] / n))
        return np.vstack(out) if out else np.zeros((0, 2))
    pts = []
    for poly in _polys_locaux(g):
        r = repere(poly[0])
        pts.append(r)
        x0, y0 = r.min(0)
        x1, y1 = r.max(0)
        X, Y = np.meshgrid(np.arange(x0, x1, pas), np.arange(y0, y1, pas))
        L = np.c_[X.ravel(), Y.ravel()]
        if len(L):
            pts.append(L[dans_polygone(L, [r])])
    return np.vstack(pts) if pts else np.zeros((0, 2))


def controler_marques(carte, feats):
    out, corr = [], []
    for f in sorted(feats, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        Q = _echantillons_marque(f)
        if not len(Q):
            continue
        jaune = str(p.get("couleur") or "") == "jaune"
        refs = carte.ref_bordure(Q, rayon=1.0, circulee=False)
        cl = carte.classe(Q)
        hors = np.zeros(len(Q), bool)
        debord = np.zeros(len(Q))
        for i, (rr, c) in enumerate(zip(refs, cl)):
            if c in ROULABLES:
                continue                        # parking ou piste derrière une bordure : marque admise
            if rr is not None and carte.bordures[rr["k"]].get("circulee_bas") and rr["t"] > 0.03:
                hors[i], debord[i] = True, rr["t"]
            elif c in NON_ROULABLES:
                hors[i], debord[i] = True, (rr["d"] if rr is not None else 1.0)
        part = float(hors.mean())
        if part == 0:
            continue
        exception = None
        if jaune:
            exception = "ligne jaune (sur bordure admise, MQ-STA-006)"
        elif p["classe"] == "symbole" and p["type"] in ("velo", "pmr"):
            exception = "figurine sur piste ou place (classe à vérifier)"
        elif p["classe"] == "passage":
            exception = "passage coupant un refuge à niveau"
        rec = dict(id=p["id"], classe=p["classe"], type=p["type"], source=p.get("src"), etat=p.get("etat"),
                   part_hors_chaussee=round(part, 3), debord_max_m=round(float(debord.max()), 3), exception=exception)
        leve = p.get("src") == "gam"
        ligne = f["geometry"]["type"] == "LineString" and p["classe"] in ("ligne", "transversale")
        n0 = int(np.argmax(~hors)) if (~hors).any() else len(hors)          # échantillons hors au début
        n1 = int(np.argmax(~hors[::-1])) if (~hors).any() else len(hors)    # et à la fin
        bouts = ligne and (~hors).any() and (n0 + n1 == int(hors.sum())) and (n0 + n1) <= 0.5 * len(hors)
        if exception:
            rec["statut"] = "exception"
        elif bouts and not leve:
            pas = 0.25
            rec.update(statut="raccourcissement_propose", raccourcir_debut_m=round(n0 * pas + (0.05 if n0 else 0), 2),
                       raccourcir_fin_m=round(n1 * pas + (0.05 if n1 else 0), 2),
                       note="extrémités au-delà de l'arête avant de la bordure : la marque s'arrête à l'arête chaussée "
                            "(TQ-MQG-014, MQ-DET-010)")
            c0 = Q[hors].mean(0)
            corr.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": coords_geojson(
                repere(c0[None], "l93"))[0]}, "properties": dict(
                id=p["id"], nature="raccourcissement_dans_chaussee", regle="MQ-DET-010", debord_m=rec["debord_max_m"],
                part_hors_chaussee=rec["part_hors_chaussee"], raccourcir_debut_m=rec["raccourcir_debut_m"],
                raccourcir_fin_m=rec["raccourcir_fin_m"], source=p.get("src"), etat=p.get("etat"), conf="moyenne")})
        elif debord.max() <= 0.5 and not leve and p["classe"] in ("ligne", "symbole", "transversale"):
            # translation vers la chaussée : opposée à la normale côté haut moyenne des échantillons hors chaussée
            ns = []
            for i in np.nonzero(hors)[0]:
                rr = refs[i]
                if rr is not None:
                    ns.append(np.array([-rr["tg"][1], rr["tg"][0]]))
            if ns:
                n = np.mean(ns, axis=0)
                n /= max(np.hypot(*n), 1e-9)
                dv = -n * (float(debord.max()) + 0.05)
                rec.update(statut="translation_proposee", translation_m=[round(float(dv[0]), 3), round(float(dv[1]), 3)])
                c0 = Q[hors].mean(0)
                corr.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords_geojson(
                    repere(np.vstack([c0, c0 + dv]), "l93"))}, "properties": dict(
                    id=p["id"], nature="translation_dans_chaussee", regle="MQ-DET-010", debord_m=rec["debord_max_m"],
                    part_hors_chaussee=rec["part_hors_chaussee"], translation_m=rec["translation_m"], source=p.get("src"),
                    etat=p.get("etat"), conf="faible")})
            else:
                rec["statut"] = "signalement"
        else:
            rec["statut"] = "signalement"
            if leve:
                rec["note"] = "marque levée GAM : la bordure ou la limite de chaussée décrite est à revoir"
            elif p["classe"] == "fleche":
                rec["note"] = ("flèche hors chaussée : jamais translatée ici (Q5) ; voir le contrôle des flèches "
                               "(conflit surface / marquage)")
        out.append(rec)
    return out, corr


def controler(carte, revue=None, faire_planches=True, existences=None, journal=None):
    """Contrôle des flèches et des marques. `existences` (Q3) : verdicts d'existence de la fusion ; les marquages
    « retirer » / « absent_2026 » sont hors contrôle (et ne bornent plus les voies), « absent_2026_a_verifier »
    est signalé ; un retrait de la fusion contredit par un levé GAM 2026 part dans le journal des désaccords."""
    feats = lire_geojson(BASE_V2 / "marquages.geojson")
    existences = existences or {}
    retires = {k for k, e in existences.items() if e["existence"] in ("retirer", "absent_2026")}
    for f in feats:
        p = f["properties"]
        e = existences.get(p["id"])
        if journal is not None and e and e["existence"] in ("retirer", "absent_2026") and p.get("src") == "gam"                 and str(e.get("date") or "") <= "2025-12-05":
            journal.append(dict(entite=p["id"], nature="retrait_fusion_contre_leve_gam_2026",
                                fusion=dict(existence=e["existence"], obs=e["obs_preuve"], date=e["date"]),
                                coherence=dict(source="levé GAM 2026", etat=p.get("etat")),
                                decision="verdict de la fusion appliqué au contrôle (hors contrôle) ; le levé GAM 2026 le "
                                         "contredit avec une preuve antérieure aux travaux : à arbitrer (terrain)",
                                renvoi="fusion_recensement"))
    actifs = [f for f in feats if f["properties"]["id"] not in retires]
    lignes = _lignes(actifs)
    fl, c1 = controler_fleches(carte, feats, lignes, existences=existences, journal=journal)
    mq, c2 = controler_marques(carte, actifs)
    exclus = list(dict(id=f["properties"]["id"], classe=f["properties"]["classe"], type=f["properties"]["type"],
                         existence=existences[f["properties"]["id"]]["existence"],
                         obs=existences[f["properties"]["id"]]["obs_preuve"]) for f in feats
                    if f["properties"]["id"] in retires and f["properties"]["classe"] != "fleche")
    exclus = sorted(exclus, key=lambda x: x["id"])
    a_verifier = sorted(k for k, e in existences.items() if e["existence"] == "absent_2026_a_verifier"
                        and any(f["properties"]["id"] == k for f in feats))
    import collections
    comptes = dict(fleches=dict(sorted(collections.Counter(r["statut"] for r in fl).items())),
                   marques_hors_chaussee=dict(sorted(collections.Counter(r["statut"] for r in mq).items())),
                   hors_controle_q3=len(exclus) + sum(1 for r in fl if r["statut"] in ("a_retirer", "absent_2026")),
                   absent_2026_a_verifier=a_verifier)
    doc = dict(schema="pj_coherence_marquages/0.2", methode=__doc__.strip(), source="base/marquages.geojson (lecture seule)",
               comptes=comptes, fleches=fl, marques=mq, hors_controle_q3=exclus)
    ecrire_json(SORTIE, arrondi(doc, 4))
    ecrire_geojson(CORR, sorted(c1 + c2, key=lambda f: f["properties"]["id"]), "corrections_marquages",
                   {"schema": "pj_coherence/0.3", "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98)",
                    "role": "propositions de recalage des marquages (flèches centrées MQ-FLE-006 entièrement roulables, "
                            "glissements et suppressions INF-FLE-004, marques dans la chaussée MQ-DET-010), à arbitrer par le "
                            "propriétaire de base/marquages.geojson"})
    return dict(comptes=comptes, fleches=fl, marques=mq, corrections=c1 + c2, hors_controle_q3=exclus)
