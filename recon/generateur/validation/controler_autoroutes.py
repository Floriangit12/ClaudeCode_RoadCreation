"""Contrôle indépendant du lot « autoroutes » (Python du système, sans Houdini) : mesures sur la géométrie FABRIQUÉE
(sol l2/, peinture l2b/, équipements et musoirs autoroute/) comparées aux cotes du modèle et des sources.

    python recon/generateur/validation/controler_autoroutes.py [recon/out/generateur/<scene> ...] [--json SORTIE]

Mesures (tolérances du lot : largeurs et modulations ± 1 cm, gabarits ± 1 mm, biseaux : longueurs sourcées ± 1 cm) :
  - largeurs des bandes (sol fabriqué, sommets sur les limites aux abscisses d'échantillonnage) ;
  - lignes : trait, intervalle (RF-MQ-MOD-*) et largeur (largeur_u × u, RF-MQ-U-01) sur les faces de dessus de la
    peinture, tirets complets seulement (le premier et le dernier d'une ligne peuvent être tronqués, choix [G] du lot L2b) ;
  - séparateurs béton (coupe : base, hauteur au-dessus du sol fabriqué, continuité) et glissières (haut de lisse au-dessus
    du sol, pas des supports, face de la lisse sur la limite) ;
  - voies d'insertion et de décélération (largeur le long du biseau), points à 1,00 m et 5,00 m, obliquité ;
  - musoirs : chevrons (angle à la bissectrice, largeur, pas, espace 2u, pointe vers l'amont), aplat, sol sans trou,
    raccord vertical des bretelles, BAU interrompue au droit du musoir.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
sys.path.insert(0, str(GEN))
import regles  # noqa: E402

SCENES = ("A1_autoroute_2x2_GBA", "A2_autoroute_2x3_glissieres", "A3_bretelle_entree", "A4_bretelle_sortie")
MODS = {m: (float(regles.valeur(f"RF-MQ-MOD-{m}")["trait"]), float(regles.valeur(f"RF-MQ-MOD-{m}")["intervalle"]))
        for m in ("T1", "T'1", "T2", "T3", "T'3", "T4")}


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def largeur_min(xy):
    """Largeur minimale d'un nuage de points (pieds à coulisse tournants sur l'enveloppe convexe) : (largeur, direction
    unitaire du côté porteur, longueur le long de ce côté)."""
    from scipy.spatial import ConvexHull
    if len(xy) < 3:
        return None
    try:
        h = ConvexHull(xy)
    except Exception:  # noqa: BLE001
        return None
    H = xy[h.vertices]
    best = None
    for i in range(len(H)):
        d = H[(i + 1) % len(H)] - H[i]
        L = np.linalg.norm(d)
        if L < 1e-9:
            continue
        d /= L
        n = np.array([-d[1], d[0]])
        w = (H @ n).max() - (H @ n).min()
        lon = (H @ d).max() - (H @ d).min()
        if best is None or w < best[0]:
            best = (float(w), d, float(lon), n)
    return best


def largeur_ligne(s, t, bornes):
    """Largeur d'un tiret dans le repère (s, t) de sa route : ajustement t = a + b·s par morceau (bornes des sections : un
    biseau change de pente à une borne), largeur = étendue des résidus × cos(atan b), maximum des morceaux."""
    out = []
    cuts = [-1e9] + [b for b in bornes if s.min() < b < s.max()] + [1e9]
    for a_, b_ in zip(cuts[:-1], cuts[1:]):
        sel = (s >= a_ - 1e-6) & (s <= b_ + 1e-6)
        if sel.sum() < 4 or s[sel].max() - s[sel].min() < 0.3:
            continue
        A = np.c_[np.ones(sel.sum()), s[sel]]
        coef, *_ = np.linalg.lstsq(A, t[sel], rcond=None)
        res = t[sel] - A @ coef
        out.append((res.max() - res.min()) * math.cos(math.atan(coef[1])))
    return float(max(out)) if out else float(t.max() - t.min())


# --------------------------------------------------------------------------------------------- repères des routes
class Repere:
    """Ligne de référence échantillonnée (l1/courbes_controle.json) : (s, t) <-> (x, y)."""

    def __init__(self, r):
        ref = r["reference"]
        self.id = r["id"]
        self.S = np.array(ref["s"], dtype=float)
        self.X = np.array(ref["x"], dtype=float)
        self.Y = np.array(ref["y"], dtype=float)
        d = np.gradient(np.c_[self.X, self.Y], self.S, axis=0)
        d /= np.linalg.norm(d, axis=1)[:, None]
        self.G = np.c_[-d[:, 1], d[:, 0]]
        self.L = float(self.S[-1])
        self.sections = r["sections"]

    def xy(self, s, t):
        s = np.asarray(s, dtype=float)
        x = np.interp(s, self.S, self.X)
        y = np.interp(s, self.S, self.Y)
        gx = np.interp(s, self.S, self.G[:, 0])
        gy = np.interp(s, self.S, self.G[:, 1])
        n = np.hypot(gx, gy)
        return x + t * gx / n, y + t * gy / n

    def st(self, x, y):
        """Projection de points (tableaux) sur la polyligne (segments les plus proches)."""
        P = np.c_[x, y]
        A = np.c_[self.X[:-1], self.Y[:-1]]
        B = np.c_[self.X[1:], self.Y[1:]]
        out_s = np.empty(len(P))
        out_t = np.empty(len(P))
        D = B - A
        L2 = (D ** 2).sum(1)
        for k0 in range(0, len(P), 4096):
            Q = P[k0:k0 + 4096]
            u = ((Q[:, None, :] - A[None]) * D[None]).sum(2) / L2[None]
            u = np.clip(u, 0, 1)
            F = A[None] + u[..., None] * D[None]
            dd = ((Q[:, None, :] - F) ** 2).sum(2)
            i = dd.argmin(1)
            ui = u[np.arange(len(Q)), i]
            Fi = F[np.arange(len(Q)), i]
            out_s[k0:k0 + 4096] = self.S[i] + ui * (self.S[i + 1] - self.S[i])
            n = np.c_[-D[i, 1], D[i, 0]] / np.sqrt(L2[i])[:, None]
            out_t[k0:k0 + 4096] = ((Q - Fi) * n).sum(1)
        return out_s, out_t

    def limite_t(self, s, cle=None, indice=None, sec=None):
        for se in self.sections:
            if (sec is None and se["s0"] - 1e-9 <= s <= se["s1"] + 1e-9) or (sec is not None and se["indice"] == sec):
                for li in se["limites"]:
                    if (cle is not None and li["cle"] == cle) or (indice is not None and li["indice"] == indice):
                        return float(np.interp(s, se["s"], li["t"]))
        return None


def charger(d):
    cc = json.loads((d / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
    rep = {r["id"]: Repere(r) for r in cc["routes"]}
    m = json.loads((DEPOT / cc["modele"]["fichier"]).read_text(encoding="utf-8")) if not Path(cc["modele"]["fichier"]).is_absolute() \
        else json.loads(Path(cc["modele"]["fichier"]).read_text(encoding="utf-8"))
    return cc, rep, m


def sol(d):
    P = np.load(d / "l2" / "sol_points.npy")
    F = np.load(d / "l2" / "sol_faces.npy")
    C = np.load(d / "l2" / "sol_comptes.npy")
    A = np.load(d / "l2" / "sol_attributs.npy")
    voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    return P, F, C, A, voc


def route_des_points(P, reps):
    """Route de chaque sommet du sol : celle dont le repère redonne (x, y) depuis (s, t) à 5 mm près."""
    out = np.full(len(P), "", dtype=object)
    for rid, r in reps.items():
        x, y = r.xy(P[:, 3], P[:, 4])
        ok = (np.hypot(x - P[:, 0], y - P[:, 1]) < 0.005) & (P[:, 3] >= -1e-6) & (P[:, 3] <= r.L + 1e-6) & (out == "")
        out[ok] = rid
    return out


# --------------------------------------------------------------------------------------------- 1. largeurs des bandes
def largeurs(d, reps, m):
    P, F, C, A, voc = sol(d)
    rpt = route_des_points(P, reps)
    cols = voc["colonnes"]
    ib = cols.index("bande_id")
    off = np.r_[0, np.cumsum(C)[:-1]]
    face_route = rpt[F[off]]
    bandes_mod = {}
    for r in m["routes"]:
        for sec in r["sections"]:
            p = next(x for x in m["profils"] if x["id"] == sec["profil"])
            for b in p["bandes"]:
                if isinstance(b["largeur"], (int, float)):
                    bandes_mod.setdefault((r["id"], b["id"]), []).append((float(sec["s0"]), float(sec["s1"]), float(b["largeur"])))
    res = []
    for (rid, bid), secs in sorted(bandes_mod.items()):
        if bid not in voc["bande_id"]:
            continue
        k = voc["bande_id"].index(bid)
        fsel = np.where((A[:, ib] == k) & (face_route == rid))[0]
        if not len(fsel):
            continue
        idx = np.unique(np.concatenate([F[off[f]:off[f] + C[f]] for f in fsel]))
        s, t = P[idx, 3], P[idx, 4]
        ecarts = []
        r = reps[rid]
        for s0, s1, w in secs:
            se = next((x for x in r.sections if abs(x["s0"] - s0) < 1e-6), None)
            if se is None:
                continue
            lg = next((li for li in se["limites"] if li["cle"].endswith("|" + bid)), None)
            ld = next((li for li in se["limites"] if li["cle"].startswith(bid + "|")), None)
            if lg is None or ld is None:
                continue
            for sk in np.arange(np.ceil(s0) + 2.0, s1 - 1.0, 25.0):
                # sommets à ± 0,6 m (pas d'échantillonnage ≤ 1 m) posés sur chacune des deux limites (à 5 cm près de la
                # limite de la courbe de contrôle L1 à leur abscisse) : écart de position de chaque bord, largeur mesurée
                sel = np.abs(s - sk) < 0.6
                if sel.sum() < 2:
                    continue
                ss, tt = s[sel], t[sel]
                tg = np.interp(ss, se["s"], lg["t"])
                td = np.interp(ss, se["s"], ld["t"])
                eg, ed = tt - tg, tt - td
                mg, md = np.abs(eg) < 0.05, np.abs(ed) < 0.05
                if not mg.any() or not md.any():
                    continue
                # écart = max(bords fabriqués / limites L1, largeur L1 à sk / largeur du modèle)
                w_l1 = float(np.interp(sk, se["s"], lg["t"]) - np.interp(sk, se["s"], ld["t"]))
                ecarts.append(max(float(np.max(np.abs(eg[mg]))), float(np.max(np.abs(ed[md]))), abs(w_l1 - w)))
        if ecarts:
            res.append({"route": rid, "bande": bid, "largeurs_modele_m": sorted({w for _, _, w in secs}),
                        "coupes": len(ecarts), "ecart_max_m": _r(max(ecarts), 5)})
    return res


# --------------------------------------------------------------------------------------------- 2. lignes
def peinture(d):
    P = np.load(d / "l2b" / "peinture_points.npy")
    F = np.load(d / "l2b" / "peinture_faces.npy")
    C = np.load(d / "l2b" / "peinture_comptes.npy")
    A = np.load(d / "l2b" / "peinture_attributs.npy")
    voc = json.loads((d / "l2b" / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
    return P, F, C, A, voc


def entites_dessus(d):
    """{pj_entite: tableau (x, y) des sommets des faces de dessus}."""
    P, F, C, A, voc = peinture(d)
    off = np.r_[0, np.cumsum(C)[:-1]]
    ie, idd = voc["colonnes"].index("pj_entite"), voc["colonnes"].index("dessus")
    dessus = A[:, idd] == 1
    out = {}
    ents = A[:, ie]
    for k in np.unique(ents[dessus]):
        fsel = np.where(dessus & (ents == k))[0]
        idx = np.unique(np.concatenate([F[off[f]:off[f] + C[f]] for f in fsel]))
        out[voc["pj_entite"][k]] = P[idx, :2]
    return out


def lignes(d, reps, m, ent):
    """Tirets des lignes longitudinales (entités ML_<route>_<cle>_<mod>_<k>_t<nnn>)."""
    u_lim = {}
    for p in m["profils"]:
        for li in p["limites"]:
            for mq in li.get("marquages") or []:
                u_lim.setdefault(mq["modulation"], set()).add(round(float(mq["largeur_u"]) * float(mq.get("u_m", 0.075)), 4))
    table = json.loads((d / "l2b" / "table_marques.json").read_text(encoding="utf-8"))["marques"]
    mod_de = {x["id"]: x.get("modulation", "") for x in table}
    groupes = {}
    for e, xy in ent.items():
        mm = re.match(r"ML_(R_\d+)_(.+)_t(\d+)$", e)
        if not mm or e not in mod_de:
            continue
        rid = mm.group(1).replace("_", "-")
        groupes.setdefault((rid, mm.group(2), mod_de[e], ""), []).append((int(mm.group(3)), xy))
    res = []
    for (rid, cle, mod, k), tirets in sorted(groupes.items()):
        r = reps.get(rid)
        if r is None:
            continue
        tirets.sort()
        ext = []
        bornes = sorted({float(se["s0"]) for se in r.sections} | {float(se["s1"]) for se in r.sections})
        from scipy.spatial import ConvexHull
        aires = []
        for _, xy in tirets:
            s, t = r.st(xy[:, 0], xy[:, 1])
            # largeur : la plus petite de trois étendues qui majorent toutes la largeur vraie (étendue en t : tiret en
            # courbe ; résidus d'un ajustement par morceau : tiret coudé ; pieds à coulisse : tiret droit oblique)
            lm = largeur_min(xy)
            ext.append((s.min(), s.max(), min(largeur_ligne(s, t, bornes), float(t.max() - t.min()),
                                              lm[0] if lm else 1e9)))
            try:
                aires.append(ConvexHull(xy).volume)
            except Exception:  # noqa: BLE001
                aires.append(0.0)
        # seulement en alignement droit (courbure nulle) pour la longueur des traits
        traits, vides, larg = [], [], []
        tr_regle = MODS.get(mod, (None, None))[0]
        w_med = float(np.median([w for _, _, w in ext]))
        rognes = 0
        for i, (a, b, w) in enumerate(ext):
            bout = len(ext) >= 3 and (i == 0 or i == len(ext) - 1)      # bouts : troncature, convergence (2u)
            # tiret rogné par le dégagement de 2u entre deux lignes qui convergent (biseau, choix [G] du lot L2b) :
            # aire < 97 % de longueur × largeur médiane
            rogne = aires[i] < 0.97 * (b - a) * w_med
            rognes += 1 if (rogne and not bout) else 0
            if not bout and not rogne:
                larg.append(w)
            if 0 < i < len(ext) - 1:
                traits.append(b - a)
            if i > 0:
                vides.append(a - ext[i - 1][1])
        res.append({"route": rid, "cle": cle, "modulation": mod, "tirets": len(ext),
                    "trait_m": [_r(min(traits)), _r(max(traits))] if traits else None,
                    "intervalle_m": [_r(min(vides)), _r(max(vides))] if vides else None,
                    "largeur_m": [_r(min(larg)), _r(max(larg))] if larg else None, "tirets_rognes_convergence": rognes,
                    "trait_regle": MODS.get(mod, (None, None))[0], "intervalle_regle": MODS.get(mod, (None, None))[1]})
    return res


# --------------------------------------------------------------------------------------------- 3. équipements
def equipements(d, reps, m):
    f = d / "autoroute" / "equipements.json"
    if not f.exists():
        return None
    e = json.loads(f.read_text(encoding="utf-8"))
    P = np.array(e["points"], dtype=float)
    cls = np.array(e["classes_points"], dtype=object)
    Ps, Fs, Cs, As, vocs = sol(d)
    out = {"separateurs": e["separateurs"], "faces_par_classe": e["faces_par_classe"]}
    # sol fabriqué : Z du sommet le plus proche (grille des sommets)
    from scipy.spatial import cKDTree
    kd = cKDTree(Ps[:, :2])

    def z_sol(x, y):
        dd, i = kd.query(np.c_[x, y], k=3)
        return Ps[i, 2].mean(1)
    r0 = reps[m["routes"][0]["id"]]
    beton = cls == "separateur_beton"
    if beton.any():
        Pb = P[beton]
        s, t = r0.st(Pb[:, 0], Pb[:, 1])
        coupes = []
        for sk in np.arange(10.0, r0.L - 10.0, 50.0):
            sel = np.abs(Pb[:, 3] - sk) < 1e-3
            if sel.sum() < 6:
                continue
            tt, zz = t[sel], Pb[sel, 2]
            zs = float(z_sol([np.mean(Pb[sel, 0])], [np.mean(Pb[sel, 1])])[0])
            coupes.append({"s": _r(sk, 2), "base_m": _r(tt.max() - tt.min()), "haut_sur_sol_m": _r(zz.max() - zs),
                           "axe_t_m": _r(0.5 * (tt.max() + tt.min()))})
        # continuité : abscisses couvertes par les anneaux du béton
        ss = np.unique(np.round(Pb[:, 3], 3))
        trous = float(np.max(np.diff(ss))) if len(ss) > 1 else None
        out["beton"] = {"coupes": coupes, "s_min": _r(ss.min(), 3), "s_max": _r(ss.max(), 3), "pas_max_m": _r(trous, 3),
                        "longueur_route_m": _r(r0.L, 3)}
    lis = cls == "glissiere_lisse"
    if lis.any():
        Pl = P[lis]
        s, t = r0.st(Pl[:, 0], Pl[:, 1])
        res = []
        for side in (1, -1):
            sel_side = (t * side) > 0
            if not sel_side.any():
                continue
            hauts = []
            for sk in np.arange(10.0, r0.L - 10.0, 50.0):
                sel = sel_side & (np.abs(Pl[:, 3] - sk) < 1e-3)
                if sel.sum() < 4:
                    continue
                zs = float(z_sol([np.mean(Pl[sel, 0])], [np.mean(Pl[sel, 1])])[0])
                tt = t[sel]
                face = tt.max() if side > 0 else tt.min()          # crête de la lisse côté trafic (vers la BDG)
                hauts.append((sk, Pl[sel, 2].max() - zs, face))
            # supports (pièces verticales « glissiere_piece » du même côté) : abscisses des centres
            pc = (cls == "glissiere_piece")
            Pp = P[pc]
            sp, tp = r0.st(Pp[:, 0], Pp[:, 1])
            selp = (tp * side) > 0
            zmin = Pp[selp, 2].min() if selp.any() else 0
            bas = selp & (Pp[:, 2] < zmin + 1e-3)                  # pied des supports (z = −0,30)
            centres = np.unique(np.round(sp[bas], 1))
            # regroupement des sommets d'un même support (8 sommets à moins de 0,1 m)
            grp = []
            for v in sorted(centres):
                if not grp or v - grp[-1][-1] > 0.5:
                    grp.append([v])
                else:
                    grp[-1].append(v)
            c = [float(np.mean(g)) for g in grp]
            pas = np.diff(c) if len(c) > 1 else np.array([])
            lim_t = None
            for li in r0.sections[0]["limites"]:
                if li["nature"].find("separateur") >= 0 and np.sign(np.mean(li["t"])) == np.sign(side):
                    lim_t = float(np.mean(li["t"]))
            res.append({"cote": "gauche" if side > 0 else "droite",
                        "haut_lisse_sur_sol_m": [_r(min(h for _, h, _ in hauts)), _r(max(h for _, h, _ in hauts))],
                        "face_t_m": [_r(min(f for _, _, f in hauts)), _r(max(f for _, _, f in hauts))],
                        "limite_t_m": _r(lim_t), "supports": len(c),
                        "pas_supports_m": [_r(pas.min()), _r(pas.max())] if len(pas) else None})
        out["glissieres"] = res
    return out


# --------------------------------------------------------------------------------------------- 4. bretelles et musoirs
def bretelles(d, reps, m, ent):
    f = d / "autoroute" / "musoirs.json"
    if not f.exists() or not m.get("carrefours"):
        return None
    mu = json.loads(f.read_text(encoding="utf-8"))
    c = m["carrefours"][0]
    rp = reps[c["branches"][0]["route"]]
    rb = reps[c["branches"][1]["route"]]
    genre = mu["musoirs"]["genres"][0]
    sJ = mu["musoirs"]["sJ"][0]
    out = {"genre": genre, "s_jonction": _r(sJ, 3)}
    # voie auxiliaire : largeur fabriquée le long de la principale (sol : bande ins1 / dec1)
    aux = "ins1" if genre == "entree" else "dec1"
    P, F, C, A, voc = sol(d)
    rpt = route_des_points(P, reps)
    off = np.r_[0, np.cumsum(C)[:-1]]
    ib = voc["colonnes"].index("bande_id")
    k = voc["bande_id"].index(aux)
    fsel = np.where((A[:, ib] == k) & (rpt[F[off]] == rp.id))[0]
    idx = np.unique(np.concatenate([F[off[f]:off[f] + C[f]] for f in fsel]))
    s, t = P[idx, 3], P[idx, 4]
    prof = []
    for sk in np.arange(np.ceil(s.min()), np.floor(s.max()) + 1.0, 1.0):
        sel = np.abs(s - sk) < 1e-3
        if sel.sum() >= 2:
            prof.append((float(sk), float(t[sel].max() - t[sel].min())))
    prof = np.array(prof)
    out["voie_auxiliaire"] = {"bande": aux, "s0": _r(prof[0, 0], 3), "s1": _r(prof[-1, 0], 3)}
    # loi attendue (modèle) : sections de la principale où la bande existe
    loi = []
    for sec in m["routes"][[r["id"] for r in m["routes"]].index(rp.id)]["sections"]:
        p = next(x for x in m["profils"] if x["id"] == sec["profil"])
        for b in p["bandes"]:
            if b["id"] == aux:
                loi.append((sec["s0"], sec["s1"], b["largeur"]))

    def w_attendu(s):
        for s0, s1, w in loi:
            if s0 - 1e-6 <= s <= s1 + 1e-6:
                if isinstance(w, (int, float)):
                    return float(w)
                pts = w["points"]
                return float(np.interp(s, [q[0] for q in pts], [q[1] for q in pts]))
        return None
    e = [abs(w - w_attendu(s)) for s, w in prof if w_attendu(s) is not None]
    out["voie_auxiliaire"]["ecart_largeur_max_m"] = _r(max(e), 5)
    biseau = [(s0, s1) for s0, s1, w in loi if not isinstance(w, (int, float))]
    out["voie_auxiliaire"]["biseau"] = [list(x) for x in biseau]
    # largeur mesurée aux bouts du biseau
    if biseau:
        s0, s1 = biseau[0]
        w0 = float(np.interp(s0 + 0.0, prof[:, 0], prof[:, 1]))
        w1 = float(np.interp(s1, prof[:, 0], prof[:, 1]))
        out["voie_auxiliaire"]["biseau_mesure"] = {"s0": s0, "s1": s1, "longueur_m": _r(s1 - s0, 3),
                                                   "largeur_s0_m": _r(w0), "largeur_s1_m": _r(w1)}
    # écart entre les bords des chaussées (rive de la principale, rive gauche de la bretelle) : points à 1 m et 5 m
    Lb = rb.L
    sb = np.linspace(0, Lb, int(Lb * 4) + 1)
    tb_lane = None
    for li in rb.sections[0]["limites"]:
        if li["indice"] == 0:
            tb_lane = li
    xb, yb = rb.xy(sb, np.interp(sb, rb.sections[0]["s"], tb_lane["t"]))
    spb, tpb = rp.st(xb, yb)
    gaps = []
    for k_, (sp_, tp_) in enumerate(zip(spb, tpb)):
        # bord droit des voies de la principale (hors voie auxiliaire) à sp
        tr = None
        for se in rp.sections:
            if se["s0"] - 1e-9 <= sp_ <= se["s1"] + 1e-9:
                for li in se["limites"]:
                    if re.match(r"^v\d+\|", li["cle"]):
                        cand = float(np.interp(sp_, se["s"], li["t"]))
                        tr = cand if tr is None or cand < tr else tr
        if tr is not None:
            gaps.append((sb[k_], sp_, tr - tp_))
    g = np.array(gaps)
    dist = np.abs(g[:, 0] - (Lb if genre == "entree" else 0.0))
    o = np.argsort(dist)
    dd, gg = dist[o], g[o, 2]

    def premier(v):
        i = np.where(gg >= v)[0]
        if not len(i):
            return None
        i = i[0]
        return float(np.interp(v, [gg[i - 1], gg[i]], [dd[i - 1], dd[i]])) if i > 0 else float(dd[i])
    p1, p5 = premier(1.0), premier(5.0)
    out["point_1m_depuis_jonction_m"] = _r(p1, 3)
    out["point_5m_depuis_jonction_m"] = _r(p5, 3)
    out["obliquite"] = _r(4.0 / (p5 - p1), 5) if p1 and p5 else None
    # BAU interrompue : sections de la principale sans BAU (bau2) près de la jonction ; aucun sommet de BAU dedans
    kb = voc["bande_id"].index("bau2") if "bau2" in voc["bande_id"] else -1
    rmod = m["routes"][[r_["id"] for r_ in m["routes"]].index(rp.id)]
    sans = []
    for sec in rmod["sections"]:
        p_ = next(x for x in m["profils"] if x["id"] == sec["profil"])
        if not any(b_["type"] == "bande_arret_urgence" and b_["sens"] == "avant" for b_ in p_["bandes"]):
            sans.append((sec["s0"], sec["s1"]))
    if kb >= 0 and sans:
        fb = np.where((A[:, ib] == kb) & (rpt[F[off]] == rp.id))[0]
        idxb = np.unique(np.concatenate([F[off[f]:off[f] + C[f]] for f in fb]))
        sbau = P[idxb, 3]
        dedans = sum(int(((sbau > a_ + 0.01) & (sbau < b_ - 0.01)).sum()) for a_, b_ in sans)
        out["bau_interrompue"] = {"intervalles_s": [list(x) for x in sans], "sommets_de_bau_dedans": dedans}
    # raccord vertical : Z des deux sols à 0,50 m de part et d'autre de la jonction (voie de la bretelle)
    from scipy.spatial import cKDTree
    selB = rpt == rb.id
    selP = rpt == rp.id
    kB, kP = cKDTree(P[selB, :2]), cKDTree(P[selP, :2])
    zB_, zP_ = P[selB, 2], P[selP, 2]
    sbJ = Lb if genre == "entree" else 0.0
    ecz = []
    for dt in (-1.5, 0.0, 1.5):
        xB, yB = rb.xy(sbJ - (0.3 if genre == "entree" else -0.3), 1.5 + dt)
        xP, yP = rb.xy(sbJ + (0.3 if genre == "entree" else -0.3), 1.5 + dt)
        dB, iB = kB.query([xB, yB], k=3)
        dP, iP = kP.query([xP, yP], k=3)
        ecz.append(abs(float(zB_[iB].mean()) - float(zP_[iP].mean())))
    out["raccord_vertical"] = {"dz_applique_m": mu["raccord_bretelles"]["ra_dz"],
                               "ecart_z_jonction_max_m": _r(max(ecz), 4)}
    # sol du musoir : aire et écart de Z aux bords
    gore = mu["sol"]
    aire = sum(abs(0.5 * sum(p[0] * q[1] - q[0] * p[1] for p, q in zip(g_["P"], g_["P"][1:] + g_["P"][:1]))) for g_ in gore)
    kAll = cKDTree(P[(selB | selP), :2])
    zAll = P[(selB | selP), 2]
    pas_z = []
    for g_ in gore:
        for (x, y, z) in g_["P"]:
            dd_, ii = kAll.query([x, y], k=1)
            if dd_ < 0.05:
                pas_z.append(abs(z - zAll[ii]))
    out["sol_musoir"] = {"faces": len(gore), "aire_m2": _r(aire, 2),
                         "aire_peinte_m2": _r(sum(1 for g_ in gore if g_["classe"] == "musoir"), 0),
                         "marche_z_bords_max_m": _r(max(pas_z) if pas_z else None, 4), "sommets_bords": len(pas_z)}
    # chevrons mesurés sur la peinture fabriquée
    out["chevrons"] = chevrons(ent, mu, rp, rb, genre)
    out["musoir_modele"] = mu["musoirs"]
    return out


def chevrons(ent, mu, rp, rb, genre):
    ch = {e: xy for e, xy in ent.items() if "_chevron_" in e}
    if not ch:
        return None
    # bissectrice : directions des deux lignes de contour (rive de la principale = son axe ; rive de la bretelle =
    # sa tangente au point à 5 m) : moyenne des deux directions
    sJ, s5 = mu["musoirs"]["sJ"][0], mu["musoirs"]["s5"][0]
    i = np.searchsorted(rp.S, 0.5 * (sJ + s5))
    dP = np.array([rp.X[i + 1] - rp.X[i], rp.Y[i + 1] - rp.Y[i]])
    dP /= np.linalg.norm(dP)
    # direction de la bretelle près du musoir (corde de 20 m)
    sbm = rb.L - 60 if genre == "entree" else 60.0
    x0, y0 = rb.xy(sbm - 10, 0.0)
    x1, y1 = rb.xy(sbm + 10, 0.0)
    dB = np.array([x1 - x0, y1 - y0])
    dB /= np.linalg.norm(dB)
    bis = (dP + dB) / np.linalg.norm(dP + dB)
    angles, largs, bandes = [], [], {}
    for e, xy in ch.items():
        lm = largeur_min(xy)
        if lm is None:
            continue
        w, d, lon, n = lm
        if lon < 2.2:
            continue      # bande coupée court par les deux bords de la zone (pointe) : côté porteur ambigu (< 2 × 1,118 m)
        a = math.degrees(math.acos(min(1.0, abs(float(d @ bis)))))
        angles.append(a)
        largs.append(w)
        fam = "h" if "_chevron_h" in e else "b"
        bandes.setdefault(fam, []).append((0.5 * float((xy @ n).max() + (xy @ n).min()), n, e, float(lon)))
    pas = []
    for fam, L in bandes.items():
        n0 = L[0][1]
        proj = sorted(0.5 * float((ch[e] @ n0).max() + (ch[e] @ n0).min()) for _, _, e, lon in L)
        dp = np.diff(proj)
        pas += [x for x in dp if 0.5 < x < 3.0]
    # pointe vers l'amont (RF-MQ-HACH-02 : pointe dirigée vers le conducteur) : dans le repère de la principale (circulation
    # dans le sens des s croissants, bretelle à droite), le bout de chaque bande sur la bissectrice (t minimal pour la
    # demi-zone haute « h », maximal pour la basse « b ») est à une abscisse plus petite que son bout extérieur
    amont, total = 0, 0
    for fam, L in bandes.items():
        for _, n, e, lon in L:
            xy = ch[e]
            w, d, lon2, n2 = largeur_min(xy)
            c = xy.mean(0)
            i = int(np.clip(np.searchsorted(rp.S, rp.st(np.array([c[0]]), np.array([c[1]]))[0][0]), 1, len(rp.S) - 1))
            T = np.array([rp.X[i] - rp.X[i - 1], rp.Y[i] - rp.Y[i - 1]])
            T /= np.linalg.norm(T)
            N = np.array([-T[1], T[0]])
            ds, dt = float(d @ T), float(d @ N)
            # orientée vers l'extérieur de la zone : demi-zone haute « h » vers la principale (t croissant), basse « b »
            # vers la bretelle (t décroissant) ; pointe vers le conducteur (amont) <=> la bande descend vers l'aval
            if (fam == "h" and dt < 0) or (fam == "b" and dt > 0):
                ds, dt = -ds, -dt
            total += 1
            amont += 1 if ds > 0 else 0
    return {"bandes": len(angles), "angle_bissectrice_deg": [_r(min(angles), 3), _r(max(angles), 3)],
            "largeur_m": [_r(min(largs), 4), _r(max(largs), 4)],
            "pas_perpendiculaire_m": [_r(min(pas), 4), _r(max(pas), 4)] if pas else None,
            "bissectrice_deg": _r(math.degrees(math.atan2(bis[1], bis[0])), 3),
            "pointe_vers_amont": [amont, total]}


# --------------------------------------------------------------------------------------------- scène
def controler(d):
    d = Path(d)
    cc, reps, m = charger(d)
    ent = entites_dessus(d)
    out = {"scene": d.name}
    out["largeurs"] = largeurs(d, reps, m)
    out["lignes"] = lignes(d, reps, m, ent)
    out["equipements"] = equipements(d, reps, m)
    out["bretelle"] = bretelles(d, reps, m, ent)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--json")
    a = ap.parse_args()
    scenes = a.scenes or [str(DEPOT / "recon" / "out" / "generateur" / s) for s in SCENES]
    res = [controler(s) for s in scenes]
    txt = json.dumps(res, ensure_ascii=False, indent=1)
    if a.json:
        Path(a.json).write_text(txt + "\n", encoding="utf-8")
    print(txt[:20000])


if __name__ == "__main__":
    main()
