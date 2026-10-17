# -*- coding: utf-8 -*-
"""Contrôles de la correction après contrôle (lot correction) : mesures indépendantes du code de fabrication et de
rendu (lecture des sorties seulement : npy, json, png).

    python recon/generateur/validation/controler_correction.py [SCENE ...] [--json FICHIER] [--avant DOSSIER]

1. Lisibilité de la vue de dessus (critère ajouté à côté de L2b-11, relecture adverse) : les faces du sol fabriqué
   (l2/sol_*.npy : classe de bande) et la peinture (l2b/peinture_*.npy, faces du dessus) sont projetées dans la grille
   de pixels de la vue de dessus (manifest_rendus.json : centre, largeur, m/px ; caméra quasi orthographique, +x à
   droite, +y en haut) ; masques érodés (3 px sol, 1 px peinture) ; luminance Rec. 709 des valeurs sRGB : médianes de
   l'enrobé (voies), du trottoir, de la peinture, de l'herbe ; écarts trottoir − enrobé et peinture − enrobé comparés à
   ceux de la référence de l'utilisateur (ref_carrefour_dessus, zones mesurées : 0,318 et 0,406) ; teinte et
   saturation de l'enrobé, teinte et écart-type de luminance de l'herbe.
2. Fil d'eau aux ralentisseurs : intervalles du caniveau déclarés (props des entités) et éléments posés
   (l2/elements.json : caniveaux, caniveaux à grille, avaloirs) : longueur du fil d'eau interrompue par file ; un
   retour de bordure sans caniveau déclaré (avancée) qui suit une file terminée par un avaloir est compté à part
   (« retours drainés ») ; une file fermée sans avaloir reste une interruption.
3. Liste des éléments de bordure (elements.json) : couverture de chaque file par ses éléments et joints ; trous > 2 cm.
4. Arbres posés (manifest_rendus.json, mesures sur les prototypes) contre le modèle : cartes de feuilles de 0,08 à
   0,15 m, rien sous le fût (gabarit RF-OSM-VEG-001), rayon du feuillage dans [0,85 ; 1,05] × houppier, hauteur ≤ 1,02 H.
   Étape 1 (route seule, décision de l'utilisateur) : aucun arbre rendu, contrôle sans objet (reporté à l'étape 2).
5. Étape 1 — route seule : scène de rendu (scene_rendu.usda, manifest_rendus.json) sans rien hors de l'emprise de la
   route (ni arbres, ni relief, ni prairie de décor, ni prolongements, ni nuages), abords du modèle non rendus, socle
   neutre ; piste cyclable distincte de la chaussée en vue de dessus (RF-MA-PIS-009 : écart de luminance et ΔE76 CIELAB
   des médianes).
"""
from __future__ import annotations

import argparse
import colorsys
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ICI = Path(__file__).resolve().parent
GEN = ICI.parent
DEPOT = GEN.parents[1]
SORTIE = DEPOT / "recon" / "out" / "generateur"
REF_ECART = {"trottoir": 0.318, "marquage": 0.406}      # ref_carrefour_dessus (tmp/correction/mesure_photos.py)
# classes du sol au niveau de la chaussée (surfaces basses voisines des caniveaux)
CHAUSSEE_CL = {"voie_circulation", "voie_bus", "stationnement", "bande_cyclable", "zone_neutralisee", "accotement_revetu",
               "bande_derasee", "livraison"}
# supports admis (correction après le second contrôle) : BEV sur une surface piétonne ou un refuge, bandes de passage
# sur la chaussée ou une piste traversée (méthode : tmp/controle_route/m2_bev_sol.py)
SUPPORT_BEV = {"trottoir", "chemin_pieton", "terre_plein", "refuge", "quai_bus", "voie_verte"}
SUPPORT_PASSAGE = CHAUSSEE_CL | {"piste_cyclable"}
REF_ENROBE = 0.334
SUJET = {"S01": 50.0, "S02": 50.0, "S03": 38.0, "S04": 25.0, "S05": 25.0, "S06": 50.0, "S07": 40.0, "S08": 51.0,
         "S09": 62.0, "S10": 50.0, "S11": 51.4, "S12": 50.0}


def _lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def _r(x, n=4):
    return None if x is None else round(float(x), n)


def _lab(rgb):
    """sRGB (0-1) -> CIELAB (D65)."""
    c = np.asarray(rgb, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    X, Y, Z = M @ lin / np.array([0.95047, 1.0, 1.08883])

    def f(t):
        return np.cbrt(t) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))


# ------------------------------------------------------------------------------------------------ 1. lisibilité
def _faces(points, faces, comptes):
    off = 0
    for c in comptes:
        yield faces[off:off + c]
        off += c


def lisibilite(d: Path) -> dict | None:
    man_f = d / "rendus" / "manifest_rendus.json"
    png = d / "rendus" / "dessus.png"
    if not man_f.exists() or not png.exists():
        return None
    man = json.loads(man_f.read_text(encoding="utf-8"))
    cam = man["cameras"]["dessus"]
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
    H, W = img.shape[:2]
    if "centre_xy" in cam:
        cx, cy = cam["centre_xy"]
    else:                                                  # manifeste d'avant la correction : centre recalculé
        Ps = np.load(d / "l2" / "sol_points.npy")          # (sujet, milieu de l'emprise), comme rendu_l2b
        s_f = SUJET.get(d.name, float(Ps[:, 3].max()) / 2)
        tm = 0.5 * (Ps[:, 4].max() + Ps[:, 4].min())
        k = np.argmin(np.abs(Ps[:, 3] - s_f) + 0.1 * np.abs(Ps[:, 4] - tm))
        cx, cy = float(Ps[k, 0]), float(Ps[k, 1]) + (tm - float(Ps[k, 4]))
    mpp = cam["largeur_m"] / W

    def pix(x, y):
        return (x - cx) / mpp + W / 2.0, H / 2.0 - (y - cy) / mpp
    P = np.load(d / "l2" / "sol_points.npy")
    F = np.load(d / "l2" / "sol_faces.npy")
    C = np.load(d / "l2" / "sol_comptes.npy")
    A = np.load(d / "l2" / "sol_attributs.npy")
    voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    classes = voc["classe"]
    mats = voc["materiau_id"]
    groupes = {"enrobe": ("voie_circulation", "voie_bus"), "trottoir": ("trottoir",), "piste": ("piste_cyclable",)}
    herbes = ("gazon_tondu", "herbe_haute")
    calques = {k: Image.new("L", (W, H), 0) for k in ("enrobe", "trottoir", "piste", "herbe", "marquage", "autre")}
    dr = {k: ImageDraw.Draw(v) for k, v in calques.items()}
    abords_invisibles = man.get("etape") == 1          # étape 1 (route seule) : abords du modèle non rendus
    for f, a in zip(_faces(P, F, C), A):
        if a[0] != 0 or not a[3]:
            continue
        cl, mt = classes[a[4]], mats[a[5]]
        if abords_invisibles and cl == "abord":
            cl, mt = "socle", "sol_neutre"
        poly = [pix(P[i, 0], P[i, 1]) for i in f]
        cle = next((k for k, v in groupes.items() if cl in v), None)
        if cle is None and mt in herbes:
            cle = "herbe"
        for k in dr:                                       # la dernière face posée l'emporte
            dr[k].polygon(poly, fill=255 if k == (cle or "autre") else 0)
    pp = d / "l2b" / "peinture_points.npy"
    Q = FQ = CQ = AQ = None
    if pp.exists():
        Q = np.load(pp)
        FQ = np.load(d / "l2b" / "peinture_faces.npy")
        CQ = np.load(d / "l2b" / "peinture_comptes.npy")
        AQ = np.load(d / "l2b" / "peinture_attributs.npy")
        for f, a in zip(_faces(Q, FQ, CQ), AQ):
            if not a[2]:
                continue
            poly = [pix(Q[i, 0], Q[i, 1]) for i in f]
            for k in dr:
                dr[k].polygon(poly, fill=255 if k == "marquage" else 0)
    # peinture par classe (correction après le second contrôle : le passage seul, comme dans la référence) et surfaces
    # cachées sous les éléments (dessus des bordures et des caniveaux en vue de dessus)
    classes_p = {}
    if pp.exists():
        pvoc = json.loads((d / "l2b" / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
        icl, ide = pvoc["colonnes"].index("classe"), pvoc["colonnes"].index("dessus")
        for f, a in zip(_faces(Q, FQ, CQ), AQ):
            if not a[ide]:
                continue
            c = pvoc["classe"][a[icl]]
            if c not in classes_p:
                classes_p[c] = Image.new("L", (W, H), 0)
            ImageDraw.Draw(classes_p[c]).polygon([pix(Q[i, 0], Q[i, 1]) for i in f], fill=255)
    cache = Image.new("L", (W, H), 0)
    zones = {k: Image.new("L", (W, H), 0) for k in ("chaussee", "haut")}
    dcache, dz = ImageDraw.Draw(cache), {k: ImageDraw.Draw(v) for k, v in zones.items()}
    for f, a in zip(_faces(P, F, C), A):
        cl = classes[a[4]]
        poly = [pix(P[i, 0], P[i, 1]) for i in f]
        if cl in ("sous_bordure", "sous_element", "caniveau_releve"):
            dcache.polygon(poly, fill=255)
        elif a[3] and a[0] == 0 and cl in CHAUSSEE_CL:
            dz["chaussee"].polygon(poly, fill=255)
        elif a[3] and a[0] == 0 and cl not in ("abord", "mur"):
            dz["haut"].polygon(poly, fill=255)
    out = {"m_par_px": _r(mpp, 4)}
    Y = _lum(img)

    def stats(m):
        n = int(m.sum())
        if n < 50:
            return None
        rgb = img[m].mean(axis=0)
        h, l_, s_ = colorsys.rgb_to_hls(*rgb)
        med = np.median(img[m], axis=0)
        hv, sv, _v = colorsys.rgb_to_hsv(*med)
        return {"pixels": n, "Y_median": _r(np.median(Y[m])), "Y_sigma": _r(Y[m].std()),
                "teinte_deg": _r(h * 360, 1), "saturation_hls": _r(s_, 3), "lab_median": [_r(x, 2) for x in _lab(med)],
                "teinte_hsv_median_deg": _r(hv * 360, 1), "saturation_hsv_median": _r(sv, 3),
                "rgb_median": [_r(x, 4) for x in med]}
    for k, er in (("enrobe", 7), ("trottoir", 7), ("piste", 7), ("herbe", 7), ("marquage", 3)):
        m = np.asarray(calques[k].filter(ImageFilter.MinFilter(er)), dtype=np.uint8) > 0
        out[k] = stats(m)
    # peinture par classe : masque de la classe moins toute autre peinture, érodé d'1 px (contrôle indépendant)
    tout_p = np.asarray(calques["marquage"], dtype=np.uint8) > 0
    out["marquage_par_classe"] = {}
    for c, im in sorted(classes_p.items()):
        m = np.asarray(im.filter(ImageFilter.MinFilter(3)), dtype=np.uint8) > 0
        m &= tout_p
        s_ = stats(m)
        if s_:
            out["marquage_par_classe"][c] = s_
    # dessus des bordures (bande cachée à 3-12 cm d'une surface haute, loin de la chaussée) et des caniveaux (bande cachée
    # à 5-20 cm de la chaussée, loin des surfaces hautes) ; méthode du contrôle indépendant (tmp/controle_route/m1_dessus.py)
    try:
        from scipy import ndimage as ndi
        mc = np.asarray(cache, dtype=np.uint8) > 0
        d_h = ndi.distance_transform_edt(~(np.asarray(zones["haut"], dtype=np.uint8) > 0)) * mpp
        d_c = ndi.distance_transform_edt(~(np.asarray(zones["chaussee"], dtype=np.uint8) > 0)) * mpp
        out["bordure_dessus"] = stats(mc & (d_h <= 0.12) & (d_h >= 0.03) & (d_c > 0.2))
        out["caniveau_dessus"] = stats(mc & (d_c <= 0.20) & (d_c >= 0.05) & (d_h > 0.2))
    except ImportError:
        pass
    # ombre de la route sur le sol neutre (étape 1, second contrôle : trait sombre de 4 à 8 px au nord) : couronne de 0 à
    # 0,30 m hors de l'emprise de la route (faces du sol hors abords) contre le sol neutre à plus de 1 m
    if abords_invisibles:
        try:
            from scipy import ndimage as ndi
            emp = Image.new("L", (W, H), 0)
            de = ImageDraw.Draw(emp)
            for f, a in zip(_faces(P, F, C), A):
                if classes[a[4]] != "abord" and a[0] != 4:          # emprise : tout le sol hors abords et murs
                    de.polygon([pix(P[i, 0], P[i, 1]) for i in f], fill=255)
            me = np.asarray(emp, dtype=np.uint8) > 0
            couronne = ndi.binary_dilation(me, iterations=max(1, int(0.30 / mpp))) & ~ndi.binary_dilation(me, iterations=2)
            loin = ~ndi.binary_dilation(me, iterations=int(1.0 / mpp))
            if couronne.sum() > 100 and loin.sum() > 100:
                out["bord_sol"] = {"p5": _r(np.percentile(Y[couronne], 5)), "median": _r(np.median(Y[couronne])),
                                   "sol_loin_median": _r(np.median(Y[loin])),
                                   "ombre": _r(np.median(Y[loin]) - np.percentile(Y[couronne], 5))}
        except ImportError:
            pass
    e = out.get("enrobe")
    if e:
        out["ecart_classe_enrobe"] = {c: _r(v["Y_median"] - e["Y_median"]) for c, v in out["marquage_par_classe"].items()}
        out["ecart_classe_enrobe_atteint"] = {c: bool(v >= REF_ECART["marquage"] - 1e-9)
                                              for c, v in out["ecart_classe_enrobe"].items()}
    if e and out.get("piste"):
        out["ecart_piste_enrobe"] = _r(out["piste"]["Y_median"] - e["Y_median"])
        out["delta_e_piste_enrobe"] = _r(float(np.linalg.norm(np.subtract(out["piste"]["lab_median"], e["lab_median"]))), 2)
    for k in ("trottoir", "marquage"):
        if e and out.get(k):
            ec = out[k]["Y_median"] - e["Y_median"]
            out[f"ecart_{k}_enrobe"] = _r(ec)
            out[f"ecart_{k}_enrobe_atteint"] = bool(ec >= REF_ECART[k] - 1e-9)
    return out


# ------------------------------------------------------------------------------------------------ 2. fil d'eau
def _iv_props(props: str, cle: str) -> list:
    try:
        d = json.loads(props or "{}")
    except ValueError:
        return []
    return [tuple(x) for x in (d.get(cle) or {}).get("intervalles", [])]


def _union(iv):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + 0.02:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def fil_eau(d: Path) -> dict:
    ent = json.loads((d / "l2" / "entites.json").read_text(encoding="utf-8"))
    el = json.loads((d / "l2" / "elements.json").read_text(encoding="utf-8"))
    files = []
    for e in ent:
        # caniveau déclaré, caniveau à grille et avaloirs (correction après le second contrôle : l'avaloir remplace le
        # caniveau qu'il occupe ; il fait partie de la file d'eau)
        dec = (_iv_props(e.get("props"), "caniveau") + _iv_props(e.get("props"), "caniveau_grille")
               + _iv_props(e.get("props"), "avaloirs"))
        if not dec:
            continue
        a0, b0 = min(x[0] for x in dec), max(x[1] for x in dec)
        pos = [(x["s0"], x["s1"]) for x in el if x["famille"] == "caniveau" and x.get("kind") == "element"
               and x.get("bordure") == e["id"]]
        u = _union(pos)
        trous = []
        cur = a0
        for a, b in u:
            if a > cur + 0.02:
                trous.append((_r(cur, 3), _r(a, 3)))
            cur = max(cur, b)
        if b0 > cur + 0.02:
            trous.append((_r(cur, 3), _r(b0, 3)))
        # un trou hors de tout caniveau déclaré (retour de bordure : avancée, îlot) qui suit une file de caniveau
        # terminée par une grille d'avaloir n'interrompt pas l'écoulement (la file a son exutoire) ; tout autre trou
        # (élément manquant dans un caniveau déclaré, caniveau coupé par un ralentisseur, file fermée sans avaloir) compte
        decl = _union(dec)
        avs = [(x["s0"], x["s1"]) for x in el if x.get("type") == "avaloir" and x.get("bordure") == e["id"]]
        draines, comptes = [], []
        for a, b in trous:
            hors = all(b <= p + 0.02 or a >= q - 0.02 for p, q in decl)
            fin = any(abs(q - a) <= 0.02 for p, q in decl)
            exu = any(abs(y - a) <= 0.05 for _x, y in avs)
            (draines if (hors and fin and exu) else comptes).append((a, b))
        files.append({"bordure": e["id"], "etendue": [_r(a0, 3), _r(b0, 3)], "interruptions": comptes,
                      "longueur_interrompue_m": _r(sum(b - a for a, b in comptes), 3),
                      "retours_draines": draines, "longueur_retours_draines_m": _r(sum(b - a for a, b in draines), 3),
                      "grilles": [(_r(x["s0"], 3), _r(x["s1"], 3)) for x in el if x.get("type") == "grille" and x.get("bordure") == e["id"]],
                      "avaloirs": len(avs)})
    return {"files": files, "longueur_interrompue_m": _r(sum(f["longueur_interrompue_m"] for f in files), 3),
            "longueur_retours_draines_m": _r(sum(f["longueur_retours_draines_m"] for f in files), 3),
            "grilles": sum(len(f["grilles"]) for f in files), "avaloirs": sum(f["avaloirs"] for f in files)}


# ------------------------------------------------------------------------------------------------ 3. éléments
def couverture_bordures(d: Path) -> dict:
    ent = {e["id"]: e for e in json.loads((d / "l2" / "entites.json").read_text(encoding="utf-8"))}
    el = json.loads((d / "l2" / "elements.json").read_text(encoding="utf-8"))
    files = []
    for kid, e in sorted(ent.items()):
        L = float(e["niv_s"][-1]) if e.get("niv_s") else 0.0
        pos = sorted((x["s0"], x["s1"]) for x in el if x["famille"] == "bordure" and x.get("bordure") == kid)
        cur, trous = 0.0, []
        for a, b in pos:
            if a > cur + 0.02:
                trous.append((_r(cur, 3), _r(a, 3)))
            cur = max(cur, b)
        if L > cur + 0.02:
            trous.append((_r(cur, 3), _r(L, 3)))
        sm = [x for x in el if x["famille"] == "bordure" and x.get("bordure") == kid and x.get("kind") == "element"
              and x.get("sur_mesure")]
        files.append({"bordure": kid, "longueur_m": _r(L, 3), "trous": trous,
                      "longueur_trous_m": _r(sum(b - a for a, b in trous), 3), "pieces_sur_mesure": len(sm),
                      "longueur_sur_mesure_m": _r(sum(x["longueur"] for x in sm), 3)})
    return {"files": files, "longueur_trous_m": _r(sum(f["longueur_trous_m"] for f in files), 3),
            "pieces_sur_mesure": sum(f["pieces_sur_mesure"] for f in files),
            "longueur_sur_mesure_m": _r(sum(f["longueur_sur_mesure_m"] for f in files), 3)}


# ------------------------------------------------------------------------------------------------ 4. arbres
def arbres(d: Path) -> dict | None:
    f = d / "rendus" / "manifest_rendus.json"
    if not f.exists():
        return None
    man = json.loads(f.read_text(encoding="utf-8"))
    out = []
    for g in man.get("arbres", []):
        sp = g["gabarit"]
        for k, m in enumerate(g["prototypes"]):
            ok_carte = m["cartes"] == 0 or (m["carte_min_m"] >= 0.08 - 1e-6 and m["carte_max_m"] <= 0.15 + 1e-6)
            ok_fut = (m["feuilles_bas_m"] is None or m["feuilles_bas_m"] >= sp["fut"] - 0.05) and m["branches_bas_m"] >= sp["fut"] - 0.05
            rr = m["rayon_feuillage_m"] / sp["houppier"] if m["cartes"] else None
            ok_r = rr is None or 0.85 <= rr <= 1.05
            ok_h = m["hauteur_m"] <= 1.02 * sp["hauteur"]
            out.append({"groupe": g["groupe"], "prototype": f"v{k}", "gabarit": {x: sp[x] for x in ("asset", "hauteur", "fut", "houppier")},
                        "mesures": m, "rayon_rel": _r(rr, 3), "cartes_ok": ok_carte, "fut_ok": ok_fut, "rayon_ok": ok_r,
                        "hauteur_ok": ok_h, "saison": g.get("saison")})
    return {"prototypes": out, "conformes": sum(1 for x in out if x["cartes_ok"] and x["fut_ok"] and x["rayon_ok"] and x["hauteur_ok"]),
            "total": len(out)}


def route_seule(d: Path) -> dict | None:
    """Étape 1 : rien hors de l'emprise de la route dans la scène rendue (lecture de scene_rendu.usda et du manifeste)."""
    f = d / "rendus" / "manifest_rendus.json"
    u = d / "rendus" / "scene_rendu.usda"
    if not f.exists() or not u.exists():
        return None
    man = json.loads(f.read_text(encoding="utf-8"))
    txt = u.read_text(encoding="utf-8", errors="replace")
    interdits = {k: (f'def Xform "{k}' in txt or f'def PointInstancer "{k}' in txt or f'"{k}' in txt)
                 for k in ("Arbres_modele", "Arbres_decor", "Montagnes", "Prolongements")}
    interdits["Sol_decor"] = 'def Xform "Sol"' in txt.split('def Xform "Decor"', 1)[1] if 'def Xform "Decor"' in txt else False
    dec = man.get("decor") or {}
    abords = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8")).get("classe", [])
    sous = dec.get("faces_sous_ensembles") or {}
    return {"etape": man.get("etape"), "mode": dec.get("mode"), "objets_hors_emprise": sorted(k for k, v in interdits.items() if v),
            "nuages": (man.get("eclairage") or {}).get("ciel", {}).get("modele", ""),
            "abords_modele": "abord" in abords,
            "faces_abords_non_rendues": sum(v for k, v in sous.items() if k.startswith("abords/")),
            "socle": "Socle_jupe" in txt and "Socle_sol" in txt,
            "conforme": man.get("etape") == 1 and not any(interdits.values()) and "Socle_sol" in txt
            and "nuages" not in (man.get("eclairage") or {}).get("ciel", {}).get("modele", "nuages")
            and ("abord" not in abords or sum(v for k, v in sous.items() if k.startswith("abords/")) > 0)}


# ------------------------------------------------------------------------------- 6. correction après le second contrôle
def _carte_sol(d: Path, x0, y0, x1, y1, pas=0.02):
    """Classe du sol L2 visible pixellisée au pas `pas` sur la fenêtre (méthode de tmp/controle_route/m2_bev_sol.py) :
    (étiquettes, vocabulaire des classes, fonction (x, y) -> classe)."""
    P = np.load(d / "l2" / "sol_points.npy")
    F = np.load(d / "l2" / "sol_faces.npy")
    C = np.load(d / "l2" / "sol_comptes.npy")
    A = np.load(d / "l2" / "sol_attributs.npy")
    voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    ic, iv = voc["colonnes"].index("classe"), voc["colonnes"].index("visible")
    W, H = int((x1 - x0) / pas) + 1, int((y1 - y0) / pas) + 1
    lab = Image.new("I", (W, H), -1)
    dr = ImageDraw.Draw(lab)
    for f, a in zip(_faces(P, F, C), A):
        if not a[iv]:
            continue
        xs, ys = (P[f, 0] - x0) / pas, (P[f, 1] - y0) / pas
        if xs.max() < 0 or xs.min() > W or ys.max() < 0 or ys.min() > H:
            continue
        dr.polygon(list(zip(xs.tolist(), ys.tolist())), fill=int(a[ic]))
    lab = np.array(lab)

    def classe(x, y):
        i, j = int((y - y0) / pas), int((x - x0) / pas)
        if not (0 <= i < lab.shape[0] and 0 <= j < lab.shape[1]):
            return None
        v = lab[i, j]
        return voc["classe"][v] if v >= 0 else None
    return classe


def supports(d: Path) -> dict:
    """Classe du sol L2 sous chaque dalle de BEV (dans SUPPORT_BEV) et sous chaque face de bande de passage (dans
    SUPPORT_PASSAGE) : 0 exception attendue (correction après le second contrôle : BEV dans les bandes plantées de
    S_M20 et S_M27, bande de passage peinte sur le trottoir de S_M27)."""
    bev = json.loads((d / "l2" / "bev.json").read_text(encoding="utf-8"))
    pp = d / "l2b" / "peinture_points.npy"
    zones = []
    for v in bev.values():
        q = np.array([p for dl in v["dalles"] for p in dl])
        zones.append((q[:, 0].min(), q[:, 1].min(), q[:, 0].max(), q[:, 1].max()))
    pas_faces = []
    if pp.exists():
        Q = np.load(pp)
        FQ = np.load(d / "l2b" / "peinture_faces.npy")
        CQ = np.load(d / "l2b" / "peinture_comptes.npy")
        AQ = np.load(d / "l2b" / "peinture_attributs.npy")
        pv = json.loads((d / "l2b" / "peinture_vocabulaire.json").read_text(encoding="utf-8"))
        icl, ie = pv["colonnes"].index("classe"), pv["colonnes"].index("pj_entite")
        for f, a in zip(_faces(Q, FQ, CQ), AQ):
            if pv["classe"][a[icl]] == "passage":
                c = Q[f, :2].mean(axis=0)
                pas_faces.append((pv["pj_entite"][a[ie]], float(c[0]), float(c[1])))
    for _e, x, y in pas_faces:
        zones.append((x, y, x, y))
    res = {"bev": {}, "passages": {}, "exceptions_bev": 0, "exceptions_passage": 0, "dalles": 0, "faces_passage": 0}
    if not zones:
        return res
    z = np.array(zones)
    classe = _carte_sol(d, z[:, 0].min() - 1, z[:, 1].min() - 1, z[:, 2].max() + 1, z[:, 3].max() + 1)
    for k, v in bev.items():
        cnt = {}
        for dl in v["dalles"]:
            q = np.array(dl)
            c = classe(q[:, 0].mean(), q[:, 1].mean())
            cnt[c] = cnt.get(c, 0) + 1
        res["bev"][k] = cnt
        res["dalles"] += sum(cnt.values())
        res["exceptions_bev"] += sum(n for c, n in cnt.items() if c not in SUPPORT_BEV)
    for e, x, y in pas_faces:
        c = classe(x, y)
        r = res["passages"].setdefault(e, {})
        r[c] = r.get(c, 0) + 1
        res["faces_passage"] += 1
        res["exceptions_passage"] += 0 if c in SUPPORT_PASSAGE else 1
    return res


def elements_files(d: Path) -> dict:
    """Continuité de chaque file d'éléments (elements.json, par bordure et famille, joints exclus) : trous > 2 cm et
    recouvrements > 2 cm entre deux éléments d'une même file (méthode de tmp/controle_route/m4_continuite.py ; un
    avaloir doit remplacer le caniveau qu'il occupe) ; types des pièces de bordure (retours « raccord_vue », chartières)."""
    el = json.loads((d / "l2" / "elements.json").read_text(encoding="utf-8"))
    files, types = {}, {}
    for x in el:
        if x.get("famille") == "bordure":
            types[x.get("type")] = types.get(x.get("type"), 0) + 1
        if x.get("type") == "joint":
            continue
        files.setdefault((x["bordure"], x["famille"]), []).append(x)
    rec, rec_m, tr_cani = [], 0.0, []
    for (b, fam), lst in sorted(files.items()):
        lst.sort(key=lambda x: (x["s0"], x["s1"]))
        for a, c in zip(lst, lst[1:]):
            g = c["s0"] - a["s1"]
            if g < -0.02:
                rec.append((f"{b}/{fam}", a["id"], a["type"], c["id"], c["type"], _r(-g, 3)))
                rec_m += -g
            if fam == "caniveau" and 0.02 < g < 0.5 and "avaloir" in (a["type"], c["type"]):
                tr_cani.append((f"{b}/{fam}", _r(a["s1"], 3), _r(c["s0"], 3)))
    return {"recouvrements": len(rec), "recouvrements_m": _r(rec_m, 3), "exemples": rec[:6],
            "trous_contre_avaloir": tr_cani[:6], "n_trous_contre_avaloir": len(tr_cani),
            "types_bordure": dict(sorted((str(k), v) for k, v in types.items())),
            "avaloirs": sum(1 for x in el if x.get("type") == "avaloir")}


def retours_types(d: Path) -> dict:
    """Pièces de bordure des retours transversaux à vue variable (intervalles « usage : retour » des entités) : typées
    « raccord_vue » (rôle « retour »), aucune typée « chartiere » (second contrôle : 52 retours d'avancée de S03 typés
    « chartiere », confondus au placement avec la chartière d'un abaissé)."""
    ent = json.loads((d / "l2" / "entites.json").read_text(encoding="utf-8"))
    el = json.loads((d / "l2" / "elements.json").read_text(encoding="utf-8"))
    ret = {e["id"]: [(iv["s0"], iv["s1"]) for iv in e["intervalles"] if iv.get("usage") == "retour"] for e in ent}
    n_ret, types = 0, {}
    for x in el:
        if x.get("famille") != "bordure" or x.get("kind") != "element":
            continue
        sm = 0.5 * (x["s0"] + x["s1"])
        if any(a - 1e-6 <= sm <= b + 1e-6 for a, b in ret.get(x.get("bordure"), [])):
            n_ret += 1
            types[x.get("type")] = types.get(x.get("type"), 0) + 1
    return {"pieces_de_retour": n_ret, "types": types, "chartieres_dans_un_retour": types.get("chartiere", 0)}


def vegetation_etape(d: Path) -> dict:
    v = json.loads((d / "l2" / "vegetation.json").read_text(encoding="utf-8"))
    if isinstance(v, dict):
        return {"format": v.get("schema"), "etape": v.get("etape"), "arbres": len(v.get("arbres", []))}
    return {"format": "liste", "etape": None, "arbres": len(v)}


def _lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def contraste_bev(d: Path) -> dict | None:
    """Contraste visuel de chaque BEV en vue de dessus (méthode de tmp/controle_route/m5_bev_contraste.py) : luminance
    relative linéaire de la BEV (médiane, masque érodé) et du revêtement voisin (couronne de 3 px à 0,30 m) ;
    C = |L1 − L2| / max(L1, L2) ; RF-MA-OBS-003 : 0,70 recherché, 0,40 acceptable."""
    man_f, png = d / "rendus" / "manifest_rendus.json", d / "rendus" / "dessus.png"
    if not man_f.exists() or not png.exists():
        return None
    try:
        from scipy import ndimage as ndi
    except ImportError:
        return None
    cam = json.loads(man_f.read_text(encoding="utf-8"))["cameras"]["dessus"]
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
    H, W = img.shape[:2]
    Yl = _lin(img) @ np.array([0.2126, 0.7152, 0.0722])
    bev = json.loads((d / "l2" / "bev.json").read_text(encoding="utf-8"))
    out = {}
    for k, v in bev.items():
        m = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(m)
        for q in v["dalles"]:
            q = np.array(q)
            px = W / 2 + (q[:, 0] - cam["centre_xy"][0]) / cam["m_par_px"]
            py = H / 2 - (q[:, 1] - cam["centre_xy"][1]) / cam["m_par_px"]
            dr.polygon(list(zip(px, py)), fill=255)
        m = np.array(m) > 0
        if m.sum() < 30:
            continue
        inner = ndi.binary_erosion(m, iterations=2)
        ring = ndi.binary_dilation(m, iterations=int(0.30 / cam["m_par_px"])) & ~ndi.binary_dilation(m, iterations=3)
        L1, L2 = float(np.median(Yl[inner])), float(np.median(Yl[ring]))
        out[k] = {"L_bev": _r(L1), "L_voisin": _r(L2), "contraste": _r(abs(L1 - L2) / max(L1, L2), 3),
                  "teinte": v.get("teinte"), "materiau_voisin": v.get("materiau_voisin")}
    return out


def _projeter(cam, res, X):
    """Point du monde -> pixel d'une caméra de rendu_l2b (_camera : lookAt œil -> cible, haut Z, ouverture 36 mm)."""
    o, c = np.array(cam["oeil_xyz"], float), np.array(cam["cible_xyz"], float)
    fw = c - o
    fw /= np.linalg.norm(fw)
    r = np.cross(fw, [0, 0, 1.0])
    r /= np.linalg.norm(r)
    u = np.cross(r, fw)
    v = np.asarray(X, float) - o
    z = v @ fw
    W, H = res
    k = cam["focale_mm"] / 36.0 * W
    return W / 2 + (v @ r) / z * k, H / 2 - (v @ u) / z * k, z


def teintes_conducteur(d: Path) -> dict | None:
    """Teinte et saturation rendues de l'enrobé et des faces vues des bordures dans la vue conducteur (correction après
    le second contrôle : enrobé à 17-19° et bordures neutres ou bleutées, photos 27-37° et 28-33°). Points projetés
    (camera du manifeste) : enrobé au milieu des voies (sol L2, classe voie, à plus de 0,4 m des limites de la voie), de 6
    à 30 m devant la caméra ; faces de bordure (files de niveaux.json) à mi-hauteur de la vue, 3 mm devant la face, de 4
    à 25 m, séparées en faces au soleil et à l'ombre (normale de la face vers le soleil)."""
    man_f, png = d / "rendus" / "manifest_rendus.json", d / "rendus" / "conducteur.png"
    if not man_f.exists() or not png.exists():
        return None
    man = json.loads(man_f.read_text(encoding="utf-8"))
    cam, res = man["cameras"]["conducteur"], man["resolutions"]["conducteur"]
    img = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
    Hh, Ww = img.shape[:2]
    az = math.radians(man["eclairage"]["soleil_azimut_deg"])
    soleil = np.array([math.cos(az), math.sin(az)])

    def lire(points):
        vals = []
        for X in points:
            px, py, z = _projeter(cam, res, X)
            if z > 0 and 2 <= px < Ww - 2 and 2 <= py < Hh - 2:
                vals.append(img[int(py), int(px)])
        return np.array(vals)

    def st(vals):
        if len(vals) < 20:
            return None
        med = np.median(vals, axis=0)
        h, s, _v = colorsys.rgb_to_hsv(*med)
        return {"points": len(vals), "Y_median": _r(float(_lum(med))), "teinte_deg": _r(h * 360, 1), "saturation": _r(s, 3)}
    P = np.load(d / "l2" / "sol_points.npy")
    F = np.load(d / "l2" / "sol_faces.npy")
    C = np.load(d / "l2" / "sol_comptes.npy")
    A = np.load(d / "l2" / "sol_attributs.npy")
    voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
    ic, iv = voc["colonnes"].index("classe"), voc["colonnes"].index("visible")
    ib = voc["colonnes"].index("bande")
    o = np.array(cam["oeil_xyz"])
    pts, bornes = [], {}
    for f, a in zip(_faces(P, F, C), A):
        if a[iv] and voc["classe"][a[ic]] in ("voie_circulation", "voie_bus"):
            b = int(a[ib])
            lo, hi = bornes.get(b, (1e9, -1e9))
            bornes[b] = (min(lo, float(P[f, 4].min())), max(hi, float(P[f, 4].max())))
            pts.append((b, P[f, :3].mean(axis=0), float(P[f, 4].mean())))
    sel = [X for b, X, t in pts if bornes[b][0] + 0.4 < t < bornes[b][1] - 0.4 and 6 < np.linalg.norm(X[:2] - o[:2]) < 30]
    out = {"enrobe": st(lire(sel))}
    niv = json.loads((d / "l2" / "niveaux.json").read_text(encoding="utf-8"))
    face = {"soleil": [], "ombre": []}
    for ch in niv["bordures"]:
        q = ch["points"]
        for a, b in zip(q, q[1:]):
            dx, dy = b["x"] - a["x"], b["y"] - a["y"]
            lg = math.hypot(dx, dy)
            if lg < 0.05 or a.get("vue", 0) < 0.08:
                continue
            n = np.array([dy, -dx]) / lg                   # face vers le côté bas (droite de la file)
            for u in np.arange(0.0, lg, 0.25):
                x, y = a["x"] + dx * u / lg, a["y"] + dy * u / lg
                X = np.array([x + 0.003 * n[0], y + 0.003 * n[1], a["pied"] + 0.5 * a["vue"]])
                dist = np.linalg.norm(X[:2] - o[:2])
                if 4 < dist < 25 and np.dot(n, (o[:2] - X[:2])) > 0:     # face tournée vers la caméra
                    face["soleil" if np.dot(n, soleil) > 0 else "ombre"].append(X)
    out["bordure_face_soleil"] = st(lire(face["soleil"]))
    out["bordure_face_ombre"] = st(lire(face["ombre"]))
    return out


def correlation_usure(dossiers: list[Path], fenetre=(44.0, 50.5), pas=0.025) -> dict:
    """Corrélation de la luminance de l'enrobé entre deux scènes au même (x, y) du monde (vue de dessus rééchantillonnée
    au pas de 2,5 cm sur x ∈ fenêtre, voies des deux scènes, sans peinture) ; correction après le second contrôle : la
    carte d'usure était lue en coordonnées du monde, sans décalage par scène (corrélation 0,67 à 0,80)."""
    vues = {}
    for d in dossiers:
        man_f, png = d / "rendus" / "manifest_rendus.json", d / "rendus" / "dessus.png"
        if not man_f.exists() or not png.exists():
            continue
        cam = json.loads(man_f.read_text(encoding="utf-8"))["cameras"]["dessus"]
        img = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
        Y = _lum(img)
        H, W = Y.shape
        mpp, (cx, cy) = cam["m_par_px"], cam["centre_xy"]
        P = np.load(d / "l2" / "sol_points.npy")
        F = np.load(d / "l2" / "sol_faces.npy")
        C = np.load(d / "l2" / "sol_comptes.npy")
        A = np.load(d / "l2" / "sol_attributs.npy")
        voc = json.loads((d / "l2" / "sol_vocabulaire.json").read_text(encoding="utf-8"))
        ic, iv = voc["colonnes"].index("classe"), voc["colonnes"].index("visible")
        mvoie = Image.new("L", (W, H), 0)
        dr = ImageDraw.Draw(mvoie)
        for f, a in zip(_faces(P, F, C), A):
            if a[iv] and voc["classe"][a[ic]] in ("voie_circulation", "voie_bus"):
                dr.polygon([((P[i, 0] - cx) / mpp + W / 2, H / 2 - (P[i, 1] - cy) / mpp) for i in f], fill=255)
        mp = Image.new("L", (W, H), 0)
        pp = d / "l2b" / "peinture_points.npy"
        if pp.exists():
            Q = np.load(pp)
            dq = ImageDraw.Draw(mp)
            for f in _faces(Q, np.load(d / "l2b" / "peinture_faces.npy"), np.load(d / "l2b" / "peinture_comptes.npy")):
                dq.polygon([((Q[i, 0] - cx) / mpp + W / 2, H / 2 - (Q[i, 1] - cy) / mpp) for i in f], fill=255)
        ok = (np.asarray(mvoie.filter(ImageFilter.MinFilter(9)), dtype=np.uint8) > 0) & \
             ~(np.asarray(mp.filter(ImageFilter.MaxFilter(9)), dtype=np.uint8) > 0)
        vues[d.name] = (Y, ok, mpp, cx, cy)
    xs = np.arange(fenetre[0], fenetre[1], pas)
    ys = np.arange(-6.0, 6.0, pas)
    gx, gy = np.meshgrid(xs, ys)
    ech = {}
    for n, (Y, ok, mpp, cx, cy) in vues.items():
        j = np.round((gx - cx) / mpp + Y.shape[1] / 2 - 0.5).astype(int)
        i = np.round(Y.shape[0] / 2 - (gy - cy) / mpp - 0.5).astype(int)
        dedans = (i >= 0) & (i < Y.shape[0]) & (j >= 0) & (j < Y.shape[1])
        i, j = np.clip(i, 0, Y.shape[0] - 1), np.clip(j, 0, Y.shape[1] - 1)
        ech[n] = (Y[i, j], ok[i, j] & dedans)
    noms = sorted(ech)
    paires = {}
    for a_ in range(len(noms)):
        for b_ in range(a_ + 1, len(noms)):
            ya, ma = ech[noms[a_]]
            yb, mb = ech[noms[b_]]
            m = ma & mb
            if m.sum() < 2000:
                continue
            u, v = ya[m] - ya[m].mean(), yb[m] - yb[m].mean()
            paires[f"{noms[a_]}/{noms[b_]}"] = {"pixels": int(m.sum()),
                                                  "correlation": _r(float((u * v).sum() / math.sqrt((u * u).sum() * (v * v).sum())), 3)}
    return {"fenetre_x": list(fenetre), "pas_m": pas, "paires": paires,
            "max": max((v["correlation"] for v in paires.values()), default=None)}


def controler(d: Path) -> dict:
    return {"scene": d.name, "lisibilite": lisibilite(d), "fil_eau": fil_eau(d), "bordures": couverture_bordures(d),
            "arbres": arbres(d), "route_seule": route_seule(d), "supports": supports(d), "elements": elements_files(d),
            "vegetation": vegetation_etape(d), "contraste_bev": contraste_bev(d), "conducteur": teintes_conducteur(d),
            "retours": retours_types(d)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--sortie", default=str(SORTIE))
    ap.add_argument("--json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    base = Path(a.sortie)
    noms = a.scenes or sorted(p.parent.parent.name for p in base.glob("*/l2/manifest_l2.json"))
    res = [controler(base / n) for n in noms]
    for r in res:
        L = r["lisibilite"] or {}
        print(f"{r['scene']} : enrobé {((L.get('enrobe') or {}).get('Y_median'))}, trottoir−enrobé {L.get('ecart_trottoir_enrobe')}, "
              f"peinture−enrobé {L.get('ecart_marquage_enrobe')}, herbe {((L.get('herbe') or {}).get('teinte_deg'))}° σ "
              f"{((L.get('herbe') or {}).get('Y_sigma'))} ; fil d'eau interrompu {r['fil_eau']['longueur_interrompue_m']} m "
              f"(grilles {r['fil_eau']['grilles']}, avaloirs {r['fil_eau']['avaloirs']}) ; bordures : trous "
              f"{r['bordures']['longueur_trous_m']} m, sur mesure {r['bordures']['pieces_sur_mesure']} ; arbres "
              f"{(r['arbres'] or {}).get('conformes')}/{(r['arbres'] or {}).get('total')}")
    if a.json:
        Path(a.json).write_text(json.dumps({"schema": "rg_controles_correction/0.1", "scenes": res}, ensure_ascii=False,
                                           indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
