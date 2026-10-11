"""Précision intrinsèque de la méthode sur images synthétiques à 5 cm (vérité connue).

Rendu : couverture exacte des gabarits IISR (sur-échantillonnage x8) à une pose tirée au hasard (graine fixe,
décalage sous-pixel, cap quelconque), enrobé 150 DN / peinture 225 DN (usée : 185 DN), flou gaussien sigma
0,7 px (FTM typique d'une ortho 5 cm), bruit gaussien sigma 4 DN, compression JPEG qualité 85 ; puis la même chaîne
que sur l'ortho (detection -> fleches / zebras / lignes). Erreurs mesurées : origine (m), cap (°), largeur et pas
des bandes, largeur et extrémités des tirets.
"""
from __future__ import annotations

import io
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import commun_pilote as C  # noqa: E402
import detection as D  # noqa: E402
import fleches as F  # noqa: E402
import lignes as LG  # noqa: E402
import zebras as Z  # noqa: E402

TAILLE = 16.0          # m
GEO = (1000.0, 1000.0 + TAILLE)


def rendre(polys, rng, peinture=225.0, fond=150.0, sigma=0.7, bruit=4.0, q=85):
    n = int(TAILLE / C.PX)
    cov = C.rasteriser(polys, GEO, (n, n), ss=8)
    img = fond + (peinture - fond) * cov
    # texture d'enrobé (bruit spatial basse fréquence)
    tex = np.asarray(Image.fromarray((rng.normal(0, 1, (n // 8, n // 8)) * 40 + 128).clip(0, 255).astype(np.uint8)).resize((n, n), Image.BICUBIC), np.float32) - 128
    img = img + 0.15 * tex
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))
    a = np.asarray(im, np.float32) + rng.normal(0, bruit, (n, n))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q)
    return np.asarray(Image.open(buf).convert("RGB"))


def essai_fleches(rng, types=("TD", "TAG", "TD_TAD", "TRIDENT"), n=8, usee=False):
    out = []
    for t in types:
        for _ in range(n):
            cap = rng.uniform(0, 2 * math.pi)
            ox, oy = GEO[0] + 8 + rng.uniform(-0.5, 0.5), GEO[1] - 8 + rng.uniform(-0.5, 0.5)
            polys = F.gabarit(t)
            ctr = F.centre_gabarit(polys)
            # pose par l'origine IISR : centre du gabarit placé en conséquence
            c_l93 = C.poser(np.array([ctr]), ox, oy, cap)[0]
            vrai = F.poser_gabarit(polys, c_l93[0], c_l93[1], cap, 1, 1, ctr)
            rgb = rendre(vrai, rng, peinture=185.0 if usee else 225.0)
            det = D.detecter(rgb, GEO)
            cands = sorted(F.candidats(det), key=lambda d: -d["aire_m2"])
            if not cands:
                out.append({"type": t, "trouve": False})
                continue
            a = F.ajuster(cands[0], det, GEO)
            e = math.hypot(a["origine_l93"][0] - ox, a["origine_l93"][1] - oy)
            de = math.degrees((math.radians(a["cap_trigo_deg"]) - cap + math.pi) % (2 * math.pi) - math.pi)
            out.append({"type": t, "trouve": True, "type_ok": a["type"] == t, "erreur_origine_m": e, "erreur_cap_deg": de,
                        "iou": a["iou_norme"]})
    return out


def essai_zebras(rng, n=6, usee=False):
    out = []
    for _ in range(n):
        th = rng.uniform(0, math.pi)
        pas = rng.choice([1.0, 1.1, 1.2])
        Lb = rng.uniform(2.5, 4.0)
        cx, cy = GEO[0] + 8 + rng.uniform(-0.3, 0.3), GEO[1] - 8 + rng.uniform(-0.3, 0.3)
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        polys, centres = [], []
        for k in range(6):
            v = (k - 2.5) * pas
            c = np.array([cx, cy]) + v * ev
            centres.append(c)
            Q = [c + su * Lb / 2 * eu + sv * 0.25 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            polys.append([np.array(Q)])
        rgb = rendre(polys, rng, peinture=185.0 if usee else 225.0)
        det = D.detecter(rgb, GEO)
        gr = Z.regrouper(D.germes_zebra(det))
        ps = [p for g in gr for p in Z.mesurer_passage(g, det, GEO)]
        if not ps:
            out.append({"trouve": False})
            continue
        p = max(ps, key=lambda p: p["n_bandes"])
        bands = Z.polygones_passage(p, regularise=False)
        errs = []
        for b in bands:
            c = np.array(b["centre"])
            errs.append(min(abs((c - cc) @ ev) for cc in centres))
        out.append({"trouve": True, "n_bandes": p["n_bandes"], "erreur_pas_m": p["pas_m"] - pas,
                    "erreur_largeur_m": p["largeur_mediane_m"] - 0.5, "erreur_longueur_m": p["longueur_mediane_m"] - Lb,
                    "erreur_angle_deg": math.degrees(C.ecart_axial(p["theta_rad"], th)),
                    "erreur_centre_travers_rms_m": float(np.sqrt(np.mean(np.square(errs))))})
    return out


def essai_tirets(rng, n=8, largeur=0.15, usee=False):
    out = []
    for _ in range(n):
        th = rng.uniform(0, math.pi)
        cx, cy = GEO[0] + 8 + rng.uniform(-0.3, 0.3), GEO[1] - 8 + rng.uniform(-0.3, 0.3)
        eu = np.array([math.cos(th), math.sin(th)])
        ev = np.array([-math.sin(th), math.cos(th)])
        Q = [np.array([cx, cy]) + su * 1.5 * eu + sv * largeur / 2 * ev for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        rgb = rendre([[np.array(Q)]], rng, peinture=185.0 if usee else 225.0)
        det = D.detecter(rgb, GEO)
        tr = [d for d in det["comps"] if d["classe"] == "trait"]
        if not tr:
            out.append({"trouve": False})
            continue
        m = LG.mesurer_trait(max(tr, key=lambda d: d["aire_m2"]), det, GEO)
        if m is None:
            out.append({"trouve": False})
            continue
        A = np.asarray(m["axe_l93"])
        lat = float(np.mean([(q - np.array([cx, cy])) @ ev for q in A]))
        ends = sorted([(np.array(m["debut"]) - [cx, cy]) @ eu, (np.array(m["fin"]) - [cx, cy]) @ eu])
        out.append({"trouve": True, "erreur_largeur_m": m["largeur_m"] - largeur, "erreur_laterale_m": lat,
                    "erreur_extremites_m": [ends[0] + 1.5, ends[1] - 1.5], "erreur_longueur_m": m["longueur_m"] - 3.0})
    return out


def resume(vals):
    v = np.abs(np.asarray([x for x in vals if x is not None and np.isfinite(x)], float))
    if not len(v):
        return None
    return {"n": int(len(v)), "moyenne_abs": float(v.mean()), "p95_abs": float(np.percentile(v, 95)), "max_abs": float(v.max())}


def main():
    rng = np.random.default_rng(20261011)
    res = {"methode": __doc__.strip()}
    for usee in (False, True):
        k = "usee" if usee else "neuve"
        fl = essai_fleches(rng, usee=usee)
        zb = essai_zebras(rng, usee=usee)
        tt = essai_tirets(rng, usee=usee)
        res[k] = {
            "fleches": {"essais": len(fl), "trouvees": sum(1 for f in fl if f["trouve"]),
                        "type_correct": sum(1 for f in fl if f.get("type_ok")),
                        "erreur_origine_m": resume([f.get("erreur_origine_m") for f in fl]),
                        "erreur_cap_deg": resume([f.get("erreur_cap_deg") for f in fl]),
                        "iou": resume([f.get("iou") for f in fl]), "detail": fl},
            "zebras": {"essais": len(zb), "trouves": sum(1 for z in zb if z["trouve"]),
                       "erreur_pas_m": resume([z.get("erreur_pas_m") for z in zb]),
                       "erreur_largeur_m": resume([z.get("erreur_largeur_m") for z in zb]),
                       "erreur_longueur_m": resume([z.get("erreur_longueur_m") for z in zb]),
                       "erreur_angle_deg": resume([z.get("erreur_angle_deg") for z in zb]),
                       "erreur_centre_travers_m": resume([z.get("erreur_centre_travers_rms_m") for z in zb]), "detail": zb},
            "tirets_015": {"essais": len(tt), "trouves": sum(1 for t in tt if t["trouve"]),
                           "erreur_largeur_m": resume([t.get("erreur_largeur_m") for t in tt]),
                           "erreur_laterale_m": resume([t.get("erreur_laterale_m") for t in tt]),
                           "erreur_extremites_m": resume([e for t in tt for e in t.get("erreur_extremites_m", [])]), "detail": tt},
        }
    C.ecrire_json(C.SORTIE / "pilote_synthetique.json", res)
    return res


if __name__ == "__main__":
    import json
    r = main()
    for k in ("neuve", "usee"):
        print(k, json.dumps({f: {kk: vv for kk, vv in v.items() if kk != "detail"} for f, v in r[k].items()}, ensure_ascii=False, indent=1))
