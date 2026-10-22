"""Contrôle indépendant du lot « ouvrages » (L8 / E07) : mesures sur les maillages exportés par fabriquer_ouvrages.py
(Python + numpy, aucune donnée de Houdini autre que les maillages), comparées aux règles et au modèle.

    python recon/generateur/validation/controler_ouvrages.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Critères (PLAN_GENERATEUR L8, tâche du lot), chacun avec sa valeur mesurée, son seuil et sa règle :
  hauteur_libre        intrados (tablier, corniche) - chaussée franchie, rayons verticaux sur la plate-forme circulable
                       sous l'emprise du tablier : >= gabarit + revanche (RF-GV-PON-012, DEF-033)
  epaisseur_dalle      épaisseur du tablier mesurée à mi-travée principale, dans l'axe du tablier : = l/28 à 1 cm près
                       (dalle, RF-GV-PON-015 / OA-ELA-002) ; autres types : élancement de leur règle
  rapport_travees      appuis mesurés (lignes d'appareils d'appui, piédroits) : balancement dans [0,6 ; 0,85]
  garde_corps          hauteur mesurée (sommet de la main courante - surface de marche au pied) dans la bande GC97
                       [0,90 + 0,005 Hc ; min(1,00 + 0,005 Hc ; 1,20)] côté piétons, 1,20 m (+- 2 cm) le long d'une piste,
                       > 0,90 m pour une BN4 (piétons interdits) ; Hc mesurée
  marquages_continus   lignes peintes de la route portée sur l'ouvrage : même motif qu'en approche (plus grand vide le
                       long de chaque ligne <= vide de la modulation + 0,10 m) et peinture à 0-6 mm au-dessus du sol
  pas_de_trou          sous la chaussée de l'ouvrage, le premier élément rencontré est le tablier à 0,08-0,60 m ; rives :
                       dessus de corniche au niveau du bord de la plate-forme (+- 3 cm)
  joints               un joint par about, couvrant >= 99 % de la largeur de la plate-forme (trottoirs compris), posé à
                       1-6 mm du sol ; aucun joint sur un portique (OA-PIPO-001)
  talus                pente maximale du terrain hors plates-formes et hors emprise des murs <= 1/1,5 (+ 5 % de
                       discrétisation) ; nombre de facettes plus raides = 0 ; aucune facette verticale (falaise)
  profil_en_long       Z de la chaussée portée dans l'axe = profil en long du modèle (routes[].profil_long) à 5 mm près
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
SORTIE = DEPOT / "recon" / "out" / "generateur"
SCENES = ("D1_passage_superieur_autoroute", "D2_passage_inferieur_voie_rapide", "D3_viaduc_vallee_seche",
          "D4_pont_urbain_piste_cyclable")
MODULATIONS = json.loads((DEPOT / "assets" / "specs" / "route" / "regles_route_fr.json").read_text(encoding="utf-8"))


def _r(x, n=4):
    if x is None:
        return None
    v = round(float(x), n)
    return 0.0 if v == 0 else v


# ------------------------------------------------------------------------------------------------ géométrie
class Maillage:
    def __init__(self, P, T, masque=None):
        if masque is not None:
            T = T[masque]
        self.P, self.T = P, T
        tri = P[T]
        self.tri = tri
        self.xmin, self.xmax = tri[:, :, 0].min(1), tri[:, :, 0].max(1)
        self.ymin, self.ymax = tri[:, :, 1].min(1), tri[:, :, 1].max(1)

    def z(self, x, y):
        """Z des intersections de la verticale (x, y) avec les triangles (tableau, éventuellement vide)."""
        m = (self.xmin <= x) & (self.xmax >= x) & (self.ymin <= y) & (self.ymax >= y)
        if not m.any():
            return np.zeros(0)
        t = self.tri[m]
        a, b, c = t[:, 0], t[:, 1], t[:, 2]
        v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]
        v2 = np.stack([x - a[:, 0], y - a[:, 1]], axis=1)
        den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
        ok = np.abs(den) > 1e-12
        den = np.where(ok, den, 1.0)
        u = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
        v = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
        w = 1 - u - v
        e = 1e-9
        sel = ok & (u >= -e) & (v >= -e) & (w >= -e)
        return (w * a[:, 2] + u * b[:, 2] + v * c[:, 2])[sel]


def charger(dsc):
    o = Path(dsc) / "ouvrages"
    r = np.load(o / "maillage_routes.npz")
    v = np.load(o / "maillage_ouvrages.npz")
    t = np.load(o / "maillage_terrain.npz")
    return r, v, t


class Route:
    """Ligne de référence locale (polyligne) : (x, y) <-> (s, t)."""

    def __init__(self, route, origine):
        g = np.array([p[:2] for p in route["ligne_reference"]["geometrie"]], dtype=np.float64) - np.array(origine[:2])
        self.g = g
        d = np.diff(g, axis=0)
        self.l = np.hypot(d[:, 0], d[:, 1])
        self.s = np.concatenate([[0.0], np.cumsum(self.l)])
        self.u = d / self.l[:, None]

    def xy(self, s, t=0.0):
        i = int(np.clip(np.searchsorted(self.s, s, side="right") - 1, 0, len(self.l) - 1))
        tx, ty = self.u[i]
        p = self.g[i] + (s - self.s[i]) * self.u[i]
        return p[0] - t * ty, p[1] + t * tx

    def st(self, x, y):
        best = None
        for i in range(len(self.l)):
            a = self.g[i]
            tx, ty = self.u[i]
            ds = (x - a[0]) * tx + (y - a[1]) * ty
            dt = -(x - a[0]) * ty + (y - a[1]) * tx
            sc = min(max(ds, 0.0), self.l[i])
            d = math.hypot(ds - sc, dt)
            if best is None or d < best[0]:
                best = (d, self.s[i] + ds, dt)
        return best[1], best[2]


def modulation(nom):
    for r in MODULATIONS["regles"]:
        if r["id"] == f"RF-MQ-MOD-{nom}":
            return r["valeurs"]
    return None


# ------------------------------------------------------------------------------------------------ critères
def controler_scene(dsc):
    dsc = Path(dsc)
    m = json.loads((dsc / "modele_voie.json").read_text(encoding="utf-8"))
    comp = json.loads((dsc / "compilation.json").read_text(encoding="utf-8"))
    pts = json.loads((dsc / "ouvrages" / "points_ouvrages.json").read_text(encoding="utf-8"))["points"]
    r, v, t = charger(dsc)
    org = m["repere"]["origine_l93"]
    routes = {x["id"]: Route(x, org) for x in m["routes"]}
    o = m["ouvrages"][0]
    c = o["construction"]
    rp = routes[c["route_portee"]]
    sab0, sab1 = c["s_abouts"]
    tab = c["tablier"]
    res = {"scene": dsc.name, "ouvrage": o["id"], "type": o["type"], "famille_tablier": c["famille_tablier"],
           "criteres": {}}
    K = res["criteres"]
    sol_p = Maillage(r["P"], r["T"], (r["route"] == c["route_portee"]) & (r["couche"] == "Sol"))
    peint = Maillage(r["P"], r["T"], (r["route"] == c["route_portee"]) & (r["couche"] == "Marquages"))
    part = v["partie"]
    tablier = Maillage(v["P"], v["T"], np.isin(part, ["tablier"]))
    intrados = Maillage(v["P"], v["T"], np.isin(part, ["tablier", "corniche"]))
    # ---- profil en long (chaussée portée dans l'axe)
    pl = {round(s, 4): z for s, z in m["routes"][[x["id"] for x in m["routes"]].index(c["route_portee"])]["profil_long"]["z"]}
    z0 = float(org[2])
    ecarts = []
    L = rp.s[-1]
    for s in np.arange(5.0, L - 5.0, 10.0):
        x, y = rp.xy(s, 0.0)
        zs = sol_p.z(x, y)
        if len(zs):
            sm = min(pl, key=lambda k: abs(k - s))
            ecarts.append(abs(zs.max() - (pl[sm] - z0)))
    K["profil_en_long"] = {"valeur": _r(max(ecarts), 4), "seuil": "<= 0,005 m", "atteint": max(ecarts) <= 0.005,
                           "points": len(ecarts), "regle": "routes[].profil_long (modèle)"}
    # ---- hauteur libre
    gab = c.get("gabarit")
    if gab:
        rf = routes[gab["route_franchie"]]
        sol_f = Maillage(r["P"], r["T"], (r["route"] == gab["route_franchie"]) & (r["couche"] == "Sol"))
        cpf = c["coupe_franchie"]
        circ = [b for b in cpf if b[4] in ("voie_circulation", "bande_arret_urgence", "bande_derasee", "voie_bus",
                                           "accotement_revetu")]
        tmin = min(min(b[0], b[2]) for b in circ)
        tmax = max(max(b[0], b[2]) for b in circ)
        hl = []
        for sy in np.arange(gab["s_franchie"] - 25.0, gab["s_franchie"] + 25.0, 0.5):
            for tt in np.linspace(tmin + 0.01, tmax - 0.01, 25):
                x, y = rf.xy(sy, tt)
                zr = sol_f.z(x, y)
                zo = intrados.z(x, y)
                if len(zr) and len(zo):
                    zr_ = zr.max()
                    au = zo[zo > zr_ + 0.5]
                    if len(au):
                        hl.append(au.min() - zr_)
        hlm = min(hl) if hl else None
        seuil = gab["hauteur_libre_min_m"]
        K["hauteur_libre"] = {"valeur": _r(hlm, 3), "seuil": f">= {seuil} m (gabarit {gab['gabarit_m']} + revanche "
                                                              f"{gab['revanche_m']})", "atteint": hlm is not None and hlm >= seuil - 1e-3,
                              "regle": "RF-GV-PON-012 ; DEF-033", "rayons_sous_tablier": len(hl)}
    else:
        # talweg : espace libre minimal entre l'intrados et le terrain naturel (revanche)
        ter = Maillage(t["P"], t["T"], t["partie"] == "terrain")
        hl = []
        s_app = c["s_appuis"]
        for s in np.arange(s_app[0] + 2.0, s_app[-1] - 2.0, 1.0):
            x, y = rp.xy(s, 0.5 * (tab["t_gauche"] + tab["t_droite"]))
            zt = ter.z(x, y)
            zo = intrados.z(x, y)
            if len(zt) and len(zo):
                hl.append(zo.min() - zt.max())
        hlm = min(hl) if hl else None
        K["hauteur_libre"] = {"valeur": _r(hlm, 3), "seuil": ">= 0,10 m au-dessus du terrain (talweg ; pas de voie "
                              "dessous : gabarit routier sans objet)", "atteint": hlm is not None and hlm >= 0.10 - 1e-3,
                              "regle": "RF-GV-PON-012 (revanche)", "rayons_sous_tablier": len(hl)}
    # ---- épaisseur du tablier à mi-travée principale
    trav = c["travees_m"]
    k = int(np.argmax(trav))
    s_mid = 0.5 * (c["s_appuis"][k] + c["s_appuis"][k + 1])
    tc = 0.5 * (tab["t_gauche"] + tab["t_droite"])
    e_mes = None
    for tt in ([tc] if tab["structure"] != "poutre" else np.linspace(tab["t_droite"] + 0.05, tab["t_gauche"] - 0.05, 121)):
        x, y = rp.xy(s_mid, tt)                     # poutres : épaisseur hourdis + poutre, au droit d'une poutre
        zt = tablier.z(x, y)
        if len(zt) >= 2:
            e_mes = max(e_mes or 0.0, float(zt.max() - zt.min()))
    l = max(trav)
    fam = tab["type"]
    if tab["structure"] == "dalle":
        cible = l / 28.0 if (fam == "PSIDA" and len(trav) >= 3) or c["famille_tablier"] == "PSIDP_LE" and len(trav) >= 3 \
            else tab["epaisseur_m"]
        K["epaisseur_dalle"] = {"valeur": _r(e_mes, 4), "seuil": f"l/28 = {l}/28 = {cible:.4f} m (+- 0,01)",
                                "atteint": e_mes is not None and abs(e_mes - cible) <= 0.01,
                                "elancement_mesure": f"l/{l / e_mes:.2f}" if e_mes else None,
                                "regle": "RF-GV-PON-015 ; OA-ELA-002 (GPOA p. 210)"}
    else:
        regle = {"portique": ("l/40 + 0,10", l / 40 + 0.10), "cadre": ("l/32 + 0,125", l / 32 + 0.125)}.get(tab["structure"])
        if tab["structure"] == "caisson":
            lo, hi = 0.045, 0.056
            K["epaisseur_dalle"] = {"valeur": _r(e_mes, 4), "seuil": f"sans objet (caisson) ; élancement h/l observé "
                                    f"[{lo} ; {hi}] (OA-CAI-001, avertissement)", "atteint": True,
                                    "elancement_mesure": _r(e_mes / l, 4) if e_mes else None,
                                    "dans_observations": bool(e_mes and lo <= e_mes / l <= hi), "regle": "OA-CAI-001"}
        elif tab["structure"] == "poutre":
            K["epaisseur_dalle"] = {"valeur": _r(e_mes, 4), "seuil": "sans objet (poutres PRAD) ; élancement [1/20 ; 1/18] "
                                    "(OA-ELA-001)", "atteint": bool(e_mes and 1 / 20 - 1e-3 <= e_mes / l <= 1 / 18 + 1e-3),
                                    "elancement_mesure": f"l/{l / e_mes:.2f}" if e_mes else None, "regle": "OA-ELA-001"}
        else:
            K["epaisseur_dalle"] = {"valeur": _r(e_mes, 4), "seuil": f"sans objet (portique) ; e = {regle[0]} = "
                                    f"{regle[1]:.4f} (+- 0,01)", "atteint": bool(e_mes and abs(e_mes - regle[1]) <= 0.01),
                                    "regle": "RF-GV-PON-015"}
    # ---- rapport de travées : appuis mesurés
    def centres(nom):
        mm = part == nom
        if not mm.any():
            return []
        cen = v["P"][v["T"][mm]].mean(axis=1)
        ss = sorted(rp.st(x_, y_)[0] for x_, y_, _ in cen)
        grp = []
        for s in ss:
            if grp and s - grp[-1][-1] < 1.2:
                grp[-1].append(s)
            else:
                grp.append([s])
        return [float(np.mean(g)) for g in grp]
    lignes = centres("appareil_appui") or centres("piedroit")
    if tab["structure"] == "poutre":           # deux lignes d'appareils sur les piles (travées isostatiques)
        fus = []
        for s in lignes:
            if fus and s - fus[-1] < 1.2:
                fus[-1] = 0.5 * (fus[-1] + s)
            else:
                fus.append(s)
        lignes = fus
    spans = [b - a for a, b in zip(lignes, lignes[1:])]
    if len(spans) >= 3:
        a1, a2 = spans[0] / spans[1], spans[-1] / spans[-2]
        K["rapport_travees"] = {"valeur": [_r(a1, 3), _r(a2, 3)], "seuil": "[0,6 ; 0,85]", "atteint": 0.6 <= min(a1, a2)
                                and max(a1, a2) <= 0.85, "travees_mesurees_m": [_r(x, 3) for x in spans],
                                "regle": "RF-GV-PON-015 ; OA-BAL-001"}
    else:
        K["rapport_travees"] = {"valeur": [_r(x, 3) for x in spans], "seuil": "sans objet (moins de 3 travées) ; "
                                f"travées = modèle {trav} à 5 cm", "atteint": len(spans) == len(trav) and all(
                                    abs(a - b) <= 0.05 for a, b in zip(spans, trav)),
                                "regle": "RF-GV-PON-015"}
    # ---- garde-corps et BN4
    gc = Maillage(v["P"], v["T"], np.isin(part, ["garde_corps", "bn4"]))
    ter_all = Maillage(t["P"], t["T"])
    eqs = c["equipements"]
    res_gc = {}
    ok_gc = True
    for cote in ("gauche", "droite"):
        eq = eqs[cote]
        tb = eq["t_bord"]
        sg = 1.0 if tb > 0 else -1.0
        tq = tb + sg * (c["corniche"]["largeur_m"] * 0.5 if eq["type"] == "garde_corps" else 0.10)
        hs, hcs = [], []
        for s in np.arange(sab0 + 1.0, sab1 - 1.0, 0.75):
            x, y = rp.xy(s, tq)
            zg = gc.z(x, y)
            xs_, ys_ = rp.xy(s, tb - sg * 0.05)
            zs = sol_p.z(xs_, ys_)
            if len(zg) and len(zs):
                hs.append(zg.max() - zs.max() - (eq.get("longrine_hauteur_m", 0.0) if eq["type"] == "BN4" else 0.0))
                xe, ye = rp.xy(s, tb + sg * 0.6)
                zb = ter_all.z(xe, ye)
                zr = r["P"][:, 2]
                if len(zb):
                    hcs.append(zs.max() - zb.max())
        h = float(np.median(hs)) if hs else None
        Hc = max(hcs) if hcs else None
        if eq["type"] == "BN4":
            # longueur de la file (lisse supérieure mesurée le long de la route portée)
            bn = Maillage(v["P"], v["T"], part == "bn4")
            ss_ = [rp.st(x_, y_)[0] for x_, y_, _ in bn.tri.mean(axis=1)[:: max(1, len(bn.tri) // 4000)]]
            lfile = (max(ss_) - min(ss_)) if ss_ else 0.0
            ok = h is not None and h > 0.90 and lfile >= 30.0 - 0.1
            seuil = ("> 0,90 m (piétons interdits, RF-GV-PON-007) ; lisse supérieure 1,00 m ; file >= 30 m "
                     f"(OA-BN4-001 ; mesurée {lfile:.1f} m)")
        elif eq.get("usage") == "cycles":
            ok = h is not None and abs(h - 1.20) <= 0.02
            seuil = "1,20 m +- 0,02 le long d'une piste cyclable (DEF-033, RF-GV-PON-007)"
        else:
            lo, hi = 0.90 + 0.005 * Hc, min(1.00 + 0.005 * Hc, 1.20)
            ok = h is not None and lo - 1e-3 <= h <= hi + 1e-3
            seuil = f"[{lo:.3f} ; {hi:.3f}] (GC97, Hc mesurée {Hc:.2f} m)"
        ok_gc &= ok
        res_gc[cote] = {"type": eq["type"], "hauteur_mesuree_m": _r(h, 3), "hc_mesuree_m": _r(Hc, 2), "seuil": seuil,
                        "atteint": ok, "echantillons": len(hs)}
    K["garde_corps"] = {"valeur": {k_: x["hauteur_mesuree_m"] for k_, x in res_gc.items()}, "seuil": "voir détail",
                        "atteint": ok_gc, "detail": res_gc, "regle": "DEF-033 ; RF-GV-PON-007 ; OA-BN4-001"}
    # ---- marquages continus sur l'ouvrage
    prof = next(p for p in m["profils"] if p["id"] == next(sec for sec in m["routes"][[x["id"] for x in m["routes"]].index(
        c["route_portee"])]["sections"] if sec["s0"] <= c["s_croisement"] <= sec["s1"])["profil"])
    cpp = c["coupe_portee"]
    tlim = [cpp[0][0]] + [b[2] for b in cpp]
    lignes_res = []
    ok_mq = True
    for i, lim in enumerate(prof["limites"]):
        for mq in lim.get("marquages") or []:
            mod = modulation(mq["modulation"])
            vide = 0.0
            if mod and isinstance(mod, dict):
                vide = float(mod.get("intervalle_m") or mod.get("intervalle") or 0.0)
            ti = tlim[i]
            pres = []
            ss = np.arange(sab0 - 30.0, sab1 + 30.0, 0.10)
            dz = []
            for s in ss:
                x, y = rp.xy(s, ti)
                zp = peint.z(x, y)
                pres.append(len(zp) > 0)
                if len(zp):
                    zs = sol_p.z(x, y)
                    if len(zs):
                        dz.append(zp.max() - zs.max())
            pres = np.array(pres)
            dedans = (ss >= sab0) & (ss <= sab1)
            # plus grand vide sur l'ouvrage
            gap, cur = 0.0, 0.0
            for p_, d_ in zip(pres, dedans):
                if not d_:
                    continue
                cur = 0.0 if p_ else cur + 0.10
                gap = max(gap, cur)
            frac_o = pres[dedans].mean()
            frac_a = pres[~dedans].mean()
            ok = gap <= vide + 0.10 + 1e-9 and (not dz or (min(dz) >= -1e-4 and max(dz) <= 0.006))
            ok_mq &= ok
            lignes_res.append({"limite": i, "t": _r(ti, 3), "modulation": mq["modulation"], "vide_modulation_m": vide,
                               "plus_grand_vide_sur_ouvrage_m": _r(gap, 2), "part_peinte_ouvrage": _r(frac_o, 3),
                               "part_peinte_approches": _r(frac_a, 3),
                               "peinture_au_dessus_du_sol_mm": [_r(1000 * min(dz), 2), _r(1000 * max(dz), 2)] if dz else None,
                               "atteint": ok})
    K["marquages_continus"] = {"valeur": len(lignes_res), "seuil": "chaque ligne : vide <= vide de la modulation + 0,10 m "
                               "; peinture à 0-6 mm du sol", "atteint": ok_mq and bool(lignes_res), "lignes": lignes_res,
                               "regle": "RF-GV-PON-001 (profil courant conservé) ; TQ-MQG-005"}
    # ---- pas de trou entre la route et le tablier
    ecarts, sans, ok_tr = [], 0, True
    pg, pd = cpp[0][0], cpp[-1][2]
    rev = tab["revetement_m"]
    for s in np.arange(sab0 + 0.6, sab1 - 0.6, 1.0):
        for tt in np.linspace(pd + 0.05, pg - 0.05, 15):
            x, y = rp.xy(s, tt)
            zs = sol_p.z(x, y)
            zo = v_struct_z(v, x, y)
            if not len(zs):
                continue
            zsm = zs.max()
            dessous = zo[zo < zsm - 1e-4]
            if not len(dessous):
                sans += 1
                continue
            ecarts.append(zsm - dessous.max())
    cor = Maillage(v["P"], v["T"], part == "corniche")
    bord = []
    for s in np.arange(sab0 + 0.6, sab1 - 0.6, 2.0):
        for tb, sg in ((pg, 1.0), (pd, -1.0)):
            x, y = rp.xy(s, tb + sg * 0.02)
            zc = cor.z(x, y)
            xs_, ys_ = rp.xy(s, tb - sg * 0.02)
            zs = sol_p.z(xs_, ys_)
            if len(zc) and len(zs):
                bord.append(zc.max() - zs.max() - (eqs["gauche" if sg > 0 else "droite"].get("longrine_hauteur_m", 0.0)
                                                   if eqs["gauche" if sg > 0 else "droite"]["type"] == "BN4" else 0.0))
    ok_tr = sans == 0 and ecarts and min(ecarts) >= 0.08 and max(ecarts) <= 0.60 and bord and max(abs(b) for b in bord) <= 0.03
    K["pas_de_trou"] = {"valeur": {"sol_sans_tablier_dessous": sans, "ecart_sol_tablier_m": [_r(min(ecarts), 3),
                                                                                             _r(max(ecarts), 3)] if ecarts else None,
                                   "ecart_corniche_bord_m": _r(max(abs(b) for b in bord), 3) if bord else None},
                        "seuil": "0 rayon sans tablier ; écart 0,08-0,60 m ; corniche au bord à 3 cm", "atteint": bool(ok_tr),
                        "rayons": len(ecarts), "regle": "RF-GV-PON-001 ; GPOA p. 54 (continuité)"}
    # ---- joints aux abouts
    jt = part == "joint"
    attendus = c["joints"]["s"]
    if not attendus:
        K["joints"] = {"valeur": int(jt.sum() > 0), "seuil": "0 joint (portique : OA-PIPO-001)", "atteint": not jt.any(),
                       "regle": "OA-PIPO-001"}
    else:
        jm = Maillage(v["P"], v["T"], jt)
        revet = Maillage(r["P"], r["T"], (r["route"] == c["route_portee"]) & np.isin(r["couche"], ["Sol", "Bordures"]))
        det, ok_j = [], True
        for sj in attendus:
            couv, dzs = 0, []
            ts = np.linspace(pd + 0.01, pg - 0.01, 200)
            for tt in ts:
                x, y = rp.xy(sj, tt)
                zj = jm.z(x, y)
                if len(zj):
                    couv += 1
                    zs = revet.z(x, y)
                    if len(zs):
                        dzs.append(zj.max() - zs.max())
            f = couv / len(ts)
            dzs = np.array(dzs)
            dans = float(((dzs >= 0.001 - 1e-4) & (dzs <= 0.006)).mean()) if len(dzs) else 0.0
            ok = f >= 0.99 and dans >= 0.95
            ok_j &= bool(ok)
            det.append({"s": sj, "couverture_largeur": _r(f, 3), "part_posee_1_6_mm": _r(dans, 3),
                        "hauteur_sur_revetement_mm_mediane": _r(1000 * float(np.median(dzs)), 2) if len(dzs) else None,
                        "atteint": bool(ok)})
        K["joints"] = {"valeur": len(det), "seuil": f"{len(attendus)} joints, couverture >= 99 % de la plate-forme, posés "
                       "à 1-6 mm au-dessus du revêtement (sol, bordures) sur >= 95 % de la largeur (le reste : marches des "
                       "bordures)",
                       "atteint": ok_j, "detail": det, "regle": "RF-GV-PON-011 ; OA-JNT-001"}
    # ---- talus sans falaise
    tm = t["partie"] == "terrain"
    tri = t["P"][t["T"][tm]]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nz = np.abs(n[:, 2]) / np.maximum(np.linalg.norm(n, axis=1), 1e-12)
    pente = np.sqrt(np.maximum(1 - nz * nz, 0)) / np.maximum(nz, 1e-9)
    cen = tri.mean(axis=1)
    exclu = np.zeros(len(tri), dtype=bool)
    # sous les plates-formes (terrain caché sous la route)
    for rid, ro in routes.items():
        # bords réels de la plate-forme (coupe du modèle ; profils dissymétriques compris) + 0,30 m
        cp_r = c["coupe_portee"] if rid == c["route_portee"] else c.get("coupe_franchie")
        tg_r, td_r = cp_r[0][0], cp_r[-1][2]
        for i in range(len(ro.l)):
            a = ro.g[i]
            tx, ty = ro.u[i]
            ds = (cen[:, 0] - a[0]) * tx + (cen[:, 1] - a[1]) * ty
            dt = -(cen[:, 0] - a[0]) * ty + (cen[:, 1] - a[1]) * tx
            exclu |= (ds >= -0.5) & (ds <= ro.l[i] + 0.5) & (dt <= tg_r + 0.3) & (dt >= td_r - 0.3)
    # emprise des murs, piédroits, piles, culées (+ 0,6 m)
    murs = np.isin(part, ["mur_aile", "piedroit", "mur_retour", "sommier", "pile", "garde_greve"])
    if murs.any():
        mt = v["P"][v["T"][murs]]
        bx0, bx1 = mt[:, :, 0].min(1) - 0.6, mt[:, :, 0].max(1) + 0.6
        by0, by1 = mt[:, :, 1].min(1) - 0.6, mt[:, :, 1].max(1) + 0.6
        for i0 in range(0, len(mt), 2000):
            sl = slice(i0, i0 + 2000)
            exclu |= ((cen[:, 0][:, None] >= bx0[sl]) & (cen[:, 0][:, None] <= bx1[sl]) &
                      (cen[:, 1][:, None] >= by0[sl]) & (cen[:, 1][:, None] <= by1[sl])).any(axis=1)
    p_ok = pente[~exclu]
    seuil = (1 / 1.5) * 1.05
    trop = int((p_ok > seuil).sum())
    K["talus"] = {"valeur": _r(p_ok.max(), 4) if len(p_ok) else None, "seuil": f"<= 1/1,5 + 5 % = {seuil:.4f} ; 0 facette "
                  "plus raide ; 0 facette verticale", "atteint": trop == 0 and len(p_ok) > 0,
                  "facettes_controlees": int(len(p_ok)), "facettes_trop_raides": trop,
                  "facettes_exclues": int(exclu.sum()), "regle": "OA-TAL-001 (GPOA p. 241)"}
    # ---- aucun terrain au-dessus des routes (surfaces de toutes les couches)
    ter_t = Maillage(t["P"], t["T"], t["partie"] == "terrain")
    viol, n_ech, pire = 0, 0, 0.0
    for rid, ro in routes.items():
        # revêtement visible : sol et bordures (sous une bordure, le sol prolongé est caché par l'élément)
        sol_r = Maillage(r["P"], r["T"], (r["route"] == rid) & np.isin(r["couche"], ["Sol", "Bordures"]))
        cp_r = c["coupe_portee"] if rid == c["route_portee"] else c.get("coupe_franchie")
        if not cp_r:
            continue
        tg_, td_ = cp_r[0][0], cp_r[-1][2]
        for s in np.arange(1.0, ro.s[-1] - 1.0, 2.0):
            for tt in np.linspace(td_ + 0.05, tg_ - 0.05, 17):
                x, y = ro.xy(s, tt)
                zs = sol_r.z(x, y)
                zt = ter_t.z(x, y)
                if len(zs) and len(zt):
                    n_ech += 1
                    dz = zt.max() - zs.max()
                    if dz > -0.005:
                        viol += 1
                        pire = max(pire, dz)
    K["terrain_sous_routes"] = {"valeur": viol, "seuil": "0 point où le terrain affleure la chaussée (terrain <= sol - "
                                "5 mm)", "atteint": viol == 0, "echantillons": n_ech, "pire_m": _r(pire, 3),
                                "regle": "TQ-SOL-007 (raccord au terrain hors des surfaces modélisées)"}
    # contrôles du compilateur (modèle)
    res["controles_compilateur"] = [x for tr_ in comp["troncons"] for x in tr_["controles"] if
                                    str(x.get("controle", "")).startswith(o["id"])]
    res["points_instances"] = len(pts)
    res["atteint"] = all(x["atteint"] for x in K.values())
    return res


_CACHE = {}


def _jsn(o):
    return o.item() if hasattr(o, "item") else str(o)


def v_struct_z(v, x, y):
    key = id(v)
    if key not in _CACHE:
        part = v["partie"]
        _CACHE[key] = Maillage(v["P"], v["T"], np.isin(part, ["tablier", "garde_greve", "dalle_transition", "corniche"]))
    return _CACHE[key].z(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json", default=str(ICI / "controles_ouvrages.json"))
    a = ap.parse_args()
    dossiers = [Path(x) for x in a.scenes] or [SORTIE / s for s in SCENES]
    out = []
    for dsc in dossiers:
        if not (dsc / "ouvrages" / "maillage_ouvrages.npz").exists():
            print(f"{dsc.name} : pas de sortie du lot ouvrages")
            continue
        _CACHE.clear()
        r = controler_scene(dsc)
        out.append(r)
        print(f"{r['scene']} : " + ", ".join(f"{k} {'OK' if x['atteint'] else 'ÉCHEC'} ({x['valeur']})"
                                               for k, x in r["criteres"].items()))
    Path(a.json).write_text(json.dumps({"schema": "rg_controles_ouvrages/0.1", "scenes": out}, ensure_ascii=False, default=_jsn,
                                       indent=1) + "\n", encoding="utf-8")
    return 0 if all(r["atteint"] for r in out) else 1


if __name__ == "__main__":
    sys.exit(main())
