"""Inférence par règles des marquages absents après fusion (actions « deduire_si_absent » de regles_conception.json,
étape 5 de fusion_detection_inference.ordre_application). Chaque entité créée porte src = « regle:<ID> », la confiance
de la règle et son score (FUS-SCO-002 : haute 0,7, moyenne 0,5, faible 0,3).

Approches à feux : signal R11 principal (type 1000001) du .xodr et ses voies commandées (validity).
- MQ-LEF-002 : ligne d'arrêt virtuelle (vérité terrain ADAS, NON peinte) sur les voies commandées, au plus en amont
  de l'aplomb du feu et du bord amont du passage piéton qui suit le feu à moins de 4 m (MQ-LEF-006) ;
- MQ-LEF-011 : approche sans ligne d'effet attestée alors qu'une autre en porte une : hypothèse T'2 0,15 à 3,0 m du bord
  amont du passage (MQ-LEF-005), score 0,35, a_verifier, non peinte avant confirmation photo (CF-08) ;
- INF-FLE-004 + MQ-FLE-001/003/004/005/006 + MQ-DET-001 : flèches de chaque voie entrante affectée (type déduit des
  manœuvres 2026) ; 2 par voie sur le site (MQ-FLE-003), pointe de la dernière à 2,0 m en amont de la ligne d'arrêt
  (MQ-FLE-004), interdistance mesurée sur la voie ou l'approche, sinon 24 m (MQ-FLE-005), tige décalée selon MQ-FLE-006,
  profil commun (DET-FLE-005), exclusions INF-FLE-006 (décalage vers l'amont) ;
- MQ-DET-004 + MQ-PP-004 + MQ-PP-003 : passage par groupe de signaux piétons R12 (1000002) sans zébra ;
- MQ-CYC-007 / MQ-CYC-008 : traversée cyclable par paire R13c (1000013) sans marque cyclable (figurine) ;
- MQ-DET-009 / MQ-BUS-005 : zigzag d'arrêt de bus (objet busStop / C6) sans zigzag à moins de 15 m (30 m : 20 amont,
  10 aval), confiance faible ;
- MQ-DET-002 + MQ-LIG-003 + MQ-DET-011 : ligne T3 2u entre voies fléchées d'une approche, de la ligne d'arrêt à 30 m en
  amont, si aucune ligne n'y est levée ni détectée ; phase ancrée à l'aval.
"""
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marquages_commun as M  # noqa: E402
import marquages_fusion as FU  # noqa: E402
import marquages_gam_entites as GE  # noqa: E402
import marquages_lignes as LG  # noqa: E402
import marquages_sources as S  # noqa: E402
import xodr_echantillonne as X  # noqa: E402
from commun import DONNEES, abscisses, lire_json, projeter  # noqa: E402

REGLES = None
TYPE_ATTENDU = {"TD": "TD", "TAG": "TAG", "TAD": "TAD", "TD+TAG": "TD_TAG", "TD+TAD": "TD_TAD"}
DECALAGE_TIGE = {"TD": 0.0, "TAD": -0.425, "TAG": 0.425, "TD_TAD": -0.275, "TD_TAG": 0.275}     # MQ-FLE-006


def regle(rid):
    global REGLES
    if REGLES is None:
        d = lire_json(Path(__file__).resolve().parents[3] / "assets/specs/regles_conception.json")
        REGLES = {r["id"]: r for r in d["regles"]}
    return REGLES[rid]


def _signaux(reseau):
    out = []
    for rid in sorted(reseau, key=int):
        sg = reseau[rid].xml.find("signals")
        if sg is None:
            continue
        for s in sg.findall("signal"):
            v = [(int(x.get("fromLane")), int(x.get("toLane"))) for x in s.findall("validity")]
            ss, t = float(s.get("s")), float(s.get("t"))
            x, y, h = X.point_st(reseau[rid], np.array([ss]), np.array([t]))
            out.append({"route": rid, "id": s.get("id"), "type": s.get("type"), "nom": s.get("name"), "s": ss, "t": t,
                        "xy": np.array([x[0], y[0]]), "validity": v})
    return out


def approches(reseau):
    """Approches à feux : [{nom, route, voies, sens (+1 : voies droites, s croissant), s_feu, xy_feu}]."""
    out = []
    for g in _signaux(reseau):
        if g["type"] != "1000001" or "principal" not in g["nom"] or not g["validity"]:
            continue
        a, b = g["validity"][0]
        voies = list(range(min(a, b), max(a, b) + 1))
        sens = 1 if voies[0] < 0 else -1
        out.append({"nom": g["nom"].replace("feu tricolore ", "").replace(" (principal)", ""), "route": g["route"], "voies": voies,
                    "sens": sens, "s_feu": g["s"], "xy_feu": g["xy"]})
    return sorted(out, key=lambda a: (int(a["route"]), a["s_feu"]))


def _pt(route, s, t):
    x, y, h = X.point_st(route, np.atleast_1d(np.asarray(s, float)), np.atleast_1d(np.asarray(t, float)))
    return np.c_[x, y], h


def _t_voies(route, s, voies):
    sec = route.section(s)
    tb = route.t_bords(np.array([s]), sec)
    ts = []
    for v in voies:
        if v not in sec.voies:
            continue
        vi = v + 1 if v < 0 else v - 1
        ts += [float(tb[v][0]), float(tb[vi][0])]
    return (min(ts), max(ts)) if ts else (None, None)


def _bord_amont_passage(reseau, ap, passages):
    """Bord amont (abscisse s) du passage qui suit le feu à moins de 4 m (MQ-LEF-006), ou None."""
    r = reseau[ap["route"]]
    best = None
    for p in passages:
        if p.get("type") != "zebra":
            continue
        import marquages_reprises as RP
        P = np.vstack([q for poly in RP.empreinte(p) for q in poly])
        Sx = np.arange(0.0, r.longueur, 0.05)
        x, y, _ = r.reference(Sx)
        ref = np.c_[x, y]
        sig, d, _ = projeter(ref, P)
        if float(np.median(d)) > 15.0:
            continue
        s = np.interp(sig, abscisses(ref), Sx)
        amont = float(s.min()) if ap["sens"] > 0 else float(s.max())
        delta = (amont - ap["s_feu"]) * ap["sens"]
        if -1.0 <= delta <= 4.0 + 6.0 and (best is None or abs(delta) < abs(best[1])):
            best = (amont, delta, p["id"])
    return best


def _transversale(eid, reseau, ap, s, regle_id, peinte, note, loc):
    r = reseau[ap["route"]]
    t0, t1 = _t_voies(r, s, ap["voies"])
    P, h = _pt(r, [s, s], [t0, t1])
    if ap["sens"] > 0:
        P = P[::-1]
    e = GE.base(eid, "transversale", "effet_feux", P, [], "", loc)
    conf = regle(regle_id)["confiance"]
    e.update({"geom": ("LineString", P), "src": f"regle:{regle_id}", "gam": [], "sources": [],
              "modulation": "T'2", "trait_m": 0.5, "vide_m": 0.5, "phase_m": 0.0, "largeur_m": 0.15,
              "longueur_m": round(float(abscisses(P)[-1]), 3), "interruptions": [],
              "ancrage": {"type": "xodr", "route": ap["route"], "voie": ap["voies"][0], "s": round(s, 3), "t": round(0.5 * (t0 + t1), 3)},
              "approche": ap["nom"], "peinte": peinte, "regles": [regle_id]})
    if not peinte:
        e["fabrication"] = {"statut": "non_fabrique", "raison": note}
    e["prov"] = {"geometrie": {"src": f"regle:{regle_id}", "ref": note, "conf": conf}}
    FU.ajouter_source(e, f"regle:{regle_id}", note, None, e["etat_zone"], conf_regle=conf)
    return e


def lignes_arret(entites, reseau, loc, journal):
    out = []
    aps = approches(reseau)
    passages = [e for e in entites if e["classe"] == "passage"]
    attestees = {}
    for ap in aps:
        att = [e for e in entites if e["classe"] == "transversale" and e.get("src", "").split(":")[0] in ("gam", "plan2025", "ortho2022")
               and _sur_approche(e, reseau, ap)]
        attestees[ap["nom"]] = att
    n = 0
    for ap in aps:
        bp = _bord_amont_passage(reseau, ap, passages)
        s_feu = ap["s_feu"]
        if bp is not None and bp[1] <= 4.0:
            s_arret = min(s_feu, bp[0]) if ap["sens"] > 0 else max(s_feu, bp[0])
            ref = f"bord amont du passage {bp[2]} ({bp[1]:+.2f} m du feu) et aplomb du feu : le plus en amont"
        else:
            s_arret = s_feu
            ref = "aplomb du feu R11 (pas de passage à moins de 4 m en aval, MQ-LEF-006)"
        ap["s_arret"] = s_arret
        e = _transversale(GE.ident("MT", 8000 + n), reseau, ap, s_arret, "MQ-LEF-002", False,
                          f"ligne d'arrêt virtuelle de l'approche {ap['nom']} (R412-30) : {ref} ; non peinte", loc)
        e["type"] = "effet_feux"
        e["virtuelle"] = True
        out.append(e)
        n += 1
        journal.append({"regle": "MQ-LEF-002", "approche": ap["nom"], "entite": e["id"], "s": round(s_arret, 2)})
        if not attestees[ap["nom"]] and any(attestees[k] for k in attestees if k != ap["nom"]) and bp is not None:
            s_h = bp[0] - ap["sens"] * (3.0 + 0.075)
            e2 = _transversale(GE.ident("MT", 8000 + n), reseau, ap, s_h, "MQ-LEF-011", False,
                               f"hypothèse de ligne d'effet T'2 0,15 à 3,0 m du bord amont du passage {bp[2]} (MQ-LEF-005) : "
                               "pratique homogène du carrefour ; non peinte avant confirmation photo (CF-08)", loc)
            e2["a_verifier"] = True
            e2["sources"] = [{"src": "regle:MQ-LEF-011", "ref": "score d'inférence 0,35", "c": None, "S": 0.35}]
            out.append(e2)
            n += 1
            journal.append({"regle": "MQ-LEF-011", "approche": ap["nom"], "entite": e2["id"], "s": round(s_h, 2)})
    return out, aps


def _sur_approche(e, reseau, ap):
    r = reseau[ap["route"]]
    c = _pts(e).mean(axis=0)
    Sx = np.arange(0.0, r.longueur, 0.1)
    x, y, _ = r.reference(Sx)
    ref = np.c_[x, y]
    sig, d, _ = projeter(ref, c[None])
    s = float(np.interp(sig[0], abscisses(ref), Sx))
    return d[0] < 12.0 and -15.0 <= (ap["s_feu"] - s) * ap["sens"] <= 15.0


# --------------------------------------------------------------------------- flèches
def _attendus():
    m = lire_json(DONNEES / "opendrive/manoeuvres_2026.json")
    par_voie = {}
    for x in m["manoeuvres"]:
        if not x.get("autorisee_2026", True):
            continue
        cle = (str(x["entree"]["route"]), int(x["entree"]["voie"]))
        man = x["manoeuvre"].split(" ")[0].lower()
        code = "TD" if man.startswith("tout") else "TAG" if "gauche" in x["manoeuvre"] else "TAD" if "droite" in x["manoeuvre"] else None
        if code:
            par_voie.setdefault(cle, set()).add(code)
    out = {}
    for cle, ms in par_voie.items():
        k = "+".join(sorted(ms, key=lambda c: ("TD", "TAG", "TAD").index(c)))
        out[cle] = TYPE_ATTENDU.get(k)          # trois directions ou gauche + droite : aucune flèche (INF-FLE-004)
    return out


def _fleches_voie(entites, reseau, loc, route, voie, s_lo, s_hi):
    r = reseau[route]
    out = []
    for e in entites:
        if e["classe"] != "fleche":
            continue
        vs = loc.voies(np.asarray(e["pose"]["origine_local"], float) + 1.5 * np.asarray(M.axes_cap(e["pose"]["cap_deg"])[1]))
        vs = [v for v in vs if v["route"] == route and v["voie"] == voie]
        if vs and s_lo - 1.0 <= vs[0]["s"] <= s_hi + 1.0:
            out.append((vs[0]["s"], e))
    return sorted(out, key=lambda x: x[0])


def st_route(r, xy):
    """(s, t) d'un point local sur la ligne de référence de la route r (t > 0 à gauche)."""
    Sx = np.arange(0.0, r.longueur + 1e-9, 0.05)
    x, y, h = r.reference(Sx)
    ref = np.c_[x, y]
    sig, d, cote = projeter(ref, np.atleast_2d(xy))
    s = np.interp(sig, abscisses(ref), Sx)
    return s, d * cote


def t_bord(r, s, v):
    """t du bord extérieur de la voie v aux abscisses s (laneSection de chaque abscisse)."""
    s = np.atleast_1d(np.asarray(s, float))
    out = np.full(len(s), np.nan)
    for i, x in enumerate(s):
        sec = r.section(x)
        tb = r.t_bords(np.array([x]), sec)
        if v in tb:
            out[i] = float(tb[v][0])
    return out


def axes_voies(r, s, voies):
    """Axe (t) de chaque voie à l'abscisse s, d'après le .xodr."""
    out = {}
    for v in voies:
        vi = v + 1 if v < 0 else v - 1
        out[v] = 0.5 * (float(t_bord(r, s, v)[0]) + float(t_bord(r, s, vi)[0]))
    return out


def fleches(entites, reseau, loc, aps, journal):
    """Flèches manquantes des approches affectées. Les voies réelles sont lues d'abord sur les flèches observées (levé,
    détections : regroupement latéral, gap > 1,6 m) — le .xodr peut être décalé par rapport à l'état 2026 —, à défaut sur
    les voies du .xodr ; axe de voie = pied de tige corrigé du décalage normatif (MQ-FLE-006)."""
    att = _attendus()
    out, n = [], 0
    for ap in aps:
        r = reseau[ap["route"]]
        sens = ap["sens"]
        voies_aff = [(v, att.get((ap["route"], v))) for v in ap["voies"]]
        s_arret = ap["s_arret"]
        s_lo, s_hi = sorted((s_arret, s_arret - sens * 80.0))
        sec_feu = r.section(ap["s_feu"])
        s_ref = min(max(s_arret - sens * 3.0, sec_feu.s + 0.1), sec_feu.s1 - 0.1)   # même laneSection que le feu (ids de voies)
        tc = axes_voies(r, s_ref, ap["voies"])
        tmin, tmax = min(tc.values()) - 2.5, max(tc.values()) + 2.5
        obs = []
        for e in entites:
            if e["classe"] != "fleche":
                continue
            o = np.asarray(e["pose"]["origine_local"], float)
            s, t = st_route(r, o)
            s, t = float(s[0]), float(t[0])
            x_, y_, h_ = r.reference(np.array([min(max(s, 0.0), r.longueur)]))
            cap_v = math.degrees(h_[0] if sens > 0 else h_[0] + math.pi) % 360.0
            if not (s_lo - 1.0 <= s <= s_hi + 1.0 and tmin <= t <= tmax) or S.angle_diff(cap_v, e["pose"]["cap_deg"]) > 30.0:
                continue
            obs.append((s, t + DECALAGE_TIGE.get(e["gabarit"], 0.0) * sens, e))
        obs.sort(key=lambda x: x[1])
        groupes = []
        for o_ in obs:
            if groupes and o_[1] - groupes[-1][-1][1] <= 1.6:
                groupes[-1].append(o_)
            else:
                groupes.append([o_])
        voies_tri = sorted(ap["voies"], key=lambda v: tc[v])
        par_voie = {v: [] for v in ap["voies"]}
        t_axe = dict(tc)
        source_axe = {v: "xodr" for v in ap["voies"]}
        if groupes and len(groupes) == len(voies_tri):
            for v, g in zip(voies_tri, groupes):
                par_voie[v] = sorted(g, key=lambda x: x[0])
                t_axe[v] = float(np.median([x[1] for x in g]))
                source_axe[v] = "fleches_observees"
        else:
            for o_ in obs:
                v = min(ap["voies"], key=lambda v: abs(tc[v] - o_[1]))
                par_voie[v].append(o_)
            for v in ap["voies"]:
                if par_voie[v]:
                    t_axe[v] = float(np.median([x[1] for x in par_voie[v]]))
                    source_axe[v] = "fleches_observees"
        ap["t_axes"] = t_axe
        ap["t_axes_source"] = source_axe
        inter = None
        for v in par_voie:
            ss = sorted(x[0] for x in par_voie[v])
            if len(ss) >= 2:
                inter = float(np.median(np.diff(ss)))
        inter = inter if inter and 10.0 <= inter <= 39.0 else 24.0
        if not any(t for _, t in voies_aff):
            continue
        for v, typ in voies_aff:
            if not typ:
                continue
            ex = par_voie[v]
            for s, _, e in ex:
                if e["gabarit"] != typ and e.get("score", 1.0) >= 0.6 and not e.get("conflit_norme"):
                    e["conflit_norme"] = {"regle": "FUS-CON-005", "type_observe": e["gabarit"], "type_manoeuvres": typ,
                                          "note": "géométrie et type observés gardés ; les deux hypothèses sont notées"}
                    journal.append({"regle": "FUS-CON-005", "entite": e["id"], "observe": e["gabarit"], "attendu": typ})
            if len(ex) >= 2:
                continue
            s_dern = s_arret - sens * 6.0                  # pointe à 2,0 m de la ligne d'arrêt (MQ-FLE-004)
            if ex:
                s_ex = ex[0][0]
                amont, aval = s_ex - sens * inter, s_ex + sens * inter
                if s_lo <= amont <= s_hi:
                    cibles = [amont]
                elif (s_dern - aval) * sens >= 0:
                    cibles = [aval]
                else:
                    cibles = []
            else:
                autres = [x[0] for vv in par_voie for x in par_voie[vv]]
                s0 = min(autres, key=lambda x: abs(x - s_dern)) if autres and min(abs(x - s_dern) for x in autres) <= 3.0 else s_dern
                cibles = [s0, s0 - sens * inter]
            for s in cibles[:2 - len(ex)]:
                s = _degager_s(s, sens, r, entites)
                if s is None or not (0.5 <= s <= r.longueur - 0.5):
                    continue
                t_pied = t_axe[v] - DECALAGE_TIGE[typ] * sens
                P, h = _pt(r, [s], [t_pied])
                cap = math.degrees(h[0] if sens > 0 else h[0] + math.pi) % 360.0
                o = P[0]
                sec = r.section(s)
                eid = GE.ident("MF", 8000 + n)
                n += 1
                e = GE.base(eid, "fleche", "directionnelle", o, [], "", loc)
                conf = regle("INF-FLE-004")["confiance"]
                note = (f"voie {v} de l'approche {ap['nom']} : type {typ} déduit des manœuvres 2026 (INF-FLE-004) ; "
                        f"pied de tige à s = {s:.2f} (dernière pointe à 2,0 m de la ligne d'arrêt, interdistance {inter:.1f} m) ; "
                        f"axe de voie {source_axe[v]}, tige décalée de {DECALAGE_TIGE[typ]:+.3f} m (MQ-FLE-006)")
                e.update({"src": "regle:INF-FLE-004", "gam": [], "sources": [], "gabarit": typ, "echelle": 1.0,
                          "pose": {"origine_local": o, "cap_deg": round(cap, 3), "cap_source": "voie"},
                          "ancrage": {"type": "xodr", "route": ap["route"], "voie": v, "section_s": round(sec.s, 3), "s": round(s, 3),
                                      "t": round(t_pied, 3)},
                          "regles": ["INF-FLE-004", "MQ-FLE-001", "MQ-FLE-003", "MQ-FLE-004", "MQ-FLE-005", "MQ-FLE-006",
                                     "MQ-DET-001", "INF-FLE-006"]})
                e["prov"] = {"geometrie": {"src": "regle:INF-FLE-004", "ref": note, "conf": conf}}
                FU.ajouter_source(e, "regle:INF-FLE-004", note, None, e["etat_zone"], conf_regle=conf)
                out.append(e)
                journal.append({"regle": "INF-FLE-004", "approche": ap["nom"], "voie": v, "entite": eid, "type": typ, "s": round(s, 2),
                                "axe_voie": source_axe[v]})
    return out


def _degager_s(s, sens, r, entites, pas=0.5, max_m=20.0):
    """INF-FLE-006 : décale vers l'amont tant que la flèche (4 m) touche un passage."""
    import marquages_reprises as RP
    zs = [np.vstack([q for poly in RP.empreinte(e) for q in poly]) for e in entites if e["classe"] == "passage"]
    d = 0.0
    while d <= max_m:
        s2 = s - sens * d
        if 0.5 <= s2 <= r.longueur - 4.5:
            P, _ = _pt(r, [s2, s2 + sens * 4.0], [0.0, 0.0])
            ok = True
            for Z in zs:
                if Z[:, 0].min() - 0.5 > P[:, 0].max() + 6 or Z[:, 0].max() + 0.5 < P[:, 0].min() - 6:
                    continue
                H = M.enveloppe_convexe(Z)
                from commun import dans_polygone, densifier
                Q, _ = densifier(np.vstack([P[0], P[1]]), 0.25)
                if dans_polygone(Q, [H]).any():
                    ok = False
                    break
            if ok:
                return s2
        d += pas
    return None


# --------------------------------------------------------------------------- passages, traversées cyclables, zigzags
def _groupes(signaux, type_):
    g = {}
    for s in signaux:
        if s["type"] != type_:
            continue
        cle = (s["route"], s["nom"].rsplit(" (", 1)[0])
        g.setdefault(cle, []).append(s)
    return [(k, v) for k, v in sorted(g.items())]


def passages(entites, reseau, loc, journal):
    """MQ-DET-004 : groupe R12 sans zébra à moins de 3 m de son milieu -> passage MQ-PP-004 (signalé)."""
    import marquages_reprises as RP
    out = []
    zs = [e for e in entites if e["classe"] == "passage"]
    n = 0
    for (route, nom), sg in _groupes(_signaux(reseau), "1000002"):
        c = np.mean([s["xy"] for s in sg], axis=0)
        proche = False
        for z in zs:
            P = np.vstack([q for poly in RP.empreinte(z) for q in poly]) if RP.empreinte(z) else z["geom"][1]
            if float(np.min(np.hypot(*(P - c).T))) < 6.0:
                proche = True
                break
        journal.append({"regle": "MQ-DET-004", "groupe": nom, "route": route, "zebra_existant": proche})
        # la génération complète (largeur roulable, MQ-PP-004) n'est faite que si aucun passage n'est proche
        if proche:
            continue
        r = reseau[route]
        s = float(np.median([x["s"] for x in sg]))
        sec = r.section(s)
        voies = [v for v in sec.voies if v != 0 and sec.voies[v].type in ("driving", "biking", "bus")]
        t0, t1 = _t_voies(r, s, voies)
        if t0 is None:
            continue
        W = t1 - t0
        nb = max(2, int(math.floor(W - 0.5)))
        g = (W - 0.5 * nb) / (nb + 1)
        if g < 0.5 or g > 0.8:
            nb2 = min((k for k in (nb - 1, nb + 1) if k >= 2), key=lambda k: abs((W - 0.5 * k) / (k + 1) - 0.65))
            nb, g = nb2, (W - 0.5 * nb2) / (nb2 + 1)
        A, h = _pt(r, [s, s], [t0 + g + 0.25, t0 + g + 0.25 + (nb - 1) * (0.5 + g)])
        e = GE.base(GE.ident("MP", 8000 + n), "passage", "zebra", A, [], "", loc)
        n += 1
        conf = regle("MQ-DET-004")["confiance"]
        note = (f"groupe de signaux piétons R12 « {nom} » sans passage marqué (MQ-DET-004) : W = {W:.2f} m, n = {nb}, g = {g:.3f} m "
                "(MQ-PP-004), bandes de 3,00 m (MQ-PP-003, médiane du site)")
        e.update({"geom": ("LineString", A), "src": "regle:MQ-DET-004", "gam": [], "sources": [], "largeur_bande_m": 0.5,
                  "intervalle_m": round(min(0.8, max(0.5, g)), 3), "pas_axe_m": round(0.5 + g, 3), "longueur_bande_m": 3.0,
                  "cap_bandes_deg": round(math.degrees(h[0]) % 360.0, 3), "nb_bandes": nb, "nb_emplacements": nb, "coupures": [],
                  "regles": ["MQ-DET-004", "MQ-PP-004", "MQ-PP-003"]})
        e["prov"] = {"geometrie": {"src": "regle:MQ-DET-004", "ref": note, "conf": conf}}
        FU.ajouter_source(e, "regle:MQ-DET-004", note, None, e["etat_zone"], conf_regle=conf)
        out.append(e)
    return out


def traversees_cyclables(entites, reseau, loc, journal):
    """MQ-CYC-007 : paire R13c (1000013) sans figurine ni chevron à moins de 4 m -> figurine VELO par sens (MQ-CYC-008)."""
    out, n = [], 0
    cyc = [e for e in entites if (e["classe"] == "symbole" and e["type"] in ("velo", "chevron"))
           or (e["classe"] == "passage" and e["type"] == "traversee_cyclable")]
    for (route, nom), sg in _groupes(_signaux(reseau), "1000013"):
        c = np.mean([s["xy"] for s in sg], axis=0)
        proche = any(float(np.min(np.hypot(*(_pts(e) - c).T))) < 4.0 for e in cyc)
        journal.append({"regle": "MQ-CYC-007", "groupe": nom, "route": route, "marque_existante": proche})
        if proche or len(sg) < 2:
            continue
        A, B = sg[0]["xy"], sg[1]["xy"]
        u = (B - A) / max(np.hypot(*(B - A)), 1e-9)
        for k, (pt, cap) in enumerate(((A + (B - A) * 0.3, M.cap_de(u)), (A + (B - A) * 0.7, M.cap_de(-u)))):
            ex, ey = M.axes_cap(cap)
            e = GE.base(GE.ident("MS", 8000 + n), "symbole", "velo", pt, [], "", loc)
            n += 1
            conf = regle("MQ-CYC-007")["confiance"]
            note = f"paire de feux cyclistes R13c « {nom} » sans marque cyclable : figurine par sens (MQ-CYC-007, MQ-CYC-008)"
            e.update({"src": "regle:MQ-CYC-007", "gam": [], "sources": [], "gabarit": "VELO", "echelle": 1.0, "a_verifier": True,
                      "pose": {"origine_local": pt - ey * 0.64, "cap_deg": round(cap, 3), "cap_source": "voie"},
                      "regles": ["MQ-CYC-007", "MQ-CYC-008"]})
            e["prov"] = {"geometrie": {"src": "regle:MQ-CYC-007", "ref": note, "conf": conf}}
            FU.ajouter_source(e, "regle:MQ-CYC-007", note, None, e["etat_zone"], conf_regle=conf)
            out.append(e)
    return out


def _pts(e):
    if "pose" in e:
        return np.atleast_2d(np.asarray(e["pose"]["origine_local"], float))
    t, g = e["geom"]
    if t == "LineString":
        return g
    return np.vstack([r for poly in g for r in poly])


def zigzags(entites, reseau, loc, journal):
    """MQ-DET-009 : arrêt de bus (objet busStop du .xodr) sans zigzag à moins de 15 m -> zigzag de 30 m (20 m amont, 10 m
    aval) le long du bord droit de la voie de droite, jaune 2u, amplitude 2,50 m, période 5 m (MQ-BUS-005)."""
    out, n = [], 0
    zz = [e for e in entites if e["classe"] == "zone" and e["type"] == "zigzag"]
    for o in X.objets(reseau):
        if o["sous_type"] != "busStop":
            continue
        proche = any(float(projeter(_pts(z), o["xy"][None])[1][0]) < 15.0 for z in zz)
        journal.append({"regle": "MQ-DET-009", "arret": o["nom"], "zigzag_existant": proche})
        if proche:
            continue
        r = reseau[o["route"]]
        s = o["s"]
        sec = r.section(s)
        droites = [v for v in sec.voies if v < 0 and sec.voies[v].type == "driving"]
        if not droites:
            continue
        v = min(droites)
        s0, s1 = max(0.5, s - 20.0), min(r.longueur - 0.5, s + 10.0)
        L = 5.0 * math.floor((s1 - s0) / 5.0)
        if L < 10.0:
            continue
        s1 = s0 + L
        tb0, tb1 = (float(x) for x in t_bord(r, [s0, s1], v))
        if np.isnan(tb0) or np.isnan(tb1):
            continue
        P, _ = _pt(r, [s0, s1], [tb0 + 0.06, tb1 + 0.06])
        # MQ-DET-010 : la proposition ne recouvre aucune marque observée (sinon elle n'est pas faite)
        import marquages_reprises as RP
        from commun import distance_segments
        sonde = {"classe": "zone", "type": "zigzag", "geom": ("LineString", P), "cote": 1, "amplitude_m": 2.5, "periode_m": 5.0,
                 "trait_m": 0.12}
        Z = np.vstack([r for poly in RP.empreinte(sonde) for r in poly])
        H = M.enveloppe_convexe(Z)
        from commun import dans_polygone
        gene = [x["id"] for x in entites if x["classe"] in ("fleche", "symbole", "passage") and "geom" in x and
                dans_polygone(_pts(x) if "pose" in x else np.vstack([r for poly in RP.empreinte(x) for r in poly]), [H]).any()]
        if gene:
            journal.append({"regle": "MQ-DET-009", "arret": o["nom"], "non_propose": f"recouvrirait {', '.join(gene)} (MQ-DET-010)"})
            continue
        e = GE.base(GE.ident("MZ", 8000 + n), "zone", "zigzag", P, [], "", loc, couleur="jaune")
        n += 1
        conf = regle("MQ-DET-009")["confiance"]
        note = f"arrêt de bus « {o['nom']} » sans zigzag : proposition de 30 m (20 m amont, 10 m aval, MQ-DET-009), à confirmer"
        e.update({"geom": ("LineString", P), "src": "regle:MQ-DET-009", "gam": [], "sources": [], "cote": 1, "amplitude_m": 2.5,
                  "periode_m": 5.0, "trait_m": 0.12, "a_verifier": True, "regles": ["MQ-DET-009", "MQ-BUS-005"]})
        e["prov"] = {"geometrie": {"src": "regle:MQ-DET-009", "ref": note, "conf": conf}}
        FU.ajouter_source(e, "regle:MQ-DET-009", note, None, e["etat_zone"], conf_regle=conf)
        out.append(e)
    return out


def files(entites, reseau, loc, aps, journal):
    """MQ-DET-002 : entre voies fléchées d'une approche, ligne T3 2u de la ligne d'arrêt à 30 m en amont si aucune ligne ne
    couvre au moins la moitié de ce tronçon (phase ancrée à l'aval, MQ-DET-011)."""
    out, n = [], 0
    lignes = FU.preparer_refs([e for e in entites if e["classe"] == "ligne"])
    for ap in aps:
        if len(ap["voies"]) < 2:
            continue
        r = reseau[ap["route"]]
        fl = [e for e in entites if e["classe"] == "fleche" and _sur_approche(e, reseau, dict(ap, s_feu=ap["s_arret"] - ap["sens"] * 12))]
        if not fl:
            continue
        v_int = -1 if ap["sens"] > 0 else min(ap["voies"])     # bord entre les deux voies : bord extérieur de la voie intérieure
        s_a, s_b = sorted((ap["s_arret"], ap["s_arret"] - ap["sens"] * 30.0))
        sec = r.section(ap["s_feu"])                     # ids de voies de la laneSection du feu
        s_a, s_b = max(0.2, s_a, sec.s + 0.05), min(s_b, sec.s1 - 0.05)
        ss = np.arange(s_a, s_b, 0.1)
        ta = ap.get("t_axes") or axes_voies(r, 0.5 * (s_a + s_b), ap["voies"])
        vs_ = sorted(ap["voies"], key=lambda v: ta[v])
        s_ref = min(max(ap["s_arret"] - ap["sens"] * 3.0, sec.s + 0.1), sec.s1 - 0.1)
        d_obs = 0.5 * (ta[vs_[0]] + ta[vs_[1]]) - float(t_bord(r, [s_ref], v_int)[0])
        tt = t_bord(r, ss, v_int) + d_obs              # bord du .xodr recalé sur les axes observés des voies
        ok_ = ~np.isnan(tt)
        ss, tt = ss[ok_], tt[ok_]
        if len(ss) < 20:
            continue
        x, y, h = X.point_st(r, ss, tt)
        P = np.c_[x, y]
        sonde = {"id": "sonde", "classe": "ligne", "type": "continue", "geom": ("LineString", P), "interruptions": []}
        f, qui, _ = FU.recouvrement(sonde, lignes, porte=0.4)
        journal.append({"regle": "MQ-DET-002", "approche": ap["nom"], "recouvrement": round(f, 3), "lignes": qui})
        if f >= 0.5:
            continue
        T, Pm = 3.0, 4.33
        if ap["sens"] < 0:
            P = P[::-1]
        L = float(abscisses(P)[-1])
        phase = (L - T) % Pm                     # trait plein au contact de la ligne d'arrêt (aval, MQ-DET-011)
        e = GE.base(GE.ident("ML", 8000 + n), "ligne", "discontinue", P, [], "", loc)
        n += 1
        conf = regle("MQ-DET-002")["confiance"]
        note = f"approche fléchée {ap['nom']} sans ligne de délimitation (recouvrement {f:.2f}) : T3 2u sur 30 m (MQ-DET-002)"
        e.update({"geom": ("LineString", M.douglas_peucker(P, 0.001)), "src": "regle:MQ-DET-002", "gam": [], "sources": [],
                  "ancrage": {"type": "axe", "source": "regle"}, "bord_xodr": {"route": ap["route"], "voie": v_int, "decalage_observe_m": round(d_obs, 3)},
                  "modulation": "T3", "trait_m": T, "vide_m": 1.33, "phase_m": round(phase, 3), "modulation_source": "IISR",
                  "n_tirets": int(L // Pm) + 1, "largeur_m": 0.12 if e["branche"].startswith("verdun") else 0.10, "role": "delimitation",
                  "longueur_m": round(L, 3), "interruptions": [], "regles": ["MQ-DET-002", "MQ-LIG-003", "MQ-DET-011"]})
        e["prov"] = {"geometrie": {"src": "regle:MQ-DET-002", "ref": note, "conf": conf}}
        FU.ajouter_source(e, "regle:MQ-DET-002", note, None, e["etat_zone"], conf_regle=conf)
        out.append(e)
    return out


def inferer(entites, reseau, loc):
    """-> (nouvelles entités, journal)."""
    journal = []
    lef, aps = lignes_arret(entites, reseau, loc, journal)
    tous = entites + lef
    fl = fleches(tous, reseau, loc, aps, journal)
    tous += fl
    pp = passages(tous, reseau, loc, journal)
    tous += pp
    tc = traversees_cyclables(tous, reseau, loc, journal)
    tous += tc
    zz = zigzags(tous, reseau, loc, journal)
    tous += zz
    fi = files(tous, reseau, loc, aps, journal)
    return lef + fl + pp + tc + zz + fi, journal, aps
