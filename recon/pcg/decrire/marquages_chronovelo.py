"""Traversées cyclables Chronovélo absentes de la description (VAL-XOD-008, MQ-CYC-007, MQ-CHR-001 ; revues du
11/10/2026 : crosswalk « bicycle » 1/1010 et 2/1011 de Verdun SO sans pavé ni carré décrit, le plus proche à 11,5 m).

Pour chaque objet crosswalk subtype « bicycle » du .xodr (contour = emprise de la traversée, levé GAM 2026 : bordures,
chevrons, vélos) sans traversée cyclable décrite à moins de 1,5 m :
- les pavés orange du plan projet 2025 (seule source admise hors levé et détection, MQ-CHR-001 : « posées si levées,
  détectées ou au plan 2025 », jamais déduites ailleurs) sont détectés par couleur sur les tuiles géoréférencées
  (blobs de plus de 0,08 m²) dans l'emprise élargie de 1 m ;
- chaque grand côté du contour (côtés qui traversent la chaussée) porteur d'au moins 4 blobs alignés à moins de 0,9 m
  donne une file : pavé PAVE_CHRONOVELO (0,70 × 0,37, pas 0,60) si les blobs sont allongés, sinon carré
  CARRE_TRAVERSEE_CYCLABLE (0,50, pas 1,00) ; la file est parallèle au côté levé (position du levé, décalage médian
  mesuré sur le plan), bornée au contour (0,25 m des bordures), régularisée au pas du gabarit ;
- l'entité est de source plan2025, confiance faible, a_verifier (aucune photo après travaux).
Python + numpy + Pillow ; déterministe (objets triés, seuils fixes).
"""
import json
import math
from collections import deque

import numpy as np
from PIL import Image

import marquages_commun as M
import marquages_fusion as FU
import marquages_gam_entites as GE
import xodr_echantillonne as X
from commun import RACINE, repere

PLAN = RACINE / "data/sites/paquet_jardin/plan_projet_2025/tuiles"
RES = 0.02
AIRE_MIN_M2 = 0.08
DIST_FILE_M = 0.9
N_MIN = 4
GABARITS = {"PAVE_CHRONOVELO": 0.60, "CARRE_TRAVERSEE_CYCLABLE": 1.00}


def _mosaique(x0, y0, x1, y1):
    W, H = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES))
    img = np.zeros((H, W, 3), np.uint8)
    O = repere(np.zeros((1, 2)), "l93")[0]
    for t in json.loads((PLAN / "index.json").read_text(encoding="utf-8")):
        a, b, c, d, e, f = t["affine_L93"]
        Mi = np.linalg.inv(np.array([[a, b], [d, e]]))
        A = Mi @ np.array([[RES, 0.0], [0.0, -RES]])
        off = Mi @ np.array([O[0] + x0 - c, O[1] + y1 - f])
        data = (A[0, 0], A[0, 1], off[0], A[1, 0], A[1, 1], off[1])
        tile = Image.open(PLAN / t["file"]).convert("RGB")
        im2 = np.array(tile.transform((W, H), Image.AFFINE, data, Image.BILINEAR))
        mk = np.array(Image.new("L", tile.size, 255).transform((W, H), Image.AFFINE, data, Image.NEAREST)) > 0
        img[mk] = im2[mk]
    return img


def blobs_orange(x0, y0, x1, y1):
    """Blobs orange du plan 2025 (local) : [(centre, aire, grand axe, petit axe, direction du grand axe)]."""
    img = _mosaique(x0, y0, x1, y1).astype(int)
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    m = (r > 170) & (g > 90) & (g < 190) & (b < 110) & (r - b > 90)
    H, W = m.shape
    lab = np.zeros(m.shape, np.int32)
    out = []
    for j, i in zip(*np.nonzero(m)):
        if lab[j, i]:
            continue
        lab[j, i] = 1
        q, pts = deque([(j, i)]), []
        while q:
            a, c = q.popleft()
            pts.append((a, c))
            for da in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    u, v = a + da, c + dc
                    if 0 <= u < H and 0 <= v < W and m[u, v] and not lab[u, v]:
                        lab[u, v] = 1
                        q.append((u, v))
        pts = np.array(pts, float)
        aire = len(pts) * RES * RES
        if aire < AIRE_MIN_M2 or aire > 1.2:
            continue
        xy = np.c_[x0 + (pts[:, 1] + 0.5) * RES, y1 - (pts[:, 0] + 0.5) * RES]
        c = xy.mean(axis=0)
        w, V = np.linalg.eigh(np.cov((xy - c).T))
        out.append((c, aire, 4.0 * math.sqrt(max(w[1], 0.0)), 4.0 * math.sqrt(max(w[0], 0.0)), V[:, 1]))
    out.sort(key=lambda t: (round(float(t[0][0]), 3), round(float(t[0][1]), 3)))
    return out


def _cote_traversant(anneau):
    """Les deux grands côtés du contour (ceux qui traversent la chaussée) : [(A, B)] et les deux autres."""
    P = np.asarray(anneau, float)
    cotes = [(P[k], P[(k + 1) % len(P)]) for k in range(len(P))]
    cotes.sort(key=lambda ab: -float(np.hypot(*(ab[1] - ab[0]))))
    return cotes[:2], cotes[2:]


def traversees(entites, reseau, loc):
    """-> (nouvelles entités MP-82nn, journal)."""
    import marquages_reprises as RP
    out, journal, n = [], [], 0
    decrites = [e for e in entites if e["classe"] == "passage" and e["type"] == "traversee_cyclable"]
    from commun import dans_polygone
    gam = []
    for e in entites:
        if str(e.get("src", "")) == "gam" and e["classe"] in ("symbole", "passage", "zone", "fleche"):
            try:
                for poly in RP.empreinte(e):
                    gam.append((np.vstack(poly).min(axis=0), np.vstack(poly).max(axis=0), poly))
            except Exception:
                pass

    def gam_polys(c, r=1.0):
        return [poly for lo, hi, poly in gam if (lo <= c + r).all() and (hi >= c - r).all()]
    pts_dec = [np.vstack([q for poly in RP.empreinte(e) for q in poly]) if RP.empreinte(e) else
               np.atleast_2d(np.vstack(e["geom"][1]) if e["geom"][0] == "MultiLineString" else e["geom"][1])
               for e in decrites]
    for o in sorted(X.objets(reseau), key=lambda o: (int(o["route"]), str(o["id"]))):
        if o["type"] != "crosswalk" or o.get("sous_type") != "bicycle" or o["anneau"] is None:
            continue
        an = np.asarray(o["anneau"], float)
        from commun import dans_polygone, distance_segments
        ra = np.vstack([an, an[:1]])
        proche = False
        for P in pts_dec:
            d, _, _ = distance_segments(P, ra[:-1], ra[1:])
            if float(d.min()) <= 1.5 or dans_polygone(P, [an]).any():
                proche = True
                break
        if proche:
            journal.append({"objet": o["id"], "route": o["route"], "decision": "traversee_deja_decrite"})
            continue
        lo, hi = an.min(axis=0) - 1.0, an.max(axis=0) + 1.0
        bl = blobs_orange(float(lo[0]), float(lo[1]), float(hi[0]), float(hi[1]))
        grands, petits = _cote_traversant(an)
        files = []
        for A, B in grands:
            u = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
            nrm = np.array([-u[1], u[0]])
            L = float(np.hypot(*(B - A)))
            sel = []
            for c, aire, gl, gw, v in bl:
                s = float((c - A) @ u)
                t = float((c - A) @ nrm)
                if abs(t) <= DIST_FILE_M and -0.3 <= s <= L + 0.3:
                    sel.append((s, t, gl, gw))
            if len(sel) < N_MIN:
                continue
            allonge = float(np.median([gl / max(gw, 1e-6) for _, _, gl, gw in sel])) >= 1.5
            if not allonge:
                # blobs trapus au pas du zébra (0,98 m) le long du côté contigu au passage : extrémités de bandes
                # colorées du plan, pas des pavés (aucun carré levé au GAM sur ce côté, où sont levés les vélos) :
                # écartés (MQ-CHR-001 : pavés 0,70 x 0,37 au pas de 0,60 seulement)
                continue
            gab = "PAVE_CHRONOVELO"
            pas = GABARITS[gab]
            t_plan = float(np.median([t for _, t, _, _ in sel]))
            # décalage au côté levé mesuré sur le plan (0,5 à 0,7 m à l'extérieur du contour .xodr, qui suit les chevrons
            # levés GAM) : gardé, l'intérieur du contour étant occupé par les chevrons et vélos levés (FUS-CON-005)
            t_med = t_plan
            # file bornée au contour (0,25 m des côtés de bordure), régularisée au pas du gabarit, centrée
            s0, s1 = 0.25 + 0.2, L - 0.25 - 0.2
            nb = int(math.floor((s1 - s0) / pas + 1e-9)) + 1
            if nb < 2:
                continue
            sc = 0.5 * (s0 + s1)
            a_ = A + u * (sc - 0.5 * pas * (nb - 1)) + nrm * t_med
            b_ = a_ + u * pas * (nb - 1)
            # FUS-CON-005 : le levé GAM prime ; pavé qui recouvre une marque levée (vélo, chevron, bande) : absent
            absents = []
            for k in range(nb):
                c = a_ + u * pas * k
                Q = np.array([c + u * du + nrm * dn for du in (-0.185, 0.0, 0.185) for dn in (-0.35, 0.0, 0.35)])
                if any(dans_polygone(Q, poly).any() for poly in gam_polys(c)):
                    absents.append(k)
            if len(absents) > 0.5 * nb:
                continue
            d = b_ - a_
            if d[0] < 0 or (abs(d[0]) < 1e-9 and d[1] < 0):
                a_, b_ = b_, a_
            files.append({"axe": [a_, b_], "nb": nb - len(absents), "pas_m": pas, "absents": absents,
                          "cap_deg": round(M.cap_de(b_ - a_), 2), "couleur": "jaune", "lien_v1": [],
                          "residu_max_m": round(float(np.max(np.abs(np.array([t for _, t, _, _ in sel]) - t_plan))), 3),
                          "gabarit": gab, "blobs_plan_2025": len(sel)})
        if not files:
            journal.append({"objet": o["id"], "route": o["route"], "decision": "aucun_pave_au_plan_2025",
                            "blobs": len(bl)})
            continue
        eid = GE.ident("MP", 8200 + n)
        n += 1
        c = an.mean(axis=0)
        e = GE.base(eid, "passage", "traversee_cyclable", c, [], "", loc, couleur="jaune")
        note = (f"objet crosswalk « bicycle » {o['route']}/{o['id']} du .xodr (levé GAM 2026 : bordures, chevrons, vélos) sans "
                f"traversée décrite (VAL-XOD-008) ; pavés orange du plan projet 2025 ({sum(f['blobs_plan_2025'] for f in files)} "
                f"blobs) le long des grands côtés du contour : {len(files)} file(s) régularisée(s) sur le gabarit du site "
                "(MQ-CHR-001, MQ-CYC-007), confiance faible, à vérifier")
        e.update({"geom": ("MultiLineString", [np.vstack(f["axe"]) for f in files]), "files": files,
                  "nb_tuiles": int(sum(f["nb"] for f in files)), "src": "plan2025", "gam": [], "sources": [],
                  "groupe": "traversee_cyclable_chronovelo_plan", "a_verifier": True,
                  "xodr_objet": o["id"], "regles": ["MQ-CHR-001", "MQ-CYC-007", "VAL-XOD-008"]})
        e["prov"] = {"geometrie": {"src": "plan2025", "ref": note, "conf": "faible"},
                     "gabarit": {"src": "regle:marquages_geometrie.gabarits", "ref": "PAVE_CHRONOVELO / CARRE_TRAVERSEE_CYCLABLE "
                                 "(pratique du site, non IISR)", "conf": "moyenne"}}
        FU.ajouter_source(e, "plan2025", note, 0.5, e.get("etat_zone"))       # P < 0,5 : confiance faible, a_verifier
        out.append(e)
        journal.append({"objet": o["id"], "route": o["route"], "decision": "deduite", "entite": eid,
                        "files": [(f["gabarit"], f["nb"]) for f in files]})
    return out, journal
