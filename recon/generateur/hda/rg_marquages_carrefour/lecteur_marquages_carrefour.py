"""Lecture des données de marquage des carrefours du modèle modele_voie/0.1 (module Python de l'HDA
rg::marquages_carrefour ; entrées-sorties seulement, aucune opération géométrique).

Python SOP « lecture » : les valeurs du modèle utiles au lot L4 sont rangées en attributs de points (aucune position
calculée ici : la géométrie vient du SOLVEUR de rg::carrefours, des NIVEAUX et des références échantillonnées).

  points du groupe « br4 » (une branche de carrefour plan) : carrefour, branche, route, extremite, regime, ligne_type,
      ligne_distance, sas_prof (0 sans sas), sas_acces, entrantes[], sortantes[] (bandes du modèle), bandes_ids[],
      bandes_types[], bandes_sens[] (profil de la section qui porte s_frontiere_m), agglomeration
  points du groupe « fl » (une consigne de flèches d'une voie) : carrefour, branche, route, bande, gabarit, nombre,
      intervalle, recul, regles
  points du groupe « mv » (un mouvement autorisé = une trajectoire du modèle) : id, carrefour, de_branche, de_bande,
      vers_branche, vers_bande, mouvement, guide (guidage.materialise), guide_mod, guide_larg, priorite, phases[]
      (phases vertes du contrôleur, déduites des feux R11 dont l'applicabilité porte la voie d'entrée)
Détail : rg_l4_modele (fichier, sha256, comptes).
"""
import hashlib
import json

import hou


def _hda(sop):
    n = sop
    while n is not None and n.type().definition() is None:
        n = n.parent()
    return n


def _txt(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _attr(geo, nom, defaut):
    if geo.findPointAttrib(nom) is None:
        geo.addArrayAttrib(hou.attribType.Point, nom, hou.attribData.String, 1) if isinstance(defaut, list) else \
            geo.addAttrib(hou.attribType.Point, nom, defaut)


def _profil_en(m, rid, s):
    r = next((x for x in m.get("routes", []) if x["id"] == rid), None)
    if r is None:
        return None
    secs = [x for x in r.get("sections", []) if float(x.get("s0", 0.0)) <= s + 1e-9] or r.get("sections", [])[:1]
    pid = secs[-1]["profil"] if secs else None
    return next((p for p in m.get("profils", []) if p["id"] == pid), None)


def _phases(m, cid):
    """{(branche, bande): [phases]} : phases « … vert » du contrôleur du carrefour ; un feu R11 vert y autorise les
    voies de son applicabilité (données du modèle seulement)."""
    sig = {s["id"]: s for s in m.get("signaux", [])}
    out = {}
    for c in m.get("controleurs", []):
        if c.get("carrefour") != cid:
            continue
        for ph in c.get("phases", []):
            nom = str(ph.get("nom", ""))
            if not nom.endswith(" vert"):
                continue
            base = nom[:-5]
            for sid, etat in (ph.get("etats") or {}).items():
                s = sig.get(sid)
                if etat != "vert" or s is None or not str(s.get("code", "")).startswith("R11"):
                    continue
                ap = s.get("applicabilite") or {}
                for b in ap.get("bandes", []):
                    k = (ap.get("branche", ""), b)
                    if base not in out.setdefault(k, []):
                        out[k].append(base)
    return out


def lire(sop):
    hda = _hda(sop)
    chemin = hda.evalParm("fichier")
    brut = open(chemin, "rb").read()
    m = json.loads(brut.decode("utf-8"))
    geo = sop.geometry()
    for nom, d in (("carrefour", ""), ("branche", ""), ("route", ""), ("extremite", ""), ("regime", ""),
                   ("ligne_type", ""), ("sas_acces", ""), ("bande", ""), ("gabarit", ""), ("regles", ""), ("id", ""),
                   ("de_branche", ""), ("de_bande", ""), ("vers_branche", ""), ("vers_bande", ""), ("mouvement", ""),
                   ("guide_mod", "")):
        _attr(geo, nom, d)
    for nom in ("ligne_distance", "sas_prof", "intervalle", "recul", "guide_larg"):
        _attr(geo, nom, 0.0)
    for nom in ("nombre", "guide", "priorite", "agglomeration"):
        _attr(geo, nom, 0)
    for nom in ("entrantes", "sortantes", "bandes_ids", "bandes_types", "bandes_sens", "phases"):
        _attr(geo, nom, [])
    g_br = geo.createPointGroup("br4")
    g_fl = geo.createPointGroup("fl")
    g_mv = geo.createPointGroup("mv")
    comptes = {"branches": 0, "fleches": 0, "mouvements": 0, "guides": 0}
    agglo = {r["id"]: (1 if r.get("agglomeration", True) else 0) for r in m.get("routes", [])}
    for c in m.get("carrefours", []):
        if c.get("type") in ("giratoire", "mini_giratoire", "bifurcation"):
            continue                                   # lots giratoires et autoroutes
        cid = c["id"]
        phases = _phases(m, cid)
        for b in sorted(c["branches"], key=lambda x: float(x.get("azimut_deg", 0.0)) % 360.0):
            p = geo.createPoint()
            g_br.add(p)
            comptes["branches"] += 1
            la = b.get("ligne_arret") or {}
            sas = b.get("sas_velo") or {}
            pr = _profil_en(m, b["route"], float(b.get("s_frontiere_m", 0.0)) - 1e-3) or {"bandes": []}
            for k, v in (("carrefour", cid), ("branche", b["id"]), ("route", b["route"]),
                         ("extremite", b.get("extremite", "")), ("regime", b.get("regime", "")),
                         ("ligne_type", la.get("type", "")), ("sas_acces", sas.get("bande_acces", ""))):
                p.setAttribValue(k, str(v))
            p.setAttribValue("ligne_distance", float(la.get("distance_m", 0.0) or 0.0))
            p.setAttribValue("sas_prof", float(sas.get("profondeur_m", 0.0) or 0.0))
            p.setAttribValue("agglomeration", agglo.get(b["route"], 1))
            p.setAttribValue("entrantes", [str(x) for x in b.get("bandes_entrantes", [])])
            p.setAttribValue("sortantes", [str(x) for x in b.get("bandes_sortantes", [])])
            p.setAttribValue("bandes_ids", [str(x["id"]) for x in pr["bandes"]])
            p.setAttribValue("bandes_types", [str(x.get("type", "")) for x in pr["bandes"]])
            p.setAttribValue("bandes_sens", [str(x.get("sens", "")) for x in pr["bandes"]])
            for f in b.get("fleches", []) or []:
                q = geo.createPoint()
                g_fl.add(q)
                comptes["fleches"] += 1
                for k, v in (("carrefour", cid), ("branche", b["id"]), ("route", b["route"]),
                             ("bande", f.get("bande", "")), ("gabarit", "_".join(f.get("types", []))),
                             ("regles", " ".join(x for x in [f.get("regle", ""), "DEF-017", "ARB-11"] if x))):
                    q.setAttribValue(k, str(v))
                q.setAttribValue("nombre", int(f.get("nombre", 3)))
                q.setAttribValue("intervalle", float(f.get("intervalle_m", 20.0)))
                q.setAttribValue("recul", float(f.get("recul_derniere_m", 1.5)))
        for t in c.get("trajectoires", []):
            de = t.get("de") or {}
            ve = t.get("vers") or {}
            q = geo.createPoint()
            g_mv.add(q)
            comptes["mouvements"] += 1
            gd = t.get("guidage") or {}
            for k, v in (("id", t["id"]), ("carrefour", cid), ("de_branche", de.get("branche", "")),
                         ("de_bande", de.get("bande", "")), ("vers_branche", ve.get("branche", "")),
                         ("vers_bande", ve.get("bande", "")), ("mouvement", t.get("mouvement", "")),
                         ("guide_mod", gd.get("modulation", "") if gd.get("materialise") else "")):
                q.setAttribValue(k, str(v))
            q.setAttribValue("guide", 1 if gd.get("materialise") else 0)
            comptes["guides"] += 1 if gd.get("materialise") else 0
            q.setAttribValue("guide_larg", float(gd.get("largeur_m", 0.0) or 0.0))
            q.setAttribValue("priorite", int(t.get("priorite", 0) or 0))
            q.setAttribValue("phases", phases.get((de.get("branche", ""), de.get("bande", "")), []))
    geo.addAttrib(hou.attribType.Global, "rg_l4_modele", "")
    geo.setGlobalAttribValue("rg_l4_modele", _txt({"fichier": chemin.replace("\\", "/"),
                                                    "sha256": hashlib.sha256(brut).hexdigest(), **comptes}))
