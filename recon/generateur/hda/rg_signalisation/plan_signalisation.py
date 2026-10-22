# -*- coding: utf-8 -*-
"""Plan de signalisation verticale et de feux d'une scène fabriquée (lot L6, étape E14) — Python pur, hors Houdini.

    python recon/generateur/hda/rg_signalisation/plan_signalisation.py recon/out/generateur/<scene> [--complement F.yaml]

Le plan décide QUOI poser et OÙ l'ancrer (route, abscisse, côté, sens de l'usager visé, hauteur, gamme, règles) ; la
géométrie (position latérale par la règle de placement ARB-20 sur le sol fabriqué, recherche du point admissible le plus
proche, cheminement de 1,40 m, refus sur surface circulée ou îlot peint, hauteur, orientation, empilement des plaques)
est faite par l'HDA rg::signalisation (VEX). Comme l'inférence OSM → modèle (PLAN_GENERATEUR § 1), ce module est un
script Python hors Houdini, déterministe : mêmes entrées, mêmes octets.

Entrées (sorties des étapes antérieures, lecture seule) : modele_voie.json (régimes, branches, îlots, passages, signaux
déjà décidés par le compilateur, contrôleurs), l1/courbes_controle.json (références des routes), l3/carrefours.json
(frontières, coins), l2/entites.json et l3 (abaissés : exclusions), autoroute/musoirs.json ; et le complément de
description de la signalisation (scenes_signalisation/complements/<scene>.yaml : destinations, nom de l'agglomération,
limites de vitesse le long de l'itinéraire, numéro de sortie…). Sans complément : destinations génériques.

Règles : base fusionnée (regles_route_fr.json, par recon/generateur/regles.py) et compléments du lot
(regles_signalisation_l6.json, espace L6-). Chaque ensemble porte ses règles et sa provenance.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

ICI = Path(__file__).resolve().parent                      # recon/generateur/hda/rg_signalisation
GEN = ICI.parents[1]                                        # recon/generateur
DEPOT = GEN.parents[1]
if str(GEN) not in sys.path:
    sys.path.insert(0, str(GEN))
import regles  # noqa: E402

SCHEMA = "rg_plan_signalisation/0.1"
CATALOGUE = DEPOT / "assets" / "specs" / "route" / "catalogue_assets_route.json"
LIB = DEPOT / "assets" / "lib" / "route_fr"
COMPLEMENTS = GEN / "scenes_signalisation" / "complements"
REGLES_L6 = ICI / "regles_signalisation_l6.json"

DESTINATIONS_GENERIQUES = ("Centre-ville", "Gare", "Zone d'activités", "Hôpital", "Toutes directions", "Mairie")


def _r(x, n=4):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ règles
@lru_cache(maxsize=1)
def regles_l6():
    d = json.loads(REGLES_L6.read_text(encoding="utf-8"))
    return {r["id"]: r for r in d["regles"]}


def val_l6(ident, chemin=None):
    v = regles_l6()[ident]["valeurs"]
    for k in (chemin.split(".") if chemin else []):
        v = v[k]
    return v


def V(ident, chemin=None):
    """Valeur d'une règle de la base (RF-*, DEF-*, ARB-*) ou du complément du lot (L6-*)."""
    if ident.startswith("L6-"):
        return val_l6(ident, chemin)
    return regles.valeur(ident, chemin) if chemin else regles.valeur(ident)


# ------------------------------------------------------------------------------------------------ catalogue
@lru_cache(maxsize=1)
def catalogue():
    d = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    return {a["id"]: a for a in d["assets"]}


@lru_cache(maxsize=512)
def etendues_gammes(asset_id):
    """Étendues (xmin, zmin, xmax, zmax) par gamme, lues dans le .usda du panneau (variantes « gamme »)."""
    a = catalogue()[asset_id]
    f = LIB / a["fichiers"]["usd"]
    txt = f.read_text(encoding="utf-8")
    out, courante, prof = {}, None, 0
    for ligne in txt.splitlines():
        m = re.match(r'^\s*"(\w+)" \{\s*$', ligne)
        if m and m.group(1) in ("miniature", "petite", "normale", "grande", "tres_grande", "superieure",
                                "exceptionnelle"):
            courante = m.group(1)
            continue
        m = re.search(r"float3\[\] extent = \[\(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\), \(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\)\]",
                      ligne)
        if m and courante:
            x0, _y0, z0, x1, _y1, z1 = (float(m.group(k)) for k in range(1, 7))
            e = out.get(courante)
            if e is None:
                out[courante] = [x0, z0, x1, z1]
            else:                                        # plusieurs maillages : union
                out[courante] = [min(e[0], x0), min(e[1], z0), max(e[2], x1), max(e[3], z1)]
    if not out:
        m = re.search(r"float3\[\] extent = \[\(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\), \(([-\d.e]+), ([-\d.e]+), ([-\d.e]+)\)\]",
                      txt)
        x0, _y0, z0, x1, _y1, z1 = (float(m.group(k)) for k in range(1, 7))
        out["normale"] = [x0, z0, x1, z1]
    return out


def asset_panneau(code):
    """Identifiant d'asset du catalogue route_fr pour un code IISR (variantes de nommage du catalogue)."""
    c = catalogue()
    for cand in (f"panneau_{code}", f"panneau_{code.replace('-', '_t_')}", f"panneau_{code.upper()}",
                 f"panneau_{code[:-1] + code[-1].upper()}", f"panneau_{code}_ex1"):
        if cand in c:
            return cand
    raise KeyError(f"code {code} absent du catalogue route_fr")


def dims_plaque(code, gamme):
    """(asset, gamme effective, largeur, hauteur, zmin, zmax) d'une plaque du catalogue."""
    aid = asset_panneau(code)
    e = etendues_gammes(aid)
    g = gamme if gamme in e else ("normale" if "normale" in e else sorted(e)[0])
    x0, z0, x1, z1 = e[g]
    return aid, g, _r(x1 - x0), _r(z1 - z0), _r(z0, 5), _r(z1, 5)


def boite_asset(aid):
    b = catalogue()[aid].get("boite_usd_m")
    return b


# ------------------------------------------------------------------------------------------------ géométrie
class Reference:
    """Ligne de référence échantillonnée d'une route (l1/courbes_controle.json, repère local)."""

    def __init__(self, r):
        ref = r["reference"]
        self.id = r["id"]
        self.s, self.x, self.y = ref["s"], ref["x"], ref["y"]
        self.L = float(r["longueur_m"])

    def _k(self, s):
        s = min(max(s, self.s[0]), self.s[-1])
        lo, hi = 0, len(self.s) - 1
        while hi - lo > 1:
            m = (lo + hi) // 2
            if self.s[m] <= s:
                lo = m
            else:
                hi = m
        return lo, hi, s

    def pt(self, s):
        lo, hi, s = self._k(s)
        ds = self.s[hi] - self.s[lo]
        a = 0.0 if ds <= 0 else (s - self.s[lo]) / ds
        return (self.x[lo] + a * (self.x[hi] - self.x[lo]), self.y[lo] + a * (self.y[hi] - self.y[lo]))

    def tangente(self, s):
        lo, hi, _ = self._k(s)
        dx, dy = self.x[hi] - self.x[lo], self.y[hi] - self.y[lo]
        n = math.hypot(dx, dy) or 1.0
        return dx / n, dy / n


def droite_de(d):
    """Normale à droite d'une direction locale (x, y)."""
    return d[1], -d[0]


# ------------------------------------------------------------------------------------------------ plan
class Plan:
    def __init__(self, dossier, complement=None):
        self.dossier = Path(dossier).resolve()
        self.scene = self.dossier.name
        self.m = json.loads((self.dossier / "modele_voie.json").read_text(encoding="utf-8"))
        self.courbes = json.loads((self.dossier / "l1" / "courbes_controle.json").read_text(encoding="utf-8"))
        f3 = self.dossier / "l3" / "carrefours.json"
        self.l3 = json.loads(f3.read_text(encoding="utf-8")) if f3.exists() else None
        fm = self.dossier / "autoroute" / "musoirs.json"
        self.musoirs = json.loads(fm.read_text(encoding="utf-8")) if fm.exists() else None
        self.o = self.m["repere"]["origine_l93"]
        self.refs = {r["id"]: Reference(r) for r in self.courbes["routes"]}
        self.routes = {r["id"]: r for r in self.m["routes"]}
        self.profils = {p["id"]: p for p in self.m["profils"]}
        self.signaux = {s["id"]: s for s in self.m.get("signaux") or []}
        self.ilots = {i["id"]: i for i in self.m.get("ilots") or [] if isinstance(i, dict)}
        for c in self.m.get("carrefours") or []:
            for i in c.get("ilots") or []:
                if isinstance(i, dict):
                    self.ilots.setdefault(i["id"], i)
        self.complement_fichier = None
        self.cpl = {}
        f = Path(complement) if complement else COMPLEMENTS / f"{self.scene}.yaml"
        if f.exists():
            sys.path.insert(0, str(GEN / "description"))
            import yaml_simple as Y
            self.cpl = Y.lire(f) or {}
            self.complement_fichier = f
        self.ensembles = []
        self.exigences = []
        self.non_poses = []
        self.faces = []                                  # faces composées à dessiner (faces_composees.py)
        self.avertissements = []
        self.n_generiques = 0

    # ---------------------------------------------------------------- outils
    def local(self, xy):
        return (_r(xy[0] - self.o[0], 4), _r(xy[1] - self.o[1], 4))

    def ctx_route(self, rid):
        r = self.routes.get(rid) or {}
        cat = r.get("categorie") or ""
        return {"agglo": bool(r.get("agglomeration")), "v": float(r.get("vitesse_kmh") or 50.0), "cat": cat,
                "autoroute": cat in ("autoroute", "bretelle"), "sens_unique": r.get("sens_unique") == "oui"}

    def profil_a(self, rid, s):
        r = self.routes[rid]
        for sec in r.get("sections") or []:
            if sec["s0"] - 1e-6 <= s <= sec["s1"] + 1e-6:
                return self.profils.get(sec["profil"])
        return self.profils.get((r.get("sections") or [{}])[-1].get("profil"))

    def voies(self, rid, s, sens):
        """Nombre de voies de circulation dans le sens (avant | arriere) au droit de s."""
        p = self.profil_a(rid, s) or {}
        n = 0
        for b in p.get("bandes") or []:
            if str(b.get("type", "")).startswith("voie") and b.get("sens") == sens:
                n += 1
        return n

    def chaussees_separees(self, rid, s):
        p = self.profil_a(rid, s) or {}
        return any(b.get("type") in ("terre_plein", "separateur") for b in p.get("bandes") or [])

    def gamme(self, ctx, ilot=False, tpc_2x2=False):
        """RF-SV-DIM.CHOIX_GAMME.GENERATEUR (IISR1 art. 5-3 1), p. 10-11)."""
        if ilot:
            return "petite"
        if ctx["autoroute"]:
            return "tres_grande" if ctx["v"] >= 130 else "grande"
        if ctx["v"] >= 110:
            return "grande"
        if ctx["v"] >= 70:
            return "grande" if tpc_2x2 else "normale"
        return "normale"

    def hauteur(self, ctx, ilot=False):
        """DEF-025 / DEF-026 (ARB-04) : bord inférieur du panneau ou du panonceau associé."""
        if ilot:
            return (V("DEF-026", "prescription_agglomeration_G_conf_faible") if ctx["agglo"]
                    else V("DEF-026", "prescription_hors_agglomeration")), "DEF-026"
        return (V("DEF-025", "hauteur_trottoir_agglo") if ctx["agglo"]
                else V("DEF-025", "hauteur_rase_campagne")), "DEF-025"

    def plaque(self, code, gamme, regles_=(), texte=None):
        aid, g, l, h, z0, z1 = dims_plaque(code, gamme)
        return {"code": code, "kind": "plaque", "asset": aid, "gamme": g, "l": l, "h": h, "zmin": z0, "zmax": z1,
                "z": -1.0, "rot": 0.0, "u": 0.0, "face": "", "texte": texte or "", "regles": list(regles_)}

    def plaque_composee(self, code, nom_face, l, h, contenu, regles_=()):
        """Plaque à inscriptions de la scène (EB10, EB20, D21, D42, D43, D31, D41, C24b, M1, M9z) : face dessinée par
        faces_composees.py ; dimensions de la série IISR1 art. 5-3 2) (RF-SV-DIM.D_E_EB) ou de la gamme."""
        self.faces.append(dict(contenu, code=code, fichier=f"faces/{nom_face}.png", l=l, h=h))
        return {"code": code, "kind": "plaque_composee", "asset": "", "gamme": "", "l": _r(l), "h": _r(h), "zmin": 0.0,
                "zmax": _r(h), "z": -1.0, "rot": 0.0, "u": 0.0, "face": f"faces/{nom_face}.png",
                "texte": contenu.get("texte", ""), "regles": list(regles_)}

    def destination(self, branche_nom, k):
        dd = (self.cpl.get("directions") or {})
        if branche_nom in dd:
            return str(dd[branche_nom]), "description:complement.directions"
        self.n_generiques += 1
        return DESTINATIONS_GENERIQUES[k % len(DESTINATIONS_GENERIQUES)], "generique"

    def ajouter(self, e):
        e.setdefault("statut_plan", "a_poser")
        if "rural" not in e:
            rid = e["ancrage"].get("route") or e.get("applicabilite", {}).get("route")
            if rid:
                e["rural"] = not self.ctx_route(rid)["agglo"]
            else:
                e["rural"] = not any(r.get("agglomeration") for r in self.routes.values())
        self.ensembles.append(e)
        return e

    # ---------------------------------------------------------------- ancrages
    def anc_route(self, rid, s, sens, cote="droite", fen=(-3.0, 1.0), surface="auto"):
        return {"type": "route", "route": rid, "s": _r(s), "sens": int(sens), "cote": cote,
                "fenetre": [_r(fen[0]), _r(fen[1])], "surface": surface}

    def anc_xy(self, xy_local, dir_trafic, surface="ilot", rayon=3.0, vise=None):
        d = {"type": "xy", "xy": [_r(xy_local[0]), _r(xy_local[1])], "dir": [_r(dir_trafic[0], 6), _r(dir_trafic[1], 6)],
             "surface": surface, "rayon": rayon}
        if vise is not None:
            d["vise"] = [_r(vise[0]), _r(vise[1])]
        return d

    # ---------------------------------------------------------------- branches de carrefour
    def branches(self):
        out = []
        l3b = {}
        if self.l3:
            for b in self.l3["branches"]:
                l3b[(b["carrefour"], b["branche"])] = b
        for c in self.m.get("carrefours") or []:
            for b in c.get("branches") or []:
                x = l3b.get((c["id"], b["id"]), {})
                sgn = 1 if b.get("extremite", "fin") == "fin" else -1
                s_front = x.get("s_front", b.get("s_frontiere_m"))
                if s_front is None:
                    ref = self.refs.get(b["route"])
                    s_front = ref.L if (ref and sgn > 0) else 0.0
                out.append({"c": c, "b": b, "id": b["id"], "nom": b["id"][2:], "route": b["route"], "sgn": sgn,
                            "s_front": float(s_front), "regime": b.get("regime"), "l3": x,
                            "sens": "avant" if sgn > 0 else "arriere"})
        return out

    # ---------------------------------------------------------------- 1. signaux du modèle
    def depuis_modele(self):
        """Chaque signal décidé par le compilateur devient un ensemble (ou rejoint un ensemble de feux) ; la position
        fine est refaite par l'HDA (le compilateur pose t au bord + 0,70 + l/2 sans regarder le sol fabriqué)."""
        feux_par_support = {}
        regimes = {(c["id"], b["id"]): b.get("regime") for c in self.m.get("carrefours") or []
                   for b in c.get("branches") or []}
        for sid in sorted(self.signaux):
            sg = self.signaux[sid]
            fam, code = sg.get("famille"), sg.get("code")
            app0 = sg.get("applicabilite") or {}
            rg0 = regimes.get((app0.get("carrefour"), app0.get("branche")))
            if code == "AB4" and rg0 in ("feux", "stop_a_verifier"):
                # jamais d'AB4 sur une branche à feux (RF-SV-AB4.POSITION) ni « à vérifier » (ARB-19) : refusé
                self.non_poses.append({"code": "AB4", "id": sid, "regle": "ARB-19" if rg0 == "stop_a_verifier"
                                       else "RF-SV-AB4.POSITION", "motif": f"branche au régime « {rg0} » : AB4 refusé"})
                continue
            pos = sg.get("position") or {}
            rid = pos.get("route")
            ctx = self.ctx_route(rid) if rid else {"agglo": True, "v": 50.0, "cat": "", "autoroute": False,
                                                  "sens_unique": False}
            app = sg.get("applicabilite") or {}
            az = (sg.get("orientation") or {}).get("azimut_deg")
            # sens de l'usager visé : azimut de la face (orientation du compilateur) = vers l'usager ; trafic = opposé
            dir_trafic = None
            if az is not None:
                a = math.radians(az)
                dir_trafic = (-math.cos(a), -math.sin(a))
            sens = self._sens_trafic(rid, pos.get("s"), dir_trafic) if rid else 1
            regs = list(sg.get("regles") or [])
            if fam == "feu":
                feux_par_support.setdefault(sid, sg)
                continue
            if code == "J3":
                self._j3(sg)
                continue
            if code in ("J14a",):
                xy = self.local(pos["xyz"])
                e = {"id": f"E-{sid[3:]}", "famille": "balise", "source": f"modele:{sid}", "regles": regs + ["DEF-025"],
                     "ancrage": self.anc_xy(xy, dir_trafic or (1, 0), surface="auto", rayon=6.0),
                     "support": {"type": "poteau", "diametre_m": 0.0603}, "bas": V("DEF-025", "hauteur_rase_campagne"),
                     "regle_hauteur": "DEF-025", "elements": [self.plaque("J14a", "normale", ["RF-SV-J14"])],
                     "applicabilite": app, "exclusif": False}
                self.ajouter(e)
                continue
            cote = pos.get("cote") or "droite"
            ilot = cote == "ilot" or (sg.get("support") or {}).get("type") == "ilot"
            gamme = sg.get("gamme") or self.gamme(ctx, ilot=ilot)
            if code in ("AB3b", "AB5"):
                # AB3b = AB3a + M1 ; AB5 = AB3a + M5 (IISR3 art. 42-2 D, F) : panonceau de distance dessiné
                dist = self._distance_panonceau(sg)
                pan = self.plaque_composee("M1" if code == "AB3b" else "M5", f"{sid[3:]}_{'M1' if code == 'AB3b' else 'M5'}",
                                           1.0 if gamme != "petite" else 0.7, 0.3 if gamme != "petite" else 0.2,
                                           {"type": "panonceau", "texte": (f"{dist} m" if code == "AB3b" else f"STOP à {dist} m")},
                                           ["RF-SV-PAN.USAGES", "RF-SV-DIM.PANONCEAUX"])
                tri = self.plaque("AB5" if False else "AB3a", gamme, regs)
                tri = self._sans_panonceau_m9c(tri, gamme)
                elements = [pan, tri]
            else:
                elements = [self.plaque(code, gamme, regs)]
                for p in sg.get("panonceaux") or []:
                    if code == "AB3a" and p.get("code", "").upper() == "M9C":
                        continue                         # M9c compris dans l'asset de l'AB3a (2 plaques)
                    elements.insert(0, self.plaque(p["code"], gamme, regs))
            h, rh = self.hauteur(ctx, ilot=ilot and code not in ("AB3a", "AB4"))
            if ilot and code in ("AB3a",):
                h, rh = self.hauteur(ctx)                # AB3a d'îlot directionnel : hauteur générale (IISR1 9)
            if sg.get("hauteur_bas_m") is not None and code in ("AB3a", "AB4", "AB25", "AB2", "AB3b", "AB5"):
                h = float(sg["hauteur_bas_m"])
            if ilot:
                xy = self.local(pos["xyz"])
                anc = self.anc_xy(xy, dir_trafic or (1, 0), surface="ilot", rayon=6.0 if code == "AB3a" else 3.0)
                if code == "B21-1" and self.l3:
                    anc["surface"] = "ilot"
            else:
                fen = (-6.0, 1.0) if code in ("AB3a", "AB4") else (-10.0, 10.0)
                anc = self.anc_route(rid, pos.get("s") or 0.0, sens, "droite" if cote == "droite" else "gauche", fen)
            e = {"id": f"E-{sid[3:]}", "famille": "panneau", "source": f"modele:{sid}",
                 "regles": sorted(set(regs + ["DEF-025", "ARB-20", "RF-SV-GEN.DISTANCE_RIVE", "RF-SV-GEN.ORIENTATION"])),
                 "ancrage": anc, "support": {"type": "poteau", "diametre_m": 0.0603 if ctx["agglo"] else 0.076},
                 "bas": _r(h), "regle_hauteur": rh, "elements": elements, "applicabilite": app,
                 "exclusif": code in ("AB3a", "AB4")}
            self.ajouter(e)
        self._feux(feux_par_support)

    def _sans_panonceau_m9c(self, tri, gamme):
        return tri

    def _distance_panonceau(self, sg):
        for c in self.m.get("carrefours") or []:
            for b in c.get("branches") or []:
                if b.get("route") == sg["position"].get("route"):
                    s_f = b.get("s_frontiere_m")
                    if s_f is not None:
                        d = abs(float(s_f) - float(sg["position"]["s"]))
                        return int(round(d / 50.0) * 50) if d >= 100 else int(round(d / 10.0) * 10)
        return 150

    def _sens_trafic(self, rid, s, dir_trafic):
        ref = self.refs.get(rid)
        if ref is None or dir_trafic is None or s is None:
            return 1
        t = ref.tangente(float(s))
        return 1 if t[0] * dir_trafic[0] + t[1] * dir_trafic[1] >= 0 else -1

    def _j3(self, sg):
        """Balise J3 dans un angle (RF-SV-J3) : au sommet du coin de bordure entre les deux branches (l3), hors chaussée."""
        m = re.match(r"SG-[^.]+\.J3_(\w+)_(\w+)", sg["id"])
        coin = None
        if m and self.l3:
            de, vers = f"B-{m.group(1)}", f"B-{m.group(2)}"
            for f in self.l3.get("faces") or []:
                if f.get("kind") == "coin" and {f.get("branche_a"), f.get("branche_b")} == {de, vers}:
                    coin = f
        if coin is None or not coin.get("points"):
            self.non_poses.append({"code": "J3", "id": sg["id"], "motif": "coin introuvable dans l3/carrefours.json"})
            return
        pts = coin["points"]
        mid = pts[len(pts) // 2]
        cx, cy = (coin.get("centre_arc") or [0, 0, 0])[:2]
        # direction vers l'extérieur du carrefour : du centre du carrefour vers le milieu du coin
        cc = self.m["carrefours"][0].get("centre")
        c0 = self.local(cc) if cc else (0.0, 0.0)
        dx, dy = mid[0] - c0[0], mid[1] - c0[1]
        n = math.hypot(dx, dy) or 1.0
        anc = self.anc_xy((mid[0] + dx / n * 1.0, mid[1] + dy / n * 1.0), (-dx / n, -dy / n), surface="auto", rayon=4.0)
        self.ajouter({"id": f"E-{sg['id'][3:]}", "famille": "balise", "source": f"modele:{sg['id']}",
                      "regles": ["RF-SV-J3", "RF-SV-GEN.DISTANCE_RIVE"], "ancrage": anc,
                      "support": {"type": "aucun", "asset": "balise_J3", "diametre_m": 0.2}, "bas": 0.0,
                      "regle_hauteur": "RF-SV-J3",
                      "elements": [{"code": "J3", "kind": "balise", "asset": "balise_J3", "gamme": "", "l": 0.2,
                                    "h": 1.3, "zmin": 0.0, "zmax": 1.3, "z": 0.0, "rot": 0.0, "u": 0.0, "face": "",
                                    "texte": "", "regles": ["RF-SV-J3"]}],
                      "applicabilite": sg.get("applicabilite") or {}, "exclusif": False})

    # ---------------------------------------------------------------- feux
    def _feux(self, feux):
        """R11v (+ répétiteur) sur mât à droite du couloir, au droit ou à l'aval de la ligne d'effet (0,30 m, DEF-027) ;
        rappels sur îlot ; R12 sur le trottoir de destination ; boîtier d'appel sur le support du R12 (RF-FEU.BOUTON_APPEL) ;
        M12 sur le mât du R11 si la branche a un sas vélo ou une bande cyclable (RF-FEU.M12). Un R12 dont le support
        est à moins de 2 m du mât du R11 de même côté partage ce mât (IISR6 fig. 25-27, RF-FEU.R12.SUR_MAT_R11)."""
        if not feux:
            return
        d27 = V("DEF-027")
        cpl_feux = self.cpl.get("feux") or {}
        boutons = str(cpl_feux.get("boutons", "oui")).lower() in ("oui", "true", "1")
        br = {(x["c"]["id"], x["id"]): x for x in self.branches()}
        r11 = {k: v for k, v in feux.items() if v["code"].startswith("R11")}
        r12 = {k: v for k, v in feux.items() if v["code"] == "R12"}
        autres = {k: v for k, v in feux.items() if k not in r11 and k not in r12}
        for sid, sg in autres.items():
            self.non_poses.append({"code": sg["code"], "id": sid, "motif": "signal lumineux sans règle d'implantation au lot L6"})
        groupes = {}                                     # R12 rattachés à un mât de R11
        for sid in sorted(r12):
            sg = r12[sid]
            p = sg["position"]
            best = None
            for kid in sorted(r11):
                k = r11[kid]
                kp = k["position"]
                if kp.get("route") == p.get("route") and kp.get("cote") == p.get("cote") and kp.get("cote") != "ilot":
                    d = abs(float(kp["s"]) - float(p["s"]))
                    if d <= 2.0 + 1e-6 and (best is None or d < best[0]):
                        best = (d, kid)
            if best:
                groupes.setdefault(best[1], []).append(sid)
        poses_r12 = {x for v in groupes.values() for x in v}
        for sid in sorted(r11):
            sg = r11[sid]
            p = sg["position"]
            rid = p["route"]
            ctx = self.ctx_route(rid)
            app = sg.get("applicabilite") or {}
            a = math.radians((sg.get("orientation") or {}).get("azimut_deg", 0.0))
            dtr = (-math.cos(a), -math.sin(a))
            sens = self._sens_trafic(rid, p["s"], dtr)
            x = br.get((app.get("carrefour"), app.get("branche")))
            tetes = (sg.get("feux") or {}).get("tetes") or [{"type": "R11v", "diametre_mm": 200}]
            el = []
            for t in tetes:
                if t.get("repetiteur"):
                    b = boite_asset("feu_repetiteur_R11v_D90")
                    hc = d27["repetiteur_centre"]
                    el.append({"code": "R11v_rep", "kind": "feu", "asset": "feu_repetiteur_R11v_D90", "gamme": "",
                               "l": _r(b[1][0] - b[0][0]), "h": _r(b[1][2] - b[0][2]), "zmin": _r(b[0][2]), "zmax": _r(b[1][2]),
                               "z": _r(hc - 0.5 * 0.345), "rot": 0.0, "u": 0.0, "face": "", "texte": "",
                               "regles": ["DEF-027", "ARB-14", "RF-FEU.HAUTEUR.GENERATEUR"], "vise_arret": 1,
                               "signal": sid})
                else:
                    aid = "feu_R11v_D300" if t.get("diametre_mm") == 300 else "feu_R11v_D200"
                    b = boite_asset(aid)
                    el.append({"code": "R11v", "kind": "feu", "asset": aid, "gamme": "", "l": _r(b[1][0] - b[0][0]),
                               "h": _r(b[1][2] - b[0][2]), "zmin": _r(b[0][2]), "zmax": _r(b[1][2]),
                               "z": _r(d27["bas_boitier"]), "rot": 0.0, "u": 0.0, "face": "", "texte": "",
                               "regles": ["DEF-027", "ARB-14", "RF-FEU.HAUTEUR.TROTTOIR"], "signal": sid})
            # M12 : sas vélo ou bande cyclable sur la branche (RF-FEU.M12 ; centre [G] L6-FEU.M12.HAUTEUR)
            m12 = False
            if x is not None:
                m12 = bool(x["b"].get("sas_velo")) or self._a_bande_cyclable(rid, p["s"])
            if (cpl_feux.get("m12") is not None):
                m12 = x is not None and x["nom"] in (cpl_feux.get("m12") or [])
            if m12 and p.get("cote") != "ilot":
                # M12 : côté nominal 150 à 300 mm (RF-SV-DIM.M12) : plaque du catalogue (443 mm) ramenée à 300 mm ;
                # décalée vers la chaussée pour ne pas surplomber le cheminement sous 2,20 m (A2007 art. 1, 6° c-d)
                aid, g, l, h, z0, z1 = dims_plaque("M12a", "normale")
                k = V("RF-SV-DIM.M12", "cote_nominal_mm")[1] / 1000.0 / l
                l, h, z0, z1 = l * k, h * k, z0 * k, z1 * k
                r_mat = 0.5 * d27["mat_diametre"]
                el.append({"code": "M12a", "kind": "plaque", "asset": aid, "gamme": g, "l": _r(l, 5), "h": _r(h, 5),
                           "zmin": _r(z0, 5), "zmax": _r(z1, 5), "echelle": _r(k, 6),
                           "z": _r(V("L6-FEU.M12.HAUTEUR", "centre_m") - h / 2 - z0), "rot": 0.0,
                           "u": _r(-(l / 2 - r_mat), 4), "face": "", "texte": "",
                           "regles": ["RF-FEU.M12", "RF-SV-DIM.M12", "L6-FEU.M12.HAUTEUR", "RF-MA-TRO-008"]})
            sources = [sid]
            for k12 in groupes.get(sid, []):
                el += self._elements_r12(r12[k12], dtr, boutons)
                sources.append(k12)
            ilot = p.get("cote") == "ilot"
            if ilot:
                anc = self.anc_xy(self.local(p["xyz"]), dtr, surface="ilot", rayon=2.5)
            else:
                # au droit ou à l'aval de la ligne d'effet (RF-FEU.POSITION_LIGNE_EFFET) : fenêtre [0 ; +1] m depuis
                # l'abscisse du compilateur (ligne + 0,30 m), élargie à +3 m signalé
                anc = self.anc_route(rid, p["s"], sens, "droite", (-0.30, 3.0))
            hm = d27["mat_hauteur"] if not ilot else V("ARB-05", "hauteur_ilot_axial_m")
            self.ajouter({"id": f"E-{sid[3:]}", "famille": "feu", "source": "modele:" + ",".join(sources),
                          "regles": sorted(set((sg.get("regles") or []) + ["DEF-027", "ARB-20", "ARB-05",
                                                                           "RF-FEU.POSITION_LIGNE_EFFET",
                                                                           "RF-FEU.JUXTAPOSITION"])),
                          "ancrage": anc, "support": {"type": "mat_feux", "diametre_m": d27["mat_diametre"],
                                                      "hauteur_m": hm,
                                                      "asset": "mat_feux_D114_H42" if ilot else "mat_feux_D114_H34"},
                          "bas": _r(d27["bas_boitier"]), "regle_hauteur": "DEF-027", "elements": el,
                          "applicabilite": app, "exclusif": False,
                          "feux": {"controleur": (sg.get("feux") or {}).get("controleur"),
                                   "groupe": (sg.get("feux") or {}).get("groupe"), "signaux": sources,
                                   "ligne_effet_s": _r(float(p["s"]) - sens * d27["mat_aval_ligne_effet"])}})
        for sid in sorted(r12):
            if sid in poses_r12:
                continue
            sg = r12[sid]
            p = sg["position"]
            rid = p["route"]
            a = math.radians((sg.get("orientation") or {}).get("azimut_deg", 0.0))
            # R12 : face vers le piéton qui attend en face (orientation du compilateur) ; ancré sur le trottoir de son côté
            ref = self.refs[rid]
            t = ref.tangente(float(p["s"]))
            sens_route = 1
            cote_r = "droite" if p.get("cote") == "droite" else "gauche"
            el = self._elements_r12(sg, None, boutons, seul=True)
            self.ajouter({"id": f"E-{sid[3:]}", "famille": "feu", "source": f"modele:{sid}",
                          "regles": sorted(set((sg.get("regles") or []) + ["RF-FEU.R12.POSITION", "ARB-20"])),
                          "ancrage": dict(self.anc_route(rid, p["s"], sens_route, cote_r, (-2.0, 2.0)),
                                          face_az=_r(math.degrees(a), 3)),
                          "support": {"type": "poteau", "diametre_m": 0.076, "asset": "support_rond_D76_H30"},
                          "bas": _r(V("DEF-027", "R12_centre") - 0.24), "regle_hauteur": "DEF-027", "elements": el,
                          "applicabilite": sg.get("applicabilite") or {}, "exclusif": False,
                          "feux": {"controleur": (sg.get("feux") or {}).get("controleur"),
                                   "groupe": (sg.get("feux") or {}).get("groupe"), "signaux": [sid]}})

    def _elements_r12(self, sg, dtr_r11, boutons, seul=False):
        """R12 (centre 2,10 m, DEF-027) tourné vers le trottoir de départ ; boîtier d'appel (centre 1,00 m) sur le même
        support, tourné vers la traversée. rot = angle (°) de la face par rapport à la face du support (R11 : face vers
        l'usager ; sinon azimut absolu porté par l'ancrage)."""
        a = (sg.get("orientation") or {}).get("azimut_deg", 0.0)
        b = boite_asset("feu_R12_D200_vertical")
        el = [{"code": "R12", "kind": "feu", "asset": "feu_R12_D200_vertical", "gamme": "", "l": _r(b[1][0] - b[0][0]),
               "h": _r(b[1][2] - b[0][2]), "zmin": _r(b[0][2]), "zmax": _r(b[1][2]),
               "z": _r(V("DEF-027", "R12_centre") - 0.24), "rot": 0.0, "u": 0.0, "face": "", "texte": "",
               "regles": ["RF-FEU.R12.POSITION", "DEF-027"], "az_abs": _r(a, 3), "signal": sg["id"]}]
        if boutons:
            bb = boite_asset("feu_boitier_appel_pieton")
            el.append({"code": "bouton_appel", "kind": "feu", "asset": "feu_boitier_appel_pieton", "gamme": "",
                       "l": _r(bb[1][0] - bb[0][0]), "h": _r(bb[1][2] - bb[0][2]), "zmin": 0.0, "zmax": _r(bb[1][2]),
                       "z": _r(V("DEF-027", "bouton_appel_centre") - 0.08), "rot": 180.0, "u": 0.0, "face": "",
                       "texte": "", "regles": ["RF-FEU.BOUTON_APPEL", "DEF-027"], "az_abs": _r(a, 3)})
        return el

    def _a_bande_cyclable(self, rid, s):
        p = self.profil_a(rid, s) or {}
        return any(b.get("type") == "bande_cyclable" for b in p.get("bandes") or [])

    # ---------------------------------------------------------------- 2. îlots : J5 au nez
    def balises_j5(self):
        """J5 au nez des îlots séparateurs bordés dont la largeur le permet (RF-SV-J5, RF-GV-ILO-008 ; balise posée par le
        compilateur dans ilots[].nez[].balise) ; hauteur DEF-026 (ARB-04) : bas 1,00 m ; sommet ≤ 1,00 m en tête d'îlot
        de route principale hors agglomération (ACI p. 69, ARB-04)."""
        for iid in sorted(self.ilots):
            il = self.ilots[iid]
            for k, nez in enumerate(il.get("nez") or []):
                if nez.get("balise") != "J5":
                    if nez.get("balise") == "aucune":
                        self.non_poses.append({"code": "J5", "id": f"{iid}.nez{k}", "regle": "RF-GV-ILO-008",
                                               "motif": "îlot trop étroit pour une J5 (balise « aucune » du compilateur)"})
                    continue
                xy = self.local(nez["position"])
                d = self._dir_ilot(il, xy)
                rid = (il.get("porte_par_profil") or {}).get("route")
                ctx = self.ctx_route(rid) if rid else {"agglo": True, "v": 50.0, "autoroute": False, "cat": ""}
                # gamme de la J5 selon la largeur de l'îlot entre rives à 1,5 m du nez : 700 mm si ≥ 2,10 m, sinon
                # 500 mm (≥ 1,90 m) (RF-SV-J5 largeur_ilot_min, RF-GV-ILO-008) ; plaque du catalogue (700 mm) à l'échelle
                larg = self._largeur_ilot(il, (xy[0] + d[0] * 1.5, xy[1] + d[1] * 1.5), d)
                aid, g, l, h, z0, z1 = dims_plaque("J5", "normale")
                k_ech = 1.0 if (larg is None or larg >= 2.10 - 1e-6) else 0.5 / 0.7
                bas = V("DEF-026", "J5")
                prin = False
                if not ctx["agglo"] and rid:
                    prin = any(x["route"] == rid and x["regime"] == "prioritaire" for x in self.branches())
                if prin:
                    bas = _r(V("DEF-026", "J5_sommet_max_tete_ilot_route_principale") - h * k_ech)
                el = self.plaque("J5", g, ["RF-SV-J5"])
                if k_ech != 1.0:
                    for kk in ("l", "h", "zmin", "zmax"):
                        el[kk] = _r(el[kk] * k_ech, 5)
                    el["echelle"] = _r(k_ech, 6)
                    el["regles"].append("RF-GV-ILO-008")
                # support 0,6 m en arrière de la pointe [G], recherche jusqu'à 3 m le long de l'îlot
                q = (xy[0] + d[0] * 0.6, xy[1] + d[1] * 0.6)
                self.ajouter({"id": f"E-J5nez.{iid[2:]}.{k}", "famille": "balise", "source": f"modele:{iid}.nez[{k}]",
                              "regles": ["RF-SV-J5", "DEF-026", "ARB-04", "RF-GV-ILO-008"],
                              "ancrage": self.anc_xy(q, d, surface="ilot", rayon=3.0),
                              "support": {"type": "poteau", "diametre_m": 0.0603}, "bas": _r(bas),
                              "regle_hauteur": "DEF-026" + (" (sommet ≤ 1,00 m, route principale hors agglomération)" if prin else ""),
                              "elements": [el], "applicabilite": {"ilot": iid},
                              "largeur_ilot_m": None if larg is None else _r(larg, 3), "exclusif": False})

    def _largeur_ilot(self, il, p, d):
        """Largeur de l'îlot (polygone du modèle) sur la perpendiculaire à d passant par p."""
        poly = il.get("polygone") or {}
        pts = poly.get("exterieur") if isinstance(poly, dict) else poly
        if not pts or len(pts) < 3:
            return None
        loc = [self.local(q) for q in pts]
        n = (-d[1], d[0])
        ts = []
        for a, b in zip(loc, loc[1:] + loc[:1]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            den = n[0] * ey - n[1] * ex
            if abs(den) < 1e-12:
                continue
            # p + n·t = a + e·u
            t_ = ((a[0] - p[0]) * ey - (a[1] - p[1]) * ex) / den
            u = ((a[0] - p[0]) * n[1] - (a[1] - p[1]) * n[0]) / den
            if -1e-9 <= u <= 1 + 1e-9:
                ts.append(t_)
        neg = [x for x in ts if x <= 0]
        pos = [x for x in ts if x >= 0]
        if not neg or not pos:
            return None
        return min(pos) - max(neg)

    def _dir_ilot(self, il, nez_xy):
        """Direction du trafic qui aborde le nez : du centre de l'îlot vers le nez, retournée (le trafic arrive face au
        nez)."""
        poly = il.get("polygone") or {}
        pts = poly.get("exterieur") if isinstance(poly, dict) else poly
        if not pts:
            return (1.0, 0.0)
        loc = [self.local(p) for p in pts]
        cx = sum(p[0] for p in loc) / len(loc)
        cy = sum(p[1] for p in loc) / len(loc)
        dx, dy = nez_xy[0] - cx, nez_xy[1] - cy
        n = math.hypot(dx, dy) or 1.0
        return (-dx / n, -dy / n)

    # ---------------------------------------------------------------- 3. directions (D21, D42, D43, D31, D41)
    def directions(self):
        brs = self.branches()
        par_car = {}
        for x in brs:
            par_car.setdefault(x["c"]["id"], []).append(x)
        for cid in sorted(par_car):
            bs = sorted(par_car[cid], key=lambda x: x["id"])
            c = bs[0]["c"]
            typ = c.get("type")
            if typ == "bifurcation":
                continue
            # destinations : par branche (destination atteinte en sortant par cette branche)
            dest = {}
            for k, x in enumerate(sorted(bs, key=lambda x: x["id"])):
                dest[x["nom"]] = self.destination(x["nom"], k)
            for x in bs:
                if x["regime"] in ("sortie_seule",):
                    continue
                ctx = self.ctx_route(x["route"])
                autres = [y for y in bs if y is not x and y["regime"] != "entree_seule"]
                mouvements = []
                for y in autres:
                    da = (y["b"].get("azimut_deg", 0.0) - x["b"].get("azimut_deg", 0.0)) % 360.0
                    # azimut des branches depuis le centre : l'usager de x arrive en direction (az_x + 180) ;
                    # tourne-à-droite si y est à droite (az_y = az_x + 90 dans le sens horaire : da ≈ 270)
                    rel = (da - 180.0) % 360.0           # 0 = tout droit, 90 = gauche, 270 = droite
                    sens_m = "TD" if rel < 45 or rel > 315 else ("TAG" if rel < 180 else "TAD")
                    mouvements.append((sens_m, y, dest[y["nom"]]))
                if typ in ("giratoire", "mini_giratoire"):
                    self._d42b(x, bs, dest, ctx)
                    self._d21_sortie_giratoire(x, c, dest)
                elif typ == "plan_feux" or len(bs) > 4 or c.get("ilots"):
                    self._d42a(x, bs, dest, ctx, mouvements)
                else:
                    if not ctx["agglo"]:
                        self._d43(x, mouvements, ctx)
                    if x["regime"] in ("cedez", "stop") and len(bs) == 3:
                        self._d21_face(x, bs, mouvements, ctx)

    def _vitesse_ms(self, ctx):
        return ctx["v"] / 3.6

    def _s_amont(self, x, d):
        """Abscisse d'un panneau avancé à d m en amont de la frontière ; tronçon trop court : début du tronçon
        (L6-SV-D42.DISTANCE_COURTE)."""
        s = x["s_front"] - x["sgn"] * d
        ref = self.refs[x["route"]]
        lo, hi = 5.0, ref.L - 5.0
        reduit = not (lo <= s <= hi)
        return min(max(s, lo), hi), reduit

    ECHELONNEMENT_M = 15.0

    def _echelonner(self, x, s, code, d_regl=None):
        """Panneau de direction : il ne doit pas masquer un panneau du même sens (IISR1 art. 4 : supports échelonnés,
        RF-SV-GEN.CONCENTRATION) ; écart minimal 15 m [G]. Décalage vers l'amont, sinon vers l'aval, en restant « à
        environ » la distance réglementaire (0,5 à 1,5 fois, [G]) quand elle tient dans le tronçon. Renvoie l'abscisse,
        ou None (non posé, écrit dans non_poses)."""
        ref = self.refs[x["route"]]
        autres = [float(e["ancrage"]["s"]) for e in self.ensembles if e["ancrage"].get("route") == x["route"]
                  and e["ancrage"].get("sens") == x["sgn"]]
        E = self.ECHELONNEMENT_M

        def libre(v):
            return 5.0 - 1e-6 <= v <= ref.L - 5.0 + 1e-6 and all(abs(v - o) >= E - 1e-6 for o in autres)

        def admissible(v):
            if d_regl is None:
                return True
            dd = abs(x["s_front"] - v)
            reduit = not (5.0 <= x["s_front"] - x["sgn"] * d_regl <= ref.L - 5.0)
            return reduit or 0.5 * d_regl - 1e-6 <= dd <= 1.5 * d_regl + 1e-6
        if libre(s):
            return s
        cands = sorted({o + k * E * sg for o in autres for k in (1,) for sg in (-1, 1)}, key=lambda v: abs(v - s))
        for v in cands:
            if libre(v) and admissible(v):
                return v
        self.non_poses.append({"code": code, "branche": x["id"], "regle": "L6-SV-D42.DISTANCE_COURTE",
                               "motif": "aucune place à 15 m des autres panneaux du même sens, à environ la distance "
                                        "réglementaire, dans le tronçon — non posé"})
        return None

    def _d42b(self, x, bs, dest, ctx):
        d = self._vitesse_ms(ctx) * V("RF-SV-D.TEMPS_DE_PARCOURS", "D42a_D42b_s")
        if not ctx["agglo"]:
            d = max(d, 150.0)                            # rase campagne : D42 à 150 m, avancé (AB25) à 100 m
        s, reduit = self._s_amont(x, d)
        s = self._echelonner(x, s, "D42b", d)
        if s is None:
            return None
        branches_diag = []
        for y in bs:
            if y is x:
                continue
            branches_diag.append({"azimut": _r((y["b"].get("azimut_deg", 0.0) - x["b"].get("azimut_deg", 0.0) + 270.0) % 360.0, 2),
                                  "texte": dest[y["nom"]][0]})
        l, h = (1.6, 1.3) if ctx["agglo"] else (1.9, 1.6)
        el = [self.plaque_composee("D42b", f"D42b_{x['nom']}", l, h,
                                   {"type": "D42b", "branches": branches_diag, "distance": None},
                                   ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-DIM.D_E_EB"])]
        bas, rh = self.hauteur(ctx)
        e = self.ajouter({"id": f"E-D42b.{x['nom']}", "famille": "panneau", "source": "plan:IISR5 art. 83-4, 84 A 2 c",
                          "regles": ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-D.HAUTEURS", "RF-SV-GIR.POSITION", "DEF-025", "ARB-20"]
                          + (["L6-SV-D42.DISTANCE_COURTE"] if reduit else []),
                          "ancrage": self.anc_route(x["route"], s, x["sgn"], "droite", (-10.0, 10.0)),
                          "support": {"type": "poteau", "diametre_m": 0.089}, "bas": _r(bas),
                          "regle_hauteur": rh, "elements": el, "applicabilite": {"branche": x["id"]}, "exclusif": False,
                          "distance_reglementaire_m": _r(d), "distance_reduite": reduit})
        # rase campagne : avancé (AB25) ramené à 100 m quand le D42b est à 150 m (RF-SV-AVANCE.DIST.RASE_CAMPAGNE)
        if not ctx["agglo"]:
            for f in self.ensembles:
                if f["source"].startswith("modele:") and f["applicabilite"].get("branche") == x["id"] and \
                        any(el["code"] == "AB25" for el in f["elements"]):
                    s100, _ = self._s_amont(x, 100.0)
                    f["ancrage"]["s"] = _r(s100)
                    f["regles"] = sorted(set(f["regles"] + ["RF-SV-AVANCE.DIST.RASE_CAMPAGNE"]))
                    f["note"] = "AB25 ramené à 100 m : D42b à 150 m (RF-SV-AVANCE.DIST.RASE_CAMPAGNE)"
        return e

    def _d42a(self, x, bs, dest, ctx, mouvements):
        d = self._vitesse_ms(ctx) * V("RF-SV-D.TEMPS_DE_PARCOURS", "D42a_D42b_s")
        s, reduit = self._s_amont(x, d)
        s = self._echelonner(x, s, "D42a", d)
        if s is None:
            return None
        diag = [{"azimut": _r({"TD": 90.0, "TAG": 180.0, "TAD": 0.0}[m] if True else 0, 2), "texte": t[0]}
                for m, y, t in mouvements]
        l, h = 1.6, 1.3
        el = [self.plaque_composee("D42a", f"D42a_{x['nom']}", l, h, {"type": "D42a", "branches": diag},
                                   ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-DIM.D_E_EB"])]
        bas, rh = self.hauteur(ctx)
        self.ajouter({"id": f"E-D42a.{x['nom']}", "famille": "panneau", "source": "plan:IISR5 art. 83-4, 84 A 2 c",
                      "regles": ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-D.HAUTEURS", "DEF-025", "ARB-20"]
                      + (["L6-SV-D42.DISTANCE_COURTE"] if reduit else []),
                      "ancrage": self.anc_route(x["route"], s, x["sgn"], "droite", (-10.0, 10.0)),
                      "support": {"type": "poteau", "diametre_m": 0.089}, "bas": _r(bas),
                      "regle_hauteur": rh, "elements": el, "applicabilite": {"branche": x["id"]}, "exclusif": False,
                      "distance_reglementaire_m": _r(d), "distance_reduite": reduit})

    def _d43(self, x, mouvements, ctx):
        d = self._vitesse_ms(ctx) * V("RF-SV-D.TEMPS_DE_PARCOURS", "D43_s")
        s, reduit = self._s_amont(x, d)
        s = self._echelonner(x, s, "D43", d)
        if s is None:
            return None
        ordre = {"TAG": 0, "TD": 1, "TAD": 2}
        plaques = []
        for m, y, (t, src) in sorted(mouvements, key=lambda z: (ordre[z[0]], z[1]["id"])):
            plaques.append({"texte": t, "fleche": m})
        el = []
        for k, p in enumerate(reversed(plaques)):        # de bas en haut : TAD en bas, TAG en haut
            el.append(self.plaque_composee("D43", f"D43_{x['nom']}_{k}", 1.3 if len(p["texte"]) <= 10 else 1.6, 0.4,
                                           {"type": "D43", "texte": p["texte"], "fleche": p["fleche"], "fond": "blanc"},
                                           ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-DIM.D_E_EB"]))
        bas, rh = self.hauteur(ctx)
        self.ajouter({"id": f"E-D43.{x['nom']}", "famille": "panneau", "source": "plan:IISR5 art. 83-4, 84 A 1",
                      "regles": ["RF-SV-D.TEMPS_DE_PARCOURS", "RF-SV-D.HAUTEURS", "DEF-025", "ARB-20",
                                 "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE"] + (["L6-SV-D42.DISTANCE_COURTE"] if reduit else []),
                      "ancrage": self.anc_route(x["route"], s, x["sgn"], "droite", (-10.0, 10.0)),
                      "support": {"type": "poteau", "diametre_m": 0.089},
                      "bas": _r(V("RF-SV-D.HAUTEURS", "simple")["D43"] if ctx["agglo"] else bas), "regle_hauteur": "RF-SV-D.HAUTEURS",
                      "elements": el, "applicabilite": {"branche": x["id"]}, "exclusif": False,
                      "distance_reglementaire_m": _r(d), "distance_reduite": reduit})

    def _d21_face(self, x, bs, mouvements, ctx):
        """Carrefour en T : ensemble D21 en face de la branche non prioritaire, de l'autre côté de la chaussée abordée
        (L6-SV-D21.FACE_A_LA_BRANCHE [G])."""
        ref = self.refs[x["route"]]
        s_f = x["s_front"]
        p = ref.pt(s_f - x["sgn"] * 0.5)
        t = ref.tangente(s_f)
        d = (t[0] * x["sgn"], t[1] * x["sgn"])
        # largeur de la chaussée abordée : branches prioritaires
        larg = 0.0
        for y in bs:
            if y is not x and y["l3"]:
                larg = max(larg, abs(y["l3"].get("t_g", 3.0)) + abs(y["l3"].get("t_d", -3.0)))
        larg = larg or 7.0
        q = (p[0] + d[0] * (larg + 1.6), p[1] + d[1] * (larg + 1.6))
        plaques = []
        ordre = {"TAG": 0, "TD": 1, "TAD": 2}
        for m, y, (txt, src) in sorted(mouvements, key=lambda z: (ordre[z[0]], z[1]["id"])):
            plaques.append((m, txt))
        el = []
        for k, (m, txt) in enumerate(reversed(plaques)):
            sens_f = "gauche" if m == "TAG" else "droite"
            el.append(self.plaque_composee("D21b", f"D21b_{x['nom']}_{k}", 1.3, 0.3,
                                           {"type": "D21", "texte": txt, "pointe": sens_f, "fond": "blanc"},
                                           ["RF-SV-D21.POSITION", "RF-SV-DIM.D_E_EB"]))
        self.ajouter({"id": f"E-D21.{x['nom']}", "famille": "panneau", "source": "plan:IISR5 art. 83-1, 84 A 1",
                      "regles": ["RF-SV-D21.POSITION", "RF-SV-D.HAUTEURS", "L6-SV-D21.FACE_A_LA_BRANCHE", "DEF-025", "ARB-20"],
                      "ancrage": self.anc_xy(q, d, surface="auto", rayon=6.0),
                      "support": {"type": "poteau", "diametre_m": 0.076}, "bas": _r(self.hauteur(ctx)[0]),
                      "regle_hauteur": "RF-SV-D.HAUTEURS", "elements": el, "applicabilite": {"branche": x["id"]},
                      "exclusif": False})

    def _d21_sortie_giratoire(self, x, c, dest):
        """D21 de position à la sortie par la branche x, sur le côté droit de la sortie, face aux usagers de l'anneau
        (L6-SV-D21.SORTIE_GIRATOIRE [G])."""
        ref = self.refs[x["route"]]
        s = x["s_front"] - x["sgn"] * 3.0
        ctx = self.ctx_route(x["route"])
        txt, src = dest[x["nom"]]
        cc = self.local(c["centre"]) if c.get("centre") else (0.0, 0.0)
        p = ref.pt(s)
        # usagers de l'anneau (sens trigonométrique) arrivant sur la sortie : visée = point de l'anneau 15 m avant
        ang = math.atan2(p[1] - cc[1], p[0] - cc[0])
        an = c.get("anneau") or {}
        rg = float(an.get("rayon_exterieur_m") or 20.0) - float(an.get("largeur_anneau_m") or 7.0) / 2
        a2 = ang - 15.0 / max(rg, 5.0)
        vise = (cc[0] + rg * math.cos(a2), cc[1] + rg * math.sin(a2))
        el = [self.plaque_composee("D21b", f"D21b_sortie_{x['nom']}", 1.3, 0.3,
                                   {"type": "D21", "texte": txt, "pointe": "droite", "fond": "blanc"},
                                   ["RF-SV-D21.POSITION", "RF-SV-DIM.D_E_EB"])]
        anc = self.anc_route(x["route"], s, -x["sgn"], "droite", (-3.0, 3.0))
        anc["vise"] = [_r(vise[0]), _r(vise[1])]
        self.ajouter({"id": f"E-D21.sortie_{x['nom']}", "famille": "panneau", "source": "plan:IISR5 art. 84 A 2 c",
                      "regles": ["RF-SV-D21.POSITION", "RF-SV-D.HAUTEURS", "L6-SV-D21.SORTIE_GIRATOIRE", "DEF-025", "ARB-20"],
                      "ancrage": anc, "support": {"type": "poteau", "diametre_m": 0.076},
                      "bas": _r(V("RF-SV-D.HAUTEURS", "complexe_giratoire")["D21"]), "regle_hauteur": "RF-SV-D.HAUTEURS",
                      "elements": el, "applicabilite": {"branche": x["id"], "sortie": True}, "exclusif": False})

    # ---------------------------------------------------------------- 4. voies affectées : C24b
    def voies_affectees(self):
        """Branche à flèches d'affectation (voies en amont > voies du mouvement direct) : C24b en position au début des
        voies affectées, à droite (RF-MQ-DIR-01, RF-SV-C24.EMPLOI ; IISR7 p. 23)."""
        for x in self.branches():
            fl = x["b"].get("fleches") or []
            types = [tuple(f.get("types") or []) for f in fl]
            if not fl or all(t in (("TD",),) for t in types):
                continue
            ctx = self.ctx_route(x["route"])
            # ordre des voies de gauche à droite pour l'usager : bandes_entrantes du modèle
            ordre = x["b"].get("bandes_entrantes") or [f["bande"] for f in fl]
            par_bande = {f["bande"]: (f.get("types") or ["TD"])[0] for f in fl}
            voies = [par_bande.get(b, "TD") for b in ordre]
            # début : flèche la plus en amont (pointe de la dernière à 1,50 m de la ligne + 2 × 20 m, DEF-017)
            n = max(int(f.get("nombre", 3)) for f in fl)
            inter = max(float(f.get("intervalle_m", 20.0)) for f in fl)
            recul = float(fl[0].get("recul_derniere_m", 1.5))
            ligne = x["b"].get("ligne_arret") or {}
            s_l = x["s_front"] - x["sgn"] * float(ligne.get("distance_m", 0.0))
            s = s_l - x["sgn"] * (recul + (n - 1) * inter + V("DEF-017", "longueur"))
            s, _ = self._s_amont(x, abs(x["s_front"] - s))
            el = [self.plaque_composee("C24b", f"C24b_{x['nom']}", 0.7 if len(voies) <= 2 else 1.05, 0.7,
                                       {"type": "C24b", "voies": voies}, ["RF-SV-C24.EMPLOI", "RF-MQ-DIR-01"])]
            bas, rh = self.hauteur(ctx)
            self.ajouter({"id": f"E-C24b.{x['nom']}", "famille": "panneau", "source": "plan:RF-MQ-DIR-01",
                          "regles": ["RF-MQ-DIR-01", "RF-SV-C24.EMPLOI", "DEF-025", "ARB-20"],
                          "ancrage": self.anc_route(x["route"], s, x["sgn"], "droite", (-6.0, 6.0)),
                          "support": {"type": "poteau", "diametre_m": 0.0603}, "bas": _r(bas), "regle_hauteur": rh,
                          "elements": el, "applicabilite": {"branche": x["id"], "voies": voies}, "exclusif": False})
            self.exigences.append({"id": f"X-C24.{x['nom']}", "branche": x["id"], "type": "voies_affectees",
                                   "codes": ["C24a", "C24b", "Da30"], "regle": "RF-MQ-DIR-01",
                                   "ensembles": [f"E-C24b.{x['nom']}"]})

    # ---------------------------------------------------------------- 5. sections : vitesse, sens unique, ralentisseurs, passages
    def sections(self):
        if self.m.get("carrefours"):
            pass
        for rid in sorted(self.routes):
            r = self.routes[rid]
            if rid not in self.refs or r.get("categorie") == "anneau_giratoire":
                continue
            ref = self.refs[rid]
            ctx = self.ctx_route(rid)
            # ---- sens unique (RF-SV-C12.EMPLOI, RF-SV-B1.POSITION) : rue seule (sans carrefour)
            if ctx["sens_unique"] and not ctx["autoroute"] and not r.get("carrefour_fin") and not r.get("carrefour_debut"):
                self._sens_unique(rid, ref, ctx)
            # ---- ralentisseurs et passages des tronçons sans carrefour
            if not r.get("carrefour_fin") and not r.get("carrefour_debut") and not ctx["autoroute"]:
                self._objets_section(rid, ref, ctx)

    def _ensemble_simple(self, ident, codes, rid, s, sens, ctx, regles_, source, cote="droite", fen=(-6.0, 6.0),
                         textes=None, composes=None, note=None):
        """Ensemble sur un support : codes de bas en haut (premier = le plus bas)."""
        g = self.gamme(ctx)
        el = []
        for k, c in enumerate(codes):
            if composes and c in composes:
                el.append(composes[c])
            else:
                el.append(self.plaque(c, g, regles_))
        bas, rh = self.hauteur(ctx)
        e = {"id": ident, "famille": "panneau", "source": source,
             "regles": sorted(set(list(regles_) + ["DEF-025", "ARB-20", "RF-SV-GEN.DISTANCE_RIVE"])),
             "ancrage": self.anc_route(rid, s, sens, cote, fen),
             "support": {"type": "poteau", "diametre_m": 0.0603 if ctx["agglo"] else 0.076}, "bas": _r(bas),
             "regle_hauteur": rh, "elements": el, "applicabilite": {"route": rid, "sens": "avant" if sens > 0 else "arriere"},
             "exclusif": False}
        if note:
            e["note"] = note
        return self.ajouter(e)

    def _sens_unique(self, rid, ref, ctx):
        self._ensemble_simple(f"E-C12.{rid}", ["C12"], rid, 5.0, 1, ctx, ["RF-SV-C12.EMPLOI"],
                              "plan:IISR5 art. 71 (début de section, position)")
        e = self._ensemble_simple(f"E-B1.{rid}", ["B1"], rid, ref.L - 5.0, -1, ctx, ["RF-SV-B1.POSITION"],
                                  "plan:IISR4 art. 50-1 (vu par l'usager qui entrerait à contresens)")
        self.exigences.append({"id": f"X-B1.{rid}", "route": rid, "type": "sens_unique", "codes": ["B1"],
                               "regle": "RF-SV-B1.POSITION", "ensembles": [e["id"]]})

    def _objets_section(self, rid, ref, ctx):
        ralent = []
        for o in self.m.get("objets") or []:
            rat = o.get("rattachement") or {}
            if (rat.get("route") or o.get("route")) != rid or o.get("type") not in ("plateau", "dos_d_ane"):
                continue
            lg = float((o.get("dimensions") or {}).get("longueur_m") or o.get("longueur_m") or 4.0)
            ralent.append((float(rat.get("s", o.get("s", 0.0))), o["type"], lg, o))
        pps = []
        for mq in self.m.get("marquages") or []:
            a = mq.get("ancrage") or {}
            if mq.get("type") == "passage_pieton" and a.get("route") == rid:
                pps.append(float(a.get("s", -1.0)))
        v30 = ctx["v"] <= 30.0
        zone30 = bool(self.cpl.get("zone_30") or False)
        # limitation propre à la rue (« signalée à tous ceux qui y entrent », RF-SV-B14.EMPLOI) : B14 30 aux deux entrées
        entrees = {}
        if v30 and ctx["agglo"] and not zone30 and not self.cpl.get("sans_b14_entree"):
            for sens, s in ((1, 5.0), (-1, ref.L - 5.0)):
                entrees[sens] = self._ensemble_simple(f"E-B14_30.{rid}.{'av' if sens > 0 else 'ar'}", ["B14_30"], rid, s,
                                                      sens, ctx, ["RF-SV-B14.EMPLOI"],
                                                      "plan:IISR4 art. 63 (limite propre à la rue, à son entrée)")
        for s0, t, lg, o in sorted(ralent, key=lambda z: z[0]):
            passage = any(abs(sp - s0) <= lg / 2 + 1e-6 for sp in pps)
            for sens in (1, -1):
                s_deb = s0 - sens * lg / 2
                tag = "av" if sens > 0 else "ar"
                if passage:
                    # passage surélevé : C20a + M9d en position (RF-SV-C20A.EMPLOI : M9d obligatoire)
                    e = self._ensemble_simple(f"E-C20a_M9d.{rid}.{tag}", ["M9D", "C20a"], rid, s_deb - sens * 0.5, sens,
                                              ctx, ["RF-SV-C20A.EMPLOI", "RF-SV-C20A.POSITION.GENERATEUR"],
                                              "plan:IISR5 art. 72-1 (passage surélevé : M9d obligatoire)", fen=(-4.0, 0.5))
                    self.exigences.append({"id": f"X-C20a.{rid}.{tag}", "route": rid, "type": "passage_sureleve",
                                           "codes": ["C20a", "M9D"], "regle": "RF-SV-C20A.EMPLOI", "ensembles": [e["id"]]})
                if not zone30 and not passage:
                    # C27 en position, obligatoire hors zone 30 (RF-SV-C27.RALENTISSEUR)
                    e = self._ensemble_simple(f"E-C27.{rid}.{tag}", ["C27"], rid, s_deb - sens * 0.5, sens, ctx,
                                              ["RF-SV-C27.RALENTISSEUR"],
                                              "plan:IISR5 art. 72-6 (C27 en position, obligatoire hors zone 30)",
                                              fen=(-4.0, 0.5))
                    self.exigences.append({"id": f"X-C27.{rid}.{tag}", "route": rid, "type": "ralentisseur",
                                           "codes": ["C27"], "regle": "RF-SV-C27.RALENTISSEUR", "ensembles": [e["id"]]})
                # avancé à 10-50 m (agglomération, RF-SV-A.DISTANCE) : dos-d'âne A2b + B14 30 (RF-SV-C27.RALENTISSEUR) ;
                # passage surélevé A13b + B14 30 + M9d (RF-SV-A13B.EMPLOI ; ordre RF-SV-ORDRE.VERTICAL : danger,
                # prescription, panonceau commun)
                danger = ["B14_30", "A13b"] if passage else ["B14_30", "A2b"]
                pan = ["M9D"] if passage else []
                regs2 = (["RF-SV-A13B.EMPLOI"] if passage else ["RF-SV-C27.RALENTISSEUR"]) +                     ["RF-SV-A.DISTANCE", "RF-SV-ORDRE.VERTICAL"]
                ent = entrees.get(sens)
                lo, hi = V("RF-SV-A.DISTANCE", "agglo_m")
                if ent is not None and lo <= abs(s_deb - ent["ancrage"]["s"]) <= hi:
                    # le support d'entrée (B14 30) reçoit le panneau de danger au-dessus et le panonceau commun dessous
                    g = self.gamme(ctx)
                    ent["elements"] = [self.plaque(c, g, regs2) for c in pan] + ent["elements"] +                         [self.plaque(danger[-1], g, regs2)]
                    ent["regles"] = sorted(set(ent["regles"] + regs2))
                    ent["note"] = f"avancé du {t} à {abs(s_deb - ent['ancrage']['s']):.0f} m sur le support d'entrée"
                    continue
                d_av = V("RF-SV-A.DISTANCE", "agglo_cible_m")
                s_av = s_deb - sens * d_av
                if not (3.0 <= s_av <= ref.L - 3.0):
                    s_av = s_deb - sens * lo if lo > 0 else s_deb - sens * 10.0
                if not (3.0 <= s_av <= ref.L - 3.0):
                    self.non_poses.append({"code": danger[-1], "route": rid, "motif": "avancé hors du tronçon"})
                    continue
                self._ensemble_simple(f"E-avance_{t}.{rid}.{tag}", pan + danger, rid, s_av, sens, ctx, regs2,
                                      f"plan:avancé du ralentisseur à {abs(s_deb - s_av):.0f} m", fen=(-8.0, 8.0))
        # passages piétons hors ralentisseur : C20a facultatif, en position (RF-SV-C20A.EMPLOI)
        for sp in pps:
            if sp < 0 or any(abs(sp - r[0]) <= r[2] / 2 + 1e-6 for r in ralent):
                continue
            w = 4.0
            for sens in (1, -1):
                tag = "av" if sens > 0 else "ar"
                self._ensemble_simple(f"E-C20a.{rid}.{tag}.{int(sp)}", ["C20a"], rid, sp - sens * (w / 2 + 0.5), sens, ctx,
                                      ["RF-SV-C20A.EMPLOI", "RF-SV-C20A.POSITION.GENERATEUR"],
                                      "plan:IISR5 art. 72-1 (facultatif, position)", fen=(-4.0, 0.5))

    # ---------------------------------------------------------------- 6. itinéraire décrit (complément) : EB10/EB20, B14, panneaux
    def itineraire(self):
        """Séquences décrites dans le complément : entrée et sortie d'agglomération (EB10 / EB20, RF-SV-EB.POSITION ;
        AB6 / AB7 au-dessus, B14 dessous, RF-SV-ORDRE.VERTICAL), paliers de vitesse (RF-SV-B14.EMPLOI), fin de
        limitation (L6-SV-B33.EMPLOI) et panneaux décrits un à un."""
        agg = self.cpl.get("agglomeration") or {}
        lim = self.cpl.get("limite_agglomeration")
        if lim:
            rid = self._route_de(lim.get("troncon"))
            s = float(lim["a"])
            ctx_in = dict(self.ctx_route(rid), agglo=True, v=50.0)
            nom = str(agg.get("nom") or "AGGLOMÉRATION")
            cart = agg.get("cartouche")
            # EB10 face aux usagers qui entrent (sens avant), EB20 au dos pour ceux qui sortent (sens arrière)
            for code, sens, cote in (("EB10", 1, "droite"), ("EB20", -1, "droite")):
                el = []
                l, h = (1.6, 0.6) if len(nom) <= 10 else (2.2, 0.6)
                el.append(self.plaque_composee(code, f"{code}_{rid}", l, h,
                                               {"type": code, "texte": nom, "commune": agg.get("commune")},
                                               ["RF-SV-EB.POSITION", "RF-SV-DIM.D_E_EB"]))
                if cart:
                    el.append(self.plaque_composee("E42", f"E42_{code}_{rid}", 0.8, 0.25,
                                                   {"type": "E42", "texte": str(cart)}, ["RF-SV-EB.POSITION"]))
                ctx_ = ctx_in if code == "EB10" else dict(self.ctx_route(rid), agglo=False,
                                                          v=float(lim.get("vitesse_hors", 80)))
                bas = V("DEF-025", "hauteur_rase_campagne")       # posé en limite : hauteur de rase campagne côté entrant
                e = self.ajouter({"id": f"E-{code}.{rid}", "famille": "panneau", "source": "description:complement.limite_agglomeration",
                                  "regles": ["RF-SV-EB.POSITION", "RF-SV-ORDRE.VERTICAL", "DEF-025", "ARB-20",
                                             "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE"],
                                  "ancrage": self.anc_route(rid, s, sens, cote, (-3.0, 3.0)),
                                  "support": {"type": "poteau", "diametre_m": 0.089}, "bas": _r(bas),
                                  "regle_hauteur": "DEF-025 (rase campagne : 1,00 m)", "elements": el,
                                  "applicabilite": {"route": rid, "sens": "avant" if sens > 0 else "arriere"},
                                  "exclusif": False})
                self.exigences.append({"id": f"X-{code}.{rid}", "route": rid, "type": "limite_agglomeration",
                                       "codes": [code], "regle": "RF-SV-EB.POSITION", "ensembles": [e["id"]]})
        for k, p in enumerate(self.cpl.get("panneaux") or []):
            rid = self._route_de(p.get("troncon"))
            s = float(p["a"])
            sens = 1 if str(p.get("sens", "avant")) in ("avant", "→", "1") else -1
            agglo = p.get("agglomeration")
            ctx = dict(self.ctx_route(rid))
            if agglo is not None:
                ctx["agglo"] = str(agglo).lower() in ("oui", "true", "1")
            if p.get("vitesse") is not None:
                ctx["v"] = float(p["vitesse"])
            codes = [str(c) for c in p.get("codes") or [p.get("code")]]
            composes = {}
            for c in codes:
                if c in ("M1", "M9z", "M5"):
                    composes[c] = self.plaque_composee(c, f"{c}_{rid}_{k}", 1.0 if self.gamme(ctx) != "petite" else 0.7,
                                                       0.3, {"type": "panonceau", "texte": str(p.get("texte") or "")},
                                                       ["RF-SV-PAN.USAGES", "RF-SV-DIM.PANONCEAUX"])
            regs = [str(r) for r in (p.get("regles") or [])]
            e = self._ensemble_simple(f"E-{p.get('id') or ('P' + str(k + 1))}.{rid}", codes, rid, s, sens, ctx, regs,
                                      "description:complement.panneaux", cote=str(p.get("cote", "droite")),
                                      fen=(-float(p.get("tolerance", 6.0)), float(p.get("tolerance", 6.0))), composes=composes,
                                      note=p.get("note"))
            if p.get("exigence"):
                self.exigences.append({"id": f"X-{e['id'][2:]}", "route": rid, "type": str(p["exigence"]),
                                       "codes": codes, "regle": regs[0] if regs else "", "ensembles": [e["id"]]})

    def _route_de(self, troncon):
        if troncon is None:
            return sorted(self.refs)[0]
        for rid, r in self.routes.items():
            if (r.get("nom") == troncon) or rid == troncon or (r.get("id") == troncon):
                return rid
        for rid in sorted(self.routes):
            if troncon in (self.routes[rid].get("prov") or {}).get("*", {}).get("src", ""):
                return rid
        # tronçons : ordre de la description
        noms = sorted(self.refs)
        return noms[0]

    # ---------------------------------------------------------------- 7. autoroutes
    def autoroutes(self):
        """Autoroutes : B14 de rappel + répétition à gauche (RF-SV-B14.EMPLOI, RF-SV-GEN.REPETITION_GAUCHE_2X2) ;
        bretelle d'entrée : AB3a + M9c au droit de l'extrémité de la ligne continue suivant le convergent
        (L6-SV-AB3A.INSERTION) ; sortie : D31d en signalisation avancée sur potence au point où la voie de sortie
        atteint 1,50 m (L6-SV-D30.POSITION, L6-SV-ECHANGEUR.SUPPORTS), D41a à 30 s (L6-SV-D40.POSITION)."""
        bifs = [c for c in self.m.get("carrefours") or [] if c.get("type") == "bifurcation"]
        aut = [rid for rid, r in sorted(self.routes.items()) if r.get("categorie") == "autoroute" and rid in self.refs]
        if not aut:
            return
        sortie = self.cpl.get("sortie") or {}
        for rid in aut:
            ref = self.refs[rid]
            ctx = self.ctx_route(rid)
            g = self.gamme(ctx)
            entree = any(b.get("regime") == "cedez" for c in bifs for b in c["branches"])
            s_entree = None
            for c in bifs:
                for b in c["branches"]:
                    if b.get("regime") == "cedez":
                        s_entree = self._s_jonction(c)
            for sens in (1, -1):
                if self.voies(rid, ref.L / 2, "avant" if sens > 0 else "arriere") == 0:
                    continue
                # rappel B14 : après l'entrée (+ 100 m [G]) si elle existe dans ce sens, sinon au premier quart
                # (intégration de l'étape 4 : abscisse dite par le complément, clé rappel_b14 {avant, arriere}, pour
                # une scène où le premier quart tombe sur un ouvrage ou dans une sortie ; sans la clé : inchangé)
                rb = self.cpl.get("rappel_b14") or {}
                if rb.get("avant" if sens > 0 else "arriere") is not None:
                    s = float(rb["avant" if sens > 0 else "arriere"])
                elif entree and s_entree is not None and sens > 0:
                    s = s_entree + 250.0
                else:
                    s = ref.L * (0.25 if sens > 0 else 0.75)
                if not (20.0 <= s <= ref.L - 20.0):
                    continue
                vt = int(ctx["v"])
                code = f"B14_{vt}"
                tag = "av" if sens > 0 else "ar"
                rap = self.plaque_composee("M9z", f"M9z_rappel_{rid}_{tag}", 1.25 if g == "tres_grande" else 1.0, 0.35,
                                           {"type": "panonceau", "texte": "RAPPEL"}, ["RF-SV-B14.EMPLOI", "RF-SV-PAN.USAGES"])
                for cote in ("droite", "gauche"):
                    el = [rap, self.plaque(code, g, ["RF-SV-B14.EMPLOI"])]
                    e = self.ajouter({"id": f"E-B14.{rid}.{tag}.{cote}", "famille": "panneau",
                                      "source": "plan:IISR4 art. 63 (rappel) ; IISR1 art. 8 c (répétition à gauche)",
                                      "regles": ["RF-SV-B14.EMPLOI", "RF-SV-GEN.REPETITION_GAUCHE_2X2", "DEF-025",
                                                 "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE", "RF-SV-DIM.CHOIX_GAMME.GENERATEUR"],
                                      "ancrage": self.anc_route(rid, s, sens, cote, (-15.0, 15.0),
                                                                surface="tpc" if cote == "gauche" else "auto"),
                                      "support": {"type": "poteau", "diametre_m": 0.076},
                                      "bas": _r(V("DEF-025", "hauteur_rase_campagne")), "regle_hauteur": "DEF-025",
                                      "elements": el, "applicabilite": {"route": rid, "sens": tag}, "exclusif": False})
                    if cote == "gauche":
                        self.exigences.append({"id": f"X-B14g.{rid}.{tag}", "route": rid, "type": "repetition_gauche",
                                               "codes": [code], "regle": "RF-SV-GEN.REPETITION_GAUCHE_2X2",
                                               "ensembles": [e["id"], e["id"].replace(".gauche", ".droite")]})
        for c in bifs:
            for b in c["branches"]:
                if b.get("regime") == "cedez":
                    self._insertion(c, b)
                if b.get("regime") == "sortie_seule":
                    self._sortie(c, b, sortie)

    def _s_jonction(self, c):
        if self.musoirs:
            mu = self.musoirs["musoirs"]
            if mu.get("sJ"):
                return float(mu["sJ"][0])
        return None

    def _insertion(self, c, b):
        rid = b["route"]
        ref = self.refs.get(rid)
        if ref is None:
            return
        ctx = self.ctx_route(rid)
        # extrémité de la ligne continue suivant le convergent : fin du musoir (point à 5 m, s5) ramenée sur la bretelle
        s = ref.L - 2.0
        e = self.ajouter({"id": f"E-AB3a.insertion.{rid}", "famille": "panneau", "source": "plan:IISR3 art. 43-1 E",
                          "regles": ["L6-SV-AB3A.INSERTION", "RF-SV-INSERTION.AB3A", "RF-SV-AB3A.POSITION", "DEF-025",
                                     "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE"],
                          "ancrage": self.anc_route(rid, s, 1, "droite", (-20.0, 2.0)),
                          "support": {"type": "poteau", "diametre_m": 0.076}, "bas": _r(V("DEF-025", "hauteur_rase_campagne")),
                          "regle_hauteur": "DEF-025", "elements": [self.plaque("AB3a", "grande", ["RF-SV-AB3A.POSITION"])],
                          "applicabilite": {"carrefour": c["id"], "branche": b["id"]}, "exclusif": True})
        self.exigences.append({"id": f"X-AB3a.insertion.{rid}", "carrefour": c["id"], "branche": b["id"],
                               "type": "regime", "regime": "cedez", "codes": ["AB3a"], "regle": "L6-SV-AB3A.INSERTION",
                               "ensembles": [e["id"]]})

    def _sortie(self, c, b, sortie):
        """Sortie : point où la voie de décélération atteint 1,50 m (loi de largeur de la section d'ouverture)."""
        prin = [x for x in c["branches"] if x is not b][0]
        rid = prin["route"]
        ref = self.refs[rid]
        ctx = self.ctx_route(rid)
        s15 = self._s_largeur(rid, "voie_deceleration", V("L6-SV-D30.POSITION", "largeur_voie_de_sortie_m"))
        if s15 is None:
            self.non_poses.append({"code": "D31d", "route": rid, "motif": "voie de décélération introuvable dans le modèle"})
            return
        num = str(sortie.get("numero", "")) or None
        dests = [str(d) for d in (sortie.get("destinations") or [])] or [self.destination("sortie", 0)[0]]
        # portique de sortie (L6-SV-ECHANGEUR.SUPPORTS : signalisation avancée sur portique ou potence ; confirmation de
        # filante sur portique) : D31d au-dessus de la voie de sortie, D62c au-dessus des voies de filante ; bas du
        # panneau à la cote du catalogue (5,50 m), au-dessus du gabarit d'autoroute (L6-SV-SURPLOMB.GABARIT : 5,35 m)
        bas_min = V("L6-SV-SURPLOMB.GABARIT", "bas_min_m")["autoroute"]
        cat_p = catalogue()["portique_signalisation_L1600"]["dimensions"]
        bas = max(bas_min, float(cat_p["bas_panneau_m"]))
        filante = [str(d) for d in (sortie.get("filante") or [])] or [self.destination("filante", 4)[0]]
        d31 = self.plaque_composee("D31d", f"D31d_{rid}", 3.0, 2.2,
                                   {"type": "D31", "numero": num, "destinations": dests, "fleche": "sortie"},
                                   ["L6-SV-D30.POSITION", "RF-SV-DIM.D_E_EB"])
        d31["voie"] = "voie_deceleration"
        d62 = self.plaque_composee("D62c", f"D62c_{rid}", 3.5, 1.6,
                                   {"type": "D62", "texte": filante[0],
                                    "voies": sum(1 for b in (self.profil_a(rid, s15) or {}).get("bandes") or []
                                                 if b.get("type") == "voie_circulation" and b.get("sens") == "avant")},
                                   ["L6-SV-ECHANGEUR.SUPPORTS", "RF-SV-DIM.D_E_EB"])
        d62["voie"] = "voie_circulation"
        self.ajouter({"id": f"E-portique.{rid}", "famille": "portique", "source": "plan:IISR5 art. 83-2, 84 A 3",
                      "regles": ["L6-SV-D30.POSITION", "L6-SV-ECHANGEUR.SUPPORTS", "L6-SV-SURPLOMB.GABARIT",
                                 "RF-SV-GEN.HAUTEUR.SURPLOMB", "RF-SV-B12.HAUTEUR", "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE"],
                      "ancrage": dict(self.anc_route(rid, s15, 1, "droite", (-5.0, 5.0)), surface="accotement"),
                      "support": {"type": "portique", "asset": "portique_signalisation_L1600", "diametre_m": 0.8,
                                  "portee_m": float(cat_p["portee_m"])},
                      "bas": _r(bas), "regle_hauteur": "L6-SV-SURPLOMB.GABARIT (catalogue : bas 5,50 m)",
                      "elements": [d31, d62], "applicabilite": {"carrefour": c["id"], "voie": "voie_deceleration"},
                      "exclusif": False})
        d41 = self._vitesse_ms(ctx) * V("L6-SV-D40.POSITION", "D41_s_avant_signalisation_avancee")
        s41 = s15 - d41
        if s41 < 5.0:
            self.non_poses.append({"code": "D41a", "route": rid, "regle": "L6-SV-D40.POSITION",
                                   "motif": f"présignalisation à {d41:.0f} m en amont du D31d (s = {s41:.0f}) : hors de la "
                                            f"scène (tronçon de {ref.L:.0f} m) — non posée"})
        else:
            el = [self.plaque_composee("D41a", f"D41a_{rid}", 3.0, 2.2,
                                       {"type": "D41", "numero": num, "destinations": dests, "distance": int(round(d41 / 100.0) * 100)},
                                       ["L6-SV-D40.POSITION", "RF-SV-DIM.D_E_EB"])]
            self.ajouter({"id": f"E-D41a.{rid}", "famille": "panneau", "source": "plan:IISR5 art. 83-4, 84 A 3",
                          "regles": ["L6-SV-D40.POSITION", "L6-SV-ECHANGEUR.SUPPORTS", "RF-SV-GEN.DISTANCE_RIVE.RASE_CAMPAGNE"],
                          "ancrage": self.anc_route(rid, s41, 1, "droite", (-20.0, 20.0)),
                          "support": {"type": "poteau", "diametre_m": 0.114, "double": True},
                          "bas": _r(V("DEF-025", "hauteur_rase_campagne")), "regle_hauteur": "L6-SV-ECHANGEUR.SUPPORTS",
                          "elements": el, "applicabilite": {"carrefour": c["id"]}, "exclusif": False})
        if not V("L6-SV-D50.EMPLOI"):
            pass
        self.non_poses.append({"code": "D51c", "route": rid, "regle": "L6-SV-D50.EMPLOI",
                               "motif": "avertissement réservé aux échangeurs numérotés espacés d'au moins 5 km : "
                                        "espacement non décrit — non posé"})

    def _s_largeur(self, rid, type_bande, w):
        """Abscisse où une bande de type donné atteint la largeur w (lois de largeur linéaires des sections)."""
        r = self.routes[rid]
        for sec in r.get("sections") or []:
            p = self.profils.get(sec["profil"]) or {}
            for b in p.get("bandes") or []:
                if b.get("type") != type_bande:
                    continue
                lg = b.get("largeur")
                if isinstance(lg, dict) and lg.get("type") in ("points", "lineaire"):
                    pts = lg.get("points") or []
                    for (s0, w0), (s1, w1) in zip(pts, pts[1:]):
                        if (w0 - w) * (w1 - w) <= 0 and w1 != w0:
                            return s0 + (w - w0) / (w1 - w0) * (s1 - s0)
        return None

    # ---------------------------------------------------------------- 8. exigences des régimes
    def exigences_regimes(self):
        """P14-1 : panneaux de chaque branche à régime ; P14-2 : jamais d'AB4 sur une branche à feux ou « à vérifier »."""
        for x in self.branches():
            c = x["c"]
            rg = x["regime"]
            ctx = self.ctx_route(x["route"])
            ids = [e["id"] for e in self.ensembles if e["applicabilite"].get("branche") == x["id"]
                   and e["applicabilite"].get("carrefour", c["id"]) == c["id"]]
            req, interdits, regle = [], [], ""
            if c.get("type") in ("giratoire", "mini_giratoire") or rg == "entree_giratoire":
                req = ["AB25"]
                regle = "RF-SV-AB25.EMPLOI"
                if c.get("type") == "giratoire":
                    req.append("B21-1")
                if not ctx["agglo"]:
                    req.append("AB3a")
            elif rg == "cedez":
                req, regle = ["AB3a"], "RF-SV-AB3A.POSITION"
            elif rg == "stop":
                req, regle = ["AB4"], "RF-SV-AB4.POSITION"
            elif rg == "stop_a_verifier":
                interdits, regle = ["AB4"], "ARB-19"
            elif rg == "feux":
                req, interdits, regle = ["R11v"], ["AB4"], "RF-FEU.R11.NOMBRE_ET_COTES"
            elif rg == "prioritaire" and not ctx["agglo"] and c.get("type") != "bifurcation":
                req, regle = ["AB2"], "RF-SV-AB2.EMPLOI"
            else:
                continue
            self.exigences.append({"id": f"X-{c['id'][2:]}.{x['nom']}", "carrefour": c["id"], "branche": x["id"],
                                   "type": "regime", "regime": rg, "codes": req, "interdits": interdits, "regle": regle,
                                   "ensembles": ids})

    # ---------------------------------------------------------------- 9. exclusions (abaissés)
    def exclusions(self):
        """Abaissés et bateaux des bordures fabriquées (l2/entites.json, l3/carrefours.json) : aucun support dessus
        (PLAN_GENERATEUR L6 ; RF-MA-TRO-001). Polylignes de bordure de l'intervalle ; l'HDA en fait des bandes de 3 m
        vers le côté haut (gauche de la file)."""
        out = []
        sources = []
        f2 = self.dossier / "l2" / "entites.json"
        if f2.exists():
            d = json.loads(f2.read_text(encoding="utf-8"))
            sources += d if isinstance(d, list) else d.get("entites", [])
        if self.l3:
            sources += self.l3.get("entites") or []
        f5 = self.dossier / "l5" / "giratoires.json"
        if f5.exists():
            g = json.loads(f5.read_text(encoding="utf-8"))
            sources += g.get("entites") or []
        for ent in sources:
            iv = [i for i in ent.get("intervalles") or [] if i.get("role") == "bateau"]
            if not iv:
                continue
            xy = ent.get("xy") or [p[:2] for p in ent.get("xyz") or []]
            if len(xy) < 2:
                continue
            ss = ent.get("niv_s")
            if not ss or len(ss) != len(xy):
                ss = [0.0]
                for a, b in zip(xy, xy[1:]):
                    ss.append(ss[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
            # fusion des intervalles contigus
            iv = sorted(iv, key=lambda i: i["s0"])
            blocs = []
            for i in iv:
                if blocs and i["s0"] <= blocs[-1][1] + 1e-3:
                    blocs[-1][1] = max(blocs[-1][1], i["s1"])
                else:
                    blocs.append([i["s0"], i["s1"]])
            for k, (s0, s1) in enumerate(blocs):
                pts = []
                for j in range(len(xy)):
                    if s0 - 1e-6 <= ss[j] <= s1 + 1e-6:
                        pts.append(xy[j])
                # bornes interpolées
                def interp(s):
                    for j in range(len(ss) - 1):
                        if ss[j] <= s <= ss[j + 1] and ss[j + 1] > ss[j]:
                            a = (s - ss[j]) / (ss[j + 1] - ss[j])
                            return [xy[j][0] + a * (xy[j + 1][0] - xy[j][0]), xy[j][1] + a * (xy[j + 1][1] - xy[j][1])]
                    return None
                a0, a1 = interp(s0), interp(s1)
                pts = ([a0] if a0 else []) + pts + ([a1] if a1 else [])
                if len(pts) >= 2:
                    out.append({"id": f"{ent.get('id')}.ab{k}", "polyligne": [[_r(p[0]), _r(p[1])] for p in pts],
                                "profondeur": 1.2, "debord": 0.3,
                                "motif": "abaissé (bateau) et zone d'attente : 1,20 m de part et d'autre de la face [G] "
                                         "(BEV 0,50 + 0,5875 m, DEF-031) ; rampants exclus par la vue (RF-MA-TRO-015)"})
        return out

    # ---------------------------------------------------------------- tout
    def construire(self):
        self.depuis_modele()
        self.balises_j5()
        self.directions()
        self.voies_affectees()
        self.sections()
        self.itineraire()
        self.autoroutes()
        self.exigences_regimes()
        ex = self.exclusions()
        ids = [e["id"] for e in self.ensembles]
        doublons = sorted({i for i in ids if ids.count(i) > 1})
        if doublons:
            raise SystemExit(f"{self.scene} : identifiants d'ensemble en double {doublons}")
        self.ensembles.sort(key=lambda e: e["id"])
        ctx0 = self.ctx_route(sorted(self.refs)[0])
        return {"schema": SCHEMA, "scene": self.scene,
                "modele": {"fichier": str((self.dossier / "modele_voie.json").relative_to(DEPOT)).replace("\\", "/"),
                           "sha256": sha256(self.dossier / "modele_voie.json")},
                "complement": ({"fichier": str(self.complement_fichier.relative_to(DEPOT)).replace("\\", "/"),
                                "sha256": sha256(self.complement_fichier)} if self.complement_fichier else None),
                "regles_base": regles.empreinte()["sha256"], "regles_l6": sha256(REGLES_L6),
                "origine_l93": self.o, "contexte": ctx0,
                "destinations_generiques": self.n_generiques,
                "ensembles": self.ensembles, "exigences": sorted(self.exigences, key=lambda x: x["id"]),
                "non_poses": self.non_poses, "exclusions": ex, "faces": sorted(self.faces, key=lambda f: f["fichier"]),
                "avertissements": self.avertissements}


def construire_plan(dossier, complement=None):
    return Plan(dossier, complement).construire()


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dossier")
    ap.add_argument("--complement")
    ap.add_argument("--sortie")
    a = ap.parse_args()
    p = construire_plan(a.dossier, a.complement)
    f = Path(a.sortie) if a.sortie else Path(a.dossier) / "l6" / "plan_signalisation.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(p, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{p['scene']} : {len(p['ensembles'])} ensembles, {len(p['exigences'])} exigences, {len(p['non_poses'])} non posés,"
          f" {len(p['faces'])} faces composées -> {f}")


if __name__ == "__main__":
    main()
