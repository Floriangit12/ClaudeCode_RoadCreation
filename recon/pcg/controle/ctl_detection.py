"""Contrôles de la détection, de la fusion et de la preuve image (DET-*, FUS-*, VAL-IMG-007) sur la description des
marquages (attributs detection, classement, sources, score, zone_etat), les hypothèses (marquages_hypotheses
.geojson), l'évaluation des détecteurs, le levé LiDAR des bordures et les tuiles de contraste de l'ortho 2022.
État cible (K.E) : FUS-SRC-001 lit la table d'admissibilité de l'état (E.v_temporelle_marquages, la même que
decrire/marquages_sources) ; ortho 2022 et plan 2025 sont lus par E.source. Les règles « plan2025 » et les
attendus de site de l'état sont traités en phase 6 (surcharge etats/<id>.regles.json).
"""
import collections
import json
import math

import numpy as np

import ctl_commun as K
from ctl_commun import regle, r4, stats
import ctl_marquages as M

ORTHO2022 = K.EC.source("ortho2022", K.SITE / "ortho5cm_2022")
PLAN2025 = K.EC.source("plan2025", K.SITE / "plan_projet_2025")


def detectees(ctx, classe, src=None):
    out = {}
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p["classe"] != classe or not p.get("detection") or not ctx.fabrique_marquage(p):
            continue
        if src and p.get("src") != src:
            continue
        out[i] = e
    return out


# =========================================================================== flèches
@regle("DET-FLE-003", "description", "mineur",
       "Flèches détectées sur l'ortho 2022 (src ortho2022, attribut detection) : NCC ≥ 0,75 (sûre) ou ≥ 0,60 avec une "
       "marge ≥ 0,05 sur le gabarit tiret ; une détection plus faible n'est posée qu'avec a_verifier. Unité : flèche "
       "détectée sur l'ortho.", "implemente")
def det_fle_003(ctx, R):
    for i, e in detectees(ctx, "fleche", "ortho2022").items():
        d = e["p"]["detection"]
        ncc, nt = float(d.get("ncc", 0)), float(d.get("ncc_tiret", 0))
        ok = ncc >= 0.75 or (ncc >= 0.60 and ncc - nt >= 0.05) or e["p"].get("a_verifier")
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=r4(ncc, 3), seuil="NCC ≥ 0,75 ou ≥ 0,60 + marge 0,05",
                 detail=f"NCC {ncc:.3f}, tiret {nt:.3f}", ecart=0.75 / max(ncc, 0.05))


@regle("DET-FLE-004", "description", "mineur",
       "Flèches détectées sur le plan projet 2025 (src plan2025, attribut detection) : NCC ≥ 0,80 (sûre) ou ≥ 0,65 "
       "(candidat, posé a_verifier). Unité : flèche détectée sur le plan.", "implemente")
def det_fle_004(ctx, R):
    for i, e in detectees(ctx, "fleche", "plan2025").items():
        ncc = float(e["p"]["detection"].get("ncc", 0))
        ok = ncc >= 0.80 or (ncc >= 0.65 and e["p"].get("a_verifier")) or (ncc >= 0.65 and e["p"].get("conflit_norme"))
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=r4(ncc, 3), seuil="NCC ≥ 0,80 (≥ 0,65 à vérifier)",
                 detail=f"NCC {ncc:.3f}" + (" (sans étiquette a_verifier)" if ncc < 0.8 else ""), ecart=0.8 / max(ncc, .05))


@regle("DET-FLE-005", "description", "mineur",
       "A priori de réseau des flèches : origine (centroïde) dans une fenêtre latérale de ±0,50 m autour du milieu de "
       "sa voie OpenDRIVE après le décalage normatif MQ-FLE-006 (±1,50 m si la voie fait plus de 4 m). Unité : flèche "
       "posée dans une voie.", "implemente")
def det_fle_005(ctx, R):
    dec = next(r for r in ctx.regles["regles"] if r["id"] == "MQ-FLE-006")["parametres"]["decalage_tige_m"]
    for i, e in M.fleches(ctx).items():
        c = M.centroide(e["poly"][0])
        v = M.voie_de(ctx, c)
        if v is None:
            continue
        rid, voie, s = v
        r = ctx.reseau[rid]
        sec = r.section(s)
        tb = r.t_bords(np.array([s]), sec)
        vi = voie - 1 if voie > 0 else voie + 1
        tc = 0.5 * float(tb[voie][0] + tb[vi][0])
        larg = abs(float(tb[voie][0] - tb[vi][0]))
        xr, yr, hr = r.reference(np.array([s]))
        nrm = np.array([-math.sin(hr[0]), math.cos(hr[0])])
        t = float((c - np.array([xr[0], yr[0]])) @ nrm)
        # décalage normatif exprimé dans le sens de circulation (x à droite) : t croît à gauche du sens de s
        sens = 1 if voie < 0 else -1
        attendu = tc - sens * float(dec.get(e["p"].get("gabarit"), 0.0))
        lim = 1.5 if larg > 4.0 else 0.5
        d = abs(t - attendu)
        R.tester(d <= lim, entite=i, xy=c, valeur=r4(d, 3), seuil=f"≤ {lim} m",
                 detail=f"décalé de {d:.2f} m du milieu de la voie {rid}/{voie} (largeur {larg:.2f} m, décalage normatif "
                        f"{dec.get(e['p'].get('gabarit'), 0.0)})", ecart=d / lim)


def typage_par_parties(sc):
    """DET-FLE-006 : type attendu à partir des NCC des gabarits."""
    S0, SD, SG = sc.get("TD", 0), sc.get("TD_TAD", 0), sc.get("TD_TAG", 0)
    t_max = max(("TAG", sc.get("TAG", 0)), ("TAD", sc.get("TAD", 0)), key=lambda x: x[1])
    if t_max[1] - S0 >= 0.15:
        return t_max[0]
    if SD >= S0 - 0.05 and SG >= S0 - 0.05 and abs(SD - SG) < 0.07:
        return "trident"
    if abs(SD - SG) >= 0.07:
        return "TD_TAD" if SD > SG else "TD_TAG"
    return "TD"


@regle("DET-FLE-006", "description", "mineur",
       "Typage des flèches détectées par parties (S0, SD, SG ; seuils 0,15 / 0,07 / 0,05) ; le type posé doit être le "
       "type par parties, ou celui des manœuvres 2026 avec une étiquette conflit_norme quand ils diffèrent. Unité : "
       "flèche détectée avec scores.", "implemente")
def det_fle_006(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        d = p.get("detection") or {}
        if p["classe"] != "fleche" or "scores" not in d or not ctx.fabrique_marquage(p):
            continue
        t = typage_par_parties(d["scores"])
        ok = t == p.get("gabarit") or bool(p.get("conflit_norme")) or p.get("src") == "gam"
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=p.get("gabarit"), seuil=f"type par parties {t}",
                 detail=f"posé {p.get('gabarit')}, typage par parties {t} (scores {d['scores']})")


@regle("DET-FLE-007", "description", "mineur",
       "Flèches hors réseau OpenDRIVE (parkings, intérieur de jonction) issues d'une détection libre : NCC ≥ 0,80, ou "
       "≥ 0,65 corroborée par une autre source. Les flèches levées au GAM ne sont pas concernées. Unité : flèche hors "
       "voie de source image.", "implemente")
def det_fle_007(ctx, R):
    for i, e in M.fleches(ctx).items():
        p = e["p"]
        if p.get("src") not in ("ortho2022", "plan2025") or M.voie_de(ctx, M.centroide(e["poly"][0])) is not None:
            continue
        d = p.get("detection") or {}
        ncc = float(d.get("ncc") or (p.get("diagnostic_cap_libre") or {}).get("iou") or 0)
        n_src = len({s["src"] for s in p.get("sources") or []})
        ok = ncc >= 0.80 or (ncc >= 0.65 and n_src >= 2)
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=r4(ncc, 3), seuil="≥ 0,80 (≥ 0,65 corroborée)",
                 detail=f"score {ncc:.2f}, {n_src} source(s)")


@regle("DET-FLE-008", "description", "mineur",
       "Glyphe hors bibliothèque : une flèche dont la meilleure NCC (detection.scores) ou le meilleur score de classement "
       "(classement) est < 0,70 n'est pas posée comme gabarit IISR sans étiquette (atypique, a_verifier ou levé GAM "
       "ajusté). Unité : flèche avec scores.", "implemente")
def det_fle_008(ctx, R):
    for i, e in M.fleches(ctx).items():
        p = e["p"]
        sc = (p.get("detection") or {}).get("scores") or p.get("classement")
        if not sc:
            continue
        best = max(v for k, v in sc.items() if not k.startswith("RAB"))
        ok = best >= 0.70 or p.get("atypique") or p.get("a_verifier") or p.get("src") == "gam"
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=r4(best, 3), seuil="≥ 0,70 ou étiqueté",
                 detail=f"meilleur score {best:.2f} ({max(sc, key=sc.get)}), posé {p.get('gabarit')} (src {p.get('src')})",
                 ecart=0.7 / max(best, 0.05))


# =========================================================================== bordures, LiDAR
@regle("DET-KRB-015", "les_deux", "majeur",
       "Abaissés détectés dans la marche LiDAR (bordures_hauteurs « mesuree » / « abaissee_mesuree » hors zone de "
       "travaux) : plage de vue ≤ 0,04 m sur ≥ 1,20 m encadrée de vues ≥ 0,10 m ; chaque plage doit recouvrir un "
       "abaissé décrit (traversée ou charretière) de la bordure la plus proche. Unité : plage détectée.",
       "implemente")
def det_krb_015(ctx, R):
    par_ligne = collections.defaultdict(list)
    for f in ctx.bordures_hauteurs:
        p = f["properties"]
        if p.get("zone_travaux_2025") or p.get("statut") not in ("mesuree", "abaissee_mesuree", "sans_ressaut_mesuree"):
            continue
        par_ligne[(p["ligne"], p.get("partie", 0))].append(f)
    ids = sorted(ctx.bordures)
    A = np.vstack([ctx.bordures[b]["P"][:-1, :2] for b in ids])
    B = np.vstack([ctx.bordures[b]["P"][1:, :2] for b in ids])
    own = np.concatenate([np.full(len(ctx.bordures[b]["P"]) - 1, k) for k, b in enumerate(ids)])
    for cle in sorted(par_ligne):
        fs = sorted(par_ligne[cle], key=lambda f: f["properties"]["troncon"])
        h = np.array([float(f["properties"]["h_vue_m"]) for f in fs])
        L = np.array([float(f["properties"]["longueur_m"]) for f in fs])
        bas = h <= 0.04
        k = 0
        while k < len(fs):
            if not bas[k]:
                k += 1
                continue
            j = k
            while j + 1 < len(fs) and bas[j + 1]:
                j += 1
            lg = L[k:j + 1].sum()
            avant = h[max(0, k - 2):k].max() if k > 0 else 0
            apres = h[j + 1:j + 3].max() if j + 1 < len(fs) else 0
            if lg >= 1.2 and avant >= 0.10 and apres >= 0.10:
                Q = np.vstack([K.ligne_local(f["geometry"])[0] for f in fs[k:j + 1]])
                c = Q.mean(0)
                d, js, _ = K.C.distance_segments(c[None], A, B)
                bid = ids[own[js[0]]]
                b = ctx.bordures[bid]
                s_, _, _ = K.C.projeter(b["P"][:, :2], Q)
                trouve = any(a["s0"] - 0.5 <= s_.max() and a["s1"] + 0.5 >= s_.min() for a in b["p"]["abaisses"])
                R.tester(trouve and d[0] < 1.0, entite=f"ligne {cle[0]} tronçons {fs[k]['properties']['troncon']}-"
                         f"{fs[j]['properties']['troncon']} -> {bid}", xy=c, valeur=r4(lg, 2), seuil="abaissé décrit",
                         detail=f"plage abaissée LiDAR de {lg:.1f} m (vue ≤ 0,04, encadrée de {avant:.2f} / {apres:.2f}) "
                                f"sans abaissé décrit sur {bid}", ecart=1 + lg / 2)
            k = j + 1


@regle("DET-LID-013", "description", "mineur",
       "L'intensité LiDAR n'est qu'une preuve d'appui (poids 0,4) : aucune marque posée sur la seule source "
       "lidar2021. Unité : marque fabriquée.", "implemente")
def det_lid_013(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if not ctx.fabrique_marquage(p):
            continue
        srcs = {s.get("src") for s in p.get("sources") or []} | {p.get("src")}
        seul = srcs <= {"lidar2021", "lidar2021_intensite"}
        R.tester(not seul, entite=i, valeur=sorted(srcs), seuil="pas de LiDAR seul")


# =========================================================================== lignes, plan, recalage
@regle("DET-LIG-010", "description", "mineur",
       "Lignes ancrées sur un bord de voie OpenDRIVE (ancrage xodr) : décalage t_off au bord ≤ 0,40 m (couloir de "
       "recherche) ; axe décrit à moins de 0,40 m du bord échantillonné sur 90 % de sa longueur. Unité : ligne ancrée "
       "xodr.", "implemente")
def det_lig_010(ctx, R):
    bords = {b.cle: b for b in K.X.tous_les_bords(ctx.reseau, 0.25)}
    for i, (P, iv, p) in M.lignes_peintes(ctx).items():
        a = p.get("ancrage") or {}
        if a.get("type") != "xodr":
            continue
        bs = [bords.get(f"{a['route']}/{bd['section_s']:g}/{bd['voie']}") for bd in a.get("bords", [])]
        bs = [b for b in bs if b is not None]
        if not bs:
            continue
        Q = np.vstack([b.xy for b in bs])
        d = K.dist_polyligne(K.densifier(P, 0.25), Q)
        part = float((d <= 0.40).mean())
        toff = abs(float(a.get("t_off_m") or 0))
        R.tester(toff <= 0.40 and part >= 0.9, entite=i, xy=P[len(P) // 2], valeur=r4(toff, 3), seuil="≤ 0,40 m",
                 detail=f"t_off {toff:.2f} m, {part * 100:.0f} % de l'axe à ≤ 0,40 m du bord", ecart=max(toff / 0.4, 0.9 / max(part, .05)))


@regle("DET-LIG-011", "description", "mineur",
       "Classification de la modulation : pour les lignes discontinues de modulation IISR nommée avec trait / vide "
       "décrits, écart relatif ≤ 10 % à la table IISR ; modulation « mesuree » rapportée (non ramenée à l'IISR). Unité : "
       "ligne discontinue.", "implemente")
def det_lig_011(ctx, R):
    mods = M.modulations(ctx)
    for i, (P, iv, p) in M.lignes_peintes(ctx).items():
        mod = p.get("modulation")
        if mod in (None, "continue"):
            continue
        tr, vi = p.get("trait_m"), p.get("vide_m")
        if mod in mods and tr and vi:
            t0, v0 = mods[mod]
            e = max(abs(tr - t0) / t0, abs(vi - v0) / v0)
            R.tester(e <= 0.10, entite=i, xy=P[len(P) // 2], valeur=r4(e, 3), seuil="±10 %",
                     detail=f"{mod} : trait {tr} / vide {vi} pour {t0} / {v0}", ecart=e / 0.1)
        elif mod not in mods:
            R.tester(False, entite=i, xy=P[len(P) // 2], valeur=mod, seuil="modulation IISR",
                     detail=f"modulation {mod} (trait {tr}, vide {vi}) non ramenée à la table IISR", severite="info")


@regle("DET-PLN-016", "description", "mineur",
       "Lignes du plan 2025 (src plan2025) : position à ±0,10 m d'une ligne GAM 2026 parallèle quand elle existe (axe "
       "à moins de 0,6 m sur ≥ 50 % de la longueur) ; la phase n'est pas contrôlée. Unité : ligne plan 2025 avec "
       "homologue GAM.", "implemente")
def det_pln_016(ctx, R):
    L_ = M.lignes_peintes(ctx)
    gam = [(i, P) for i, (P, iv, p) in L_.items() if p.get("src") == "gam"]
    for i, (P, iv, p) in L_.items():
        if p.get("src") != "plan2025":
            continue
        Q = K.densifier(P, 0.25)
        best = None
        for j, G in gam:
            d = K.dist_polyligne(Q, G)
            part = float((d <= 0.6).mean())
            if part >= 0.5 and (best is None or np.median(d[d <= 0.6]) < best[0]):
                best = (float(np.median(d[d <= 0.6])), j)
        if best is None:
            continue
        R.tester(best[0] <= 0.10, entite=i, xy=P[len(P) // 2], valeur=r4(best[0], 3), seuil="±0,10 m",
                 detail=f"écart médian au levé GAM {best[1]} {best[0] * 100:.1f} cm", ecart=best[0] / 0.1)


@regle("DET-REG-001", "description", "mineur",
       "Recalage des rasters sur le PCRS : RMSE du calage du plan 2025 ≤ 0,03 m (georef.json, tolérance 0,01) ; "
       "recalages image appliqués aux entités (recalage_image_m, recalage_ortho) ≤ 0,10 m (tolérance des mires). "
       "Unités : calage du plan, entité recalée.", "implemente")
def det_reg_001(ctx, R):
    g = json.loads((PLAN2025 / "georef.json").read_text(encoding="utf-8"))
    rm = float(g.get("rmse_m", 0))
    R.tester(rm <= 0.04, entite="plan_projet_2025/georef.json", valeur=r4(rm, 4), seuil="≤ 0,03 m (±0,01)",
             detail=f"RMSE {rm:.3f} m sur {g.get('points_homologues')} points homologues", ecart=rm / 0.03)
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        r = p.get("recalage_image_m")
        ro = p.get("recalage_ortho")
        if r is None and ro is None:
            continue
        d = float(np.hypot(*r)) if r is not None else float(np.hypot(ro.get("dx", 0), ro.get("dy", 0)))
        R.tester(d <= 0.10 + 1e-6, entite=i, valeur=r4(d, 3), seuil="≤ 0,10 m",
                 detail=f"recalage image de {d:.2f} m ({p.get('src')})", ecart=d / 0.1, severite="info")


@regle("DET-TRV-012", "description", "mineur",
       "Lignes d'effet des feux : une LEF peinte doit être levée (GAM) ou confirmée par une détection ou par le plan "
       "2025 ; sinon elle n'est qu'une ligne virtuelle (MQ-LEF-002) ou une hypothèse non peinte (MQ-LEF-011). Unité : "
       "ligne d'effet.", "implemente")
def det_trv_012(ctx, R):
    for i, e in M.lefs(ctx).items():
        p = e["p"]
        peinte = ctx.fabrique_marquage(p)
        ok = (not peinte) or p.get("src") in ("gam", "plan2025", "ortho2022")
        R.tester(ok, entite=i, xy=M.axe(e).mean(0), valeur=p.get("src"), seuil="peinte seulement si observée",
                 detail=f"LEF peinte de source {p.get('src')}")


@regle("DET-ZEB-009", "description", "mineur",
       "Zébras détectés par périodicité (attribut detection) : pic sur fond ≥ 8, au moins 3 bandes, pas dans "
       "[0,8 ; 1,6] m. Unité : zébra détecté.", "implemente")
def det_zeb_009(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        d = p.get("detection") or {}
        if p["classe"] != "passage" or "pic_sur_fond" not in d:
            continue
        ok = d["pic_sur_fond"] >= 8 and d.get("nb_bandes", 0) >= 3 and 0.8 <= d.get("pas_m", 1.0) <= 1.6
        R.tester(ok, entite=i, valeur=d["pic_sur_fond"], seuil="pic/fond ≥ 8, ≥ 3 bandes",
                 detail=f"pic/fond {d['pic_sur_fond']}, {d.get('nb_bandes')} bandes, pas {d.get('pas_m')} m")


# =========================================================================== fusion
SRC_BASE = {"gam": "leve", "pcrs": "leve", "plan2025": "plan2025", "ortho2022": "ortho2022", "v1": "v1",
            "lidar2021": "lidar2021", "panoramax": "panoramax"}


@regle("FUS-SRC-001", "description", "majeur",
       "Admissibilité des sources selon l'état de la zone (paramètres de la règle) : conservée {levé, ortho 2022, LiDAR, "
       "plan, Panoramax, règle} ; refaite à l'identique {levé, plan, ortho si cohérente, Panoramax ≥ 2025-09, "
       "règle} ; neuve 2025 {levé, plan, Panoramax ≥ 2025-09, règle}. Source v1 seule : admise seulement a_verifier. "
       "Unité : marque fabriquée.", "implemente")
def fus_src_001(ctx, R):
    if K.E:
        # état cible : même table que decrire/marquages_sources (E.v_temporelle_marquages) ; v_temporelle > 0 = admise
        adm = admissibilite_etat(K.E)
        base = src_base_etat
    else:
        adm = {"conserve": {"leve", "ortho2022", "lidar2021", "plan2025", "panoramax", "regle"},
               "refait_2025_identique": {"leve", "plan2025", "ortho2022", "panoramax", "regle"},
               "neuf_2025": {"leve", "plan2025", "panoramax", "regle"},
               "construit_2023_2024": {"leve", "plan2025", "panoramax", "regle"}}
        base = lambda src: "regle" if src.startswith("regle") else SRC_BASE.get(src, src)  # noqa: E731
    if K.E:
        R.mesure("etat_cible", {"id": K.E.id, "admissibilite": {z: sorted(v) for z, v in sorted(adm.items())}})
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if not ctx.fabrique_marquage(p):
            continue
        src = str(p.get("src"))
        b = base(src)
        z = p.get("zone_etat")
        ok = b in adm.get(z, set()) or (b == "v1" and p.get("a_verifier"))
        R.tester(ok, entite=i, valeur=src, seuil=f"admissible en {z}", detail=f"source {src} en zone {z}")


def src_base_etat(src):
    """Source de base d'une marque pour un état : regle:<ID> -> regle ; photo:/mapillary:/panoramax: -> photo."""
    if src.startswith("regle"):
        return "regle"
    if ":" in src and src.split(":", 1)[0] in ("photo", "mapillary", "panoramax"):
        return "photo"
    return src


def admissibilite_etat(E):
    """{état de zone: sources admises} tiré de E.v_temporelle (poids > 0), plus l'inférence par règle ; le paquet v1
    reste un germe : admis seulement avec a_verifier (test de fus_src_001)."""
    adm = {}
    for s, t in E.v_temporelle.items():
        for z, v in t.items():
            if v > 0 and s != "v1":
                adm.setdefault(z, set()).add(s)
    for z in adm:
        adm[z].add("regle")
    return adm


@regle("FUS-SCO-002", "description", "mineur",
       "Score d'existence : une marque posée a P ≥ 0,5, ou 0,3 ≤ P < 0,5 avec l'étiquette a_verifier, ou est exigée par "
       "une règle (src regle) ; P < 0,3 jamais posé ; score dans [0, 1]. Unité : marque fabriquée.", "implemente")
def fus_sco_002(ctx, R):
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if not ctx.fabrique_marquage(p):
            continue
        P = p.get("score")
        regle_ = str(p.get("src", "")).startswith("regle")
        ok = P is not None and 0 <= P <= 1 and (P >= 0.5 or (P >= 0.3 and p.get("a_verifier")) or regle_)
        R.tester(ok, entite=i, valeur=P, seuil="P ≥ 0,5 ou a_verifier", detail=f"score {P}, a_verifier "
                 f"{bool(p.get('a_verifier'))}, src {p.get('src')}", ecart=0.5 / max(P or 0.01, 0.01))


@regle("FUS-SNP-004", "description", "mineur",
       "Accrochage normatif : largeurs de lignes dans {0,10 ; 0,12 ; 0,15 ; 0,18 ; 0,25 ; 0,30} (± 0,02) ou largeurs "
       "propres aux pistes (0,06 / 0,09) ; flèches posées sur un gabarit IISR (gabarit renseigné) sauf contour atypique "
       "étiqueté ; zébras à bandes de 0,50 m et vide dans [0,50 ; 0,80]. Unité : ligne, flèche, zébra.",
       "implemente")
def fus_snp_004(ctx, R):
    larg = [0.06, 0.09, 0.10, 0.12, 0.15, 0.18, 0.25, 0.30]
    for i, (P, iv, p) in M.lignes_peintes(ctx).items():
        w = float(p.get("largeur_m") or 0)
        e = min(abs(w - x) for x in larg)
        R.tester(e <= 0.02 + 1e-6, entite=i, xy=P[len(P) // 2], valeur=w, seuil="largeur normalisée ±0,02",
                 detail=f"largeur {w} m", ecart=1 + e / 0.02)
    for i, e in M.fleches(ctx).items():
        p = e["p"]
        ok = bool(p.get("gabarit")) or p.get("atypique")
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=p.get("gabarit"), seuil="gabarit IISR ou atypique")
    for zid, z in M.zebras(ctx).items():
        p = z["p"]
        ok = abs(float(p.get("largeur_bande_m", 0.5)) - 0.5) <= 0.01 and 0.5 - 1e-6 <= float(p.get("intervalle_m", 0.5)) <= 0.8 + 1e-6
        R.tester(ok, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=p.get("intervalle_m"), seuil="bande 0,50, vide 0,50-0,80",
                 detail=f"bande {p.get('largeur_bande_m')}, vide {p.get('intervalle_m')}")


@regle("FUS-ASS-003", "description", "mineur",
       "Appariement multi-sources : les hypothèses fusionnées dans une même marque (marquages_hypotheses : décision "
       "apparie / confirme / fusionne) sont dans les portes de la classe (flèche 1 m, 2 m si GAM ponctuel ; zébra 1 m "
       "d'axe ; ligne 0,3 m ; symbole 0,8 m), mesurées entre centroïdes de l'hypothèse et de la marque. Unité : "
       "hypothèse appariée.", "partiel", "portes angulaires et recouvrement des lignes non mesurés (géométries "
       "d'hypothèse ponctuelles)")
def fus_ass_003(ctx, R):
    portes = {"fleche": 1.0, "passage": 1.0, "ligne": 0.3, "transversale": 1.0, "symbole": 0.8, "zone": 1.0}
    for f in C_lire(ctx):
        p = f["properties"]
        if p.get("decision") not in ("apparie", "confirme", "fusionne") or p.get("entite") not in ctx.marquages:
            continue
        g = f.get("geometry")
        if not g:
            continue
        e = ctx.marquages[p["entite"]]
        if "poly" in e:
            ce = M.centroide(e["poly"][0])
        elif "lignes" in e:
            ce = None
        else:
            continue
        if g["type"] == "Point":
            q = K.C.repere(np.array(g["coordinates"][:2]))
        elif g["type"] in ("LineString", "MultiLineString"):
            q = np.vstack(K.ligne_local(g))
        elif g["type"] in ("Polygon", "MultiPolygon"):
            q = M.centroide(K.poly_local(g)[0])
        else:
            continue
        cl = e["p"]["classe"]
        porte = portes.get(cl, 1.0) * (2.0 if (cl == "fleche" and p.get("src") == "gam") else 1.0)
        if ce is None:
            P = M.axe(e)
            d = float(np.median(K.dist_polyligne(np.atleast_2d(q), P)))
        else:
            d = float(np.min(np.hypot(*(np.atleast_2d(q).mean(0) - ce))))
        R.tester(d <= porte, entite=f"{p['id']} -> {p['entite']}", valeur=r4(d, 3), seuil=f"≤ {porte} m",
                 detail=f"hypothèse {p.get('src')} à {d:.2f} m de la marque ({cl})", ecart=d / porte)


def C_lire(ctx):
    return ctx._m("hyp", lambda: K.C.lire_geojson(ctx.dbase / "marquages_hypotheses.geojson"))


@regle("FUS-CON-005", "description", "mineur",
       "Conflits à signaler : une flèche de confiance ≥ 0,6 dont le type diffère du type attendu des manœuvres "
       "(INF-FLE-004) porte l'étiquette conflit_norme. Unité : flèche sur une voie attendue.", "implemente")
def fus_con_005(ctx, R):
    att = next(r for r in ctx.regles["regles"] if r["id"] == "INF-FLE-004")["parametres"]["attendu_site"]
    for i, e in M.fleches(ctx).items():
        v = M.voie_de(ctx, M.centroide(e["poly"][0]))
        if v is None:
            continue
        cle = f"R{v[0]}.v{v[1]}"
        typ = att.get(cle) or att.get(f"R{v[0]}")
        if typ is None:
            continue
        p = e["p"]
        diff = (typ == "aucune") or p.get("gabarit") != typ
        conf = (p.get("score") or 0) >= 0.6
        ok = not (diff and conf) or bool(p.get("conflit_norme"))
        R.tester(ok, entite=i, xy=M.centroide(e["poly"][0]), valeur=p.get("gabarit"), seuil="conflit_norme si type ≠ attendu",
                 detail=f"{cle} : posé {p.get('gabarit')}, attendu {typ}, score {p.get('score')}, sans conflit_norme")


# =========================================================================== VAL-IMG-007
def filtre_1d(a, k, op, axe):
    """Minimum ou maximum glissant de largeur k (impair) le long d'un axe : algorithme de van Herk / Gil-Werman."""
    a = np.moveaxis(a, axe, -1)
    n = a.shape[-1]
    r = k // 2
    neutre = np.inf if op is np.minimum else -np.inf
    pad = np.full(a.shape[:-1] + (r,), neutre)
    b = np.concatenate([pad, a, pad], axis=-1)
    m = b.shape[-1]
    nb = int(np.ceil(m / k))
    b = np.concatenate([b, np.full(a.shape[:-1] + (nb * k - m,), neutre)], axis=-1)
    blocs = b.reshape(a.shape[:-1] + (nb, k))
    g = op.accumulate(blocs, axis=-1).reshape(a.shape[:-1] + (nb * k,))
    h = op.accumulate(blocs[..., ::-1], axis=-1)[..., ::-1].reshape(a.shape[:-1] + (nb * k,))
    idx = np.arange(n)
    out = op(h[..., idx], g[..., idx + k - 1])
    return np.moveaxis(out, -1, axe)


def tuile_tophat(ctx, x0, y0):
    """Top-hat blanc (luminance − ouverture par un carré de 1,55 m) de la tuile d'ortho 2022 de 50 m à 5 cm
    (DET-PRE-002) : (tableau, géotransformation (x centre pixel 0, dx, y centre pixel 0, dy))."""
    def f():
        from PIL import Image
        fp = ORTHO2022 / f"pcrs5cm_{int(x0)}_{int(y0)}.jpg"
        if not fp.exists():
            return None
        L = np.asarray(Image.open(fp).convert("L"), np.float64)
        k = 31
        ouv = filtre_1d(filtre_1d(L, k, np.minimum, 0), k, np.minimum, 1)
        ouv = filtre_1d(filtre_1d(ouv, k, np.maximum, 0), k, np.maximum, 1)
        v = [float(x) for x in fp.with_suffix(".jgw").read_text().split()]
        return L - ouv, (v[4], v[0], v[5], v[3])
    return ctx._m(f"tophat:{x0}:{y0}", f)


@regle("VAL-IMG-007", "description", "mineur",
       "Preuve image a posteriori sur l'ortho 2022 (zones conservées, sources admissibles) : NCC entre le masque de la "
       "marque décrite (rendu à 5 cm : polygone, ou axe tamponné à la demi-largeur, parties peintes) et le top-hat blanc de la tuile d'ortho 2022 "
       "(luminance − ouverture par un carré de 1,55 m, DET-PRE-002) dans sa boîte élargie de 0,5 m ; signalée si "
       "NCC < 0,3. Lignes d'effet exclues. Unité : marque fabriquée en zone conservée.", "partiel",
       "zones refaites / neuves (plan 2025 inversé) non contrôlées")
def val_img_007(ctx, R):
    from PIL import Image, ImageDraw
    vals = []
    for i, e in sorted(ctx.marquages.items()):
        p = e["p"]
        if p.get("zone_etat") != "conserve" or not ctx.fabrique_marquage(p) or p["type"] == "effet_feux":
            continue
        if "poly" in e:
            polys = [[r + np.array(K.O[:2]) for r in pp] for pp in e["poly"]]
            lignes = []
        elif "lignes" in e and p["classe"] == "ligne":
            P = M.axe(e)
            iv = M.intervalles_peints(p, M.longueur(P), M.modulations(ctx))
            lignes = [(K.C.sous_polyligne(P, a, b) + np.array(K.O[:2]), float(p.get("largeur_m") or 0.1)) for a, b in iv]
            polys = []
        else:
            continue
        pts = np.vstack([r for pp in polys for r in pp] + [L for L, _ in lignes]) if (polys or lignes) else None
        if pts is None or not len(pts):
            continue
        lo, hi = pts.min(0) - 0.5, pts.max(0) + 0.5
        x0, y0 = math.floor(lo[0] / 50) * 50, math.floor(lo[1] / 50) * 50
        if math.floor(hi[0] / 50) * 50 != x0 or math.floor(hi[1] / 50) * 50 != y0:
            continue                                   # marque à cheval sur deux tuiles : non contrôlée
        t = tuile_tophat(ctx, x0, y0)
        if t is None:
            continue
        a, (gx0, dx, gy0, dy) = t
        c0 = int(max(0, math.floor((lo[0] - gx0) / dx)))
        c1 = int(min(a.shape[1], math.ceil((hi[0] - gx0) / dx) + 1))
        r0 = int(max(0, math.floor((hi[1] - gy0) / dy)))
        r1 = int(min(a.shape[0], math.ceil((lo[1] - gy0) / dy) + 1))
        if c1 - c0 < 3 or r1 - r0 < 3:
            continue
        sub = a[r0:r1, c0:c1]
        im = Image.new("L", (c1 - c0, r1 - r0), 0)
        dr = ImageDraw.Draw(im)

        def px(Q):
            return [((x - gx0) / dx - c0, (y - gy0) / dy - r0) for x, y in Q]
        for pp in polys:
            dr.polygon(px(pp[0]), fill=255)
            for h in pp[1:]:
                dr.polygon(px(h), fill=0)
        for L, w in lignes:
            if len(L) >= 2:
                dr.line(px(L), fill=255, width=max(1, int(round(w / abs(dx)))))
        m = np.asarray(im, np.float64)
        if m.std() < 1e-6 or sub.std() < 1e-6:
            continue
        ncc = float(((m - m.mean()) * (sub - sub.mean())).mean() / (m.std() * sub.std()))
        vals.append(ncc)
        R.tester(ncc >= 0.3, entite=i, xy=pts.mean(0) - np.array(K.O[:2]), valeur=r4(ncc, 3), seuil="NCC ≥ 0,3",
                 detail=f"{p['classe']}/{p['type']} (src {p.get('src')}) : NCC {ncc:.2f} avec le contraste de l'ortho "
                        f"2022", ecart=0.3 / max(ncc, 0.03))
    R.mesure("ncc", stats(vals, (5, 50, 95)))


@regle("DET-PRE-002", "description", "info",
       "Canal de vraisemblance de marquage : paramètres des tuiles de contraste (contraste_par_tuile.json : élément "
       "structurant ≥ 1,5 m, seuil top-hat 25 DN) et couverture des tuiles d'ortho de 50 m portant de la chaussée "
       "(une tuile de contraste par tuile d'ortho utilisée). Unité : paramètre, tuile.", "partiel",
       "traitement interne aux détecteurs : seuls ses paramètres et sa couverture sont contrôlables")
def det_pre_002(ctx, R):
    d = json.loads((K.SITE / "marquages/contraste_par_tuile.json").read_text(encoding="utf-8"))
    es = float(d.get("element_structurant_m", 0))
    R.tester(es >= 1.5, entite="element_structurant_m", valeur=es, seuil="≥ 1,5 m")
    R.tester(int(d.get("seuil_tophat", 0)) == 25, entite="seuil_tophat", valeur=d.get("seuil_tophat"), seuil="25 DN")
    noms = {t["tuile"].replace("pcrs5cm_", "contraste_") for t in d.get("tuiles", []) if t.get("part_chaussee", 0) > 0}
    for n in sorted(noms):
        R.tester((K.SITE / "marquages/contraste_5cm" / n).exists(), entite=n, seuil="tuile de contraste présente")
