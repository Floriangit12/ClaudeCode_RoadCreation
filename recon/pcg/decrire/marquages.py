"""Famille « marquages » de la description v2 (schéma description_scene_v2/0.3), site complet : GAM d'abord,
détection ensuite, règles pour ce qui manque, v1 comme simple indice.

Usage :
    python recon/pcg/decrire/marquages.py [--sortie DOSSIER] [--rapport RAPPORT.json] [--indices FICHIER]
    (normalement appelé par composer.py, qui écrit aussi le manifeste et lance la validation)
Sorties (défaut recon/out/paquet_jardin/v2/description/base) :
    marquages.geojson                 entités paramétriques (Lambert-93), une par ligne, triées par id : fabriquées
    marquages_correspondance.geojson  devenir de chacun des 996 marquages v1 (géométrie nulle), justifié
    marquages_hypotheses.geojson      toutes les hypothèses examinées (GAM, plan 2025, ortho 2022, règles, indices v1) :
                                      source, score S, décision, entité retenue (traçabilité, non fabriqué)
    marquages_indices_v1.geojson      indices v1 paramétrés (marquages_indices_v1, non fabriqués)

Priorité des sources par élément (FUS-SRC-001, marquages_sources) :
    1. levé GAM 2026 (Meylan_Topo.dwg) : polylignes classées (marquages_gam_classer) puis entités normatives
       (marquages_gam_entites) : zébras, flèches IISR ajustées, blocs VELO / PMR / FLECHE, chevrons, dents, zigzags,
       hachures, axes et tirets levés ; fait foi pour l'état 2026 ;
    2. plan projet 2025 calé (zone des travaux, éléments absents du GAM) : détection des flèches par voie
       (DET-FLE-004), des zébras par périodicité (DET-ZEB-009), des lignes le long des bords de voie (DET-PLN-016),
       et confirmation guidée des indices v1 (detection_indices) ;
    3. ortho PCRS 5 cm 2022 hors des zones refaites ou construites : mêmes détecteurs (DET-FLE-003, DET-ZEB-009,
       DET-LIG-010/011) ; une marque supprimée par les travaux n'est pas un fantôme sans preuve d'effacement
       postérieure aux travaux (aucune photo après 08/2025) : elle est retirée (pas de taches blanches) ;
    4. règles « deduire_si_absent » (marquages_inference) : lignes d'arrêt (MQ-LEF-002, MQ-LEF-011), flèches par voie
       (INF-FLE-004, MQ-FLE-003 à 006, MQ-DET-001), passages par groupe R12 (MQ-DET-004, MQ-PP-004), traversées
       cyclables (MQ-CYC-007), zigzags d'arrêt de bus (MQ-DET-009), files (MQ-DET-002, MQ-LIG-003) ;
    5. v1 : indice sémantique (existence, type, couleur, usure) et fenêtre de recherche ; aucune géométrie v1.
Fusion (marquages_fusion) : appariement FUS-ASS-003 (portes + hongrois), score FUS-SCO-002, accrochage normatif
FUS-SNP-004, conflits FUS-CON-005. Contraintes (marquages_contraintes) : interruptions des lignes aux passages, aux
lignes d'effet et aux zigzags (MQ-LIG-002, MQ-DET-010), dégagement des bordures levées GAM (2u), aucune ligne
inférée dans l'aire du carrefour (MQ-LIG-001).
Chaque entité porte src (gam | plan2025 | ortho2022 | regle:<id> | v1), confiance, score, sources [{src, ref, c, S}],
regles [ids] et lien_v1.
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import detection_fleches as DF  # noqa: E402
import detection_indices as DI  # noqa: E402
import detection_lignes as DL  # noqa: E402
import detection_zebras as DZ  # noqa: E402
import marquages_commun as M  # noqa: E402
import marquages_fusion as FU  # noqa: E402
import marquages_gam_entites as GE  # noqa: E402
import marquages_indices_v1 as MI  # noqa: E402
import marquages_lignes as LG  # noqa: E402
import marquages_sources as S  # noqa: E402
import marquages_symboles as SY  # noqa: E402
import xodr_echantillonne as X  # noqa: E402
from commun import (DONNEES, PAQUET, SORTIE, SPECS, VECTEURS, ZONE, abscisses, arrondi, ecrire_geojson, point_a,  # noqa: E402
                    lire_geojson, projeter, repere)

SCHEMA_ID = "description_scene_v2/0.3"
FICHIER = "marquages.geojson"
FICHIER_CORR = "marquages_correspondance.geojson"
FICHIER_HYP = "marquages_hypotheses.geojson"
FICHIER_IND = "marquages_indices_v1.geojson"
REFERENCES = dict(MI.REFERENCES)
REFERENCES.update({
    "plan_projet_2025": (VECTEURS / "plan_projet_2025/georef.json", "plan projet 2025 calé (affine, RMSE 3 cm) : détection DET-FLE-004, "
                         "DET-ZEB-009, DET-PLN-016 dans la zone des travaux"),
    "regles_conception": (SPECS / "regles_conception.json", "255 règles citées (MQ-*, DET-*, FUS-*, INF-*, VAL-*)"),
    "relief_zones": (DONNEES / "relief/relief_zones_2026.geojson", "zones de relief 2026"),
    "manoeuvres_2026": (DONNEES / "opendrive/manoeuvres_2026.json", "affectation des voies entrantes (INF-FLE-004)"),
    "gam_bordure_lin": (VECTEURS / "etat_2026/bordure_lin_L93.geojson", "bordures levées GAM 2026 (dégagement des marques)"),
})
SCRIPTS = sorted(set(MI.SCRIPTS + ["marquages.py", "marquages_indices_v1.py", "marquages_sources.py", "marquages_gam_classer.py",
                                   "marquages_gam_entites.py", "marquages_fusion.py", "marquages_inference.py",
                                   "marquages_contraintes.py", "detection_commun.py", "detection_fleches.py",
                                   "detection_zebras.py", "detection_lignes.py", "detection_indices.py",
                                   "marquages_supports.py", "marquages_chronovelo.py"]))
SEUIL_CONFIRME = 0.5           # c_detection d'un indice guidé confirmé
SEUIL_INFIRME = 0.2            # en dessous (image admissible) : indice infirmé


# --------------------------------------------------------------------------- indices v1
def charger_indices(chemin=None):
    """Indices v1 paramétrés : (features L93, correspondance v1 d'origine, rapport) ; chemin : fichier déjà calculé
    (développement) sinon marquages_indices_v1.construire()."""
    if chemin:
        feats = lire_geojson(chemin)
        corr = lire_geojson(Path(chemin).with_name(Path(chemin).stem + "_correspondance.geojson")) \
            if Path(chemin).with_name(Path(chemin).stem + "_correspondance.geojson").exists() else []
        return feats, corr, {}
    return MI.construire()


def interne(f):
    from marquages_controles import entite_locale
    e = entite_locale(f)
    e["lien_v1"] = list(e.get("lien_v1", []))
    return e


# --------------------------------------------------------------------------- détection guidée des indices
def _points(e):
    import marquages_reprises as RP
    if e["classe"] in ("ligne", "transversale"):
        return e["geom"][1]
    polys = RP.empreinte(e)
    return np.vstack([r for poly in polys for r in poly]) if polys else np.atleast_2d(e["geom"][1][0] if e["geom"][0] == "LineString" else
                                                                                      np.vstack([r for p in e["geom"][1] for r in p]))


def verifier_indice(e):
    """Détection guidée sur le(s) raster(s) admissible(s) de la zone de l'indice (FUS-SRC-001 : plan 2025 puis ortho 2022 en
    zone refaite à l'identique ; plan seul en zone neuve ; ortho seule en zone conservée) -> {raster, etat, c, mesure}."""
    import marquages_reprises as RP
    Q = _points(e)
    etat = S.etat_majoritaire(Q)
    rasters = DI.rasters_pour(etat)
    if not rasters:
        return {"raster": None, "etat": etat, "c": None, "mesure": None}
    best = None
    for raster in rasters:
        if e.get("couleur") in ("jaune", "ocre") and raster == "plan2025":
            raster = "plan2025_orange"
        if e["classe"] in ("ligne", "transversale"):
            from marquages_controles import _pieces
            q = dict(e, type="discontinue") if e["classe"] == "transversale" else e
            mes = DI.verifier_ligne(raster, e["geom"][1], _pieces(q, e["geom"][1]))
            c = None if mes is None else mes["fraction"]
            if mes is not None and mes.get("fausse_alarme") is not None and mes["fausse_alarme"] > 0.5 and e.get("type") == "discontinue":
                c = c * 0.5                   # motif peint partout : tirets non confirmés (continue ou autre marque)
        elif e["classe"] == "passage" and e["type"] == "zebra":
            mes = DI.verifier_zebra(raster, e)
            c = None if mes is None else DZ.c_detection(mes["pic_sur_fond"]) * (1.0 if mes["pas_ok"] else 0.5)
        else:
            polys = RP.empreinte(e)
            if not polys:
                continue
            mes = DI.verifier_empreinte(raster, polys)
            c = None if mes is None else DI.c_empreinte("ortho2022" if raster == "ortho2022" else "plan2025", mes)
        if c is not None and (best is None or c > best["c"]):
            best = {"raster": raster, "etat": etat, "c": c, "mesure": mes}
    return best or {"raster": rasters[0], "etat": etat, "c": None, "mesure": None}


def src_raster(r):
    return "plan2025" if (r or "").startswith("plan") else r


def translater(e, v):
    """Translation d'une entité interne (pose, géométrie, files, origine des bandes)."""
    v = np.asarray(v, float)
    if "pose" in e:
        e["pose"] = dict(e["pose"], origine_local=np.asarray(e["pose"]["origine_local"], float) + v)
    t, g = e["geom"]
    if t == "LineString":
        e["geom"] = (t, np.asarray(g) + v)
    elif t in ("Polygon", "MultiPolygon"):
        e["geom"] = (t, [[np.asarray(r) + v for r in poly] for poly in g])
    if "files" in e:
        e["files"] = [dict(fl, axe=np.asarray(fl["axe"]) + v) for fl in e["files"]]
    if "origine_bandes_local" in e:
        e["origine_bandes_local"] = np.asarray(e["origine_bandes_local"]) + v
    if "pose" in e and e["classe"] in ("fleche", "symbole"):
        g = GE.geom_posee(e)
        if g is not None:
            e["geom"] = g


# --------------------------------------------------------------------------- détections libres
def detections(reseau, toutes_zones=False):
    out = {"fleches": [], "zebras": [], "lignes": []}
    for r in ("plan2025", "ortho2022"):
        out["fleches"] += DF.detecter(reseau, r, toutes_zones)
        out["zebras"] += DZ.balayer(reseau, r, toutes_zones)
        out["lignes"] += DL.lignes_bords(reseau, r, admissible_seul=not toutes_zones)
    return out


def _ent_det_fleche(d, n, loc):
    eid = GE.ident("MF", 6000 + n)
    o = d["origine"]
    e = GE.base(eid, "fleche", "directionnelle", o, [], "", loc)
    e["gam"] = []
    src = d["source"]
    e["src"] = src
    e["sources"] = []
    e.update({"gabarit": d["gabarit"], "echelle": 1.0, "pose": {"origine_local": o, "cap_deg": d["cap_deg"], "cap_source": "voie"},
              "ancrage": {"type": "xodr", "route": d["route"], "voie": d["voie_id"], "section_s": round(d["section_s"], 3),
                          "s": d["s"], "t": d["x"]},
              "detection": {k: d[k] for k in ("ncc", "ncc_tiret", "scores", "statut", "voie")}, "regles": [
                  "DET-FLE-004" if src == "plan2025" else "DET-FLE-003", "DET-FLE-006", "FUS-SNP-004"]})
    e["prov"] = {"geometrie": {"src": src, "ref": f"détection rectifiée par voie {d['voie']} s = {d['s']:.2f} (NCC {d['ncc']:.2f}, "
                               f"typage par parties {d['statut']}) ; gabarit IISR posé", "conf": "moyenne"}}
    return e


def _ent_det_zebra(reseau, d, n, loc):
    r = reseau[d["route"]]
    tb = np.array(d["t_bandes"])
    s_c = 0.5 * (d["s_min"] + d["s_max"])
    x, y, h = X.point_st(r, np.array([s_c, s_c]), np.array([tb[0], tb[-1]]))
    A, B = np.array([x[0], y[0]]), np.array([x[1], y[1]])
    pas_mes = d["pas_m"]
    vide = min(0.80, max(0.50, pas_mes - 0.50))
    pas = 0.5 + vide
    nb = int(round((tb[-1] - tb[0]) / pas_mes)) + 1
    B = A + (B - A) / max(np.hypot(*(B - A)), 1e-9) * pas * (nb - 1)
    eid = GE.ident("MP", 6000 + n)
    e = GE.base(eid, "passage", "zebra", np.vstack([A, B]), [], "", loc)
    e["gam"], e["src"], e["sources"] = [], d["source"], []
    present = {int(round((t - tb[0]) / pas_mes)) for t in tb}
    e.update({"geom": ("LineString", np.vstack([A, B])), "largeur_bande_m": 0.5, "intervalle_m": round(vide, 3), "pas_axe_m": round(pas, 3),
              "longueur_bande_m": round(max(2.5, min(d["longueur_bande_m"], 6.0)), 2), "cap_bandes_deg": round(math.degrees(h[0]) % 360.0, 3),
              "nb_bandes": len(present), "nb_emplacements": nb, "coupures": [i for i in range(nb) if i not in present],
              "detection": {k: d[k] for k in ("route", "s", "pic_sur_fond", "pas_m", "nb_bandes")},
              "regles": ["DET-ZEB-009", "MQ-PP-004", "MQ-DET-003", "FUS-SNP-004"]})
    e["prov"] = {"geometrie": {"src": d["source"], "ref": f"périodicité route {d['route']} s = {d['s']:.1f} (pic/fond {d['pic_sur_fond']}, "
                               f"pas {pas_mes:.3f} m, {d['nb_bandes']} bandes) ; bandes normatives (MQ-PP-004)", "conf": "moyenne"}}
    return e


# --------------------------------------------------------------------------- fusion par classe
class Journal:
    def __init__(self):
        self.hyp = []          # hypothèses : {id, classe, type, src, S, c, decision, entite, ref, geom}
        self.devenir = {}      # MQ -> (devenir, entité, note)

    def h(self, **k):
        self.hyp.append(k)


def _indices_par_classe(ind):
    out = collections.defaultdict(list)
    for e in ind:
        out[e["classe"]].append(e)
    return out


def _confirmer(e_ind, ver, journal, prefixe_note=""):
    """Indice confirmé par l'image : entité de source image (forme normative de l'indice, pose recalée)."""
    e = dict(e_ind)
    raster = src_raster(ver["raster"])
    e["src"] = raster
    e["etat_zone"] = ver["etat"]
    e["sources"] = []
    FU.ajouter_source(e, "v1", f"indice v1 {e_ind['id']} ({', '.join(e_ind['lien_v1'][:6])}{'…' if len(e_ind['lien_v1']) > 6 else ''})",
                      1.0, ver["etat"])
    mes = ver["mesure"] or {}
    FU.ajouter_source(e, raster, f"détection guidée sur {ver['raster']} : " + json.dumps(arrondi(mes), ensure_ascii=False), ver["c"], ver["etat"])
    if e["classe"] not in ("ligne", "transversale") and mes and (abs(mes.get("dx", 0)) > 0.02 or abs(mes.get("dy", 0)) > 0.02):
        translater(e, (mes["dx"], mes["dy"]))
        e["recalage_image_m"] = [mes["dx"], mes["dy"]]
    e["prov"] = dict(e.get("prov", {}))
    e["prov"]["existence"] = {"src": raster, "ref": f"indice v1 confirmé par détection guidée (c = {ver['c']:.2f})", "conf": "moyenne"}
    if "pose" in e:
        e["prov"]["pose"] = {"src": raster, "ref": "pose recalée sur l'image (translation ± 0,30 m)", "conf": "moyenne"}
    e["regles"] = sorted(set(e.get("regles", [])) | {"FUS-SRC-001", "FUS-SNP-004", "VAL-IMG-007"})
    e["indice_v1"] = e_ind["id"]
    if e["classe"] == "passage" and e["type"] == "zebra" and not (0.5 - 1e-6 <= float(e["intervalle_m"]) <= 0.8 + 1e-6):
        # FUS-SNP-004 / MQ-PP-004 : bande 0,50, vide mesuré borné à [0,50 ; 0,80] ; axe conservé depuis la première bande
        A, B = e["geom"][1][:2]
        ax = (B - A) / max(float(np.hypot(*(B - A))), 1e-9)
        vide = min(0.8, max(0.5, float(e["intervalle_m"])))
        nb = int(e.get("nb_emplacements") or e["nb_bandes"])
        e["mesures_v1"] = {"intervalle_m": e["intervalle_m"], "pas_axe_m": e["pas_axe_m"]}
        e["intervalle_m"], e["largeur_bande_m"], e["pas_axe_m"] = round(vide, 3), 0.5, round(0.5 + vide, 3)
        e["geom"] = ("LineString", np.vstack([A, A + ax * e["pas_axe_m"] * (nb - 1)]))
        e["regles"] = sorted(set(e["regles"]) | {"MQ-PP-004"})
    fab = (e.get("fabrication") or {}).get("raison", "")
    if fab and "bâtiment" not in fab:
        e.pop("fabrication", None)      # statut lié au sol v1 (non à jour) : sans objet, le sol est fabriqué en v2
    if e.get("axe_v1_a_recaler") and not recaler_axe_detecte(e, ver["raster"]):
        return None                   # axe v1 non recalable sur l'image : la géométrie v1 est interdite
    return e


def fusion_ponctuelle(gam, det, ind, classe, porte, journal, loc, cap_libre=False):
    """Flèches et symboles : GAM (référence) <- détections libres <- indices v1 (appariement hongrois) ; indices non
    appariés : détection guidée. -> entités retenues."""
    ret = [dict(e) for e in gam]
    for e in ret:
        e["sources"] = list(e.get("sources", []))
    # détections libres
    for d in det:
        ok = apparier_un(ret, d, porte, cap_libre, loc=loc)
        if ok is not None:
            r = ret[ok]
            FU.ajouter_source(r, d["src"], d["prov"]["geometrie"]["ref"], d.get("_c", 1.0), r.get("etat_zone"))
            r.setdefault("detections", []).append(d["id"])
            journal.h(id=d["id"], classe=classe, src=d["src"], decision="apparie", entite=r["id"], S=d.get("_S"))
        else:
            d = dict(d)
            FU.ajouter_source(d, d["src"], d["prov"]["geometrie"]["ref"], d.get("_c", 1.0), d.get("etat_zone"))
            ret.append(d)
            journal.h(id=d["id"], classe=classe, src=d["src"], decision="nouvelle", entite=d["id"], S=d.get("_S"))
    # indices v1
    for e_ind in ind:
        ok = apparier_un(ret, e_ind, porte, cap_libre, meme_type=classe == "symbole", loc=loc)
        if ok is not None:
            r = ret[ok]
            FU.ajouter_source(r, "v1", f"indice v1 {e_ind['id']}", 1.0, r.get("etat_zone"), lien=e_ind["lien_v1"])
            FU.semantique_v1(r, e_ind)
            for mq in e_ind["lien_v1"]:
                journal.devenir[mq] = ("genere", r["id"], f"même marque que {r['id']} (source {r['src']}) ; indice v1 {e_ind['id']}")
            journal.h(id=e_ind["id"], classe=classe, src="v1", decision="apparie", entite=r["id"])
            continue
        traiter_indice_seul(e_ind, ret, journal)
    return ret


def apparier_un(ret, e, porte, cap_libre=False, meme_type=False, loc=None):
    """Appariement d'une hypothèse posée à la meilleure entité retenue (FUS-ASS-003) : porte 1,0 m / 15° (flèche), 2,0 m
    pour un bloc GAM ponctuel ; une flèche non levée (plan, ortho, indice v1) est la même que la flèche GAM de la même voie
    à moins de 8 m en long (MQ-FLE-005 : deux flèches d'une voie sont espacées d'au moins 10 m)."""
    cand = [i for i, r in enumerate(ret) if "pose" in r and (not meme_type or r["type"] == e["type"])]
    if not cand or "pose" not in e:
        return None
    pm, pd = porte
    best = None
    oe = np.asarray(e["pose"]["origine_local"], float)
    ve = None
    if loc is not None and e.get("src") != "gam" and e["classe"] == "fleche":
        # même voie à moins de 8 m en long d'une flèche levée : la même marque (deux flèches d'une voie sont espacées
        # d'au moins 10 m, MQ-FLE-005) ; le levé 2026 fixe la position réalisée (plan = projet, image 2022 = avant travaux)
        vs = loc.voies(oe + 1.5 * M.axes_cap(e["pose"]["cap_deg"])[1])
        ve = vs[0] if vs else None
    for i in cand:
        r = ret[i]
        o = np.asarray(r["pose"]["origine_local"], float)
        d = float(np.hypot(*(o - oe)))
        dc = S.angle_diff(r["pose"]["cap_deg"], e["pose"]["cap_deg"])
        if cap_libre:
            dc = min(dc, 180.0 - dc)
        g = PORTE_BLOC if (r.get("gam_pct") or e.get("gam_pct")) else pm
        cout = None
        if d <= g and dc <= pd:
            cout = d / g + 0.1 * dc / pd
        elif ve is not None and r.get("src") == "gam" and dc <= pd:
            vr = loc.voies(o + 1.5 * M.axes_cap(r["pose"]["cap_deg"])[1])
            if vr and vr[0]["route"] == ve["route"] and vr[0]["voie"] == ve["voie"] and abs(vr[0]["s"] - ve["s"]) <= 8.0:
                cout = 1.0 + abs(vr[0]["s"] - ve["s"]) / 8.0
        if cout is not None and (best is None or cout < best[0] - 1e-12):
            best = (cout, i)
    return None if best is None else best[1]


PORTE_BLOC = 2.0


def traiter_indice_seul(e_ind, ret, journal):
    """Indice v1 sans observation appariée : détection guidée ; confirmé -> ajouté ; sinon rejeté ou a_verifier."""
    ty = e_ind["type"]
    if e_ind["classe"] == "fantome":
        for mq in e_ind["lien_v1"]:
            journal.devenir[mq] = ("retire", None, "fantôme (marque 2022 effacée par les travaux 2025) : aucune preuve d'effacement "
                                   "postérieure aux travaux (aucune photo après 08/2025) -> non décrit (TQ-MQG-012, pas de tache)")
        journal.h(id=e_ind["id"], classe="fantome", src="v1", decision="retire_fantome")
        return
    if e_ind["classe"] == "zone" and ty in FU.TYPES_RASTER:
        for mq in e_ind["lien_v1"]:
            journal.devenir[mq] = ("retire", None, f"forme v1 « {ty} » d'origine raster sans source vectorielle (GAM) ni gabarit "
                                   "normatif : géométrie v1 interdite (refonte GAM d'abord)")
        journal.h(id=e_ind["id"], classe="zone", src="v1", decision="retire_forme_raster")
        return
    ver = verifier_indice(e_ind)
    c = ver["c"]
    seuil = SEUIL_CONFIRME if e_ind["classe"] in ("ligne", "transversale") else SEUIL_INFIRME   # ligne : crête sur la moitié au moins
    e = _confirmer(e_ind, ver, journal) if (c is not None and c >= seuil) else None
    if e is not None:
        FU.finaliser_score(e)
        if c < SEUIL_CONFIRME:
            e["usure"], e["couverture"] = "2", 0.62
            e["prov"]["usure"] = {"src": src_raster(ver["raster"]), "ref": f"marque faiblement visible (c = {c:.2f}) : usure 2", "conf": "faible"}
        ret.append(e)
        for mq in e_ind["lien_v1"]:
            journal.devenir[mq] = ("genere", e["id"], f"indice v1 {'confirmé' if c >= SEUIL_CONFIRME else 'faiblement confirmé'} sur "
                                   f"{ver['raster']} (c = {c:.2f}, P = {e['score']:.2f}) ; forme normative")
        journal.h(id=e_ind["id"], classe=e_ind["classe"], src=src_raster(ver["raster"]), decision="confirme" if c >= SEUIL_CONFIRME
                  else "faible", entite=e["id"], c=c)
        return
    if c is None and ver["raster"] is None and not e_ind.get("axe_v1_a_recaler"):
        # aucune image admissible (zone construite après 2022 hors plan) : indice seul, a_verifier (FUS-SCO-002 : P = 0,3)
        e = dict(e_ind)
        e["src"], e["etat_zone"], e["sources"] = "v1", ver["etat"], []
        FU.ajouter_source(e, "v1", f"indice v1 {e_ind['id']} invérifiable (aucun raster admissible en zone {ver['etat']})", 1.0, ver["etat"])
        e["a_verifier"] = True
        e["regles"] = sorted(set(e.get("regles", [])) | {"FUS-SRC-001", "FUS-SCO-002"})
        # aucune géométrie v1 FABRIQUÉE dans le carré (demande utilisateur ; revues du 11/10/2026 : MP-0370,
        # MS-0262..0265 peints à P = 0,30) : l'indice reste décrit (hypothèse) mais n'est pas fabriqué tant qu'une
        # photo postérieure aux travaux (Panoramax ≥ 2025-09) ne le confirme pas
        raison = (f"indice v1 seul (P = 0,30, zone {ver['etat']}) : hypothèse a_verifier non fabriquée, en attente d'une "
                  "photo postérieure aux travaux (FUS-SCO-002, FUS-SRC-001)")
        e["fabrication"] = {"statut": "non_fabrique", "raison": raison}
        ret.append(e)
        for mq in e_ind["lien_v1"]:
            journal.devenir[mq] = ("garde_non_fabrique", e["id"], raison)
        journal.h(id=e_ind["id"], classe=e_ind["classe"], src="v1", decision="inverifiable", entite=e["id"])
        return
    for mq in e_ind["lien_v1"]:
        journal.devenir[mq] = ("retire", None, f"indice v1 infirmé par l'image admissible {ver['raster']} (c = "
                               f"{'n.d.' if c is None else f'{c:.2f}'} < {seuil}) en zone {ver['etat']} : absent de l'état 2026 ou "
                               "non mesurable (géométrie v1 interdite)")
    journal.h(id=e_ind["id"], classe=e_ind["classe"], src="v1", decision="infirme", c=c, raster=ver["raster"])


def _aire_commune(pa, pb):
    """Aire commune approchée (rastérisation 5 cm) de deux listes de polygones -> (commune, aire de pa)."""
    P = np.vstack([r for poly in list(pa) + list(pb) for r in poly])
    x0, y0 = P.min(axis=0) - 0.1
    nx, ny = int((P[:, 0].max() - x0) / 0.05) + 3, int((P[:, 1].max() - y0) / 0.05) + 3
    if nx * ny > 4_000_000:
        return 0.0, 1.0
    a = M.raster_masque(pa, x0, y0, nx, ny, 0.05)
    b = M.raster_masque(pb, x0, y0, nx, ny, 0.05)
    return float((a & b).sum()) * 0.0025, float(a.sum()) * 0.0025


def _bbox_polys(polys):
    P = np.vstack([r for poly in polys for r in poly])
    return (*P.min(axis=0), *P.max(axis=0))


def fusion_surfaciques(gam, det, ind, journal):
    """Passages et zones : GAM <- détections (zébras) <- indices v1 (recouvrement d'empreinte ≥ 0,3 de l'indice ou axes de
    zébra à 1 m / 10°, FUS-ASS-003)."""
    import marquages_reprises as RP
    ret = [dict(e) for e in gam]
    for e in ret:
        e["sources"] = list(e.get("sources", []))
    emp = {id(e): RP.empreinte(e) for e in ret}
    for d in det:
        zs = [r for r in ret if r.get("type") == "zebra"]
        pr = FU.apparier_zebras([d], zs)
        if pr:
            r = zs[pr[0][1]]
            FU.ajouter_source(r, d["src"], d["prov"]["geometrie"]["ref"], d.get("_c", 1.0), r.get("etat_zone"))
            r.setdefault("detections", []).append(d["id"])
            journal.h(id=d["id"], classe="passage", src=d["src"], decision="apparie", entite=r["id"])
        else:
            d = dict(d)
            FU.ajouter_source(d, d["src"], d["prov"]["geometrie"]["ref"], d.get("_c", 1.0), d.get("etat_zone"))
            ret.append(d)
            emp[id(d)] = RP.empreinte(d)
            journal.h(id=d["id"], classe="passage", src=d["src"], decision="nouvelle", entite=d["id"])
    for e_ind in ind:
        pi = RP.empreinte(e_ind)
        best = None
        if pi:
            bi = _bbox_polys(pi)
            for r in ret:
                pr_ = emp.get(id(r))
                if not pr_:
                    continue
                br = _bbox_polys(pr_)
                if br[2] < bi[0] or bi[2] < br[0] or br[3] < bi[1] or bi[3] < br[1]:
                    continue
                com, ai = _aire_commune(pi, pr_)
                if ai > 0 and com / ai >= 0.3 and (best is None or com / ai > best[0]):
                    best = (com / ai, r)
        if best is None and e_ind.get("type") == "zebra":
            zs = [r for r in ret if r.get("type") == "zebra"]
            pr = FU.apparier_zebras([e_ind], zs)
            if pr:
                best = (None, zs[pr[0][1]])
        if best is not None:
            r = best[1]
            FU.ajouter_source(r, "v1", f"indice v1 {e_ind['id']}", 1.0, r.get("etat_zone"), lien=e_ind["lien_v1"])
            FU.semantique_v1(r, e_ind)
            rec = "axe" if best[0] is None else f"{best[0]:.2f}"
            for mq in e_ind["lien_v1"]:
                journal.devenir[mq] = ("genere", r["id"], f"même marque que {r['id']} (source {r['src']}, recouvrement {rec}) ; "
                                       f"indice v1 {e_ind['id']}")
            journal.h(id=e_ind["id"], classe=e_ind["classe"], src="v1", decision="apparie", entite=r["id"])
            continue
        n0 = len(ret)
        traiter_indice_seul(e_ind, ret, journal)
        for r in ret[n0:]:
            emp[id(r)] = RP.empreinte(r)
    return ret


def _ent_det_ligne(d, chaines, n, loc):
    ch = chaines[d["chaine"]]
    Q = ch.axe(d["t_off"], d["s0"], d["s1"])
    eid = GE.ident("ML", 6000 + n)
    e = GE.base(eid, "ligne", d["type"], Q, [], "", loc)
    e["gam"], e["src"], e["sources"] = [], d["source"], []
    role = LG.role_xodr(ch, 0.5 * (d["s0"] + d["s1"])) or ("axe", "défaut")
    w, pw = GE._largeur(None, role[0], e["branche"], False)
    e.update({"geom": ("LineString", M.douglas_peucker(Q, 0.001)),
              "ancrage": {"type": "xodr", "route": ch.route, "bords": ch.troncons(d["s0"], d["s1"]), "s0": round(d["s0"], 3),
                          "s1": round(d["s1"], 3), "t_off_m": round(d["t_off"], 4)},
              "largeur_m": w, "role": role[0] if role[0] in LG.ROLES_U else "axe", "interruptions": [],
              "detection": {k: d.get(k) for k in ("source", "n_vus", "couverture", "code")},
              "regles": ["DET-PLN-016" if d["source"] == "plan2025" else "DET-LIG-010", "DET-LIG-011", "TQ-DED-002", "FUS-SNP-004"]})
    e["longueur_m"] = round(float(abscisses(e["geom"][1])[-1]), 3)
    if d["type"] == "discontinue":
        e.update({"modulation": d["code"], "trait_m": d["trait_m"], "vide_m": d["vide_m"], "phase_m": 0.0, "modulation_source": "IISR",
                  "n_tirets": d["n_tirets"]})
    else:
        e["modulation"] = "continue"
    e["prov"] = {"geometrie": {"src": "xodr", "ref": f"bord {ch.cle} + t_off détecté ({d['t_off']:+.3f} m)", "conf": "haute"},
                 "existence": {"src": d["source"], "ref": f"crête détectée sur {d['source']} : {d.get('n_vus')} plage(s), "
                               f"couverture {d['couverture']:.2f}", "conf": "moyenne"},
                 "largeur_m": pw}
    return e


def fusion_lignes(gam, det, ind, journal, chaines, loc):
    """Lignes : GAM <- détections le long des bords (recouvrement ≥ 0,7 à 0,30 m : appariée ; < 0,3 : nouvelle) <- indices
    v1 (recouvrement ≥ 0,7 : apparié ; sinon réancrage OpenDRIVE puis détection guidée)."""
    ret = [dict(e) for e in gam]
    for e in ret:
        e["sources"] = list(e.get("sources", []))
    FU.preparer_refs(ret)
    for d in det:
        f, qui, _ = FU.recouvrement(d, ret)
        if f >= 0.7:
            for r in ret:
                if r["id"] in qui:
                    FU.ajouter_source(r, d["src"], d["prov"]["existence"]["ref"], d.get("_c", 1.0), r.get("etat_zone"))
            journal.h(id=d["id"], classe="ligne", src=d["src"], decision="apparie", entite=",".join(qui))
        elif f < 0.3 and d["type"] in ("continue", "discontinue") and d.get("_c", 0) >= 0.5:
            d = dict(d)
            FU.ajouter_source(d, d["src"], d["prov"]["existence"]["ref"], d.get("_c", 1.0), d.get("etat_zone"))
            FU.preparer_refs([d])
            ret.append(d)
            journal.h(id=d["id"], classe="ligne", src=d["src"], decision="nouvelle", entite=d["id"])
        else:
            journal.h(id=d["id"], classe="ligne", src=d["src"], decision="ecartee",
                      note=f"recouvrement {f:.2f}, type {d['type']}, c {d.get('_c')}")
    for e_ind in ind:
        f, qui, _ = FU.recouvrement(e_ind, ret)
        if f >= 0.7:
            for r in ret:
                if r["id"] in qui:
                    FU.ajouter_source(r, "v1", f"indice v1 {e_ind['id']}", 1.0, r.get("etat_zone"), lien=e_ind["lien_v1"])
                    FU.semantique_v1(r, e_ind)
            for mq in e_ind["lien_v1"]:
                journal.devenir[mq] = ("genere", qui[0], f"même ligne que {', '.join(qui)} (recouvrement {f:.2f}) ; indice v1 {e_ind['id']}")
            journal.h(id=e_ind["id"], classe="ligne", src="v1", decision="apparie", entite=",".join(qui))
            continue
        n0 = len(ret)
        e2 = reancrer(e_ind, chaines)
        traiter_indice_seul(e2, ret, journal)
        if len(ret) > n0:
            FU.preparer_refs(ret[n0:])
            if f >= 0.3:
                ret[-1]["recouvrement_partiel"] = {"lignes": qui, "part": round(f, 3)}
    return ret


def reancrer(e, chaines):
    """Ligne v1 sur axe propre (ancrage axe / v1) : réancrage sur un bord OpenDRIVE si le bord + t_off suit l'axe à 4 cm
    (p95) ; sinon l'axe sera recalé sur la crête détectée (detection guidée)."""
    if e["classe"] != "ligne" or e.get("ancrage", {}).get("type") != "axe" or e["ancrage"].get("source") != "v1":
        return e
    r = GE._ancrer(list(chaines.values()), e["geom"][1])
    if r is None:
        e = dict(e)
        e["axe_v1_a_recaler"] = True
        return e
    anc, Q, mes, ch = r
    e = dict(e)
    L0 = float(abscisses(e["geom"][1])[-1])
    e["ancrage"] = anc
    e["geom"] = ("LineString", M.douglas_peucker(Q, 0.001))
    L1 = float(abscisses(e["geom"][1])[-1])
    if e.get("interruptions"):
        k = L1 / max(L0, 1e-9)
        e["interruptions"] = [[round(a * k, 3), round(b * k, 3)] for a, b in e["interruptions"]]
    e["longueur_m"] = round(L1, 3)
    e["reancrage"] = {"bord": ch.cle, "lateral_p95_m": mes["lateral_gam_p95_m"]}
    e["prov"] = dict(e["prov"], geometrie={"src": "xodr", "ref": f"axe v1 réancré sur le bord {ch.cle} + t_off", "conf": "haute"})
    return e


def recaler_axe_detecte(e, raster):
    """Axe d'une ligne v1 non réancrée recalé sur la crête détectée (droite des moindres carrés sur les points de crête,
    ou polyligne lissée sur 2 m si l'axe est courbe) : la géométrie vient de l'image, plus du v1."""
    P = e["geom"][1]
    det = DL.detecter(raster, P, couloir=0.3)
    sig, peint = det["sig"], det["peint"]
    if peint.sum() < 10:
        return False
    Q, tg = point_a(P, sig[peint])
    n = np.c_[-tg[:, 1], tg[:, 0]]
    C = Q + n * det["t_crete"][peint][:, None]
    if len(P) <= 2 or M.rect_min(P)["W"] < 0.05:
        c0 = C.mean(axis=0)
        _, _, vt = np.linalg.svd(C - c0)
        u = vt[0] if float(vt[0] @ (P[-1] - P[0])) >= 0 else -vt[0]
        a = float(((P[0] - c0) @ u))
        b = float(((P[-1] - c0) @ u))
        Pn = np.vstack([c0 + u * a, c0 + u * b])
    else:
        k = max(1, int(round(1.0 / DL.PAS_S)))
        Cs = np.array([C[max(0, i - k):i + k + 1].mean(axis=0) for i in range(len(C))])
        Pn = M.douglas_peucker(Cs, 0.01)
        if len(Pn) < 2:
            return False
    L0 = float(abscisses(P)[-1])
    e["geom"] = ("LineString", Pn)
    L1 = float(abscisses(Pn)[-1])
    if e.get("interruptions"):
        k = L1 / max(L0, 1e-9)
        e["interruptions"] = [[round(a * k, 3), round(b * k, 3)] for a, b in e["interruptions"]]
    e["longueur_m"] = round(L1, 3)
    e["ancrage"] = {"type": "axe", "source": "detection"}
    e["prov"] = dict(e["prov"], geometrie={"src": src_raster(raster), "ref": f"axe recalé sur la crête détectée ({int(peint.sum())} "
                                           "rangées peintes)", "conf": "moyenne"})
    e.pop("axe_v1_a_recaler", None)
    return True


RANG_SRC = {"gam": 0, "plan2025": 1, "ortho2022": 2, "regle": 3, "v1": 4}


def _rang(e):
    s_ = str(e.get("src", "v1"))
    return RANG_SRC["regle" if s_.startswith("regle:") else s_ if s_ in RANG_SRC else "v1"]


def dedoublonner(entites, journal):
    """FUS-ASS-003 / MQ-DET-010 : (1) une flèche détectée sans indice qui recouvre l'emprise d'un zébra est un faux
    positif (bandes) : retirée (INF-FLE-006) ; (2) deux flèches ou deux symboles de même type dont les empreintes se
    recouvrent à 30 % ou plus sont la même marque : la source de rang supérieur (FUS-SRC-001) garde la géométrie, l'autre
    lui apporte son score et ses liens v1."""
    import marquages_contraintes as CT
    import marquages_reprises as RP
    from commun import dans_polygone, echantillons_interieurs
    zebras = [CT.emprise_zebra(e, marge=0.0) for e in entites if e["classe"] == "passage" and e["type"] == "zebra"]
    retires = set()
    for e in entites:
        if e["classe"] != "fleche" or not e.get("detection") or e.get("lien_v1"):
            continue
        P = np.vstack([r for poly in e["geom"][1] for r in poly])
        q = echantillons_interieurs([M.enveloppe_convexe(P)], 0.1)
        if any(float(dans_polygone(q, [Z]).mean()) >= 0.10 for Z in zebras):
            retires.add(e["id"])
            journal.h(id=e["id"], classe="fleche", src=e.get("src"), decision="retire_sur_zebra",
                      note="flèche détectée sur les bandes d'un zébra (faux positif, INF-FLE-006)")
    cyc_gam = [np.atleast_2d(np.asarray(e["pose"]["origine_local"], float)) for e in entites
               if e.get("src") == "gam" and e["classe"] == "symbole" and e["type"] in ("velo", "chevron")]
    zeb_gam = [CT.emprise_zebra(e, marge=0.0) for e in entites if e.get("src") == "gam" and e["classe"] == "passage" and e["type"] == "zebra"]
    for e in entites:
        if e["classe"] != "passage" or e["type"] != "traversee_cyclable" or e.get("src") == "gam":
            continue
        P = np.vstack([r for poly in RP.empreinte(e) for r in poly])
        pres = any(float(np.min(np.hypot(*(P - c).T))) < 1.5 for c in cyc_gam)
        sur = any(dans_polygone(P, [Z]).mean() > 0.05 for Z in zeb_gam)
        if pres or sur:
            retires.add(e["id"])
            for mq in e.get("lien_v1", []):
                journal.devenir[mq] = ("retire", None, "traversée cyclable 2026 décrite par le levé GAM (figurines et chevrons, "
                                       "MQ-CYC-007/008) : pavés du projet ou de 2022 non réalisés à cet endroit (FUS-SRC-001)")
            journal.h(id=e["id"], classe="passage", src=e.get("src"), decision="retire_gam_prioritaire")
    # barre levée isolée contenue dans un zébra : bande partielle du même passage (le zébra l'absorbe)
    zebras_e = [(e, CT.emprise_zebra(e, marge=0.05)) for e in entites if e["classe"] == "passage" and e["type"] == "zebra"]
    for e in entites:
        if e["classe"] != "symbole" or e["type"] != "barre" or e["id"] in retires:
            continue
        P = np.vstack([r for poly in e["geom"][1] for r in poly])
        q = echantillons_interieurs([M.enveloppe_convexe(P)], 0.05)
        for z, Z in zebras_e:
            if float(dans_polygone(q, [Z]).mean()) >= 0.5:
                retires.add(e["id"])
                for x in e.get("sources", []):
                    z.setdefault("sources", []).append(dict(x, ref=f"{e['id']} (bande levée du passage) : {x['ref']}"))
                for mq in e.get("lien_v1", []):
                    journal.devenir[mq] = ("genere", z["id"], f"bande du passage {z['id']} ; via {e['id']}")
                z["lien_v1"] = sorted(set(z.get("lien_v1", [])) | set(e.get("lien_v1", [])))
                z.setdefault("gam_bandes", []).extend(e.get("gam", []))
                journal.h(id=e["id"], classe="symbole", src=e.get("src"), decision="absorbe_par_zebra", entite=z["id"])
                break
    # flèche au droit d'un pictogramme levé hors bibliothèque (flèche coudée du carrefour) : le levé prime (rang 1)
    atyp = [e for e in entites if e.get("src") == "gam" and e["classe"] == "zone" and e["type"] == "divers"]
    for e in entites:
        if e["classe"] != "fleche" or e["id"] in retires or e.get("src") == "gam":
            continue
        for g in atyp:
            com, ae = _aire_commune(e["geom"][1], g["geom"][1])
            if ae > 0 and com / ae >= 0.2:
                retires.add(e["id"])
                for x in e.get("sources", []):
                    g.setdefault("sources", []).append(dict(x, ref=f"{e['id']} : {x['ref']}"))
                for mq in e.get("lien_v1", []):
                    journal.devenir[mq] = ("genere", g["id"], f"flèche relevée par le GAM sous la forme {g['id']} (hors gabarit IISR) ; via {e['id']}")
                g["lien_v1"] = sorted(set(g.get("lien_v1", [])) | set(e.get("lien_v1", [])))
                journal.h(id=e["id"], classe="fleche", src=e.get("src"), decision="absorbe_par_gam", entite=g["id"])
                break
    poses = [e for e in entites if e["classe"] in ("fleche", "symbole") and "geom" in e and e["id"] not in retires]
    emp = {e["id"]: e["geom"][1] for e in poses}
    bb = {k: (*np.vstack([r for poly in v for r in poly]).min(axis=0), *np.vstack([r for poly in v for r in poly]).max(axis=0)) for k, v in emp.items()}
    ordre = sorted(poses, key=lambda e: (_rang(e), -float(e.get("score") or S.existence([x["S"] for x in e.get("sources", [])])), e["id"]))
    gardes = []
    for e in ordre:
        b = bb[e["id"]]
        dup = None
        for g in gardes:
            if g["classe"] != e["classe"] or (g["classe"] == "symbole" and g["type"] != e["type"]):
                continue
            bg = bb[g["id"]]
            if bg[2] < b[0] or b[2] < bg[0] or bg[3] < b[1] or b[3] < bg[1]:
                continue
            com, ae = _aire_commune(emp[e["id"]], emp[g["id"]])
            _, ag = _aire_commune(emp[g["id"]], emp[e["id"]])
            if com / max(min(ae, ag), 1e-9) >= 0.30:
                dup = g
                break
        if dup is None:
            gardes.append(e)
            continue
        retires.add(e["id"])
        for x in e.get("sources", []):
            dup.setdefault("sources", []).append(dict(x, ref=f"{e['id']} : {x['ref']}"))
        dup["lien_v1"] = sorted(set(dup.get("lien_v1", [])) | set(e.get("lien_v1", [])))
        if e["classe"] == "fleche" and e.get("gabarit") != dup.get("gabarit") and not dup.get("conflit_norme"):
            dup["conflit_type_sources"] = {"retenu": dup.get("gabarit"), "autre": e.get("gabarit"), "source_autre": e.get("src")}
        for mq in e.get("lien_v1", []):
            journal.devenir[mq] = ("genere", dup["id"], f"même marque que {dup['id']} (empreintes superposées, source {dup.get('src')} "
                                   f"prioritaire) ; via {e['id']}")
        journal.h(id=e["id"], classe=e["classe"], src=e.get("src"), decision="fusionne", entite=dup["id"])
    return [e for e in entites if e["id"] not in retires]


# --------------------------------------------------------------------------- construction
CHAMPS_INTERNES = ("_seg", "_bb", "_c", "_S", "etat_zone", "axe_v1_a_recaler", "gam_pct_brut")


def _scores_detection(d, src, c):
    d["_c"] = c
    d["_S"] = round(S.score(src, c, d.get("etat_zone", "conserve")), 3)
    return d


DERNIER = {}                   # hypothèses et indices v1 de la dernière construction (écrits par ecrire)


def construire(indices=None):
    """-> (features marquages, features correspondance, rapport) ; hypothèses et indices v1 dans DERNIER."""
    reseau = X.lire_xodr()
    LG.RESEAU[:] = [reseau]
    loc = SY.Localisateur(reseau)
    chaines = {ch.cle: ch for ch in LG.chaines_reseau(reseau)}
    journal = Journal()
    # 1. GAM
    gam, j_gam = GE.entites(reseau, loc)
    for e in gam:
        journal.h(id=e["id"], classe=e["classe"], src="gam", decision="pose", entite=e["id"], S=e["sources"][0]["S"])
    # 2. indices v1 paramétrés
    feats_v1, corr_v1, rap_v1 = charger_indices(indices)
    ind = [interne(f) for f in feats_v1]
    # 3. détections libres (zone admissible seulement)
    det = detections(reseau)
    d_fl = [_scores_detection(_ent_det_fleche(d, i, loc), d["source"], DI.c_detection(d["source"], d["ncc"]))
            for i, d in enumerate(sorted([x for x in det["fleches"] if x["gabarit"]], key=lambda x: (x["source"], x["voie"], x["s"])))]
    d_zb = [_scores_detection(_ent_det_zebra(reseau, d, 100 + i, loc), d["source"], DZ.c_detection(d["pic_sur_fond"]))
            for i, d in enumerate(sorted(det["zebras"], key=lambda x: (x["source"], int(x["route"]), x["s"])))]
    d_lg = [_scores_detection(_ent_det_ligne(d, chaines, 200 + i, loc), d["source"], d["c_detection"])
            for i, d in enumerate(sorted(det["lignes"], key=lambda x: (x["source"], x["chaine"], x["s0"])))]
    GE.completer_geom(d_fl)
    for d in d_fl + d_zb + d_lg:
        d["etat_zone"] = S.etat_majoritaire(_points(d))
    # 4. fusion par classe
    par = _indices_par_classe(ind)
    g = collections.defaultdict(list)
    for e in gam:
        g[e["classe"]].append(e)
    fl = fusion_ponctuelle(g["fleche"], d_fl, par["fleche"], "fleche", FU.PORTES["fleche"], journal, loc)
    sy = fusion_ponctuelle(g["symbole"], [], par["symbole"], "symbole", FU.PORTES["symbole"], journal, loc, cap_libre=True)
    pa = fusion_surfaciques(g["passage"], d_zb, par["passage"], journal)
    zo = fusion_surfaciques(g["zone"], [], par["zone"], journal)
    li = fusion_lignes(g["ligne"], d_lg, par["ligne"], journal, chaines, loc)
    tr = []
    for e_ind in par["transversale"]:
        traiter_indice_seul(e_ind, tr, journal)
    for e_ind in par["fantome"]:
        traiter_indice_seul(e_ind, [], journal)
    entites = dedoublonner(fl + sy + pa + zo + li + tr, journal)
    # 5. inférence par règles (éléments absents)
    import marquages_inference as INF
    inf, j_inf, aps = INF.inferer(entites, reseau, loc)
    GE.completer_geom(inf)
    for e in inf:
        journal.h(id=e["id"], classe=e["classe"], src=e["src"], decision="infere", entite=e["id"], S=e["sources"][0]["S"] if e.get("sources") else None)
    entites += inf
    # MQ-CHR-001 / MQ-CYC-007 / VAL-XOD-008 : traversées Chronovélo du plan 2025 aux crosswalk « bicycle » non décrits
    import marquages_chronovelo as CH
    chv, j_chv = CH.traversees(entites, reseau, loc)
    for e in chv:
        journal.h(id=e["id"], classe=e["classe"], src=e["src"], decision="deduit_plan2025", entite=e["id"],
                  S=e["sources"][0]["S"] if e.get("sources") else None)
    entites += chv
    # 6. contraintes
    import marquages_contraintes as CT
    j_int = CT.interrompre(entites)
    entites, j_vides = _sans_peinture(entites, journal)
    # scores, confiance, champs finaux
    GE.completer_ancrage(entites, loc)
    for e in entites:
        if not e.get("sources"):
            FU.ajouter_source(e, e.get("src", "v1"), "source unique", 1.0, e.get("etat_zone"))
        FU.finaliser_score(e, regle_exige=str(e.get("src", "")).startswith("regle:"))
        if e.get("src", "").startswith("regle:") and any(x["src"] == "regle:MQ-LEF-011" for x in e["sources"]):
            e["score"], e["confiance"], e["a_verifier"] = 0.35, "faible", True
        e.setdefault("lien_v1", [])
        e.setdefault("regles", [])
    # supports des marques non levées (VAL-FLE-001, MQ-DET-010, FUS-CON-005 ; revues du 11/10/2026) : non fabriquées
    import marquages_supports as SU
    j_sup = SU.controler(entites, loc, reseau, journal.devenir)
    # FUS-SCO-002 : P < 0,3 -> rejeté (sauf élément exigé par une règle deduire_si_absent)
    rejetes = {e["id"] for e in entites if e["score"] < S.SEUIL_A_VERIFIER and not str(e.get("src", "")).startswith("regle:")}
    for e in entites:
        if e["id"] in rejetes:
            journal.h(id=e["id"], classe=e["classe"], src=e.get("src"), decision="rejete_score", S=e["score"])
            for mq in e.get("lien_v1", []):
                journal.devenir[mq] = ("retire", None, f"existence fusionnée P = {e['score']:.2f} < 0,30 (FUS-SCO-002) : rejeté")
    entites = [e for e in entites if e["id"] not in rejetes]
    # un marquage v1 n'est rattaché qu'à une entité : celle de son devenir (dernière décision du journal)
    par_id = {e["id"]: e for e in entites}
    for e in entites:
        e["lien_v1"] = sorted(mq for mq in e.get("lien_v1", []) if journal.devenir.get(mq, (None, None))[1] == e["id"])
    for mq, (fate, eid, _) in sorted(journal.devenir.items()):
        if fate == "genere" and eid in par_id and mq not in par_id[eid]["lien_v1"]:
            par_id[eid]["lien_v1"] = sorted(par_id[eid]["lien_v1"] + [mq])
    ids = [e["id"] for e in entites]
    doublons = [i for i, n in collections.Counter(ids).items() if n > 1]
    if doublons:
        raise RuntimeError(f"identifiants en double : {doublons[:10]}")
    feats = [feature(e) for e in sorted(entites, key=lambda e: e["id"])]
    corr = correspondance(corr_v1, journal, set(ids))
    hyp = hypotheses(journal, entites)
    rap = rapport(entites, journal, j_gam, j_inf, j_int, j_vides, aps, corr, det)
    rap["supports_non_leves"] = j_sup              # VAL-FLE-001, MQ-DET-010, FUS-CON-005 (non fabriqués)
    rap["traversees_chronovelo_plan2025"] = j_chv  # MQ-CHR-001, MQ-CYC-007, VAL-XOD-008
    # devenir des lignes v1 sur axe propre (213 indices « axe v1 » : réancrées sur le GAM ou le .xodr, recalées sur la crête
    # détectée, ou retirées)
    axe_v1 = [e["id"] for e in ind if e["classe"] == "ligne" and (e.get("ancrage") or {}).get("type") == "axe"
              and (e.get("ancrage") or {}).get("source") == "v1"]
    dec = {}
    for h in journal.hyp:
        if h["id"] in axe_v1:
            dec[h["id"]] = h
    par_e = {e.get("indice_v1"): e for e in entites if e.get("indice_v1")}
    bilan = collections.Counter()
    for i in axe_v1:
        h = dec.get(i, {})
        d = h.get("decision", "absent")
        if d == "apparie":
            bilan["reancree_sur_ligne_gam_ou_detectee"] += 1
        elif d in ("confirme", "faible"):
            e = par_e.get(i, {})
            a = e.get("ancrage", {})
            bilan["reancree_xodr" if a.get("type") == "xodr" else "axe_recale_sur_crete_detectee" if a.get("source") == "detection"
                  else "autre"] += 1
        else:
            bilan[f"retiree_{d}"] += 1
    rap["lignes_axe_v1"] = {"n": len(axe_v1), "devenir": dict(sorted(bilan.items()))}
    DERNIER.clear()
    DERNIER.update(hyp=hyp, ind=feats_v1)
    return feats, corr, rap


def _sans_peinture(entites, journal):
    """Lignes entièrement interrompues (aucune partie peinte) : retirées, devenir justifié."""
    from marquages_controles import _pieces
    out, j = [], []
    for e in entites:
        if e["classe"] == "ligne" and not _pieces(e, e["geom"][1]):
            j.append(e["id"])
            for mq in e.get("lien_v1", []):
                journal.devenir[mq] = ("retire", None, f"ligne {e['id']} entièrement interrompue (passages, marques, bordures : "
                                       "MQ-LIG-002, MQ-DET-010)")
            journal.h(id=e["id"], classe="ligne", src=e.get("src"), decision="retire_sans_peinture")
            continue
        out.append(e)
    return out, j


def feature(e):
    e2 = {k: v for k, v in e.items() if k not in CHAMPS_INTERNES}
    e2["etat"] = e2.get("etat") if e2.get("etat") in ("conserve", "neuf_2025", "refait_2025_identique") else "neuf_2025"
    e2["zone_etat"] = e.get("etat_zone")
    if "gam" in e2 and not e2["gam"]:
        e2.pop("gam")
    for k in ("sources",):
        if k in e2:
            e2[k] = arrondi(e2[k])
    return MI.feature(e2)


def correspondance(corr_v1, journal, ids_ok):
    """Devenir des 996 marquages v1 : celui de la refonte (journal), sinon celui de la chaîne v1 (retrait déjà justifié)."""
    V = {m["id"]: m for m in M.v1()}
    anc = {f["properties"]["id"]: f["properties"] for f in corr_v1}
    out = []
    for mq in sorted(V):
        p = V[mq]["p"]
        if mq in journal.devenir:
            fate, eid, note = journal.devenir[mq]
            if fate == "genere" and eid not in ids_ok:
                fate, eid, note = "retire", None, f"{note} ; entité {eid} retirée ensuite (entièrement interrompue)"
        elif mq in anc and anc[mq]["devenir"] == "retire":
            fate, eid, note = "retire", None, "chaîne v1 : " + anc[mq]["note"]
        else:
            fate, eid, note = "retire", None, "indice v1 absorbé par la chaîne v1 dans une entité non retenue par la refonte (non confirmé)"
        out.append({"type": "Feature", "geometry": None,
                    "properties": {"id": mq, "type_v1": p["type"], "groupe_v1": p["groupe"], "source_v1": p["source"],
                                   "contour_raster_v1": V[mq]["raster"], "devenir": fate, "entite": eid, "note": note}})
    return out


def hypotheses(journal, entites):
    out = []
    for i, h in enumerate(journal.hyp):
        p = {"id": f"H{i:05d}"}
        p.update({k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items() if k != "id"})
        p["hypothese"] = h["id"]
        out.append({"type": "Feature", "geometry": None, "properties": p})
    return out


def _pct(v, q):
    return round(float(np.percentile(v, q)), 4) if len(v) else None


def rapport(entites, journal, j_gam, j_inf, j_int, j_vides, aps, corr, det):
    src = collections.Counter(e["src"].split(":")[0] if not e["src"].startswith("regle:") else "regle" for e in entites)
    par = collections.defaultdict(collections.Counter)
    for e in entites:
        par[e["src"] if not e["src"].startswith("regle:") else "regle"][f"{e['classe']}/{e['type']}"] += 1
    dec = collections.Counter((h.get("src"), h.get("decision")) for h in journal.hyp)
    return arrondi({
        "schema": SCHEMA_ID,
        "priorite_sources": S.doc(),
        "n_entites": len(entites),
        "comptes_par_source": dict(sorted(src.items())),
        "comptes_par_source_type": {k: dict(sorted(v.items())) for k, v in sorted(par.items())},
        "comptes_par_classe": dict(sorted(collections.Counter(f"{e['classe']}/{e['type']}" for e in entites).items())),
        "a_verifier": sorted(e["id"] for e in entites if e.get("a_verifier")),
        "conflits_norme": sorted([e["id"], e["conflit_norme"]] for e in entites if e.get("conflit_norme")),
        "decisions_hypotheses": {f"{s}/{d}": n for (s, d), n in sorted(dec.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1])))},
        "gam": j_gam,
        "inferences": j_inf,
        "approches": [{k: v for k, v in a.items() if k != "xy_feu"} for a in aps],
        "interruptions": {"n_lignes": len(j_int)},
        "lignes_sans_peinture_retirees": j_vides,
        "correspondance_v1": dict(sorted(collections.Counter(f["properties"]["devenir"] for f in corr).items())),
        "detections_brutes": {k: len(v) for k, v in det.items()},
        "infere": sorted([e["id"], e["src"], e["classe"], e["type"]] for e in entites if e["src"].startswith("regle:")),
    })


def ecrire(sortie, feats, corr, hyp=None, ind=None, zone="site"):
    sortie = Path(sortie)
    hyp = DERNIER.get("hyp") if hyp is None else hyp
    ind = DERNIER.get("ind") if ind is None else ind
    ent = {"schema": SCHEMA_ID, "famille": "marquages", "zone_pilote": zone,
           "emprise": "site complet (carré de 300 m du levé GAM 2026)",
           "sources": "gam > plan2025 > ortho2022 > regle > v1 (indice) ; voir marquages.py",
           "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98, 216.30)"}
    ecrire_geojson(sortie / FICHIER, feats, "marquages", ent)
    ecrire_geojson(sortie / FICHIER_CORR, corr, "marquages_correspondance", dict(ent, famille="marquages_correspondance"))
    if hyp is not None:
        ecrire_geojson(sortie / FICHIER_HYP, hyp, "marquages_hypotheses", dict(ent, famille="marquages_hypotheses"))
    if ind is not None:
        ecrire_geojson(sortie / FICHIER_IND, ind, "marquages_indices_v1", dict(ent, famille="marquages_indices_v1"))
    return sortie / FICHIER, sortie / FICHIER_CORR


def maj_manifeste(dossier, feats, corr, rap):
    """Met à jour la seule partie marquages du manifeste description_scene_v2.json (couches, comptes, statistiques,
    hash_marquages) quand la famille est écrite seule (composer.py réécrit tout le manifeste)."""
    import hashlib
    from commun import ecrire_json, lire_json, rel, sha256
    dossier = Path(dossier)
    f = dossier / "description_scene_v2.json"
    if not f.exists():
        return False
    man = lire_json(f)
    info = man.setdefault("couches", {})
    for fam, nom in (("marquages", FICHIER), ("marquages_correspondance", FICHIER_CORR)):
        info[fam] = {"fichier": f"base/{nom}", "n": len(feats if fam == "marquages" else corr), "sha256": sha256(dossier / "base" / nom)}
    man["schema"] = SCHEMA_ID
    man.setdefault("comptes", {})["marquages"] = len(feats)
    man["comptes"]["marquages_v1"] = len(corr)
    man.setdefault("statistiques", {})["marquages"] = rap
    refs = man.setdefault("references", {})
    for k, (p_, r) in REFERENCES.items():
        refs[k] = {"fichier": rel(p_), "sha256": sha256(p_), "role": r}
    gen = man.setdefault("generateur", {}).setdefault("scripts", {})
    ici = Path(__file__).resolve().parent
    for s_ in SCRIPTS:
        gen[f"recon/pcg/decrire/{s_}"] = sha256(ici / s_)
    man["hash_marquages"] = hashlib.sha256("".join(info[k]["sha256"] for k in sorted(info) if k.startswith("marquages")).encode()).hexdigest()
    ecrire_json(f, man)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", default=str(SORTIE / "base"))
    ap.add_argument("--rapport", help="écrit le rapport JSON (comptes, couverture, métriques)")
    ap.add_argument("--indices", help="indices v1 déjà calculés (marquages_indices_v1.geojson ; développement)")
    ap.add_argument("--manifeste", action="store_true", help="met à jour la partie marquages du manifeste du dossier parent")
    a = ap.parse_args()
    feats, corr, rap = construire(a.indices)
    ecrire(a.sortie, feats, corr)
    if a.manifeste:
        maj_manifeste(Path(a.sortie).parent, feats, corr, rap)
    print(json.dumps({k: rap[k] for k in ("n_entites", "comptes_par_source", "comptes_par_classe", "correspondance_v1")},
                     ensure_ascii=False, indent=1))
    if a.rapport:
        Path(a.rapport).write_text(json.dumps(rap, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
