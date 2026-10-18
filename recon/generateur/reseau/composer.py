# -*- coding: utf-8 -*-
"""Composition de plusieurs sites de Meylan en une seule scène (lot N1, option « composer »).

    python -B recon/generateur/reseau/resoudre_reseau.py --composer a41
    python -B recon/generateur/reseau/resoudre_reseau.py --composer paquet_jardin,axe_verdun_centre

Chaque site (`recon/generateur/meylan/<site>/description.yaml`) est d'abord résolu seul (nœuds partagés du réseau
commun `meylan/reseau_meylan.yaml`), puis ramené dans le repère de la composition (origine du premier site, ou celle
de la composition). Les identifiants de tronçons, carrefours, giratoires et bretelles sont préfixés par l'alias du site
(références des branches, îlots, phases de feux, guidage, véhicules et bretelles comprises). Les matériaux, marquages
et la confiance de chaque site deviennent ceux de ses tronçons.

Continuité : aux nœuds partagés, les tronçons qui se suivent sont fusionnés en une seule route (`fusion.py`) : pas de
couture de bordure, de marquage ni de sol au raccord. Les nœuds partagés de valence ≥ 3 sans carrefour (divergences,
convergences, chaussées séparées) sont rapportés.
"""
from __future__ import annotations

import copy
import re
from pathlib import Path

import fusion as FU
import resoudre_reseau as RR
from resoudre_reseau import ErreurReseau, MEYLAN, D, YE, yaml_simple, _r

CLES_TR_PORTEES = ("profil", "evenements", "vegetation", "objets", "signalisation", "abords")


def alias(site: str, table: dict) -> str:
    if site in table:
        return str(table[site])
    return "".join(m[0] for m in re.split(r"[_\W]+", site) if m)[:4] or site[:4]


def troncons_de(exact: dict) -> list:
    """Tronçons explicites d'une description exacte : chacun porte sa géométrie, son profil, ses évènements, ses
    panneaux, ses abords, son contexte, ses matériaux, ses marquages et sa confiance."""
    out = []
    racine_ctx = dict(exact.get("contexte") or {})
    if exact.get("troncons"):
        for k, t in enumerate(exact["troncons"]):
            t = copy.deepcopy(t)
            for c in CLES_TR_PORTEES:
                if t.get(c) is None and exact.get(c) is not None:
                    t[c] = copy.deepcopy(exact[c])
            t.setdefault("id", f"T{k + 1}")
            out.append(t)
    else:
        g = dict(exact.get("troncon") or {k: exact[k] for k in ("trace", "polyligne", "longueur", "depart", "cap", "de",
                                                                "vers") if k in exact})
        t = copy.deepcopy(g)
        for c in CLES_TR_PORTEES + ("nom",):
            if exact.get(c) is not None:
                t[c] = copy.deepcopy(exact[c])
        t.setdefault("id", "T1")
        out.append(t)
    for t in out:
        t["contexte"] = dict(racine_ctx, **(t.get("contexte") or {}))
        for c in ("materiaux", "marquages", "confiance"):
            if t.get(c) is None and exact.get(c) is not None:
                t[c] = copy.deepcopy(exact[c])
    return out


def _decaler_geom(t: dict, dx: float, dy: float):
    def p(v):
        return [_r(float(v[0]) + dx), _r(float(v[1]) + dy)]
    for k in ("de", "vers", "depart"):
        if isinstance(t.get(k), list):
            t[k] = p(t[k])
    if t.get("polyligne"):
        t["polyligne"] = [p(v) for v in t["polyligne"]]


def composer(nom: str, reseau: Path | None = None):
    """(texte YAML exact, dict exact, rapport, octets d'entrée, source)."""
    reseau = Path(reseau) if reseau else MEYLAN / "reseau_meylan.yaml"
    R = RR.charger_yaml(reseau) if reseau.exists() else {}
    comps = (R.get("compositions") or {})
    spec = dict(comps.get(nom) or {})
    sites = spec.get("sites") or [s.strip() for s in nom.split(",") if s.strip()]
    if not sites or (not spec and len(sites) == 1 and sites[0] == nom and not (MEYLAN / nom).is_dir()):
        raise ErreurReseau(f"composition « {nom} » inconnue ({', '.join(comps)})")
    table = R.get("alias") or {}
    octets = b""
    parts = []
    for site in sites:
        f = MEYLAN / site / "description.yaml"
        if not f.exists():
            raise ErreurReseau(f"site « {site} » : {f} introuvable")
        o = f.read_bytes()
        octets += o
        d = yaml_simple.charger(o.decode("utf-8"))
        src = str(f.relative_to(RR.DEPOT)).replace("\\", "/")
        if RR.est_reseau(d):
            ex, rp = RR.resoudre_dict(d, src, f.parent, commun=R if R else None)
        else:
            ex, rp = d, {"troncons": {}, "noeuds": {}}
        parts.append((site, alias(site, table), ex, rp))
    o0 = [float(x) for x in (spec.get("origine") or parts[0][2].get("origine") or D.ORIGINE_DEPOT)]
    if len(o0) == 2:
        o0.append(D.ORIGINE_DEPOT[2])
    rap = {"version": RR.VERSION, "composition": nom, "sites": [], "origine": o0, "fusions": [],
           "noeuds_non_fusionnes": [], "avertissements": [], "approximations": [], "noeuds": {}, "troncons": {}}
    troncons, objets = [], {"carrefours": [], "giratoires": [], "bretelles": []}
    ecarts, dates, fins, bloques = {}, {}, {}, set()
    for site, al, ex, rp in parts:
        o = [float(x) for x in (ex.get("origine") or D.ORIGINE_DEPOT)]
        dx, dy = o[0] - o0[0], o[1] - o0[1]
        ren = {}
        for t in troncons_de(ex):
            nid = f"{al}_{t['id']}"
            info = (rp.get("troncons") or {}).get(str(t["id"])) or {}
            ren[str(t["id"])] = nid
            _decaler_geom(t, dx, dy)
            t["id"] = nid
            troncons.append(t)
            for bout in ("de", "vers"):
                if info.get(bout):
                    fins.setdefault(info[bout], []).append((nid, bout))
        for cle in objets:
            for c in ex.get(cle) or []:
                c2 = FU.renommer_ref(copy.deepcopy(c), ren)
                if c2.get("id") is not None:
                    c2["id"] = f"{al}_{c2['id']}"
                for k in ("centre", "point"):
                    if isinstance(c2.get(k), list):
                        c2[k] = [_r(float(c2[k][0]) + dx), _r(float(c2[k][1]) + dy)]
                objets[cle].append(c2)
        for n, inf in (rp.get("noeuds") or {}).items():
            if inf.get("carrefour"):
                bloques.add(n)
            rap["noeuds"].setdefault(n, {}).update({k: v for k, v in inf.items() if k != "troncons"})
        for r_, m in (ex.get("ecarts_admis") or {}).items():
            ecarts.setdefault(r_, []).append(f"{site} : {m}")
        if ex.get("date"):
            dates[site] = str(ex["date"])
        rap["sites"].append({"site": site, "alias": al, "origine": o, "date_etat": ex.get("date"),
                             "troncons": list(ren.values()), "fusions_internes": rp.get("fusions") or []})
        rap["avertissements"] += [f"{site} : {w}" for w in rp.get("avertissements") or []]
        rap["approximations"] += [dict(a, site=site) for a in rp.get("approximations") or []]
    trs = FU.fusionner_aux_noeuds(troncons, fins, bloques, o0, objets, rap)
    for t in trs:
        rap["troncons"][t["id"]] = {"longueur_m": _r(FU.longueur(t, o0), 2)}
    titre = spec.get("titre") or " + ".join(s for s, *_ in parts)
    date = str(spec["date"]) if spec.get("date") else (max(dates.values()) if dates else None)
    if len(set(dates.values())) > 1:
        rap["avertissements"].append(f"dates d'état différentes selon les sites : {dates} ; la scène composée porte "
                                     f"{date} (chaque site garde sa date d'état, à lire site par site)")
    out = {"format": RR.FORMAT_ETAPE2, "scene": spec.get("scene") or f"meylan_composition_{nom.replace(',', '_')}",
           "titre": f"Composition de sites de Meylan : {titre}"}
    if date:
        out["date"] = date
    out.update({"confiance": "moyenne", "origine": [_r(x) for x in o0],
                "description": f"Scène composée par recon/generateur/reseau/composer.py : {', '.join(sites)}.",
                "contexte": dict(parts[0][2].get("contexte") or {}), "troncons": trs})
    for cle in objets:
        if objets[cle]:
            out[cle] = objets[cle]
    if ecarts:
        out["ecarts_admis"] = {r_: " | ".join(ms) for r_, ms in sorted(ecarts.items())}
    texte = YE.ecrire(out, entete=f"Composition « {nom} » résolue par recon/generateur/reseau/composer.py ; ne pas modifier "
                                  "à la main.")
    YE.verifier_aller_retour(out, texte)
    rap["dates_etat"] = dates
    return texte, out, rap, octets, f"composition:{nom}"
