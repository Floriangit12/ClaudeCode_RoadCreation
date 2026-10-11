"""Contrôles des HDA de marquage (hython Houdini 22) : mesures indépendantes (numpy) des maillages fabriqués contre la
description, et comparaison avec l'ancienne fabrication numpy (recon/out/paquet_jardin/v2/fabrique/marquages.usda).

    hython recon/pcg/houdini/hda/pj_marquage_commun/verifier_marquages.py

Lit les sorties cuites des branches de la scène maîtresse (fab_marquages_lignes, fab_passages, fab_symboles,
fab_zones), recalcule de son côté (Python, sans réutiliser le code VEX) ce que la description impose, et écrit
recon/out/paquet_jardin/v2/fabrique_hda/controle/marquages_controles.json :
    VAL-LIG-002  lignes : longueur peinte (aire / largeur) contre modulation + phase + interruptions ; écart latéral
                 des sommets à l'axe régularisé ; largeur
    VAL-ZEB-003  zébras : nombre de bandes, pas, angle, longueur et largeur des bandes
    VAL-FLE-001  flèches et symboles : origine et cap des instances contre le contour décrit (gabarit posé)
    TQ-SOL-013   drapé : dessus de la peinture - (modèle de nivellement + épaisseur), région de la pièce
    comparaison  ancienne fabrication : entités communes, écarts de centroïde et d'aire
Le script ne modifie aucune géométrie.
"""
import collections
import json
import math
import sys
from pathlib import Path

import hou
import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI.parents[0] / "commun"))
import pj_hda_outils as O  # noqa: E402

RACINE = O.RACINE
sys.path.insert(0, str(RACINE / "recon/pcg/decrire"))
from nivellement_requete import Nivellement  # noqa: E402

HIP = RACINE / "recon/pcg/houdini/paquet_jardin_pcg.hip"
DESCRIPTION = RACINE / "recon/out/paquet_jardin/v2/description/base"
SORTIE = RACINE / "recon/out/paquet_jardin/v2/fabrique_hda"
ANCIEN = RACINE / "recon/out/paquet_jardin/v2/fabrique/marquages.usda"
SPEC = RACINE / "assets/specs/marquages_geometrie.json"
OX, OY = 917279.43, 6460289.98
EPAISSEUR = 0.003


def stat(v, nd=4):
    v = np.asarray(v, float)
    if not len(v):
        return {"n": 0}
    return {"n": int(len(v)), "p50": round(float(np.percentile(v, 50)), nd), "p95": round(float(np.percentile(v, 95)), nd),
            "max": round(float(v.max()), nd)}


# ----------------------------------------------------------------------------------------- géométrie cuite
def faces(geo):
    """Faces (id, pj_entite, pj_piece, normale, aire, sommets (x, y, z) locaux Z haut)."""
    out = []
    for pr in geo.prims():
        P = np.array([v.point().position() for v in pr.vertices()])
        P = np.c_[P[:, 0], -P[:, 2], P[:, 1]]
        n = pr.normal()
        out.append({"id": pr.attribValue("id"), "ent": pr.attribValue("pj_entite"),
                     "piece": pr.attribValue("pj_piece") if geo.findPrimAttrib("pj_piece") else 0,
                     "ny": n[1], "aire": pr.intrinsicValue("measuredarea"), "P": P})
    return out


def empreinte(fs):
    """Aire de l'empreinte (projection horizontale du dessus et des chanfreins)."""
    return sum(f["aire"] * f["ny"] for f in fs if f["ny"] > 0.1)


# ----------------------------------------------------------------------------------------- description
def axe_primitives(prs, pas=0.01):
    """Axe régularisé densifié (Python, indépendant du VEX) : droites et arcs (clothoïdes en sous-arcs de 5 cm)."""
    pts = []
    for pr in prs:
        L = pr["s1"] - pr["s0"]
        n = max(2, int(math.ceil(L / pas)) + 1)
        x0, y0, c0, k0 = pr["x0"] - OX, pr["y0"] - OY, pr["cap0_rad"], pr["k0"]
        k1 = pr.get("k1", k0)
        for u in np.linspace(0, L, n):
            if abs(k1 - k0) > 1e-12:            # clothoïde : intégration numérique
                m = max(1, int(math.ceil(u / 0.005)))
                t = np.linspace(0, u, m + 1)
                c = c0 + k0 * t + 0.5 * (k1 - k0) / max(L, 1e-9) * t * t
                x, y = x0 + np.trapz(np.cos(c), t), y0 + np.trapz(np.sin(c), t)
            elif abs(k0) < 1e-12:
                x, y = x0 + u * math.cos(c0), y0 + u * math.sin(c0)
            else:
                cc = c0 + k0 * u
                x, y = x0 + (math.sin(cc) - math.sin(c0)) / k0, y0 - (math.cos(cc) - math.cos(c0)) / k0
            pts.append((x, y))
    return np.array(pts)


def dist_polyligne(Q, A):
    """Distance de chaque point Q à la polyligne A."""
    a, b = A[:-1], A[1:]
    ab = b - a
    l2 = np.maximum((ab ** 2).sum(1), 1e-12)
    d = np.full(len(Q), np.inf)
    for k in range(0, len(Q), 2000):
        q = Q[k:k + 2000, None, :]
        t = np.clip(((q - a) * ab).sum(2) / l2, 0, 1)
        pr = a + t[..., None] * ab
        d[k:k + 2000] = np.sqrt(((q - pr) ** 2).sum(2)).min(1)
    return d


def intervalles(p, L, mods):
    """Parties peintes attendues (même règle que l'ancienne fabrication : modulation, phase, interruptions)."""
    tr, vi = p.get("trait_m"), p.get("vide_m")
    mod = p.get("modulation") or "continue"
    if (not tr or not vi) and mod in mods:
        tr, vi = mods[mod]
    if mod == "continue" or not tr or not vi:
        iv = [(0.0, L)]
    else:
        per = tr + vi
        ph = p.get("phase_m")
        if ph is None:
            ph = (L - tr) - per * math.floor((L - tr) / per)            # MQ-DET-011
        iv = [(max(ph + k * per, 0.0), min(ph + k * per + tr, L))
              for k in range(int(math.floor(-ph / per)) - 1, int(math.ceil((L - ph) / per)) + 2)]
        iv = [(a, b) for a, b in iv if b - a > 1e-4]
    for a0, b0 in p.get("interruptions") or []:
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
    return [(a, b) for a, b in iv if b - a >= 0.01]


# ----------------------------------------------------------------------------------------- contrôles
def controle_lignes(geo, desc, mods):
    par = collections.defaultdict(list)
    for f in faces(geo):
        par[f["id"]].append(f)
    auto, ambigu = {}, {}
    if geo.findPrimAttrib("pj_coupures_auto") is not None:
        for pr in geo.prims():
            if pr.attribValue("pj_coupures_auto"):
                auto[pr.attribValue("id")] = pr.attribValue("pj_coupures_auto")
            if pr.attribValue("pj_marches_ambigues"):
                ambigu[pr.attribValue("id")] = pr.attribValue("pj_marches_ambigues")
    ecart_aire, lateral, manq, mauvais = [], [], [], []
    for i, f in sorted(desc.items()):
        p = f["properties"]
        if p["classe"] not in ("ligne", "transversale") or (p.get("fabrication") or {}).get("statut") == "non_fabrique":
            continue
        prs = (p.get("geometrie_reguliere") or {}).get("primitives") or []
        if prs:
            L = prs[-1]["s1"]
            A = axe_primitives(prs)
        else:
            A = np.array(f["geometry"]["coordinates"])[:, :2] - (OX, OY)
            L = float(np.hypot(*np.diff(A, axis=0).T).sum())
        w = float(p.get("largeur_m") or 0.10)
        att = w * sum(b - a for a, b in intervalles(p, L, mods))
        fs = par.get(i, [])
        if not fs:
            if att > 1e-3:
                manq.append(i)
            continue
        mes = empreinte(fs)
        r = mes / max(att, 1e-9) - 1.0
        if i not in auto:                                 # coupures automatiques aux marches : longueur réduite voulue
            ecart_aire.append(abs(r))
            if abs(r) > 0.02:
                mauvais.append((i, round(r, 4)))
        Q = np.concatenate([g["P"][:, :2] for g in fs if g["ny"] > 0.1])
        d = dist_polyligne(Q, A) - w / 2
        lateral.append(max(0.0, float(d.max())))
    return {"regle": "VAL-LIG-002", "entites": len(ecart_aire) + len(auto), "manquantes": manq,
            "coupures_auto_marches_MQ-DET-010": dict(sorted(auto.items())),
            "marches_ambigues_non_coupees": dict(sorted(ambigu.items())),
            "ecart_relatif_aire": stat(ecart_aire), "hors_tolerance_2pct": mauvais[:20],
            "depassement_lateral_m": stat(lateral),
            "note": "aire de l'empreinte (dessus + chanfreins projetés) contre largeur x longueur peinte attendue ; "
                    "dépassement = distance max d'un sommet à l'axe régularisé moins la demi-largeur"}


def controle_zebras(geo, desc):
    par = collections.defaultdict(lambda: collections.defaultdict(list))
    for f in faces(geo):
        if f["ny"] > 0.1:
            par[f["id"]][f["piece"]].append(f)
    res, defauts = [], []
    for i, f in sorted(desc.items()):
        p = f["properties"]
        if p["classe"] != "passage" or p["type"] != "zebra":
            continue
        A, B = np.array(f["geometry"]["coordinates"][0][:2]) - (OX, OY), np.array(f["geometry"]["coordinates"][-1][:2]) - (OX, OY)
        ax = (B - A) / np.linalg.norm(B - A)
        cap = math.radians(p["cap_bandes_deg"])
        u = np.array([math.cos(cap), math.sin(cap)])
        nb = int(p.get("nb_emplacements") or p["nb_bandes"]) - len(p.get("coupures") or [])
        bandes = []
        for pc, fs in sorted(par[i].items()):
            Q = np.concatenate([g["P"][:, :2] for g in fs])
            # centroïde et axes d'inertie pondérés par l'aire projetée des triangles (le maillage n'est pas uniforme)
            w = np.array([g["aire"] * g["ny"] for g in fs])
            C = np.array([g["P"][:, :2].mean(0) for g in fs])
            c = (C * w[:, None]).sum(0) / w.sum()
            lu = np.ptp(Q @ u)
            lv = np.ptp(Q @ np.array([-u[1], u[0]]))
            cov = ((C - c).T * w) @ (C - c) / w.sum()
            ev, evec = np.linalg.eigh(cov)
            g = evec[:, -1]
            ang = math.degrees(math.acos(min(1.0, abs(float(g @ u)))))
            bandes.append((float((c - A) @ ax), lu, lv, ang))
        bandes.sort()
        pas = np.diff([b[0] for b in bandes])
        decoupe = bool(p.get("decoupes"))
        e = {"id": i, "bandes": len(bandes), "attendues": nb,
             "pas_ecart_max_m": round(float(np.abs(pas - p["pas_axe_m"]).max()), 4) if len(pas) else None,
             "angle_max_deg": round(max(b[3] for b in bandes), 3) if bandes else None,
             "longueur_ecart_max_m": round(max(abs(b[1] - p["longueur_bande_m"]) for b in bandes), 4) if bandes else None,
             "largeur_ecart_max_m": round(max(abs(b[2] - p["largeur_bande_m"]) for b in bandes), 4) if bandes else None,
             "decoupes": decoupe}
        ok = (e["bandes"] == nb and (e["pas_ecart_max_m"] or 0) <= 0.03 and (e["angle_max_deg"] or 0) <= 3.0
              and (decoupe or ((e["longueur_ecart_max_m"] or 0) <= 0.2 and (e["largeur_ecart_max_m"] or 0) <= 0.02)))
        e["ok"] = ok
        if not ok:
            defauts.append(i)
        res.append(e)
    return {"regle": "VAL-ZEB-003", "zebras": len(res), "defauts": defauts, "detail": res,
            "tolerances": {"pas_m": 0.03, "angle_deg": 3, "longueur_m": 0.2, "largeur_m": 0.02}}


def poser(q, o, cap, e=1.0):
    ey = np.array([math.cos(math.radians(cap)), math.sin(math.radians(cap))])
    ex = np.array([ey[1], -ey[0]])
    q = np.asarray(q, float) * e
    return o + q[:, :1] * ex + q[:, 1:2] * ey


def controle_symboles(points, desc, spec):
    """Instances : gabarit posé (origine, cap des points) contre le contour décrit (VAL-FLE-001)."""
    d_or, d_cap, d_cont, lignes = [], [], [], []
    for pt in points["points"]:
        p = desc[pt["id"]]["properties"]
        g = desc[pt["id"]]["geometry"]
        x = pt["x"]
        q = pt["q"]                                       # [x, y, z, w] local
        yaw = math.degrees(math.atan2(2 * (q[3] * q[2] + q[0] * q[1]), 1 - 2 * (q[1] ** 2 + q[2] ** 2)))
        dcap = abs((yaw - p["pose"]["cap_deg"] + 180) % 360 - 180)
        d_cap.append(dcap)
        if x["genre"] != "gabarit":
            continue
        gab = spec["gabarits"][p["gabarit"]]
        e = float(p.get("echelle") or 1.0)
        anneaux = [gab["polygone"]] + gab.get("trous", []) + [v["polygone"] for _, v in sorted((gab.get("parties") or {}).items())
                                                             if isinstance(v, dict) and "polygone" in v]
        o = np.array(pt["p"][:2])
        posees = [poser(r, o, p["pose"]["cap_deg"], e) for r in anneaux]
        bord = np.concatenate([np.r_[r, r[:1]] for r in posees])
        decrits = np.concatenate([np.array(r)[:, :2] - (OX, OY) for r in
                                  (g["coordinates"] if g["type"] == "Polygon" else [r for pp in g["coordinates"] for r in pp])])
        dm = float(dist_polyligne(decrits, bord).max())
        d_cont.append(dm)
        # origine : centroïde décrit contre centroïde du gabarit posé (sommets)
        d_or.append(float(np.linalg.norm(decrits.mean(0) - bord[:-1].mean(0))) if p["gabarit"] != "VELO" else 0.0)
        lignes.append((pt["id"], p["gabarit"], round(dm, 4), round(dcap, 3)))
    return {"regle": "VAL-FLE-001", "instances": len(points["points"]), "ecart_cap_deg": stat(d_cap, 3),
            "ecart_contour_gabarit_m": stat(d_cont), "pire": sorted(lignes, key=lambda t: -t[2])[:8],
            "tolerances": {"origine_p95_m": 0.10, "cap_deg": 2.0},
            "note": "contour décrit (levé GAM, plan, ortho) contre gabarit IISR posé à l'origine et au cap de l'instance"}


def controle_drape(geos, niv, points):
    """Dessus de la peinture (faces horizontales) contre le modèle : z - épaisseur - z_modèle(région de la pièce),
    et région propriétaire de chaque sommet (marches de bordure franchies)."""
    out = {}
    for nom, geo in geos.items():
        reg = geo.findPrimAttrib("pj_region") is not None
        X, Y, Z, R = [], [], [], []
        vus = set()
        for pr in geo.prims():
            if pr.normal()[1] < 0.9:
                continue
            r = pr.attribValue("pj_region") if reg else -1
            for v in pr.vertices():
                pt = v.point()
                if pt.number() in vus:
                    continue
                vus.add(pt.number())
                P = pt.position()
                X.append(P[0]); Y.append(-P[2]); Z.append(P[1]); R.append(r)
        X, Y, Z, R = map(np.asarray, (X, Y, Z, R))
        zp = niv.z(X, Y)
        zr = zp.copy()
        for r in np.unique(R):
            if r < 0:
                continue
            niv.region[f"__r{r}"] = int(r)
            m = R == r
            zr[m] = niv.z(X[m], Y[m], f"__r{r}")
        d = Z - EPAISSEUR - zr
        ok = np.isfinite(d)
        dp = np.abs(Z - EPAISSEUR - zp)
        okp = np.isfinite(dp)
        out[nom] = {"sommets": int(len(Z)), "ecart_modele_region_m": stat(np.abs(d[ok]), 5),
                    "hors_modele": int((~ok).sum()),
                    "sommets_sur_marche_2cm": int((dp[okp] > 0.02).sum()),
                    "part_sur_marche": round(float((dp[okp] > 0.02).mean()), 5) if okp.any() else 0.0}
    P = np.array([p["p"] for p in points["points"]])
    zi = niv.z(P[:, 0], P[:, 1])
    di = np.abs(P[:, 2] - zi)
    out["instances_symboles"] = {"points": int(len(P)), "ecart_origine_modele_m": stat(di[np.isfinite(di)], 5)}
    return {"regle": "TQ-SOL-013 / CF-26 (un seul modèle de Z) ; MQ-DET-010", "par_branche": out}


def comparer_ancien(geos, points, desc):
    """Ancienne fabrication numpy (fabrique/marquages.usda, description antérieure) : entités communes."""
    from pxr import Usd, UsdGeom
    st = Usd.Stage.Open(str(ANCIEN))
    anc = collections.defaultdict(lambda: [0.0, np.zeros(2)])
    for pr in st.Traverse():
        if not pr.IsA(UsdGeom.Mesh):
            continue
        m = UsdGeom.Mesh(pr)
        P = np.array(m.GetPointsAttr().Get())
        cnt = np.array(m.GetFaceVertexCountsAttr().Get())
        idx = np.array(m.GetFaceVertexIndicesAttr().Get())
        ids = UsdGeom.PrimvarsAPI(pr).GetPrimvar("id").Get()
        assert (cnt == 3).all()
        T = P[idx.reshape(-1, 3)]
        a = 0.5 * np.abs(np.cross(T[:, 1, :2] - T[:, 0, :2], T[:, 2, :2] - T[:, 0, :2]))
        c = T[:, :, :2].mean(1)
        for k, i in enumerate(ids):
            e = anc[str(i).split("/")[0]]
            e[0] += a[k]
            e[1] = e[1] + a[k] * c[k]
    neuf = collections.defaultdict(lambda: [0.0, np.zeros(2)])
    for nom, geo in geos.items():
        for f in faces(geo):
            if f["ny"] > 0.1:
                a = f["aire"] * f["ny"]
                e = neuf[f["id"]]
                e[0] += a
                e[1] = e[1] + a * f["P"][:, :2].mean(0)
    for pt in points["points"]:
        x = pt["x"]
        neuf[pt["id"]] = [None, np.array(pt["p"][:2])]
    communs = sorted(set(anc) & set(neuf))
    dc, ra = [], []
    gros = []
    for i in communs:
        a_o, c_o = anc[i]
        a_n, c_n = neuf[i]
        c_o = c_o / max(a_o, 1e-12)
        if a_n is None:                                   # instance : origine du gabarit, pas un centroïde
            continue
        c_n = c_n / max(a_n, 1e-12)
        d = float(np.linalg.norm(c_o - c_n))
        dc.append(d)
        ra.append(a_n / max(a_o, 1e-9))
        if d > 0.5:
            gros.append((i, round(d, 3)))
    par_classe = collections.Counter()
    for i in neuf:
        if i in desc:
            par_classe[desc[i]["properties"]["classe"]] += 1
    return {"ancienne": {"fichier": str(ANCIEN.relative_to(RACINE).as_posix()), "entites": len(anc)},
            "nouvelle": {"entites": len(neuf), "par_classe": dict(sorted(par_classe.items()))},
            "communes": len(communs), "seulement_ancienne": len(set(anc) - set(neuf)),
            "seulement_nouvelle": len(set(neuf) - set(anc)),
            "ecart_centroide_m": stat(dc), "rapport_aire_nouvelle_sur_ancienne": stat(ra, 3),
            "deplacees_plus_50cm": sorted(gros, key=lambda t: -t[1])[:15],
            "note": "l'ancienne fabrication lisait la description 0.2 (597 entités, fantômes v1, axes v1) ; la nouvelle "
                    "lit la description 0.3 (GAM d'abord, géométrie régularisée)"}


def principal():
    hou.hipFile.load(str(HIP), suppress_save_prompt=True, ignore_load_warnings=True)
    O.installer_tout()
    hou.hscript(f'set -g PJ_DESCRIPTION = "{DESCRIPTION.as_posix()}"')
    hou.hscript(f'set -g PJ_SORTIE = "{SORTIE.as_posix()}"')
    hou.hscript("varchange")
    desc = {f["properties"]["id"]: f for f in json.load(open(DESCRIPTION / "marquages.geojson", encoding="utf-8"))["features"]}
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    mods = {k: (v["trait_m"], v["vide_m"]) for k, v in spec["modulations"]["table"].items()}
    g = "/obj/paquet_jardin/fab_"
    geos = {b: hou.node(g + b).geometry() for b in ("marquages_lignes", "passages", "symboles", "zones")}
    points = json.loads((SORTIE / "points" / "symboles.json").read_text(encoding="utf-8"))
    niv = Nivellement(DESCRIPTION)
    noeuds = {}
    for t in ("marquage_solide", "gabarits_iisr", "marquage_ligne", "passage_pieton", "symbole_iisr", "marquage_zone"):
        noeuds[O.nom_type(t)] = O.compter_noeuds(O.nom_type(t))
    ctl = {"schema": "pj_marquages_controles/0.1",
           "hda": noeuds,
           "lignes": controle_lignes(geos["marquages_lignes"], desc, mods),
           "zebras": controle_zebras(geos["passages"], desc),
           "symboles": controle_symboles(points, desc, spec),
           "symboles_hda": geos["symboles"].attribValue("pj_symboles_controles"),
           "drape": controle_drape(geos, niv, points),
           "solide": {b: geo.attribValue("pj_marquage_controles") for b, geo in geos.items()},
           "ancienne_fabrication": comparer_ancien(geos, points, desc)}
    f = SORTIE / "controle" / "marquages_controles.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(ctl, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)),
                 encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in ctl.items() if k not in ("zebras",)}, ensure_ascii=False, indent=1,
                     default=str)[:9000])
    print("zebras", ctl["zebras"]["defauts"])
    return 0


if __name__ == "__main__":
    sys.exit(principal())
