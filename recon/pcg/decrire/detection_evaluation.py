"""Précision et rappel des détecteurs (plan 2025, ortho 2022) mesurés contre le levé GAM 2026 pris comme vérité terrain,
dans les zones couvertes par le levé (VAL-FLE-001, VAL-ZEB-003, VAL-LIG-002 ; FUS-ASS-003 pour l'appariement).

Usage :
    python recon/pcg/decrire/detection_evaluation.py [--sortie FICHIER.json]
Protocole :
- détecteurs lancés sur TOUT le raster (sans filtre d'admissibilité) ; on n'évalue chaque raster que là où il est
  admissible (FUS-SRC-001 : plan 2025 en zone refaite ou neuve, ortho 2022 en zone conservée ou refaite à l'identique),
  sinon la « vérité » 2026 diffère légitimement de l'image ;
- zone couverte par le levé : points à moins de 6 m d'une polyligne GAM de marquage ;
- flèches : appariement à 1,0 m et 15° (2,0 m sur le plan, projet), type correct compté à part ;
- zébras : centres à moins de 2,0 m ou emprises qui se recouvrent ;
- lignes : longueur peinte (échantillons de 0,25 m) à moins de 0,30 m d'une partie peinte d'une ligne GAM quasi parallèle,
  sur les bords détectables (deux voies roulables) ; précision = part détectée confirmée par le GAM, rappel = part GAM
  retrouvée.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_fleches as DF  # noqa: E402
import detection_lignes as DL  # noqa: E402
import detection_zebras as DZ  # noqa: E402
import marquages_commun as M  # noqa: E402
import marquages_sources as S  # noqa: E402
import xodr_echantillonne as X  # noqa: E402
from commun import SORTIE, arrondi, densifier, distance_segments, ecrire_json  # noqa: E402

COUVERTURE_M = 6.0


def _couverture():
    segs = [(P[:-1], P[1:]) for P in M.gam_lin() if len(P) >= 2]
    A = np.vstack([a for a, _ in segs])
    B = np.vstack([b for _, b in segs])

    def f(Q):
        d, _, _ = distance_segments(np.atleast_2d(Q), A, B)
        return d <= COUVERTURE_M
    return f


def _admissible(src, Q):
    return np.array([S.admissible(src, e) for e in S.etat_zone(np.atleast_2d(Q))], bool)


def evaluer(reseau=None):
    import marquages_gam_entites as GE
    import marquages_symboles as SY
    import marquages_fusion as FU
    reseau = reseau or X.lire_xodr()
    loc = SY.Localisateur(reseau)
    gam, _ = GE.entites(reseau, loc)
    couvert = _couverture()
    out = {"protocole": __doc__.split("Protocole :")[1].strip(), "fleches": {}, "zebras": {}, "lignes": {}}
    gt_f = [e for e in gam if e["classe"] == "fleche"]
    gt_z = [e for e in gam if e["classe"] == "passage" and e["type"] == "zebra"]
    gt_l = FU.preparer_refs([e for e in gam if e["classe"] == "ligne"])
    for src in ("plan2025", "ortho2022"):
        # --- flèches
        det = DF.detecter(reseau, src, toutes_zones=True)
        det = [d for d in det if _admissible(src, d["origine"][None])[0] and couvert(d["origine"][None])[0]]
        gt = [e for e in gt_f if _admissible(src, np.asarray(e["pose"]["origine_local"])[None])[0]]
        porte = 2.0 if src == "plan2025" else 1.0
        C = np.full((len(det), len(gt)), np.inf)
        for i, d in enumerate(det):
            for j, g in enumerate(gt):
                dd = float(np.hypot(*(d["origine"] - np.asarray(g["pose"]["origine_local"]))))
                if dd <= porte and S.angle_diff(d["cap_deg"], g["pose"]["cap_deg"]) <= 15.0:
                    C[i, j] = dd
        pr = FU.hongrois(C)
        tp = len(pr)
        type_ok = sum(1 for i, j in pr if det[i]["gabarit"] == gt[j]["gabarit"])
        # même voie (écart latéral ≤ 1,0 m) à moins de 8 m en long : appariement de la fusion pour le plan (projet)
        C2 = np.full((len(det), len(gt)), np.inf)
        for i, d in enumerate(det):
            for j, g in enumerate(gt):
                v = d["origine"] - np.asarray(g["pose"]["origine_local"])
                ex, ey = M.axes_cap(g["pose"]["cap_deg"])
                if abs(float(v @ ex)) <= 1.0 and abs(float(v @ ey)) <= 8.0 and S.angle_diff(d["cap_deg"], g["pose"]["cap_deg"]) <= 15.0:
                    C2[i, j] = abs(float(v @ ey))
        pr2 = FU.hongrois(C2)
        out["fleches"][src + "_meme_voie_8m"] = {"vrais_positifs": len(pr2), "precision": round(len(pr2) / len(det), 3) if det else None,
                                                 "rappel": round(len(pr2) / len(gt), 3) if gt else None,
                                                 "type_correct": f"{sum(1 for i, j in pr2 if det[i]['gabarit'] == gt[j]['gabarit'])}/{len(pr2)}",
                                                 "ecart_long_m": [round(float(C2[i, j]), 2) for i, j in pr2]}
        out["fleches"][src] = {"detections": len(det), "verite_gam": len(gt), "vrais_positifs": tp,
                               "precision": round(tp / len(det), 3) if det else None, "rappel": round(tp / len(gt), 3) if gt else None,
                               "type_correct": f"{type_ok}/{tp}",
                               "ecart_position_m": [round(float(C[i, j]), 3) for i, j in pr]}
        # --- zébras
        dz = DZ.balayer(reseau, src, toutes_zones=True)
        dz = [d for d in dz if _admissible(src, d["xy"][None])[0] and couvert(d["xy"][None])[0]]
        gz = [e for e in gt_z if _admissible(src, e["geom"][1].mean(axis=0)[None])[0]]
        C = np.full((len(dz), len(gz)), np.inf)
        for i, d in enumerate(dz):
            for j, g in enumerate(gz):
                A, B = g["geom"][1][:2]
                from commun import projeter
                _, dd, _ = projeter(np.vstack([A, B]), d["xy"][None])
                if float(dd[0]) <= 2.0 + 0.5 * float(g["longueur_bande_m"]):
                    C[i, j] = float(dd[0])
        pr = FU.hongrois(C)
        out["zebras"][src] = {"detections": len(dz), "verite_gam": len(gz), "vrais_positifs": len(pr),
                              "precision": round(len(pr) / len(dz), 3) if dz else None,
                              "rappel": round(len(pr) / len(gz), 3) if gz else None,
                              "ecart_pas_m": [round(abs(dz[i]["pas_m"] - gz[j]["pas_axe_m"]), 3) for i, j in pr]}
        # --- lignes (bords détectables)
        dl = DL.lignes_bords(reseau, src, admissible_seul=False)
        tot_d = ok_d = 0.0
        refs_det = []
        chaines = {ch.cle: ch for ch, _, _ in DL.guides_detectables(reseau)}
        for d in dl:
            ch = chaines.get(d["chaine"])
            if ch is None:
                continue
            P = ch.axe(d["t_off"], d["s0"], d["s1"])
            e = {"id": f"D{len(refs_det)}", "classe": "ligne", "type": d["type"], "geom": ("LineString", P), "interruptions": [],
                 "trait_m": d.get("trait_m", 3.0), "vide_m": d.get("vide_m", 1.33), "phase_m": 0.0}
            q, t = FU.peint_ligne(e)
            if len(q) == 0:
                continue
            m = _admissible(src, q) & couvert(q)
            if not m.any():
                continue
            f, _, cv = FU.recouvrement(e, gt_l)
            tot_d += float(m.sum()) * 0.25
            ok_d += float((cv & m).sum()) * 0.25
            refs_det.append(e)
        FU.preparer_refs(refs_det)
        tot_g = ok_g = 0.0
        guides = [ch.axe(0.0, a, b) for ch, a, b in DL.guides_detectables(reseau)]
        GA = np.vstack([g[:-1] for g in guides])
        GB = np.vstack([g[1:] for g in guides])
        for g in gt_l:
            q, t = FU.peint_ligne(g)
            if len(q) == 0:
                continue
            dg, _, _ = distance_segments(q, GA, GB)
            m = _admissible(src, q) & (dg <= 0.5)
            if not m.any():
                continue
            f, _, cv = FU.recouvrement(g, refs_det)
            tot_g += float(m.sum()) * 0.25
            ok_g += float((cv & m).sum()) * 0.25
        out["lignes"][src] = {"longueur_detectee_m": round(tot_d, 1), "longueur_detectee_confirmee_m": round(ok_d, 1),
                              "precision": round(ok_d / tot_d, 3) if tot_d else None, "longueur_gam_m": round(tot_g, 1),
                              "longueur_gam_retrouvee_m": round(ok_g, 1), "rappel": round(ok_g / tot_g, 3) if tot_g else None}
    return arrondi(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", default=str(SORTIE / "evaluation_detection_marquages.json"))
    a = ap.parse_args()
    r = evaluer()
    ecrire_json(a.sortie, r)
    print(json.dumps({k: v for k, v in r.items() if k != "protocole"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
