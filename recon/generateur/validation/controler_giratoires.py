"""Contrôle indépendant du lot L5, partie giratoires (Python du système, sans Houdini) : critères L5 du plan
(PLAN_GENERATEUR § 3) mesurés sur la géométrie fabriquée exportée par fabriquer_giratoires.py.

    python recon/generateur/validation/controler_giratoires.py [<dossier de scène> ...] [--json SORTIE]

Lit <scene>/l5/giratoires.json (anneau, congés, faces des îlots, coupes des dessus, entités, BEV, marques),
<scene>/l3/carrefours.json (SOLVEUR fusionné : coins, lignes CÉDEZ, frontières), <scene>/l3/mesures_l3.json et
<scene>/l5/mesures_l5.json (étanchéité), <scene>/l2b/table_marques.json (bandes des passages peintes),
<scene>/l2/vegetation.json et <scene>/modele_voie.json.
Critères (valeur, seuil, atteint) :
  GI-01 anneau de largeur uniforme (bord intérieur fabriqué : couronne, îlot central ou bord du dôme ; bord extérieur :
        arc de l'anneau des faces de coin) ± 1 cm, et largeur = chaussée annulaire du modèle ± 1 cm
  GI-02 déflexion < 100 m sur chaque traversée (RF-GV-GIR-008 : cercle à 2,00 m des bordures d'entrée et de sortie et à
        1,50 m de l'îlot central fabriqué)
  GI-03 îlots séparateurs = ACI tableau 2 (H, B, d, r ± 1 cm ; d = 0 et r = 0,25 si Rg < 15 m ; retrait de 1 m sur
        l'anneau) ; mini-giratoire : largeur 0,85-2,00 m (RF-GV-GIR-016)
  GI-04 refuge ≥ 2,00 m au droit du passage (face fabriquée)
  GI-05 couronne franchissable : vue ≤ 0,03 m, pente 4-6 %, matériau contrasté
  GI-06 îlot central hors agglomération sans arbre ni obstacle (ACI p. 84)
  GI-07 passages à 2-5 m de la ligne CÉDEZ (RF-GV-GIR-015, ARB-02)
  GI-08 raccordements tangents : rupture ≤ 0,5° aux points de tangence, rayons = Re / Rs / R0 ± 1 cm
  GI-09 ligne CÉDEZ sur chaque entrée (RF-GV-GIR-024)
  GI-10 mini-giratoire : dôme de 10-15 cm (≤ 12 cm bus), relief 1-3 cm, contour T'2 3u peint
  GI-11 sol étanche : raccords cœur / branches ≤ 1 mm, 0 bord libre hors extérieur ; îlots : 0 bord libre visible
  GI-12 abaissés des refuges avec BEV (DEF-031)
"""
import argparse
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(GEN))
import regles  # noqa: E402

SCENES = ("G1_giratoire_urbain_D40", "G2_giratoire_periurbain_D50", "G3_mini_giratoire_D20", "G4_giratoire_multivoie_D50")
SORTIE = DEPOT / "recon" / "out" / "generateur"


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def lire(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def dist_seg(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    l2 = vx * vx + vy * vy
    u = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / l2)) if l2 > 1e-18 else 0.0
    return math.hypot(p[0] - a[0] - u * vx, p[1] - a[1] - u * vy)


def cercle_deflexion(A, B, O, rho):
    """Rayon du cercle passant par A et B, contournant le cercle (O, rho) qui lui est intérieurement tangent (même
    construction que description/carrefours.py:cercle_deflexion, refaite ici sur la géométrie fabriquée)."""
    if dist_seg(O, A, B) >= rho:
        return None
    M = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
    h = math.dist(A, B) / 2
    nb = (-(B[1] - A[1]) / (2 * h), (B[0] - A[0]) / (2 * h))
    so = (O[0] - M[0]) * nb[0] + (O[1] - M[1]) * nb[1]
    sg = 1.0 if so > 0 else -1.0

    def f(t):
        C = (M[0] + sg * t * nb[0], M[1] + sg * t * nb[1])
        return math.dist(C, O) - (math.hypot(h, t) - rho)
    lo, hi = 0.0, 1e4
    if f(lo) >= 0:
        return h
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return math.hypot(h, (lo + hi) / 2)


def cercle_ajuste(P):
    """Cercle des moindres carrés (Kasa) : centre, rayon, écart max."""
    n = len(P)
    sx = sum(p[0] for p in P) / n
    sy = sum(p[1] for p in P) / n
    u = [p[0] - sx for p in P]
    v = [p[1] - sy for p in P]
    suu = sum(a * a for a in u); svv = sum(b * b for b in v); suv = sum(a * b for a, b in zip(u, v))
    suuu = sum(a ** 3 for a in u); svvv = sum(b ** 3 for b in v)
    suvv = sum(a * b * b for a, b in zip(u, v)); svuu = sum(b * a * a for a, b in zip(u, v))
    det = suu * svv - suv * suv
    if abs(det) < 1e-18:
        return None
    uc = (0.5 * (suuu + suvv) * svv - 0.5 * (svvv + svuu) * suv) / det
    vc = (0.5 * (svvv + svuu) * suu - 0.5 * (suuu + suvv) * suv) / det
    c = (uc + sx, vc + sy)
    rs = [math.dist(c, p) for p in P]
    R = sum(rs) / n
    return c, R, max(abs(r - R) for r in rs)


def angle_rupture(P, i):
    a, b, c = P[i - 1], P[i], P[i + 1]
    v1 = (b[0] - a[0], b[1] - a[1]); v2 = (c[0] - b[0], c[1] - b[1])
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 0.0
    cs = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))
    return math.degrees(math.acos(cs))


def critere(cid, nom, valeur, seuil, atteint, detail=None):
    return {"id": cid, "critere": nom, "valeur": valeur, "seuil": seuil, "atteint": bool(atteint), "detail": detail or {}}


def controler_scene(d):
    d = Path(d)
    g5 = lire(d / "l5" / "giratoires.json")
    c3 = lire(d / "l3" / "carrefours.json")
    m3 = lire(d / "l3" / "mesures_l3.json")
    m5 = lire(d / "l5" / "mesures_l5.json")
    mod = lire(d / "modele_voie.json")
    tm = lire(d / "l2b" / "table_marques.json") if (d / "l2b" / "table_marques.json").exists() else {"marques": []}
    veg = lire(d / "l2" / "vegetation.json") if (d / "l2" / "vegetation.json").exists() else {}
    res = {"scene": d.name, "criteres": [], "mesures": {}}
    C = res["criteres"]
    for gp in g5["giratoires"]:
        cid = gp["id"]
        typ = gp["type"]
        O = (gp["centre"][0], gp["centre"][1])
        Rg, la = gp["Rg"], gp["la"]
        R0 = gp["R0"]
        faces = [f for f in g5["faces"] if f.get("carrefour") == cid]
        coins = [c for c in g5["coins"] if c.get("carrefour") == cid]
        brs = [b for b in g5["branches"] if b.get("carrefour") == cid]
        mes = res["mesures"].setdefault(cid, {})
        # ---------------------------------------------------------------- GI-01 anneau uniforme
        fin = [f for f in faces if f["kind"] in ("couronne",)] or [f for f in faces if f["kind"] in ("central", "dome")]
        r_in = [math.dist(O, p[:2]) for p in fin[0]["points"]] if fin else []
        r_out = []
        for c in coins:
            U = []
            acc = 0.0
            P = [p[:2] for p in c["points"]]
            for i, p in enumerate(P):
                if i:
                    acc += math.dist(P[i - 1], p)
                U.append(acc)
            for u, p in zip(U, P):
                if c["u_Kb"] - 1e-6 <= u <= c["u_Ka"] + 1e-6:
                    r_out.append(math.dist(O, p))
        if r_in and r_out:
            w_mod = R0 - gp["r_ci"]
            larg = [ro - ri for ro in (min(r_out), max(r_out)) for ri in (min(r_in), max(r_in))]
            ecart_unif = max(larg) - min(larg)
            ecart_mod = max(abs(x - w_mod) for x in larg)
            mes["anneau"] = {"r_interieur": [_r(min(r_in)), _r(max(r_in))], "r_exterieur": [_r(min(r_out)), _r(max(r_out))],
                             "largeur_modele": _r(w_mod), "la": la}
            C.append(critere("GI-01", f"{cid} : anneau de largeur uniforme (bord intérieur fabriqué → arc de l'anneau des coins)",
                             f"largeur {min(larg):.4f}-{max(larg):.4f} m (chaussée annulaire du modèle {w_mod:.2f} m : "
                             f"voies {la:.2f}{' + bande dérasée' if w_mod - la > 1e-3 else ''}) ; écart max {1000 * max(ecart_unif, ecart_mod):.1f} mm",
                             "± 1 cm", ecart_unif <= 0.02 and ecart_mod <= 0.01))
        # ---------------------------------------------------------------- GI-08 raccordements tangents
        rupt, ecr = [], []
        for c in coins:
            P = [p[:2] for p in c["points"]]
            U = [0.0]
            for i in range(1, len(P)):
                U.append(U[-1] + math.dist(P[i - 1], P[i]))
            idx = {k: min(range(len(U)), key=lambda i: abs(U[i] - c[k])) for k in ("u_Tb", "u_Kb", "u_Ka", "u_Ta")}
            for k, i in idx.items():
                if 0 < i < len(P) - 1:
                    rupt.append(angle_rupture(P, i))
            for (a, b, Rc) in ((idx["u_Tb"], idx["u_Kb"], c["rayon_b"]), (idx["u_Kb"], idx["u_Ka"], c["rayon_anneau"]),
                               (idx["u_Ka"], idx["u_Ta"], c["rayon"])):
                fit = cercle_ajuste(P[a:b + 1]) if b - a >= 2 else None
                if fit:
                    ecr.append(abs(fit[1] - Rc))
        if rupt:
            C.append(critere("GI-08", f"{cid} : raccordements d'entrée Re et de sortie Rs tangents à la branche et à l'anneau",
                             f"rupture max {max(rupt):.3f}° ({len(rupt)} points de tangence) ; rayon - consigne max {1000 * max(ecr):.2f} mm "
                             f"({len(ecr)} arcs : Re {coins[0]['rayon']:.0f}, Rs {coins[0]['rayon_b']:.0f}, anneau {R0:.2f})",
                             "≤ 0,5° ; ± 1 cm", max(rupt) <= 0.5 and max(ecr) <= 0.01))
        # ---------------------------------------------------------------- GI-02 déflexion
        rint = [f for f in faces if f["kind"] in ("couronne", "central")]
        if typ != "mini_giratoire" and rint:
            r_ilot = max(sum(math.dist(O, p[:2]) for p in f["points"]) / len(f["points"]) for f in rint)
            rho = r_ilot + 1.5
            defl = {}
            for x in brs:
                if not x.get("n_entrantes"):
                    continue
                for y in brs:
                    if y is x or not y.get("n_sortantes"):
                        continue
                    a = (y["azimut"] - x["azimut"]) % 360.0
                    if not (120.0 <= a <= 240.0):
                        continue
                    A = (x["Pf"][0] + (x["t_d"] + 2.0) * x["nrm"][0], x["Pf"][1] + (x["t_d"] + 2.0) * x["nrm"][1])
                    B = (y["Pf"][0] + (y["t_g"] - 2.0) * y["nrm"][0], y["Pf"][1] + (y["t_g"] - 2.0) * y["nrm"][1])
                    Rd = cercle_deflexion(A, B, O, rho)
                    defl[f"{x['branche']}→{y['branche']}"] = None if Rd is None else _r(Rd, 2)
            mes["deflexion_m"] = defl
            vals = [v for v in defl.values()]
            pire = max((v if v is not None else 1e9) for v in vals) if vals else None
            C.append(critere("GI-02", f"{cid} : déflexion de chaque traversée (îlot fabriqué r = {r_ilot:.2f} m + 1,50 m ; 2,00 m des bordures)",
                             f"max {pire:.2f} m sur {len(vals)} traversées" if pire is not None and pire < 1e8 else "rectiligne",
                             "< 100 m", pire is not None and pire < regles.valeur("RF-GV-GIR-008", "max")))
        # ---------------------------------------------------------------- GI-03 / GI-04 îlots séparateurs, refuges
        seps = [f for f in faces if f["kind"] == "ilot"]
        modeles = [i for i in g5["ilots_modele"] if i.get("carrefour") == cid and i["id"] != gp["ilot_central"]]
        tab = regles.valeur("RF-GV-GIR-013", "valeurs")
        if typ == "mini_giratoire":
            lmin, lmax = regles.valeur("RF-GV-GIR-016", "ilot_separateur")
            larg = []
            for f in seps:
                larg.append(_largeur_max(f, brs))
            C.append(critere("GI-03", f"{cid} : îlots séparateurs du mini-giratoire (RF-GV-GIR-016)",
                             f"{len(seps)} / {len(modeles)} îlots fabriqués" + (f" ; largeurs {min(larg):.2f}-{max(larg):.2f} m" if larg else
                             " (polygones du modèle dégénérés : voir avertissements)"),
                             f"{len(modeles)} îlots de {lmin:.2f} à {lmax:.2f} m",
                             len(seps) == len(modeles) and len(modeles) > 0 and all(lmin <= x <= lmax for x in larg)))
        else:
            if Rg < 15:
                att = {"H": tab["<15"]["H"], "B": tab["<15"]["B"], "d": 0.0, "r": 0.25}
            else:
                att = {"H": Rg, "B": Rg / 4, "d": (0.5 + Rg / 50) / 2, "r": Rg / 50}
            ecs, det = [], {}
            for f in seps:
                m_ = _mesurer_goutte(f, brs, Rg)
                if m_ is None:
                    continue
                det[f["ref"]] = m_
                for k in ("H", "B", "d", "r"):
                    a_ = att[k]
                    if isinstance(a_, list):
                        e_ = 0.0 if a_[0] - 0.01 <= m_[k] <= a_[1] + 0.01 else min(abs(m_[k] - a_[0]), abs(m_[k] - a_[1]))
                    else:
                        e_ = abs(m_[k] - a_)
                    ecs.append(e_)
                ecs.append(abs(m_["retrait_anneau"] - regles.valeur("RF-GV-GIR-013", "retrait_anneau")))
            mes["ilots_separateurs"] = det
            C.append(critere("GI-03", f"{cid} : îlots séparateurs fabriqués = ACI tableau 2 (H, B, d, r ; retrait 1 m)",
                             f"{len(det)} îlots ; écart max {1000 * max(ecs):.1f} mm ; " +
                             "; ".join(f"{k} H {v['H']:.3f} B {v['B']:.3f} d {v['d']:.3f} r {v['r']:.3f} retrait {v['retrait_anneau']:.3f}"
                                       for k, v in list(det.items())[:1]),
                             f"H {att['H']}, B {att['B']}, d {att['d']:.3f}, r {att['r']:.3f} ± 1 cm",
                             len(det) == len(modeles) and len(det) > 0 and max(ecs) <= 0.01))
        # refuges
        pas = [p for p in g5["passages"] if p.get("carrefour") == cid]
        refs = []
        for p in pas:
            # mini-giratoire : îlot séparateur de 0,85-2,00 m (RF-GV-GIR-016), pas un refuge (RF-GV-GIR-014 : 2,00 m)
            if not p.get("refuge") or typ == "mini_giratoire":
                continue
            f = next((f for f in seps if f["ref"] == p["refuge"]), None)
            if f is None:
                refs.append((p["id"], 0.0))
                continue
            a, b = p["axe0"][:2], p["axe1"][:2]
            refs.append((p["id"], _corde(f["points"], a, b)))
        if refs:
            C.append(critere("GI-04", f"{cid} : refuges dans les îlots séparateurs au droit des passages (face fabriquée)",
                             f"min {min(x[1] for x in refs):.3f} m ({len(refs)} refuges)", "≥ 2,00 m",
                             min(x[1] for x in refs) >= regles.valeur("RF-GV-GIR-014", "largeur_au_passage_min") - 1e-4))
            ab = [f for f in seps if f.get("ab0")]
            nab = sum(len(f.get("ab0") or []) for f in seps)
            bev = len({b["id"].rsplit("-", 1)[0] + "-" + b["id"].rsplit("-", 1)[1] for b in g5["bev"] if any(f["ref"].replace(".", "_") in b["id"].replace(".", "_") for f in seps)})
            C.append(critere("GI-12", f"{cid} : abaissés des refuges (DEF-031) et leurs BEV",
                             f"{nab} abaissés sur {len(ab)} îlots ; {bev} BEV", f"{2 * len(refs)} abaissés et autant de BEV",
                             nab == 2 * len(refs) and bev == nab))
        # ---------------------------------------------------------------- GI-05 couronne
        fc = next((f for f in faces if f["kind"] == "couronne"), None)
        if fc:
            coupe = [x for x in g5["coupes_dessus"].get(cid, []) if x[2] == fc["ref"]]
            pente = None
            if len(coupe) >= 3:
                coupe.sort()
                (r1, z1, _), (r2, z2, _) = coupe[1], coupe[-2]
                pente = (z1 - z2) / (r2 - r1) * 100.0     # montée vers le centre
                pente = -pente if pente < 0 else pente
            ent = next((e for e in g5["entites"] if e["id"] == "K-" + fc["ref"].replace(" ", "_")), None)
            vue = max(t - p for t, p in zip(ent["niv_z_tete"], ent["niv_z_pied"])) if ent else fc["vue"]
            mat = fc["materiau_top"]
            p0, p1 = regles.valeur("RF-GV-GIR-006", "bande_pente_pct")
            vmax = regles.valeur("RF-GV-GIR-006", "bande_bordure_vue_max_cm") / 100.0
            C.append(critere("GI-05", f"{cid} : couronne franchissable (bordure, pente, revêtement)",
                             f"vue {vue:.3f} m ; pente {pente:.2f} % ; {mat} (chaussée : enrobé)" if pente is not None else f"vue {vue:.3f}",
                             f"vue ≤ {vmax:.2f} m ; pente {p0}-{p1} % ; matériau contrasté",
                             vue <= vmax + 1e-4 and pente is not None and p0 - 0.05 <= pente <= p1 + 0.05 and "enrobe" not in mat))
        # ---------------------------------------------------------------- GI-06 îlot central sans obstacle (hors agglo)
        if not gp.get("agglomeration"):
            arbres = [a for a in (veg.get("arbres") or []) if math.dist(O, (a.get("x", 1e9), a.get("y", 1e9))) < Rg]
            fcen = next((f for f in faces if f["kind"] == "central"), None)
            C.append(critere("GI-06", f"{cid} : îlot central hors agglomération sans arbre ni obstacle agressif (ACI p. 84)",
                             f"{len(arbres)} arbre ; dessus {fcen['materiau_top'] if fcen else '—'}", "0 arbre, 0 obstacle",
                             len(arbres) == 0 and fcen is not None))
        # ---------------------------------------------------------------- GI-07 passages / ligne CÉDEZ ; GI-09 lignes
        lignes = [l for l in c3["solveur"].get("ligne", []) if l.get("carrefour") == cid and l.get("gabarit") == "CEDEZ"]
        entrants = [b for b in brs if b.get("n_entrantes")]
        C.append(critere("GI-09", f"{cid} : ligne CÉDEZ sur chaque entrée (RF-GV-GIR-024)", f"{len(lignes)} / {len(entrants)}",
                         f"{len(entrants)}", len(lignes) == len(entrants)))
        dists = []
        bands = [m for m in tm.get("marques", []) if m.get("classe") == "passage"]
        for p in pas:
            b = next((x for x in brs if x["route"] == p["route"]), None)
            l = next((l for l in lignes if l.get("route") == p["route"]), None)
            if b is None or l is None:
                continue
            s_l = l["s"] - 0.25                                    # bord amont de la ligne (largeur 0,50 m)
            mb = [m for m in bands if m.get("route") == p["route"]]
            s1 = max(m["s1"] for m in mb) if mb else p["s"] + 0.5 * p["largeur"]
            dists.append(s_l - s1)
        if dists:
            lo, hi = regles.valeur("RF-GV-GIR-015", "urbain_distance_cedez")
            if typ == "mini_giratoire":
                lo = min(lo, 2.0)
            C.append(critere("GI-07", f"{cid} : passages en retrait de la ligne CÉDEZ (bande peinte la plus proche → ligne)",
                             f"{min(dists):.2f}-{max(dists):.2f} m ({len(dists)} passages)", f"{lo:.0f}-{hi:.0f} m (± 5 cm)",
                             lo - 0.05 <= min(dists) and max(dists) <= hi + 0.05))
        # ---------------------------------------------------------------- GI-10 mini-giratoire
        fd = next((f for f in faces if f["kind"] == "dome"), None)
        if fd:
            coupe = sorted(x for x in g5["coupes_dessus"].get(cid, []) if x[2] == fd["ref"])
            zc = coupe[0][1] if coupe else None
            zr = coupe[-1][1] if coupe else None
            pied = sum(fd["pied_z"]) / len(fd["pied_z"])
            h = zc - pied if zc is not None else None
            rel = zr - pied if zr is not None else None
            mq = [v for k, v in g5["marques"].items() if "contour" in k]
            ok_mq = bool(mq) and all(abs(v["largeur_m"] - 0.15) < 1e-3 and v["modulation"] == "T'2" for v in mq)
            d0, d1 = regles.valeur("RF-GV-GIR-016", "dome_cm")
            bus = regles.valeur("RF-GV-GIR-016", "dome_bus_max_cm")
            r0_, r1_ = regles.valeur("RF-GV-GIR-016", "relief_dissuasif_cm")
            C.append(critere("GI-10", f"{cid} : îlot central franchissable en dôme, contour T'2 3u (RF-GV-GIR-016, RF-MQ-GIR-02)",
                             f"dôme {100 * h:.1f} cm ; relief au bord {100 * rel:.1f} cm ; contour "
                             f"{mq[0]['modulation'] if mq else '—'} {mq[0]['largeur_m'] if mq else 0:.2f} m, {mq[0]['traits'] if mq else 0} traits",
                             f"dôme {d0}-{d1} cm (bus ≤ {bus}) ; relief {r0_}-{r1_} cm ; T'2 0,15 m",
                             h is not None and d0 / 100 - 1e-3 <= h <= min(d1, bus) / 100 + 1e-3 and r0_ / 100 - 1e-3 <= rel <= r1_ / 100 + 1e-3 and ok_mq))
        # ---------------------------------------------------------------- GI-11 sol étanche
        C.append(critere("GI-11", f"{cid} : sol étanche (raccords cœur / branches ; bords libres ; îlots posés)",
                         f"écart max {1000 * m3['ecart_max_m']:.2f} mm ; {m3['bords_libres_hors_exterieur']} bords libres hors extérieur ; "
                         f"îlots : {m5['bords_libres_au_dessus_du_sol']} bords libres visibles",
                         "≤ 1 mm ; 0 ; 0",
                         m3["ecart_max_m"] <= 0.001 and m3["bords_libres_hors_exterieur"] == 0 and m5["bords_libres_au_dessus_du_sol"] == 0))
        mes["avertissements"] = g5.get("avertissements", [])
    return res


def _repere(f, brs):
    """Branche d'un îlot séparateur : celle dont l'axe passe le plus près du centre de l'îlot."""
    P = [p[:2] for p in f["points"]]
    G = (sum(p[0] for p in P) / len(P), sum(p[1] for p in P) / len(P))
    best = None
    for b in brs:
        v = (G[0] - b["Pf"][0], G[1] - b["Pf"][1])
        x = -(v[0] * b["dir"][0] + v[1] * b["dir"][1])
        y = v[0] * b["nrm"][0] + v[1] * b["nrm"][1]
        if x > -2.0 and (best is None or abs(y) < best[0]):
            best = (abs(y), b)
    return best[1] if best else None


def _local(P, b):
    return [(-((p[0] - b["Pf"][0]) * b["dir"][0] + (p[1] - b["Pf"][1]) * b["dir"][1]),
             (p[0] - b["Pf"][0]) * b["nrm"][0] + (p[1] - b["Pf"][1]) * b["nrm"][1]) for p in P]


def _droite(pts):
    """y = a x + c (moindres carrés)."""
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    a = sxy / sxx
    return a, my - a * mx


def _mesurer_goutte(f, brs, R0):
    """Enveloppe de l'îlot (ACI tableau 2) retrouvée sur la face fabriquée : côtés longs (droites ajustées) décalés de
    la saillie de 0,50 m vers l'extérieur ; H = abscisse du sommet depuis la frontière ; B = écart des côtés à la
    frontière ; d = décalage du sommet par rapport à l'axe ; r = rayon du nez (cercle ajusté) ; retrait à l'anneau."""
    b = _repere(f, brs)
    if b is None:
        return None
    P = [p[:2] for p in f["points"]]
    L = _local(P, b)
    xs = [p[0] for p in L]
    x0, x1 = min(xs), max(xs)
    ym = sum(p[1] for p in L) / len(L)
    mil = [p for p in L if x0 + 0.25 * (x1 - x0) <= p[0] <= x1 - 0.15 * (x1 - x0)]
    gauche = [p for p in mil if p[1] > ym]
    droite = [p for p in mil if p[1] <= ym]
    if len(gauche) < 2 or len(droite) < 2:
        return None
    sail = 0.5
    ag, cg = _droite(gauche)
    ad, cd = _droite(droite)
    cg += sail * math.sqrt(1 + ag * ag)
    cd -= sail * math.sqrt(1 + ad * ad)
    xa = (cd - cg) / (ag - ad)
    ya = ag * xa + cg
    B = cg - cd
    # nez : points à moins de 1,2 r_estimé du bout
    tip = sorted(L, key=lambda p: -p[0])[:9]
    fit = cercle_ajuste(tip)
    r = fit[1] if fit else 0.0
    ret = min(math.dist((0, 0), (p[0] - 0, p[1])) for p in [(0, 0)]) if False else min(
        math.hypot(q[0] - b["centre"][0], q[1] - b["centre"][1]) for q in P) - R0
    return {"branche": b["branche"], "H": round(xa, 4), "B": round(B, 4), "d": round(abs(ya), 4), "r": round(r, 4),
            "retrait_anneau": round(ret, 4), "longueur_ilot": round(x1 - x0, 4)}


def _corde(pts, a, b):
    """Longueur de la droite (a, b) dans le polygone pts (somme des intervalles intérieurs)."""
    P = [p[:2] for p in pts]
    if P[0] == P[-1]:
        P = P[:-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    ts = []
    for i in range(len(P)):
        p, q = P[i], P[(i + 1) % len(P)]
        ex, ey = q[0] - p[0], q[1] - p[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = ((p[0] - a[0]) * ey - (p[1] - a[1]) * ex) / den
        u = ((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / den
        if 0 <= u <= 1:
            ts.append(t)
    ts.sort()
    return sum((ts[i + 1] - ts[i]) * L for i in range(0, len(ts) - 1, 2))


def _largeur_max(f, brs):
    b = _repere(f, brs)
    L = _local([p[:2] for p in f["points"]], b)
    return max(p[1] for p in L) - min(p[1] for p in L)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    dossiers = [Path(s) if Path(s).exists() else SORTIE / s for s in (a.scenes or SCENES)]
    out = {"schema": "rg_controles_giratoires/0.1", "scenes": []}
    for d in dossiers:
        r = controler_scene(d)
        out["scenes"].append(r)
        for c in r["criteres"]:
            print(f"{'OK ' if c['atteint'] else 'NON'} {c['id']} {c['critere']} : {c['valeur']} (seuil {c['seuil']})")
        for cid, m in r["mesures"].items():
            for x in m.get("avertissements", []):
                print("   avertissement :", x)
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
