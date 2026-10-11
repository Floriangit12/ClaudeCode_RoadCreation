"""Comparaison de la résolution courante avec la résolution précédente (référence figée
resolue/historique/journal_resolution_r1.json : 279 modifications, cohérence v2 et revue v2).

Clé d'une modification : (famille, identifiant, nature, attribut mis à jour). Une modification est « nouvelle » (absente de r1),
« retirée » (présente en r1, plus appliquée), « modifiée » (même clé, valeur après différente) ou « inchangée ».
Chaque modification retirée est rattachée à la raison courante (entité non résolue ou décision confirmée), ce qui
rend visibles les retours arrière (R5 de la revue v3).
"""
import json


def _cle(e):
    """(famille, id, nature, attribut) : plusieurs attributs d'une même entité sont des modifications distinctes."""
    attr = ",".join(sorted((e.get("apres") or {}).keys())) if e["nature"] == "attribut" and isinstance(e.get("apres"), dict) else ""
    return (e["famille"], e["id"], e["nature"], attr)


def _same(a, b):
    return json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False)


def _court(v):
    if not isinstance(v, dict):
        return v
    out = {}
    for k in ("xy_local", "d_m", "azimut_deg", "fabrication", "pose_point_l93", "instancier", "statut_2026", "interruptions",
              "porte_par"):
        if k in v:
            out[k] = v[k]
    return out or v


def comparer(r1, J):
    if r1 is None:
        return None
    A = {_cle(e): e for e in r1["appliquees"]}
    B = {_cle(e): e for e in J.appliquees}
    raisons = {}
    for e in J.non_resolues:
        raisons.setdefault(e["id"], []).append(f"non résolu ({e['nature']}, {e['origine']}) : {e['motif'][:220]}")
    for e in J.confirmees:
        raisons.setdefault(e["id"], []).append(f"confirmé ({e['nature']}) : {e['motif'][:220]}")
    nouvelles, retirees, modifiees = [], [], []
    for k in sorted(set(B) - set(A)):
        e = B[k]
        nouvelles.append({"famille": k[0], "id": k[1], "nature": k[2], "attribut": k[3] or None, "apres": _court(e["apres"]), "regles": e["regles"],
                          "motif": e["motif"][:240]})
    for k in sorted(set(A) - set(B)):
        e = A[k]
        retirees.append({"famille": k[0], "id": k[1], "nature": k[2], "attribut": k[3] or None, "apres_r1": _court(e["apres"]),
                         "raison": (raisons.get(k[1]) or ["décision non reconduite"])[0]})
    for k in sorted(set(A) & set(B)):
        if not _same(A[k]["apres"], B[k]["apres"]):
            modifiees.append({"famille": k[0], "id": k[1], "nature": k[2], "attribut": k[3] or None, "apres_r1": _court(A[k]["apres"]),
                              "apres": _court(B[k]["apres"]), "regles": B[k]["regles"], "motif": B[k]["motif"][:240]})
    for k, e in B.items():
        e["comparaison_r1"] = ("nouvelle" if k not in A else
                               ("modifiee" if not _same(A[k]["apres"], e["apres"]) else "inchangee"))
    na = {(e["famille"], e["id"], e["nature"]) for e in r1["non_resolues"]}
    nb = {(e["famille"], e["id"], e["nature"]) for e in J.non_resolues}
    st_a, st_b = {}, {}
    for e in r1["non_resolues"]:
        s = (e.get("station") or {}).get("station") or "sans position"
        st_a[s] = st_a.get(s, 0) + 1
    for e in J.non_resolues:
        s = (e.get("station") or {}).get("station") or "sans position"
        st_b[s] = st_b.get(s, 0) + 1
    return {
        "reference": "resolue/historique/journal_resolution_r1.json",
        "appliquees_r1": len(A), "appliquees": len(B),
        "nouvelles": nouvelles, "retirees": retirees, "modifiees": modifiees,
        "inchangees": len(set(A) & set(B)) - len(modifiees),
        "non_resolues_r1": len(na), "non_resolues": len(nb),
        "non_resolues_sorties": len(na - nb), "non_resolues_entrees": len(nb - na),
        "non_resolues_par_station_r1": dict(sorted(st_a.items())), "non_resolues_par_station": dict(sorted(st_b.items())),
    }
