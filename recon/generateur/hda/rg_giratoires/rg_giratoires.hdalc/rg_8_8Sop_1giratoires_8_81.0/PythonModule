"""Lecture des giratoires du modèle modele_voie/0.1 (module Python de l'HDA rg::giratoires ; entrées-sorties seulement).

Python SOP « giratoires » : aucune opération géométrique ; les valeurs du modèle (carrefours de type giratoire et
mini_giratoire : anneau, raccordements, branches, îlots, passages ; profil de la route d'anneau) sont rangées en
attributs ; Lambert-93 -> local (origine du repère) -> Houdini (x, 0, −y), comme rg::lire_modele et rg::carrefours.

Géométrie produite :
  points du groupe « giratoire » : id, type, centre (local), Rg, la, Ri, slf, Ri_inf, route_anneau, ilot_central,
                                   agglomeration, sens ; bandes du profil de l'anneau (de l'intérieur vers l'extérieur :
                                   a_type[], a_ref[], a_larg[], a_mat[], a_dz[], a_devers[], a_franch[]) et limites
                                   (l_nature[], l_bord[], l_vue[], l_marq[] JSON ; premier marquage : l_mmod[],
                                   l_mlu[] largeur en u, l_mum[] u), u_m ; regles
  points du groupe « branche »   : mêmes attributs que rg::carrefours (carrefour, branche, route, extremite, s_front,
                                   azimut, rang, regime, ligne_type, passage, ilot, centre) + Re, Rs (raccordements du
                                   modèle, anneau.construction.raccordements), regle_racc, n_entrantes, n_sortantes
  points du groupe « passage »   : id, route, carrefour, s, largeur, axe0, axe1, refuge, abaisses, bev
  primitives « ilot_g »          : îlots du giratoire (polygone) : id, type, carrefour, materiau, remplissage,
                                   franchissable, ceinture, ceinture_vue, surelevation, bombement, contour (JSON),
                                   nez_rayon, refuge_largeur, refuge_traversee
Détail : rg_giratoires (fichier, sha256, comptes), anneaux (ids des routes d'anneau), giratoires (ids).
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


def _attr(geo, classe, nom, defaut):
    if classe == "point" and geo.findPointAttrib(nom) is None:
        geo.addAttrib(hou.attribType.Point, nom, defaut)
    elif classe == "prim" and geo.findPrimAttrib(nom) is None:
        geo.addAttrib(hou.attribType.Prim, nom, defaut)


def _largeur(b):
    w = b.get("largeur", 0.0)
    if isinstance(w, (int, float)):
        return float(w)
    pts = (w or {}).get("points") or []
    return float(pts[-1][1]) if pts else 0.0



def _zones_passage(m, route, s, o):
    """Zones peintes du passage d'une branche (marquages passage_pieton du modèle, un polygone par groupe de bandes)
    en local : (xy aplatis, nombre de points par zone) ; correction après le contrôle de l'étape 2 (bandes prolongées
    dans les congés de coin par rg::carrefours_sol)."""
    xy, nz, ids = [], [], []
    for x in m.get("marquages", []):
        an = x.get("ancrage") or {}
        if x.get("type") != "passage_pieton" or an.get("route") != route or an.get("s") is None:
            continue
        if abs(float(an["s"]) - float(s)) > 0.05:
            continue
        ext = list((x.get("geometrie") or {}).get("exterieur") or [])
        if len(ext) > 1 and ext[0] == ext[-1]:
            ext = ext[:-1]
        if len(ext) < 3:
            continue
        for q in ext:
            xy += [float(q[0]) - o[0], float(q[1]) - o[1]]
        nz.append(len(ext))
        ids.append(x["id"])
    return xy, nz, ids

def lire(sop):
    hda = _hda(sop)
    chemin = hda.evalParm("fichier")
    brut = open(chemin, "rb").read()
    m = json.loads(brut.decode("utf-8"))
    o = m["repere"]["origine_l93"]
    geo = sop.geometry()

    def h(q):
        return (float(q[0]) - o[0], 0.0, -(float(q[1]) - o[1]))

    def loc(q):
        return (float(q[0]) - o[0], float(q[1]) - o[1], 0.0)

    routes = {r["id"]: r for r in m.get("routes", [])}
    profils = {p["id"]: p for p in m.get("profils", [])}
    for nom, d in (("carrefour", ""), ("branche", ""), ("route", ""), ("extremite", ""), ("regle_coin", ""),
                   ("regime", ""), ("ligne_type", ""), ("passage", ""), ("ilot", ""), ("id", ""), ("refuge", ""),
                   ("type", ""), ("route_anneau", ""), ("ilot_central", ""), ("sens", ""), ("regle_racc", ""),
                   ("regles", "")):
        _attr(geo, "point", nom, d)
    for nom in ("s_front", "azimut", "rayon_coin", "ligne_distance", "s", "largeur", "Rg", "la", "Ri", "slf",
                "Ri_inf", "Re", "Rs", "u_m"):
        _attr(geo, "point", nom, 0.0)
    for nom in ("rang", "abaisses", "bev", "agglomeration", "n_entrantes", "n_sortantes"):
        _attr(geo, "point", nom, 0)
    for nom in ("centre", "axe0", "axe1"):
        _attr(geo, "point", nom, (0.0, 0.0, 0.0))
    for nom, d in (("id", ""), ("type", ""), ("carrefour", ""), ("materiau", ""), ("remplissage", ""),
                   ("franchissable", ""), ("ceinture", ""), ("contour", ""), ("refuge_traversee", "")):
        _attr(geo, "prim", nom, d)
    for nom in ("ceinture_vue", "surelevation", "bombement", "nez_rayon", "refuge_largeur"):
        _attr(geo, "prim", nom, 0.0)
    tab_s = ("a_type", "a_ref", "a_mat", "a_franch", "l_nature", "l_bord", "l_marq", "l_mmod")
    tab_f = ("a_larg", "a_dz", "a_devers", "l_vue", "l_mlu", "l_mum")
    for nom in tab_s:
        geo.addArrayAttrib(hou.attribType.Point, nom, hou.attribData.String)
    for nom in tab_f:
        geo.addArrayAttrib(hou.attribType.Point, nom, hou.attribData.Float)
    g_gi = geo.createPointGroup("giratoire")
    g_br = geo.createPointGroup("branche")
    geo.addArrayAttrib(hou.attribType.Point, "pp_zxy", hou.attribData.Float)
    geo.addArrayAttrib(hou.attribType.Point, "pp_zn", hou.attribData.Int)
    geo.addArrayAttrib(hou.attribType.Point, "pp_zid", hou.attribData.String)
    g_pa = geo.createPointGroup("passage")
    g_il = geo.createPrimGroup("ilot_g")
    anneaux, ids = [], []
    n_br = n_il = 0
    for c in m.get("carrefours", []):
        if c.get("type") not in ("giratoire", "mini_giratoire"):
            continue
        cid = c["id"]
        ids.append(cid)
        an = c.get("anneau") or {}
        cons = an.get("construction") or {}
        ctr = loc(c["centre"])
        ra = cons.get("route_anneau", "")
        if ra:
            anneaux.append(ra)
        # point du giratoire : anneau du modèle et profil de la route d'anneau (bandes de l'intérieur vers l'extérieur :
        # l'anneau est parcouru dans le sens trigonométrique, t positif à gauche = vers le centre)
        p = geo.createPoint()
        g_gi.add(p)
        p.setPosition(h(c["centre"]))
        Rg = float(an.get("rayon_exterieur_m", 0.0))
        Ri = float(an.get("rayon_ilot_central_m", 0.0))
        slf = float(an.get("bande_franchissable_m", 0.0) or 0.0)
        vals = {"id": cid, "type": c.get("type", ""), "route_anneau": ra, "ilot_central": an.get("ilot_central", "") or "",
                "sens": an.get("sens", "trigonometrique"), "regles": " ".join(c.get("regles", []))}
        for kk, v in vals.items():
            p.setAttribValue(kk, str(v))
        p.setAttribValue("centre", ctr)
        p.setAttribValue("Rg", Rg)
        p.setAttribValue("la", float(an.get("largeur_anneau_m", 0.0)))
        p.setAttribValue("Ri", Ri)
        p.setAttribValue("slf", slf)
        p.setAttribValue("Ri_inf", float(cons.get("Ri_infranchissable", Ri - slf)))
        r_an = routes.get(ra) or {}
        p.setAttribValue("agglomeration", 1 if r_an.get("agglomeration", True) else 0)
        secs = r_an.get("sections") or []
        pr_an = profils.get(secs[0]["profil"]) if secs else None
        if pr_an:
            bs = pr_an.get("bandes", [])
            p.setAttribValue("a_type", [b.get("type", "") for b in bs])
            p.setAttribValue("a_ref", [(b.get("niveau") or {}).get("reference", "") for b in bs])
            p.setAttribValue("a_mat", [b.get("materiau_id", "") for b in bs])
            p.setAttribValue("a_franch", [str((b.get("terre_plein") or {}).get("franchissable", "")) for b in bs])
            p.setAttribValue("a_larg", [_largeur(b) for b in bs])
            p.setAttribValue("a_dz", [float((b.get("niveau") or {}).get("dz_m", 0.0) or 0.0) for b in bs])
            p.setAttribValue("a_devers", [float((b.get("niveau") or {}).get("devers_pct", 0.0) or 0.0) for b in bs])
            li = pr_an.get("limites", [])
            p.setAttribValue("l_nature", [",".join(x.get("nature", [])) for x in li])
            p.setAttribValue("l_bord", [((x.get("bordure") or {}).get("profil", "")) for x in li])
            p.setAttribValue("l_vue", [float((x.get("bordure") or {}).get("vue_m", 0.0) or 0.0) for x in li])
            p.setAttribValue("l_marq", [_txt(x.get("marquages", [])) for x in li])
            mq0 = [(x.get("marquages") or [{}])[0] for x in li]
            p.setAttribValue("l_mmod", [str(q.get("modulation", "")) for q in mq0])
            p.setAttribValue("l_mlu", [float(q.get("largeur_u", 0.0) or 0.0) for q in mq0])
            p.setAttribValue("l_mum", [float(q.get("u_m", 0.0) or 0.0) for q in mq0])
            p.setAttribValue("u_m", float(pr_an.get("u_m", 0.05)))
        # branches (ordre trigonométrique des azimuts), raccordements du modèle
        racc = cons.get("raccordements") or {}
        fr = {f.get("route"): f for f in c.get("frontiere", []) if f.get("type") == "joint"}
        brs = sorted(c["branches"], key=lambda b: float(b.get("azimut_deg", 0.0)) % 360.0)
        for k, b in enumerate(brs):
            q = geo.createPoint()
            g_br.add(q)
            n_br += 1
            q.setPosition(h(c["centre"]))
            la_ = b.get("ligne_arret") or {}
            rc = racc.get(b["id"]) or {}
            rr = routes.get(b["route"]) or {}
            sf = b.get("s_frontiere_m")
            if sf is None:
                f = fr.get(b["route"]) or {}
                sf = f.get("s0", (rr.get("ligne_reference") or {}).get("longueur_m", -1.0))
            vals = {"carrefour": cid, "branche": b["id"], "route": b["route"], "extremite": b.get("extremite", ""),
                    "regime": b.get("regime", ""), "ligne_type": la_.get("type", ""),
                    "passage": b.get("passage_pieton", "") or "", "ilot": b.get("ilot_separateur", "") or "",
                    "regle_racc": rc.get("source", "")}
            for kk, v in vals.items():
                q.setAttribValue(kk, str(v))
            q.setAttribValue("s_front", float(sf))
            q.setAttribValue("azimut", float(b.get("azimut_deg", 0.0)) % 360.0)
            q.setAttribValue("rayon_coin", -1.0)
            q.setAttribValue("ligne_distance", float(la_.get("distance_m", 0.0) or 0.0))
            q.setAttribValue("rang", k)
            q.setAttribValue("centre", ctr)
            q.setAttribValue("Re", float(rc.get("entree_m", -1.0)))
            q.setAttribValue("Rs", float(rc.get("sortie_m", -1.0)))
            q.setAttribValue("n_entrantes", len(b.get("bandes_entrantes", [])))
            q.setAttribValue("n_sortantes", len(b.get("bandes_sortantes", [])))
        for pp_ in c.get("passages_pieton", []):
            q = geo.createPoint()
            g_pa.add(q)
            ax = pp_.get("axe") or [c["centre"], c["centre"]]
            q.setPosition(h(ax[0]))
            q.setAttribValue("id", pp_["id"])
            q.setAttribValue("route", pp_.get("route", ""))
            q.setAttribValue("carrefour", cid)
            q.setAttribValue("s", float(pp_.get("s", 0.0)))
            q.setAttribValue("largeur", float(pp_.get("largeur_m", 4.0)))
            q.setAttribValue("axe0", loc(ax[0]))
            q.setAttribValue("axe1", loc(ax[-1]))
            q.setAttribValue("refuge", str(pp_.get("refuge") or ""))
            q.setAttribValue("abaisses", 1 if pp_.get("abaisses", True) else 0)
            q.setAttribValue("bev", 1 if pp_.get("bev", True) else 0)
            zxy, zn, zid = _zones_passage(m, pp_.get("route", ""), pp_.get("s", 0.0), o)
            q.setAttribValue("pp_zxy", zxy)
            q.setAttribValue("pp_zn", zn)
            q.setAttribValue("pp_zid", zid)
    for i in m.get("ilots", []):
        if i.get("carrefour") not in ids:
            continue
        pg = (i.get("polygone") or {}).get("exterieur") or []
        if pg and pg[0] == pg[-1]:
            pg = pg[:-1]
        if len(pg) < 3:
            continue
        pts = geo.createPoints([h(q) for q in pg])
        pr = geo.createPolygon(is_closed=True)
        for q in pts:
            pr.addVertex(q)
        g_il.add(pr)
        n_il += 1
        tp = i.get("terre_plein") or {}
        ce = tp.get("ceinture") or {}
        rem = tp.get("remplissage") or {}
        nez = i.get("nez") or []
        ref = i.get("refuge") or {}
        for kk, v in (("id", i["id"]), ("type", i.get("type", "")), ("carrefour", i.get("carrefour", "")),
                      ("materiau", rem.get("materiau_id", "")), ("remplissage", rem.get("type", "")),
                      ("franchissable", str(tp.get("franchissable", ""))), ("ceinture", ce.get("profil", "")),
                      ("contour", _txt(tp.get("marquage_contour")) if tp.get("marquage_contour") else ""),
                      ("refuge_traversee", ref.get("traversee", "") or "")):
            pr.setAttribValue(kk, str(v))
        pr.setAttribValue("ceinture_vue", float(ce.get("vue_m", 0.0) or 0.0))
        pr.setAttribValue("surelevation", float(tp.get("surelevation_m", 0.0) or 0.0))
        pr.setAttribValue("bombement", float(rem.get("bombement_m", 0.0) or 0.0))
        pr.setAttribValue("nez_rayon", float(nez[0].get("rayon_m", 0.0)) if nez else 0.0)
        pr.setAttribValue("refuge_largeur", float(ref.get("largeur_m", 0.0) or 0.0))
    geo.addArrayAttrib(hou.attribType.Global, "rg_anneaux", hou.attribData.String)
    geo.setGlobalAttribValue("rg_anneaux", anneaux)
    geo.addArrayAttrib(hou.attribType.Global, "rg_giratoires_ids", hou.attribData.String)
    geo.setGlobalAttribValue("rg_giratoires_ids", ids)
    geo.addAttrib(hou.attribType.Global, "rg_giratoires", "")
    geo.setGlobalAttribValue("rg_giratoires", _txt({
        "fichier": chemin.replace("\\", "/"), "sha256": hashlib.sha256(brut).hexdigest(),
        "giratoires": len(ids), "branches": n_br, "ilots": n_il, "origine_l93": [o[0], o[1]]}))
