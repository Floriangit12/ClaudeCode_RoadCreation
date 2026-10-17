# -*- coding: utf-8 -*-
"""Tests du format de description simple et de son compilateur (lot L0).

    python recon/generateur/description/tests/tester_descriptions.py [--json FICHIER]   (défaut : recon/generateur/tmp/tests/tests_description_L0.json ;
    seul validation/faire_rapport_L0.py écrit la version versionnée validation/tests_description_L0.json)

1. Chaque exemple de `description/exemples/` et chaque scène du catalogue voisin (`scenes_simples/S*.yaml`) compile
   en modèle valide (validateur, provenance exigée : 0 erreur) et deux compilations donnent des octets identiques.
2. Faits attendus sur les exemples (écrits d'après les règles, pas recopiés des sorties) : largeurs complétées,
   sections de neutralisation, abaissés, flèches de rabattement, ralentisseurs, arrêt de bus…
3. Attendus du catalogue voisin vérifiables au niveau du modèle (longueur, emprise, chaussée, voies, flèches,
   figurines, inscriptions, bordures, oblique) ; les attendus de dessin (nombre de traits, hachures) relèvent du lot L4.
4. Erreurs attendues : ce que la description ne peut pas dire sans règle, ou ce que les règles interdisent.
Code retour 0 si tout passe.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
GEN = ICI.parents[1]
sys.path.insert(0, str(GEN))
sys.path.insert(0, str(GEN / "description"))
from description import description_vers_modele as D  # noqa: E402
from description import yaml_simple  # noqa: E402
from commun import profil as PF  # noqa: E402

EXEMPLES = sorted((GEN / "description" / "exemples").glob("*.yaml"))
CATALOGUE = sorted((GEN / "scenes_simples").glob("S*.yaml"))
MEYLAN = sorted((GEN / "scenes_meylan").glob("*.yaml"))      # rues réelles décrites d'après photo (correction)
VEGETAL = {"gazon_tondu", "herbe_haute", "gazon_sec", "noue_plantee", "terre_nue"}


def compiler(chemin: Path):
    octets = chemin.read_bytes()
    d = yaml_simple.charger(octets.decode("utf-8"))
    src = str(chemin.relative_to(GEN.parents[1])).replace("\\", "/")
    m1, r1 = D.compiler(copy.deepcopy(d), src, hashlib.sha256(octets).hexdigest())
    m2, _ = D.compiler(copy.deepcopy(d), src, hashlib.sha256(octets).hexdigest())
    o1 = json.dumps(m1, ensure_ascii=False, indent=1).encode("utf-8")
    o2 = json.dumps(m2, ensure_ascii=False, indent=1).encode("utf-8")
    return m1, r1, o1 == o2, hashlib.sha256(o1).hexdigest(), d


def profils(m):
    return {p["id"]: p for p in m["profils"]}


def profil_a(m, s, route=0):
    P = profils(m)
    for sec in m["routes"][route]["sections"]:
        if s <= sec["s1"] + 1e-9:
            return P[sec["profil"]]
    return P[m["routes"][route]["sections"][-1]["profil"]]


def largeurs_a(m, s):
    p = profil_a(m, s)
    return [(b["id"], b["type"], b["sens"], round(D.largeur_a(b["largeur"], s), 4), b.get("materiau_id"), b["niveau"]["reference"]) for b in p["bandes"]]


def trace_modele(m, route=0):
    """Ligne de référence reconstruite depuis geometrie_reguliere."""
    from commun import geometrie as G
    prims = m["routes"][route]["ligne_reference"]["geometrie_reguliere"]
    p0 = prims[0]
    tr = G.Trace(p0["x0"], p0["y0"], p0["cap_deg"])
    for p in prims:
        k0, k1 = p.get("courbure0", 0.0), p.get("courbure1", 0.0)
        tr._ajouter(p["longueur"], k0, k1)
    return tr


def longueur_bordures(m, profil_bordure="T2", pas=0.25, avancees=False):
    """Longueur en plan (m) des arêtes de bordure d'un profil donné, section par section (lois et courbes comprises).
    avancees=False : comme le catalogue voisin, sans les bordures d'avancées ; avancees=True : bordures d'avancées,
    retours compris (aux bornes de section, la bordure fait le tour de la largeur de la bande)."""
    tr = trace_modele(m)
    P = profils(m)
    secs = m["routes"][0]["sections"]
    tot = 0.0

    def avancee(p, i):
        return "avancee_trottoir" in [p["bandes"][j].get("sous_type") for j in (i - 1, i) if 0 <= j < len(p["bandes"])]

    for sec in secs:
        p = P[sec["profil"]]
        n = max(1, int(math.ceil((sec["s1"] - sec["s0"]) / pas)))
        for i, l in enumerate(p["limites"]):
            if "bordure" not in l["nature"] or l["bordure"]["profil"] != profil_bordure or avancee(p, i) != avancees:
                continue
            pts = []
            for k in range(n + 1):
                x = sec["s0"] + (sec["s1"] - sec["s0"]) * k / n
                pts.append(tr.point_st(x, D.t_limites(p, x)[i]))
            tot += sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    if avancees:
        for sec, x in ((secs[0], secs[0]["s0"]), (secs[-1], secs[-1]["s1"])):     # retours aux extrémités du tronçon
            for bd in P[sec["profil"]]["bandes"]:
                if bd.get("sous_type") == "avancee_trottoir":
                    tot += D.largeur_a(bd["largeur"], x)
        for a, b in zip(secs, secs[1:]):
            pa, pb = P[a["profil"]], P[b["profil"]]
            for p in (pa, pb):
                for j, bd in enumerate(p["bandes"]):
                    if bd.get("sous_type") == "avancee_trottoir":
                        tot += D.largeur_a(bd["largeur"], a["s1"])
    return tot


def profil_courant(m):
    """Profil utilisé sur la plus grande longueur du tronçon."""
    lg = {}
    for sec in m["routes"][0]["sections"]:
        lg[sec["profil"]] = lg.get(sec["profil"], 0.0) + sec["s1"] - sec["s0"]
    return profils(m)[max(sorted(lg), key=lambda k: lg[k])]


# ------------------------------------------------------------------------------------------- faits sur les exemples
def faits_exemples(res):
    """Faits attendus écrits à la main d'après les règles."""
    out = []

    def fait(ex, titre, ok, detail=None):
        out.append({"exemple": ex, "fait": titre, "ok": bool(ok), "detail": detail})

    m = res["01_route_2x1_sans_bordure"]["modele"]
    w = largeurs_a(m, 1.0)
    fait("01", "voies de 3,00 m et BDD de 0,50 m complétées (RF-OSM-LAR-014, RD à 1 chaussée)",
         [x[3] for x in w] == [1.5, 0.5, 3.0, 3.0, 0.5, 1.5], w)
    fait("01", "vitesse 80 km/h complétée (RF-OSM-VIT-003)", m["routes"][0]["vitesse_kmh"] == 80, m["routes"][0]["vitesse_kmh"])
    fait("01", "rives T2 3u au bord des voies, axe T1 2u (RF-OSM-MRQ-021, RF-OSM-MRQ-010)",
         PF.resume(profil_a(m, 1))["limites"] == ["virtuelle", "changement_revetement", "T2 3u", "T1 2u", "T2 3u", "changement_revetement", "virtuelle"],
         PF.resume(profil_a(m, 1))["limites"])
    fait("01", "tracé droite + arc R 150 m de 25° + droite (longueur 60 + 65,45 + 50)",
         abs(m["routes"][0]["ligne_reference"]["longueur_m"] - (110 + math.radians(25) * 150)) < 1e-3,
         m["routes"][0]["ligne_reference"]["longueur_m"])

    m = res["02_rue_1x1_trottoirs"]["modele"]
    secs = [(s["s0"], s["s1"]) for s in m["routes"][0]["sections"]]
    fait("02", "stationnement neutralisé 5 m en amont du passage et à son droit : section [33 ; 42] (RF-OSM-STA-002, DEF-009)",
         (33.0, 42.0) in secs, secs)
    lim = profil_a(m, 10)["limites"]
    # profil au droit du passage (s = 40) : abaissés et BEV ; profil voisin qui touche le passage (s = 10, jonction en
    # 42) : mêmes abaissés pour les rampants, sans BEV (correction après le second contrôle : BEV posée une seule fois)
    ab = [a for l in profil_a(m, 40)["limites"] if "bordure" in l["nature"] for a in l["bordure"].get("abaisses", [])]
    ab_v = [a for l in lim if "bordure" in l["nature"] for a in l["bordure"].get("abaisses", [])]
    fait("02", "abaissés de 4,00 m (passage DEF-011) en vue 0,02, rampants 2,40 m à 5 %, BEV (DEF-031) sur les 2 bordures "
               "au droit du passage ; profil voisin : rampants seuls, sans BEV",
         len(ab) == 2 and all(a["s0"] == 38.0 and a["s1"] == 42.0 and a["vue_m"] == 0.02 and a["rampant_m"] == 2.4 and a["bev"] for a in ab)
         and len(ab_v) == 2 and not any(a["bev"] for a in ab_v), {"passage": ab, "voisin": ab_v})
    it = [i for l in lim if "marquage" in l["nature"] for mm in l["marquages"] for i in mm.get("interruptions", [])]
    fait("02", "lignes interrompues à 0,50 m du passage (RF-MQ-PP-03) : [37,5 ; 42,5]",
         it and all(i["s0"] == 37.5 and i["s1"] == 42.5 for i in it), it)

    m = res["05_rue_piste_bande_plantee_arret_bus"]["modele"]
    secs = {(s["s0"], s["s1"]): s["profil"] for s in m["routes"][0]["sections"]}
    q = profils(m)[secs.get((127.0, 141.0), "?")] if (127.0, 141.0) in secs else None
    fait("05", "quai de 14 m (DEF-032) de 127 à 141 m, poteau à 140 m : stationnement et bande plantée en quai",
         q is not None and [b["type"] for b in q["bandes"]][6:8] == ["quai_bus", "quai_bus"], [b["type"] for b in q["bandes"]] if q else secs)
    fait("05", "neutralisation 5 m avant et après le quai (RF-MA-BUS-015)", (122.0, 127.0) in secs and (141.0, 146.0) in secs, list(secs))
    zz = [x for x in m.get("marquages", []) if x["type"] == "zigzag"]
    fait("05", "zigzag jaune de 30 m : 20 m en amont du poteau, 10 m en aval (DEF-019, ARB-03)",
         len(zz) == 1 and zz[0]["couleur"] == "jaune" and zz[0]["geometrie"][0][0] == round(917279.43 + 120, 4) and zz[0]["geometrie"][-1][0] == round(917279.43 + 150, 4),
         [(z["geometrie"][0], z["geometrie"][-1]) for z in zz])
    sig = sorted(s["code"] for s in m.get("signaux", []))
    fait("05", "C20a des deux côtés du passage et C6 en tête de quai", sig == ["C20a", "C20a", "C6"], sig)
    obj = sorted(o["type"] for o in m.get("objets", []))
    fait("05", "poteau d'arrêt et abri (RF-MA-BUS-012)", obj == ["abri_bus", "poteau_arret_bus"], obj)

    m = res["06_rabattement_2_vers_1"]["modele"]
    fl = sorted(x["ancrage"]["s"] for x in m.get("marquages", []) if x["type"] == "fleche")
    fait("06", "3 flèches RAB_D à L, L − i1, L − i1 − i2 du milieu du biseau [90 ; 150] : 81, 107, 120 (RF-MQ-RAB-05, L = 39)",
         fl == [81.0, 107.0, 120.0], fl)
    fait("06", "voie supprimée : largeur 3,00 → 0 sur le biseau de 60 m",
         any(isinstance(b["largeur"], dict) and b["largeur"]["points"] == [[90.0, 3.0], [150.0, 0.0]] for p in m["profils"] for b in p["bandes"]), None)

    m = res["07_zone30_ralentisseurs_passage"]["modele"]
    tri = [x for x in m.get("marquages", []) if x.get("gabarit") == "TRIANGLE_DOS_ANE"]
    fait("07", "3 triangles D.8 par voie sur le dos-d'âne, pointes dans le sens de circulation (RF-MQ-RAL-01)",
         len(tri) == 6 and sorted({x["ancrage"]["cap_deg"] for x in tri}) == [0.0, 180.0], len(tri))
    ax = [mm for l in profil_a(m, 10)["limites"] for mm in l.get("marquages", []) if mm["modulation"] == "T3"]
    fait("07", "axe T3 2u sur le dos-d'âne prolongé de 10 m (chaussée ≥ 5 m, RF-MQ-RAL-01) : [28 ; 52]",
         len(ax) == 1 and ax[0]["intervalle"] == {"s0": 28.0, "s1": 52.0}, ax)
    pl = [o for o in m.get("objets", []) if o["type"] == "plateau"]
    fait("07", "plateau de 4,00 m (RF-MA-RAL-001) + 2 rampes à 7 % pour 0,10 m (DEF-034) : 6,857 m",
         len(pl) == 1 and abs(pl[0]["dimensions"]["longueur_m"] - (4 + 2 * 0.1 / 0.07)) < 1e-3, pl and pl[0]["dimensions"])
    fait("07", "pas de triangles sur le plateau qui porte le passage (RF-MQ-PP-04)",
         not [x for x in m.get("marquages", []) if x.get("gabarit") == "TRIANGLE_PLATEAU"], None)
    pps = [x for x in m.get("marquages", []) if x["type"] == "passage_pieton"]
    lgb = [round(math.dist(x["geometrie"]["exterieur"][0], x["geometrie"]["exterieur"][2]), 3) for x in pps]
    fait("07", "bandes du passage sur le plateau = plateau + 2 × 0,50 m = 5,00 m (RF-MQ-PP-04)", lgb == [5.0], lgb)

    m = res["08_sens_unique_stationnement_charretieres"]["modele"]
    p = profil_a(m, 10)
    ab = {i: [a["type"] for a in l["bordure"].get("abaisses", [])] for i, l in enumerate(p["limites"]) if "bordure" in l["nature"]}
    fait("08", "entrée charretière gauche sur la bordure gauche, droite + abaissé sur la bordure droite", ab == {1: ["charretiere"], 4: ["charretiere", "traversee"]}, ab)
    fait("08", "voie de 3,50 m à sens unique : contrôle RF-OSM-LAR-011 conforme (borne haute)",
         any(c["regle"] == "RF-OSM-LAR-011" and c["statut"] == "conforme" for t in res["08_sens_unique_stationnement_charretieres"]["rapport"]["troncons"] for c in t["controles"]), None)

    m = res["09_elargissement_tourne_a_gauche"]["modele"]
    p = profil_a(m, 170)
    fait("09", "voie de tourne-à-gauche de 2,75 m (RF-OSM-LAR-012 présélection) séparée par T3 2u (RF-OSM-MRQ-011)",
         PF.resume(p)["bandes"][2] == ["voie_tourne_gauche", "avant", 2.75] and PF.resume(p)["limites"][3] == "T3 2u", PF.resume(p))

    m = res["12_piste_bidirectionnelle_separateur"]["modele"]
    p = profil_a(m, 10)
    axe = p["limites"][2]["marquages"][0] if "marquage" in p["limites"][2]["nature"] else {}
    fait("12", "piste bidirectionnelle coupée en deux, axe T'1 2u en u = 3 cm (RF-OSM-CYC-002, DEF-001)",
         axe.get("modulation") == "T'1" and axe.get("u_m") == 0.03, axe)
    fait("12", "séparateur de 0,50 m à 0,15 m de haut (RF-MA-SEP-001)",
         p["limites"][3]["nature"] == ["separateur"] and p["limites"][3]["separateur"]["hauteur_m"] == 0.15, p["limites"][3])

    m = res["11_description_rapide_depuis_photo"]["modele"]
    fait("11", "les évènements écrits en phrases donnent passage, plateau, quai et entrée charretière",
         sorted({x["type"] for x in m.get("marquages", [])}) == ["passage_pieton", "zigzag"]
         and sorted(o["type"] for o in m.get("objets", [])) == ["plateau", "poteau_arret_bus"], None)
    return out


# ------------------------------------------------------------------------------------------- catalogue voisin
def attendus_catalogue(m, r, d):
    """(vérifiés, non vérifiables) : comparaison des attendus déclarés que le modèle porte."""
    a = d.get("attendus") or {}
    ver, nv = [], []

    def cmp(cle, attendu, obtenu, tol=1e-3):
        if isinstance(attendu, (int, float)) and isinstance(obtenu, (int, float)):
            ok = abs(attendu - obtenu) <= tol
        else:
            ok = attendu == obtenu
        ver.append({"attendu": cle, "valeur_attendue": attendu, "valeur_modele": obtenu, "ok": ok})

    rt = m["routes"][0]
    pc = profil_courant(m)
    w = [(b["id"], b["type"], b["sens"], round(PF.nombre(b["largeur"]), 4), b.get("materiau_id"), b["niveau"]["reference"]) for b in pc["bandes"]]
    for k, v in a.items():
        if k == "longueur":
            cmp(k, v, rt["ligne_reference"]["longueur_m"])
        elif k == "largeur_emprise":
            cmp(k, v, round(sum(x[3] for x in w), 4))
        elif k == "largeur_chaussee":       # chaussée revêtue contiguë autour de la première voie (définition du catalogue)
            j = next(i for i, x in enumerate(w) if x[1] in PF.VOIES_MOTORISEES)
            ok_ch = lambda x: x[5] == "chaussee" and x[4] not in VEGETAL  # noqa: E731
            g = j
            while g - 1 >= 0 and ok_ch(w[g - 1]):
                g -= 1
            dd = j
            while dd + 1 < len(w) and ok_ch(w[dd + 1]):
                dd += 1
            cmp(k, v, round(sum(x[3] for x in w[g:dd + 1]), 4))
        elif k == "voies":
            cmp(k, v, {s: sum(1 for x in w if x[1] in PF.VOIES_MOTORISEES and x[2] == s) for s in v})
        elif k == "fleches":
            fl = {}
            for x in m.get("marquages", []):
                if x["type"] == "fleche":
                    fl[x["gabarit"]] = fl.get(x["gabarit"], 0) + 1
            cmp(k, v, fl)
        elif k == "fleches_s":
            cmp(k, sorted(v), sorted(x["ancrage"]["s"] for x in m.get("marquages", []) if x["type"] == "fleche"))
        elif k == "figurines":
            n = 0
            for p in m["profils"]:
                for b in p["bandes"]:
                    for o in b.get("objets_le_long", []):
                        if o["type"] == "figurine_velo" and o["mode"] == "points":
                            n += len(o["s_points"])
            cmp(k, v, n)
        elif k == "inscriptions":
            ins = {}
            for x in m.get("marquages", []):
                if x["type"] == "inscription":
                    t = x["x-opendrive"]["texte"]
                    ins[t] = ins.get(t, 0) + 1
            cmp(k, v, ins)
        elif k == "bordures_m":
            cmp(k, v, {pb: round(longueur_bordures(m, pb), 2) for pb in v}, tol=0)
            ver[-1]["ok"] = all(abs(longueur_bordures(m, pb) - lv) <= 0.05 for pb, lv in v.items())
            ver[-1]["tolerance_m"] = 0.05
        elif k == "bordures_avancees_m":
            cmp(k, v, {pb: round(longueur_bordures(m, pb, avancees=True), 2) for pb in v}, tol=0)
            ver[-1]["ok"] = all(abs(longueur_bordures(m, pb, avancees=True) - lv) <= 0.05 for pb, lv in v.items())
            ver[-1]["tolerance_m"] = 0.05
        elif k == "passages":
            obt = []
            for x in sorted((x for x in m.get("marquages", []) if x["type"] == "passage_pieton"), key=lambda x: x["ancrage"]["s"]):
                ext = x["geometrie"]["exterieur"]
                obt.append({"s": x["ancrage"]["s"], "longueur_bandes": round(math.dist(ext[0], ext[2]), 3), "W": round(math.dist(ext[1], ext[4]), 3)})
            att = [{kk: pp[kk] for kk in ("s", "longueur_bandes", "W") if kk in pp} for pp in v]
            cmp(k, att, [{kk: o[kk] for kk in a_.keys()} for o, a_ in zip(obt, att)] if len(obt) == len(att) else obt)
            nv.append({"attendu": "passages.bandes / passages.e", "valeur": [{kk: pp.get(kk) for kk in ("bandes", "e")} for pp in v],
                       "raison": "nombre et marges des bandes calculés au lot L4 (DEF-011)"})
        elif k in ("abaisses", "bev"):
            ab = []
            for p in m["profils"]:
                for l in p["limites"]:
                    if "bordure" in l["nature"]:
                        ab += [json.dumps(a, sort_keys=True) + str(l["bordure"].get("cote_haut")) for a in l["bordure"].get("abaisses", [])]
            ab = sorted(set(ab))
            n = len(ab) if k == "abaisses" else sum(1 for a in ab if '"bev": true' in a)
            cmp(k, v, n)
        elif k == "oblique":
            loi = [b["largeur"]["points"] for p in m["profils"] for b in p["bandes"]
                   if isinstance(b["largeur"], dict) and b["type"] in PF.VOIES_MOTORISEES]
            s0 = min(pt[0][0] for pt in loi) if loi else None
            s1 = max(pt[-1][0] for pt in loi) if loi else None
            cmp(k, {"s0": v["s0"], "s1": v["s1"]}, {"s0": s0, "s1": s1})
        else:
            nv.append({"attendu": k, "valeur": v, "raison": "dessin des marques (traits, hachures, aplats, continues) : lot L4"})
    return ver, nv


# ------------------------------------------------------------------------------------------- erreurs attendues
CAS_ERREURS = [
    ("E1", "passage piéton sur un dos-d'âne (RF-MA-RAL-001)", {"contexte": {"agglomeration": "oui", "vitesse": 30},
     "troncon": {"longueur": 100}, "profil": "trottoir 2 | voie 3 ← | voie 3 → | trottoir 2",
     "evenements": [{"dos_d_ane": {"a": 50}}, {"passage_pieton": {"a": 51}}]}, "RF-MA-RAL-001"),
    ("E2", "mot inconnu dans le profil", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "trottoir 2 | voie 3 ← | voie magique 3 → | trottoir 2"}, "magique"),
    ("E3", "entrée charretière sans largeur : aucune règle ne la fixe", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "trottoir 2 | voie 3 ← | voie 3 → | trottoir 2", "evenements": [{"entree_charretiere": {"a": 20, "cote": "droite"}}]}, "aucune règle"),
    ("E4", "voie ← à droite d'une voie → (circulation à droite, RF-OSM-PRF-002)", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "trottoir 2 | voie 3 → | voie 3 ← | trottoir 2"}, "RF-OSM-PRF-002"),
    ("E5", "clé inconnue à la racine (jamais ignorée en silence)", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "voie 3 ← | voie 3 →", "trottoirs_magiques": 3}, "trottoirs_magiques"),
    ("E6", "flèche de schéma non autorisé (RF-MQ-DIR-02)", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 100},
     "profil": "voie 3 → | voie 3 →", "evenements": [{"fleches": {"a": 20, "type": "TAG_TAD"}}]}, "RF-MQ-DIR-02"),
    ("E7", "fosse sans largeur (aucune règle)", {"contexte": {"agglomeration": "non"}, "troncon": {"longueur": 50},
     "profil": "fosse | voie ← | voie → | fosse"}, "aucune règle"),
    ("E8", "paramètre d'évènement inconnu", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "voie 3 ← | voie 3 →", "evenements": [{"passage_pieton": {"a": 20, "couleur_fluo": "oui"}}]}, "couleur_fluo"),
    ("E9", "bordure entre deux bandes au même niveau", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "voie 3 ← | bordure T2 | voie 3 →"}, "même niveau"),
    # corrections après contrôle (relecture adverse, tmp/verif/adv A6, A11, A12)
    ("E10", "dos-d'âne hors agglomération à 80 km/h : interdit réglementaire bloquant (RF-MA-RAL-001)",
     {"contexte": {"agglomeration": "non", "vitesse": 80}, "troncon": {"longueur": 100},
      "profil": "bdd 1 | voie 3 ← | voie 3 → | bdd 1", "evenements": [{"dos_d_ane": {"a": 50}}]}, "RF-MA-RAL-001"),
    ("E11", "deux passages piétons superposés (50 et 51)", {"contexte": {"agglomeration": "oui", "vitesse": 30},
     "troncon": {"longueur": 100}, "profil": "trottoir 2 | voie 3 ← | voie 3 → | trottoir 2",
     "evenements": [{"passage_pieton": {"a": 50}}, {"passage_pieton": {"a": 51}}]}, "chevauche"),
    ("E12", "plateau et dos-d'âne superposés", {"contexte": {"agglomeration": "oui", "vitesse": 30},
     "troncon": {"longueur": 100}, "profil": "trottoir 2 | voie 3 ← | voie 3 → | trottoir 2",
     "evenements": [{"plateau": {"a": 50}}, {"dos_d_ane": {"a": 52}}]}, "deux ralentisseurs"),
    ("E13", "plateau (trapézoïdal) hors agglomération : interdit bloquant (RF-MA-RAL-001)",
     {"contexte": {"agglomeration": "non", "vitesse": 50}, "troncon": {"longueur": 100},
      "profil": "bdd 1 | voie 3 ← | voie 3 → | bdd 1", "evenements": [{"plateau": {"a": 50}}]}, "RF-MA-RAL-001"),
    ("E14", "écart admis citant une règle inconnue", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "voie 3 ← | voie 3 →", "ecarts_admis": {"RF-MA-RAL-999": "essai"}}, "règle inconnue"),
    ("E15", "écart admis sans motif", {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
     "profil": "voie 3 ← | voie 3 →", "ecarts_admis": {"RF-MA-RAL-001": ""}}, "motif à dire"),
    ("E16", "essence d'arbre inconnue du catalogue de végétation", {"contexte": {"agglomeration": "oui"},
     "troncon": {"longueur": 50}, "profil": "trottoir 3 | voie 3 ← | voie 3 → | trottoir 3",
     "objets": [{"arbres": {"bande": "trottoir droite", "essence": "baobab"}}]}, "vegetation.json"),
    # correction après le second contrôle de l'étape 1 : un passage doit aboutir sur une surface piétonne par des
    # bandes revêtues (S_M20 : BEV dans la bande plantée ; S_M27 : passage qui aboutissait dans la berme)
    ("E17", "passage qui aboutit dans une bande plantée sans traversée revêtue décrite",
     {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 60},
      "profil": "bande plantée 3 | bordure basse vue 0,06 | voie 3 ← | voie 3 → | trottoir 2",
      "evenements": [{"passage_pieton": {"a": 30}}]}, "avant toute surface piétonne"),
    ("E18", "passage qui aboutit dans une berme (herbe à niveau) avant le trottoir",
     {"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 60},
      "profil": "trottoir 2 niveau chaussée | berme 2 | voie 3 ← | voie 3 → | trottoir 2",
      "evenements": [{"passage_pieton": {"a": 30}}]}, "« berme »"),
]


def tests_erreurs():
    out = []
    for cid, titre, d, attendu in CAS_ERREURS:
        try:
            D.compiler(copy.deepcopy(d), f"(test {cid})")
            out.append({"id": cid, "titre": titre, "ok": False, "detail": "aucune erreur levée"})
        except D.ErreurDescription as e:
            out.append({"id": cid, "titre": titre, "ok": attendu in str(e), "detail": str(e)[:300]})
    # forme texte = forme dictionnaire
    base = {"contexte": {"agglomeration": "oui", "vitesse": 30}, "troncon": {"longueur": 120},
            "profil": "trottoir 2 | voie ← | voie → | stationnement | trottoir 2"}
    m1, _ = D.compiler(dict(base, evenements=["à 40 : passage piéton", "à 90 : plateau avec passage piéton"]), "(t)")
    m2, _ = D.compiler(dict(base, evenements=[{"passage_pieton": {"a": 40}}, {"plateau": {"a": 90, "passage_pieton": "oui"}}]), "(t)")
    sec = lambda m: [(s["s0"], s["s1"]) for s in m["routes"][0]["sections"]]  # noqa: E731
    out.append({"id": "F1", "titre": "« à 40 : passage piéton » ≡ {passage_pieton: {a: 40}} (mêmes sections, marquages, objets)",
                "ok": sec(m1) == sec(m2) and len(m1.get("marquages", [])) == len(m2.get("marquages", [])) and
                [o["dimensions"] for o in m1.get("objets", [])] == [o["dimensions"] for o in m2.get("objets", [])],
                "detail": [sec(m1), sec(m2)]})
    # forme ligne = forme structurée (catalogue voisin)
    m3, _ = D.compiler({"contexte": {"agglomeration": True, "vitesse_kmh": 50}, "trace": [{"droite": 100}],
                        "profil": [{"bande": "trottoir", "largeur": 2.0}, {"bordure": "T2", "vue": 0.14},
                                   {"bande": "voie", "sens": "arriere", "largeur": 3.0}, {"bande": "voie", "sens": "avant", "largeur": 3.0},
                                   {"bordure": "T2", "vue": 0.14}, {"bande": "trottoir", "largeur": 2.0}]}, "(t)")
    m4, _ = D.compiler({"contexte": {"agglomeration": "oui", "vitesse": 50}, "troncon": {"longueur": 100},
                        "profil": "trottoir 2 | bordure T2 vue 14 cm | voie 3 ← | voie 3 → | bordure T2 | trottoir 2"}, "(t)")
    out.append({"id": "F2", "titre": "profil en ligne ≡ profil structuré (mêmes bandes, limites, niveaux)",
                "ok": PF.resume(m3["profils"][0]) == PF.resume(m4["profils"][0]) and
                [b["niveau"] for b in m3["profils"][0]["bandes"]] == [b["niveau"] for b in m4["profils"][0]["bandes"]],
                "detail": [PF.resume(m3["profils"][0]), PF.resume(m4["profils"][0])]})
    # corrections après contrôle : écart admis explicitement (cas réel), dévers des accotements (RF-GV-DEV-001),
    # blocage de la fabrication sur un contrôle non conforme non admis (fabriquer_generateur.preparer_entree)
    d5 = {"contexte": {"agglomeration": "non", "vitesse": 80}, "troncon": {"longueur": 100},
          "profil": "bdd 1 | voie 3 ← | voie 3 → | bdd 1", "evenements": [{"dos_d_ane": {"a": 50}}],
          "ecarts_admis": {"RF-MA-RAL-001": "cas réel relevé (essai)"}}
    m5, r5 = D.compiler(copy.deepcopy(d5), "(t)")
    st5 = [c["statut"] for t in r5["troncons"] for c in t["controles"] if c.get("controle") == "dos_d_ane_contexte"]
    out.append({"id": "F3", "titre": "interdit admis par « ecarts_admis » (motif) : compile, contrôle non_conforme_admis, "
                                     "aucune non-conformité bloquante", "ok": st5 == ["non_conforme_admis"] and not r5["non_conformites"],
                "detail": {"statuts": st5, "non_conformites": r5["non_conformites"]}})
    m6, _ = D.compiler({"contexte": {"agglomeration": "non", "vitesse": 80}, "troncon": {"longueur": 60},
                        "profil": "berme 1 | bdd 1.75 | surlargeur 0.25 | voie 3 ← | voie 3 → | surlargeur 0.25 | bdd 1.75 | berme 1"}, "(t)")
    dv = [(b["type"], b["niveau"].get("devers_pct"), (b["prov"].get("niveau.devers_pct") or {}).get("regle"))
          for b in m6["profils"][0]["bandes"]]
    att6 = [("berme", -8, "RF-GV-DEV-001"), ("bande_derasee", -4, "RF-GV-DEV-001"), ("accotement_revetu", -2.5, "DEF-006"),
            ("voie_circulation", -2.5, "DEF-006"), ("voie_circulation", 2.5, "DEF-006"), ("accotement_revetu", 2.5, "DEF-006"),
            ("bande_derasee", 4, "RF-GV-DEV-001"), ("berme", 8, "RF-GV-DEV-001")]
    out.append({"id": "F4", "titre": "dévers des accotements : BDD 4 %, berme 8 % vers l'extérieur (RF-GV-DEV-001), "
                                     "surlargeur et voies 2,5 % (DEF-006), provenance de chaque dévers",
                "ok": [(a, float(b), c) for a, b, c in dv] == [(a, float(b), c) for a, b, c in att6], "detail": dv})
    sys.path.insert(0, str(GEN))
    from commun import conformite as CF
    _, r7 = D.compiler({"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
                        "profil": "trottoir 1 | voie 3 ← | voie 3 → | trottoir 2"}, "(t)")
    b7 = CF.bloquants(r7)
    _, r8 = D.compiler({"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 50},
                        "profil": "trottoir 1 | voie 3 ← | voie 3 → | trottoir 2",
                        "ecarts_admis": {r7["non_conformites"][0]["regle"] if r7["non_conformites"] else "RF-MA-TRO-001": "trottoir étroit relevé"}}, "(t)")
    out.append({"id": "F5", "titre": "fabrication refusée sur un contrôle hors plage non admis (trottoir de 1 m), acceptée s'il est admis",
                "ok": len(b7) >= 1 and not CF.bloquants(r8), "detail": {"bloquants": b7, "admis": CF.bloquants(r8)}})
    # arbres : dimensions portées dans le modèle (essence du catalogue, houppier dit, fût au gabarit RF-OSM-VEG-001)
    m9, _ = D.compiler({"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 60},
                        "profil": "trottoir 3 | voie 3 ← | voie 3 → | trottoir 3",
                        "objets": [{"arbres": {"bande": "trottoir droite", "essence": "tilleul"}},
                                   {"arbres": {"bande": "trottoir gauche", "houppier_rayon": 1.0, "hauteur": 6}}]}, "(t)")
    arb = {o["ancrage"]["reference"]: o for b in m9["profils"][0]["bandes"] for o in b.get("objets_le_long", [])
           if o["famille"] == "vegetation"}
    a_d = arb.get("rive_gauche", {})        # trottoir de droite : ancré à sa rive gauche (côté voie)
    a_g = arb.get("rive_droite", {})
    ok9 = (a_d.get("asset_id") == "arbre_tilia_cordata_moyen" and a_d.get("hauteur_m") == 14.0 and
           a_d.get("houppier_rayon_m") == 4.0 and a_d.get("fut_m") == 3.8 and
           a_g.get("houppier_rayon_m") == 1.0 and a_g.get("hauteur_m") == 6.0 and a_g.get("fut_m") == 2.5)
    # contrôle croisé du lecteur YAML minimal par PyYAML (Python du système), s'il est présent
    try:
        import yaml as _py
        import glob as _gl

        def _norm(o):
            if isinstance(o, dict):
                return {k: _norm(v) for k, v in o.items()}
            if isinstance(o, list):
                return [_norm(v) for v in o]
            if isinstance(o, str):
                return o.rstrip(chr(10))
            if type(o).__name__ in ("date", "datetime"):
                return o.isoformat()
            return o
        fichiers = sorted(_gl.glob(str(GEN / "description" / "exemples" / "*.yaml")) + _gl.glob(str(GEN / "scenes_simples" / "*.yaml"))
                          + _gl.glob(str(GEN / "scenes_meylan" / "*.yaml")) + _gl.glob(str(GEN / "validation" / "essais_L1" / "*.yaml")))
        ecarts = [Path(f).name for f in fichiers
                  if _norm(D.yaml_simple.charger(Path(f).read_text(encoding="utf-8"))) != _norm(_py.safe_load(Path(f).read_text(encoding="utf-8")))]
        out.append({"id": "Y1", "titre": f"yaml_simple = PyYAML {_py.__version__} sur {len(fichiers)} descriptions (au saut de ligne "
                                         "final des blocs et aux dates nues près)", "ok": not ecarts, "detail": ecarts})
    except ImportError:
        out.append({"id": "Y1", "titre": "contrôle croisé PyYAML sauté (PyYAML absent)", "ok": True, "detail": None})
    out.append({"id": "F6", "titre": "arbres : tilleul du catalogue (14 m, houppier 4 m) au-dessus de la chaussée -> fût 3,80 ; "
                                     "houppier dit de 1 m au-dessus du seul trottoir -> fût 2,50 (RF-OSM-VEG-001)",
                "ok": ok9, "detail": {k: {c: v.get(c) for c in ("asset_id", "hauteur_m", "houppier_rayon_m", "fut_m")}
                                      for k, v in arb.items()}})
    # passage relié par une traversée revêtue (évènements « profil » au droit du passage) : abaissés et BEV sur les seules
    # bordures d'aboutissement (chaussée | chemin), bandes peintes sur la chaussée seulement ; profils voisins : rampants
    # sans BEV ; dévers dit (« dévers 0 ») recopié dans le modèle (correction après le second contrôle)
    base10 = "bande plantée 3 | bordure basse vue 0,06 | voie 3 ← | voie 3 → | bordure basse vue 0,06 | bande plantée 2 | trottoir 2"
    trav10 = "chemin 3 dévers 0 | bordure basse vue 0,06 | voie 3 ← | voie 3 → | bordure basse vue 0,06 | chemin 2 | trottoir 2"
    m10, r10 = D.compiler({"contexte": {"agglomeration": "oui"}, "troncon": {"longueur": 60}, "profil": base10,
                           "evenements": [{"profil": {"a": 28, "nouveau": trav10}}, {"profil": {"a": 32, "nouveau": base10}},
                                          {"passage_pieton": {"a": 30}}]}, "(t)")
    P10 = {p["id"]: p for p in m10["profils"]}
    ab10 = {s["s0"]: [(i, a["bev"]) for i, l in enumerate(P10[s["profil"]]["limites"]) if "bordure" in l["nature"]
                      for a in l["bordure"].get("abaisses", [])] for s in m10["routes"][0]["sections"]}
    pp10 = [x for x in m10.get("marquages", []) if x["type"] == "passage_pieton"]
    dv10 = [b["niveau"].get("devers_pct") for b in P10[m10["routes"][0]["sections"][1]["profil"]]["bandes"]]
    out.append({"id": "F7", "titre": "passage relié par une traversée revêtue : abaissés + BEV aux deux aboutissements (chemins) "
                                     "seulement, rampants sans BEV dans les profils voisins, une seule zone peinte (chaussée), "
                                     "dévers dit",
                "ok": ab10.get(28.0) == [(1, True), (3, True)] and ab10.get(0.0) == [(1, False), (3, False)]
                and ab10.get(32.0) == [(1, False), (3, False)] and len(pp10) == 1 and dv10[0] == 0.0,
                "detail": {"abaisses": ab10, "passages": len(pp10), "devers": dv10}})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=str(GEN / "tmp" / "tests" / "tests_description_L0.json"),
                    help="sortie JSON (défaut dans tmp/ ; validation/ seulement par faire_rapport_L0.py)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    res, sortie = {}, {"exemples": [], "catalogue_voisin": [], "meylan": [], "faits": [], "erreurs": []}
    for f in EXEMPLES + CATALOGUE + MEYLAN:
        try:
            m, r, det, sha, d = compiler(f)
            ligne = {"fichier": str(f.relative_to(GEN)).replace("\\", "/"), "scene": r["scene"], "compile": True,
                     "erreurs_validation": r["validation"]["nb_erreurs"], "deterministe": det, "sha256": sha,
                     "sections": sum(t["sections"] for t in r["troncons"]), "profils": len(m["profils"]),
                     "prov_genres": r["validation"]["prov_genres"],
                     "avertissements": sum(len(t["avertissements"]) for t in r["troncons"]) + len(r["avertissements"])}
            ligne["ok"] = ligne["erreurs_validation"] == 0 and det
            ligne["non_conformites_non_admises"] = len(r.get("non_conformites", []))
            ligne["ecarts_admis"] = sorted(r.get("ecarts_admis", {}))
            if f in MEYLAN:
                ligne["ok"] = ligne["ok"] and ligne["non_conformites_non_admises"] == 0
            res[f.stem] = {"modele": m, "rapport": r}
            if f in CATALOGUE:
                ver, nv = attendus_catalogue(m, r, d)
                ligne["attendus_verifies"] = ver
                ligne["attendus_non_verifiables_L0"] = nv
                ligne["attendus_ok"] = all(x["ok"] for x in ver)
                ligne["ok"] = ligne["ok"] and ligne["attendus_ok"]
        except Exception as e:  # noqa: BLE001 - une description qui ne compile pas est un échec rapporté
            ligne = {"fichier": str(f.relative_to(GEN)).replace("\\", "/"), "compile": False, "ok": False, "erreur": f"{type(e).__name__}: {e}"}
        sortie["catalogue_voisin" if f in CATALOGUE else ("meylan" if f in MEYLAN else "exemples")].append(ligne)
    try:
        sortie["faits"] = faits_exemples(res)
    except Exception as e:  # noqa: BLE001
        sortie["faits"] = [{"exemple": "?", "fait": "exception", "ok": False, "detail": f"{type(e).__name__}: {e}"}]
    sortie["erreurs"] = tests_erreurs()
    tous = sortie["exemples"] + sortie["catalogue_voisin"] + sortie["meylan"]
    sortie["bilan"] = {
        "descriptions": len(tous), "compilent_valides": sum(1 for x in tous if x.get("compile") and x.get("erreurs_validation") == 0),
        "deterministes": sum(1 for x in tous if x.get("deterministe")),
        "exemples": len(sortie["exemples"]), "catalogue_voisin": len(sortie["catalogue_voisin"]), "meylan": len(sortie["meylan"]),
        "catalogue_attendus_ok": sum(1 for x in sortie["catalogue_voisin"] if x.get("attendus_ok")),
        "faits": len(sortie["faits"]), "faits_ok": sum(1 for x in sortie["faits"] if x["ok"]),
        "erreurs_attendues": len(sortie["erreurs"]), "erreurs_ok": sum(1 for x in sortie["erreurs"] if x["ok"])}
    for x in tous:
        print(f"{'OK ' if x['ok'] else 'ÉCHEC'}\t{x['fichier']}\t" + (f"{x['sections']} sections, {x['erreurs_validation']} erreur(s), "
              f"déterministe={x['deterministe']}" if x.get("compile") else x.get("erreur", "")))
        for v in x.get("attendus_verifies", []):
            if not v["ok"]:
                print(f"\t\tattendu {v['attendu']} : {v['valeur_attendue']} ≠ {v['valeur_modele']}")
    for x in sortie["faits"]:
        print(f"{'OK ' if x['ok'] else 'ÉCHEC'}\tfait {x['exemple']}\t{x['fait']}" + ("" if x["ok"] else f"\n\t\t{json.dumps(x['detail'], ensure_ascii=False)[:300]}"))
    for x in sortie["erreurs"]:
        print(f"{'OK ' if x['ok'] else 'ÉCHEC'}\t{x['id']}\t{x['titre']}" + ("" if x["ok"] else f"\n\t\t{x['detail']}"))
    b = sortie["bilan"]
    print(f"descriptions valides : {b['compilent_valides']} / {b['descriptions']} ; déterministes : {b['deterministes']} ; "
          f"attendus du catalogue : {b['catalogue_attendus_ok']} / {b['catalogue_voisin']} ; faits : {b['faits_ok']} / {b['faits']} ; "
          f"erreurs attendues : {b['erreurs_ok']} / {b['erreurs_attendues']}")
    Path(a.json).parent.mkdir(parents=True, exist_ok=True)
    Path(a.json).write_bytes((json.dumps(sortie, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    tout_ok = all(x["ok"] for x in tous + sortie["faits"] + sortie["erreurs"])
    return 0 if tout_ok else 1


if __name__ == "__main__":
    sys.exit(main())
