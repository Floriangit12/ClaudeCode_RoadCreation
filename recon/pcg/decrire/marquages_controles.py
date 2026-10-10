"""Contrôles géométriques et de cohérence de la famille marquages (appelés par valider.py).

- correspondance v1 : chacun des 996 marquages v1 a un devenir, une seule fois ; entités citées
  existantes et liens réciproques (lien_v1 <-> correspondance) ;
- lignes : longueur_m = longueur de la géométrie (± 1 cm), modulation cohérente (trait, vide, phase),
  interruptions dans [0, L] triées et disjointes ; ancrage xodr : axe recalculé depuis le .xodr à
  moins de 5 mm de la géométrie, |t_off| ≤ 0,30 m + largeur/2 (ligne dans les bords de voie) ;
- recouvrements : aucune paire de lignes quasi parallèles dont les parties peintes (tirets, traits)
  se recouvrent sur plus de 0,20 m ;
- zébras : ≥ 75 % de chaque bande (21 points) dans la chaussée (voies OpenDRIVE roulables, masque
  chaussee_2026, surfaces v1 chaussée / parking / accès / piste / autre en enrobé) ;
- polygones : aucun contour en marches d'escalier (critère commun.contour_raster) ;
compléments bloquants (revue du 10/10, deuxième tour) :
- écart latéral au levé GAM par entité : p95 < 0,05 m (lignes GAM d'une autre marque exclues : gam_refs_exclues) ;
- modulation_source « IISR » => trait et vide de la table IISR à 1 cm près ;
- largeurs T3 (hors bandes 5u) toutes égales à marquages_lignes.LARGEUR_T3 (tableau des largeurs dans mesures) ;
- même limite de voie (même chaîne de bords xodr, |Δt_off| < 0,30 m) : parties peintes de deux lignes disjointes en s (pas
  de baïonnette) ;
- recouvrements entre entités (empreintes rastérisées au pas de 2 cm, découpes retirées) ≤ 0,01 m², hors surface colorée,
  fantômes et paires ligne / ligne (contrôle dédié) ;
- dégagement des bordures : aucune partie peinte dans un sol surélevé (marquages_bordures.distance_signee < −1 cm) hors
  marques justifiées (support_sol) et fantômes ;
- correspondance : devenir garde_non_fabrique => entité marquée fabrication.statut non_fabrique.
"""
import collections
import math

import numpy as np

import marquages_commun as M
from commun import DONNEES, abscisses, anneaux, dans_polygone, distance_segments, lire_geojson, repere


def _local(c):
    return repere(np.asarray(c, float)[..., :2])


def _pieces(p, P):
    """Parties peintes (σ0, σ1) d'une ligne le long de sa géométrie locale P."""
    L = float(abscisses(P)[-1])
    if p["type"] == "discontinue":
        T, V, ph = p["trait_m"], p["vide_m"], p["phase_m"]
        per = T + V
        k0 = math.floor(-ph / per) - 1
        iv = [(ph + k * per, ph + k * per + T) for k in range(k0, int((L - ph) / per) + 2)]
    else:
        iv = [(0.0, L)]
    iv = [(max(0.0, a), min(L, b)) for a, b in iv if b > 0 and a < L]
    for a0, b0 in p.get("interruptions", []):
        out = []
        for a, b in iv:
            if b <= a0 or a >= b0:
                out.append((a, b))
            else:
                if a < a0:
                    out.append((a, a0))
                if b > b0:
                    out.append((b0, b))
        iv = out
    return [(a, b) for a, b in iv if b - a > 1e-3]


def _echantillons(P, iv, pas=0.05):
    from commun import point_a
    pts, tgs = [], []
    for a, b in iv:
        s = np.arange(a, b + 1e-9, pas)
        q, t = point_a(P, s)
        pts.append(q)
        tgs.append(t)
    return (np.vstack(pts), np.vstack(tgs)) if pts else (np.zeros((0, 2)), np.zeros((0, 2)))


def _segments(P, iv):
    from commun import sous_polyligne
    A, B = [], []
    for a, b in iv:
        Q = sous_polyligne(P, a, b)
        if len(Q) >= 2:
            A.append(Q[:-1])
            B.append(Q[1:])
    return (np.vstack(A), np.vstack(B)) if A else (np.zeros((0, 2)), np.zeros((0, 2)))


def controles(feats, corr):
    err, warn = [], []
    ids = {f["properties"]["id"]: f for f in feats}
    v1 = {f["properties"]["id"] for f in lire_geojson(DONNEES / "marquages/marquages_2026.geojson")}
    # ---- correspondance
    vus = collections.Counter(c["properties"]["id"] for c in corr)
    for mq, n in vus.items():
        if n != 1:
            err.append(f"{mq} : {n} lignes de correspondance")
    for mq in sorted(v1 - set(vus)):
        err.append(f"{mq} : marquage v1 sans devenir")
    for mq in sorted(set(vus) - v1):
        err.append(f"{mq} : absent du paquet v1")
    for c in corr:
        p = c["properties"]
        if p["devenir"] == "garde_non_fabrique":
            f = ids.get(p["entite"])
            if f is not None and (f["properties"].get("fabrication") or {}).get("statut") != "non_fabrique":
                err.append(f"{p['id']} : garde_non_fabrique mais {p['entite']} n'est pas marquée non fabriquée")
        if p["devenir"] != "retire":
            f = ids.get(p["entite"])
            if f is None:
                err.append(f"{p['id']} : entité {p['entite']} absente")
            elif p["id"] not in f["properties"]["lien_v1"]:
                err.append(f"{p['id']} : absent de lien_v1 de {p['entite']}")
    ent_de = {c["properties"]["id"]: c["properties"]["entite"] for c in corr}
    for i, f in ids.items():
        for mq in f["properties"]["lien_v1"]:
            if ent_de.get(mq) != i:
                err.append(f"{i} : lien_v1 {mq} rattaché à {ent_de.get(mq)}")
    # ---- lignes
    reseau, chaines = None, None
    lignes = []
    for i, f in sorted(ids.items()):
        p = f["properties"]
        if p["classe"] not in ("ligne", "transversale"):
            continue
        P = _local(f["geometry"]["coordinates"])
        L = float(abscisses(P)[-1])
        if abs(L - p["longueur_m"]) > 0.01:
            err.append(f"{i} : longueur_m {p['longueur_m']} ≠ géométrie {L:.3f}")
        if p["type"] == "discontinue" or p["classe"] == "transversale":
            if p["phase_m"] >= p["trait_m"] + p["vide_m"] + 1e-6:
                err.append(f"{i} : phase_m hors période")
        prec = 0.0
        for a, b in p.get("interruptions", []):
            if a < prec - 1e-6 or b < a or b > L + 0.01:
                err.append(f"{i} : interruption [{a}, {b}] hors [0, {L:.3f}] ou non triée")
            prec = b
        anc = p.get("ancrage", {})
        if anc.get("type") == "xodr" and "bords" in anc:
            if reseau is None:
                import marquages_lignes as LG
                import xodr_echantillonne as X
                reseau = X.lire_xodr()
                chaines = {}
                for ch in LG.chaines_reseau(reseau):
                    for b in ch.bords:
                        chaines[(ch.route, round(b.section_s, 3), b.voie)] = ch
            b0 = anc["bords"][0]
            ch = chaines.get((anc["route"], round(b0["section_s"], 3), b0["voie"]))
            if ch is None:
                err.append(f"{i} : bord d'ancrage {anc['route']}/{b0['section_s']}/{b0['voie']} introuvable")
            else:
                Q = ch.axe(anc["t_off_m"], anc["s0"], anc["s1"], profil=anc.get("t_off_profil"))
                d, _, _ = distance_segments(Q, P[:-1], P[1:])
                if d.max() > 0.005:
                    err.append(f"{i} : axe recalculé depuis l'ancrage xodr à {d.max() * 1000:.1f} mm de la géométrie")
                if abs(anc["t_off_m"]) > 0.30 + p["largeur_m"] / 2:
                    err.append(f"{i} : t_off {anc['t_off_m']} hors des bords de voie (± 0,30 + largeur/2)")
        if p["classe"] == "ligne":
            lignes.append((i, p, P))
    chaines = chaines or None
    # ---- recouvrements de parties peintes
    data = []
    for i, p, P in lignes:
        iv = _pieces(p, P)
        q, t = _echantillons(P, iv)
        A, B = _segments(P, iv)
        bb = (*P.min(axis=0) - 0.4, *P.max(axis=0) + 0.4)
        data.append((i, p, q, t, A, B, bb))
    n_rec = 0
    for a in range(len(data)):
        ia, pa, qa, ta, _, _, ba = data[a]
        for b in range(a + 1, len(data)):
            ib, pb, qb, tb, Ab, Bb, bb = data[b]
            if ba[2] < bb[0] or bb[2] < ba[0] or ba[3] < bb[1] or bb[3] < ba[1] or len(qa) == 0 or len(Ab) == 0:
                continue
            d, j, _ = distance_segments(qa, Ab, Bb)
            seg = Bb[j] - Ab[j]
            seg /= np.maximum(np.hypot(*seg.T), 1e-12)[:, None]
            par = np.abs(np.einsum("ij,ij->i", seg, ta)) > 0.9
            rec = (d < (pa["largeur_m"] + pb["largeur_m"]) / 2 - 0.005) & par
            if rec.sum() * 0.05 > 0.20 + 1e-6:
                n_rec += 1
                err.append(f"{ia} / {ib} : parties peintes superposées sur {rec.sum() * 0.05:.2f} m")
    # ---- zébras dans la chaussée
    roul = []
    for f in lire_geojson(DONNEES / "opendrive/lanes_2026.geojson"):
        t = f["properties"].get("type")
        if t in ("driving", "biking", "bus") or (t is None and f["properties"].get("jonction")):
            roul += [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
    for f in lire_geojson(DONNEES / "surfaces/surfaces_2026.geojson"):
        q = f["properties"]
        if q.get("classe") in ("chaussee", "parking", "acces_riverain", "piste_cyclable") or (q.get("classe") == "autre" and q.get("materiau") == "enrobe"):
            roul += [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
    for f in lire_geojson(DONNEES / "relief/relief_zones_2026.geojson"):
        if f["properties"].get("zone") == "chaussee_2026":
            roul += [[repere(r) for r in poly] for poly in anneaux(f["geometry"])]
    hors = 0
    for i, f in sorted(ids.items()):
        p = f["properties"]
        if p["classe"] != "passage" or p["type"] != "zebra":
            continue
        A, B = _local(f["geometry"]["coordinates"])
        h = math.radians(p["cap_bandes_deg"])
        u = np.array([math.cos(h), math.sin(h)])
        n = np.array([-u[1], u[0]])
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        nb = p["nb_emplacements"] if "nb_emplacements" in p else p["nb_bandes"]
        for k in range(nb):
            if k in p["coupures"]:
                continue
            c = A + ax * k * p["pas_axe_m"]
            ga, gb = np.meshgrid(np.linspace(-0.45, 0.45, 7), np.linspace(-0.4, 0.4, 3))
            pts = c + np.outer(ga.ravel() * p["longueur_bande_m"], u) + np.outer(gb.ravel() * p["largeur_bande_m"], n)
            dedans = np.zeros(len(pts), bool)
            for poly in roul:
                dedans |= dans_polygone(pts, poly)
            if dedans.mean() < 0.75:
                hors += 1
                msg = f"{i} : bande {k} hors de la chaussée ({dedans.mean():.0%} dedans)"
                if dedans.mean() < 0.5 and p["prov"]["geometrie"]["src"] != "ortho2022":
                    err.append(msg)
                else:
                    warn.append(msg + " : référence de chaussée incomplète ou passage 2022")
    # ---- marches d'escalier (critère raster v1 + détecteur élargi) ; géométrie d'origine raster non reconstruite
    for i, f in sorted(ids.items()):
        g = f["geometry"]
        if g["type"] in ("Polygon", "MultiPolygon"):
            for poly in anneaux(g):
                if any(M.contour_raster(r) for r in poly):
                    err.append(f"{i} : contour en marches d'escalier")
        p = f["properties"]
        if p.get("contour_raster_v1") and p.get("simplification") not in (None, "rectangle", "ruban", "redressé") \
                and not str(p.get("simplification", "")).startswith("gabarit") and "+" not in str(p.get("simplification", ""))                 and not str(p.get("simplification", "")).endswith("rectangles"):
            err.append(f"{i} : contour d'origine raster gardé sans reconstruction ({p.get('simplification')})")
    # ---- mesures bloquantes : écart latéral et phase des tirets contre le GAM, phase contre l'ortho 2022
    mes = mesures(feats)
    if mes["lateral_gam"]["p95_m"] is not None and mes["lateral_gam"]["p95_m"] >= 0.05:
        err.append(f"écart latéral au levé GAM : p95 {mes['lateral_gam']['p95_m']:.3f} m ≥ 0,05")
    if mes["phase_gam"]["p95_m"] is not None and mes["phase_gam"]["p95_m"] >= 0.10:
        err.append(f"phase des tirets contre les tirets levés GAM : p95 {mes['phase_gam']['p95_m']:.3f} m ≥ 0,10")
    if mes["phase_ortho"]["p95_m"] is not None and mes["phase_ortho"]["p95_m"] >= 0.10:
        err.append(f"phase des tirets contre l'ortho 2022 : p95 {mes['phase_ortho']['p95_m']:.3f} m ≥ 0,10")
    for c in mes["phase_ortho"]["conflits_gam"]:
        warn.append(f"{c['id']} : phase prise sur les tirets levés GAM, l'ortho 2022 indique {c['delta_m']:+.2f} m (corrélation {c['corr_max']:.2f})")
    for i in mes["lateral_gam"]["entites_p95_sup_0_05"]:
        err.append(f"{i} : écart latéral au levé GAM p95 {mes['lateral_gam']['par_entite'][i]:.3f} m ≥ 0,05")
    e2, w2 = controles_reprises(feats, chaines)
    return err + e2, warn + w2


def entite_locale(f):
    """Entité au format interne de la description (coordonnées locales) depuis une feature GeoJSON."""
    p = dict(f["properties"])
    g = f["geometry"]
    e = dict(p)
    if g["type"] == "LineString":
        e["geom"] = ("LineString", _local(g["coordinates"]))
    elif g["type"] == "MultiLineString":
        e["geom"] = ("MultiLineString", [_local(x) for x in g["coordinates"]])
    else:
        e["geom"] = (g["type"], [[_local(r) for r in poly] for poly in anneaux(g)])
    if "files" in p:
        e["files"] = [dict(fl, axe=_local(fl["axe_l93"])) for fl in p["files"]]
    if "pose" in p:
        e["pose"] = dict(p["pose"], origine_local=_local(np.asarray(p["pose"]["point_l93"], float)[None])[0])
    if "decoupes" in p:
        e["decoupes"] = [dict(d, polygone_local=_local(d["polygone_l93"])) for d in p["decoupes"]]
    return e


def controles_reprises(feats, chaines=None):
    """Contrôles bloquants ajoutés au deuxième tour de revue (voir l'en-tête)."""
    import marquages_bordures as MB
    import marquages_lignes as LG
    import marquages_reprises as RP
    err, warn = [], []
    tab = LG.modulations()
    ents = {f["properties"]["id"]: entite_locale(f) for f in feats}
    # modulation « IISR » = table
    for i, e in sorted(ents.items()):
        if e.get("modulation_source") == "IISR":
            nom = tab.get(e.get("modulation"))
            if nom is None or abs(e["trait_m"] - nom["trait_m"]) > 0.01 or abs(e["vide_m"] - nom["vide_m"]) > 0.01:
                err.append(f"{i} : modulation_source IISR mais {e.get('modulation')} {e.get('trait_m')}/{e.get('vide_m')} hors table")
    # largeurs T3
    for i, e in sorted(ents.items()):
        if e["classe"] == "ligne" and str(e.get("modulation", "")).replace("_site", "") == "T3" and e.get("role") != "bande" \
                and abs(e["largeur_m"] - LG.LARGEUR_T3) > 1e-6:
            err.append(f"{i} : T3 de largeur {e['largeur_m']} ≠ {LG.LARGEUR_T3} (largeurs T3 harmonisées)")
    # même limite de voie : parties peintes disjointes en s
    if chaines is None:
        import xodr_echantillonne as X
        chaines = {}
        for ch in LG.chaines_reseau(X.lire_xodr()):
            for b in ch.bords:
                chaines[(ch.route, round(b.section_s, 3), b.voie)] = ch
    par_ch = {}
    for i, e in sorted(ents.items()):
        a = e.get("ancrage", {})
        if e["classe"] != "ligne" or a.get("type") != "xodr" or not a.get("bords"):
            continue
        b0 = a["bords"][0]
        ch = chaines.get((a["route"], round(b0["section_s"], 3), b0["voie"]))
        if ch is None:
            continue
        P = e["geom"][1]
        L = float(abscisses(P)[-1])
        k = (a["s1"] - a["s0"]) / max(L, 1e-9)
        iv = [(a["s0"] + x * k, a["s0"] + y * k) for x, y in _pieces(e, P)]
        par_ch.setdefault(ch.cle, []).append((i, float(a["t_off_m"]), iv, e["type"], float(e["largeur_m"])))
    for cle, ls in sorted(par_ch.items()):
        for x in range(len(ls)):
            for y in range(x + 1, len(ls)):
                (ia, ta, va, ya, wa), (ib, tb, vb, yb, wb) = ls[x], ls[y]
                # lignes mixtes (continue + discontinue juxtaposées) : permises si leurs peintures ne se touchent pas
                if abs(ta - tb) >= 0.30 or (ya != yb and abs(ta - tb) >= (wa + wb) / 2 + 0.02):
                    continue
                rec = sum(max(0.0, min(b1, b2) - max(a1, a2)) for a1, b1 in va for a2, b2 in vb)
                if rec > 0.05:
                    err.append(f"{ia} / {ib} : même limite de voie ({cle}, Δt {abs(ta - tb):.2f} m), parties peintes superposées sur {rec:.2f} m de route (baïonnette)")
    # recouvrements entre entités
    for a, b, aire in RP.recouvrements(list(ents.values())):
        err.append(f"{a} / {b} : recouvrement de {aire:.4f} m²")
    # dégagement des bordures
    n_ok = 0
    for i, e in sorted(ents.items()):
        if e.get("support_sol") or e["classe"] == "fantome" or (e.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        if e["classe"] in ("ligne", "transversale"):
            s_, Q, T = MB._echantillons(e, e["geom"][1])
            if not len(Q):
                continue
            sd, _, tg, ob = MB.distance_signee(Q)
            c = np.abs((T * tg).sum(axis=1))
            w = float(e["largeur_m"])
            reach = np.where(c >= MB.PARALLELE, sd - w / 2, sd - (w / 2) * np.sqrt(np.maximum(0.0, 1.0 - c ** 2)))
            dedans = reach < -0.01
        else:
            polys = RP.empreinte(e)
            if not polys:
                continue
            Q = MB._bord_polys(polys, 0.05)
            cut = RP._decoupes(e)
            if cut:
                from commun import dans_polygones
                Q = Q[~dans_polygones(Q, cut)]
            if not len(Q):
                continue
            sd, _, _, ob = MB.distance_signee(Q, e["classe"] == "passage")
            dedans = sd < -0.01
        if dedans.sum() >= 3:
            noms = sorted({str(o[0]) for k, o in enumerate(ob) if dedans[k] and o is not None})
            err.append(f"{i} : {int(dedans.sum())} points peints dans un sol surélevé ou une bordure ({', '.join(noms[:3])})")
        else:
            n_ok += 1
    return err, warn


def _q(v, q):
    return round(float(np.percentile(v, q)), 4) if len(v) else None


def mesures(feats):
    """Mesures de conformité de la famille (recalculées sur le GeoJSON) :
    - lateral_gam : distance des axes levés GAM (médiane des paires de bords) des MQ liés (ou des lignes GAM d'un
      ajout) à l'axe de l'entité, au pas de 0,10 m, sur ses parties peintes ;
    - phase_gam : tirets levés isolés GAM (marquages_gam.tirets_leves) recouvrant une partie peinte d'une ligne
      discontinue / segment / transversale : écart des milieux ;
    - phase_ortho : décalage de phase optimal (marquages_ortho.phase_ortho) des lignes discontinues des états 2022 d'au
      moins 2 tirets entiers à pic net (≥ 0,3), hors lignes phasées sur des tirets levés GAM (conflits listés)."""
    import marquages_gam as MG
    import marquages_ortho as MO
    from commun import densifier, lire_geojson, projeter, point_a
    v1 = {f["properties"]["id"]: f["properties"] for f in lire_geojson(DONNEES / "marquages/marquages_2026.geojson")}
    lat, lat_ent, ph, ph_det, orth, conflits = [], {}, [], [], [], []
    for f in sorted(feats, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p["classe"] not in ("ligne", "transversale"):
            continue
        P = _local(f["geometry"]["coordinates"])
        L = float(abscisses(P)[-1])
        q = dict(p, type="discontinue") if p["classe"] == "transversale" else p
        iv = _pieces(q, P)
        refs = sorted(({int(k) for mq in p["lien_v1"] for k in (v1[mq].get("gam_ref") or "").split(",") if k}
                       | set((p.get("ajout") or {}).get("gam", []))) - set(p.get("gam_refs_exclues", [])))
        if refs and iv:
            d_e = []
            for G, _, _ in MG.axes_leves(refs):
                Q, _ = densifier(G, 0.10)
                s, d, _ = projeter(P, Q)
                ok = (s > 0.05) & (s < L - 0.05) & (d < 0.5) & np.array([any(a <= x <= b for a, b in iv) for x in s], bool)
                d_e.append(d[ok])
            d_e = np.concatenate(d_e) if d_e else np.zeros(0)
            if len(d_e):
                lat.append(d_e)
                lat_ent[p["id"]] = _q(d_e, 95)
        # phase : motif des tirets sans les interruptions (marques voisines, bordures), qui ne sont pas des erreurs de phase
        ivp = _pieces(dict(q, interruptions=[]), P)
        if q["type"] in ("discontinue", "segment") and ivp:
            iv_ph = ivp
            for a, b, t, ks in MG.tirets_leves(P):
                if a < -0.30 or b > L + 0.30:
                    continue
                best = max(iv_ph, key=lambda x: min(x[1], b) - max(x[0], a))
                if min(best[1], b) - max(best[0], a) <= 0:
                    continue
                e = abs(0.5 * (a + b) - 0.5 * (best[0] + best[1]))
                ph.append(e)
                ph_det.append([p["id"], list(ks), round(e, 3)])
        if p["classe"] == "ligne" and p["type"] == "discontinue" and p["etat"] in MO.ETATS_2022:
            r = MO.phase_ortho(P, p)
            if r is None or r["n_tirets"] < 2 or r["corr_max"] < MO.PIC_NET:
                continue
            if (p.get("prov", {}).get("phase_m") or {}).get("src") == "gam":
                if abs(r["delta_m"]) >= 0.10:
                    conflits.append(dict(id=p["id"], **r))
                continue
            orth.append([p["id"], r["delta_m"], r["corr_max"]])
    lat = np.concatenate(lat) if lat else np.zeros(0)
    do = np.abs([o[1] for o in orth])
    import marquages_lignes as LG
    t3 = collections.Counter(str(f["properties"]["largeur_m"]) for f in feats if f["properties"]["classe"] == "ligne"
                             and str(f["properties"].get("modulation", "")).replace("_site", "") == "T3")
    return {"largeurs_t3": {"regle": f"T3 hors bandes 5u : {LG.LARGEUR_T3} m (critère phase 2, décision n° 10 en attente)",
                            "comptes": dict(sorted(t3.items()))},
            "lateral_gam": {"n": int(len(lat)), "p50_m": _q(lat, 50), "p95_m": _q(lat, 95), "max_m": _q(lat, 100),
                            "entites_p95_sup_0_05": sorted(k for k, v in lat_ent.items() if v >= 0.05),
                            "par_entite": {k: v for k, v in sorted(lat_ent.items()) if v >= 0.05}},
            "phase_gam": {"n": len(ph), "p50_m": _q(ph, 50), "p95_m": _q(ph, 95), "max_m": _q(ph, 100), "detail": ph_det},
            "phase_ortho": {"n_lignes_pic_net": len(orth), "p50_m": _q(do, 50), "p95_m": _q(do, 95), "max_m": _q(do, 100),
                            "sup_0_10": [o for o in orth if abs(o[1]) >= 0.10], "conflits_gam": conflits}}


if __name__ == "__main__":
    import json
    import sys
    from commun import SORTIE, lire_geojson
    base = sys.argv[1] if len(sys.argv) > 1 else str(SORTIE / "base")
    m = mesures(lire_geojson(base + "/marquages.geojson"))
    print(json.dumps(m, ensure_ascii=False, indent=1))
