"""Description RÉSOLUE du site Paquet Jardin : base 0.3 + décisions prouvées seulement.

Usage :
    python recon/pcg/decrire/resoudre.py [--sortie DOSSIER] [--sans-planches] [--sans-validation] [--forcer]

Entrées (lecture seule) : description/base (schéma 0.3), objets du paquet v1, description/enrichi (fusion 0.3),
description/coherence (cohérence v2), revues adverses (resoudre_revue.py), PROTOCOLE_TERRAIN.md (stations).
Sorties (défaut recon/out/paquet_jardin/v2/description/resolue) :
    description_scene_v2.json        manifeste 0.3 (couches, sha256, hash, statistiques.resolution)
    base/*.geojson, base/nivellement* même schéma que description/base : pj::lire_description lit
                                     resolue/base au lieu de base (paramètre « dossier »)
    objets/{mobilier,arbres}.geojson objets du paquet résolus (même schéma + propriété resolution) et ajouts
    objets/vegetation_ajouts.geojson haies et massifs ajoutés ; objets/ponctuels_sol_ajouts.geojson tampons, avaloirs
    journal_resolution.json          chaque décision appliquée (avant, après, observations, règles, revue) et chaque
                                     entité non résolue (motif, station terrain)
    modifications.geojson, non_resolus.geojson   couches de contrôle (L93)
    planches/*.jpg                   avant / après sur l'ortho 2022 des 15 changements les plus significatifs
    REPORT.md
Déterministe : aucune date d'exécution, tris par identifiant, flottants arrondis ; deux exécutions donnent des
fichiers identiques à l'octet. Garde de validation : une entité dont la modification fait échouer valider.py est
remise dans son état de base et listée (origine « validation »).
"""
import argparse
import collections
import copy
import hashlib
import json
import platform
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import MNT, O, RACINE, SORTIE, arrondi, ecrire_geojson, ecrire_json, rel, sha256  # noqa: E402
import resoudre_regles as RR  # noqa: E402
import resoudre_revue as RV  # noqa: E402
from resoudre_ajouts import ResolveurAjouts  # noqa: E402
from resoudre_journal import Contexte, Journal  # noqa: E402
from resoudre_marquages import ResolveurMarquages  # noqa: E402
from resoudre_objets import ResolveurObjets, _xy  # noqa: E402
from resoudre_sol import ResolveurSol  # noqa: E402
import resoudre_sources as RS  # noqa: E402

ICI = Path(__file__).resolve().parent
SORTIE_RESOLUE = SORTIE / "resolue"
SCRIPTS = ["resoudre.py", "resoudre_sources.py", "resoudre_regles.py", "resoudre_revue.py", "resoudre_journal.py",
           "resoudre_objets.py", "resoudre_marquages.py", "resoudre_sol.py", "resoudre_ajouts.py", "resoudre_planches.py",
           "resoudre_rapport.py"]
SCHEMA_JOURNAL = "pj_resolution/0.1"


def _entete(src_fc, modifie):
    e = dict(src_fc.get("description_v2") or {})
    if modifie:
        e["resolution"] = "description résolue (recon/pcg/decrire/resoudre.py) : base 0.3 + décisions prouvées ; " \
                          "journal ../journal_resolution.json"
    return e


def _sha_texte(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def resoudre(sortie, bloques=frozenset(), forcer=False):
    S = RS.Sources()
    chaine = S.chaine()
    if chaine and not forcer:
        raise SystemExit("RES-CHN-001 : la cohérence ou la fusion n'ont pas lu la base courante :\n  " + "\n  ".join(chaine)
                         + "\nrelancer fusion_recensement.py puis coherence.py, ou --forcer pour un essai")
    J = Journal()
    ctx = Contexte(S.base["surfaces"]["features"], S.base["bordures"]["features"])
    mnt = MNT()
    ro = ResolveurObjets(S, J, ctx)
    mob, arb = ro.executer()
    rm = ResolveurMarquages(S, J, ctx)
    nouveaux_mq = rm.executer(S.ajouts)
    rs = ResolveurSol(S, J)
    xy_obj = {i: _xy(f) for i, (fam, f) in ro.obj.items()}
    rs.executer(xy_obj)
    ra = ResolveurAjouts(S, J, ctx, mnt)
    arb_aj, mob_aj, veg, ponct = ra.executer()
    # ------------------------------------------------------------------ garde de validation : retour à la base
    if bloques:
        brut = {}
        for fam in RS.FAMILLES_BASE:
            for f in S.base_brut[fam]["features"]:
                brut[f["properties"]["id"]] = (fam, f)
        for fam in ("marquages", "surfaces", "ilots", "bordures", "ponctuels_sol"):
            fc = S.base[fam]
            out = []
            for f in fc["features"]:
                i = f["properties"]["id"]
                if i in bloques:
                    if i in brut:
                        out.append(copy.deepcopy(brut[i][1]))
                    continue
                out.append(f)
            fc["features"] = out
        restes = []
        for e in J.appliquees:
            if e["id"] in bloques and e["famille"] in ("marquages", "surfaces", "ilots", "bordures", "ponctuels_sol"):
                J.non_resolu(e["id"], e["famille"], e["nature"], origine="validation", xy=e.get("xy_apres_local"),
                             regles=e["regles"] + ["RES-SRC-001"], observations=e["observations"], revue=e.get("revue"),
                             proposition={"avant": e["avant"], "apres": e["apres"]}, classe=e.get("classe"),
                             motif="modification retirée : la description résolue ne passait plus valider.py")
            else:
                restes.append(e)
        J.appliquees = restes
    affecter_stations(J)
    J.trier()
    # ------------------------------------------------------------------ écriture
    sortie = Path(sortie)
    (sortie / "base").mkdir(parents=True, exist_ok=True)
    (sortie / "objets").mkdir(parents=True, exist_ok=True)
    modifiees = {e["famille"] for e in J.appliquees}
    info = {}
    for fam in RS.FAMILLES_BASE:
        dst = sortie / "base" / f"{fam}.geojson"
        src = RS.BASE / f"{fam}.geojson"
        if fam in modifiees or (fam == "marquages" and nouveaux_mq):
            fc = S.base[fam]
            ecrire_geojson(dst, fc["features"], fc["name"], _entete(fc, True))
        else:
            shutil.copyfile(src, dst)
        info[fam] = {"fichier": f"base/{fam}.geojson", "n": len(S.base[fam]["features"]), "sha256": sha256(dst)}
    man0 = S.manifeste
    for nom in RS.FICHIERS_COPIES:
        src = RS.BASE / nom
        dst = sortie / "base" / nom
        shutil.copyfile(src, dst)
        cle = nom.split(".")[0]
        if cle in man0["couches"]:
            info[cle] = dict(man0["couches"][cle], sha256=sha256(dst))
    ent_obj = {"schema": "pj_objets_resolus/0.1", "famille": "objets", "zone_pilote": "ZP-01",
               "repere": "EPSG:2154 ; local = L93 - (917279.43, 6460289.98) ; z = NGF - 216,30",
               "source": "recon/out/paquet_jardin/package/donnees/objets (paquet v1) + resolution",
               "resolution": "propriété resolution.decisions sur chaque objet modifié ; journal ../journal_resolution.json"}
    sorties_obj = {}
    for nom, feats in (("mobilier", mob + mob_aj), ("arbres", arb + arb_aj), ("vegetation_ajouts", veg),
                       ("ponctuels_sol_ajouts", ponct)):
        dst = sortie / "objets" / f"{nom}.geojson"
        ecrire_geojson(dst, feats, nom, dict(ent_obj, famille=nom))
        sorties_obj[nom] = {"fichier": f"objets/{nom}.geojson", "n": len(feats), "sha256": sha256(dst)}
    # ------------------------------------------------------------------ couches de contrôle
    mods, nres = [], []
    for k, e in enumerate(J.appliquees):
        a, b = e.get("xy_avant_local"), e.get("xy_apres_local")
        if b is None:
            continue
        if a is not None and np.hypot(a[0] - b[0], a[1] - b[1]) > 0.005:
            g = {"type": "LineString", "coordinates": [[round(a[0] + O[0], 3), round(a[1] + O[1], 3)],
                                                       [round(b[0] + O[0], 3), round(b[1] + O[1], 3)]]}
        else:
            g = {"type": "Point", "coordinates": [round(b[0] + O[0], 3), round(b[1] + O[1], 3)]}
        mods.append({"type": "Feature", "geometry": g,
                     "properties": {"id": f"{e['famille']}:{e['id']}:{e['nature']}:{k:04d}", "entite": e["id"],
                                    "famille": e["famille"], "nature": e["nature"], "regles": e["regles"], "conf": e["conf"],
                                    "portee": e["portee"], "motif": e["motif"][:200]}})
    for k, e in enumerate(J.non_resolues):
        xy = e.get("xy_local")
        if xy is None:
            continue
        nres.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [round(xy[0] + O[0], 3), round(xy[1] + O[1], 3)]},
                     "properties": {"id": f"{e['famille']}:{e['id']}:{e['nature']}:{k:04d}", "entite": e["id"],
                                    "famille": e["famille"], "nature": e["nature"], "origine": e["origine"],
                                    "station": (e["station"] or {}).get("station"), "motif": e["motif"][:200]}})
    ecrire_geojson(sortie / "modifications.geojson", mods, "modifications",
                   {"schema": SCHEMA_JOURNAL, "famille": "modifications", "zone_pilote": "ZP-01"})
    ecrire_geojson(sortie / "non_resolus.geojson", nres, "non_resolus",
                   {"schema": SCHEMA_JOURNAL, "famille": "non_resolus", "zone_pilote": "ZP-01"})
    # ------------------------------------------------------------------ journal
    comptes = J.comptes()
    journal = {
        "schema": SCHEMA_JOURNAL,
        "site": "paquet_jardin", "etat": "2026-10",
        "repere": "local = L93 - (917279.43, 6460289.98), z = NGF - 216.30",
        "commande": "python recon/pcg/decrire/resoudre.py",
        "regles": RR.REGLES,
        "seuils": {"double_lecture_m": RR.SEUIL_DOUBLE_LECTURE_M, "sigma_max_ajout_m": RR.SIGMA_MAX_AJOUT,
                   "sigma_max_marquage_ajout_m": RR.SIGMA_MAX_MARQUAGE_AJOUT, "tranches_probantes": sorted(RR.TRANCHES_PROBANTES),
                   "deplace_travaux_m": RR.DEPLACE_TRAVAUX_M, "fin_travaux": RR.FIN_TRAVAUX},
        "revues": {"revue_v2": {"id": RV.REVUE_V2_ID, "dossier_preuves": RV.REVUE_V2_DOSSIER, "verdicts": RV.REVUE_V2},
                   "revue_v1": {"id": RV.REVUE_V1_ID, "verdicts": RV.REVUE_V1},
                   "seconde_lecture": {"id": RV.RELECTURE_ID, "lectures": RV.RELECTURE}},
        "entrees": S.empreintes,
        "chaine": {"ecarts": chaine, "forcee": bool(chaine and forcer)},
        "validation_bloques": sorted(bloques),
        "comptes": comptes,
        "appliquees": J.appliquees,
        "non_resolues": J.non_resolues,
    }
    ecrire_json(sortie / "journal_resolution.json", arrondi(journal))
    # ------------------------------------------------------------------ manifeste 0.3
    man = copy.deepcopy(man0)
    man["couches"] = {k: info[k] for k in man0["couches"] if k in info}
    man["comptes"] = dict(man0["comptes"], marquages=len(S.base["marquages"]["features"]),
                          surfaces=len(S.base["surfaces"]["features"]), ilots=len(S.base["ilots"]["features"]),
                          bordures=len(S.base["bordures"]["features"]))
    refs = dict(man0["references"])
    for k, v in sorted(S.empreintes.items()):
        if not k.startswith("base_"):
            refs[f"resolution_{k}"] = {"fichier": v["fichier"], "sha256": v["sha256"], "role": "entrée de la résolution"}
    refs["resolution_base_d_origine"] = {"fichier": "recon/out/paquet_jardin/v2/description/description_scene_v2.json",
                                         "sha256": S.empreintes["manifeste_base"]["sha256"],
                                         "role": "manifeste de la base résolue (hash_description d'origine "
                                                 f"{man0['hash_description']})"}
    man["references"] = dict(sorted(refs.items()))
    stats = dict(man0["statistiques"])
    stats["resolution"] = {"schema": SCHEMA_JOURNAL, "journal": "journal_resolution.json",
                           "hash_description_base": man0["hash_description"], "comptes": comptes,
                           "objets": sorties_obj, "chaine": chaine}
    man["statistiques"] = stats
    gen = dict(man0["generateur"])
    scripts = dict(gen.get("scripts", {}))
    for s in SCRIPTS:
        if (ICI / s).exists():
            scripts[f"recon/pcg/decrire/{s}"] = sha256(ICI / s)
    man["generateur"] = {"commande": "python recon/pcg/decrire/resoudre.py (base : " + gen.get("commande", "") + ")",
                         "scripts": dict(sorted(scripts.items())),
                         "interpreteur": f"CPython {platform.python_version()} ; numpy {np.__version__}"}
    sol = [k for k in sorted(info) if k in man["couches"] and not k.startswith("marquages") and k != "regularisation_sources"]
    man["hash_description"] = hashlib.sha256("".join(info[k]["sha256"] for k in sol).encode()).hexdigest()
    man["hash_marquages"] = hashlib.sha256("".join(info[k]["sha256"] for k in sorted(info)
                                                   if k.startswith("marquages") and k in man["couches"]).encode()).hexdigest()
    ecrire_json(sortie / "description_scene_v2.json", man)
    return S, J, man, journal


def affecter_stations(J):
    """Entités non résolues hors de portée des stations S1-S15 : stations à créer N1..Nk (couverture de 30 m)."""
    hors = [(f"{k:05d}", tuple(e["xy_local"])) for k, e in enumerate(J.non_resolues)
            if e.get("xy_local") is not None and str((e.get("station") or {}).get("station") or "").startswith("nouvelle")]
    grp = RR.regrouper_stations(hors)
    for k, e in enumerate(J.non_resolues):
        g = grp.get(f"{k:05d}")
        if g:
            nom, c, d = g
            e["station"] = {"station": nom, "distance_m": d, "centre_local": list(c),
                            "note": f"station à créer en ({c[0]:+.0f} ; {c[1]:+.0f}) : hors de portée de S1-S15"}


def valider_resolue(sortie):
    import valider
    err, warn, n = valider.valider_dossier(sortie)
    return err, warn, n


def ids_fautifs(err, J):
    """Identifiants modifiés par la résolution cités dans les erreurs de validation."""
    modifs = {e["id"] for e in J.appliquees}
    out = set()
    for e in err:
        for tok in e.replace(",", " ").replace(":", " ").replace("/", " ").split():
            if tok in modifs:
                out.add(tok)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", default=str(SORTIE_RESOLUE))
    ap.add_argument("--sans-planches", action="store_true")
    ap.add_argument("--sans-validation", action="store_true")
    ap.add_argument("--forcer", action="store_true", help="ignorer RES-CHN-001 (base différente de celle lue par la fusion)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    bloques = frozenset()
    for passe in range(4):
        S, J, man, journal = resoudre(a.sortie, bloques, a.forcer)
        print(f"passe {passe + 1} : {len(J.appliquees)} modifications appliquées, {len(J.non_resolues)} entités non résolues")
        if a.sans_validation:
            err, warn = [], []
            break
        err, warn, n = valider_resolue(a.sortie)
        fautifs = ids_fautifs(err, J)
        if not err:
            break
        if not fautifs - bloques:
            break
        bloques = frozenset(bloques | fautifs)
        print(f"  validation : {len(err)} erreur(s) ; entités remises à l'état de base : {sorted(fautifs)}")
    val = {"erreurs": err, "avertissements": len(warn), "bloques": sorted(bloques)}
    if not a.sans_validation:
        _, warn_base, _ = valider_resolue(SORTIE)
        val["memes_avertissements"] = sorted(warn) == sorted(warn_base)
        val["avertissements_nouveaux"] = sorted(set(warn) - set(warn_base))
        val["avertissements_disparus"] = sorted(set(warn_base) - set(warn))
    import resoudre_rapport
    import resoudre_planches
    planches = []
    if not a.sans_planches:
        planches = resoudre_planches.planches(Path(a.sortie), S, J)
    resoudre_rapport.rapport(Path(a.sortie), S, J, man, journal, val, planches)
    print(f"description résolue écrite dans {a.sortie}")
    print(f"hash_description {man['hash_description']}")
    if err:
        print(f"ÉCHEC de la validation : {len(err)} erreur(s)")
        for e in err[:50]:
            print("  -", e)
        sys.exit(1)
    if not a.sans_validation:
        print(f"validation : OK ({len(warn)} avertissements)")


if __name__ == "__main__":
    main()
