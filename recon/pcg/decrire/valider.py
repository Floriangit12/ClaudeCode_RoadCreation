"""Validation de la description v2 : schéma JSON (draft 2020-12, validateur minimal intégré, le
paquet jsonschema n'étant pas installé) puis contrôles géométriques et de cohérence.

Usage :
    python recon/pcg/decrire/valider.py [DOSSIER_DESCRIPTION]
Défaut : recon/out/paquet_jardin/v2/description. Code de sortie 0 si tout est valide, 1 sinon.

Contrôles en plus du schéma :
- intervalles de chaque bordure : partition exacte de [0, longueur], vues dans la plage du profil ;
- abaissés et chartières dans [0, L], sans chevauchement ; BEV ancrées sur un abaissé existant ;
- longueur_m = longueur 2D de la polyligne (± 2 cm) ; Z dans la plage du MNT 2026 ;
- anneaux fermés, aires > 0 ; tout dans l'emprise de la zone pilote (± 0,5 m) ;
- identifiants uniques et références résolues (bords, ceintures, îlots, surfaces, ancrages) ;
- remplissages d'îlots 0 à 8 cm sous le dessus de bordure ; materiau_id présents dans la table ;
- famille marquages (0.2, si présente) : voir marquages_controles.py (correspondance des 996 v1,
  lignes dans les bords de voie, tirets sans recouvrement, zébras dans la chaussée, 0 marche d'escalier).
"""
import re
import sys
from pathlib import Path

import numpy as np

from commun import MATERIAUX, SCHEMA, SORTIE, lire_json
import contexte as ctx

VUE_PLAGE = {"P1": (0.0, 0.03), "A2": (0.03, 0.09), "T2": (0.09, 0.175), "T3": (0.175, 0.30),
             "QUAI_BUS": (0.15, 0.24), "T2_bateau": (0.0, 0.04), "MURET_TALUS": (0.30, 1.5)}


# --------------------------------------------------------------------------- schéma (sous-ensemble 2020-12)
class Validateur:
    def __init__(self, racine):
        self.racine = racine

    def resoudre(self, ref):
        if not ref.startswith("#/"):
            raise ValueError(f"$ref non local : {ref}")
        n = self.racine
        for k in ref[2:].split("/"):
            n = n[k.replace("~1", "/").replace("~0", "~")]
        return n

    @staticmethod
    def type_ok(v, t):
        if t == "null":
            return v is None
        if t == "boolean":
            return isinstance(v, bool)
        if t == "object":
            return isinstance(v, dict)
        if t == "array":
            return isinstance(v, list)
        if t == "string":
            return isinstance(v, str)
        if t == "integer":
            return (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, float) and v.is_integer())
        if t == "number":
            return isinstance(v, (int, float)) and not isinstance(v, bool)
        raise ValueError(f"type inconnu {t}")

    def valider(self, v, s, chemin="$"):
        """Liste des erreurs (chaînes)."""
        if s is True or s == {}:
            return []
        if s is False:
            return [f"{chemin} : interdit"]
        err = []
        if "$ref" in s:
            err += self.valider(v, self.resoudre(s["$ref"]), chemin)
        if "type" in s:
            ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(self.type_ok(v, t) for t in ts):
                return err + [f"{chemin} : type {type(v).__name__} au lieu de {ts}"]
        if "const" in s and not egal(v, s["const"]):
            err.append(f"{chemin} : {v!r} ≠ const {s['const']!r}")
        if "enum" in s and not any(egal(v, e) for e in s["enum"]):
            err.append(f"{chemin} : {v!r} hors enum")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if "minimum" in s and v < s["minimum"]:
                err.append(f"{chemin} : {v} < minimum {s['minimum']}")
            if "maximum" in s and v > s["maximum"]:
                err.append(f"{chemin} : {v} > maximum {s['maximum']}")
            if "exclusiveMinimum" in s and v <= s["exclusiveMinimum"]:
                err.append(f"{chemin} : {v} ≤ {s['exclusiveMinimum']}")
            if "exclusiveMaximum" in s and v >= s["exclusiveMaximum"]:
                err.append(f"{chemin} : {v} ≥ {s['exclusiveMaximum']}")
        if isinstance(v, str):
            if "pattern" in s and not re.search(s["pattern"], v):
                err.append(f"{chemin} : {v!r} ne suit pas {s['pattern']}")
            if "minLength" in s and len(v) < s["minLength"]:
                err.append(f"{chemin} : chaîne trop courte")
        if isinstance(v, dict):
            for k in s.get("required", []):
                if k not in v:
                    err.append(f"{chemin} : clé requise absente « {k} »")
            if "minProperties" in s and len(v) < s["minProperties"]:
                err.append(f"{chemin} : moins de {s['minProperties']} propriétés")
            props = s.get("properties", {})
            for k, x in v.items():
                if k in props:
                    err += self.valider(x, props[k], f"{chemin}.{k}")
                elif "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        err.append(f"{chemin} : propriété non prévue « {k} »")
                    elif isinstance(ap, dict):
                        err += self.valider(x, ap, f"{chemin}.{k}")
        if isinstance(v, list):
            if "minItems" in s and len(v) < s["minItems"]:
                err.append(f"{chemin} : moins de {s['minItems']} éléments")
            if "maxItems" in s and len(v) > s["maxItems"]:
                err.append(f"{chemin} : plus de {s['maxItems']} éléments")
            pre = s.get("prefixItems", [])
            for i, x in enumerate(v):
                if i < len(pre):
                    err += self.valider(x, pre[i], f"{chemin}[{i}]")
                elif "items" in s:
                    if s["items"] is False:
                        err.append(f"{chemin}[{i}] : élément en trop")
                    else:
                        err += self.valider(x, s["items"], f"{chemin}[{i}]")
        for sub in s.get("allOf", []):
            err += self.valider(v, sub, chemin)
        if "anyOf" in s and not any(not self.valider(v, sub, chemin) for sub in s["anyOf"]):
            err.append(f"{chemin} : aucune branche anyOf valide")
        if "oneOf" in s:
            n_ok = sum(1 for sub in s["oneOf"] if not self.valider(v, sub, chemin))
            if n_ok != 1:
                err.append(f"{chemin} : {n_ok} branches oneOf valides au lieu d'une")
        if "not" in s and not self.valider(v, s["not"], chemin):
            err.append(f"{chemin} : correspond au schéma interdit (not)")
        return err


def egal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(egal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(egal(x, y) for x, y in zip(a, b))
    return a == b


# --------------------------------------------------------------------------- contrôles géométriques
def longueur2d(c):
    a = np.asarray(c, float)[:, :2]
    return float(np.hypot(*np.diff(a, axis=0).T).sum())


def aire(r):
    a = np.asarray(r, float)[:, :2]
    return 0.5 * float(np.dot(a[:-1, 0], a[1:, 1]) - np.dot(a[1:, 0], a[:-1, 1]))


def anneaux_de(g):
    return [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"] if g["type"] == "MultiPolygon" else []


def controles(couches, mnt_z=(213.1, 219.9)):
    err, warn = [], []
    x0, y0, x1, y1 = ctx.zone_pilote()["emprise"]
    e = (x0 + 917279.43 - 0.5, y0 + 6460289.98 - 0.5, x1 + 917279.43 + 0.5, y1 + 6460289.98 + 0.5)
    mats = set(lire_json(MATERIAUX)["materiaux"])
    ids = {}
    for fam, feats in couches.items():
        for f in feats:
            i = f["properties"]["id"]
            if i in ids:
                err.append(f"id en double : {i} ({ids[i]} et {fam})")
            ids[i] = fam

    def dans_e(c):
        a = np.asarray(c, float)
        return bool(np.all((a[:, 0] >= e[0]) & (a[:, 0] <= e[2]) & (a[:, 1] >= e[1]) & (a[:, 1] <= e[3])))

    abaisses = {}
    for f in couches["bordures"]:
        p, c = f["properties"], f["geometry"]["coordinates"]
        L = p["longueur_m"]
        if abs(longueur2d(c) - L) > 0.02:
            err.append(f"{p['id']} : longueur_m {L} ≠ longueur géométrique {longueur2d(c):.3f}")
        if not dans_e(c):
            err.append(f"{p['id']} : hors emprise de la zone pilote")
        zs = [q[2] for q in c]
        if min(zs) < mnt_z[0] or max(zs) > mnt_z[1]:
            err.append(f"{p['id']} : Z hors plage MNT {min(zs):.2f}-{max(zs):.2f}")
        its = p["intervalles"]
        if abs(its[0]["s0"]) > 1e-3 or abs(its[-1]["s1"] - L) > 0.01:
            err.append(f"{p['id']} : intervalles ne couvrant pas [0, {L}]")
        for a, b in zip(its[:-1], its[1:]):
            if abs(a["s1"] - b["s0"]) > 1e-3:
                err.append(f"{p['id']} : trou ou chevauchement entre intervalles à s={a['s1']}")
        for it in its:
            if it["s1"] - it["s0"] < -1e-9:
                err.append(f"{p['id']} : intervalle inversé {it}")
            lo, hi = VUE_PLAGE.get(it["profil"], (0, 1.5))
            vues = [it["vue_m"]] + ([it["vue_m_fin"]] if "vue_m_fin" in it else [])
            if it["role"] == "courant" and not all(lo - 1e-6 <= v <= hi + 1e-6 for v in vues):
                err.append(f"{p['id']} : vue {vues} hors plage {it['profil']} {lo}-{hi}")
        prec = -1.0
        for a in p["abaisses"]:
            abaisses[a["id"]] = p["id"]
            if a["s0"] < -1e-6 or a["s1"] > L + 0.01 or a["s1"] <= a["s0"]:
                err.append(f"{a['id']} : intervalle {a['s0']}-{a['s1']} hors [0, {L}]")
            if a["s0"] < prec - 1e-6:
                err.append(f"{a['id']} : chevauche l'abaissé précédent")
            prec = a["s1"]
            for r in a["raccords"]:
                if r["s0"] < -1e-6 or r["s1"] > L + 0.01:
                    err.append(f"{a['id']} : chartière hors bordure")
            if a["type"] == "traversee" and a["vue_m"] > 0.02 + 1e-6:
                err.append(f"{a['id']} : vue de traversée {a['vue_m']} > 0,02 m (arrêté du 15/01/2007)")
    kids = {f["properties"]["id"] for f in couches["bordures"]}
    iids = {f["properties"]["id"] for f in couches["ilots"]}
    sids = {f["properties"]["id"] for f in couches["surfaces"]}
    for fam in ("surfaces", "ilots", "ponctuels_sol"):
        for f in couches[fam]:
            p, g = f["properties"], f["geometry"]
            for poly in anneaux_de(g):
                for k, r in enumerate(poly):
                    if r[0][:2] != r[-1][:2] or len(r) < 4:
                        err.append(f"{p['id']} : anneau non fermé ou dégénéré")
                    if (k == 0 and aire(r) <= 0) or (k > 0 and aire(r) >= 0):
                        err.append(f"{p['id']} : orientation d'anneau non conforme RFC 7946")
                    if not dans_e(r):
                        err.append(f"{p['id']} : hors emprise de la zone pilote")
    for f in couches["surfaces"]:
        p = f["properties"]
        for b in p["bords"]:
            if b["bordure"] not in kids:
                err.append(f"{p['id']} : bord {b['bordure']} inconnu")
        for i in p["ilots"]:
            if i not in iids:
                err.append(f"{p['id']} : îlot {i} inconnu")
        if p["revetement"]["materiau_id"] not in mats:
            err.append(f"{p['id']} : materiau_id absent de la table")
    for f in couches["ilots"]:
        p = f["properties"]
        for k in p["ceinture"]:
            if k not in kids:
                err.append(f"{p['id']} : ceinture {k} inconnue")
        for s in p["surface"]:
            if s not in sids:
                err.append(f"{p['id']} : surface {s} inconnue")
        r = p["remplissage"]
        if r["materiau_id"] not in mats:
            err.append(f"{p['id']} : materiau_id absent de la table")
        if r["materiau_id"] in ("brf_bois_concasse", "gravier_concasse_6_10") and not 0.03 <= r["retrait_sous_bordure_m"] <= 0.05:
            err.append(f"{p['id']} : remplissage {r['retrait_sous_bordure_m']} m sous la bordure (attendu 0,03-0,05)")
    for f in couches["ponctuels_sol"]:
        p = f["properties"]
        a = p["ancrage"]
        if a["bordure"] not in kids:
            err.append(f"{p['id']} : bordure d'ancrage {a['bordure']} inconnue")
        if a.get("abaisse") and abaisses.get(a["abaisse"]) != a["bordure"]:
            err.append(f"{p['id']} : abaissé d'ancrage {a.get('abaisse')} absent de {a['bordure']}")
        if p["materiau_id"] not in mats:
            err.append(f"{p['id']} : materiau_id absent de la table")
    return err, warn


def valider_dossier(dossier):
    dossier = Path(dossier)
    schema = lire_json(SCHEMA)
    v = Validateur(schema)
    err = []
    couches = {}
    for fam in ("bordures", "surfaces", "ilots", "ponctuels_sol"):
        d = lire_json(dossier / "base" / f"{fam}.geojson")
        err += [f"[{fam}] {e}" for e in v.valider(d, schema["$defs"][f"collection_{fam}"], fam)]
        couches[fam] = d["features"]
    for fam in ("marquages", "marquages_correspondance"):      # schéma 0.2 (famille optionnelle)
        f = dossier / "base" / f"{fam}.geojson"
        if f.exists():
            d = lire_json(f)
            err += [f"[{fam}] {e}" for e in v.valider(d, schema["$defs"][f"collection_{fam}"], fam)]
            couches[fam] = d["features"]
    man = dossier / "description_scene_v2.json"
    if man.exists():
        err += [f"[manifeste] {e}" for e in v.valider(lire_json(man), schema, "manifeste")]
    else:
        err.append("[manifeste] description_scene_v2.json absent")
    e2, w2 = controles(couches)
    if "marquages" in couches:
        import marquages_controles
        e3, w3 = marquages_controles.controles(couches["marquages"], couches.get("marquages_correspondance", []))
        e2, w2 = e2 + [f"[marquages] {e}" for e in e3], w2 + w3
    return err + [f"[controle] {e}" for e in e2], w2, {k: len(x) for k, x in couches.items()}


def main():
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE
    err, warn, n = valider_dossier(dossier)
    print(f"description v2 : {n}")
    for w in warn:
        print("  avertissement :", w)
    if err:
        print(f"{len(err)} erreur(s) :")
        for e in err[:200]:
            print("  -", e)
        sys.exit(1)
    print("valide : schéma description_scene_v2 (0.1 / 0.2) + contrôles géométriques")


if __name__ == "__main__":
    main()
