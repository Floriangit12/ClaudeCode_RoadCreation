"""Objets à contrôler par le solveur de cohérence : lecture seule des couches du paquet et des specs.

- mobilier.geojson : 153 objets ponctuels + 51 clôtures (lignes, jamais déplacées) ;
- arbres.geojson : 467 arbres ;
- instances.json : têtes de feux et panonceaux portés (parent = support), azimut = 90 − yaw ;
- assets/specs/feux.json (supports_site) et panneaux.json (positions) : HYPOTHÈSES CONCURRENTES
  (même objet placé ou orienté autrement par une autre source, ou support absent du mobilier) ;
  appariées au mobilier par id, sinon par code et distance (≤ 6 m).

Classe de preuve (σ, déplacement maximal) : `resolution.qualite_preuve` des règles (motifs regex
sur le champ source), meilleure preuve du groupe rigide (même poteau, support cité), surclassée en
`photo_pnp` si la triangulation Panoramax (enrichi/poses/triangulation.json) a confirmé le mât.
"""
import re
import sys

import numpy as np

from commun import DONNEES, RACINE, SPECS, lire_geojson, lire_json, repere

sys.path.insert(0, str(RACINE / "recon/pcg/specs_outils"))
from valider_regles_implantation import classe_preuve, groupes_support  # noqa: E402

TRIANGULATION = RACINE / "recon/out/paquet_jardin/v2/enrichi/poses/triangulation.json"
FIN_TRAVAUX = "2025-08-31"
CLASSES_ANTERIEURES = {"lidar2021", "ortho2022", "panoramax_brut", "constat", "lidar2021_couronne", "inventaire"}


def rayon_emprise(voc, typ):
    d = voc["objet_types"].get(typ, {})
    if "emprise_diametre_m" in d:
        return d["emprise_diametre_m"] / 2.0
    if "emprise_largeur_m" in d:
        return d["emprise_largeur_m"] / 2.0
    return 0.05


def dims_emprise(voc, typ):
    """(longueur, largeur) de l'emprise au sol (rectangle) ou None pour un objet rond."""
    d = voc["objet_types"].get(typ, {})
    if "emprise_longueur_m" in d:
        return d["emprise_longueur_m"], d.get("emprise_largeur_m", 0.1)
    return None


def azimut_grossier(az, pas=45.0):
    return az is not None and abs((float(az) / pas) - round(float(az) / pas)) < 1e-6


def date_source(src):
    """Date la plus récente citée dans la source (AAAA-MM-JJ ou AAAA-MM), ou None."""
    ds = re.findall(r"(20\d\d-\d\d(?:-\d\d)?)", src or "")
    if not ds:
        return None
    return max(d if len(d) == 10 else d + "-01" for d in ds)


def classe_developpement(h):
    """VEG-02 : petit (h < 9 m), moyen (9-15 m), grand (> 15 m)."""
    if h is None:
        return "moyen"
    return "petit" if h < 9 else "moyen" if h <= 15 else "grand"


def charger(regles):
    """Liste d'objets (dict) triés par id + hypothèses concurrentes des specs."""
    res = regles["resolution"]
    voc = regles["vocabulaire"]
    mob = lire_geojson(DONNEES / "objets/mobilier.geojson")
    pts = [f for f in mob if f["geometry"]["type"] == "Point"]
    groupe = groupes_support(pts)
    tri = {}
    if TRIANGULATION.exists():
        for r in lire_json(TRIANGULATION)["verification_mobilier"]["resultats"]:
            for oid in r["objets"]:
                tri[oid] = r
    objets = []
    for f in pts:
        p = f["properties"]
        xy = repere(np.asarray(f["geometry"]["coordinates"][:2], float)[None])[0]
        cle, sigma, dmax = classe_preuve(p.get("source"), p.get("confiance"), res)
        o = dict(id=p["id"], couche="mobilier", type=p["type"], code=p.get("code"), p0=xy,
                 z0=p.get("z_local"), z_source=p.get("z_source"), azimut0=p.get("azimut_deg"),
                 hauteur=p.get("hauteur_m"), statut=p.get("statut_2026") or "", confiance=p.get("confiance"),
                 source=p.get("source") or "", groupe=groupe[p["id"]], preuve=cle, sigma=sigma, dmax=dmax,
                 rayon=rayon_emprise(voc, p["type"]), dims=dims_emprise(voc, p["type"]), props=p,
                 triangulation=None)
        r = tri.get(p["id"])
        if r and r.get("position_triangulee"):
            o["triangulation"] = {k: r.get(k) for k in ("position_triangulee", "ecart_m", "fiable", "decision",
                                                       "n_inliers", "angle_intersection_deg", "conclusion",
                                                       "ecart_type_m", "revue_visuelle", "planche_comparaison")}
            if r.get("decision") in ("garder", "affiner"):
                et = float(np.hypot(*r["ecart_type_m"]))
                o["preuve_photo"] = dict(classe="photo_pnp", sigma=max(0.1, et), decision=r["decision"],
                                         position=r["position_triangulee"])
        objets.append(o)
    # groupes rigides complétés : parent des instances (panneau sur candélabre) et objets confondus
    # (< 0,15 m) dont l'un est un panneau
    inst = lire_json(DONNEES / "objets/instances.json")["instances"]
    par_id = {o["id"]: o for o in objets}
    for i in inst:
        par = str(i.get("parent") or "")
        if i["id"] in par_id and par in par_id and par_id[i["id"]]["groupe"] == i["id"]:
            par_id[i["id"]]["groupe"] = par_id[par]["groupe"]
    for a in objets:
        for b in objets:
            if a["id"] < b["id"] and a["groupe"] != b["groupe"] and "panneau" in (a["type"], b["type"]) \
                    and float(np.hypot(*(a["p0"] - b["p0"]))) < 0.15:
                gb = b["groupe"]
                for o in objets:
                    if o["groupe"] == gb:
                        o["groupe"] = a["groupe"]
    # preuve propre, surclassée en photo_pnp si la triangulation a confirmé le mât
    for o in objets:
        o["preuve_propre"] = o["preuve"]
        pp = o.get("preuve_photo")
        if pp and pp["sigma"] < o["sigma"]:
            o["preuve"], o["sigma"] = "photo_pnp", round(pp["sigma"], 3)
            o["dmax"] = max(o["dmax"], res["qualite_preuve"]["photo_pnp"]["deplacement_max_m"])
    # meilleure preuve du groupe rigide (GEN-05) : le groupe se résout comme un seul objet
    meilleure = {}
    for o in objets:
        g = o["groupe"]
        if g not in meilleure or o["sigma"] < meilleure[g][1]:
            meilleure[g] = (o["preuve"], o["sigma"], o["dmax"])
    for o in objets:
        o["preuve"], o["sigma"], o["dmax"] = meilleure[o["groupe"]]
    # clôtures (lignes) : limites dures, jamais déplacées (BAR-02)
    clotures = []
    for f in mob:
        if f["geometry"]["type"] == "LineString":
            p = f["properties"]
            clotures.append(dict(id=p["id"], couche="mobilier", type=p["type"], statut=p.get("statut_2026") or "",
                                 source=p.get("source") or "", P=repere(np.asarray(f["geometry"]["coordinates"])[:, :2]),
                                 longueur=p.get("longueur_m")))
    # arbres
    for f in lire_geojson(DONNEES / "objets/arbres.geojson"):
        p = f["properties"]
        xy = repere(np.asarray(f["geometry"]["coordinates"][:2], float)[None])[0]
        cle, sigma, dmax = classe_preuve(p.get("source"), p.get("confiance"), res)
        objets.append(dict(id=p["id"], couche="arbres", type="arbre", code=None, p0=xy, z0=p.get("z_local"),
                           z_source=p.get("z_source"), azimut0=None, hauteur=p.get("hauteur_m"),
                           statut=p.get("statut_2026") or "", confiance=p.get("confiance"),
                           source=p.get("source") or "", groupe=p["id"], preuve=cle, sigma=sigma, dmax=dmax,
                           preuve_propre=cle, rayon=rayon_emprise(voc, "arbre"), dims=None, props=p,
                           developpement=classe_developpement(p.get("hauteur_m")), triangulation=None))
    objets.sort(key=lambda o: o["id"])
    return objets, clotures


def tetes(objets):
    """Têtes et panonceaux portés (instances.json) rattachés à leur support."""
    par_id = {o["id"]: o for o in objets}
    out = []
    inst = lire_json(DONNEES / "objets/instances.json")["instances"]
    for i in inst:
        if not i.get("type_tete") or i.get("parent") not in par_id:
            continue
        sup = par_id[i["parent"]]
        az = (90.0 - float(i["yaw_deg"])) % 360.0
        out.append(dict(id=i["id"], type="tete_feu", type_tete=i["type_tete"], parent=i["parent"],
                        p=np.array([i["x"], i["y"]]), z=i["z"], azimut0=az, statut=i.get("statut") or "",
                        etat=i.get("etat") or "", support=sup))
    out.sort(key=lambda t: t["id"])
    return out


def hypotheses_specs(objets):
    """Positions et azimuts alternatifs donnés par feux.json et panneaux.json."""
    par_id = {o["id"]: o for o in objets}
    hyps = []
    feux = lire_json(SPECS / "feux.json")
    for s in feux["supports_site"]:
        xy = np.array(s["local"][:2], float)
        o = par_id.get(s["id"])
        tetes_ = [dict(type=t["type"], azimut=t.get("azimut_deg"), h=t.get("hauteur_centre_m")) for t in s.get("tetes", [])]
        hyps.append(dict(id="SPEC-" + s["id"], spec="feux.json", ref=s["id"], code="support_feux", p=xy,
                         azimut=None, objet=o["id"] if o else None, tetes=tetes_, statut=s.get("statut_2026"),
                         confiance=s.get("confiance"), source=s.get("source"), role=s.get("role")))
    pan = lire_json(SPECS / "panneaux.json")
    for e in pan["panneaux"]:
        code = e["code"].split(" ")[0]
        for q in e.get("positions") or []:
            xy = np.array(q["local"][:2], float)
            o = par_id.get(q.get("id"))
            if o is not None and float(np.hypot(*(o["p0"] - xy))) > 10.0:
                o = None                 # même identifiant, autre objet (numérotation différente des specs)
            if o is None:
                cand = [x for x in objets if x["type"] == "panneau" and (x["code"] or "").startswith(code[:3])
                        and float(np.hypot(*(x["p0"] - xy))) <= 6.0]
                cand.sort(key=lambda x: (float(np.hypot(*(x["p0"] - xy))), x["id"]))
                o = cand[0] if cand else None
            hyps.append(dict(id="SPEC-" + q["id"], spec="panneaux.json", ref=q["id"], code=e["code"], p=xy,
                             azimut=q.get("azimut_face_deg"), objet=o["id"] if o else None,
                             statut=q.get("statut_2026"), confiance=q.get("confiance"), source=q.get("source"),
                             ecart_couche=q.get("ecart_couche_objets")))
    hyps.sort(key=lambda h: h["id"])
    return hyps


def anterieure_travaux(o):
    """La preuve de position est-elle antérieure à la fin des travaux 2025 ?"""
    if o["preuve"] in CLASSES_ANTERIEURES and o["preuve"] != "constat":
        return True
    if o["preuve"] == "constat":
        d = date_source(o["source"]) or ("2025-08-31" if "travaux" in o["source"] else None)
        return d is None or d <= FIN_TRAVAUX
    if o["preuve"] in ("osm", "panoramax_brut", "plan2025"):
        d = date_source(o["source"])
        return d is None or d <= FIN_TRAVAUX
    return False


def valide_pour_photo(o, date_photo):
    """Une photo prise à `date_photo` peut-elle prouver la position 2026 de l'objet ?
    Non pour un objet posé ou déduit pour 2026 (aucune photo postérieure aux travaux)."""
    st = o["statut"]
    if st.startswith("déduit 2026") or st.startswith("2026") or st.startswith("planté 2025") or o.get("travaux"):
        return date_photo > FIN_TRAVAUX
    if st.startswith("absent"):
        return False
    return True
