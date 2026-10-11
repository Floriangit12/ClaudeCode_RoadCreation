"""Canal de mesures du solveur de cohérence v2 (correctifs P3, P4 et P9 de la revue v1).

P3 — une mesure {position ou (ds, dt), σ} devient le NOUVEL A PRIORI p0 de l'objet (classe « mesure »,
σ 0,05-0,3 m) AVANT la résolution ; la règle ne remplace plus une valeur mesurée par sa cible. Sources :
- revue_coherence.json (schéma 0.2) : champ `mesure` saisi par Claude sur les planches et les photos
  (position_local, ou ds / dt dans le repère de la bordure de référence de la position source), avec
  photos citées ;
- fusion du recensement (description/enrichi/corrections_position.geojson, fusion 0.3) : décision
  « appliquer » -> mesure ; « revue_requise » -> hypothèse F montrée sur la planche, non appliquée ;
- triangulations d'axes de mâts sur photos calées (enrichi/recensement/mapillary/triangulation_mixte.json,
  « fiable » : ≥ 3 vues, angle ≥ 20°, stabilité) ;
- ombres portées (coherence_ombres, P10) : preuve anisotrope ; probante seulement si les deux orthos
  s'accordent à 0,5 m, sinon indice (planches) ;
chaque mesure n'est retenue que si sa date la rend valable pour l'objet (valide_pour_photo : objet posé
ou déduit pour 2026 -> seulement après les travaux ; objet dans l'emprise des travaux prouvé avant ->
pas de mesure antérieure sans appui). Fusion de plusieurs mesures par moindres carrés pondérés
(covariances), avec test de cohérence (écart ≤ 3σ combiné) ; en cas de désaccord, la plus précise.

P9 — position source brute : nœud OSM brut (data/sites/paquet_jardin/vector/osm_*.geojson) pour les
objets OSM ; le recalage v1 (« recalé de X m ») est ainsi compté dans le budget ; |p_final − p_brut| ≤
d_max de la classe de la source brute. Une mesure est une nouvelle source : p_brut := p_mesure,
d_max := max(3σ, 0,3 m).

P4 — orientation par raccourci : chaque vue donne |angle| entre la normale de la plaque et la visée
(w/h mesuré / w/h de face : disque et octogone 1,0, triangle 1,155, rectangle selon le code) et le côté
vu (face / dos) ; l'azimut de face est le minimum de Σ (écart(az, relèvement) − θ)² sur ≥ 2 vues, ce qui
lève l'ambiguïté de signe. Les plaques de chaque mât (nombre, formes, ordre vertical) sont identifiées
avant de transférer une conclusion : un verdict d'orientation dont les plaques citées ne correspondent pas
aux codes du groupe est rejeté (`plaques_incompatibles`).
"""
import functools
import json
import math
import re

import numpy as np

from coherence_carte import COHERENCE
from commun import RACINE, SORTIE, VECTEURS, lire_json, repere

REVUE = COHERENCE / "revue_coherence.json"
FUSION_POS = SORTIE / "enrichi/corrections_position.geojson"
TRIANG_MIXTE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/triangulation_mixte.json"
SIGMA_MIN = 0.05
FORMES = {"disque": 1.0, "octogone": 1.0, "triangle": 1.1547, "carre": 1.0, "losange": 1.0}
FORME_CODE = [(r"^AB4", "octogone"), (r"^AB3", "triangle"), (r"^A\d", "triangle"), (r"^AB\d", "triangle"),
              (r"^B", "disque"), (r"^C1(13|14)", "carre"), (r"^C", "rectangle"), (r"^M", "panonceau"),
              (r"^J5", "balise"), (r"^D21", "lames"), (r"^CE", "rectangle"), (r"^AB6", "losange")]


def forme_code(code):
    for motif, f in FORME_CODE:
        if re.search(motif, str(code or "")):
            return f
    return "autre"


# --------------------------------------------------------------------------- revue
@functools.lru_cache(maxsize=1)
def revue():
    if not REVUE.exists():
        return {}
    d = lire_json(REVUE)
    return d.get("revues", {})


# --------------------------------------------------------------------------- p_brut (P9)
@functools.lru_cache(maxsize=1)
def noeuds_osm():
    """{osm_id ('node/123'): (x, y) local} pour tous les points des couches OSM du site."""
    from pyproj import Transformer
    t = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    out = {}
    for f in sorted((VECTEURS / "vector").glob("osm_*.geojson")):
        for g in lire_json(f)["features"]:
            if g["geometry"]["type"] != "Point":
                continue
            oid = str(g["properties"].get("osm_id") or g.get("id") or "")
            if not oid.startswith("node/"):
                continue
            lon, lat = g["geometry"]["coordinates"][:2]
            xy = np.array(t.transform(lon, lat))
            out[oid] = repere(xy[None])[0]
    return out


def position_brute(o, res):
    """(p_brut, dmax_brut, source) : nœud OSM brut si l'objet en vient, sinon p0 (budget réduit du
    recalage v1 annoncé dans la remarque)."""
    from valider_regles_implantation import classe_preuve
    props = o.get("props") or {}
    cle, sig, dmax = classe_preuve(o.get("source"), o.get("confiance"), res)
    rem = str(props.get("remarque") or "")
    if str(o.get("statut") or "").startswith("déduit"):
        return np.asarray(o["p0"], float), float(dmax), "position déduite (pas de source brute)"
    if re.search(r"recal[ée]e? sur (le|la|un|une) [^;]*(m[âa]t|ombre|pied|ortho|LiDAR)|position recal[ée]e|luminaire classe",
                 rem, re.I) and re.search(r"ortho|LiDAR|m[âa]t visible|luminaire", rem, re.I):
        # recalage v1 sur une preuve plus forte que le nœud (mât visible sur l'ortho, luminaire LiDAR) : c'est la
        # position source brute (le nœud OSM n'est qu'un indice d'identité)
        return np.asarray(o["p0"], float), float(dmax), "position recalée en v1 sur l'ortho 2022 ou le LiDAR (remarque)"
    oid = props.get("osm_id")
    if oid and oid in noeuds_osm():
        return np.asarray(noeuds_osm()[oid], float), float(dmax), f"OSM {oid} (nœud brut)"
    m = re.search(r"recal[ée] de ([0-9.]+) m", rem)
    if m:
        return np.asarray(o["p0"], float), max(float(dmax) - float(m.group(1)), 0.1), \
            f"position v1 (recalée de {m.group(1)} m, source brute inconnue : budget réduit)"
    return np.asarray(o["p0"], float), float(dmax), "position source"


# --------------------------------------------------------------------------- mesures
def _cov(sig_long, sig_trav, az_deg):
    u = np.array([math.sin(math.radians(az_deg)), math.cos(math.radians(az_deg))])
    e = np.array([u[1], -u[0]])
    return sig_long ** 2 * np.outer(u, u) + sig_trav ** 2 * np.outer(e, e)


def _mesure(oid, xy, sigma, source, methode, date, preuves, statut="probante", cov=None, note=None):
    xy = np.asarray(xy, float)
    cov = np.eye(2) * sigma ** 2 if cov is None else np.asarray(cov, float)
    return dict(objet=oid, xy=xy, sigma_m=round(float(math.sqrt(max(np.linalg.eigvalsh(cov)))), 3), cov=cov,
                source=source, methode=methode, date=date, preuves=preuves, statut=statut, note=note)


def mesures_brutes(objets, ombres, carte):
    """Toutes les mesures candidates par objet (avant le filtre de validité)."""
    par = {o["id"]: o for o in objets}
    out = {}

    def add(m):
        out.setdefault(m["objet"], []).append(m)
    # 1. revue (Claude, planches et photos citées)
    for oid, rv in sorted(revue().items()):
        ms = rv.get("mesure")
        if not ms or oid not in par:
            continue
        o = par[oid]
        if ms.get("position_local") is not None:
            xy = np.asarray(ms["position_local"], float)
        else:
            r = carte.ref_bordure(np.asarray(o["p0"], float)[None], rayon=10.0, circulee=False)[0]
            if r is None:
                continue
            n = np.array([-r["tg"][1], r["tg"][0]])
            t_cible = ms.get("t")
            dt = (float(t_cible) - r["t"]) if t_cible is not None else float(ms.get("dt", 0.0))
            xy = np.asarray(o["p0"], float) + float(ms.get("ds", 0.0)) * r["tg"] + dt * n
        cov = None
        if ms.get("sigma_long_m") is not None:
            cov = _cov(float(ms["sigma_long_m"]), float(ms["sigma_travers_m"]), float(ms["azimut_long_deg"]))
        add(_mesure(oid, xy, float(ms.get("sigma_m", ms.get("sigma_travers_m", 0.25))), "revue_coherence",
                    ms.get("methode", "lecture planche"), ms.get("date"), ms.get("photos") or [], cov=cov, note=ms.get("note")))
    # 2. fusion du recensement 0.3
    if FUSION_POS.exists():
        for f in lire_json(FUSION_POS)["features"]:
            p = f["properties"]
            if p.get("famille") != "mobilier" or p["id"] not in par or not p.get("p_fusion_local"):
                continue
            dates = sorted(x.get("date") or "" for x in p.get("provenance") or [])
            add(_mesure(p["id"], p["p_fusion_local"], max(float(p.get("sigma_m") or 0.3), SIGMA_MIN), "fusion_recensement_0.3",
                        "+".join(p.get("methodes") or []), dates[-1] if dates else None, p.get("obs") or [],
                        statut="probante" if p.get("decision") == "appliquer" else "hypothese",
                        note=f"décision fusion « {p.get('decision')} » ; " + "; ".join(p.get("raisons") or [])))
    # 3. triangulations d'axes (photos calées Panoramax + Mapillary)
    if TRIANG_MIXTE.exists():
        for r in lire_json(TRIANG_MIXTE)["resultats"]:
            if not r.get("fiable") or r["entite"] not in par:
                continue
            sig = max(float(math.hypot(*r["ecart_type"])), 0.10, float(r.get("stabilite_loo_m") or 0) / 2)
            dates = sorted(v["date"] for v in r["vues"])
            add(_mesure(r["entite"], r["xy"], sig, "triangulation_mixte", f"axe triangulé ({r['n_inliers']} vues, "
                        f"{r['angle_intersection_deg']}°)", dates[-1], [v["source"] for v in r["vues"]],
                        note=f"dates des vues {dates[0]} à {dates[-1]}"))
    # 4. ombres portées (P10)
    for oid, dd in sorted(((ombres or {}).get("detections") or {}).items()):
        a = dd.get("pcrs2022")
        if not a or not a.get("accepte") or oid not in par:
            continue
        b = dd.get("ign2024")
        accord = bool(b and b.get("accepte") and (dd.get("accord_2022_2024_m") or 9) <= 0.5)
        cov = _cov(a["sigma_long_m"], a["sigma_travers_m"], a["az_ombre_grille"])
        add(_mesure(oid, a["xy"], a["sigma_travers_m"], "ombre_ortho", "pied de mât par l'ombre portée (PCRS 2022"
                    + (" + IGN 2024 concordante" if accord else "") + ")", "2022-05-10", ["ortho:pcrs2022"] + (["ortho:ign2024"] if accord else []),
                    statut="probante" if accord else "indice", cov=cov,
                    note=f"z {a['z']}, unicité {a['unicite']}, ombre à {a['az_ombre_grille']}°"))
    return out


def combiner(ms):
    """Moindres carrés pondérés des mesures probantes ; cohérence (écart de Mahalanobis ≤ 3 deux à deux,
    sinon on garde la plus précise et les compatibles avec elle)."""
    if not ms:
        return None
    ms = sorted(ms, key=lambda m: (m["sigma_m"], m["source"]))
    ref = ms[0]
    garde = [ref]
    rejet = []
    for m in ms[1:]:
        C = ref["cov"] + m["cov"]
        d = ref["xy"] - m["xy"]
        mah = float(math.sqrt(d @ np.linalg.solve(C, d)))
        (garde if mah <= 3.0 else rejet).append(dict(m, mahalanobis=round(mah, 2)) if m is not ref else m)
    W = sum(np.linalg.inv(m["cov"]) for m in garde)
    Cf = np.linalg.inv(W)
    xy = Cf @ sum(np.linalg.inv(m["cov"]) @ m["xy"] for m in garde)
    sig = float(math.sqrt(max(np.linalg.eigvalsh(Cf))))
    return dict(xy=xy, cov=Cf, sigma_m=round(max(sig, SIGMA_MIN), 3), retenues=garde, ecartees=rejet)


def appliquer(objets, carte, res, ombres, valide_pour_photo, anterieure_travaux):
    """Ajoute à chaque objet : p_brut, dmax_brut, mesures (toutes, avec statut de validité), et remplace
    p0 / σ / d_max / preuve par la mesure combinée quand elle existe (P3). Renvoie le journal."""
    brutes = mesures_brutes(objets, ombres, carte)
    journal = []
    for o in objets:
        pb, dmb, src = position_brute(o, res)
        o["p_source"] = np.asarray(o["p0"], float).copy()
        o["p_brut"], o["dmax_brut"], o["source_brute"] = pb, dmb, src
        o["mesures"] = []
        ms = brutes.get(o["id"], [])
        for m in ms:
            ok = True
            motif = None
            if m["date"] and not valide_pour_photo(o, m["date"]):
                ok, motif = False, f"mesure du {m['date']} non valable pour l'état 2026 de l'objet ({o['statut']})"
            elif m["source"] != "revue_coherence" and m["date"] and m["date"] <= "2025-12-05" and o.get("_emprise_travaux") \
                    and anterieure_travaux(o):
                ok, motif = False, "mesure antérieure aux travaux, objet dans l'emprise (FUS-DATE-02, sans appui)"
            m2 = dict(m, valide=ok, motif_rejet=motif)
            o["mesures"].append(m2)
        probantes = [m for m in o["mesures"] if m["valide"] and m["statut"] == "probante"]
        comb = combiner(probantes)
        if comb is None:
            continue
        p_old = np.asarray(o["p0"], float)
        o["mesure"] = dict(xy=comb["xy"], sigma_m=comb["sigma_m"], cov=comb["cov"],
                           sources=sorted({m["source"] for m in comb["retenues"]}),
                           retenues=[dict(source=m["source"], methode=m["methode"], xy=[round(float(v), 3) for v in m["xy"]],
                                          sigma_m=m["sigma_m"], date=m["date"], preuves=m["preuves"]) for m in comb["retenues"]],
                           ecartees=[dict(source=m["source"], xy=[round(float(v), 3) for v in m["xy"]], sigma_m=m["sigma_m"],
                                          mahalanobis=m.get("mahalanobis")) for m in comb["ecartees"]],
                           d_p0_m=round(float(np.hypot(*(comb["xy"] - p_old))), 3))
        o["p0"] = np.asarray(comb["xy"], float)
        o["preuve_avant_mesure"] = (o["preuve"], o["sigma"], o["dmax"])
        o["preuve"] = "mesure"
        o["sigma"] = comb["sigma_m"]
        o["dmax"] = round(max(3 * comb["sigma_m"], 0.3), 3)
        o["p_brut"], o["dmax_brut"] = o["p0"].copy(), o["dmax"]
        o["source_brute"] = "mesure (" + ", ".join(o["mesure"]["sources"]) + ")"
        journal.append(dict(objet=o["id"], d_m=o["mesure"]["d_p0_m"], sigma_m=comb["sigma_m"], sources=o["mesure"]["sources"]))
    return journal


# --------------------------------------------------------------------------- orientation par raccourci (P4)
def azimut_par_raccourci(vues, pas=0.5):
    """vues : [dict(releve_deg (azimut objet -> caméra), rapport_wh, rapport_face, cote 'face'|'dos'|None)].
    Renvoie dict(azimut, rms_deg, second, n) ou None (moins de 2 vues)."""
    if len(vues) < 2:
        return None
    th = []
    for v in vues:
        r = min(max(float(v["rapport_wh"]) / float(v["rapport_face"]), 0.0), 1.0)
        a = math.degrees(math.acos(r))
        th.append((float(v["releve_deg"]), a, v.get("cote")))
    best = []
    for az in np.arange(0.0, 360.0, pas):
        J = 0.0
        for rel, a, cote in th:
            e = abs((az - rel + 180) % 360 - 180)        # angle face <-> caméra
            if cote == "face":
                r = e - a if e <= 90 else 1e3
            elif cote == "dos":
                r = (180 - e) - a if e >= 90 else 1e3
            else:
                r = min(e, 180 - e) - a
            J += r * r
        best.append((J, float(az)))
    best.sort()
    J0, az0 = best[0]
    second = next((b for b in best if abs((b[1] - az0 + 180) % 360 - 180) > 30), None)
    return dict(azimut=round(az0, 1), rms_deg=round(math.sqrt(J0 / len(th)), 1),
                second=None if second is None else dict(azimut=round(second[1], 1), rms_deg=round(math.sqrt(second[0] / len(th)), 1)),
                n=len(th), obliquites_deg=[round(a, 1) for _, a, _ in th])


def plaques_compatibles(codes_groupe, plaques_vues):
    """Les plaques vues sur le mât (formes) correspondent-elles aux codes du groupe ?"""
    attendu = sorted(forme_code(c) for c in codes_groupe if forme_code(c) not in ("autre",))
    vu = sorted(plaques_vues)
    return attendu == vu, attendu
