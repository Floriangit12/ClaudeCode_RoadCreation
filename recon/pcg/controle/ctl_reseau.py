"""Contrôles du réseau et du carrefour (VAL-XOD-008, VAL-JCT-010, VAL-COV-006, largeurs GA-CHA-005 / MQ-LAR-*,
rayons GA-RAY-*, visibilité MQ-LEF-010 / MQ-PP-013, passages MQ-PP-001 / 002, quais GA-QBU-*, îlots GA-ILO-*,
pistes MQ-CYC-013 / GA-CYC-005, gabarit GA-CHA-006) sur le .xodr (paquet_jardin_2026.xodr, lanes_2026.geojson,
manoeuvres_2026.json), la description et la fabrication.
"""
import collections
import math

import numpy as np

import ctl_commun as K
from ctl_commun import regle, r4, stats
import ctl_marquages as M
import ctl_sol as S

BRANCHES = {"verdun_sw": ("1", "2"), "verdun_ne": ("3", "4"), "reviree": ("5",), "vercors": ("6",)}
ROUTE_BRANCHE = {"1": "verdun_sw", "2": "verdun_sw", "3": "verdun_ne", "4": "verdun_ne", "5": "reviree",
                 "6": "vercors"}


# =========================================================================== outils
def largeurs_voies(ctx, pas=1.0):
    """[(route, section_s, voie, type, s (n,), largeur (n,), cote)] des voies hors jonction."""
    def f():
        out = []
        for rid in sorted(ctx.reseau, key=int):
            r = ctx.reseau[rid]
            if r.jonction != "-1":
                continue
            for sec in r.sections:
                s = np.linspace(sec.s, sec.s1, max(2, int((sec.s1 - sec.s) / pas) + 1))
                tb = r.t_bords(s, sec)
                for v, voie in sorted(sec.voies.items()):
                    if v == 0:
                        continue
                    vi = v - 1 if v > 0 else v + 1
                    out.append((rid, sec.s, v, voie.type, s, np.abs(tb[v] - tb[vi]), 1 if v > 0 else -1))
        return out
    return ctx._m(f"res:larg:{pas}", f)


def centre_voie(ctx, rid, sec_s, v, s):
    r = ctx.reseau[rid]
    sec = next(x for x in r.sections if abs(x.s - sec_s) < 1e-6)
    tb = r.t_bords(np.asarray(s, float), sec)
    vi = v - 1 if v > 0 else v + 1
    t = 0.5 * (tb[v] + tb[vi])
    x, y, h = K.X.point_st(r, np.asarray(s, float), t)
    return np.c_[x, y], h, t


def groupes_r12(ctx):
    """Têtes R12 du .xodr regroupées par mât (≤ 1 m) : [(xy moyen, [ids])]."""
    def f():
        pts = [(s["id"], s["xy"]) for s in ctx.signaux if s["type"] == "1000002"]
        if not pts:
            return []
        Q = np.array([p[1] for p in pts])
        lab = K.grappes(Q, 1.0)
        out = []
        for k in range(lab.max() + 1):
            m = lab == k
            out.append((Q[m].mean(0), [pts[i][0] for i in np.nonzero(m)[0]]))
        out.sort(key=lambda t: (round(float(t[0][0]), 2), round(float(t[0][1]), 2)))
        return out
    return ctx._m("res:r12", f)


def quais(ctx):
    return [(bid, b) for bid, b in sorted(ctx.bordures.items())
            if any(it["profil"] == "QUAI_BUS" for it in b["p"]["intervalles"])]


def abris(ctx):
    out = []
    for f in sorted(ctx.mobilier, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if p["type"] != "abri_bus" or p.get("x_local") is None:
            continue
        poly = None
        w = p.get("emprise_osm")
        if w and w.startswith("POLYGON"):
            xy = [tuple(map(float, c.split())) for c in w[w.index("((") + 2:w.index("))")].split(",")]
            poly = K.C.repere(np.array(xy))
        if poly is None:
            c = np.array([p["x_local"], p["y_local"]])
            a = math.radians(90 - float(p.get("azimut_deg") or 0))
            u = np.array([math.cos(a), math.sin(a)])
            v = np.array([-u[1], u[0]])
            L, l = float(p.get("longueur_m") or 4), float(p.get("largeur_m") or 1.5)
            poly = np.array([c - u * L / 2 - v * l / 2, c + u * L / 2 - v * l / 2, c + u * L / 2 + v * l / 2,
                             c - u * L / 2 + v * l / 2])
        out.append((p["id"], poly, p))
    return out


def ilot_largeur_axe(poly, A, B):
    """Longueur de la ligne (A, B) prolongée de 6 m à l'intérieur du polygone (largeur selon l'axe du passage)."""
    ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
    t = np.arange(-6.0, np.linalg.norm(B - A) + 6.0, 0.02)
    Q = A + t[:, None] * ax
    return float(K.dans(Q, poly).sum() * 0.02)


# =========================================================================== largeurs
@regle("GA-CHA-005", "description", "mineur",
       "Largeurs des files de circulation générale (voies driving du .xodr hors jonction, échantillons tous les 1 m, 5 m "
       "extrêmes de chaque section exclus) : Verdun (deux voies de même sens) 2,50-3,25 m ; Revirée (double sens) "
       "2,75-3,25 m ; Vercors (sens unique par file) 2,50-3,25 m ; 30 derniers mètres avant la jonction (stockage aux "
       "feux) 2,60-3,00 m. Conforme si la médiane est dans la plage et moins de 20 % des échantillons hors plage "
       "(±0,05). Unité : voie (section).", "implemente")
def ga_cha_005(ctx, R):
    for rid, sec_s, v, typ, s, w, cote in largeurs_voies(ctx):
        if typ != "driving":
            continue
        r = ctx.reseau[rid]
        sec = next(x for x in r.sections if abs(x.s - sec_s) < 1e-6)
        m = (s >= sec.s + 5) & (s <= sec.s1 - 5)
        if m.sum() < 3:
            continue
        lo, hi = (2.75, 3.25) if rid == "5" else (2.5, 3.25)
        # stockage : 30 m avant la jonction dans le sens de circulation (fin de route à droite, début à gauche)
        jn_fin = rid in ("1", "3") or (rid == "5" and cote > 0) or (rid == "6" and cote > 0)
        stock = (s >= r.longueur - 30) if (jn_fin and cote < 0) else (s <= 30) if (jn_fin and cote > 0) else np.zeros(len(s), bool)
        for nom, sel, (a, b) in (("section", m & ~stock, (lo, hi)), ("stockage", m & stock, (2.6, 3.0))):
            if sel.sum() < 3:
                continue
            ww = w[sel]
            med = float(np.median(ww))
            hors = float(((ww < a - 0.05) | (ww > b + 0.05)).mean())
            ok = a - 1e-6 <= med <= b + 1e-6 and hors <= 0.2
            xy, _, _ = centre_voie(ctx, rid, sec_s, v, [float(np.median(s[sel]))])
            R.tester(ok, entite=f"route {rid} s{sec_s:g} voie {v} ({nom})", xy=xy[0], valeur=r4(med, 2),
                     seuil=f"{a:.2f}-{b:.2f} m", detail=f"largeur médiane {med:.2f} m (min {ww.min():.2f}, max "
                     f"{ww.max():.2f}), {hors * 100:.0f} % hors plage", ecart=max(a / max(med, 0.1), med / b, hors / 0.2))


@regle("MQ-LAR-002", "description", "mineur",
       "Couloirs bus 3,00-3,50 m (aucune voie bus au .xodr) ; voie générale parcourue par des bus ≥ 3,25 m : voie "
       "driving la plus à droite des routes desservies (Verdun 1-4, Vercors 6, Revirée 5 : arrêts C6), médiane "
       "hors jonction. Unité : voie de droite d'une route desservie.", "implemente")
def mq_lar_002(ctx, R):
    vus = {}
    for rid, sec_s, v, typ, s, w, cote in largeurs_voies(ctx):
        if typ == "bus":
            med = float(np.median(w))
            R.tester(3.0 <= med <= 3.5, entite=f"route {rid} voie {v} (bus)", valeur=r4(med, 2), seuil="3,00-3,50 m")
        if typ != "driving":
            continue
        cle = (rid, sec_s, cote)
        if cle not in vus or abs(v) > abs(vus[cle][0]):
            vus[cle] = (v, s, w)
    for (rid, sec_s, cote), (v, s, w) in sorted(vus.items()):
        med = float(np.median(w))
        xy, _, _ = centre_voie(ctx, rid, sec_s, v, [float(np.median(s))])
        R.tester(med >= 3.25 - 1e-6, entite=f"route {rid} s{sec_s:g} voie {v}", xy=xy[0], valeur=r4(med, 2),
                 seuil="≥ 3,25 m (voie parcourue par des bus)", detail=f"voie de droite de {med:.2f} m",
                 ecart=3.25 / max(med, 0.1))


@regle("MQ-LAR-003", "description", "mineur",
       "Largeurs cyclables (voies biking du .xodr) : piste bidirectionnelle (Chronovélo de Verdun, routes 1-4) ≥ 3,00 m, "
       "piste unidirectionnelle (Vercors, route 6) ≥ 2,00 m ; médiane hors 3 m extrêmes. Unité : voie biking.",
       "implemente")
def mq_lar_003(ctx, R):
    for rid, sec_s, v, typ, s, w, cote in largeurs_voies(ctx):
        if typ != "biking":
            continue
        lim = 3.0 if rid in ("1", "2", "3", "4") else 2.0
        m = (s >= s.min() + 3) & (s <= s.max() - 3)
        if m.sum() < 2:
            continue
        med = float(np.median(w[m]))
        xy, _, _ = centre_voie(ctx, rid, sec_s, v, [float(np.median(s[m]))])
        R.tester(med >= lim - 1e-6, entite=f"route {rid} s{sec_s:g} voie {v}", xy=xy[0], valeur=r4(med, 2),
                 seuil=f"≥ {lim:.2f} m", detail=f"piste de {med:.2f} m (min {w[m].min():.2f})", ecart=lim / max(med, 0.1))


@regle("GA-RAY-003", "description", "mineur",
       "Rayon des pistes cyclables (axe des voies biking du .xodr, cercle par 3 points à ±1 m, 2 m extrêmes de chaque "
       "laneSection exclus) : ≥ 5 m partout (carrefour), ≥ 22 m hors des 15 m d'extrémité de section (itinéraire Chronovélo à haut niveau de service). "
       "Unité : voie biking.", "implemente")
def ga_ray_003(ctx, R):
    for rid, sec_s, v, typ, s, w, cote in largeurs_voies(ctx, 0.25):
        if typ != "biking":
            continue
        xy, _, _ = centre_voie(ctx, rid, sec_s, v, s)
        Rr = K.C.rayon_courbure(xy, K.C.abscisses(xy), 1.0)
        utile = (s >= s.min() + 2) & (s <= s.max() - 2)          # raccords de laneSection exclus
        if utile.sum() < 3:
            continue
        rmin = float(Rr[utile].min())
        coeur = (s >= s.min() + 15) & (s <= s.max() - 15)
        rcoeur = float(Rr[coeur].min()) if coeur.any() else np.inf
        k = int(np.argmin(np.where(utile, Rr, np.inf)))
        ok = rmin >= 5.0 and rcoeur >= 22.0
        R.tester(ok, entite=f"route {rid} s{sec_s:g} voie {v}", xy=xy[k], valeur=r4(min(rmin, rcoeur), 1),
                 seuil="≥ 5 m (≥ 22 m hors extrémités)", detail=f"rayon min {rmin:.1f} m, hors extrémités {rcoeur:.1f} m",
                 ecart=max(5 / max(rmin, 0.1), 22 / max(rcoeur, 0.1)))


@regle("GA-RAY-002", "description", "mineur",
       "Giration d'un bus standard (12,10 × 2,50 m, empattement 5,9 m, porte-à-faux avant 2,7 m) sur les mouvements "
       "tournants des routes de liaison desservant Verdun et Vercors : enveloppe balayée de part et d'autre de l'axe de "
       "la voie de liaison (rayon local par 3 points à ±2 m) ; aucun nez de bordure non franchissable (vue > 0,05 m) "
       "d'un trottoir, d'un îlot ou d'un quai dans l'enveloppe. Unité : manœuvre tournante.", "partiel",
       "modèle cinématique simplifié (rayon local, pas d'intégration de la trajectoire de l'essieu arrière)")
def ga_ray_002(ctx, R):
    L_ar, L_av, w = 5.9, 5.9 + 2.7, 2.5
    nez = []
    for bid, b in sorted(ctx.bordures.items()):
        s, xy, nrm, _ = S.echantillons(ctx, bid, 0.25)
        v = S.vue_a(b["p"], s)
        m = v > 0.05
        nez += [(bid, q) for q in xy[m]]
    if not nez:
        return
    NZ = np.array([q for _, q in nez])
    for man in ctx.manoeuvres["manoeuvres"]:
        lid = str(man["route_de_liaison"]["id"])
        if not man.get("autorisee_2026") or "tout droit" in man["manoeuvre"]:
            continue
        if not ({str(man["entree"]["route"]), str(man["sortie"]["route"])} & {"1", "2", "3", "4", "6"}):
            continue
        r = ctx.reseau[lid]
        s = np.linspace(0, r.longueur, max(3, int(r.longueur / 0.25)))
        sec = r.sections[0]
        tb = r.t_bords(s, sec)
        t = 0.5 * (tb[-1] + tb[0])
        x, y, h = K.X.point_st(r, s, t)
        P = np.c_[x, y]
        Rr = K.C.rayon_courbure(P, K.C.abscisses(P), 2.0)
        k_ = np.cross(np.gradient(P, axis=0), np.gradient(np.gradient(P, axis=0), axis=0))
        ext = np.sqrt((Rr + w / 2) ** 2 + L_av ** 2) - Rr
        inn = Rr - (np.sqrt(np.maximum(Rr ** 2 - L_ar ** 2, 0.0)) - w / 2)
        ext = np.where(np.isfinite(Rr), ext, w / 2)
        inn = np.where(np.isfinite(Rr), np.minimum(inn, 6.0), w / 2)
        nrm = np.c_[-np.sin(h), np.cos(h)]
        cote_int = np.sign(k_)              # > 0 : virage à gauche, intérieur à gauche
        d, j, proj = K.C.distance_segments(NZ, P[:-1], P[1:])
        loin = d > 8.0
        sgn = np.einsum("ij,ij->i", NZ - proj, nrm[j])
        interieur = np.sign(sgn) == cote_int[j]
        lim = np.where(interieur, inn[j], ext[j])
        dedans = (~loin) & (d < lim)
        n = int(dedans.sum())
        ids = sorted({nez[i][0] for i in np.nonzero(dedans)[0]})
        k = int(np.nonzero(dedans)[0][0]) if n else 0
        R.tester(n == 0, entite=f"{man['code']} (liaison {lid})", xy=NZ[k] if n else P[len(P) // 2], valeur=n,
                 seuil="aucun nez de bordure dans l'enveloppe", detail=f"rayon min {np.nanmin(Rr):.1f} m ; "
                 f"{n} point(s) de nez balayé(s) : {ids[:5]}", ecart=1 + n / 20)


# =========================================================================== passages et feux
@regle("MQ-PP-001", "description", "majeur",
       "Chaque branche du carrefour à feux (Verdun SW, Verdun NE, Revirée, Vercors) porte au moins une traversée "
       "piétonne marquée (zébra fabriqué de la branche). Unité : branche.", "implemente")
def mq_pp_001(ctx, R):
    Z = M.zebras(ctx)
    for br in BRANCHES:
        n = sum(1 for z in Z.values() if z["p"].get("branche") == br)
        R.tester(n >= 1, entite=br, valeur=n, seuil="≥ 1 traversée", detail=f"{n} zébra(s) sur la branche")


@regle("MQ-PP-002", "description", "majeur",
       "Dans le carrefour à feux, chaque traversée des branches à moins de 30 m de l'aire du carrefour est équipée de "
       "signaux piétons R12 (groupe de têtes R12 du .xodr à moins de 8 m d'une extrémité) et chaque groupe R12 a une traversée à moins de 8 m. Unités : "
       "zébra d'une branche à feux, groupe R12.", "implemente")
def mq_pp_002(ctx, R):
    jn = ctx.jonction
    Z = {i: z for i, z in M.zebras(ctx).items() if z["p"].get("branche") in BRANCHES
         and float(K.dist_polys(((z["A"] + z["B"]) / 2)[None], jn)[0]) <= 30.0}
    G = groupes_r12(ctx)
    for zid, z in Z.items():
        d = min([min(np.hypot(*(g - z["A"])), np.hypot(*(g - z["B"]))) for g, _ in G], default=np.inf)
        R.tester(d <= 8.0, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(d, 1), seuil="R12 à ≤ 8 m",
                 detail=f"groupe R12 le plus proche à {d:.1f} m")
    tous = M.zebras(ctx)
    for g, ids in G:
        d = min([float(K.dist_polys(g[None], [z["rect"]])[0]) for z in tous.values()], default=np.inf)
        R.tester(d <= 8.0, entite="R12 " + ",".join(ids), xy=g, valeur=r4(d, 1), seuil="traversée à ≤ 8 m",
                 detail=f"zébra le plus proche à {d:.1f} m")


@regle("MQ-LEF-010", "description", "majeur",
       "Visibilité des R11 principaux sur 30 m : rayons depuis l'œil du conducteur (1,30 m) au centre de chaque voie "
       "commandée, 10, 20 et 30 m en amont du feu, vers la tête (zOffset + 0,48 m) ; obstacles : troncs (Ø 0,4 m, "
       "jusqu'à 40 % de la hauteur), houppiers (sphère de diamètre décrit centrée à h − rayon), panneaux (0,7 m à "
       "leur hauteur), mâts et abris. Unité : rayon (feu × voie × distance).", "partiel",
       "houppiers modélisés par des sphères ; mobilier sans géométrie fine")
def mq_lef_010(ctx, R):
    obs = []
    for f in ctx.arbres:
        p = f["properties"]
        if "absent" in str(p.get("statut_2026", "")) or p.get("x_local") is None:
            continue
        h = float(p.get("hauteur_m") or 8)
        rc = float(p.get("diametre_couronne_m") or 4) / 2
        xy = np.array([p["x_local"], p["y_local"]])
        zs = float(p.get("z_local") or 0)
        obs.append(("tronc " + p["id"], xy, 0.2, zs, zs + 0.4 * h))
        obs.append(("houppier " + p["id"], xy, rc, zs + max(h - 2 * rc, 2.0), zs + h))
    for f in ctx.mobilier:
        p = f["properties"]
        if f["geometry"]["type"] != "Point" or p.get("x_local") is None:
            continue
        zs = float(p.get("z_local") or 0)
        h = float(p.get("hauteur_m") or 2.5)
        r = {"panneau": 0.35, "abri_bus": 1.0, "mobilier_publicitaire": 0.7, "lampadaire": 0.1}.get(p["type"])
        if r:
            obs.append((p["id"], np.array([p["x_local"], p["y_local"]]), r, zs + max(0.0, h - 1.0), zs + h + 0.3))
    for sig in [s for s in ctx.signaux if s["type"] == "1000001" and "principal" in s["nom"]]:
        r, sec, voies, cote = M.approche_r11(ctx, sig)
        z_t = float(ctx.niv.z(np.array([sig["xy"][0]]), np.array([sig["xy"][1]]))[0]) + sig["zOffset"] + 0.48
        cible = np.array([sig["xy"][0], sig["xy"][1], z_t])
        sens = 1 if cote < 0 else -1
        for v in voies:
            for dist in (10.0, 20.0, 30.0):
                s0 = sig["s"] - sens * dist
                if not 0 <= s0 <= r.longueur:
                    continue
                sec0 = r.section(s0)
                if v not in sec0.voies:
                    continue
                xy, _, _ = centre_voie(ctx, r.id, sec0.s, v, [s0])
                z0 = float(ctx.niv.z(xy[:, 0], xy[:, 1])[0]) + 1.30
                oeil = np.array([xy[0, 0], xy[0, 1], z0])
                gene = []
                for nom, c, rad, za, zb in obs:
                    d2 = cible[:2] - oeil[:2]
                    L2 = float(d2 @ d2)
                    t = float(np.clip((c - oeil[:2]) @ d2 / max(L2, 1e-9), 0, 1))
                    if t < 0.03 or t > 0.97:
                        continue
                    q = oeil + t * (cible - oeil)
                    if np.hypot(*(q[:2] - c)) < rad and za <= q[2] <= zb:
                        gene.append(nom)
                R.tester(not gene, entite=f"{sig['nom']} / voie {v} à {dist:.0f} m", xy=oeil[:2], valeur=len(gene),
                         seuil="aucun masque", detail="masqué par " + ", ".join(sorted(gene)[:4]), ecart=1 + len(gene))


@regle("MQ-PP-013", "description", "mineur",
       "Triangle de visibilité des traversées : aucun masque de 0,60 à 2,30 m (mobilier hors mâts : abris, armoires, "
       "mobilier publicitaire, panneaux d'information, distributeurs, conteneurs ; clôtures) dans le triangle formé par "
       "le piéton (1 m derrière l'extrémité du zébra), l'extrémité du zébra et le conducteur à 28 m en amont sur l'axe "
       "de la chaussée, pour les deux sens. Unité : extrémité × sens.", "partiel",
       "végétation basse et stationnement non décrits ; sens de circulation pris des deux côtés")
def mq_pp_013(ctx, R):
    masques = []
    for f in ctx.mobilier:
        p = f["properties"]
        if p["type"] in ("abri_bus", "armoire", "mobilier_publicitaire", "panneau_information", "distributeur",
                         "conteneur_verre", "totem_PR"):
            if f["geometry"]["type"] == "Point" and p.get("x_local") is not None:
                masques.append((p["id"], np.array([[p["x_local"], p["y_local"]]])))
        elif p["type"] == "cloture" and f["geometry"]["type"] == "LineString" and (p.get("hauteur_m") or 1.0) >= 0.6:
            masques.append((p["id"], K.densifier(K.ligne_local(f["geometry"])[0], 0.25)))
    for zid, z in sorted(M.zebras(ctx).items()):
        A, B = z["A"], z["B"]
        ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
        u = np.array([math.cos(math.radians(z["p"]["cap_bandes_deg"])), math.sin(math.radians(z["p"]["cap_bandes_deg"]))])
        for bout, E, sgn in (("A", A, -1), ("B", B, 1)):
            P = E + sgn * 1.0 * ax
            for sens in (1, -1):
                D = (A + B) / 2 - sens * 28.0 * u
                tri = [np.array([P, E, D])]
                gene = [i for i, Q in masques if K.dans(Q, tri).any()]
                R.tester(not gene, entite=f"{zid} {bout} sens {sens:+d}", xy=E, valeur=len(gene), seuil="aucun masque",
                         detail="masque : " + ", ".join(gene[:4]))


# =========================================================================== îlots et refuges
def paires_ilot_axe(ctx, classe="zebra"):
    out = []
    if classe == "zebra":
        axes = [(i, z["A"], z["B"]) for i, z in M.zebras(ctx).items()]
    else:
        axes = []
        for i, e in sorted(ctx.marquages.items()):
            p = e["p"]
            if p["classe"] == "passage" and p["type"] == "traversee_cyclable" and "lignes" in e:
                for L in e["lignes"]:
                    axes.append((i, L[0], L[-1]))
    for iid, il in sorted(ctx.ilots.items()):
        poly = il["poly"][0]
        for zid, A, B in axes:
            w = ilot_largeur_axe(poly, A, B)
            if w > 0.05:
                out.append((iid, il, zid, w, A, B))
    return out


@regle("GA-ILO-001", "description", "majeur",
       "Un îlot traversé par un passage n'est refuge que s'il fait ≥ 1,50 m dans le sens de la traversée (longueur de "
       "l'axe du zébra prolongé de 6 m à l'intérieur du polygone de l'îlot) ; sinon pas de surélévation (îlot "
       "franchissable). Unité : couple îlot / zébra.", "implemente")
def ga_ilo_001(ctx, R):
    vus = set()
    for iid, il, zid, w, A, B in paires_ilot_axe(ctx):
        vus.add(iid)
        refuge = not il["p"].get("franchissable")
        ok = w >= 1.50 - 1e-6 or not refuge
        R.tester(ok, entite=f"{iid} / {zid}", xy=il["poly"][0][0].mean(0), valeur=r4(w, 2), seuil="≥ 1,50 m",
                 detail=f"îlot {il['p']['type']} de {w:.2f} m dans le sens de la traversée, surélevé", ecart=1.5 / max(w, 0.1))
    # îlots typés « refuge » qu'aucun zébra ne traverse (revue conformité du 11/10/2026 : I-0056, I-0242, I-0332,
    # I-0368, I-0658 non contrôlés) : largeur minimale (petite dimension de la boîte orientée) ≥ 1,50 m, sinon le type
    # « refuge » est à revoir (mineur : aucune traversée ne s'y appuie)
    for iid, il in sorted(ctx.ilots.items()):
        if iid in vus or il["p"].get("type") != "refuge":
            continue
        P = np.asarray(il["poly"][0][0], float)
        c = P.mean(0)
        _, V = np.linalg.eigh(np.cov((P - c).T))
        q = (P - c) @ V
        w = float(min(q[:, 0].max() - q[:, 0].min(), q[:, 1].max() - q[:, 1].min()))
        R.tester(w >= 1.50 - 1e-6, entite=f"{iid} (sans zébra)", xy=c, valeur=r4(w, 2), seuil="≥ 1,50 m",
                 detail=f"îlot typé refuge sans traversée, largeur minimale {w:.2f} m : type ou largeur à revoir",
                 ecart=1.5 / max(w, 0.1), severite="mineur")


@regle("GA-ILO-002", "description", "majeur",
       "Longueur d'une traversée sans refuge : ≤ 12 m en carrefour à feux (branches à feux), ≤ 8 m sans feux "
       "(longueur de l'axe du zébra + 2 intervalles). Unité : zébra.", "implemente")
def ga_ilo_002(ctx, R):
    for zid, z in sorted(M.zebras(ctx).items()):
        p = z["p"]
        L = float(np.linalg.norm(z["B"] - z["A"])) + 0.5 + 2 * float(p.get("intervalle_m") or 0.5)
        feux = p.get("branche") in BRANCHES
        lim = 12.0 if feux else 8.0
        R.tester(L <= lim, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(L, 1), seuil=f"≤ {lim:.0f} m",
                 detail=f"traversée de {L:.1f} m sans refuge ({'feux' if feux else 'sans feux'}, {p.get('branche')})",
                 ecart=L / lim)


@regle("GA-ILO-006", "description", "mineur",
       "Refuge traversé par une traversée cyclable en deux temps : ≥ 2,00 m dans le sens de la traversée. Unité : "
       "couple îlot / traversée cyclable.", "implemente")
def ga_ilo_006(ctx, R):
    for iid, il, zid, w, A, B in paires_ilot_axe(ctx, "cyclable"):
        R.tester(w >= 2.0, entite=f"{iid} / {zid}", xy=il["poly"][0][0].mean(0), valeur=r4(w, 2), seuil="≥ 2,00 m",
                 detail=f"îlot de {w:.2f} m dans le sens de la traversée cyclable", ecart=2.0 / max(w, 0.1))


@regle("GA-ILO-007", "les_deux", "mineur",
       "Îlots bordés le long d'une voie : si une ligne continue longe la bordure (à moins de 0,6 m, parallèle), la face "
       "est à 3,5u de l'axe de la ligne (0,175 m pour u = 5 cm, 0,21 m pour u = 6 cm) à ±0,05 m ; sinon la face suit le "
       "bord de voie OpenDRIVE (écart médian ≤ 0,30 m). Unité : bordure de ceinture longeant une voie driving.",
       "implemente")
def ga_ilo_007(ctx, R):
    L_ = M.lignes_peintes(ctx)
    cont = [(i, P) for i, (P, iv, p) in L_.items() if p.get("modulation") == "continue"]
    bords = [b for b in K.X.tous_les_bords(ctx.reseau, 0.25)
             if b.type_voie == "driving" and ctx.reseau[b.route].jonction == "-1"]
    BA = np.vstack([b.xy[:-1] for b in bords])
    BB = np.vstack([b.xy[1:] for b in bords])
    for iid, il in sorted(ctx.ilots.items()):
        for bid in il["p"].get("ceinture", []):
            if bid not in ctx.bordures:
                continue
            s, xy, nrm, _ = S.echantillons(ctx, bid, 0.25)
            d_voie, _, _ = K.C.distance_segments(xy, BA, BB)
            proche = d_voie < 1.0
            if proche.sum() < 8:
                continue
            Q = xy[proche]
            best = None
            for li, P in cont:
                d = K.dist_polyligne(Q, P)
                if np.median(d) < 0.6:
                    best = (li, float(np.median(d))) if best is None or np.median(d) < best[1] else best
            u = 0.06 if il["p"].get("type") == "terre_plein_central" else 0.05
            if best:
                ok = abs(best[1] - 3.5 * u) <= 0.05
                det = f"continue {best[0]} à {best[1]:.3f} m de la face (3,5u = {3.5 * u:.3f})"
                val, ec = best[1], abs(best[1] - 3.5 * u) / 0.05
            else:
                med = float(np.median(d_voie[proche]))
                ok = med <= 0.30
                det = f"sans ligne : face à {med:.2f} m du bord de voie"
                val, ec = med, med / 0.30
            R.tester(ok, entite=f"{iid} / {bid}", xy=Q[len(Q) // 2], valeur=r4(val, 3), seuil="3,5u ±0,05 ou bord de voie",
                     detail=det, ecart=max(ec, 1.0))


@regle("GA-ILO-005", "description", "info",
       "Îlots sans fonction de refuge (séparateurs, directionnels, terre-pleins, massifs) : bordures basses franchissables "
       "(A2, I1, I2, IL ; vue 0,04-0,10 m) sauf vue mesurée (LiDAR). Unité : bordure de ceinture d'un îlot non refuge "
       "dont la vue n'est pas mesurée.", "implemente")
def ga_ilo_005(ctx, R):
    for iid, il in sorted(ctx.ilots.items()):
        if il["p"]["type"] == "refuge":
            continue
        for bid in il["p"].get("ceinture", []):
            if bid not in ctx.bordures:
                continue
            p = ctx.bordures[bid]["p"]
            src = (p["prov"].get("intervalles") or {}).get("src", "")
            if "lidar" in src or p["source"].get("statut_hauteur") == "mesuree":
                continue
            profs = sorted({it["profil"] for it in p["intervalles"] if it["role"] == "courant"})
            vues = [it["vue_m"] for it in p["intervalles"] if it["role"] == "courant"]
            ok = all(pr in ("A2", "I1", "I2", "IL") for pr in profs) and all(0.04 - 1e-6 <= v <= 0.10 + 1e-6 for v in vues)
            R.tester(ok, entite=f"{iid} / {bid}", xy=ctx.bordures[bid]["P"][0, :2], valeur=",".join(profs),
                     seuil="A2 / I1 / I2 / IL, vue 0,04-0,10", detail=f"profils {profs}, vues {sorted(set(vues))} "
                     f"(hauteur {src})")


# =========================================================================== pistes, quais
@regle("MQ-CYC-013", "description", "majeur",
       "Traversée piétonne d'une branche bordée par une piste bidirectionnelle : écart d entre la piste (voie biking) et "
       "la chaussée (voie driving) le long de l'axe du zébra ; d < 0,50 m (contiguës) ou d ≥ 1,50 m (refuge) ; "
       "0,50 ≤ d < 1,50 m signalé (refuge trop étroit). Unité : zébra coupant une voie biking.", "implemente")
def mq_cyc_013(ctx, R):
    bik = [v["poly"] for v in ctx.voies if v["type"] == "biking" and not v["jonction"]]
    drv = [v["poly"] for v in ctx.voies if v["type"] in ("driving", "bus") and not v["jonction"]]
    for zid, z in sorted(M.zebras(ctx).items()):
        A, B = z["A"], z["B"]
        ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
        t = np.arange(-4.0, np.linalg.norm(B - A) + 4.0, 0.05)
        Q = A + t[:, None] * ax
        mb, md = K.dans_liste(Q, bik), K.dans_liste(Q, drv)
        if not mb.any() or not md.any():
            continue
        tb, td = t[mb], t[md]
        # écart minimal entre un échantillon piste et un échantillon chaussée
        d = float(np.min(np.abs(tb[:, None] - td[None, :]))) - 0.05
        d = max(d, 0.0)
        ok = d < 0.5 or d >= 1.5
        R.tester(ok, entite=zid, xy=(A + B) / 2, valeur=r4(d, 2), seuil="d < 0,50 ou ≥ 1,50 m",
                 detail=f"écart piste / chaussée de {d:.2f} m le long de la traversée", ecart=2.0)


@regle("GA-QBU-004", "description", "mineur",
       "Arrêt de bus en alignement droit, jamais le long d'un trottoir en courbe : rayon minimal (primitives "
       "régularisées, sinon cercle par 3 points à ±2 m) des parties QUAI_BUS des bordures (1 m de raccord exclu à chaque "
       "bout) ≥ 200 m. Unité : bordure de "
       "quai.", "implemente")
def ga_qbu_004(ctx, R):
    for bid, b in quais(ctx):
        iq = [it for it in b["p"]["intervalles"] if it["profil"] == "QUAI_BUS"]
        s0, s1 = min(it["s0"] for it in iq) + 1.0, max(it["s1"] for it in iq) - 1.0
        if s1 - s0 < 2.0:
            continue
        prs = (b["p"].get("geometrie_reguliere") or {}).get("primitives") or []
        arcs = [pr.get("rayon_m") or (1 / abs(pr["k0"]) if abs(pr.get("k0", 0)) > 1e-9 else np.inf) for pr in prs
                if pr["type"] in ("arc", "clothoide") and pr["s1"] > s0 and pr["s0"] < s1]
        s = np.arange(s0, s1, 0.5)
        rmes = float(np.min(K.C.rayon_courbure(b["P"][:, :2], s, 2.0))) if len(s) else np.inf
        rmin = min(arcs) if arcs else rmes
        R.tester(rmin >= 200.0, entite=bid, xy=K.point(b["P"], (s0 + s1) / 2), valeur=r4(rmin, 1), seuil="≥ 200 m",
                 detail=f"rayon min sur la partie QUAI_BUS ({s0:.1f}-{s1:.1f} m) {rmin:.1f} m", ecart=200 / max(rmin, 1.0))


@regle("GA-QBU-005", "description", "mineur",
       "Dégagement sur le quai : au moins 0,90 m libres entre le nez de bordure du quai et l'abri (emprise OSM ou "
       "longueur × largeur décrites). Unité : abri voyageurs.", "partiel", "aire de rotation et 2,20 m libres au droit "
       "de la porte médiane non contrôlées")
def ga_qbu_005(ctx, R):
    Q_ = quais(ctx)
    if not Q_:
        return
    A = np.vstack([b["P"][:-1, :2] for _, b in Q_])
    B = np.vstack([b["P"][1:, :2] for _, b in Q_])
    from ctl_sol import kerbs_chaussee_index
    A2, B2 = kerbs_chaussee_index(ctx)
    for aid, poly, p in abris(ctx):
        d, _, _ = K.C.distance_segments(poly, A, B)
        d2, _, _ = K.C.distance_segments(poly, A2, B2)
        dd = float(min(d.min(), d2.min()))
        R.tester(dd >= 0.90, entite=aid, xy=poly.mean(0), valeur=r4(dd, 2), seuil="≥ 0,90 m",
                 detail=f"abri à {dd:.2f} m du nez de bordure", ecart=0.9 / max(dd, 0.05))


@regle("GA-CYC-005", "description", "mineur",
       "Piste longeant un arrêt : elle passe derrière l'abri (abri plus proche de la chaussée que l'axe de la piste) ; "
       "abri à ≥ 0,90 m de la chaussée. Unité : abri à moins de 8 m d'une voie biking.", "partiel",
       "cheminement de 1,40 m côté façades non mesurable (façades non décrites)")
def ga_cyc_005(ctx, R):
    bik = [v for v in ctx.voies if v["type"] == "biking"]
    from ctl_sol import kerbs_chaussee_index
    A2, B2 = kerbs_chaussee_index(ctx)
    for aid, poly, p in abris(ctx):
        c = poly.mean(0)
        db = [float(K.dist_polys(c[None], [v["poly"]])[0]) for v in bik]
        if not db or min(db) > 8.0:
            continue
        v = bik[int(np.argmin(db))]
        cb = v["poly"][0][np.argmin(np.hypot(*(v["poly"][0] - c).T))]
        da, _, _ = K.C.distance_segments(c[None], A2, B2)
        dp, _, _ = K.C.distance_segments(cb[None], A2, B2)
        ok = da[0] < dp[0] and K.C.distance_segments(poly, A2, B2)[0].min() >= 0.9
        R.tester(ok, entite=aid, xy=c, valeur=r4(da[0], 2), seuil="piste derrière l'abri, abri ≥ 0,90 m",
                 detail=f"abri à {da[0]:.2f} m de la chaussée, piste à {dp[0]:.2f} m")


@regle("GA-QBU-007", "description", "mineur",
       "Abords d'un arrêt : aucun passage piéton à moins de 5 m des extrémités du quai (prolongement de la bordure de "
       "quai) et aucune surface de stationnement contre la chaussée dans les 5 m amont / aval. Unité : quai.",
       "partiel", "places de stationnement non décrites : surfaces de classe parking à moins de 5 m seulement")
def ga_qbu_007(ctx, R):
    G = S.grille(ctx)
    for bid, b in quais(ctx):
        P = b["P"][:, :2]
        tg0, tg1 = P[1] - P[0], P[-1] - P[-2]
        ext = np.vstack([P[0] - 5 * tg0 / np.linalg.norm(tg0), P, P[-1] + 5 * tg1 / np.linalg.norm(tg1)])
        det = []
        for zid, z in M.zebras(ctx).items():
            d = float(K.dist_polys(K.densifier(ext, 0.25), [z["rect"]]).min())
            if d < 5.0:
                det.append(f"passage {zid} à {d:.1f} m")
        Qe = K.densifier(ext, 0.25)
        _, xy, nrm, _ = S.echantillons(ctx, bid, 0.5)
        sonde = np.vstack([Qe - 1.0 * nrm.mean(0), Qe - 2.0 * nrm.mean(0)])
        _, cl = S.region_en(ctx, sonde)
        if (cl == "parking").sum() * 0.25 > 1.0:
            det.append(f"stationnement contre la chaussée sur {(cl == 'parking').sum() * 0.25:.1f} m")
        R.tester(not det, entite=bid, xy=P[len(P) // 2], valeur=len(det), seuil="5 m dégagés", detail=" ; ".join(det))


@regle("GA-QBU-008", "description", "mineur",
       "Pas d'avaloir sous le passage des roues du bus sur l'emprise du quai et 3 m de part et d'autre (ponctuels_sol "
       "de type avaloir). Unité : quai.", "implemente")
def ga_qbu_008(ctx, R):
    av = [v["poly"][0][0].mean(0) for v in ctx.ponctuels.values() if v["p"].get("type") in ("avaloir", "grille")]
    for bid, b in quais(ctx):
        d = min([float(K.dist_polyligne(np.array([a]), b["P"][:, :2])[0]) for a in av], default=np.inf)
        R.tester(d > 1.0, entite=bid, xy=b["P"][0, :2], valeur=r4(d if np.isfinite(d) else -1, 2), seuil="aucun avaloir",
                 detail=f"avaloir à {d:.2f} m")


@regle("GA-CHA-006", "description", "mineur",
       "Hauteur libre : lampadaires à crosse dont le pied est à moins de 2 m d'une bordure de chaussée (crosse "
       "au-dessus de la chaussée) : hauteur ≥ 3,80 m ; panneaux sur cheminement : bord bas ≥ 2,20 m si posés à moins de "
       "0,5 m du cheminement libre (hauteur décrite − 0,7 m). Unité : objet concerné.", "partiel",
       "houppiers (hauteur de base) et potences non décrits")
def ga_cha_006(ctx, R):
    from ctl_sol import kerbs_chaussee_index
    A2, B2 = kerbs_chaussee_index(ctx)
    G = S.grille(ctx)
    for f in sorted(ctx.mobilier, key=lambda f: f["properties"]["id"]):
        p = f["properties"]
        if f["geometry"]["type"] != "Point" or p.get("x_local") is None:
            continue
        xy = np.array([p["x_local"], p["y_local"]])
        h = p.get("hauteur_m")
        if p["type"] == "lampadaire" and "crosse" in str(p.get("sous_type", "")):
            d, _, _ = K.C.distance_segments(xy[None], A2, B2)
            if d[0] <= 2.0:
                R.tester(h is not None and h >= 3.8, entite=p["id"], xy=xy, valeur=h, seuil="≥ 3,80 m",
                         detail=f"lampadaire à crosse à {d[0]:.1f} m de la chaussée, hauteur {h}")
        elif p["type"] == "panneau" and h is not None and h > 1.0:
            _, cl = S.region_en(ctx, xy[None])
            if cl[0] in K.PIETON:
                bas = h - 0.7
                R.tester(bas >= 2.2, entite=p["id"], xy=xy, valeur=r4(bas, 2), seuil="bord bas ≥ 2,20 m",
                         detail=f"panneau {p.get('code')} sur trottoir, bord bas estimé {bas:.2f} m", ecart=2.2 / max(bas, 0.1))


# =========================================================================== VAL-XOD-008
@regle("VAL-XOD-008", "les_deux", "majeur",
       "Cohérence .xodr / scène fabriquée : (a) chaque roadMark solid / broken / solid solid a une ligne fabriquée le "
       "long de son bord (≥ 50 % à 0,30 m) de largeur décrite = width ±0,01 m, de type cohérent (continue / "
       "discontinue / double) ; (b) roadMark curb : height 0,13 contre la vue décrite de la bordure longeant le bord "
       "(±0,005 m) ; (c) objets crosswalk zebra : IoU ≥ 0,8 et angle ≤ 3° (grands côtés) avec un zébra fabriqué, "
       "crosswalk bicycle : traversée cyclable ou pavés jaunes Chronovélo à ≤ 1,5 m du contour de l'objet ; (d) trafficIsland apparié "
       "à un îlot ; (e) R11 principal : LEF (peinte ou virtuelle) à 0-4 m ; R12 : traversée ; R13c : piste à ≤ 6 m ; "
       "C6 : quai à ≤ 15 m ; (f) Z au centre des voies hors jonction |xodr − sol fabriqué| ≤ 0,02 m (médiane par "
       "voie, p95 rapporté). Unités : roadMark, objet, signal, voie.", "implemente")
def val_xod_008(ctx, R):
    import nivellement_xodr as NX
    L_ = M.lignes_peintes(ctx)
    lignes = [(i, P, p) for i, (P, iv, p) in L_.items()]
    # (a) / (b) roadMarks
    for rid in sorted(ctx.reseau, key=int):
        r = ctx.reseau[rid]
        if r.jonction != "-1":
            continue
        for b in K.X.bords_route(r, 0.5):
            sec = next(x for x in r.sections if abs(x.s - b.section_s) < 1e-6)
            if b.voie not in sec.voies:
                continue
            marques = sec.voies[b.voie].marques
            for k, rm in enumerate(marques):
                ty = rm.get("type")
                if ty in (None, "none"):
                    continue
                sa = sec.s + rm["sOffset"]
                sb = sec.s + marques[k + 1]["sOffset"] if k + 1 < len(marques) else sec.s1
                m = (b.s >= sa) & (b.s <= sb)
                if m.sum() < 2:
                    continue
                Q = b.xy[m]
                cle = f"route {rid} s{b.section_s:g} voie {b.voie} [{sa:.0f}-{sb:.0f}] {ty}"
                if ty == "curb":
                    best = None
                    for bid, bb in ctx.bordures.items():
                        P = bb["P"][:, :2]
                        if np.hypot(*(P[:, None] - Q[None, [0, -1]]).reshape(-1, 2).T).min() > 60:
                            continue
                        d = K.dist_polyligne(Q, P)
                        part = float((d <= 0.5).mean())
                        if part > 0.3 and (best is None or part > best[0]):
                            sb_, _, _ = K.C.projeter(P, Q[d <= 0.5])
                            best = (part, bid, float(np.median(S.vue_a(bb["p"], sb_))))
                    h = float(rm.get("height") or 0)
                    if best is None:
                        R.tester(False, entite=cle, xy=Q[len(Q) // 2], seuil="bordure le long du bord",
                                 detail=f"(b) aucune bordure décrite le long du roadMark curb (height {h})", ecart=2,
                                 severite="mineur")
                    else:
                        R.tester(abs(best[2] - h) <= 0.005, entite=cle, xy=Q[len(Q) // 2], valeur=r4(best[2], 3),
                                 seuil=f"vue = height {h} ±0,005", detail=f"(b) {best[1]} : vue décrite {best[2]:.3f} m "
                                 f"pour height {h} m", ecart=abs(best[2] - h) / 0.005, severite="mineur")
                    continue
                best = None
                for i, P, p in lignes:
                    lo, hi = P.min(0) - 1, P.max(0) + 1
                    if (Q[:, 0].max() < lo[0] or Q[:, 0].min() > hi[0] or Q[:, 1].max() < lo[1]
                            or Q[:, 1].min() > hi[1]):
                        continue
                    part = float((K.dist_polyligne(Q, P) <= 0.30).mean())
                    if part > 0.0 and (best is None or part > best[0]):
                        best = (part, i, p)
                parts = sum(1 for i, P, p in lignes if (K.dist_polyligne(Q, P) <= 0.30).mean() > 0.2)
                if best is None or best[0] < 0.5:
                    R.tester(False, entite=cle, xy=Q[len(Q) // 2], valeur=r4(best[0] if best else 0, 2),
                             seuil="ligne fabriquée le long du roadMark", detail=f"(a) roadMark {ty} sans ligne fabriquée "
                             f"(couverture {best[0] * 100 if best else 0:.0f} %)", ecart=2)
                    continue
                part, i, p = best
                w_x = float(rm.get("width") or 0)
                w_d = float(p.get("largeur_m") or 0.10)
                mod = p.get("modulation")
                type_ok = (ty == "solid" and mod == "continue") or (ty == "broken" and mod not in (None, "continue")) \
                    or (ty == "solid solid" and parts >= 2)
                ok = abs(w_x - w_d) <= 0.01 + 1e-6 and type_ok
                R.tester(ok, entite=cle, xy=Q[len(Q) // 2], valeur=r4(w_d, 3), seuil=f"width {w_x} ±0,01, type",
                         detail=f"(a) {i} : largeur {w_d} pour width {w_x}, modulation {mod} pour {ty}"
                                + ("" if ty != "solid solid" else f" ({parts} lignes)"),
                         ecart=max(abs(w_x - w_d) / 0.01, 1.0 if type_ok else 2.0))
    # (c) crosswalks
    Z = M.zebras(ctx)
    fab = M.fab_marquages(ctx)
    tcs = {i: np.vstack(e["lignes"]) for i, e in ctx.marquages.items() if e["p"]["classe"] == "passage"
           and e["p"]["type"] == "traversee_cyclable" and "lignes" in e and ctx.fabrique_marquage(e["p"])}

    def axe_long(r_):
        a = np.r_[r_, r_[:1]]
        k = int(np.argmax(np.hypot(*np.diff(a, axis=0).T)))
        return K.cap_deg(a[k + 1] - a[k]) % 180
    for o in ctx.xodr_objets:
        if o["type"] == "crosswalk" and o.get("sous_type") == "bicycle":
            an = o["anneau"]
            c = an.mean(0) if an is not None else o["xy"]
            jaunes = [(float(K.dist_polys(c[None], e["poly"])[0]), i) for i, e in ctx.marquages.items()
                      if e["p"].get("couleur") == "jaune" and "poly" in e and ctx.fabrique_marquage(e["p"])]
            if an is not None:
                # distance de la traversée au CONTOUR de l'objet (0 si dedans) et non à son centre : une file de pavés
                # borde la traversée de 3,6 m de large (revue du 11/10/2026, MP-8200/8201 à 0,5 m du contour)
                def d_contour(P):
                    P = np.atleast_2d(P)
                    return 0.0 if K.dans(P, [an]).any() else float(K.dist_polys(P, [[an]]).min())
                cand = [(d_contour(K.densifier(P, 0.25) if len(P) > 1 else P), i) for i, P in tcs.items()]
            else:
                cand = [(float(K.dist_polyligne(c[None], P)[0]), i) for i, P in tcs.items()]
            d = min(cand + jaunes, default=(np.inf, None))
            R.tester(d[0] <= 1.5, entite=f"crosswalk {o['route']}/{o['id']} (bicycle)", xy=c, valeur=r4(d[0], 2),
                     seuil="traversée cyclable à ≤ 1,5 m", detail=f"(c) traversée cyclable {d[1]} à {d[0]:.2f} m",
                     ecart=d[0] / 1.5)
            continue
        if o["type"] == "crosswalk":
            an = o["anneau"]
            if an is None:
                continue
            best = None
            for zid, z in Z.items():
                lo, hi = an.min(0), an.max(0)
                g = np.mgrid[lo[0]:hi[0]:0.05, lo[1]:hi[1]:0.05].reshape(2, -1).T
                if not len(g):
                    continue
                ma = K.dans(g, [an])
                mz = K.dans(g, z["rect"])
                if not mz.any():
                    continue
                # aire de l'union : complétée par le rectangle du zébra hors boîte de l'objet
                inter = (ma & mz).sum() * 0.0025
                union = ma.sum() * 0.0025 + K.aire(z["rect"][0]) - inter
                iou = inter / max(union, 1e-9)
                if best is None or iou > best[0]:
                    ang = K.ecart_angle(axe_long(an), axe_long(z["rect"][0]), 180.0)
                    best = (iou, zid, ang)
            if best is None:
                R.tester(False, entite=f"crosswalk {o['route']}/{o['id']} ({o['sous_type']})", xy=an.mean(0),
                         seuil="zébra apparié", detail="(c) aucun zébra fabriqué sous l'objet crosswalk", ecart=2)
                continue
            iou, zid, ang = best
            ok = iou >= 0.8 and ang <= 3.0
            R.tester(ok, entite=f"crosswalk {o['route']}/{o['id']} ({o['sous_type']})", xy=an.mean(0), valeur=r4(iou, 2),
                     seuil="IoU ≥ 0,8, angle ≤ 3°", detail=f"(c) {zid} : IoU {iou:.2f}, angle {ang:.1f}°",
                     ecart=max(0.8 / max(iou, 0.05), ang / 3.0))
        elif o["type"] == "trafficIsland":
            c = o["anneau"].mean(0) if o["anneau"] is not None else o["xy"]
            ok = any(K.dans(c[None], il["poly"][0])[0] or float(K.dist_polys(c[None], il["poly"])[0]) < 1.0
                     for il in ctx.ilots.values())
            R.tester(ok, entite=f"trafficIsland {o['route']}/{o['id']}", xy=c, seuil="îlot décrit apparié",
                     detail="(d) aucun îlot décrit sous l'objet trafficIsland")
    # (e) signaux
    lef = M.lefs(ctx)
    for sig in ctx.signaux:
        if sig["type"] == "1000001" and "principal" in sig["nom"]:
            r = ctx.reseau[sig["route"]]
            sref = np.linspace(0, r.longueur, int(r.longueur / 0.1) + 2)
            xr, yr, _ = r.reference(sref)
            ref = np.c_[xr, yr]
            s_s = K.C.projeter(ref, sig["xy"][None])[0][0]
            sens = 1.0 if sig["orientation"] == "+" else -1.0
            av = []
            for i, e in lef.items():
                c = M.axe(e).mean(0)
                if np.hypot(*(c - sig["xy"])) > 15:
                    continue
                av.append(((s_s - K.C.projeter(ref, c[None])[0][0]) * sens, i))
            ok = any(-0.3 <= a <= 4.0 for a, _ in av)
            R.tester(ok, entite=f"R11 {sig['nom']}", xy=sig["xy"], valeur=r4(min([a for a, _ in av], key=abs), 2)
                     if av else None, seuil="LEF à 0-4 m en amont", detail=f"(e) LEF : {[(i, round(a, 2)) for a, i in av]}")
        elif sig["type"] == "1000013":
            d = min([float(K.dist_polys(sig["xy"][None], [v["poly"]])[0]) for v in ctx.voies if v["type"] == "biking"],
                    default=np.inf)
            R.tester(d <= 6.0, entite=f"R13c {sig['nom']}", xy=sig["xy"], valeur=r4(d, 1), seuil="piste à ≤ 6 m",
                     detail=f"(e) piste à {d:.1f} m")
        elif sig["type"] == "C6":
            d = min([float(K.dist_polyligne(sig["xy"][None], b["P"][:, :2])[0]) for _, b in quais(ctx)], default=np.inf)
            R.tester(d <= 15.0, entite=f"C6 {sig['nom']}", xy=sig["xy"], valeur=r4(d, 1), seuil="quai à ≤ 15 m",
                     detail=f"(e) bordure de quai à {d:.1f} m")
    for g, ids in groupes_r12(ctx):
        d = min([float(K.dist_polys(g[None], [z["rect"]])[0]) for z in Z.values()], default=np.inf)
        R.tester(d <= 8.0, entite="R12 " + ",".join(ids), xy=g, valeur=r4(d, 1), seuil="traversée à ≤ 8 m",
                 detail=f"(e) zébra à {d:.1f} m")
    # (f) Z au centre des voies
    mods = NX.modeles()
    tous = []
    for rid, sec_s, v, typ, s, w, cote in largeurs_voies(ctx, 1.0):
        if typ not in ("driving", "bus") or rid not in mods:
            continue
        xy, _, t = centre_voie(ctx, rid, sec_s, v, s)
        zx = mods[rid].z(s, t)
        zs = S.requete_sol(ctx, xy)
        d = zs - zx
        ok_ = np.isfinite(d)
        if ok_.sum() < 3:
            continue
        tous.append(np.abs(d[ok_]))
        med = float(np.median(np.abs(d[ok_])))
        k = int(np.nanargmax(np.abs(np.where(ok_, d, 0))))
        R.tester(med <= 0.02, entite=f"route {rid} s{sec_s:g} voie {v} (Z)", xy=xy[k], valeur=r4(med, 4),
                 seuil="|xodr − sol| médiane ≤ 0,02 m", detail=f"(f) |Z xodr − sol fabriqué| médiane {med * 100:.1f} cm, "
                 f"max {np.abs(d[ok_]).max() * 100:.1f} cm", ecart=med / 0.02)
    if tous:
        R.mesure("f_ecart_z_centre_voies_m", stats(np.concatenate(tous), (50, 95, 99)))


# =========================================================================== VAL-COV-006 / VAL-JCT-010
def extremites_zebra(ctx, z):
    """Pour chaque extrémité : (bordure coupée ou None, abaissé de traversée couvrant, BEV ancrée sur l'abaissé)."""
    out = []
    A, B = z["A"], z["B"]
    ax = (B - A) / max(np.linalg.norm(B - A), 1e-9)
    for nom, P0, P1 in (("A", A, A - 3.5 * ax), ("B", B, B + 3.5 * ax)):
        best = None
        for bid, b in ctx.bordures.items():
            Q = b["P"][:, :2]
            for t, j in M.intersections(P0, P1, Q):
                if best is None or t < best[0]:
                    s_ = float(b["s"][j] + np.hypot(*(P0 + t * (P1 - P0) - Q[j])))
                    best = (t, bid, s_)
        if best is None:
            out.append((nom, None, None, None, P0))
            continue
        _, bid, s_ = best
        ab = next((a for a in ctx.bordures[bid]["p"]["abaisses"] if a["type"] in ("traversee", "traversee_cyclable")
                   and a["s0"] - 0.6 <= s_ <= a["s1"] + 0.6), None)
        bev = None
        if ab is not None:
            bev = next((i for i, v in ctx.ponctuels.items() if (v["p"].get("ancrage") or {}).get("abaisse") == ab["id"]),
                       None)
        out.append((nom, bid, ab, bev, P0))
    return out


def part_inferee(ctx):
    c = collections.defaultdict(lambda: [0, 0])
    for e in ctx.marquages.values():
        p = e["p"]
        z = p.get("zone_etat", "?")
        c[z][1] += 1
        if str(p.get("src", "")).startswith("regle") or p.get("src") == "v1":
            c[z][0] += 1
    return {z: {"inferes_ou_v1": a, "total": b, "part": r4(a / b, 3)} for z, (a, b) in sorted(c.items())}


@regle("VAL-COV-006", "description", "majeur",
       "Complétude par approche et par traversée : ligne d'arrêt (LEF peinte ou virtuelle) par approche à feux ; "
       "flèches sur toutes les voies des approches affectées (INF-FLE-004) ; passage par groupe R12 ; abaissé de "
       "traversée et BEV à chaque extrémité de passage bordée (axe prolongé de 3,5 m coupant une bordure ; BEV exigée "
       "pour un abaissé de traversée sur trottoir) ; part des éléments inférés ou v1 seuls par zone rapportée. "
       "Unité : élément exigé.", "implemente")
def val_cov_006(ctx, R):
    lef = M.lefs(ctx)
    for sig in [s for s in ctx.signaux if s["type"] == "1000001" and "principal" in s["nom"]]:
        d = min([float(np.hypot(*(M.axe(e).mean(0) - sig["xy"]))) for e in lef.values()], default=np.inf)
        R.tester(d <= 15.0, entite=f"LEF {sig['nom']}", xy=sig["xy"], valeur=r4(d, 1), seuil="LEF peinte ou virtuelle",
                 detail=f"LEF la plus proche à {d:.1f} m")
    att = next(r for r in ctx.regles["regles"] if r["id"] == "INF-FLE-004")["parametres"]["attendu_site"]
    fl = collections.defaultdict(list)
    for i, e in M.fleches(ctx).items():
        v = M.voie_de(ctx, M.centroide(e["poly"][0]))
        if v:
            fl[f"R{v[0]}.v{v[1]}"].append(i)
    for cle, typ in sorted(att.items()):
        if typ == "aucune" or "." not in cle:
            continue
        R.tester(bool(fl.get(cle)), entite=f"flèches {cle}", valeur=len(fl.get(cle, [])), seuil=f"flèches {typ}",
                 detail=f"{len(fl.get(cle, []))} flèche(s) sur la voie")
    Z = M.zebras(ctx)
    for g, ids in groupes_r12(ctx):
        d = min([float(K.dist_polys(g[None], [z["rect"]])[0]) for z in Z.values()], default=np.inf)
        R.tester(d <= 8.0, entite="passage R12 " + ",".join(ids), xy=g, valeur=r4(d, 1), seuil="passage à ≤ 8 m")
    for zid, z in sorted(Z.items()):
        for nom, bid, ab, bev, P0 in extremites_zebra(ctx, z):
            if bid is None:
                continue
            ok = ab is not None and (bev is not None or ab["type"] != "traversee"
                                     or not (ab.get("bev") or {}).get("present", True))
            R.tester(ok, entite=f"{zid} extrémité {nom} ({bid})", xy=P0, valeur=None, seuil="abaissé + BEV",
                     detail=("pas d'abaissé de traversée" if ab is None else f"{ab['id']} sans BEV décrite"))
    R.mesure("part_inferee_par_zone", part_inferee(ctx))


@regle("VAL-JCT-010", "les_deux", "majeur",
       "Check-list par branche du carrefour à feux : LEF (peinte ou virtuelle) et R11 à 0-4 m (MQ-LEF-004) ; files "
       "matérialisées (ligne passant à moins de 1 m du bord entre les voies commandées, 10 m en amont du feu) d'au "
       "moins 20 m peints (MQ-LIG-004) ; flèches sur chaque voie "
       "affectée (MQ-FLE-001) ; zébra (MQ-PP-001) ; abaissé et BEV aux extrémités bordées (GA-ABA-001, GA-BEV-001) ; "
       "relief des bandes ≥ 2,5 mm (MQ-PP-014) ; aucune ligne inférée dans l'aire du carrefour (MQ-LIG-001). Unité : "
       "item de check-list × branche ; part inférée par branche rapportée.", "implemente")
def val_jct_010(ctx, R):
    Z = M.zebras(ctx)
    lef = M.lefs(ctx)
    L_ = M.lignes_peintes(ctx)
    att = next(r for r in ctx.regles["regles"] if r["id"] == "INF-FLE-004")["parametres"]["attendu_site"]
    fl = collections.defaultdict(list)
    for i, e in M.fleches(ctx).items():
        v = M.voie_de(ctx, M.centroide(e["poly"][0]))
        if v:
            fl[f"R{v[0]}.v{v[1]}"].append(i)
    parts = {}
    for br, routes in BRANCHES.items():
        sig = next((s for s in ctx.signaux if s["type"] == "1000001" and "principal" in s["nom"]
                    and s["route"] in routes), None)
        if sig is not None:
            d = [(float(np.hypot(*(M.axe(e).mean(0) - sig["xy"]))), i) for i, e in lef.items()]
            d = min(d) if d else (np.inf, None)
            R.tester(d[0] <= 15.0, entite=f"{br} : LEF", xy=sig["xy"], valeur=d[1], seuil="LEF peinte ou virtuelle",
                     detail=f"LEF {d[1]} à {d[0]:.1f} m du R11")
            # files matérialisées ≥ 20 m en amont de la LEF (entre voies de même sens)
            r, sec, voies, cote = M.approche_r11(ctx, sig)
            if len(voies) >= 2:
                lg = 0.0
                for i, (P, iv, p) in L_.items():
                    s10 = sig["s"] - (10.0 if sig["orientation"] == "+" else -10.0)
                    sec10 = r.section(s10)
                    tb = r.t_bords(np.array([s10]), sec10)
                    v_int = sorted(voies, key=abs)[0]
                    x, y, _ = K.X.point_st(r, np.array([s10]), tb[v_int])
                    d_ = float(K.dist_polyligne(np.array([[x[0], y[0]]]), P)[0])
                    if d_ < 1.0:
                        lg = max(lg, sum(b - a for a, b in iv))
                R.tester(lg >= 20.0, entite=f"{br} : files", xy=sig["xy"], valeur=r4(lg, 1), seuil="≥ 20 m",
                         detail=f"ligne de délimitation peinte de {lg:.1f} m en amont")
        for cle, typ in att.items():
            if typ == "aucune" or "." not in cle or cle[1:].split(".")[0] not in routes:
                continue
            R.tester(bool(fl.get(cle)), entite=f"{br} : flèches {cle}", valeur=len(fl.get(cle, [])), seuil=typ)
        zb = {i: z for i, z in Z.items() if z["p"].get("branche") == br}
        R.tester(bool(zb), entite=f"{br} : zébra", valeur=len(zb), seuil="≥ 1")
        for zid, z in sorted(zb.items()):
            for nom, bid, ab, bev, P0 in extremites_zebra(ctx, z):
                if bid is None:
                    continue
                R.tester(ab is not None and (bev is not None or ab["type"] != "traversee"),
                         entite=f"{br} : {zid} {nom}", xy=P0, seuil="abaissé + BEV",
                         detail="pas d'abaissé" if ab is None else f"{ab['id']} sans BEV")
            ep, _, _ = M.epaisseurs(ctx, zid)
            e = float(np.nanmedian(ep)) if len(ep) and np.isfinite(ep).any() else 0.0
            R.tester(e >= 0.0025, entite=f"{br} : {zid} relief", valeur=r4(e, 4), seuil="≥ 2,5 mm")
        n_inf = sum(1 for e in ctx.marquages.values() if e["p"].get("branche") == br
                    and (str(e["p"].get("src", "")).startswith("regle") or e["p"].get("src") == "v1"))
        n_tot = sum(1 for e in ctx.marquages.values() if e["p"].get("branche") == br)
        parts[br] = {"inferes_ou_v1": n_inf, "total": n_tot, "part": r4(n_inf / max(n_tot, 1), 3)}
    jn = ctx.jonction
    for i, (P, iv, p) in L_.items():
        if str(p.get("src", "")).startswith("regle"):
            inside = K.dans_liste(M.points_peints(P, iv), jn).sum() * 0.1
            R.tester(inside <= 1.0, entite=f"carrefour : {i}", xy=P.mean(0), valeur=r4(inside, 1),
                     seuil="aucune ligne inférée dans l'aire")
    R.mesure("part_inferee_par_branche", parts)


@regle("GA-ABA-006", "description", "mineur",
       "Traversées déduites (zébras de source règle, MQ-DET-004) : perpendiculaires aux bordures (±10°), hors arrondis "
       "(rayon des bordures coupées ≥ 12 m), BEV à ≥ 0,50 m l'une de l'autre. Unité : traversée déduite (aucune sur le "
       "site : les passages viennent du levé, du plan et de l'ortho).", "implemente")
def ga_aba_006(ctx, R):
    for zid, z in sorted(M.zebras(ctx).items()):
        if not str(z["p"].get("src", "")).startswith("regle"):
            continue
        cap = M.axe_chaussee_zebra(ctx, z)
        ang = K.ecart_angle(z["p"]["cap_bandes_deg"], cap, 180.0) if cap is not None else 0.0
        R.tester(ang <= 10.0, entite=zid, xy=(z["A"] + z["B"]) / 2, valeur=r4(ang, 1), seuil="perpendiculaire ±10°")
