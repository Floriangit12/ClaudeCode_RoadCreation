"""Canal de mesures du solveur de cohérence v3 (P3, P4, P9 de la revue v1 ; Q1, Q6, Q7, Q8 de la revue v2).

P3 — une mesure {position ou (ds, dt), σ} devient le NOUVEL A PRIORI p0 de l'objet (classe « mesure ») AVANT la
résolution ; la règle ne remplace plus une valeur mesurée par sa cible. Sources :
- revue_coherence.json (schéma 0.3) : champ `mesure` saisi par Claude (position_local, ou ds / dt dans le repère
  de la bordure de référence), `nature` (triangulation_photos | lecture_ombre | pixel_ortho | rayon_photo_regle),
  photos citées, corroboration éventuelle (lecture indépendante) ;
- fusion du recensement (enrichi/corrections_position.geojson, fusion 0.3) : « appliquer » -> mesure ;
  « revue_requise » -> hypothèse F (planche), jamais appliquée ;
- triangulations d'axes de mâts sur photos calées (recensement/mapillary/triangulation_mixte.json, « fiable ») ;
- ombres portées (coherence_ombres, P10) : probante seulement si les deux orthos s'accordent à 0,5 m.
Chaque mesure n'est retenue que si sa date la rend valable pour l'objet (valide_pour_photo ; objet dans
l'emprise des travaux prouvé avant : pas de mesure antérieure sans appui).

Q7 — nature de la mesure et type d'objet : une lecture « pixel_ortho » (tache sur l'ortho 2022, qui n'est pas
une ortho vraie : un point à h mètres est déversé de plusieurs décimètres) ne vaut que pour un objet AU SOL
(potelet, borne, banc, corbeille, jardinière, armoire, boîte aux lettres…). Pour un mât (candélabre, panneau,
support de feux, caméra, poteau), seuls valent un départ d'ombre CORROBORÉ (deux lectures indépendantes :
détecteur d'ombres et lecture de Claude ou de la revue adverse, ou les deux orthos) et une triangulation
photo (≥ 2 visées à ≥ 15°) ; un rayon photo borné par une règle n'est pas une mesure de mât. Sinon : indice.

Q6 — covariance : une mesure photo reçoit une covariance anisotrope tirée de la dispersion réelle de ses
résidus (triangulation mixte : résidus angulaires par vue), avec le plancher géométrique d·σ_pose en travers
et d·σ_pose / sin(angle d'intersection) en profondeur (infinie, 100 m, sous 15°) ; un σ saisi à la main
sous ce plancher est refusé (remplacé par le plancher, drapeau `sigma_saisi_refuse`).

Q1 — chaque mesure est confrontée aux photos décisives de sa planche (coherence_accord) : hors « accord », elle
devient un INDICE ; seule la composante latérale OBSERVÉE (axes détectés) peut alors s'appliquer.

P9/Q8 — deux contrôles : (1) le budget de la SOURCE d'origine est gardé (p_brut_source, d_max de sa classe ;
dépassement signalé `budget_source_depasse`) ; (2) compatibilité mesure ↔ source (distance de Mahalanobis
avec Σ_mesure + σ_source²) : au-delà de 3, `deplace_par_travaux` si la mesure est postérieure aux travaux
(statut 2026 « déplacé lors des travaux 2025 », photos antérieures non valables), sinon `mesure_contestee`
(confiance faible, à vérifier). Une mesure compatible dont une direction n'est pas observée (profondeur) est
fusionnée avec la source, qui fixe cette direction. Le budget de la mesure est max(3σ, 0,3 m) autour d'elle.

P4 — orientation par raccourci : chaque vue donne |angle| entre la normale de la plaque et la visée
(w/h mesuré / w/h de face : disque et octogone 1,0, triangle 1,155, rectangle selon le code) et le côté
vu (face / dos) ; l'azimut de face est le minimum de Σ (écart(az, relèvement) − θ)² sur ≥ 2 vues, ce qui
lève l'ambiguïté de signe. Les plaques de chaque mât sont identifiées avant de transférer une conclusion
(`plaques_incompatibles` sinon).
"""
import functools
import math
import re

import numpy as np

from coherence_carte import COHERENCE
from commun import RACINE, SORTIE, VECTEURS, lire_json, repere

REVUE = COHERENCE / "revue_coherence.json"
FUSION_POS = SORTIE / "enrichi/corrections_position.geojson"
TRIANG_MIXTE = RACINE / "recon/out/paquet_jardin/v2/enrichi/recensement/mapillary/triangulation_mixte.json"
SIGMA_MIN = 0.05
SIGMA_PLAN_MIN = 0.10
SIGMA_INFINI = 100.0
ANGLE_MIN = 15.0
MAHA_MAX = 3.0
FIN_TRAVAUX_2025 = "2025-12-05"
FORMES = {"disque": 1.0, "octogone": 1.0, "triangle": 1.1547, "carre": 1.0, "losange": 1.0}
FORME_CODE = [(r"^AB4", "octogone"), (r"^AB3", "triangle"), (r"^A\d", "triangle"), (r"^AB\d", "triangle"),
              (r"^B", "disque"), (r"^C1(13|14)", "carre"), (r"^C", "rectangle"), (r"^M", "panonceau"),
              (r"^J5", "balise"), (r"^D21", "lames"), (r"^CE", "rectangle"), (r"^AB6", "losange")]
# Q7 : objets au sol (lecture pixel_ortho admise) et mâts
TYPES_SOL = {"potelet", "borne", "banc", "corbeille", "jardiniere", "armoire", "boite_aux_lettres", "stationnement_velos",
             "barriere", "chicane", "fontaine", "conteneur_verre", "distributeur", "poteau_incendie", "regard", "bloc_rocheux",
             "barriere_levante"}
TYPES_MATS = {"lampadaire", "mat_camera", "poteau_reseau", "support_feux", "panneau", "poteau_arret", "balise_J11",
              "panneau_information", "totem_PR", "mobilier_publicitaire", "arbre", "abri_bus", "portail"}
NATURES_PHOTO = {"triangulation_photos", "rayon_photo_regle"}
NATURES_OMBRE = {"lecture_ombre", "ombre_detecteur"}


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


@functools.lru_cache(maxsize=1)
def presences_revue():
    """Q4 : entrées de présence 2026 saisies par Claude ({id: dict(valeur, photos, note)})."""
    if not REVUE.exists():
        return {}
    return lire_json(REVUE).get("presence_2026", {}) or {}


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


def _sig_max(cov):
    return float(math.sqrt(max(np.linalg.eigvalsh(cov))))


def _sig_dir(cov, v):
    v = np.asarray(v, float) / max(np.hypot(*v), 1e-12)
    return float(math.sqrt(max(float(v @ cov @ v), 0.0)))


def photo_id(s):
    """'pnx:<uuid>' -> 'pnx:<8 car.>' ; 'mly:<id>' inchangé ; autre -> None."""
    s = str(s or "")
    if s.startswith("pnx:"):
        return "pnx:" + s[4:12]
    if s.startswith("mly:"):
        return s
    return None


def _mesure(oid, xy, sigma, source, methode, date, preuves, statut="probante", cov=None, note=None, nature=None,
            photos=None, rayons=None):
    xy = np.asarray(xy, float)
    cov = np.eye(2) * sigma ** 2 if cov is None else np.asarray(cov, float)
    return dict(objet=oid, xy=xy, sigma_m=round(_sig_max(cov), 3), cov=cov, source=source, methode=methode, date=date,
                preuves=preuves, statut=statut, note=note, nature=nature,
                photos=sorted({p for p in (photo_id(x) for x in (photos or [])) if p}), rayons=rayons)


def _nature_revue(ms):
    nat = ms.get("nature")
    if nat:
        return nat
    m = str(ms.get("methode") or "")
    if re.search(r"ombre", m, re.I):
        return "lecture_ombre"
    if re.search(r"triangul|pointage", m, re.I):
        return "triangulation_photos"
    if re.search(r"rayon", m, re.I):
        return "rayon_photo_regle"
    return "pixel_ortho"


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
        m = _mesure(oid, xy, float(ms.get("sigma_m", ms.get("sigma_travers_m", 0.25))), "revue_coherence",
                    ms.get("methode", "lecture planche"), ms.get("date"), ms.get("photos") or [], cov=cov, note=ms.get("note"),
                    nature=_nature_revue(ms), photos=ms.get("photos") or [])
        m["corroboration"] = ms.get("corroboration")
        m["sigma_saisi"] = True
        add(m)
    # 2. fusion du recensement 0.3
    if FUSION_POS.exists():
        for f in lire_json(FUSION_POS)["features"]:
            p = f["properties"]
            if p.get("famille") != "mobilier" or p["id"] not in par or not p.get("p_fusion_local"):
                continue
            dates = sorted(x.get("date") or "" for x in p.get("provenance") or [])
            meth = p.get("methodes") or []
            nature = "pixel_ortho" if "pixel_ortho" in meth else ("triangulation_photos" if "triangulation" in meth else
                                                                   "inventaire")
            m = _mesure(p["id"], p["p_fusion_local"], max(float(p.get("sigma_m") or 0.3), SIGMA_MIN), "fusion_recensement_0.3",
                        "+".join(meth), dates[-1] if dates else None, p.get("obs") or [],
                        statut="probante" if p.get("decision") == "appliquer" else "hypothese",
                        note=f"décision fusion « {p.get('decision')} » ; " + "; ".join(p.get("raisons") or []),
                        nature=nature, photos=[x.get("source") for x in p.get("provenance") or []])
            m["sigma_saisi"] = True
            add(m)
    # 3. triangulations d'axes (photos calées Panoramax + Mapillary)
    if TRIANG_MIXTE.exists():
        for r in lire_json(TRIANG_MIXTE)["resultats"]:
            if not r.get("fiable") or r["entite"] not in par:
                continue
            sig = max(float(math.hypot(*r["ecart_type"])), 0.10, float(r.get("stabilite_loo_m") or 0) / 2)
            dates = sorted(v["date"] for v in r["vues"])
            rayons = [dict(photo=photo_id(v["source"]), az=float(v["az"]), d_m=float(v["d_m"]), residu_deg=float(res))
                      for v, res in zip(r["vues"], r.get("residus_deg") or [0.0] * len(r["vues"]))]
            add(_mesure(r["entite"], r["xy"], sig, "triangulation_mixte", f"axe triangulé ({r['n_inliers']} vues, "
                        f"{r['angle_intersection_deg']}°)", dates[-1], [v["source"] for v in r["vues"]],
                        note=f"dates des vues {dates[0]} à {dates[-1]}", nature="triangulation_photos",
                        photos=[v["source"] for v in r["vues"]], rayons=rayons))
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
                    note=f"z {a['z']}, unicité {a['unicite']}, ombre à {a['az_ombre_grille']}°", nature="ombre_detecteur"))
    return out


# --------------------------------------------------------------------------- Q7
def au_sol(o):
    t = o.get("type")
    if t in TYPES_SOL:
        return True
    if t in TYPES_MATS:
        return False
    return o.get("hauteur") is not None and float(o["hauteur"]) <= 1.5


def _maha(a, b):
    C = a["cov"] + b["cov"]
    d = a["xy"] - b["xy"]
    return float(math.sqrt(max(d @ np.linalg.solve(C, d), 0.0)))


def controle_q7(o, m, toutes):
    """(admise, motif, corroborée_par) d'une mesure m pour l'objet o au titre de Q7."""
    nat = m.get("nature")
    if au_sol(o) or nat in ("inventaire",):
        return True, None, None
    autres = [x for x in toutes if x is not m and x.get("valide", True)]
    if nat == "triangulation_photos":
        return True, None, None
    if nat == "rayon_photo_regle":
        return False, "rayon photo borné par une règle : pas une triangulation (mât, Q7)", None
    if nat in ("pixel_ortho",) + tuple(NATURES_OMBRE):
        corr = []
        for x in autres:
            if x.get("nature") in NATURES_OMBRE | {"pixel_ortho"} and x.get("source") != m.get("source") \
                    and (_maha(m, x) <= MAHA_MAX or float(np.hypot(*(m["xy"] - x["xy"]))) <= 0.30):
                corr.append(f"{x['source']} ({x.get('nature')}, {float(np.hypot(*(m['xy'] - x['xy']))):.2f} m)")
        if m.get("corroboration"):
            corr.append(str(m["corroboration"]))
        if nat == "ombre_detecteur" and m["statut"] == "probante":
            corr.append("orthos 2022 et 2024 concordantes")
        if nat == "pixel_ortho" and not any(("ombre" in c) or ("lecture" in c) for c in corr):
            return False, ("lecture pixel_ortho sur un mât (tache de la lanterne déversée sur l'ortho non vraie) sans départ "
                           "d'ombre corroboré ni triangulation (Q7)"), corr or None
        if not corr:
            return False, "départ d'ombre non corroboré (une seule lecture) : indice (Q7)", None
        return True, None, corr
    return True, None, None


# --------------------------------------------------------------------------- Q6
def _cat():
    import coherence_poses as PO
    return {p["id"]: p for p in PO.catalogue()}


def plancher_q6(m, cat):
    """Plancher géométrique d'une mesure photo (photos citées) ; covariance de la triangulation mixte à partir de
    ses résidus réels. Renvoie (cov, info) ou (None, None)."""
    import coherence_accord as AC
    import coherence_poses as PO
    if m.get("nature") not in NATURES_PHOTO:
        return None, None
    if m.get("rayons"):
        rays, pl, azs, res = [], [], [], []
        for r in m["rayons"]:
            p = cat.get(r["photo"])
            sg = PO.sigma_deg(p, r["d_m"]) if p else 0.5
            s = r["d_m"] * math.radians(sg)
            e = r["d_m"] * math.radians(r["residu_deg"])
            u = np.array([math.sin(math.radians(r["az"])), math.cos(math.radians(r["az"]))])
            rays.append((np.zeros(2), u, np.array([u[1], -u[0]]), s))
            pl.append(s)
            azs.append(r["az"])
            res.append(e)
        th = AC.angle_max(azs)
        base = float(np.median(pl))
        rms = float(np.sqrt(np.mean(np.square(res))))
        J = sum(np.outer(n, n) / s ** 2 for _, _, n, s in rays)
        chi2 = sum((e / s) ** 2 for e, (_, _, _, s) in zip(res, rays))
        k = max(1.0, chi2 / max(len(rays) - 2, 1))
        w, V = np.linalg.eigh(np.linalg.inv(J + np.eye(2) * 1e-9) * k)
        s1, s2 = math.sqrt(max(w[0], 0)), math.sqrt(max(w[1], 0))
        s1 = max(s1, base, rms / math.sqrt(len(rays)))
        s2 = SIGMA_INFINI if th < ANGLE_MIN else max(s2, base / math.sin(math.radians(th)))
        cov = s1 ** 2 * np.outer(V[:, 0], V[:, 0]) + s2 ** 2 * np.outer(V[:, 1], V[:, 1])
        return cov, dict(origine="résidus de la triangulation", n=len(rays), angle_deg=round(th, 1), rms_m=round(rms, 3),
                         plancher_m=round(base, 3), sigma_travers=round(s1, 3), sigma_profondeur=round(s2, 3))
    cams = [cat[p]["cam"].C for p in m.get("photos") or [] if p in cat]
    sgs = []
    for p in m.get("photos") or []:
        if p in cat:
            d = float(np.hypot(*(m["xy"] - cat[p]["cam"].C[:2])))
            sgs.append(PO.sigma_deg(cat[p], d))
    pg = AC.plancher_geometrique(m["xy"], cams, sgs)
    if pg is None:
        return None, dict(origine="aucune photo calée citée : profondeur et travers non bornés par la géométrie")
    return pg["cov"], dict(origine="plancher des photos citées", n=pg["n"], angle_deg=pg["angle_deg"],
                           sigma_travers=pg["sigma_lat"], sigma_profondeur=pg["sigma_prof"])


def appliquer_plancher(m, cov_pl, info):
    """Covariance finale = max(saisie, plancher) le long des axes du plancher ; σ saisi sous le plancher refusé."""
    if cov_pl is None:
        return m
    w, V = np.linalg.eigh(cov_pl)
    out = np.zeros((2, 2))
    refus = []
    for k in range(2):
        v = V[:, k]
        s_pl = math.sqrt(max(w[k], 0.0))
        s_m = _sig_dir(m["cov"], v)
        if m.get("sigma_saisi") and s_m < 0.9 * s_pl:
            refus.append(f"{s_m:.2f} m < plancher {s_pl:.2f} m")
        out += max(s_pl, s_m) ** 2 * np.outer(v, v)
    m2 = dict(m, cov=out, sigma_m=round(_sig_max(out), 3), q6=dict(info, sigma_saisi_m=m["sigma_m"], refus=refus or None))
    if refus:
        m2["sigma_saisi_refuse"] = True
    return m2


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
        mah = _maha(ref, m)
        (garde if mah <= MAHA_MAX else rejet).append(dict(m, mahalanobis=round(mah, 2)))
    W = sum(np.linalg.inv(m["cov"]) for m in garde)
    Cf = np.linalg.inv(W)
    xy = Cf @ sum(np.linalg.inv(m["cov"]) @ m["xy"] for m in garde)
    return dict(xy=xy, cov=Cf, sigma_m=round(max(_sig_max(Cf), SIGMA_MIN), 3), retenues=garde, ecartees=rejet)


def preparer(objets, carte, res, ombres, valide_pour_photo, anterieure_travaux):
    """Position source, source brute (P9), mesures candidates avec validité de date, Q7 et plancher Q6.
    Ne combine rien : le test d'accord image (Q1) se fait ensuite, puis `appliquer`."""
    brutes = mesures_brutes(objets, ombres, carte)
    cat = _cat()
    for o in objets:
        from valider_regles_implantation import classe_preuve
        pb, dmb, src = position_brute(o, res)
        o["p_source"] = np.asarray(o["p0"], float).copy()
        o["p_brut"], o["dmax_brut"], o["source_brute"] = pb, dmb, src
        o["p_brut_source"], o["dmax_brut_source"], o["source_brute_origine"] = pb.copy(), dmb, src
        o["sigma_brut_source"] = float(classe_preuve(o.get("source"), o.get("confiance"), res)[1])
        o["mesures"] = []
        for m in brutes.get(o["id"], []):
            ok, motif = True, None
            if m["date"] and not valide_pour_photo(o, m["date"]):
                ok, motif = False, f"mesure du {m['date']} non valable pour l'état 2026 de l'objet ({o['statut']})"
            elif m["source"] != "revue_coherence" and m["date"] and m["date"] <= FIN_TRAVAUX_2025 and o.get("_emprise_travaux") \
                    and anterieure_travaux(o):
                ok, motif = False, "mesure antérieure aux travaux, objet dans l'emprise (FUS-DATE-02, sans appui)"
            o["mesures"].append(dict(m, valide=ok, motif_rejet=motif, cov_saisie=np.asarray(m["cov"], float).copy()))
        for k, m in enumerate(o["mesures"]):
            if not m["valide"]:
                continue
            cov_pl, info = plancher_q6(m, cat)
            m2 = appliquer_plancher(m, cov_pl, info) if cov_pl is not None else dict(m, q6=info)
            if m2.get("nature") in ("pixel_ortho", "lecture_ombre") and m2["sigma_m"] < SIGMA_PLAN_MIN:
                m2 = dict(m2, cov=m2["cov"] * (SIGMA_PLAN_MIN / max(m2["sigma_m"], 1e-6)) ** 2, sigma_m=SIGMA_PLAN_MIN)
            ok7, motif7, corr = controle_q7(o, m2, o["mesures"])
            m2["q7"] = dict(admise=ok7, motif=motif7, corroboration=corr)
            if not ok7 and m2["statut"] == "probante":
                m2["statut"], m2["motif_indice"] = "indice", "Q7 : " + motif7
            o["mesures"][k] = m2


def appliquer(objets, q1=None):
    """Q1 (résultats d'accord par mesure), combinaison, Q8 ; remplace p0 / σ / d_max / preuve par la mesure combinée.
    q1 : {(objet, index de mesure): résultat coherence_accord.accord}. Renvoie le journal."""
    import coherence_accord as AC
    q1 = q1 or {}
    journal = []
    for o in objets:
        A = np.asarray(o["p_source"], float)
        lat_obs = None
        for k, m in enumerate(o["mesures"]):
            r = q1.get((o["id"], k))
            if r is None:
                continue
            m["q1"] = {kk: v for kk, v in r.items() if kk != "photos"}
            m["q1_photos"] = r["photos"]
            if m["statut"] != "probante" or not m["valide"]:
                continue
            if r["verdict"] == "accord":
                if m.get("nature") in NATURES_PHOTO and not m.get("rayons"):
                    # (une triangulation mixte garde la covariance de ses propres résidus, sur toutes ses vues)
                    # Q6 : la covariance vient alors des photos qui OBSERVENT la mesure (dispersion réelle des axes,
                    # plancher d·σ_pose et d·σ_pose / sin(angle)) ; elle remplace le plancher des seules photos citées
                    vus = [(l["cam_c"], l["axe_X"], l["d_m"], l["sigma_deg"]) for l in r["photos"]
                           if l.get("cam_c") is not None and l["photo"] in r["photos_X_observee"] and l.get("axe_X") is not None]
                    cp = AC.covariance_photo(m["xy"], vus)
                    if cp is not None:
                        q6_cite = m.get("q6")
                        m.update(appliquer_plancher(dict(m, cov=m["cov_saisie"]), cp["cov"],
                                                    dict(origine="résidus des axes observés (Q1)", n=len(vus),
                                                         angle_deg=cp["angle_deg"], rms_m=cp["rms_m"],
                                                         sigma_travers=cp["sigma_lat"], sigma_profondeur=cp["sigma_prof"],
                                                         plancher_photos_citees=q6_cite)))
            elif r["verdict"] in ("desaccord", "contradictoire", "accord_insuffisant"):
                m["statut"], m["motif_indice"] = "indice", f"Q1 : {r['verdict']} avec les photos décisives de la planche"
                lo = r.get("laterale_observee")
                if lo and lo.get("significative") and (lat_obs is None or lo["n"] > lat_obs["n"]):
                    lat_obs = lo
            elif r["verdict"] == "non_concluant":
                m["q1_non_concluant"] = True
        if lat_obs is not None:
            ell = np.asarray(lat_obs["direction"], float)
            cov = lat_obs["sigma_m"] ** 2 * np.outer(ell, ell) + SIGMA_INFINI ** 2 * np.outer([ell[1], -ell[0]], [ell[1], -ell[0]])
            o["mesures"].append(dict(_mesure(o["id"], lat_obs["position"], lat_obs["sigma_m"], "laterale_observee_q1",
                                             f"composante latérale observée par {lat_obs['n']} axe(s) détecté(s) (Q1)", None, [],
                                             cov=cov, nature="laterale_observee",
                                             note=f"décalage {lat_obs['decalage_m']:+.2f} ± {lat_obs['sigma_m']:.2f} m le long de "
                                                  f"{lat_obs['direction']}"), valide=True, motif_rejet=None,
                                     q7=dict(admise=True, motif=None, corroboration=None)))
        probantes = [m for m in o["mesures"] if m["valide"] and m["statut"] == "probante"]
        comb = combiner(probantes)
        if comb is None:
            continue
        p_old = np.asarray(o["p0"], float)
        # Q8 : compatibilité mesure <-> source d'origine
        sig_src = max(float(o.get("sigma_brut_source") or o["sigma"]), SIGMA_MIN)
        src = dict(xy=np.asarray(o["p_brut_source"], float), cov=np.eye(2) * sig_src ** 2)
        maha = _maha(dict(xy=comb["xy"], cov=comb["cov"]), src)
        dates = sorted(m["date"] for m in comb["retenues"] if m.get("date"))
        date_m = dates[-1] if dates else None
        apres = bool(date_m and date_m > FIN_TRAVAUX_2025)
        q8 = dict(mahalanobis=round(maha, 2), sigma_source_m=sig_src, date_mesure=date_m, mesure_posterieure_travaux=apres,
                  verdict="compatible" if maha <= MAHA_MAX else ("deplace_par_travaux" if apres else "mesure_contestee"))
        xy, cov = comb["xy"], comb["cov"]
        if maha <= MAHA_MAX and _sig_max(cov) > 1.0:
            W = np.linalg.inv(cov) + np.linalg.inv(src["cov"])
            cov = np.linalg.inv(W)
            xy = cov @ (np.linalg.inv(comb["cov"]) @ comb["xy"] + np.linalg.inv(src["cov"]) @ src["xy"])
            q8["direction_non_observee_fixee_par_la_source"] = True
        o["q8"] = q8
        if q8["verdict"] == "deplace_par_travaux":
            o["deplace_travaux"] = True
            o["statut_2026_source"] = o["statut"]
            o["statut_2026_maj"] = f"déplacé lors des travaux 2025 (mesure du {date_m}, {maha:.1f}σ de la source)"
        sig = round(max(_sig_max(cov) if _sig_max(cov) < SIGMA_INFINI / 2 else
                        float(math.sqrt(min(np.linalg.eigvalsh(cov)))), SIGMA_MIN), 3)
        o["mesure"] = dict(xy=xy, sigma_m=sig, cov=cov, sources=sorted({m["source"] for m in comb["retenues"]}),
                           retenues=[dict(source=m["source"], methode=m["methode"], nature=m.get("nature"),
                                          xy=[round(float(v), 3) for v in m["xy"]], sigma_m=m["sigma_m"], date=m["date"],
                                          preuves=m["preuves"], q1=(m.get("q1") or {}).get("verdict"),
                                          q6=m.get("q6")) for m in comb["retenues"]],
                           ecartees=[dict(source=m["source"], xy=[round(float(v), 3) for v in m["xy"]], sigma_m=m["sigma_m"],
                                          mahalanobis=m.get("mahalanobis")) for m in comb["ecartees"]],
                           d_p0_m=round(float(np.hypot(*(xy - p_old))), 3), q8=q8)
        o["p0"] = np.asarray(xy, float)
        o["preuve_avant_mesure"] = (o["preuve"], o["sigma"], o["dmax"])
        o["preuve"] = "mesure"
        o["sigma"] = sig
        o["dmax"] = round(max(3 * sig, 0.3), 3)
        o["p_brut"], o["dmax_brut"] = o["p0"].copy(), o["dmax"]
        o["source_brute"] = "mesure (" + ", ".join(o["mesure"]["sources"]) + ")"
        journal.append(dict(objet=o["id"], d_m=o["mesure"]["d_p0_m"], sigma_m=sig, sources=o["mesure"]["sources"],
                            q8=q8["verdict"]))
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
