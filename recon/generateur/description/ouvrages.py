# -*- coding: utf-8 -*-
"""Compilateur des ouvrages d'art d'une description (lot « ouvrages » : L8 du plan, étape E07 de la chaîne).

Clé racine `ouvrages:` de la description simple (FORMAT_DESCRIPTION.md § 17). Un ouvrage porte un tronçon (`porte`)
au-dessus d'un tronçon franchi (`franchit: <id>`) ou d'un talweg (`franchit: {talweg: {...}}`) ; le compilateur en tire,
sans rien inventer (valeur dite, sinon règle citée, sinon arrêt « à dire ») :

- la position (croisement des lignes de référence, abscisse et biais), les appuis (travées dites), les abouts et les
  joints (OA-JNT-001, OA-JNT-002, OA-ESP-001 ; aucun joint sur un portique ou un cadre, OA-PIPO-001) ;
- l'épaisseur du tablier par l'élancement du type (RF-GV-PON-015 ; OA-ELA-001, OA-ELA-002 ; caisson : épaisseur dite,
  contrôlée contre les observations OA-CAI-001), le balancement des travées (RF-GV-PON-015) ;
- le gabarit sous l'ouvrage (RF-GV-PON-012 : 4,30 m, 4,75 m sous une autoroute ou une voie rapide, + revanche 0,10 m,
  DEF-033) et le PROFIL EN LONG de la route portée (raccordements paraboliques saillant / rentrant et déclivité des
  tables OA-PEL-001 / OA-PEL-002) qui le garantit, avec l'espace libre au-dessus du terrain sous le tablier ;
- la hauteur de chute Hc et la hauteur des garde-corps (DEF-033, RF-GV-PON-007 : bande GC97 pour les piétons, 1,20 m le
  long d'une piste cyclable) ou la barrière BN4 (OA-BN4-001) ;
- les talus 3/2 (OA-TAL-001), les dalles de transition (OA-DDT-001), le revêtement sur tablier (OA-REV-001, choix [G]).

Sorties dans le modèle : `ouvrages[]` (contrat du schéma + `construction`, ajout rétrocompatible du lot), et sur les
routes : `profil_long` (source « ouvrage », z NGF), `layer` (OSM : 1 pour la route portée, 0 pour la route franchie),
`ouvrages` ; contrôles dans compilation.json (troncons[route portée].controles), bloquants s'ils sont hors plage.
Les valeurs des règles complémentaires (assets/specs/route/regles_ouvrages_fr.json) sont citées par une provenance
« catalogue:regles_ouvrages_fr.json#OA-… » (jamais dans un champ « regle » : contrôle C11 du validateur).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ICI = Path(__file__).resolve().parent
DEPOT = ICI.parents[2]
FICHIER_OA = DEPOT / "assets" / "specs" / "route" / "regles_ouvrages_fr.json"

import regles  # noqa: E402
from commun import prov as P  # noqa: E402
from description import vocabulaire as V  # noqa: E402

VERSION = "description/ouvrages.py 1.0 (lot ouvrages)"
CLES_OUVRAGE = {"id", "nom", "type", "porte", "franchit", "centre", "travees", "tablier", "epaisseur", "piles", "culees",
                "piedroits", "murs_aile", "corniche", "appareils_appui", "equipements", "profil_en_long",
                "dalles_transition", "revetement", "biais"}
TYPES = {"passage_superieur": ("pont_route", "PS"), "ps": ("pont_route", "PS"), "pont": ("pont_route", "pont"),
         "pont_route": ("pont_route", "pont"), "passage_inferieur": ("passage_inferieur", "PI"),
         "pi": ("passage_inferieur", "PI"), "viaduc": ("viaduc", "viaduc")}
# familles de tablier -> (structure du schéma, clé de RF-GV-PON-015 ou règle complémentaire)
TABLIERS = {"PSIDA": "dalle", "PSIDP": "dalle", "PIPO": "portique", "PICF": "cadre", "PRAD": "poutre", "VIPP": "poutre",
            "CAISSON": "caisson"}
CIRCULABLES = {"voie_circulation", "voie_bus", "bande_arret_urgence", "bande_derasee", "accotement_revetu",
               "voie_tourne_gauche", "voie_tourne_droite", "voie_stockage", "bande_cyclable", "chaussee_partagee",
               "zone_neutralisee", "voie_insertion", "voie_acceleration", "voie_deceleration"}
CATEGORIES_GRAND_GABARIT = ("autoroute", "voie_express", "bretelle")
REVANCHE_TERRAIN = 0.10           # espace libre minimal entre l'intrados et le terrain naturel (revanche, RF-GV-PON-012)
PAS_PROFIL = 0.5                  # pas d'échantillonnage du profil en long écrit dans le modèle (m)


MARGE_TERRAIN_NIVEAU = 0.65       # [G] terrain naturel sous le plus bas bord des routes à niveau (intégration de l'étape 4) :
                                  # au moins le raccord adouci de rg::ouvrages (0,60 m) + 2 cm, pour que le congé du pied
                                  # des talus ne remonte pas au bord des plates-formes


class ErreurOuvrage(ValueError):
    pass


def z_bords_routes_a_niveau(d: dict, modele: dict, par_id: dict):
    """Intégration de l'étape 4 : None si toutes les routes du modèle sont portées ou franchies par un ouvrage (scènes
    du lot « ouvrages », inchangées) ; sinon le z relatif le plus bas des bords extérieurs de toutes les routes (début,
    milieu et fin de chaque section, lois de largeur comprises)."""
    liste = d.get("ouvrages") or []
    if isinstance(liste, dict):
        liste = list(liste.values())
    lies = set()
    for o in liste:
        if not isinstance(o, dict):
            continue
        for cle in ("porte", "franchit"):
            v = o.get(cle)
            if isinstance(v, list) and len(v) == 1:
                v = v[0]
            if isinstance(v, (str, int)) and str(v) in par_id:
                lies.add(par_id[str(v)]["rid"])
    if all(r["id"] in lies for r in modele["routes"]):
        return None
    zmin = None
    for r in modele["routes"]:
        for sec in r["sections"]:
            prof = next(p for p in modele["profils"] if p["id"] == sec["profil"])
            for s in (sec["s0"], 0.5 * (sec["s0"] + sec["s1"]), sec["s1"]):
                c = coupe(prof, s)
                z = min(c[0]["z_g"], c[-1]["z_d"])
                zmin = z if zmin is None else min(zmin, z)
    return zmin


def _oa():
    d = json.loads(FICHIER_OA.read_text(encoding="utf-8"))
    return {r["id"]: r for r in d["regles"]}


def oa(ident: str, note: str | None = None, conf: str | None = None) -> dict:
    """Provenance d'une valeur tirée d'une règle complémentaire du lot (genre « catalogue » du validateur)."""
    r = _oa()[ident]
    s = r["source"]
    txt = f"{s['doc']} p. {s['page']}" + (f" ; {note}" if note else "")
    return P.entree(f"catalogue:regles_ouvrages_fr.json#{ident}", None, conf or r.get("confiance", "moyenne"), txt)


def oa_val(ident: str, *chemin):
    v = _oa()[ident]["valeurs"]
    for c in chemin:
        v = v[c]
    return v


def _r(x, n=4):
    v = round(float(x), n)
    return 0.0 if v == 0 else v


# ------------------------------------------------------------------------------------------------ coupe en travers
def largeur_bande(b: dict, s: float) -> float:
    w = b["largeur"]
    if isinstance(w, (int, float)):
        return float(w)
    if isinstance(w, dict) and w.get("points"):          # loi par points (s, w) : linéaire
        pts = w["points"]
        if s <= pts[0][0]:
            return float(pts[0][1])
        for (s0, w0), (s1, w1) in zip(pts, pts[1:]):
            if s <= s1:
                return float(w0 + (w1 - w0) * (s - s0) / max(s1 - s0, 1e-9))
        return float(pts[-1][1])
    raise ErreurOuvrage(f"largeur de bande non lue : {w}")


def coupe(profil: dict, s: float) -> list[dict]:
    """Coupe en travers d'un profil du modèle à l'abscisse s : une entrée par limite (t, z relatifs à la référence) et
    par bande, de gauche à droite. Modèle de Z de rg_niveau.h simplifié (contrôles du compilateur) : bandes de chaussée
    ancrées à z = 0 sur la référence, dévers de chaque bande ; saut de la vue d'une bordure (côté haut) − 4 mm
    (TQ-SOL-013 (6)) ; trottoir au dévers de sa bande."""
    bandes, lims = profil["bandes"], profil["limites"]
    n = len(bandes)
    ref = profil.get("reference") or {}
    r = int(ref.get("limite", 0))
    w = [largeur_bande(b, s) for b in bandes]
    t = [0.0] * (n + 1)
    t[r] = -float(ref.get("decalage_m", 0.0))         # README_RG § 4 : t_r = − reference.decalage_m
    for i in range(r - 1, -1, -1):
        t[i] = t[i + 1] + w[i]
    for i in range(r + 1, n + 1):
        t[i] = t[i - 1] - w[i - 1]
    r = min(range(n + 1), key=lambda i: (abs(t[i]), i))   # ancrage z = 0 à la limite la plus proche de t = 0
    # z aux deux bords de chaque bande (zg, zd) en partant de la référence
    zg, zd = [0.0] * n, [0.0] * n

    def saut(lim, vers):                    # marche d'une bordure franchie en allant vers « gauche » ou « droite »
        bo = lim.get("bordure")
        if not bo or "bordure" not in (lim.get("nature") or []):
            return 0.0
        h = float(bo.get("vue_m", 0.0)) - 0.004
        return h if bo.get("cote_haut") == vers else -h

    z = 0.0
    for i in range(r, n):                   # vers la droite depuis la limite de référence
        if i > r:
            z += saut(lims[i], "droite")
        dev = float((bandes[i].get("niveau") or {}).get("devers_pct", 0.0))
        zg[i] = z
        z -= dev / 100.0 * w[i]
        zd[i] = z
    z = 0.0
    for i in range(r - 1, -1, -1):          # vers la gauche
        if i + 1 < r:
            z += saut(lims[i + 1], "gauche")
        dev = float((bandes[i].get("niveau") or {}).get("devers_pct", 0.0))
        zd[i] = z
        z += dev / 100.0 * w[i]
        zg[i] = z
    out = []
    for i, b in enumerate(bandes):
        out.append({"bande": b.get("id"), "type": b.get("type"), "t_g": t[i], "t_d": t[i + 1], "z_g": zg[i],
                    "z_d": zd[i], "largeur": w[i], "niveau": (b.get("niveau") or {}).get("reference")})
    return out


def coupe_route(modele: dict, route: dict, s: float) -> list[dict]:
    for sec in route["sections"]:
        if sec["s0"] - 1e-9 <= s <= sec["s1"] + 1e-9:
            prof = next(p for p in modele["profils"] if p["id"] == sec["profil"])
            return coupe(prof, s)
    raise ErreurOuvrage(f"{route['id']} : aucune section en s = {s}")


# ------------------------------------------------------------------------------------------------ géométrie en plan
def _poly(route):
    return [tuple(p[:2]) for p in route["ligne_reference"]["geometrie"]]


def _abscisses(pts):
    s = [0.0]
    for a, b in zip(pts, pts[1:]):
        s.append(s[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    return s


def croisement(ra: dict, rb: dict):
    """(s sur ra, s sur rb, point, angle entre les tangentes en degrés) du croisement des lignes de référence."""
    pa, pb = _poly(ra), _poly(rb)
    sa, sb = _abscisses(pa), _abscisses(pb)
    for i, (a0, a1) in enumerate(zip(pa, pa[1:])):
        for j, (b0, b1) in enumerate(zip(pb, pb[1:])):
            dax, day = a1[0] - a0[0], a1[1] - a0[1]
            dbx, dby = b1[0] - b0[0], b1[1] - b0[1]
            den = dax * dby - day * dbx
            if abs(den) < 1e-12:
                continue
            u = ((b0[0] - a0[0]) * dby - (b0[1] - a0[1]) * dbx) / den
            v = ((b0[0] - a0[0]) * day - (b0[1] - a0[1]) * dax) / den
            if -1e-9 <= u <= 1 + 1e-9 and -1e-9 <= v <= 1 + 1e-9:
                la, lb = math.hypot(dax, day), math.hypot(dbx, dby)
                ang = math.degrees(math.acos(max(-1.0, min(1.0, abs(dax * dbx + day * dby) / (la * lb)))))
                return (sa[i] + u * la, sb[j] + v * lb, (a0[0] + u * dax, a0[1] + u * day), ang)
    return None


# ------------------------------------------------------------------------------------------------ profil en long
class ProfilEnLong:
    """Profil symétrique autour de s_c : palier à z0 jusqu'à s_c − demi, rentrant de rayon Rr, rampe g, saillant de rayon
    Rs centré en s_c (sommet à z_c), puis l'inverse. Plat si z_c <= z0."""

    def __init__(self, s_c, z_c, z0, g, Rs, Rr):
        self.s_c, self.z_c, self.z0, self.g, self.Rs, self.Rr = s_c, z_c, z0, g, Rs, Rr
        H = z_c - z0
        self.plat = H <= 1e-9
        if self.plat:
            self.Ls = self.Lt = self.Lr = 0.0
            return
        hs, hr = g * g * Rs / 2.0, g * g * Rr / 2.0
        if hs + hr > H + 1e-12:                    # sans rampe : g réduit
            g = math.sqrt(2.0 * H / (Rs + Rr))
            self.g = g
            hs, hr = g * g * Rs / 2.0, g * g * Rr / 2.0
        self.Ls, self.Lr = g * Rs, g * Rr
        self.Lt = max(0.0, (H - hs - hr) / g)
        self.demi = self.Ls + self.Lt + self.Lr

    def z(self, s):
        if self.plat:
            return self.z0
        d = abs(s - self.s_c)
        if d <= self.Ls:
            return self.z_c - d * d / (2.0 * self.Rs)
        z1 = self.z_c - self.Ls * self.Ls / (2.0 * self.Rs)
        if d <= self.Ls + self.Lt:
            return z1 - self.g * (d - self.Ls)
        z2 = z1 - self.g * self.Lt
        if d <= self.demi:
            u = self.demi - d
            return self.z0 + u * u / (2.0 * self.Rr)
        return self.z0

    def elements(self):
        if self.plat:
            return [{"type": "palier", "z": _r(self.z0)}]
        sc = self.s_c
        e = [{"type": "palier", "s1": _r(sc - self.demi), "z": _r(self.z0)},
             {"type": "rentrant", "s0": _r(sc - self.demi), "s1": _r(sc - self.demi + self.Lr), "rayon_m": _r(self.Rr, 1)},
             {"type": "rampe", "s0": _r(sc - self.Ls - self.Lt), "s1": _r(sc - self.Ls), "declivite_pct": _r(100 * self.g, 3)},
             {"type": "saillant", "s0": _r(sc - self.Ls), "s1": _r(sc + self.Ls), "rayon_m": _r(self.Rs, 1),
              "sommet_z": _r(self.z_c)},
             {"type": "pente", "s0": _r(sc + self.Ls), "s1": _r(sc + self.Ls + self.Lt), "declivite_pct": _r(-100 * self.g, 3)},
             {"type": "rentrant", "s0": _r(sc + self.demi - self.Lr), "s1": _r(sc + self.demi), "rayon_m": _r(self.Rr, 1)},
             {"type": "palier", "s0": _r(sc + self.demi), "z": _r(self.z0)}]
        return e


def classe_pel(o: dict, chemin: str):
    """(classe, déclivité max %, Rs, Rr, provenances) du profil en long dit (`profil_en_long: {classe: U60 | U80_A80 |
    A100 | R1 | R2 | artere_interurbaine_110}` et/ou valeurs dites)."""
    pel = o.get("profil_en_long") or {}
    if not isinstance(pel, dict):
        raise ErreurOuvrage(f"{chemin}.profil_en_long : dictionnaire attendu")
    cl = pel.get("classe")
    tables = {"U60": ("OA-PEL-002", "U60"), "U80_A80": ("OA-PEL-002", "U80_A80"), "A100": ("OA-PEL-002", "A100"),
              "R1": ("OA-PEL-001", "R1"), "R2": ("OA-PEL-001", "R2"),
              "ARTERE_INTERURBAINE_110": ("OA-PEL-001", "artere_interurbaine_110")}
    vals, prov = {}, {}
    if cl is not None:
        k = str(cl).upper().replace(" ", "_").replace("/", "_")
        if k not in tables:
            raise ErreurOuvrage(f"{chemin}.profil_en_long.classe : {cl} inconnue ({', '.join(tables)})")
        rid, cle = tables[k]
        t = oa_val(rid, cle)
        vals = {"pente": t["declivite_max_pct"], "rs": t["rayon_saillant_min_m"], "rr": t["rayon_rentrant_min_m"]}
        prov = {c: oa(rid, note=f"classe {cle}, valeur limite") for c in vals}
    for cle_d, cle in (("pente_max", "pente"), ("rayon_saillant", "rs"), ("rayon_rentrant", "rr")):
        if pel.get(cle_d) is not None:
            vals[cle] = V.nombre(pel[cle_d], f"{chemin}.profil_en_long.{cle_d}")
            prov[cle] = P.description(f"{chemin}.profil_en_long.{cle_d}")
    manque = [c for c in ("pente", "rs", "rr") if c not in vals]
    if manque:
        raise ErreurOuvrage(f"{chemin}.profil_en_long : à dire ({', '.join(manque)}) — « classe: U60 | U80_A80 | A100 | "
                            "R1 | R2 | artere_interurbaine_110 » (OA-PEL-001, OA-PEL-002) ou valeurs dites")
    return cl, vals["pente"], vals["rs"], vals["rr"], prov


# ------------------------------------------------------------------------------------------------ lecture
def _dict(v, chemin):
    if v is None:
        return {}
    if not isinstance(v, dict):
        raise ErreurOuvrage(f"{chemin} : dictionnaire attendu")
    return v


def _num(d, cle, chemin, obligatoire=True, defaut=None):
    if d.get(cle) is None:
        if obligatoire:
            raise ErreurOuvrage(f"{chemin}.{cle} : à dire (aucune règle ne fixe cette cote dans DocRoute)")
        return defaut
    return V.nombre(d[cle], f"{chemin}.{cle}")


def epaisseur_regle(fam: str, enc: bool, travees: list[float], continu: bool):
    """(épaisseur, élancement texte, provenance, domaine (min, max)) de la famille de tablier."""
    n = len(travees)
    l = max(travees)
    if fam == "PSIDA":
        k, txt = ((1 / 20, "l/20") if n == 1 else (1 / 26, "l/26") if n == 2 else (1 / 28, "l/28"))
        cle = "PSIDA_iso" if n == 1 else "PSIDA_2_travees" if n == 2 else "PSIDA_3_travees_plus"
        dom = (7.0, 15.0) if n <= 2 else (6.0, 20.0)
        return l * k, txt, P.inference("RF-GV-PON-015", note=f"{cle} : e = {txt} de la travée principale"), dom
    if fam == "PSIDP" and enc:
        v = oa_val("OA-ELA-002")
        k, txt = ((sum(v["isostatique"]) / 2, "l/23,5") if n == 1 else (v["deux_travees"], "l/25") if n == 2
                  else (v["trois_travees_et_plus"], "l/28"))
        return l * k, txt, oa("OA-ELA-002", note=f"dalle à larges encorbellements, {n} travée(s) : e = {txt}"), \
            (v["portee_min_m"], v["portee_max_m"])
    if fam == "PSIDP":
        k, txt = ((1 / 23.5, "l/23,5") if n == 1 else (1 / 28, "l/28") if n == 2 else (1 / 33, "l/33"))
        cle = "PSIDP_iso" if n == 1 else "PSIDP_2" if n == 2 else "PSIDP_3plus"
        return l * k, txt, P.inference("RF-GV-PON-015", note=f"{cle} : e = {txt}"), (14.0, 25.0)
    if fam == "PIPO":
        return l / 40 + 0.10, "l/40 + 0,10", P.inference("RF-GV-PON-015", note="PIPO : e = l/40 + 0,100"), (8.0, 22.0)
    if fam == "PICF":
        return l / 32 + 0.125, "l/32 + 0,125", P.inference("RF-GV-PON-015", note="PICF : e = l/32 + 0,125"), (2.0, 12.0)
    if fam in ("PRAD", "VIPP"):
        v = oa_val("OA-ELA-001", fam)
        plage = v["continu"] if (continu and fam == "PRAD") else v["isostatique"]
        k = sum(plage) / 2.0
        txt = f"l/{1 / k:.1f} (milieu de la plage {'continue' if continu else 'isostatique'} [G])"
        return l * k, txt, oa("OA-ELA-001", note=f"{fam} : e = {txt}"), tuple(v["portee"])
    raise ErreurOuvrage(f"famille de tablier sans élancement réglé : {fam} (caisson : épaisseur à dire)")


def compiler_ouvrages(d: dict, modele: dict, rapport: dict, trs: list[dict], origine: list, conf: str = "moyenne"):
    """Ajoute ouvrages[], profils en long et couches au modèle ; contrôles dans le rapport (tronçon porté)."""
    liste = d.get("ouvrages") or []
    if isinstance(liste, dict):                       # forme de la couche réseau : dictionnaire par identifiant
        liste = [dict(v, id=k) for k, v in liste.items()]
    if not isinstance(liste, list):
        raise ErreurOuvrage("ouvrages : liste attendue")
    par_id = {str(t["desc"].get("id")): t for t in trs if t["desc"].get("id") is not None}
    sortie = []
    for k, o in enumerate(liste):
        ch = f"ouvrages[{k}]"
        o = _dict(o, ch)
        inconnues = sorted(set(o) - CLES_OUVRAGE)
        if inconnues:
            raise ErreurOuvrage(f"{ch} : clé(s) inconnue(s) {', '.join(inconnues)} (admises : {', '.join(sorted(CLES_OUVRAGE))})")
        sortie.append(_un_ouvrage(o, ch, k, d, modele, rapport, trs, par_id, origine, conf))
    if sortie:
        modele["ouvrages"] = sortie
    return sortie


def _ctrl(tr_rap, controle, valeur, plage, regle, statut, note=None, **extra):
    c = {"controle": controle, "valeur": valeur, "plage": plage, "regle": regle, "statut": statut}
    if note:
        c["note"] = note
    c.update(extra)
    tr_rap["controles"].append(c)
    return c


def _dans(v, lo, hi):
    return lo - 1e-9 <= v <= hi + 1e-9


def _un_ouvrage(o, ch, k, d, modele, rapport, trs, par_id, origine, conf):
    oid = "O-" + str(o.get("id") or f"{k + 1}")
    typ_dit = V.norm_cle(o.get("type", ""))
    if typ_dit not in TYPES:
        raise ErreurOuvrage(f"{ch}.type : {o.get('type')} inconnu ({', '.join(sorted(TYPES))})")
    typ_modele, fonction = TYPES[typ_dit]
    for cle in ("porte", "franchit"):                 # forme de la couche réseau : listes d'un seul tronçon
        if isinstance(o.get(cle), list):
            if len(o[cle]) != 1:
                raise ErreurOuvrage(f"{ch}.{cle} : un seul tronçon par ouvrage (lu {o[cle]})")
            o[cle] = o[cle][0]
    porte = par_id.get(str(o.get("porte")))
    if porte is None:
        raise ErreurOuvrage(f"{ch}.porte : tronçon « {o.get('porte')} » inconnu (tronçons à id : {', '.join(par_id)})")
    rP = porte["route"]
    rid = porte["rid"]
    tr_rap = next(t for t in rapport["troncons"] if t["route"] == rid)
    L = float(rP["ligne_reference"]["longueur_m"])
    prov = {"*": P.description(ch, conf, note="ouvrage décrit"), "type": P.description(f"{ch}.type", conf)}
    # ---- franchissement
    fr = o.get("franchit")
    rF = None
    talweg = None
    if isinstance(fr, dict):
        fr = _dict(fr, f"{ch}.franchit")
        tw = _dict(fr.get("talweg"), f"{ch}.franchit.talweg")
        if not tw:
            raise ErreurOuvrage(f"{ch}.franchit : « <id de tronçon> » ou « {{talweg: {{profondeur, largeur_fond, "
                                "pente_versants}} »")
        talweg = {"profondeur_m": _num(tw, "profondeur", f"{ch}.franchit.talweg"),
                  "largeur_fond_m": _num(tw, "largeur_fond", f"{ch}.franchit.talweg"),
                  "pente_versants_h_sur_v": _num(tw, "pente_versants", f"{ch}.franchit.talweg", False,
                                                 oa_val("OA-TAL-001", "pente_h_sur_v"))}
        prov["construction.terrain.talweg.pente_versants_h_sur_v"] = (
            P.description(f"{ch}.franchit.talweg.pente_versants") if tw.get("pente_versants") is not None
            else oa("OA-TAL-001", note="berges du talweg au talus des remblais (choix [G])"))
        if o.get("centre") is None:
            raise ErreurOuvrage(f"{ch}.centre : abscisse du talweg sur le tronçon porté à dire")
        s_x = V.nombre(o["centre"], f"{ch}.centre")
        angle = V.nombre(o.get("biais", 90), f"{ch}.biais")
        s_y = None
        franchit = [{"type": "talweg", "ref": "talweg dit"}]
    else:
        tF = par_id.get(str(fr))
        if tF is None:
            raise ErreurOuvrage(f"{ch}.franchit : tronçon « {fr} » inconnu")
        rF = tF["route"]
        x = croisement(rP, rF)
        if x is None:
            raise ErreurOuvrage(f"{ch} : les lignes de référence de « {o.get('porte')} » et « {fr} » ne se croisent pas")
        s_x, s_y, _pt, angle = x
        if o.get("centre") is not None:
            s_x = V.nombre(o["centre"], f"{ch}.centre")
        franchit = [{"type": "route", "ref": rF["id"]}]
    if not (0.0 < s_x < L):
        raise ErreurOuvrage(f"{ch} : croisement hors du tronçon porté (s = {s_x:.2f}, L = {L:.2f})")
    sin_b = math.sin(math.radians(max(angle, 1.0)))
    # ---- travées, appuis, abouts
    trav = o.get("travees")
    if not isinstance(trav, list) or not trav:
        raise ErreurOuvrage(f"{ch}.travees : liste des portées entre axes d'appuis à dire (m)")
    trav = [V.nombre(x, f"{ch}.travees[{i}]") for i, x in enumerate(trav)]
    Lt = sum(trav)
    s_app = [s_x - Lt / 2.0]
    for x in trav:
        s_app.append(s_app[-1] + x)
    # ---- tablier
    tab = _dict(o.get("tablier"), f"{ch}.tablier")
    fam = str(tab.get("type", "")).upper()
    if fam not in TABLIERS:
        raise ErreurOuvrage(f"{ch}.tablier.type : {tab.get('type')} ({', '.join(TABLIERS)})")
    structure = TABLIERS[fam]
    portique = fam in ("PIPO", "PICF")
    enc = tab.get("encorbellements")
    enc = _dict(enc, f"{ch}.tablier.encorbellements") if isinstance(enc, dict) else ({} if enc is None else
                                                                                       ({"_oui": True} if V.booleen(enc, f"{ch}.tablier.encorbellements") else {}))
    continu = V.booleen(tab.get("continu", "non" if fam in ("PRAD", "VIPP") else "oui"), f"{ch}.tablier.continu")
    if fam == "CAISSON":
        if o.get("epaisseur") is None:
            raise ErreurOuvrage(f"{ch}.epaisseur : hauteur du caisson à dire (OA-CAI-001 : observations seulement)")
        e = V.nombre(o["epaisseur"], f"{ch}.epaisseur")
        prov["tablier.epaisseur_m"] = P.description(f"{ch}.epaisseur", conf)
        el_txt, dom = "dite", (None, None)
        lo, hi = oa_val("OA-CAI-001", "plage_observee")
        ratio = e / max(trav)
        _ctrl(tr_rap, f"{oid} élancement du caisson h / l", _r(ratio, 4), [lo, hi], None,
              "conforme" if _dans(ratio, lo, hi) else "avertissement",
              note="OA-CAI-001 (observations sur ouvrages réels, confiance faible) : contrôle d'avertissement")
    else:
        e_regle, el_txt, p_e, dom = epaisseur_regle(fam, bool(enc), trav, continu)
        if o.get("epaisseur") is not None:
            e = V.nombre(o["epaisseur"], f"{ch}.epaisseur")
            prov["tablier.epaisseur_m"] = P.description(f"{ch}.epaisseur", conf)
            ok = abs(e - e_regle) <= 0.05 * e_regle
            _ctrl(tr_rap, f"{oid} épaisseur dite / élancement {el_txt}", _r(e, 3), [_r(0.95 * e_regle, 3), _r(1.05 * e_regle, 3)],
                  "RF-GV-PON-015" if fam in ("PSIDA", "PSIDP", "PIPO", "PICF") and not enc else None,
                  "conforme" if ok else "hors_plage")
        else:
            e = e_regle
            prov["tablier.epaisseur_m"] = p_e
    e = round(e, 3)
    lmax = max(trav)
    if dom[0] is not None:
        _ctrl(tr_rap, f"{oid} portée principale dans le domaine du type {fam}", _r(lmax, 2), [dom[0], dom[1]],
              "RF-GV-PON-015" if fam in ("PSIDA", "PSIDP", "PIPO", "PICF") and not enc else None,
              "conforme" if _dans(lmax, dom[0], dom[1]) else "hors_plage",
              note=None if fam in ("PSIDA", "PSIDP", "PIPO", "PICF") and not enc else
              ("OA-ELA-002" if enc else "OA-ELA-001"))
    # balancement
    if len(trav) >= 3:
        for cote, a in (("gauche", trav[0] / trav[1]), ("droite", trav[-1] / trav[-2])):
            _ctrl(tr_rap, f"{oid} balancement travée de rive {cote}", _r(a, 3), [0.6, 0.85], "RF-GV-PON-015",
                  "conforme" if _dans(a, 0.6, 0.85) else "hors_plage", note="OA-BAL-001 : max ≈ 0,80, min 0,55")
    elif len(trav) == 2 and structure != "poutre":
        a = min(trav) / max(trav)
        _ctrl(tr_rap, f"{oid} balancement (2 travées)", _r(a, 3), [0.6, 1.0], "RF-GV-PON-015",
              "conforme" if a > 0.6 else "hors_plage")
    # ---- coupe de la route portée au croisement : bords de plate-forme, surface la plus basse, équipements
    cp = coupe_route(modele, rP, s_x)
    t_g, t_d = cp[0]["t_g"], cp[-1]["t_d"]
    z_bg, z_bd = cp[0]["z_g"], cp[-1]["z_d"]
    z_min = min(min(b["z_g"], b["z_d"]) for b in cp)
    rev = (V.nombre(o["revetement"], f"{ch}.revetement") if o.get("revetement") is not None
           else oa_val("OA-REV-001", "epaisseur_m"))
    prov["construction.tablier.revetement_m"] = (P.description(f"{ch}.revetement") if o.get("revetement") is not None
                                                 else oa("OA-REV-001", note="choix [G]"))
    z_dessus = z_min - rev                            # dessus du béton du tablier, relatif à l'axe de la route portée
    # corniche et bandes d'équipement
    cor = _dict(o.get("corniche"), f"{ch}.corniche")
    corniche = None
    if cor:
        corniche = {"hauteur_m": _num(cor, "hauteur", f"{ch}.corniche"), "largeur_m": _num(cor, "largeur", f"{ch}.corniche"),
                    "debord_m": _num(cor, "debord", f"{ch}.corniche", False, 0.0)}
        prov["construction.corniche"] = P.description(f"{ch}.corniche", conf)
    eqs = _dict(o.get("equipements"), f"{ch}.equipements")
    # hauteur de chute : surface de marche au bord - terrain le plus bas sous l'ouvrage
    if talweg:
        z_nat = 0.0
        z_bas = -talweg["profondeur_m"]
    else:
        cpF = coupe_route(modele, rF, s_y)
        z_nat = min(cpF[0]["z_g"], cpF[-1]["z_d"])   # terrain naturel au niveau des bords extérieurs de la route franchie
        # intégration de l'étape 4 (scène qui compose un ouvrage et d'autres routes à niveau : bretelle, branches d'un
        # carrefour) : le terrain naturel passe sous le plus bas des bords de toutes les routes (toutes sections), moins
        # une marge [G] ; les routes à niveau reposent sur un léger remblai (talus OA-TAL-001 de rg::ouvrages autour de
        # leur sol), aucune n'est recouverte par le terrain. Sans autre route : inchangé.
        z_bords = z_bords_routes_a_niveau(d, modele, par_id)
        if z_bords is not None:
            z_nat = min(z_nat, z_bords) - MARGE_TERRAIN_NIVEAU
            prov["construction.terrain.z_naturel_rel"] = P.solveur(
                "ouvrage.terrain", note=f"routes à niveau hors ouvrage : terrain naturel {MARGE_TERRAIN_NIVEAU:.2f} m sous "
                                        "le plus bas de leurs bords (choix [G], intégration de l'étape 4)")
        z_bas = z_nat
    # ---- gabarit et profil en long
    pel_prov = {}
    gab = None
    exig = []                                          # (raison, z_c minimal)
    if rF is not None:
        catF = rF.get("categorie")
        g_m = 4.75 if catF in CATEGORIES_GRAND_GABARIT else 4.30
        cle_g = "autoroutes_VRU" if catF in CATEGORIES_GRAND_GABARIT else "reseau_national_et_local"
        rev_g = float(regles.valeur("DEF-033")["revanche"])
        h_libre = g_m + rev_g
        circ = [b for b in cpF if b["type"] in CIRCULABLES]
        if not circ:
            raise ErreurOuvrage(f"{ch} : aucune bande circulable sur la route franchie")
        z_F = max(max(b["z_g"], b["z_d"]) for b in circ)
        demi = max(max(abs(b["t_g"]), abs(b["t_d"])) for b in circ)
        cpF_all = [max(abs(b["t_g"]), abs(b["t_d"])) for b in cpF]
        B_dem = (t_g - t_d) / 2.0
        ds = demi / sin_b + B_dem * abs(math.cos(math.radians(angle))) / sin_b
        gab = {"route_franchie": rF["id"], "categorie_franchie": catF, "gabarit_m": g_m, "revanche_m": rev_g,
               "hauteur_libre_min_m": _r(h_libre, 3), "z_franchie_max_rel": _r(z_F, 4), "demi_largeur_circulable_m": _r(demi, 3),
               "demi_largeur_plateforme_franchie_m": _r(max(cpF_all), 3), "s_franchie": _r(s_y, 4), "biais_deg": _r(angle, 3),
               "ds_m": _r(ds, 3)}
        prov["gabarit_vertical_m"] = P.inference("RF-GV-PON-012", note=f"{cle_g} = {g_m} m ; revanche 0,10 (DEF-033)")
        exig.append(("gabarit", z_F + h_libre + e - z_dessus, ds))
    # espace libre au-dessus du terrain naturel sous le tablier (entre les fronts des culées)
    cul = _dict(o.get("culees"), f"{ch}.culees")
    pd = _dict(o.get("piedroits"), f"{ch}.piedroits")
    if portique:
        if not pd:
            raise ErreurOuvrage(f"{ch}.piedroits : épaisseur à dire (portique / cadre)")
        piedroits = {"epaisseur_m": _num(pd, "epaisseur", f"{ch}.piedroits"),
                     "semelle_m": _num(pd, "semelle", f"{ch}.piedroits", False, 0.0)}
        prov["construction.piedroits"] = P.description(f"{ch}.piedroits", conf)
        culees = None
        d_front = piedroits["epaisseur_m"] / 2.0
    else:
        if not cul:
            raise ErreurOuvrage(f"{ch}.culees : sommier, garde-grève et murs en retour à dire")
        som = _dict(cul.get("sommier"), f"{ch}.culees.sommier")
        culees = {"type": str(cul.get("type", "perchee")),
                  "sommier_hauteur_m": _num(som, "hauteur", f"{ch}.culees.sommier"),
                  "sommier_largeur_m": _num(som, "largeur", f"{ch}.culees.sommier"),
                  "garde_greve_epaisseur_m": _num(cul, "garde_greve", f"{ch}.culees"),
                  "murs_retour_longueur_m": _num(cul, "murs_retour", f"{ch}.culees"),
                  "murs_retour_epaisseur_m": _num(cul, "murs_retour_epaisseur", f"{ch}.culees")}
        prov["construction.culees"] = P.description(f"{ch}.culees", conf)
        piedroits = None
        d_front = culees["sommier_largeur_m"] / 2.0
    app = _dict(o.get("appareils_appui"), f"{ch}.appareils_appui")
    if portique:
        appareils = None
        h_app = 0.0
    else:
        appareils = {"a_m": _num(app, "a", f"{ch}.appareils_appui"), "b_m": _num(app, "b", f"{ch}.appareils_appui"),
                     "hauteur_m": _num(app, "hauteur", f"{ch}.appareils_appui"),
                     "nombre": int(_num(app, "nombre", f"{ch}.appareils_appui"))}
        prov["construction.appareils_appui"] = P.description(f"{ch}.appareils_appui", conf)
        h_app = appareils["hauteur_m"]

    def z_terrain(s):
        if talweg is None:
            return z_nat
        u = abs(s - s_x) * sin_b
        demi_f = talweg["largeur_fond_m"] / 2.0
        if u <= demi_f:
            return -talweg["profondeur_m"]
        return min(0.0, -talweg["profondeur_m"] + (u - demi_f) / talweg["pente_versants_h_sur_v"])

    s_f0, s_f1 = s_app[0] + d_front, s_app[-1] - d_front
    ech = [s_f0 + (s_f1 - s_f0) * i / 200.0 for i in range(201)]
    zt_max = max(z_terrain(s) for s in ech)
    s_tmax = max(ech, key=lambda s: (z_terrain(s), -abs(s - s_x)))
    exig.append(("terrain", None, None))
    # ---- profil en long
    pente_max = Rs = Rr = None
    cl = None
    besoin = []
    for raison, zc_min, dsx in exig:
        if raison == "gabarit":
            besoin.append((raison, zc_min, dsx))
    # exigence terrain : z_c tel que l'intrados reste à REVANCHE_TERRAIN au-dessus du terrain naturel sous le tablier
    besoin_terrain = (zt_max + REVANCHE_TERRAIN + e - z_dessus, abs(s_tmax - s_x))
    z0 = 0.0
    a_relever = any(b[1] > z0 for b in besoin) or besoin_terrain[0] > z0
    if a_relever:
        cl, pente_max, Rs, Rr, pel_prov = classe_pel(o, ch)
        z_c = z0
        for raison, zc_min, dsx in besoin:
            z_c = max(z_c, zc_min + dsx * dsx / (2.0 * Rs))
        z_c = max(z_c, besoin_terrain[0] + besoin_terrain[1] ** 2 / (2.0 * Rs))
        z_c = math.ceil(z_c * 100.0) / 100.0       # au centimètre supérieur
        pl = ProfilEnLong(s_x, z_c, z0, pente_max / 100.0, Rs, Rr)
        if not pl.plat and (s_x - pl.demi < 0 or s_x + pl.demi > L):
            raise ErreurOuvrage(f"{ch} : profil en long de {2 * pl.demi:.1f} m (déclivité {100 * pl.g:.2f} %, Rs {Rs:.0f}, "
                                f"Rr {Rr:.0f}) plus long que le tronçon porté autour du croisement (s = {s_x:.1f}, L = {L:.1f})")
    else:
        pl = ProfilEnLong(s_x, z0, z0, 0.0, 1.0, 1.0)
    # ---- hauteur de chute et dispositifs de retenue
    zl = pl.z
    s_ab0, s_ab1 = None, None
    d_about = 0.0 if portique else oa_val("OA-JNT-002", "about_appareil_m")
    if portique:
        s_ab0, s_ab1 = s_app[0] - piedroits["epaisseur_m"] / 2.0, s_app[-1] + piedroits["epaisseur_m"] / 2.0
    else:
        s_ab0, s_ab1 = s_app[0] - d_about, s_app[-1] + d_about
    ss = [s_ab0 + (s_ab1 - s_ab0) * i / 100.0 for i in range(101)]

    def hc(z_bord):
        return max(zl(s) + z_bord - z_terrain(s) for s in ss)

    def cote(nom, idx_bande, z_bord):
        v = eqs.get(nom)
        if v is None:
            raise ErreurOuvrage(f"{ch}.equipements.{nom} : garde-corps S8, BN4 ou BN4 + garde-corps à dire")
        txt = V.norm(v if isinstance(v, str) else v.get("type", ""))
        bande = cp[idx_bande]
        Hc = hc(z_bord)
        res = {"bande_bord": bande["type"], "hc_m": _r(Hc, 3), "t_bord": _r(bande["t_g"] if idx_bande == 0 else bande["t_d"], 4),
               "z_bord_rel": _r(z_bord, 4)}
        if "bn4" in txt:
            res.update({"type": "BN4", "hauteur_m": oa_val("OA-BN4-001", "lisse_superieure_hauteur_m"),
                        "entraxe_poteaux_m": oa_val("OA-BN4-001", "entraxe_poteaux_m"),
                        "longrine_hauteur_m": 0.15, "distance_bord_m": oa_val("OA-BN4-001", "distance_bord_ouvrage_min_m"),
                        "longueur_file_min_m": oa_val("OA-BN4-001", "longueur_file_min_m"),
                        "asset_id": None})
            prov[f"construction.equipements.{nom}"] = oa("OA-BN4-001", note="longrine 0,15 m dans la plage 0,12-0,18 (choix [G])")
            if bande["type"] in ("trottoir", "chemin_pieton", "piste_cyclable", "voie_verte"):
                raise ErreurOuvrage(f"{ch}.equipements.{nom} : BN4 seule le long d'un cheminement piéton ou cycliste : "
                                    "ajouter un garde-corps (RF-GV-PON-010, classes A ou B)")
            _ctrl(tr_rap, f"{oid} barrière {nom} (piétons interdits : h > 0,90 m)", 1.0, [0.9, None], "RF-GV-PON-007",
                  "conforme")
            return res
        if "garde" in txt:
            if bande["type"] == "piste_cyclable":
                h = float(regles.valeur("DEF-033")["garde_corps_cycles"])
                bande_h = [h, 1.40]
                res.update({"usage": "cycles", "hauteur_m": h, "bande_m": bande_h, "asset_id": "garde_corps_pont_S8_cycles_L30",
                            "hauteur_asset_m": 1.2})
                prov[f"construction.equipements.{nom}.hauteur_m"] = P.defaut("DEF-033", note="garde_corps_cycles 1,20 m "
                                                                             "le long d'une piste cyclable (RF-GV-PON-007)")
            elif bande["type"] in ("trottoir", "chemin_pieton", "voie_verte"):
                h = min(0.95 + 0.005 * Hc, 1.20)
                bande_h = [0.90 + 0.005 * Hc, min(1.00 + 0.005 * Hc, 1.20)]
                res.update({"usage": "pietons", "hauteur_m": _r(h, 3), "bande_m": [_r(bande_h[0], 3), _r(bande_h[1], 3)],
                            "asset_id": "garde_corps_pont_S8_L30", "hauteur_asset_m": 1.0})
                prov[f"construction.equipements.{nom}.hauteur_m"] = P.defaut("DEF-033", note=f"min(0,95 + 0,005 Hc ; 1,20), "
                                                                             f"Hc = {Hc:.2f} m (GC97 p. 16)")
            else:
                raise ErreurOuvrage(f"{ch}.equipements.{nom} : garde-corps seul le long d'une bande {bande['type']} "
                                    "(chaussée) : dispositif de retenue de véhicules à dire (BN4, RF-GV-PON-010)")
            res.update({"type": "garde_corps", "modele": "S8", "entraxe_montants_m": 1.5})
            res["echelle_z_asset"] = _r(res["hauteur_m"] / res["hauteur_asset_m"], 4)
            return res
        raise ErreurOuvrage(f"{ch}.equipements.{nom} : « {v} » inconnu (garde-corps S8, BN4)")

    eq_g = cote("gauche", 0, z_bg)
    eq_d = cote("droite", len(cp) - 1, z_bd)
    for nom, eq in (("gauche", eq_g), ("droite", eq_d)):
        if eq["type"] == "garde_corps":
            lo, hi = eq["bande_m"]
            _ctrl(tr_rap, f"{oid} garde-corps {nom} ({eq['usage']}) h", eq["hauteur_m"], [lo, hi],
                  "DEF-033" if eq["usage"] == "pietons" else "RF-GV-PON-007",
                  "conforme" if _dans(eq["hauteur_m"], lo, hi) else "hors_plage", note=f"Hc = {eq['hc_m']} m")
    # trottoirs sur l'ouvrage
    for b in cp:
        if b["type"] == "trottoir":
            _ctrl(tr_rap, f"{oid} trottoir sur l'ouvrage ({b['bande']})", _r(b["largeur"], 3), [1.0, None], "RF-GV-PON-003",
                  "conforme" if b["largeur"] >= 1.0 - 1e-9 else "non_conforme", note="≥ 1,25 m si fréquenté")
    # trottoirs sous l'ouvrage (route franchie)
    if rF is not None:
        for b in cpF:
            if b["type"] == "trottoir":
                _ctrl(tr_rap, f"{oid} trottoir sous l'ouvrage ({rF['id']}.{b['bande']})", _r(b["largeur"], 3), [2.0, None],
                      "RF-GV-PON-014", "conforme" if b["largeur"] >= 2.0 - 1e-9 else "non_conforme")
    # ---- piles
    pi = _dict(o.get("piles"), f"{ch}.piles")
    piles = None
    if len(s_app) > 2:
        if not pi:
            raise ErreurOuvrage(f"{ch}.piles : type (voiles, poteaux) et cotes à dire")
        ptyp = V.norm(pi.get("type", ""))
        if ptyp.startswith("voile"):
            piles = {"type": "voiles", "epaisseur_m": _num(pi, "epaisseur", f"{ch}.piles"),
                     "largeur_m": _num(pi, "largeur", f"{ch}.piles")}
        elif ptyp.startswith("poteau"):
            chv = _dict(pi.get("chevetre"), f"{ch}.piles.chevetre")
            piles = {"type": "poteaux", "nombre": int(_num(pi, "nombre", f"{ch}.piles")),
                     "diametre_m": _num(pi, "diametre", f"{ch}.piles"), "entraxe_m": _num(pi, "entraxe", f"{ch}.piles"),
                     "chevetre": {"hauteur_m": _num(chv, "hauteur", f"{ch}.piles.chevetre"),
                                  "largeur_m": _num(chv, "largeur", f"{ch}.piles.chevetre"),
                                  "longueur_m": _num(chv, "longueur", f"{ch}.piles.chevetre")}}
        else:
            raise ErreurOuvrage(f"{ch}.piles.type : voiles ou poteaux")
        piles["s"] = [_r(s, 4) for s in s_app[1:-1]]
        prov["construction.piles"] = P.description(f"{ch}.piles", conf)
        # distance des appuis aux voies de la route franchie (RF-GV-PON-014)
        if rF is not None:
            demi_voies = max((max(abs(b["t_g"]), abs(b["t_d"])) for b in cpF if b["type"] in
                              ("voie_circulation", "voie_bus")), default=0.0)
            for sp in s_app[1:-1]:
                u = abs(sp - s_x) * sin_b
                ep = piles["epaisseur_m"] if piles["type"] == "voiles" else piles["diametre_m"]
                dist = u - ep / 2.0 / sin_b - demi_voies
                if u < demi_voies + 30:
                    _ctrl(tr_rap, f"{oid} pile s = {sp:.2f} : distance au bord des voies franchies", _r(dist, 3), [2.0, None],
                          "RF-GV-PON-014", "conforme" if dist >= 2.0 - 1e-9 else "non_conforme")
    # ---- murs en aile (portique), dalles de transition, joints, talus
    murs_aile = None
    if portique:
        ma = _dict(o.get("murs_aile"), f"{ch}.murs_aile")
        if not ma:
            raise ErreurOuvrage(f"{ch}.murs_aile : épaisseur à dire (OA-PIPO-001 : murs de tête)")
        murs_aile = {"epaisseur_m": _num(ma, "epaisseur", f"{ch}.murs_aile"),
                     "disposition": "paralleles_voie_franchie"}
        prov["construction.murs_aile"] = P.description(f"{ch}.murs_aile", conf,
                                                       note="murs en aile parallèles à la voie franchie (OA-PIPO-001)")
    ddt = None
    if V.booleen(o.get("dalles_transition", "oui"), f"{ch}.dalles_transition"):
        ddt = {"longueur_m": oa_val("OA-DDT-001", "longueur_retenue_m"), "epaisseur_m": oa_val("OA-DDT-001", "epaisseur_m")}
        prov["construction.dalles_transition"] = oa("OA-DDT-001", note="longueur 4,0 m, milieu de la plage 3-5 m (choix [G])")
    if portique:
        joints = {"s": [], "type": None, "motif": "portique : joints supprimés (OA-PIPO-001, GPOA p. 213)"}
        prov["joints_chaussee_s"] = oa("OA-PIPO-001", note="aucun joint de chaussée sur un portique ou un cadre")
    else:
        gap = oa_val("OA-ESP-001", "about_garde_greve_m")
        joints = {"s": [_r(s_ab0 - gap / 2.0, 4), _r(s_ab1 + gap / 2.0, 4)], "type": "revetement_ameliore",
                  "largeur_m": oa_val("OA-JNT-001", "largeur_m"), "vide_about_garde_greve_m": gap,
                  "travers_trottoirs": True}
        prov["joints_chaussee_s"] = oa("OA-JNT-001", note="un joint par about, sur toute la largeur roulable et à travers le "
                                                          "trottoir (RF-GV-PON-011, GPOA p. 54) ; vide about / garde-grève "
                                                          "0,40 m (OA-ESP-001) ; about à 0,50 m de l'axe d'appui (OA-JNT-002)")
    talus = {"pente_h_sur_v": oa_val("OA-TAL-001", "pente_h_sur_v")}
    prov["construction.talus"] = oa("OA-TAL-001")
    # ---- tablier : section
    B_g = t_g + (corniche["largeur_m"] if corniche else 0.0)
    B_d = t_d - (corniche["largeur_m"] if corniche else 0.0)
    for nom, eq in (("gauche", eq_g), ("droite", eq_d)):
        if eq["type"] == "BN4":
            zone = eq["distance_bord_m"] + 0.25        # lisses + poteaux (0,25 m [G]) puis 0,45 m jusqu'au bord (OA-BN4-001)
            eq["zone_m"] = _r(zone, 3)
            if nom == "gauche":
                B_g = t_g + zone + (corniche["largeur_m"] if corniche else 0.0)
            else:
                B_d = t_d - zone - (corniche["largeur_m"] if corniche else 0.0)
    section = {"t_gauche": _r(B_g, 4), "t_droite": _r(B_d, 4), "largeur_m": _r(B_g - B_d, 4), "z_dessus_rel": _r(z_dessus, 4),
               "epaisseur_m": e}
    if enc:
        section["encorbellement"] = {"longueur_m": _num(enc, "longueur", f"{ch}.tablier.encorbellements"),
                                     "epaisseur_extremite_m": _num(enc, "epaisseur_extremite", f"{ch}.tablier.encorbellements"),
                                     "epaisseur_racine_m": _num(enc, "epaisseur_racine", f"{ch}.tablier.encorbellements")}
        prov["construction.tablier.encorbellement"] = P.description(f"{ch}.tablier.encorbellements", conf)
    if fam == "CAISSON":
        cs = _dict(tab.get("caisson"), f"{ch}.tablier.caisson")
        section["caisson"] = {k: _num(cs, k, f"{ch}.tablier.caisson") for k in
                              ("largeur_inferieure", "ecart_ames", "hourdis", "epaisseur_extremite")}
        prov["construction.tablier.caisson"] = P.description(f"{ch}.tablier.caisson", conf)
    if structure == "poutre":
        pt = _dict(tab.get("poutres"), f"{ch}.tablier.poutres")
        section["poutres"] = {"nombre": int(_num(pt, "nombre", f"{ch}.tablier.poutres")),
                              "largeur_ame_m": _num(pt, "largeur_ame", f"{ch}.tablier.poutres"),
                              "talon_m": _num(pt, "talon", f"{ch}.tablier.poutres"),
                              "hourdis_m": _num(pt, "hourdis", f"{ch}.tablier.poutres")}
        prov["construction.tablier.poutres"] = P.description(f"{ch}.tablier.poutres", conf)
    # épaisseur du tablier : contrôle l/28 des dalles (critère du lot)
    if structure == "dalle":
        _ctrl(tr_rap, f"{oid} épaisseur de la dalle e / l", _r(e / lmax, 5), [_r(e / lmax, 5), _r(e / lmax, 5)],
              "RF-GV-PON-015" if not enc else None, "conforme", note=f"e = {e} m = {el_txt} (l = {lmax} m)")
    # ---- profil en long écrit sur la route portée
    z_ngf0 = float(origine[2]) if len(origine) > 2 else 0.0
    pts = sorted({_r(s, 4) for s in [i * PAS_PROFIL for i in range(int(L / PAS_PROFIL) + 1)] + [L]})
    rP["profil_long"] = {"source": "ouvrage", "z": [[_r(s, 4), _r(z_ngf0 + zl(s), 4)] for s in pts],
                         "pente_max_pct": _r(100 * (pl.g if not pl.plat else 0.0), 4)}
    rP.setdefault("prov", {})["profil_long"] = (P.solveur("ouvrage.profil_en_long", note=(
        f"{oid} : z NGF = {z_ngf0} + z local ; sommet {pl.z_c:.2f} m au croisement, gabarit RF-GV-PON-012 + revanche, "
        "raccordements paraboliques (OA-PEL-001 / OA-PEL-002)")))
    rP["layer"] = 1
    rP["prov"]["layer"] = P.solveur("ouvrage.layer", note="route portée par l'ouvrage (OSM layer=1, RF-OSM-OUV-001)",
                                    regle="RF-OSM-OUV-001")
    rP.setdefault("ouvrages", []).append(oid)
    if rF is not None:
        rF["layer"] = 0
        rF.setdefault("prov", {})["layer"] = P.solveur("ouvrage.layer", note="route franchie (layer=0)",
                                                       regle="RF-OSM-OUV-001")
        rF.setdefault("ouvrages", []).append(oid)
    if a_relever and not pl.plat:
        _ctrl(tr_rap, f"{oid} déclivité du profil en long", _r(100 * pl.g, 3), [None, pente_max], None,
              "conforme" if 100 * pl.g <= pente_max + 1e-9 else "hors_plage", note=f"classe {cl} (OA-PEL)")
    # ---- dispositifs de retenue (contrat du schéma)
    dr = []
    for nom, eq in (("gauche", eq_g), ("droite", eq_d)):
        dr.append({"cote": nom, "type": "BN4" if eq["type"] == "BN4" else "garde_corps", "hauteur_m": eq["hauteur_m"]})
    hc_max = max(eq_g["hc_m"], eq_d["hc_m"])
    construction = {
        "version": VERSION, "fonction": fonction, "famille_tablier": fam + ("_LE" if enc and fam == "PSIDP" else ""),
        "route_portee": rid, "route_franchie": rF["id"] if rF is not None else None,
        "s_croisement": _r(s_x, 4), "biais_deg": _r(angle, 3), "travees_m": trav, "s_appuis": [_r(s, 4) for s in s_app],
        "s_abouts": [_r(s_ab0, 4), _r(s_ab1, 4)], "elancement": el_txt, "continu": continu,
        "tablier": dict(section, type=fam, structure=structure, revetement_m=rev),
        "corniche": corniche, "equipements": {"gauche": eq_g, "droite": eq_d}, "piles": piles, "culees": culees,
        "piedroits": piedroits, "murs_aile": murs_aile, "appareils_appui": appareils, "joints": joints,
        "dalles_transition": ddt, "talus": talus, "gabarit": gab, "hc_m": _r(hc_max, 3),
        "terrain": {"z_naturel_rel": _r(z_nat, 4), "talweg": talweg, "revanche_intrados_terrain_m": REVANCHE_TERRAIN,
                    "z_bas_rel": _r(z_bas, 4)},
        "profil_en_long": {"route": rid, "classe": cl, "declivite_max_pct": pente_max, "rayon_saillant_m": Rs,
                           "rayon_rentrant_m": Rr, "sommet_z_rel": _r(pl.z_c, 4), "z0_rel": z0,
                           "elements": pl.elements(), "z_ngf_origine": z_ngf0},
        "coupe_portee": [[_r(b["t_g"], 4), _r(b["z_g"], 4), _r(b["t_d"], 4), _r(b["z_d"], 4), b["type"]] for b in cp],
        "coupe_franchie": [[_r(b["t_g"], 4), _r(b["z_g"], 4), _r(b["t_d"], 4), _r(b["z_d"], 4), b["type"]] for b in cpF]
        if rF is not None else None,
    }
    prov.update(pel_prov and {f"construction.profil_en_long.{k}": v for k, v in pel_prov.items()} or {})
    ouv = {"id": oid, "type": typ_modele, "routes_portees": [{"route": rid, "s0": _r(s_ab0, 4), "s1": _r(s_ab1, 4)}],
           "franchit": franchit, "layer": 1,
           "tablier": {"epaisseur_m": e, "largeur_m": section["largeur_m"], "materiau": "beton",
                       "structure": structure, "corniche": corniche is not None, "type": fam},
           "dispositifs_retenue": dr,
           "appuis": {"culees": not portique, **({"piles_largeur_m": piles["epaisseur_m"] if piles["type"] == "voiles"
                                                 else piles["diametre_m"]} if piles else {})},
           "joints_chaussee_s": joints["s"],
           "raccords": {"pente_pct": _r(100 * (pl.g if not pl.plat else 0.0), 3),
                        **({"remblai_longueur_m": _r(pl.demi - (s_x - s_ab0), 2)} if not pl.plat else {})},
           "construction": construction, "prov": prov}
    if gab:
        ouv["gabarit_vertical_m"] = gab["hauteur_libre_min_m"]
    if o.get("nom"):
        ouv["construction"]["nom"] = str(o["nom"])
    ouv["x-opendrive"] = {"object_type": "bridge", "type": "concrete"}
    prov["layer"] = P.solveur("ouvrage.layer", regle="RF-OSM-OUV-001")
    return ouv
